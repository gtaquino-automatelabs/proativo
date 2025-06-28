"""
Testes unitários para endpoints de upload de arquivos.

Este módulo testa todas as funcionalidades dos endpoints de upload,
incluindo validações, processamento e tratamento de erros.
"""

import io
import pytest
from unittest.mock import Mock, patch, mock_open, AsyncMock
from pathlib import Path
from uuid import uuid4, UUID
from datetime import datetime

from fastapi import HTTPException, UploadFile, status
from fastapi.testclient import TestClient

from src.api.endpoints.upload import (
    router,
    detect_file_type_from_name,
    validate_file_extension,
    generate_unique_filename,
    upload_file,
    get_upload_status,
    get_upload_history,
    get_upload_metrics
)
from src.api.models.upload import (
    FileType,
    UploadStatus,
    UploadResponse,
    UploadStatusResponse,
    UploadHistoryResponse
)
from src.api.config import Settings
from src.etl.data_processor import DataProcessor, FileFormat, DataType


class TestUploadHelperFunctions:
    """Testes para funções auxiliares do upload."""
    
    def test_detect_file_type_from_name_equipment(self):
        """Testa detecção de tipo de arquivo para equipamentos."""
        test_cases = [
            "equipamentos.csv",
            "equipment_data.xlsx",
            "assets_list.xml",
            "EQUIPMENT.CSV",
            "plant_assets.csv"
        ]
        
        for filename in test_cases:
            result = detect_file_type_from_name(filename)
            assert result == FileType.EQUIPMENT, f"Failed for {filename}"
    
    def test_detect_file_type_from_name_maintenance(self):
        """Testa detecção de tipo de arquivo para manutenções."""
        test_cases = [
            "manutencao.csv",
            "maintenance_records.xlsx",
            "servicos.xml",
            "MAINTENANCE.CSV",
            "maint_orders.csv"
        ]
        
        for filename in test_cases:
            result = detect_file_type_from_name(filename)
            assert result == FileType.MAINTENANCE, f"Failed for {filename}"
    
    def test_detect_file_type_from_name_unknown(self):
        """Testa detecção de tipo desconhecido."""
        test_cases = [
            "dados.csv",
            "report.xlsx",
            "unknown_file.xml",
            "generic_data.csv"
        ]
        
        for filename in test_cases:
            result = detect_file_type_from_name(filename)
            assert result == FileType.UNKNOWN, f"Failed for {filename}"
    
    def test_validate_file_extension_valid(self):
        """Testa validação de extensões válidas."""
        allowed = [".csv", ".xlsx", ".xml"]
        
        valid_files = [
            "test.csv",
            "data.xlsx",
            "config.xml",
            "TEST.CSV",
            "DATA.XLSX"
        ]
        
        for filename in valid_files:
            result = validate_file_extension(filename, allowed)
            assert result is True, f"Failed for {filename}"
    
    def test_validate_file_extension_invalid(self):
        """Testa validação de extensões inválidas."""
        allowed = [".csv", ".xlsx", ".xml"]
        
        invalid_files = [
            "test.txt",
            "data.pdf",
            "config.json",
            "file.doc",
            "image.png"
        ]
        
        for filename in invalid_files:
            result = validate_file_extension(filename, allowed)
            assert result is False, f"Failed for {filename}"
    
    def test_generate_unique_filename(self, tmp_path):
        """Testa geração de nomes únicos para arquivos."""
        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir()
        
        # Teste com arquivo que não existe
        unique_name = generate_unique_filename("test.csv", upload_dir)
        assert unique_name.startswith("test_")
        assert unique_name.endswith(".csv")
        assert len(unique_name) > len("test.csv")
        
        # Teste com arquivo que já existe
        existing_file = upload_dir / "existing.csv"
        existing_file.touch()
        
        unique_name = generate_unique_filename("existing.csv", upload_dir)
        assert unique_name != "existing.csv"
        assert unique_name.startswith("existing_")
        assert unique_name.endswith(".csv")


