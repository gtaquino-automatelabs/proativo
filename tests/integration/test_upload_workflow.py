"""
Testes de integração completos para o fluxo de upload de arquivos.

Este módulo testa todo o fluxo integrado:
- Upload via API endpoint
- Processamento ETL dos dados
- Armazenamento no banco de dados
- Monitoramento de status
- Sistema de notificações
- Validação de integridade dos dados
"""

import pytest
import asyncio
import tempfile
import os
import io
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import pandas as pd

from fastapi.testclient import TestClient
from fastapi import UploadFile

from src.api.main import app
from src.api.models.upload import FileType, UploadStatus
from src.etl.data_processor import DataProcessor, FileFormat, DataType
from src.etl.upload_monitor import UploadMonitor
from src.etl.upload_job_manager import create_upload_job_manager
from src.database.connection import get_database_connection
from src.database.repositories import EquipmentRepository, MaintenanceRepository, UploadStatusRepository
from src.database.models import UploadStatus as UploadStatusModel


class TestDataGenerator:
    """Gerador de dados de teste para upload."""
    
    @staticmethod
    def create_equipment_csv() -> str:
        """Cria conteúdo CSV de equipamentos para teste."""
        return """id,nome,tipo,localizacao,status,potencia_mva,tensao_primaria,tensao_secundaria,fabricante,ano_fabricacao
EQ001,Motor Bomba 1,Motor,Setor A,Operacional,15.5,13800,380,WEG,2020
EQ002,Compressor Principal,Compressor,Setor B,Manutenção,25.0,13800,380,Atlas Copco,2018
EQ003,Transformador Auxiliar,Transformador,Subestação,Operacional,100.0,138000,13800,ABB,2019
EQ004,Gerador Emergência,Gerador,Casa de Máquinas,Standby,50.0,,13800,Cummins,2021
EQ005,Ventilador Industrial,Ventilador,Setor C,Operacional,5.5,380,380,Otam,2022"""
    
    @staticmethod
    def create_maintenance_csv() -> str:
        """Cria conteúdo CSV de manutenções para teste."""
        return """id,equipment_id,tipo,descricao,data_inicio,data_fim,status,custo,tecnico_responsavel,observacoes
1,EQ001,Preventiva,Troca de rolamentos,2024-01-15,2024-01-16,Concluida,2500.00,João Silva,Rolamentos substituídos conforme programação
2,EQ002,Corretiva,Reparo no sistema de refrigeração,2024-02-10,2024-02-12,Concluida,8750.50,Maria Santos,Sistema funcionando normalmente
3,EQ003,Preventiva,Inspeção termográfica,2024-01-20,2024-01-20,Concluida,1200.00,Carlos Oliveira,Sem anomalias detectadas
4,EQ004,Preventiva,Teste de funcionamento,2024-03-01,,Agendada,1500.00,Ana Costa,Teste mensal programado
5,EQ001,Preventiva,Lubrificação geral,2024-03-15,,Agendada,800.00,Pedro Lima,Manutenção de rotina trimestral"""
    
    @staticmethod
    def create_invalid_csv() -> str:
        """Cria CSV inválido para testes de erro."""
        return """id,nome,tipo
EQ001,Equipment 1,
,Equipment 2,Motor
EQ003,,Pump
invalid_data_here
EQ004,Equipment 4,Generator,extra_column_value"""
    
    @staticmethod
    def create_large_csv(num_records: int = 1000) -> str:
        """Cria CSV grande para testes de performance."""
        header = "id,nome,tipo,localizacao,status,potencia_mva,fabricante,ano_fabricacao\n"
        lines = []
        
        for i in range(num_records):
            lines.append(f"EQ{i:06d},Equipment {i},Motor,Setor {i % 10},Operacional,{10.5 + i % 50},Fabricante {i % 5},{2015 + i % 10}")
        
        return header + "\n".join(lines)
    
    @staticmethod
    def create_xlsx_content() -> bytes:
        """Cria conteúdo Excel para teste."""
        df = pd.DataFrame({
            'id': ['EQ001', 'EQ002', 'EQ003'],
            'nome': ['Motor A', 'Pump B', 'Generator C'],
            'tipo': ['Motor', 'Pump', 'Generator'],
            'status': ['Operacional', 'Manutenção', 'Standby']
        })
        
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)
        return buffer.getvalue()


