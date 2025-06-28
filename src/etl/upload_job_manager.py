"""
Gerenciador de Jobs de Upload.

Integra o UploadMonitor com o sistema de jobs do DataIngestionOrchestrator
para processamento automático e agendado de arquivos de upload.
"""

import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from .upload_monitor import UploadMonitor
from .data_ingestion import DataIngestionOrchestrator, IngestionJob

try:
    from ..database.repositories import RepositoryManager
except ImportError:
    RepositoryManager = None

logger = logging.getLogger(__name__)


class UploadJobManager:
    """Gerenciador de jobs de upload."""
    
    def __init__(self, repository_manager=None):
        """Inicializa o gerenciador de jobs de upload."""
        self.repository_manager = repository_manager
        
        # Configurações a partir de variáveis de ambiente
        self.upload_dir = Path(os.getenv('UPLOAD_DIRECTORY', 'data/uploads'))
        self.job_schedule = os.getenv('UPLOAD_JOB_SCHEDULE', '*/5')  # A cada 5 minutos
        
        # Componentes principais
        self.upload_monitor = None
        self.ingestion_orchestrator = None
        self.upload_job = None
        
        # Estado
        self.running = False
    
    def initialize(self) -> None:
        """Inicializa os componentes."""
        logger.info("Inicializando gerenciador de jobs de upload")
        
        # Inicializa monitor de upload
        self.upload_monitor = UploadMonitor(
            upload_dir=self.upload_dir,
            repository_manager=self.repository_manager
        )
        
        # Inicializa orquestrador de ingestão
        self.ingestion_orchestrator = DataIngestionOrchestrator(
            repository_manager=self.repository_manager
        )
        
        # Cria job de upload
        self.upload_job = self._create_upload_job()
        
        logger.info(f"Gerenciador inicializado para diretório: {self.upload_dir}")
    
    def _create_upload_job(self) -> IngestionJob:
        """Cria job de ingestão para uploads."""
        processed_dir = self.upload_dir / "processed"
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        job = IngestionJob(
            name="upload_processor",
            source_path=self.upload_dir,
            schedule_expression=self.job_schedule,
            auto_detect=True,
            file_pattern="*",
            move_processed=True,
            archive_path=processed_dir
        )
        
        self.ingestion_orchestrator.add_job(job)
        logger.info(f"Job de upload criado com agendamento: {self.job_schedule}")
        
        return job
    
    def start(self, use_monitor: bool = True, use_scheduler: bool = True) -> None:
        """Inicia o gerenciador."""
        if self.running:
            logger.warning("Gerenciador já está em execução")
            return
        
        if not self.upload_monitor or not self.ingestion_orchestrator:
            self.initialize()
        
        self.running = True
        logger.info("Iniciando gerenciador de jobs de upload")
        
        # Inicia monitor em tempo real (opcional)
        if use_monitor:
            self.upload_monitor.start()
            logger.info("Monitor de upload em tempo real iniciado")
        
        # Inicia agendador de jobs (opcional)
        if use_scheduler:
            self.ingestion_orchestrator.start()
            logger.info("Agendador de jobs iniciado")
        
        logger.info("Gerenciador de jobs de upload iniciado com sucesso")
    
    def stop(self) -> None:
        """Para o gerenciador."""
        if not self.running:
            return
        
        logger.info("Parando gerenciador de jobs de upload")
        self.running = False
        
        # Para componentes
        if self.upload_monitor:
            self.upload_monitor.stop()
        
        if self.ingestion_orchestrator:
            self.ingestion_orchestrator.stop()
        
        logger.info("Gerenciador parado")
    
    def run_upload_job_now(self) -> None:
        """Executa o job de upload imediatamente."""
        if not self.ingestion_orchestrator or not self.upload_job:
            raise RuntimeError("Gerenciador não foi inicializado")
        
        self.ingestion_orchestrator.run_job_now("upload_processor")
        logger.info("Job de upload executado manualmente")
    
    def get_upload_statistics(self) -> Dict[str, Any]:
        """Obtém estatísticas completas de upload."""
        stats = {
            'running': self.running,
            'upload_dir': str(self.upload_dir),
            'job_schedule': self.job_schedule,
            'monitor_stats': None,
            'job_stats': None,
            'recent_uploads': []
        }
        
        # Estatísticas do monitor
        if self.upload_monitor:
            stats['monitor_stats'] = self.upload_monitor.get_statistics()
            stats['recent_uploads'] = [
                {
                    'upload_id': upload.upload_id,
                    'file_path': str(upload.file_path),
                    'status': upload.status,
                    'created_at': upload.created_at.isoformat(),
                    'records_processed': upload.records_processed,
                    'records_valid': upload.records_valid,
                    'file_size': upload.file_size
                }
                for upload in self.upload_monitor.get_all_uploads()[-10:]  # Últimos 10
            ]
        
        # Estatísticas do job
        if self.ingestion_orchestrator:
            job_status = self.ingestion_orchestrator.get_job_status("upload_processor")
            stats['job_stats'] = job_status.get("upload_processor", {})
        
        return stats
    
    def get_recent_job_logs(self, limit: int = 20) -> list:
        """Obtém logs recentes do job de upload."""
        if not self.ingestion_orchestrator:
            return []
        
        return self.ingestion_orchestrator.get_execution_logs(
            job_name="upload_processor",
            limit=limit
        )
    
    def force_process_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Força o processamento de um arquivo específico."""
        if not self.upload_monitor:
            raise RuntimeError("Monitor não foi inicializado")
        
        upload_status = self.upload_monitor.force_process_file(file_path)
        
        if upload_status:
            return {
                'upload_id': upload_status.upload_id,
                'status': upload_status.status,
                'records_processed': upload_status.records_processed,
                'records_valid': upload_status.records_valid,
                'error_message': upload_status.error_message
            }
        
        return None


def create_upload_job_manager(repository_manager=None, auto_start: bool = False) -> UploadJobManager:
    """Cria e opcionalmente inicia o gerenciador de jobs de upload."""
    manager = UploadJobManager(repository_manager)
    manager.initialize()
    
    if auto_start:
        manager.start()
    
    return manager 