"""
Orquestrador de ingestão automatizada de dados.

Gerencia o processamento automático de arquivos, agendamento de tarefas,
monitoramento de diretórios e integração com o pipeline ETL.
"""

import logging
import asyncio
import schedule
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from threading import Thread
from queue import Queue, Empty
import json

from .data_processor import DataProcessor
from .exceptions import DataProcessingError
from ..database.repositories import RepositoryManager

logger = logging.getLogger(__name__)


class IngestionJob:
    """Representa um job de ingestão."""
    
    def __init__(self, name: str, source_path: Path, schedule_expression: str = None,
                 auto_detect: bool = True, file_pattern: str = "*",
                 move_processed: bool = True, archive_path: Path = None):
        """Inicializa job de ingestão.
        
        Args:
            name: Nome do job
            source_path: Diretório ou arquivo fonte
            schedule_expression: Expressão de agendamento (ex: "daily", "hourly", "*/5")
            auto_detect: Se deve auto-detectar tipos de arquivo e dados
            file_pattern: Padrão de arquivos para processar
            move_processed: Se deve mover arquivos processados
            archive_path: Diretório para arquivar arquivos processados
        """
        self.name = name
        self.source_path = source_path
        self.schedule_expression = schedule_expression
        self.auto_detect = auto_detect
        self.file_pattern = file_pattern
        self.move_processed = move_processed
        self.archive_path = archive_path or source_path / "processed"
        
        # Estatísticas do job
        self.stats = {
            'total_runs': 0,
            'successful_runs': 0,
            'failed_runs': 0,
            'last_run': None,
            'last_success': None,
            'last_error': None,
            'files_processed': 0,
            'records_processed': 0
        }
        
        self.enabled = True


