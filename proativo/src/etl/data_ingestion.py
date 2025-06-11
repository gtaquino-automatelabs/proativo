"""
Orquestrador de ingestão automatizada de dados do PROAtivo.

Este módulo implementa o sistema de monitoramento e ingestão automática
de arquivos de dados, com suporte a agendamento e processamento em background.
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Union
import os
from enum import Enum
import json

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
import aiofiles
import aiocron

from ..database.connection import get_db_session
from ..utils.logger import get_logger
from .data_processor import DataProcessor, DataProcessingError

logger = get_logger(__name__)


class IngestionStatus(Enum):
    """Status de ingestão de arquivo."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class FileSystemHandler(FileSystemEventHandler):
    """Handler para eventos do sistema de arquivos."""
    
    def __init__(self, ingestion_service: 'DataIngestionService'):
        """
        Inicializa o handler.
        
        Args:
            ingestion_service: Serviço de ingestão para processar arquivos
        """
        self.ingestion_service = ingestion_service
        self.supported_extensions = {'.csv', '.xml', '.xlsx', '.xls'}
    
    def on_created(self, event: FileSystemEvent):
        """Processa evento de criação de arquivo."""
        if not event.is_directory:
            file_path = Path(event.src_path)
            if file_path.suffix.lower() in self.supported_extensions:
                logger.info(f"Novo arquivo detectado: {file_path}")
                # Adicionar à fila de processamento
                asyncio.create_task(
                    self.ingestion_service.add_to_queue(file_path)
                )
    
    def on_modified(self, event: FileSystemEvent):
        """Processa evento de modificação de arquivo."""
        if not event.is_directory:
            file_path = Path(event.src_path)
            if file_path.suffix.lower() in self.supported_extensions:
                logger.info(f"Arquivo modificado: {file_path}")
                # Adicionar à fila com delay para garantir que escrita terminou
                asyncio.create_task(
                    self.ingestion_service.add_to_queue(file_path, delay=2)
                )