@pytest.mark.integration
class TestUploadWorkflow:
    """Testes de integração do fluxo completo de upload."""
    
    @pytest.fixture
    def client(self):
        """Cliente de teste da API."""
        return TestClient(app)
    
    @pytest.fixture
    def temp_upload_dir(self):
        """Diretório temporário para uploads."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    async def mock_database(self):
        """Mock do banco de dados para testes."""
        with patch('src.database.connection.get_database_connection') as mock_conn:
            # Mock da conexão
            mock_connection = Mock()
            mock_conn.return_value = mock_connection
            
            # Mock dos repositórios
            equipment_repo = Mock(spec=EquipmentRepository)
            maintenance_repo = Mock(spec=MaintenanceRepository)
            upload_repo = Mock(spec=UploadStatusRepository)
            
            # Configurar comportamentos dos mocks
            equipment_repo.create_bulk.return_value = 5  # 5 equipamentos inseridos
            maintenance_repo.create_bulk.return_value = 5  # 5 manutenções inseridas
            upload_repo.create.return_value = None
            upload_repo.update_status.return_value = None
            
            yield {
                'connection': mock_connection,
                'equipment_repo': equipment_repo,
                'maintenance_repo': maintenance_repo,
                'upload_repo': upload_repo
            }
    
    @pytest.fixture
    def mock_settings(self):
        """Configurações mock para testes."""
        settings = Mock()
        settings.upload_allowed_extensions = ['.csv', '.xlsx', '.xml']
        settings.upload_max_size = 50 * 1024 * 1024  # 50MB
        settings.upload_directory = "data/uploads"
        return settings
    
    async def test_complete_csv_upload_workflow(self, client, temp_upload_dir, mock_database):
        """Testa fluxo completo de upload de CSV."""
        # Preparar dados de teste
        csv_content = TestDataGenerator.create_equipment_csv()
        csv_bytes = csv_content.encode('utf-8')
        
        # Simular upload via API
        files = {"file": ("equipment_test.csv", io.BytesIO(csv_bytes), "text/csv")}
        data = {
            "file_type": FileType.EQUIPMENT.value,
            "description": "Teste de upload de equipamentos",
            "overwrite_existing": False
        }
        
        with patch('src.api.endpoints.upload.get_current_settings') as mock_get_settings, \
             patch('src.api.endpoints.upload.Path') as mock_path, \
             patch('src.api.endpoints.upload.open', create=True) as mock_open, \
             patch('src.api.endpoints.upload.DataProcessor') as mock_processor_class:
            
            # Configurar mocks
            mock_get_settings.return_value = self.mock_settings()
            
            mock_upload_dir = Mock()
            mock_upload_dir.mkdir = Mock()
            mock_upload_dir.__truediv__ = Mock(return_value=Path("data/uploads/equipment_test.csv"))
            mock_path.return_value = mock_upload_dir
            
            mock_processor = Mock()
            mock_processor.detect_file_format.return_value = FileFormat.CSV
            mock_processor.detect_data_type.return_value = DataType.EQUIPMENT_DATA
            mock_processor_class.return_value = mock_processor
            
            # Executar upload
            response = client.post("/api/v1/files/upload", files=files, data=data)
            
            # Verificar resposta do upload
            assert response.status_code == 200
            upload_data = response.json()
            
            assert "upload_id" in upload_data
            assert upload_data["filename"] == "equipment_test.csv"
            assert upload_data["file_type"] == FileType.EQUIPMENT.value
            assert upload_data["status"] == UploadStatus.UPLOADED.value
            
            upload_id = upload_data["upload_id"]
            
            # Simular processamento ETL
            await self._simulate_etl_processing(upload_id, csv_content, mock_database)
            
            # Verificar status final
            status_response = client.get(f"/api/v1/files/status/{upload_id}")
            assert status_response.status_code == 200
            
            status_data = status_response.json()
            assert status_data["status"] == UploadStatus.COMPLETED.value
            assert status_data["records_processed"] == 5
            assert status_data["records_valid"] == 5
            assert status_data["records_invalid"] == 0
    
    async def test_excel_upload_workflow(self, client, mock_database):
        """Testa fluxo de upload de arquivo Excel."""
        # Preparar dados Excel
        excel_content = TestDataGenerator.create_xlsx_content()
        
        files = {"file": ("equipment_test.xlsx", io.BytesIO(excel_content), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        data = {
            "file_type": FileType.EQUIPMENT.value,
            "description": "Teste de upload Excel",
            "overwrite_existing": False
        }
        
        with patch('src.api.endpoints.upload.get_current_settings') as mock_get_settings, \
             patch('src.api.endpoints.upload.Path') as mock_path, \
             patch('src.api.endpoints.upload.open', create=True) as mock_open, \
             patch('src.api.endpoints.upload.DataProcessor') as mock_processor_class:
            
            # Configurar mocks
            mock_get_settings.return_value = self.mock_settings()
            
            mock_upload_dir = Mock()
            mock_upload_dir.mkdir = Mock()
            mock_upload_dir.__truediv__ = Mock(return_value=Path("data/uploads/equipment_test.xlsx"))
            mock_path.return_value = mock_upload_dir
            
            mock_processor = Mock()
            mock_processor.detect_file_format.return_value = FileFormat.XLSX
            mock_processor.detect_data_type.return_value = DataType.EQUIPMENT_DATA
            mock_processor_class.return_value = mock_processor
            
            # Executar upload
            response = client.post("/api/v1/files/upload", files=files, data=data)
            
            # Verificar resposta
            assert response.status_code == 200
            upload_data = response.json()
            assert upload_data["filename"] == "equipment_test.xlsx"
            assert upload_data["file_type"] == FileType.EQUIPMENT.value
    
    async def test_invalid_file_upload_workflow(self, client, mock_database):
        """Testa fluxo com arquivo inválido."""
        # Preparar dados inválidos
        invalid_csv = TestDataGenerator.create_invalid_csv()
        csv_bytes = invalid_csv.encode('utf-8')
        
        files = {"file": ("invalid_equipment.csv", io.BytesIO(csv_bytes), "text/csv")}
        data = {
            "file_type": FileType.EQUIPMENT.value,
            "description": "Teste com dados inválidos",
            "overwrite_existing": False
        }
        
        with patch('src.api.endpoints.upload.get_current_settings') as mock_get_settings, \
             patch('src.api.endpoints.upload.Path') as mock_path, \
             patch('src.api.endpoints.upload.open', create=True) as mock_open, \
             patch('src.api.endpoints.upload.DataProcessor') as mock_processor_class:
            
            # Configurar mocks
            mock_get_settings.return_value = self.mock_settings()
            
            mock_upload_dir = Mock()
            mock_upload_dir.mkdir = Mock()
            mock_upload_dir.__truediv__ = Mock(return_value=Path("data/uploads/invalid_equipment.csv"))
            mock_path.return_value = mock_upload_dir
            
            mock_processor = Mock()
            mock_processor.detect_file_format.return_value = FileFormat.CSV
            mock_processor.detect_data_type.return_value = DataType.EQUIPMENT_DATA
            mock_processor_class.return_value = mock_processor
            
            # Executar upload
            response = client.post("/api/v1/files/upload", files=files, data=data)
            
            # Verificar que upload foi aceito
            assert response.status_code == 200
            upload_data = response.json()
            upload_id = upload_data["upload_id"]
            
            # Simular processamento com erros
            await self._simulate_etl_processing_with_errors(upload_id, invalid_csv, mock_database)
            
            # Verificar status com erros
            status_response = client.get(f"/api/v1/files/status/{upload_id}")
            assert status_response.status_code == 200
            
            status_data = status_response.json()
            assert status_data["records_invalid"] > 0
            assert status_data["error_message"] is not None
    
    # Métodos auxiliares
    async def _simulate_etl_processing(self, upload_id: str, csv_content: str, mock_database: Dict):
        """Simula processamento ETL completo."""
        # Atualizar status para processando
        mock_database['upload_repo'].update_status(
            upload_id,
            UploadStatus.PROCESSING.value,
            progress_percentage=0
        )
        
        # Simular processamento dos dados
        lines = csv_content.strip().split('\n')
        records_count = len(lines) - 1  # Excluir header
        
        # Simular inserção no banco
        mock_database['equipment_repo'].create_bulk.return_value = records_count
        
        # Atualizar status final
        mock_database['upload_repo'].update_status(
            upload_id,
            UploadStatus.COMPLETED.value,
            progress_percentage=100,
            records_processed=records_count,
            records_valid=records_count,
            records_invalid=0
        )
    
    async def _simulate_etl_processing_with_errors(self, upload_id: str, csv_content: str, mock_database: Dict):
        """Simula processamento ETL com erros."""
        lines = csv_content.strip().split('\n')
        total_records = len(lines) - 1
        invalid_records = 3  # Simular 3 registros inválidos
        valid_records = total_records - invalid_records
        
        # Atualizar com erros
        mock_database['upload_repo'].update_status(
            upload_id,
            UploadStatus.COMPLETED.value,
            progress_percentage=100,
            records_processed=total_records,
            records_valid=valid_records,
            records_invalid=invalid_records,
            error_message="Alguns registros continham dados inválidos"
        )


@pytest.mark.integration
class TestUploadErrorScenarios:
    """Testes de cenários de erro específicos."""
    
    @pytest.fixture
    def client(self):
        """Cliente de teste da API."""
        return TestClient(app)
    
    async def test_file_too_large_error(self, client):
        """Testa erro de arquivo muito grande."""
        # Criar arquivo simulando ser muito grande
        large_content = b"x" * (60 * 1024 * 1024)  # 60MB
        
        files = {"file": ("huge_file.csv", io.BytesIO(large_content), "text/csv")}
        
        response = client.post("/api/v1/files/upload", files=files)
        
        # Deve retornar erro 413 (Request Entity Too Large)
        assert response.status_code == 413
        error_data = response.json()
        assert "muito grande" in error_data["detail"].lower()
    
    async def test_invalid_file_extension_error(self, client):
        """Testa erro de extensão inválida."""
        files = {"file": ("document.txt", io.BytesIO(b"some text"), "text/plain")}
        
        response = client.post("/api/v1/files/upload", files=files)
        
        assert response.status_code == 400
        error_data = response.json()
        assert "extensão" in error_data["detail"].lower()
    
    async def test_empty_filename_error(self, client):
        """Testa erro de nome de arquivo vazio."""
        files = {"file": ("", io.BytesIO(b"data"), "text/csv")}
        
        response = client.post("/api/v1/files/upload", files=files)
        
        assert response.status_code == 400
        error_data = response.json()
        assert "vazio" in error_data["detail"].lower()