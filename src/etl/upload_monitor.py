"""
Monitor de diretório de uploads.

Monitora o diretório data/uploads para novos arquivos enviados via interface web
e os processa automaticamente usando o pipeline ETL existente.
"""

import logging
import asyncio
import time
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from threading import Thread
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import json
import shutil

from .data_processor import DataProcessor, FileFormat, DataType
from .exceptions import DataProcessingError

try:
    from ..database.repositories import RepositoryManager
except ImportError:
    RepositoryManager = None

logger = logging.getLogger(__name__)


class UploadFileHandler(FileSystemEventHandler):
    """Handler para eventos de arquivo no diretório de uploads."""
    
    def __init__(self, upload_monitor: 'UploadMonitor'):
        """Inicializa o handler.
        
        Args:
            upload_monitor: Instância do monitor de uploads
        """
        super().__init__()
        self.upload_monitor = upload_monitor
    
    def on_created(self, event):
        """Chamado quando um arquivo é criado."""
        if not event.is_directory:
            self.upload_monitor.queue_file_for_processing(Path(event.src_path))
    
    def on_moved(self, event):
        """Chamado quando um arquivo é movido."""
        if not event.is_directory:
            self.upload_monitor.queue_file_for_processing(Path(event.dest_path))


class UploadStatus:
    """Status de processamento de um upload."""
    
    def __init__(self, file_path: Path, upload_id: Optional[str] = None):
        """Inicializa status de upload.
        
        Args:
            file_path: Caminho do arquivo
            upload_id: ID único do upload
        """
        self.file_path = file_path
        self.upload_id = upload_id or file_path.stem
        self.status = "pending"  # pending, processing, completed, failed
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self.records_processed = 0
        self.records_valid = 0
        self.records_invalid = 0
        self.file_size = file_path.stat().st_size if file_path.exists() else 0
        self.data_type: Optional[DataType] = None
        self.file_format: Optional[FileFormat] = None