class DataIngestionService:
    """
    Serviço de orquestração da ingestão automatizada de dados.
    
    Funcionalidades:
    - Monitoramento de diretórios
    - Processamento agendado
    - Fila de processamento
    - Controle de estado
    - Retry automático
    """
    
    def __init__(
        self,
        watched_directories: List[Union[str, Path]],
        db_url: Optional[str] = None,
        batch_size: int = 100,
        max_retries: int = 3,
        state_file: Optional[Union[str, Path]] = None
    ):
        """
        Inicializa o serviço de ingestão.
        
        Args:
            watched_directories: Lista de diretórios a monitorar
            db_url: URL de conexão com banco (opcional)
            batch_size: Tamanho do lote para processamento
            max_retries: Número máximo de tentativas
            state_file: Arquivo para persistir estado (opcional)
        """
        self.watched_directories = [Path(d) for d in watched_directories]
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.state_file = Path(state_file) if state_file else Path("ingestion_state.json")
        
        # Configurar banco de dados
        if db_url:
            self.engine = create_async_engine(db_url)
            self.async_session = sessionmaker(
                self.engine, class_=AsyncSession, expire_on_commit=False
            )
        else:
            self.engine = None
            self.async_session = None
        
        # Estado interno
        self.processing_queue: asyncio.Queue = asyncio.Queue()
        self.processed_files: Set[str] = set()
        self.failed_files: Dict[str, int] = {}  # arquivo -> tentativas
        self.file_status: Dict[str, IngestionStatus] = {}
        self.is_running = False
        
        # Observadores de diretório
        self.observers: List[Observer] = []
        
        # Tarefas agendadas
        self.scheduled_tasks: List[aiocron.Cron] = []
        
        # Carregar estado persistido
        self._load_state()
    
    async def start(self):
        """Inicia o serviço de ingestão."""
        logger.info("Iniciando serviço de ingestão de dados")
        
        self.is_running = True
        
        # Iniciar monitoramento de diretórios
        self._start_directory_monitoring()
        
        # Iniciar processador de fila
        asyncio.create_task(self._process_queue())
        
        # Iniciar tarefas agendadas
        self._setup_scheduled_tasks()
        
        logger.info("Serviço de ingestão iniciado com sucesso")
    
    async def stop(self):
        """Para o serviço de ingestão."""
        logger.info("Parando serviço de ingestão")
        
        self.is_running = False
        
        # Parar observadores
        for observer in self.observers:
            observer.stop()
            observer.join()
        
        # Cancelar tarefas agendadas
        for task in self.scheduled_tasks:
            task.stop()
        
        # Salvar estado
        await self._save_state()
        
        # Fechar conexão com banco
        if self.engine:
            await self.engine.dispose()
        
        logger.info("Serviço de ingestão parado")
    
    async def add_to_queue(self, file_path: Union[str, Path], delay: int = 0):
        """
        Adiciona arquivo à fila de processamento.
        
        Args:
            file_path: Caminho do arquivo
            delay: Delay em segundos antes de processar
        """
        file_path = Path(file_path)
        file_str = str(file_path.absolute())
        
        # Verificar se já foi processado
        if file_str in self.processed_files:
            logger.debug(f"Arquivo já processado: {file_path}")
            return
        
        # Verificar se excedeu tentativas
        if self.failed_files.get(file_str, 0) >= self.max_retries:
            logger.warning(f"Arquivo excedeu tentativas máximas: {file_path}")
            self.file_status[file_str] = IngestionStatus.SKIPPED
            return
        
        # Adicionar delay se necessário
        if delay > 0:
            await asyncio.sleep(delay)
        
        # Adicionar à fila
        await self.processing_queue.put(file_path)
        self.file_status[file_str] = IngestionStatus.PENDING
        logger.info(f"Arquivo adicionado à fila: {file_path}")
    
    async def process_file(self, file_path: Path) -> bool:
        """
        Processa um arquivo individual.
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            True se processado com sucesso, False caso contrário
        """
        file_str = str(file_path.absolute())
        self.file_status[file_str] = IngestionStatus.PROCESSING
        
        try:
            # Criar sessão do banco
            async with self.async_session() as session:
                # Criar processador
                processor = DataProcessor(session)
                
                # Processar arquivo
                result = await processor.process_file(
                    file_path,
                    batch_size=self.batch_size
                )
                
                # Marcar como processado
                self.processed_files.add(file_str)
                self.file_status[file_str] = IngestionStatus.COMPLETED
                
                # Remover de falhas se existir
                self.failed_files.pop(file_str, None)
                
                logger.info(
                    f"Arquivo processado com sucesso: {file_path} "
                    f"({result['inserted_records']} registros inseridos)"
                )
                
                return True
                
        except Exception as e:
            logger.error(f"Erro ao processar arquivo {file_path}: {e}")
            
            # Incrementar contador de falhas
            self.failed_files[file_str] = self.failed_files.get(file_str, 0) + 1
            
            if self.failed_files[file_str] >= self.max_retries:
                self.file_status[file_str] = IngestionStatus.FAILED
                logger.error(f"Arquivo falhou após {self.max_retries} tentativas: {file_path}")
            else:
                self.file_status[file_str] = IngestionStatus.PENDING
                # Re-adicionar à fila para retry
                await self.add_to_queue(file_path, delay=5)
            
            return False
    
    async def process_directory(
        self,
        directory_path: Union[str, Path],
        recursive: bool = True
    ) -> Dict[str, any]:
        """
        Processa todos os arquivos em um diretório.
        
        Args:
            directory_path: Caminho do diretório
            recursive: Se deve processar subdiretórios
            
        Returns:
            Estatísticas do processamento
        """
        directory_path = Path(directory_path)
        
        # Coletar arquivos
        pattern = "**/*" if recursive else "*"
        files = []
        
        for ext in ['.csv', '.xml', '.xlsx', '.xls']:
            files.extend(directory_path.glob(f"{pattern}{ext}"))
        
        # Adicionar à fila
        for file_path in files:
            await self.add_to_queue(file_path)
        
        return {
            'directory': str(directory_path),
            'files_queued': len(files)
        }
    
    def _start_directory_monitoring(self):
        """Inicia monitoramento dos diretórios configurados."""
        handler = FileSystemHandler(self)
        
        for directory in self.watched_directories:
            if directory.exists() and directory.is_dir():
                observer = Observer()
                observer.schedule(handler, str(directory), recursive=True)
                observer.start()
                self.observers.append(observer)
                logger.info(f"Monitorando diretório: {directory}")
            else:
                logger.warning(f"Diretório não encontrado: {directory}")
    
    def _setup_scheduled_tasks(self):
        """Configura tarefas agendadas."""
        # Processar diretórios a cada hora
        @aiocron.crontab('0 * * * *')
        async def hourly_scan():
            logger.info("Executando varredura horária de diretórios")
            for directory in self.watched_directories:
                await self.process_directory(directory)
        
        # Salvar estado a cada 5 minutos
        @aiocron.crontab('*/5 * * * *')
        async def save_state():
            await self._save_state()
        
        # Relatório diário
        @aiocron.crontab('0 9 * * *')
        async def daily_report():
            await self._generate_daily_report()
    
    async def _process_queue(self):
        """Processa continuamente a fila de arquivos."""
        while self.is_running:
            try:
                # Pegar próximo arquivo da fila (com timeout)
                file_path = await asyncio.wait_for(
                    self.processing_queue.get(),
                    timeout=1.0
                )
                
                # Processar arquivo
                await self.process_file(file_path)
                
            except asyncio.TimeoutError:
                # Continuar loop se não há arquivos
                continue
            except Exception as e:
                logger.error(f"Erro no processador de fila: {e}")
                await asyncio.sleep(5)
    
    async def _save_state(self):
        """Salva estado atual em arquivo."""
        state = {
            'processed_files': list(self.processed_files),
            'failed_files': self.failed_files,
            'file_status': {k: v.value for k, v in self.file_status.items()},
            'last_saved': datetime.now().isoformat()
        }
        
        try:
            async with aiofiles.open(self.state_file, 'w') as f:
                await f.write(json.dumps(state, indent=2))
            logger.debug("Estado salvo com sucesso")
        except Exception as e:
            logger.error(f"Erro ao salvar estado: {e}")
    
    def _load_state(self):
        """Carrega estado do arquivo."""
        if not self.state_file.exists():
            return
        
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            
            self.processed_files = set(state.get('processed_files', []))
            self.failed_files = state.get('failed_files', {})
            self.file_status = {
                k: IngestionStatus(v) 
                for k, v in state.get('file_status', {}).items()
            }
            
            logger.info(f"Estado carregado: {len(self.processed_files)} arquivos processados")
        except Exception as e:
            logger.error(f"Erro ao carregar estado: {e}")
    
    async def _generate_daily_report(self):
        """Gera relatório diário de processamento."""
        report = {
            'date': datetime.now().date().isoformat(),
            'total_processed': len(self.processed_files),
            'total_failed': len([
                f for f, s in self.file_status.items() 
                if s == IngestionStatus.FAILED
            ]),
            'total_pending': await self.processing_queue.qsize(),
            'status_summary': {}
        }
        
        # Contar por status
        for status in IngestionStatus:
            count = len([
                f for f, s in self.file_status.items() 
                if s == status
            ])
            report['status_summary'][status.value] = count
        
        logger.info(f"Relatório diário: {report}")
        
        # Salvar relatório
        report_file = Path(f"ingestion_report_{report['date']}.json")
        async with aiofiles.open(report_file, 'w') as f:
            await f.write(json.dumps(report, indent=2))
    
    def get_status(self) -> Dict[str, any]:
        """
        Retorna status atual do serviço.
        
        Returns:
            Dicionário com informações de status
        """
        return {
            'is_running': self.is_running,
            'watched_directories': [str(d) for d in self.watched_directories],
            'queue_size': self.processing_queue.qsize(),
            'processed_files': len(self.processed_files),
            'failed_files': len(self.failed_files),
            'status_counts': {
                status.value: len([
                    f for f, s in self.file_status.items() 
                    if s == status
                ])
                for status in IngestionStatus
            }
        }