"""
Testes para limpeza automática de arquivos processados.

Este módulo testa a funcionalidade de limpeza automática de arquivos
antigos nos diretórios processed e failed do sistema de upload.
"""

import pytest
import tempfile
import time
import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any

from src.etl.upload_monitor import UploadMonitor, UploadStatus
from src.database.repositories import RepositoryManager


class TestUploadCleanup:
    """Testes para limpeza automática de arquivos."""
    
    @pytest.fixture
    def temp_upload_dir(self):
        """Diretório temporário para testes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def upload_monitor(self, temp_upload_dir):
        """Monitor de upload para testes."""
        monitor = UploadMonitor(temp_upload_dir)
        yield monitor
        # Cleanup
        if monitor.running:
            monitor.stop()
    
    @pytest.fixture
    def mock_repository_manager(self):
        """Mock do gerenciador de repositórios."""
        return Mock(spec=RepositoryManager)
    
    def test_cleanup_old_files_basic(self, upload_monitor):
        """Testa limpeza básica de arquivos antigos."""
        # Criar estrutura de diretórios
        processed_dir = upload_monitor.processed_dir
        failed_dir = upload_monitor.failed_dir
        processed_dir.mkdir(parents=True, exist_ok=True)
        failed_dir.mkdir(parents=True, exist_ok=True)
        
        # Criar arquivos antigos (48h atrás)
        old_time = time.time() - (48 * 3600)  # 48 horas atrás
        
        old_processed_file = processed_dir / "old_equipment.csv"
        old_processed_file.write_text("id,name\n1,Equipment A")
        old_processed_file.touch(times=(old_time, old_time))
        
        old_failed_file = failed_dir / "old_maintenance.csv"
        old_failed_file.write_text("invalid data")
        old_failed_file.touch(times=(old_time, old_time))
        
        # Criar arquivos recentes (2h atrás)
        recent_time = time.time() - (2 * 3600)  # 2 horas atrás
        
        recent_processed_file = processed_dir / "recent_equipment.csv"
        recent_processed_file.write_text("id,name\n2,Equipment B")
        recent_processed_file.touch(times=(recent_time, recent_time))
        
        recent_failed_file = failed_dir / "recent_maintenance.csv"
        recent_failed_file.write_text("recent invalid data")
        recent_failed_file.touch(times=(recent_time, recent_time))
        
        # Configurar limpeza para arquivos com mais de 24h
        upload_monitor.config['max_file_age_hours'] = 24
        
        # Executar limpeza
        upload_monitor._cleanup_old_files()
        
        # Verificar resultados
        assert not old_processed_file.exists(), "Arquivo antigo processado deveria ter sido removido"
        assert not old_failed_file.exists(), "Arquivo antigo falhado deveria ter sido removido"
        assert recent_processed_file.exists(), "Arquivo recente processado deveria permanecer"
        assert recent_failed_file.exists(), "Arquivo recente falhado deveria permanecer"
    
    def test_cleanup_with_subdirectories(self, upload_monitor):
        """Testa limpeza em subdiretórios organizados por data."""
        # Criar estrutura com subdiretórios por data
        processed_dir = upload_monitor.processed_dir
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Subdiretório antigo
        old_date_dir = processed_dir / "2024-01-01"
        old_date_dir.mkdir(parents=True, exist_ok=True)
        
        # Subdiretório recente
        recent_date = datetime.now().strftime("%Y-%m-%d")
        recent_date_dir = processed_dir / recent_date
        recent_date_dir.mkdir(parents=True, exist_ok=True)
        
        # Arquivos antigos
        old_time = time.time() - (48 * 3600)  # 48 horas atrás
        
        old_file = old_date_dir / "old_equipment.csv"
        old_file.write_text("id,name\n1,Old Equipment")
        old_file.touch(times=(old_time, old_time))
        
        old_metadata = old_date_dir / "old_equipment.csv.meta.json"
        old_metadata.write_text('{"upload_id": "old-id", "processed_at": "2024-01-01T10:00:00"}')
        old_metadata.touch(times=(old_time, old_time))
        
        # Arquivos recentes
        recent_time = time.time() - (2 * 3600)  # 2 horas atrás
        
        recent_file = recent_date_dir / "recent_equipment.csv"
        recent_file.write_text("id,name\n2,Recent Equipment")
        recent_file.touch(times=(recent_time, recent_time))
        
        recent_metadata = recent_date_dir / "recent_equipment.csv.meta.json"
        recent_metadata.write_text('{"upload_id": "recent-id", "processed_at": "' + datetime.now().isoformat() + '"}')
        recent_metadata.touch(times=(recent_time, recent_time))
        
        # Configurar limpeza
        upload_monitor.config['max_file_age_hours'] = 24
        
        # Executar limpeza
        upload_monitor._cleanup_old_files()
        
        # Verificar resultados
        assert not old_file.exists(), "Arquivo antigo deveria ter sido removido"
        assert not old_metadata.exists(), "Metadados antigos deveriam ter sido removidos"
        assert recent_file.exists(), "Arquivo recente deveria permanecer"
        assert recent_metadata.exists(), "Metadados recentes deveriam permanecer"
        
        # Verificar se diretório vazio foi removido
        assert not old_date_dir.exists(), "Diretório vazio deveria ter sido removido"
        assert recent_date_dir.exists(), "Diretório com arquivos deveria permanecer"
    
    def test_remove_empty_directories(self, upload_monitor):
        """Testa remoção de diretórios vazios."""
        processed_dir = upload_monitor.processed_dir
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Criar estrutura de diretórios
        empty_dir1 = processed_dir / "2024-01-01"
        empty_dir2 = processed_dir / "2024-01-02" 
        non_empty_dir = processed_dir / "2024-01-03"
        
        empty_dir1.mkdir(parents=True, exist_ok=True)
        empty_dir2.mkdir(parents=True, exist_ok=True)
        non_empty_dir.mkdir(parents=True, exist_ok=True)
        
        # Adicionar arquivo apenas no diretório não-vazio
        (non_empty_dir / "file.txt").write_text("content")
        
        # Executar remoção de diretórios vazios
        upload_monitor._remove_empty_directories(processed_dir)
        
        # Verificar resultados
        assert not empty_dir1.exists(), "Diretório vazio 1 deveria ter sido removido"
        assert not empty_dir2.exists(), "Diretório vazio 2 deveria ter sido removido"
        assert non_empty_dir.exists(), "Diretório com arquivos deveria permanecer"
        assert processed_dir.exists(), "Diretório base deveria permanecer"
    
    def test_cleanup_loop_integration(self, upload_monitor):
        """Testa integração do loop de limpeza."""
        # Mock da configuração para limpeza rápida
        upload_monitor.config['cleanup_interval_hours'] = 0.001  # ~3.6 segundos
        upload_monitor.config['max_file_age_hours'] = 0.001  # ~3.6 segundos
        
        # Criar arquivo que será considerado antigo
        processed_dir = upload_monitor.processed_dir
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        test_file = processed_dir / "test_cleanup.csv"
        test_file.write_text("id,name\n1,Test")
        
        # Iniciar monitor
        upload_monitor.start()
        
        # Aguardar tempo suficiente para limpeza
        time.sleep(5)  # 5 segundos
        
        # Parar monitor
        upload_monitor.stop()
        
        # Verificar se arquivo foi removido
        assert not test_file.exists(), "Arquivo deveria ter sido removido pela limpeza automática"
        
        # Verificar estatísticas
        stats = upload_monitor.get_statistics()
        assert 'last_cleanup' in stats, "Estatísticas deveriam incluir timestamp da última limpeza"
    
    def test_cleanup_with_metadata_files(self, upload_monitor):
        """Testa limpeza incluindo arquivos de metadados."""
        processed_dir = upload_monitor.processed_dir
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Criar arquivos antigos
        old_time = time.time() - (48 * 3600)  # 48 horas atrás
        
        # Arquivo de dados
        data_file = processed_dir / "equipment.csv"
        data_file.write_text("id,name\n1,Equipment")
        data_file.touch(times=(old_time, old_time))
        
        # Arquivo de metadados
        meta_file = processed_dir / "equipment.csv.meta.json"
        metadata = {
            "upload_id": "test-id",
            "original_filename": "equipment.csv",
            "processed_at": "2024-01-01T10:00:00",
            "records_processed": 1,
            "records_valid": 1,
            "records_invalid": 0
        }
        meta_file.write_text(json.dumps(metadata, indent=2))
        meta_file.touch(times=(old_time, old_time))
        
        # Configurar limpeza
        upload_monitor.config['max_file_age_hours'] = 24
        
        # Executar limpeza
        upload_monitor._cleanup_old_files()
        
        # Verificar se ambos os arquivos foram removidos
        assert not data_file.exists(), "Arquivo de dados deveria ter sido removido"
        assert not meta_file.exists(), "Arquivo de metadados deveria ter sido removido"
    
    def test_cleanup_error_handling(self, upload_monitor):
        """Testa tratamento de erros durante limpeza."""
        processed_dir = upload_monitor.processed_dir
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Criar arquivo que simula erro de remoção
        problem_file = processed_dir / "problem_file.csv"
        problem_file.write_text("content")
        
        # Mock para simular erro na remoção
        with patch.object(Path, 'unlink', side_effect=OSError("Permission denied")) as mock_unlink:
            # Executar limpeza (não deve falhar)
            upload_monitor._cleanup_old_files()
            
            # Verificar que tentou remover
            mock_unlink.assert_called()
        
        # Arquivo deve ainda existir devido ao erro
        assert problem_file.exists(), "Arquivo deveria ainda existir devido ao erro simulado"
    
    def test_get_processed_files(self, upload_monitor):
        """Testa obtenção de lista de arquivos processados."""
        processed_dir = upload_monitor.processed_dir
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Criar arquivos processados com metadados
        for i in range(3):
            # Arquivo de dados
            data_file = processed_dir / f"equipment_{i}.csv"
            data_file.write_text(f"id,name\n{i},Equipment {i}")
            
            # Arquivo de metadados
            meta_file = processed_dir / f"equipment_{i}.csv.meta.json"
            metadata = {
                "upload_id": f"test-id-{i}",
                "original_filename": f"equipment_{i}.csv",
                "processed_at": datetime.now().isoformat(),
                "records_processed": 1,
                "records_valid": 1,
                "records_invalid": 0,
                "file_size": len(data_file.read_text())
            }
            meta_file.write_text(json.dumps(metadata, indent=2))
        
        # Obter lista de arquivos processados
        processed_files = upload_monitor.get_processed_files(limit=10)
        
        # Verificar resultados
        assert len(processed_files) == 3, "Deveria retornar 3 arquivos processados"
        
        for file_info in processed_files:
            assert 'upload_id' in file_info, "Informações deveriam incluir upload_id"
            assert 'original_filename' in file_info, "Informações deveriam incluir nome original"
            assert 'processed_at' in file_info, "Informações deveriam incluir data de processamento"
            assert 'current_path' in file_info, "Informações deveriam incluir caminho atual"
            assert 'metadata_path' in file_info, "Informações deveriam incluir caminho dos metadados"
    
    def test_get_failed_files(self, upload_monitor):
        """Testa obtenção de lista de arquivos que falharam."""
        failed_dir = upload_monitor.failed_dir
        failed_dir.mkdir(parents=True, exist_ok=True)
        
        # Criar arquivos que falharam com metadados de erro
        for i in range(2):
            # Arquivo de dados
            data_file = failed_dir / f"invalid_{i}.csv"
            data_file.write_text("invalid,data,format")
            
            # Arquivo de erro
            error_file = failed_dir / f"invalid_{i}.csv.error.json"
            error_metadata = {
                "upload_id": f"failed-id-{i}",
                "original_filename": f"invalid_{i}.csv",
                "failed_at": datetime.now().isoformat(),
                "error_message": f"Invalid format in file {i}",
                "file_size": len(data_file.read_text())
            }
            error_file.write_text(json.dumps(error_metadata, indent=2))
        
        # Obter lista de arquivos que falharam
        failed_files = upload_monitor.get_failed_files(limit=10)
        
        # Verificar resultados
        assert len(failed_files) == 2, "Deveria retornar 2 arquivos que falharam"
        
        for file_info in failed_files:
            assert 'upload_id' in file_info, "Informações deveriam incluir upload_id"
            assert 'original_filename' in file_info, "Informações deveriam incluir nome original"
            assert 'failed_at' in file_info, "Informações deveriam incluir data da falha"
            assert 'error_message' in file_info, "Informações deveriam incluir mensagem de erro"
            assert 'current_path' in file_info, "Informações deveriam incluir caminho atual"
            assert 'error_metadata_path' in file_info, "Informações deveriam incluir caminho dos metadados de erro"
    
    def test_get_directory_structure(self, upload_monitor):
        """Testa obtenção da estrutura de diretórios."""
        # Criar estrutura de exemplo
        upload_dir = upload_monitor.upload_dir
        processed_dir = upload_monitor.processed_dir
        failed_dir = upload_monitor.failed_dir
        
        upload_dir.mkdir(parents=True, exist_ok=True)
        processed_dir.mkdir(parents=True, exist_ok=True)
        failed_dir.mkdir(parents=True, exist_ok=True)
        
        # Adicionar alguns arquivos
        (upload_dir / "pending.csv").write_text("pending data")
        (processed_dir / "success.csv").write_text("processed data")
        (failed_dir / "error.csv").write_text("failed data")
        
        # Criar subdiretório por data
        date_dir = processed_dir / "2024-01-01"
        date_dir.mkdir(parents=True, exist_ok=True)
        (date_dir / "archived.csv").write_text("archived data")
        
        # Obter estrutura
        structure = upload_monitor.get_directory_structure()
        
        # Verificar estrutura
        assert 'upload_dir' in structure
        assert 'processed_dir' in structure
        assert 'failed_dir' in structure
        assert 'directories' in structure
        
        directories = structure['directories']
        
        # Verificar contadores
        assert directories['upload']['total_files'] == 1
        assert directories['processed']['total_files'] == 2  # success.csv + archived.csv
        assert directories['failed']['total_files'] == 1
        
        # Verificar subdiretórios
        processed_subdirs = directories['processed']['subdirectories']
        assert len(processed_subdirs) == 1
        assert processed_subdirs[0]['name'] == '2024-01-01'
        assert processed_subdirs[0]['files_count'] == 1


@pytest.mark.integration
class TestUploadCleanupIntegration:
    """Testes de integração para limpeza automática."""
    
    @pytest.fixture
    def temp_upload_dir(self):
        """Diretório temporário para testes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def test_full_cleanup_workflow(self, temp_upload_dir):
        """Testa fluxo completo de processamento e limpeza."""
        # Criar monitor
        monitor = UploadMonitor(temp_upload_dir)
        
        # Configurar para limpeza rápida
        monitor.config['max_file_age_hours'] = 0.001  # ~3.6 segundos
        monitor.config['cleanup_interval_hours'] = 0.001
        
        try:
            # Simular processamento de arquivo
            upload_status = UploadStatus(temp_upload_dir / "test.csv")
            upload_status.records_processed = 10
            upload_status.records_valid = 8
            upload_status.records_invalid = 2
            upload_status.file_format = "CSV"
            upload_status.data_type = "EQUIPMENT_DATA"
            
            # Criar arquivo de teste
            test_file = temp_upload_dir / "test.csv"
            test_file.write_text("id,name\n1,Test Equipment")
            upload_status.file_path = test_file
            
            # Simular movimentação para processed
            monitor._move_to_processed(upload_status)
            
            # Verificar que arquivo foi movido
            assert not test_file.exists(), "Arquivo original deveria ter sido movido"
            
            # Encontrar arquivo processado
            processed_files = list(monitor.processed_dir.rglob("*.csv"))
            assert len(processed_files) == 1, "Deveria haver 1 arquivo processado"
            
            processed_file = processed_files[0]
            metadata_file = processed_file.with_suffix(processed_file.suffix + '.meta.json')
            
            assert processed_file.exists(), "Arquivo processado deveria existir"
            assert metadata_file.exists(), "Arquivo de metadados deveria existir"
            
            # Aguardar tempo para arquivo ficar "antigo"
            time.sleep(4)
            
            # Executar limpeza manual
            monitor._cleanup_old_files()
            
            # Verificar que arquivos foram removidos
            assert not processed_file.exists(), "Arquivo processado deveria ter sido removido"
            assert not metadata_file.exists(), "Metadados deveriam ter sido removidos"
            
        finally:
            if monitor.running:
                monitor.stop()
    
    def test_cleanup_preserves_recent_files(self, temp_upload_dir):
        """Testa que limpeza preserva arquivos recentes."""
        monitor = UploadMonitor(temp_upload_dir)
        
        # Configurar limpeza para arquivos com mais de 1 hora
        monitor.config['max_file_age_hours'] = 1
        
        try:
            # Criar arquivo recente
            processed_dir = monitor.processed_dir
            processed_dir.mkdir(parents=True, exist_ok=True)
            
            recent_file = processed_dir / "recent.csv"
            recent_file.write_text("id,name\n1,Recent Equipment")
            
            # Executar limpeza
            monitor._cleanup_old_files()
            
            # Arquivo recente deve permanecer
            assert recent_file.exists(), "Arquivo recente deveria permanecer"
            
        finally:
            if monitor.running:
                monitor.stop()


if __name__ == "__main__":
    # Executar testes de limpeza
    pytest.main([__file__, "-v", "--tb=short"])