class UploadMonitor:
    """Monitor principal para arquivos de upload."""
    
    def __init__(self, upload_dir: Path, repository_manager=None):
        """Inicializa o monitor de uploads.
        
        Args:
            upload_dir: Diretório de uploads para monitorar
            repository_manager: Gerenciador de repositórios
        """
        self.upload_dir = Path(upload_dir)
        self.processed_dir = self.upload_dir / "processed"
        self.failed_dir = self.upload_dir / "failed"
        
        # Cria diretórios necessários
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.failed_dir.mkdir(parents=True, exist_ok=True)
        
        # Inicializa processador de dados
        self.repository_manager = repository_manager
        self.data_processor = DataProcessor(repository_manager)
        
        # Configurações (usando variáveis de ambiente)
        self.config = {
            'processing_delay_seconds': int(os.getenv('UPLOAD_PROCESSING_DELAY_SECONDS', '2')),
            'max_file_age_hours': int(os.getenv('UPLOAD_MAX_FILE_AGE_HOURS', '24')),
            'supported_extensions': os.getenv('UPLOAD_SUPPORTED_EXTENSIONS', '.csv,.xml,.xlsx,.xls').split(','),
            'max_file_size_mb': int(os.getenv('MAX_FILE_SIZE_MB', '50')),
            'cleanup_interval_hours': int(os.getenv('UPLOAD_CLEANUP_INTERVAL_HOURS', '6'))
        }
        
        # Estado do monitor
        self.running = False
        self.observer = None
        self.processing_thread = None
        self.cleanup_thread = None
        
        # Fila de processamento e status
        self.processing_queue: List[UploadStatus] = []
        self.upload_status: Dict[str, UploadStatus] = {}
        
        # Estatísticas
        self.stats = {
            'files_monitored': 0,
            'files_processed': 0,
            'files_failed': 0,
            'total_records_processed': 0,
            'last_cleanup': None,
            'monitor_started': None
        }
    
    def start(self) -> None:
        """Inicia o monitor de uploads."""
        if self.running:
            logger.warning("Monitor de uploads já está em execução")
            return
        
        self.running = True
        self.stats['monitor_started'] = datetime.now()
        
        logger.info(f"Iniciando monitor de uploads em: {self.upload_dir}")
        
        # Configura observer do watchdog
        self.observer = Observer()
        handler = UploadFileHandler(self)
        self.observer.schedule(handler, str(self.upload_dir), recursive=False)
        self.observer.start()
        
        # Inicia thread de processamento
        self.processing_thread = Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()
        
        # Inicia thread de limpeza
        self.cleanup_thread = Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        
        # Processa arquivos já existentes
        self._scan_existing_files()
        
        logger.info("Monitor de uploads iniciado com sucesso")
    
    def stop(self) -> None:
        """Para o monitor de uploads."""
        if not self.running:
            return
        
        logger.info("Parando monitor de uploads")
        self.running = False
        
        # Para observer
        if self.observer:
            self.observer.stop()
            self.observer.join()
        
        logger.info("Monitor de uploads parado")
    
    def queue_file_for_processing(self, file_path: Path) -> None:
        """Adiciona arquivo à fila de processamento.
        
        Args:
            file_path: Caminho do arquivo para processar
        """
        if not self._is_valid_file(file_path):
            logger.debug(f"Arquivo ignorado (não válido): {file_path}")
            return
        
        # Verifica se já está sendo processado
        upload_id = self._generate_upload_id(file_path)
        if upload_id in self.upload_status:
            logger.debug(f"Arquivo já está sendo processado: {file_path}")
            return
        
        # Busca upload existente no banco de dados pelo nome do arquivo
        existing_upload_id = self._find_existing_upload_id(file_path)
        if existing_upload_id:
            upload_id = existing_upload_id
            logger.debug(f"Arquivo encontrado no banco com ID: {upload_id}")
        
        # Cria status de upload
        upload_status = UploadStatus(file_path, upload_id)
        self.upload_status[upload_id] = upload_status
        self.processing_queue.append(upload_status)
        self.stats['files_monitored'] += 1
        
        logger.info(f"Arquivo adicionado à fila de processamento: {file_path}")
    
    def _is_valid_file(self, file_path: Path) -> bool:
        """Verifica se o arquivo é válido para processamento."""
        if not file_path.exists():
            return False
        
        if file_path.suffix.lower() not in self.config['supported_extensions']:
            return False
        
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > self.config['max_file_size_mb']:
            logger.warning(f"Arquivo muito grande ({file_size_mb:.1f}MB): {file_path}")
            return False
        
        if file_path.name.startswith('.') or file_path.name.startswith('~'):
            return False
        
        return True
    
    def _generate_upload_id(self, file_path: Path) -> str:
        """Gera ID único para upload."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{timestamp}_{file_path.stem}"
    
    def _processing_loop(self) -> None:
        """Loop principal de processamento."""
        while self.running:
            try:
                if self.processing_queue:
                    upload_status = self.processing_queue.pop(0)
                    self._process_upload(upload_status)
                else:
                    time.sleep(1)
            except Exception as e:
                logger.error(f"Erro no loop de processamento: {e}")
                time.sleep(5)
    
    def _process_upload(self, upload_status: UploadStatus) -> None:
        """Processa um upload específico."""
        logger.info(f"Iniciando processamento: {upload_status.file_path}")
        
        upload_status.status = "processing"
        upload_status.started_at = datetime.now()
        
        # Atualiza status no banco de dados
        self._update_database_status(upload_status.upload_id, "processing", started_at=upload_status.started_at)
        
        try:
            # Aguarda para garantir que o arquivo foi completamente escrito
            time.sleep(self.config['processing_delay_seconds'])
            
            # Detecta formato e tipo de dados
            upload_status.file_format = self.data_processor.detect_file_format(upload_status.file_path)
            upload_status.data_type = self.data_processor.detect_data_type(
                upload_status.file_path, upload_status.file_format
            )
            
            # Processa arquivo
            if self.repository_manager:
                # Processa e salva no banco
                result = asyncio.run(self.data_processor.process_and_save(
                    upload_status.file_path,
                    upload_status.data_type,
                    upload_status.file_format
                ))
                
                upload_status.records_processed = result.get('records_processed', 0)
                upload_status.records_valid = result.get('records_saved', 0)
                upload_status.records_invalid = result.get('validation_errors', 0)
            else:
                # Apenas processa sem salvar
                valid_records, validation_errors = self.data_processor.process_file(
                    upload_status.file_path,
                    upload_status.data_type,
                    upload_status.file_format
                )
                
                upload_status.records_processed = len(valid_records) + len(validation_errors)
                upload_status.records_valid = len(valid_records)
                upload_status.records_invalid = len(validation_errors)
            
            # Move para diretório de processados
            self._move_to_processed(upload_status)
            
            upload_status.status = "completed"
            upload_status.completed_at = datetime.now()
            
            # Atualiza status final no banco de dados
            self._update_database_status(
                upload_status.upload_id, 
                "completed",
                completed_at=upload_status.completed_at,
                records_processed=upload_status.records_processed,
                records_valid=upload_status.records_valid,
                records_invalid=upload_status.records_invalid,
                file_format=upload_status.file_format.value if upload_status.file_format else None,
                data_type=upload_status.data_type.value if upload_status.data_type else None,
                processed_file_path=str(upload_status.file_path)
            )
            
            # Atualiza estatísticas
            self.stats['files_processed'] += 1
            self.stats['total_records_processed'] += upload_status.records_processed
            
            logger.info(f"Upload processado com sucesso: {upload_status.upload_id} "
                       f"({upload_status.records_valid} registros válidos)")
            
        except Exception as e:
            # Move para diretório de falhas
            self._move_to_failed(upload_status)
            
            upload_status.status = "failed"
            upload_status.completed_at = datetime.now()
            upload_status.error_message = str(e)
            
            # Atualiza status de erro no banco de dados
            self._update_database_status(
                upload_status.upload_id, 
                "failed",
                completed_at=upload_status.completed_at,
                error_message=upload_status.error_message,
                records_processed=upload_status.records_processed,
                records_valid=upload_status.records_valid,
                records_invalid=upload_status.records_invalid
            )
            
            self.stats['files_failed'] += 1
            
            logger.error(f"Erro ao processar upload {upload_status.upload_id}: {e}")
    
    def _update_database_status(self, upload_id: str, status: str, **kwargs) -> None:
        """Atualiza o status do upload no banco de dados."""
        if not self.repository_manager:
            return  # Não faz nada se não há repositório configurado
        
        try:
            # Importa dentro do método para evitar dependências circulares
            import asyncio
            from ..database.connection import get_async_session
            from ..database.repositories import RepositoryManager
            
            async def update_status():
                async with get_async_session() as session:
                    repo_manager = RepositoryManager(session)
                    await repo_manager.upload_status.update_status(upload_id, status, **kwargs)
                    await repo_manager.commit()
            
            # Executa a atualização assíncrona
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Se já há um loop rodando, agenda para executar
                    asyncio.create_task(update_status())
                else:
                    # Se não há loop, executa diretamente
                    asyncio.run(update_status())
            except RuntimeError:
                # Fallback para quando não consegue executar async
                asyncio.run(update_status())
            
            logger.debug(f"Status do upload {upload_id} atualizado no banco: {status}")
            
        except Exception as e:
                         logger.warning(f"Erro ao atualizar status do upload {upload_id} no banco: {e}")
             # Não para o processamento se falhar a atualização do banco
    
    def _find_existing_upload_id(self, file_path: Path) -> Optional[str]:
        """Procura upload existente no banco pelo nome do arquivo."""
        if not self.repository_manager:
            return None
        
        try:
            import asyncio
            from ..database.connection import get_async_session
            from ..database.repositories import RepositoryManager
            
            async def find_upload():
                async with get_async_session() as session:
                    repo_manager = RepositoryManager(session)
                    # Busca por nome do arquivo armazenado
                    uploads = await repo_manager.upload_status.list_by_status("uploaded", limit=100)
                    for upload in uploads:
                        if upload.stored_filename == file_path.name:
                            return upload.upload_id
                    return None
            
            # Executa busca
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Se há loop rodando, não pode usar run
                    return None  # Fallback para não bloquear
                else:
                    return asyncio.run(find_upload())
            except RuntimeError:
                return asyncio.run(find_upload())
                
        except Exception as e:
            logger.debug(f"Erro ao buscar upload existente: {e}")
            return None
    
    def _move_to_processed(self, upload_status: UploadStatus) -> None:
        """Move arquivo para diretório de processados com organização por data."""
        try:
            # Cria subdiretório por data
            date_str = datetime.now().strftime("%Y-%m-%d")
            date_dir = self.processed_dir / date_str
            date_dir.mkdir(parents=True, exist_ok=True)
            
            # Gera nome único para evitar conflitos
            dest_path = self._generate_unique_dest_path(
                upload_status.file_path.name, 
                date_dir
            )
            
            # Move arquivo
            shutil.move(str(upload_status.file_path), str(dest_path))
            upload_status.file_path = dest_path
            
            # Cria arquivo de metadados
            self._create_processing_metadata(upload_status, dest_path)
            
            logger.info(f"Arquivo processado movido para: {dest_path}")
            logger.debug(f"Registros: {upload_status.records_valid} válidos, "
                        f"{upload_status.records_invalid} inválidos")
            
        except Exception as e:
            logger.error(f"Erro ao mover arquivo para processados: {e}")
            # Tenta mover para diretório raiz se falhar
            try:
                fallback_path = self.processed_dir / upload_status.file_path.name
                shutil.move(str(upload_status.file_path), str(fallback_path))
                upload_status.file_path = fallback_path
                logger.warning(f"Arquivo movido para fallback: {fallback_path}")
            except Exception as fallback_error:
                logger.error(f"Erro no fallback: {fallback_error}")
    
    def _move_to_failed(self, upload_status: UploadStatus) -> None:
        """Move arquivo para diretório de falhas com organização por data."""
        try:
            # Cria subdiretório por data
            date_str = datetime.now().strftime("%Y-%m-%d")
            date_dir = self.failed_dir / date_str
            date_dir.mkdir(parents=True, exist_ok=True)
            
            # Gera nome único para evitar conflitos
            dest_path = self._generate_unique_dest_path(
                upload_status.file_path.name, 
                date_dir
            )
            
            # Move arquivo
            shutil.move(str(upload_status.file_path), str(dest_path))
            upload_status.file_path = dest_path
            
            # Cria arquivo de erro
            self._create_error_metadata(upload_status, dest_path)
            
            logger.warning(f"Arquivo com falha movido para: {dest_path}")
            if upload_status.error_message:
                logger.error(f"Erro: {upload_status.error_message}")
            
        except Exception as e:
            logger.error(f"Erro ao mover arquivo para falhas: {e}")
            # Tenta mover para diretório raiz se falhar
            try:
                fallback_path = self.failed_dir / upload_status.file_path.name
                shutil.move(str(upload_status.file_path), str(fallback_path))
                upload_status.file_path = fallback_path
                logger.warning(f"Arquivo movido para fallback: {fallback_path}")
            except Exception as fallback_error:
                logger.error(f"Erro no fallback: {fallback_error}")
    
    def _generate_unique_dest_path(self, filename: str, target_dir: Path) -> Path:
        """Gera caminho único para evitar conflitos de nomes."""
        dest_path = target_dir / filename
        
        if not dest_path.exists():
            return dest_path
        
        # Se arquivo já existe, adiciona contador
        file_path = Path(filename)
        stem = file_path.stem
        suffix = file_path.suffix
        
        counter = 1
        while dest_path.exists():
            new_filename = f"{stem}_({counter}){suffix}"
            dest_path = target_dir / new_filename
            counter += 1
        
        return dest_path
    
    def _create_processing_metadata(self, upload_status: UploadStatus, file_path: Path) -> None:
        """Cria arquivo de metadados para arquivo processado com sucesso."""
        try:
            metadata = {
                'upload_id': upload_status.upload_id,
                'original_filename': file_path.name,
                'processed_at': upload_status.completed_at.isoformat() if upload_status.completed_at else None,
                'processing_time_seconds': (
                    (upload_status.completed_at - upload_status.started_at).total_seconds()
                    if upload_status.completed_at and upload_status.started_at else None
                ),
                'file_format': upload_status.file_format.value if upload_status.file_format else None,
                'data_type': upload_status.data_type.value if upload_status.data_type else None,
                'file_size_bytes': upload_status.file_size,
                'records_processed': upload_status.records_processed,
                'records_valid': upload_status.records_valid,
                'records_invalid': upload_status.records_invalid,
                'status': 'completed'
            }
            
            metadata_path = file_path.with_suffix(f"{file_path.suffix}.meta.json")
            
            import json
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Metadados criados: {metadata_path}")
            
        except Exception as e:
            logger.error(f"Erro ao criar metadados: {e}")
    
    def _create_error_metadata(self, upload_status: UploadStatus, file_path: Path) -> None:
        """Cria arquivo de metadados para arquivo que falhou no processamento."""
        try:
            metadata = {
                'upload_id': upload_status.upload_id,
                'original_filename': file_path.name,
                'failed_at': upload_status.completed_at.isoformat() if upload_status.completed_at else None,
                'processing_time_seconds': (
                    (upload_status.completed_at - upload_status.started_at).total_seconds()
                    if upload_status.completed_at and upload_status.started_at else None
                ),
                'file_format': upload_status.file_format.value if upload_status.file_format else None,
                'data_type': upload_status.data_type.value if upload_status.data_type else None,
                'file_size_bytes': upload_status.file_size,
                'error_message': upload_status.error_message,
                'status': 'failed'
            }
            
            metadata_path = file_path.with_suffix(f"{file_path.suffix}.error.json")
            
            import json
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Metadados de erro criados: {metadata_path}")
            
        except Exception as e:
            logger.error(f"Erro ao criar metadados de erro: {e}")
    
    def _scan_existing_files(self) -> None:
        """Escaneia arquivos já existentes no diretório."""
        logger.info("Escaneando arquivos existentes no diretório de uploads")
        
        for file_path in self.upload_dir.iterdir():
            if file_path.is_file():
                self.queue_file_for_processing(file_path)
    
    def _cleanup_loop(self) -> None:
        """Loop de limpeza de arquivos antigos."""
        while self.running:
            try:
                self._cleanup_old_files()
                self.stats['last_cleanup'] = datetime.now()
                
                # Aguarda próxima limpeza
                time.sleep(self.config['cleanup_interval_hours'] * 3600)
            except Exception as e:
                logger.error(f"Erro na limpeza: {e}")
                time.sleep(3600)  # Aguarda 1h antes de tentar novamente
    
    def _cleanup_old_files(self) -> None:
        """Remove arquivos antigos dos diretórios processed e failed."""
        cutoff_time = datetime.now() - timedelta(hours=self.config['max_file_age_hours'])
        removed_count = 0
        
        for directory in [self.processed_dir, self.failed_dir]:
            if not directory.exists():
                continue
                
            # Processa recursivamente incluindo subdiretórios por data
            for item_path in directory.rglob("*"):
                if item_path.is_file():
                    file_time = datetime.fromtimestamp(item_path.stat().st_mtime)
                    if file_time < cutoff_time:
                        try:
                            item_path.unlink()
                            removed_count += 1
                            logger.debug(f"Arquivo antigo removido: {item_path}")
                        except Exception as e:
                            logger.error(f"Erro ao remover arquivo antigo {item_path}: {e}")
            
            # Remove diretórios vazios
            self._remove_empty_directories(directory)
        
        if removed_count > 0:
            logger.info(f"Limpeza concluída: {removed_count} arquivos antigos removidos")
    
    def _remove_empty_directories(self, base_dir: Path) -> None:
        """Remove diretórios vazios recursivamente."""
        try:
            for dir_path in sorted(base_dir.rglob("*"), reverse=True):
                if dir_path.is_dir() and dir_path != base_dir:
                    try:
                        if not any(dir_path.iterdir()):  # Diretório vazio
                            dir_path.rmdir()
                            logger.debug(f"Diretório vazio removido: {dir_path}")
                    except OSError:
                        # Diretório não está vazio ou não pode ser removido
                        pass
        except Exception as e:
            logger.error(f"Erro ao remover diretórios vazios: {e}")
    
    def get_upload_status(self, upload_id: str) -> Optional[UploadStatus]:
        """Obtém status de um upload específico."""
        return self.upload_status.get(upload_id)
    
    def get_all_uploads(self) -> List[UploadStatus]:
        """Obtém lista de todos os uploads."""
        return list(self.upload_status.values())
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtém estatísticas do monitor."""
        return {
            **self.stats,
            'queue_size': len(self.processing_queue),
            'total_uploads': len(self.upload_status),
            'running': self.running,
            'upload_dir': str(self.upload_dir)
        }
    
    def force_process_file(self, file_path: Path) -> Optional[UploadStatus]:
        """Força o processamento de um arquivo específico."""
        if not self._is_valid_file(file_path):
            return None
        
        upload_status = UploadStatus(file_path)
        self.upload_status[upload_status.upload_id] = upload_status
        self._process_upload(upload_status)
        
        return upload_status
    
    def get_processed_files(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Obtém lista de arquivos processados com sucesso."""
        processed_files = []
        
        if not self.processed_dir.exists():
            return processed_files
        
        # Busca arquivos de metadados
        metadata_files = list(self.processed_dir.rglob("*.meta.json"))
        
        # Ordena por data de modificação (mais recentes primeiro)
        metadata_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        for metadata_file in metadata_files[:limit]:
            try:
                import json
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                # Adiciona informações do arquivo
                data_file = metadata_file.with_suffix('').with_suffix('')  # Remove .meta.json
                if data_file.exists():
                    metadata['current_path'] = str(data_file)
                    metadata['metadata_path'] = str(metadata_file)
                    processed_files.append(metadata)
                    
            except Exception as e:
                logger.error(f"Erro ao ler metadados {metadata_file}: {e}")
        
        return processed_files
    
    def get_failed_files(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Obtém lista de arquivos que falharam no processamento."""
        failed_files = []
        
        if not self.failed_dir.exists():
            return failed_files
        
        # Busca arquivos de erro
        error_files = list(self.failed_dir.rglob("*.error.json"))
        
        # Ordena por data de modificação (mais recentes primeiro)
        error_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        for error_file in error_files[:limit]:
            try:
                import json
                with open(error_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                # Adiciona informações do arquivo
                data_file = error_file.with_suffix('').with_suffix('')  # Remove .error.json
                if data_file.exists():
                    metadata['current_path'] = str(data_file)
                    metadata['error_metadata_path'] = str(error_file)
                    failed_files.append(metadata)
                    
            except Exception as e:
                logger.error(f"Erro ao ler metadados de erro {error_file}: {e}")
        
        return failed_files
    
    def get_directory_structure(self) -> Dict[str, Any]:
        """Obtém estrutura de diretórios de upload."""
        structure = {
            'upload_dir': str(self.upload_dir),
            'processed_dir': str(self.processed_dir),
            'failed_dir': str(self.failed_dir),
            'directories': {}
        }
        
        # Conta arquivos em cada diretório
        for dir_name, dir_path in [
            ('upload', self.upload_dir),
            ('processed', self.processed_dir),
            ('failed', self.failed_dir)
        ]:
            if dir_path.exists():
                # Conta total de arquivos
                all_files = list(dir_path.rglob("*"))
                data_files = [f for f in all_files if f.is_file() and not f.name.endswith(('.meta.json', '.error.json'))]
                
                structure['directories'][dir_name] = {
                    'total_files': len(data_files),
                    'total_size_bytes': sum(f.stat().st_size for f in data_files if f.exists()),
                    'subdirectories': []
                }
                
                # Lista subdiretórios (organizados por data)
                subdirs = [d for d in dir_path.iterdir() if d.is_dir()]
                for subdir in sorted(subdirs):
                    subdir_files = [f for f in subdir.rglob("*") if f.is_file() and not f.name.endswith(('.meta.json', '.error.json'))]
                    structure['directories'][dir_name]['subdirectories'].append({
                        'name': subdir.name,
                        'files_count': len(subdir_files),
                        'size_bytes': sum(f.stat().st_size for f in subdir_files if f.exists())
                    })
            else:
                structure['directories'][dir_name] = {
                    'total_files': 0,
                    'total_size_bytes': 0,
                    'subdirectories': []
                }
        
        return structure 