class TestUploadEndpoint:
    """Testes para endpoint de upload de arquivos."""
    
    @pytest.fixture
    def mock_settings(self):
        """Settings mock para testes."""
        settings = Mock(spec=Settings)
        settings.upload_allowed_extensions = [".csv", ".xlsx", ".xml"]
        settings.upload_max_size = 50 * 1024 * 1024  # 50MB
        settings.upload_directory = "data/uploads"
        return settings
    
    @pytest.fixture
    def mock_upload_file(self):
        """Mock de UploadFile para testes."""
        file_content = b"id,name,type\n1,Equipment A,Motor\n2,Equipment B,Pump"
        
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "equipment.csv"
        mock_file.read = AsyncMock(return_value=file_content)
        
        return mock_file
    
    @pytest.fixture
    def mock_data_processor(self):
        """Mock do DataProcessor para testes."""
        processor = Mock(spec=DataProcessor)
        processor.detect_file_format.return_value = FileFormat.CSV
        processor.detect_data_type.return_value = DataType.EQUIPMENT_DATA
        return processor
    
    @pytest.mark.asyncio
    async def test_upload_file_success(self, mock_settings, mock_upload_file, mock_data_processor):
        """Testa upload de arquivo com sucesso."""
        
        with patch("src.api.endpoints.upload.Path") as mock_path, \
             patch("src.api.endpoints.upload.open", mock_open()) as mock_file, \
             patch("src.api.endpoints.upload.DataProcessor", return_value=mock_data_processor), \
             patch("src.api.endpoints.upload.uuid4", return_value=UUID("12345678-1234-5678-9012-123456789012")):
            
            # Configurar mocks
            mock_upload_dir = Mock()
            mock_upload_dir.mkdir = Mock()
            mock_upload_dir.__truediv__ = Mock(return_value=Path("data/uploads/equipment_20240115_12345678.csv"))
            mock_path.return_value = mock_upload_dir
            
            # Executar upload
            result = await upload_file(
                file=mock_upload_file,
                file_type=FileType.EQUIPMENT,
                description="Test upload",
                overwrite_existing=False,
                settings=mock_settings,
                _=None
            )
            
            # Verificar resultado
            assert isinstance(result, UploadResponse)
            assert result.filename == "equipment.csv"
            assert result.file_size > 0
            assert result.file_type == FileType.EQUIPMENT
            assert result.status == UploadStatus.UPLOADED
            assert "sucesso" in result.message.lower()
            
            # Verificar que arquivo foi salvo
            mock_file.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_upload_file_empty_filename(self, mock_settings):
        """Testa erro com nome de arquivo vazio."""
        
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = ""
        
        with pytest.raises(HTTPException) as exc_info:
            await upload_file(
                file=mock_file,
                file_type=None,
                description=None,
                overwrite_existing=False,
                settings=mock_settings,
                _=None
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "vazio" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_upload_file_invalid_extension(self, mock_settings):
        """Testa erro com extensão inválida."""
        
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.txt"
        
        with pytest.raises(HTTPException) as exc_info:
            await upload_file(
                file=mock_file,
                file_type=None,
                description=None,
                overwrite_existing=False,
                settings=mock_settings,
                _=None
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Extensão" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_upload_file_too_large(self, mock_settings):
        """Testa erro com arquivo muito grande."""
        
        # Arquivo muito grande (100MB)
        large_content = b"x" * (100 * 1024 * 1024)
        
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "large.csv"
        mock_file.read = AsyncMock(return_value=large_content)
        
        with pytest.raises(HTTPException) as exc_info:
            await upload_file(
                file=mock_file,
                file_type=None,
                description=None,
                overwrite_existing=False,
                settings=mock_settings,
                _=None
            )
        
        assert exc_info.value.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        assert "muito grande" in str(exc_info.value.detail).lower()
    
    @pytest.mark.asyncio
    async def test_upload_file_auto_detect_type(self, mock_settings, mock_data_processor):
        """Testa auto-detecção de tipo de arquivo."""
        
        file_content = b"order_id,equipment_id,date\n1,EQ001,2024-01-15"
        
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "maintenance_orders.csv"
        mock_file.read = AsyncMock(return_value=file_content)
        
        with patch("src.api.endpoints.upload.Path") as mock_path, \
             patch("src.api.endpoints.upload.open", mock_open()), \
             patch("src.api.endpoints.upload.DataProcessor", return_value=mock_data_processor), \
             patch("src.api.endpoints.upload.uuid4"):
            
            # Configurar mocks
            mock_upload_dir = Mock()
            mock_upload_dir.mkdir = Mock()
            mock_upload_dir.__truediv__ = Mock(return_value=Path("data/uploads/file.csv"))
            mock_path.return_value = mock_upload_dir
            
            # Executar upload sem especificar tipo
            result = await upload_file(
                file=mock_file,
                file_type=None,  # Não especifica tipo
                description=None,
                overwrite_existing=False,
                settings=mock_settings,
                _=None
            )
            
            # Verificar que tipo foi auto-detectado
            assert result.file_type == FileType.MAINTENANCE


class TestUploadStatusEndpoint:
    """Testes para endpoint de consulta de status."""
    
    @pytest.fixture
    def mock_settings(self):
        """Settings mock para testes."""
        settings = Mock(spec=Settings)
        return settings
    
    @pytest.mark.asyncio
    async def test_get_upload_status_success(self, mock_settings):
        """Testa consulta de status com sucesso."""
        
        upload_id = str(uuid4())
        
        with patch("src.api.endpoints.upload.get_database_connection") as mock_db, \
             patch("src.api.endpoints.upload.UploadStatusRepository") as mock_repo:
            
            # Configurar mock do repositório
            mock_repo_instance = Mock()
            mock_repo.return_value = mock_repo_instance
            
            # Mock de dados de status
            mock_status_data = {
                'upload_id': upload_id,
                'filename': 'test.csv',
                'status': 'completed',
                'progress_percentage': 100,
                'records_processed': 150,
                'records_valid': 145,
                'records_invalid': 5,
                'error_message': None,
                'started_at': datetime(2024, 1, 15, 10, 30),
                'completed_at': datetime(2024, 1, 15, 10, 32),
                'processing_time_seconds': 120.5
            }
            
            mock_repo_instance.get_by_upload_id.return_value = mock_status_data
            
            # Executar consulta
            result = await get_upload_status(upload_id, mock_settings)
            
            # Verificar resultado
            assert isinstance(result, UploadStatusResponse)
            assert str(result.upload_id) == upload_id
            assert result.filename == 'test.csv'
            assert result.status == UploadStatus.COMPLETED
            assert result.progress_percentage == 100
            assert result.records_processed == 150
    
    @pytest.mark.asyncio
    async def test_get_upload_status_not_found(self, mock_settings):
        """Testa erro quando upload não é encontrado."""
        
        upload_id = str(uuid4())
        
        with patch("src.api.endpoints.upload.get_database_connection") as mock_db, \
             patch("src.api.endpoints.upload.UploadStatusRepository") as mock_repo:
            
            # Configurar mock do repositório
            mock_repo_instance = Mock()
            mock_repo.return_value = mock_repo_instance
            mock_repo_instance.get_by_upload_id.return_value = None
            
            # Executar e verificar exceção
            with pytest.raises(HTTPException) as exc_info:
                await get_upload_status(upload_id, mock_settings)
            
            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
            assert "não encontrado" in str(exc_info.value.detail).lower()


class TestUploadHistoryEndpoint:
    """Testes para endpoint de histórico de uploads."""
    
    @pytest.fixture
    def mock_settings(self):
        """Settings mock para testes."""
        settings = Mock(spec=Settings)
        return settings
    
    @pytest.mark.asyncio
    async def test_get_upload_history_success(self, mock_settings):
        """Testa consulta de histórico com sucesso."""
        
        with patch("src.api.endpoints.upload.get_database_connection") as mock_db, \
             patch("src.api.endpoints.upload.UploadStatusRepository") as mock_repo:
            
            # Configurar mock do repositório
            mock_repo_instance = Mock()
            mock_repo.return_value = mock_repo_instance
            
            # Mock de dados de histórico
            mock_history_data = [
                {
                    'upload_id': str(uuid4()),
                    'filename': 'test1.csv',
                    'status': 'completed',
                    'progress_percentage': 100,
                    'records_processed': 100,
                    'records_valid': 95,
                    'records_invalid': 5,
                    'completed_at': datetime(2024, 1, 15, 10, 30)
                },
                {
                    'upload_id': str(uuid4()),
                    'filename': 'test2.csv',
                    'status': 'processing',
                    'progress_percentage': 50,
                    'records_processed': 50,
                    'records_valid': 48,
                    'records_invalid': 2,
                    'completed_at': None
                }
            ]
            
            mock_repo_instance.get_recent_uploads.return_value = mock_history_data
            mock_repo_instance.count_uploads.return_value = 2
            
            # Executar consulta
            result = await get_upload_history(
                limit=10,
                status_filter=None,
                settings=mock_settings
            )
            
            # Verificar resultado
            assert isinstance(result, UploadHistoryResponse)
            assert len(result.uploads) == 2
            assert result.total_count == 2
            assert result.uploads[0].filename == 'test1.csv'
            assert result.uploads[1].filename == 'test2.csv'
    
    @pytest.mark.asyncio
    async def test_get_upload_history_with_filter(self, mock_settings):
        """Testa consulta de histórico com filtro de status."""
        
        with patch("src.api.endpoints.upload.get_database_connection") as mock_db, \
             patch("src.api.endpoints.upload.UploadStatusRepository") as mock_repo:
            
            # Configurar mock do repositório
            mock_repo_instance = Mock()
            mock_repo.return_value = mock_repo_instance
            
            # Mock de dados filtrados
            mock_history_data = [
                {
                    'upload_id': str(uuid4()),
                    'filename': 'completed.csv',
                    'status': 'completed',
                    'progress_percentage': 100,
                    'records_processed': 100,
                    'records_valid': 100,
                    'records_invalid': 0,
                    'completed_at': datetime(2024, 1, 15, 10, 30)
                }
            ]
            
            mock_repo_instance.get_recent_uploads.return_value = mock_history_data
            mock_repo_instance.count_uploads.return_value = 1
            
            # Executar consulta com filtro
            result = await get_upload_history(
                limit=10,
                status_filter="completed",
                settings=mock_settings
            )
            
            # Verificar que filtro foi aplicado
            mock_repo_instance.get_recent_uploads.assert_called_once_with(10, "completed")
            mock_repo_instance.count_uploads.assert_called_once_with("completed")
            
            assert len(result.uploads) == 1
            assert result.uploads[0].status == UploadStatus.COMPLETED


class TestUploadMetricsEndpoint:
    """Testes para endpoint de métricas de upload."""
    
    @pytest.fixture
    def mock_settings(self):
        """Settings mock para testes."""
        settings = Mock(spec=Settings)
        return settings
    
    @pytest.mark.asyncio
    async def test_get_upload_metrics_success(self, mock_settings):
        """Testa consulta de métricas com sucesso."""
        
        with patch("src.api.endpoints.upload.get_database_connection") as mock_db, \
             patch("src.api.endpoints.upload.UploadStatusRepository") as mock_repo:
            
            # Configurar mock do repositório
            mock_repo_instance = Mock()
            mock_repo.return_value = mock_repo_instance
            
            # Mock de métricas
            mock_repo_instance.get_metrics_summary.return_value = {
                'total_uploads': 100,
                'successful_uploads': 85,
                'failed_uploads': 10,
                'processing_uploads': 5,
                'total_records_processed': 10000,
                'average_processing_time': 45.5,
                'success_rate': 85.0
            }
            
            # Executar consulta
            result = await get_upload_metrics(mock_settings)
            
            # Verificar resultado
            assert isinstance(result, dict)
            assert result['total_uploads'] == 100
            assert result['successful_uploads'] == 85
            assert result['failed_uploads'] == 10
            assert result['processing_uploads'] == 5
            assert result['success_rate'] == 85.0
            assert result['total_records_processed'] == 10000
            assert result['average_processing_time'] == 45.5


class TestUploadIntegration:
    """Testes de integração para fluxo completo de upload."""
    
    @pytest.mark.asyncio
    async def test_upload_workflow_integration(self):
        """Testa integração completa do fluxo de upload."""
        
        # Este teste seria mais complexo e testaria a integração
        # entre todos os componentes do sistema de upload
        
        # Por ora, deixamos como placeholder para implementação futura
        # quando tivermos um ambiente de teste integrado completo
        pass 