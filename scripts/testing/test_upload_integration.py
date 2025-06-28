"""
Script de teste para integração completa do sistema de upload.

Demonstra como usar o UploadJobManager, UploadMonitor e DataProcessor
para processar arquivos de upload de forma integrada.
"""

import asyncio
import logging
import time
from pathlib import Path
import sys
import os
import shutil

# Adiciona o diretório src ao path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from etl.upload_job_manager import create_upload_job_manager
from etl.upload_monitor import UploadMonitor
from etl.data_processor import DataProcessor, FileFormat, DataType
from database.repositories import RepositoryManager
from database.connection import DatabaseConnection

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_test_environment():
    """Configura ambiente de teste."""
    # Diretórios de teste
    test_upload_dir = Path("data/test_uploads")
    test_samples_dir = Path("data/samples")
    
    # Cria diretório de teste
    test_upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Copia alguns arquivos de exemplo para teste
    if test_samples_dir.exists():
        sample_files = list(test_samples_dir.glob("*.csv"))[:2]  # Pega 2 arquivos CSV
        
        for sample_file in sample_files:
            dest_file = test_upload_dir / f"test_{sample_file.name}"
            if not dest_file.exists():
                shutil.copy2(sample_file, dest_file)
                logger.info(f"Arquivo de teste copiado: {dest_file}")
    
    return test_upload_dir


def test_data_processor_standalone():
    """Testa DataProcessor standalone."""
    logger.info("=== Teste DataProcessor Standalone ===")
    
    processor = DataProcessor()
    test_dir = Path("data/samples")
    
    if not test_dir.exists():
        logger.warning("Diretório de samples não encontrado")
        return
    
    # Testa com arquivo CSV
    csv_files = list(test_dir.glob("*.csv"))
    if csv_files:
        test_file = csv_files[0]
        logger.info(f"Testando arquivo: {test_file}")
        
        try:
            # Detecta formato
            file_format = processor.detect_file_format(test_file)
            logger.info(f"Formato detectado: {file_format.value}")
            
            # Detecta tipo de dados
            data_type = processor.detect_data_type(test_file, file_format)
            logger.info(f"Tipo de dados detectado: {data_type.value}")
            
            # Processa arquivo
            valid_records, validation_errors = processor.process_file(test_file)
            logger.info(f"Processamento: {len(valid_records)} válidos, {len(validation_errors)} inválidos")
            
            # Mostra algumas estatísticas
            stats = processor.get_processing_statistics()
            logger.info(f"Estatísticas: {stats}")
            
        except Exception as e:
            logger.error(f"Erro no teste: {e}")


def test_upload_monitor():
    """Testa UploadMonitor."""
    logger.info("=== Teste UploadMonitor ===")
    
    test_upload_dir = setup_test_environment()
    
    # Cria monitor
    monitor = UploadMonitor(test_upload_dir)
    
    try:
        # Inicia monitor
        monitor.start()
        logger.info("Monitor iniciado")
        
        # Aguarda um pouco para processamento
        time.sleep(5)
        
        # Verifica estatísticas
        stats = monitor.get_statistics()
        logger.info(f"Estatísticas do monitor: {stats}")
        
        # Lista uploads
        uploads = monitor.get_all_uploads()
        logger.info(f"Total de uploads: {len(uploads)}")
        
        for upload in uploads:
            logger.info(f"Upload {upload.upload_id}: {upload.status} - {upload.records_valid} registros válidos")
        
    finally:
        # Para monitor
        monitor.stop()
        logger.info("Monitor parado")


def test_upload_job_manager():
    """Testa UploadJobManager."""
    logger.info("=== Teste UploadJobManager ===")
    
    test_upload_dir = setup_test_environment()
    
    # Cria gerenciador (sem auto-start)
    manager = create_upload_job_manager(auto_start=False)
    
    try:
        # Inicia apenas o monitor (não o scheduler para teste)
        manager.start(use_monitor=True, use_scheduler=False)
        logger.info("Gerenciador iniciado")
        
        # Aguarda processamento
        time.sleep(5)
        
        # Executa job manualmente
        manager.run_upload_job_now()
        logger.info("Job executado manualmente")
        
        # Aguarda mais um pouco
        time.sleep(3)
        
        # Verifica estatísticas
        stats = manager.get_upload_statistics()
        logger.info(f"Estatísticas completas: {stats}")
        
        # Verifica logs do job
        job_logs = manager.get_recent_job_logs(limit=5)
        logger.info(f"Logs recentes do job: {len(job_logs)} entradas")
        
        for log in job_logs:
            logger.info(f"Log: {log.get('job_name')} - {log.get('success')} - {log.get('files_processed')} arquivos")
        
    finally:
        # Para gerenciador
        manager.stop()
        logger.info("Gerenciador parado")