class DataIngestionOrchestrator:
    """Orquestrador principal de ingestão de dados."""
    
    def __init__(self, repository_manager: RepositoryManager = None):
        """Inicializa o orquestrador.
        
        Args:
            repository_manager: Gerenciador de repositórios
        """
        self.repository_manager = repository_manager
        self.data_processor = DataProcessor(repository_manager)
        
        # Jobs de ingestão
        self.jobs: Dict[str, IngestionJob] = {}
        
        # Configurações
        self.config = {
            'max_concurrent_jobs': 3,
            'job_timeout_minutes': 60,
            'retry_attempts': 3,
            'retry_delay_minutes': 5,
            'cleanup_old_logs_days': 30
        }
        
        # Estado do orquestrador
        self.running = False
        self.scheduler_thread = None
        self.job_queue = Queue()
        self.worker_threads = []
        
        # Logs de execução
        self.execution_logs = []
        
    def add_job(self, job: IngestionJob) -> None:
        """Adiciona um job de ingestão.
        
        Args:
            job: Job de ingestão
        """
        self.jobs[job.name] = job
        logger.info(f"Job adicionado: {job.name}")
        
        # Configura agendamento se especificado
        if job.schedule_expression:
            self._schedule_job(job)
    
    def remove_job(self, job_name: str) -> None:
        """Remove um job de ingestão.
        
        Args:
            job_name: Nome do job
        """
        if job_name in self.jobs:
            del self.jobs[job_name]
            logger.info(f"Job removido: {job_name}")
        
        # Remove do agendamento
        schedule.clear(job_name)
    
    def _schedule_job(self, job: IngestionJob) -> None:
        """Configura agendamento para um job.
        
        Args:
            job: Job para agendar
        """
        if not job.schedule_expression:
            return
        
        def job_wrapper():
            if job.enabled:
                self.job_queue.put(job.name)
        
        # Interpreta expressão de agendamento
        if job.schedule_expression == "daily":
            schedule.every().day.at("02:00").do(job_wrapper).tag(job.name)
        elif job.schedule_expression == "hourly":
            schedule.every().hour.do(job_wrapper).tag(job.name)
        elif job.schedule_expression.startswith("*/"):
            # Formato: */5 para cada 5 minutos
            try:
                minutes = int(job.schedule_expression[2:])
                schedule.every(minutes).minutes.do(job_wrapper).tag(job.name)
            except ValueError:
                logger.error(f"Expressão de agendamento inválida: {job.schedule_expression}")
        else:
            logger.warning(f"Expressão de agendamento não reconhecida: {job.schedule_expression}")
    
    def start(self) -> None:
        """Inicia o orquestrador."""
        if self.running:
            logger.warning("Orquestrador já está em execução")
            return
        
        self.running = True
        logger.info("Iniciando orquestrador de ingestão")
        
        # Inicia thread do scheduler
        self.scheduler_thread = Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        # Inicia workers
        for i in range(self.config['max_concurrent_jobs']):
            worker = Thread(target=self._worker_loop, daemon=True)
            worker.start()
            self.worker_threads.append(worker)
        
        logger.info(f"Orquestrador iniciado com {len(self.worker_threads)} workers")
    
    def stop(self) -> None:
        """Para o orquestrador."""
        if not self.running:
            return
        
        logger.info("Parando orquestrador de ingestão")
        self.running = False
        
        # Aguarda threads terminarem
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        
        # Limpa agendamentos
        schedule.clear()
    
    def _scheduler_loop(self) -> None:
        """Loop principal do scheduler."""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                logger.error(f"Erro no scheduler: {e}")
                time.sleep(5)
    
    def _worker_loop(self) -> None:
        """Loop principal do worker."""
        while self.running:
            try:
                # Pega job da fila (timeout de 1 segundo)
                job_name = self.job_queue.get(timeout=1)
                
                if job_name in self.jobs:
                    job = self.jobs[job_name]
                    self._execute_job(job)
                
                self.job_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Erro no worker: {e}")
    
    def _execute_job(self, job: IngestionJob) -> None:
        """Executa um job de ingestão.
        
        Args:
            job: Job para executar
        """
        start_time = datetime.now()
        job.stats['total_runs'] += 1
        job.stats['last_run'] = start_time
        
        logger.info(f"Executando job: {job.name}")
        
        try:
            # Verifica se o caminho fonte existe
            if not job.source_path.exists():
                raise FileNotFoundError(f"Caminho fonte não encontrado: {job.source_path}")
            
            # Processa arquivos
            if job.source_path.is_file():
                results = [asyncio.run(self.data_processor.process_and_save(job.source_path))]
            else:
                # Encontra arquivos para processar
                files_to_process = list(job.source_path.glob(job.file_pattern))
                
                # Filtra apenas arquivos suportados
                supported_extensions = {'.csv', '.xml', '.xlsx', '.xls'}
                files_to_process = [
                    f for f in files_to_process 
                    if f.is_file() and f.suffix.lower() in supported_extensions
                ]
                
                if not files_to_process:
                    logger.info(f"Nenhum arquivo encontrado para o job {job.name}")
                    return
                
                # Processa cada arquivo
                results = []
                for file_path in files_to_process:
                    try:
                        result = asyncio.run(self.data_processor.process_and_save(file_path))
                        results.append(result)
                        
                        # Move arquivo se configurado
                        if job.move_processed and result.get('success'):
                            self._archive_file(file_path, job.archive_path)
                            
                    except Exception as e:
                        logger.error(f"Erro ao processar arquivo {file_path}: {e}")
                        results.append({
                            'file_path': str(file_path),
                            'error': str(e),
                            'success': False
                        })
            
            # Processa resultados
            successful_files = sum(1 for r in results if r.get('success'))
            total_records = sum(r.get('valid_records', 0) for r in results)
            
            # Atualiza estatísticas
            job.stats['successful_runs'] += 1
            job.stats['last_success'] = datetime.now()
            job.stats['files_processed'] += successful_files
            job.stats['records_processed'] += total_records
            
            # Log de execução
            execution_time = (datetime.now() - start_time).total_seconds()
            log_entry = {
                'job_name': job.name,
                'start_time': start_time.isoformat(),
                'execution_time_seconds': execution_time,
                'files_processed': successful_files,
                'total_files': len(results),
                'records_processed': total_records,
                'success': True,
                'results': results
            }
            
            self.execution_logs.append(log_entry)
            logger.info(f"Job {job.name} concluído: {successful_files}/{len(results)} arquivos, {total_records} registros")
            
        except Exception as e:
            # Atualiza estatísticas de erro
            job.stats['failed_runs'] += 1
            job.stats['last_error'] = str(e)
            
            # Log de erro
            execution_time = (datetime.now() - start_time).total_seconds()
            log_entry = {
                'job_name': job.name,
                'start_time': start_time.isoformat(),
                'execution_time_seconds': execution_time,
                'error': str(e),
                'success': False
            }
            
            self.execution_logs.append(log_entry)
            logger.error(f"Erro no job {job.name}: {e}")
        
        finally:
            # Limpa logs antigos
            self._cleanup_old_logs()
    
    def _archive_file(self, file_path: Path, archive_path: Path) -> None:
        """Move arquivo para diretório de arquivo.
        
        Args:
            file_path: Arquivo para mover
            archive_path: Diretório de destino
        """
        try:
            # Cria diretório se não existe
            archive_path.mkdir(parents=True, exist_ok=True)
            
            # Gera nome único se arquivo já existe
            dest_path = archive_path / file_path.name
            counter = 1
            while dest_path.exists():
                stem = file_path.stem
                suffix = file_path.suffix
                dest_path = archive_path / f"{stem}_{counter}{suffix}"
                counter += 1
            
            # Move arquivo
            file_path.rename(dest_path)
            logger.debug(f"Arquivo movido: {file_path} -> {dest_path}")
            
        except Exception as e:
            logger.error(f"Erro ao mover arquivo {file_path}: {e}")
    
    def _cleanup_old_logs(self) -> None:
        """Remove logs antigos."""
        cutoff_date = datetime.now() - timedelta(days=self.config['cleanup_old_logs_days'])
        
        initial_count = len(self.execution_logs)
        self.execution_logs = [
            log for log in self.execution_logs
            if datetime.fromisoformat(log['start_time']) > cutoff_date
        ]
        
        removed_count = initial_count - len(self.execution_logs)
        if removed_count > 0:
            logger.debug(f"Removidos {removed_count} logs antigos")
    
    def run_job_now(self, job_name: str) -> None:
        """Executa um job imediatamente.
        
        Args:
            job_name: Nome do job
        """
        if job_name not in self.jobs:
            raise ValueError(f"Job não encontrado: {job_name}")
        
        self.job_queue.put(job_name)
        logger.info(f"Job {job_name} adicionado à fila para execução imediata")
    
    def get_job_status(self, job_name: str = None) -> Dict[str, Any]:
        """Retorna status dos jobs.
        
        Args:
            job_name: Nome do job específico (None para todos)
            
        Returns:
            Status dos jobs
        """
        if job_name:
            if job_name not in self.jobs:
                return {}
            return {job_name: self.jobs[job_name].stats}
        
        return {name: job.stats for name, job in self.jobs.items()}
    
    def get_execution_logs(self, job_name: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Retorna logs de execução.
        
        Args:
            job_name: Nome do job específico (None para todos)
            limit: Número máximo de logs a retornar
            
        Returns:
            Lista de logs de execução
        """
        logs = self.execution_logs
        
        if job_name:
            logs = [log for log in logs if log['job_name'] == job_name]
        
        # Retorna os mais recentes primeiro
        logs = sorted(logs, key=lambda x: x['start_time'], reverse=True)
        
        return logs[:limit]
    
    def create_equipment_ingestion_job(self, name: str, source_path: Path, 
                                     schedule_expression: str = None) -> IngestionJob:
        """Cria job de ingestão para equipamentos.
        
        Args:
            name: Nome do job
            source_path: Diretório fonte
            schedule_expression: Expressão de agendamento
            
        Returns:
            Job criado
        """
        job = IngestionJob(
            name=name,
            source_path=source_path,
            schedule_expression=schedule_expression,
            file_pattern="*equipment*"
        )
        
        self.add_job(job)
        return job
    
    def create_maintenance_ingestion_job(self, name: str, source_path: Path,
                                       schedule_expression: str = None) -> IngestionJob:
        """Cria job de ingestão para manutenções.
        
        Args:
            name: Nome do job
            source_path: Diretório fonte
            schedule_expression: Expressão de agendamento
            
        Returns:
            Job criado
        """
        job = IngestionJob(
            name=name,
            source_path=source_path,
            schedule_expression=schedule_expression,
            file_pattern="*maintenance*"
        )
        
        self.add_job(job)
        return job 