def test_force_process_file():
    """Testa processamento forçado de arquivo."""
    logger.info("=== Teste Processamento Forçado ===")
    
    test_upload_dir = setup_test_environment()
    
    # Cria monitor
    monitor = UploadMonitor(test_upload_dir)
    
    # Lista arquivos disponíveis
    test_files = list(test_upload_dir.glob("*.csv"))
    
    if not test_files:
        logger.warning("Nenhum arquivo de teste encontrado")
        return
    
    test_file = test_files[0]
    logger.info(f"Processando arquivo forçadamente: {test_file}")
    
    try:
        # Processa arquivo específico
        upload_status = monitor.force_process_file(test_file)
        
        if upload_status:
            logger.info(f"Processamento concluído:")
            logger.info(f"  Status: {upload_status.status}")
            logger.info(f"  Registros processados: {upload_status.records_processed}")
            logger.info(f"  Registros válidos: {upload_status.records_valid}")
            logger.info(f"  Registros inválidos: {upload_status.records_invalid}")
            if upload_status.error_message:
                logger.error(f"  Erro: {upload_status.error_message}")
        else:
            logger.warning("Arquivo não pôde ser processado")
            
    except Exception as e:
        logger.error(f"Erro no processamento forçado: {e}")


async def test_with_database():
    """Testa integração com banco de dados."""
    logger.info("=== Teste com Banco de Dados ===")
    
    try:
        # Tenta conectar ao banco
        db_connection = DatabaseConnection()
        await db_connection.connect()
        
        # Cria repository manager
        repo_manager = RepositoryManager(db_connection)
        
        # Cria gerenciador com repository
        manager = create_upload_job_manager(
            repository_manager=repo_manager,
            auto_start=False
        )
        
        test_upload_dir = setup_test_environment()
        
        # Inicia apenas monitor
        manager.start(use_monitor=True, use_scheduler=False)
        logger.info("Gerenciador com banco iniciado")
        
        # Aguarda processamento
        time.sleep(5)
        
        # Verifica estatísticas
        stats = manager.get_upload_statistics()
        logger.info(f"Estatísticas com banco: {stats}")
        
        # Para gerenciador
        manager.stop()
        
        # Fecha conexão
        await db_connection.disconnect()
        logger.info("Teste com banco concluído")
        
    except Exception as e:
        logger.error(f"Erro no teste com banco: {e}")
        logger.info("Teste com banco ignorado (banco pode não estar disponível)")


def cleanup_test_environment():
    """Limpa ambiente de teste."""
    test_dirs = [
        Path("data/test_uploads"),
    ]
    
    for test_dir in test_dirs:
        if test_dir.exists():
            shutil.rmtree(test_dir)
            logger.info(f"Diretório de teste removido: {test_dir}")


def main():
    """Função principal de teste."""
    logger.info("Iniciando testes de integração do sistema de upload")
    
    try:
        # Testa componentes individuais
        test_data_processor_standalone()
        print("\n" + "="*50 + "\n")
        
        test_upload_monitor()
        print("\n" + "="*50 + "\n")
        
        test_upload_job_manager()
        print("\n" + "="*50 + "\n")
        
        test_force_process_file()
        print("\n" + "="*50 + "\n")
        
        # Testa com banco (se disponível)
        asyncio.run(test_with_database())
        
        logger.info("Todos os testes concluídos com sucesso!")
        
    except KeyboardInterrupt:
        logger.info("Testes interrompidos pelo usuário")
    except Exception as e:
        logger.error(f"Erro nos testes: {e}")
    finally:
        cleanup_test_environment()


if __name__ == "__main__":
    main() 