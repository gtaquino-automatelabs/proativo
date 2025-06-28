"""
Testes de performance para upload de arquivos grandes.

Este módulo testa a performance do sistema com arquivos próximos ao limite
de 50MB, medindo tempos de upload, processamento e uso de memória.
"""

import pytest
import asyncio
import time
import io
import csv
import tempfile
import psutil
import os
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

from fastapi import UploadFile
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.endpoints.upload import upload_file
from src.api.config import Settings
from src.etl.data_processor import DataProcessor, FileFormat, DataType
from src.frontend.components.file_upload import FileUploadComponent
from src.frontend.services.api_client import APIClient


class PerformanceDataGenerator:
    """Gerador de dados para testes de performance."""
    
    @staticmethod
    def generate_large_csv_content(target_size_mb: int, data_type: str = "equipment") -> bytes:
        """
        Gera conteúdo CSV grande para testes de performance.
        
        Args:
            target_size_mb: Tamanho alvo em MB
            data_type: Tipo de dados (equipment ou maintenance)
            
        Returns:
            Conteúdo CSV em bytes
        """
        target_size_bytes = target_size_mb * 1024 * 1024
        
        if data_type == "equipment":
            headers = [
                "id", "name", "type", "model", "manufacturer", "serial_number",
                "location", "status", "criticality", "installation_date",
                "last_maintenance", "next_maintenance", "cost_center",
                "description", "specifications", "notes"
            ]
            
            def generate_equipment_row(row_id: int) -> List[str]:
                return [
                    str(row_id),
                    f"Equipment_{row_id:06d}",
                    f"Type_{row_id % 10}",
                    f"Model_{row_id % 50}",
                    f"Manufacturer_{row_id % 20}",
                    f"SN{row_id:010d}",
                    f"Location_{row_id % 100}",
                    ["Active", "Inactive", "Maintenance"][row_id % 3],
                    ["Low", "Medium", "High", "Critical"][row_id % 4],
                    f"2020-{(row_id % 12) + 1:02d}-{(row_id % 28) + 1:02d}",
                    f"2024-{(row_id % 12) + 1:02d}-{(row_id % 28) + 1:02d}",
                    f"2024-{((row_id % 12) + 2):02d}-{(row_id % 28) + 1:02d}",
                    f"CC_{row_id % 20:03d}",
                    f"Description for equipment {row_id} with detailed information about its purpose and usage",
                    f"Specifications: Power={row_id % 1000}W, Voltage={row_id % 500}V, Current={row_id % 100}A",
                    f"Additional notes and maintenance history for equipment {row_id}"
                ]
            
            generate_row = generate_equipment_row
            
        else:  # maintenance
            headers = [
                "id", "equipment_id", "order_number", "type", "priority",
                "status", "scheduled_date", "completion_date", "technician",
                "description", "work_performed", "parts_used", "cost",
                "downtime_hours", "notes", "follow_up_required"
            ]
            
            def generate_maintenance_row(row_id: int) -> List[str]:
                return [
                    str(row_id),
                    str((row_id % 10000) + 1),
                    f"MO{row_id:08d}",
                    ["Preventive", "Corrective", "Predictive", "Emergency"][row_id % 4],
                    ["Low", "Medium", "High", "Critical"][row_id % 4],
                    ["Scheduled", "In Progress", "Completed", "Cancelled"][row_id % 4],
                    f"2024-{(row_id % 12) + 1:02d}-{(row_id % 28) + 1:02d}",
                    f"2024-{(row_id % 12) + 1:02d}-{(row_id % 28) + 2:02d}",
                    f"Tech_{row_id % 50:03d}",
                    f"Maintenance work description for order {row_id} including detailed procedures and safety requirements",
                    f"Work performed: inspection, cleaning, lubrication, adjustment, replacement of components for maintenance {row_id}",
                    f"Parts: Filter_{row_id % 100}, Oil_{row_id % 50}, Belt_{row_id % 30}, Bearing_{row_id % 20}",
                    f"{(row_id % 5000) + 100}.{row_id % 100:02d}",
                    f"{row_id % 48}",
                    f"Detailed maintenance notes and observations for order {row_id} including recommendations for future work",
                    ["Yes", "No"][row_id % 2]
                ]
            
            generate_row = generate_maintenance_row
        
        # Calcular tamanho aproximado de uma linha
        sample_row = generate_row(1)
        sample_line = ",".join(f'"{field}"' for field in sample_row) + "\n"
        line_size = len(sample_line.encode('utf-8'))
        
        # Calcular número de linhas necessárias
        header_line = ",".join(f'"{header}"' for header in headers) + "\n"
        header_size = len(header_line.encode('utf-8'))
        
        available_size = target_size_bytes - header_size
        num_rows = available_size // line_size
        
        # Gerar CSV
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)
        
        # Escrever header
        writer.writerow(headers)
        
        # Escrever dados
        for i in range(1, num_rows + 1):
            row = generate_row(i)
            writer.writerow(row)
        
        content = output.getvalue()
        return content.encode('utf-8')
    
    @staticmethod
    def generate_large_xlsx_content(target_size_mb: int) -> bytes:
        """
        Gera conteúdo XLSX grande para testes.
        
        Args:
            target_size_mb: Tamanho alvo em MB
            
        Returns:
            Conteúdo XLSX em bytes
        """
        try:
            import pandas as pd
            import openpyxl
        except ImportError:
            pytest.skip("pandas e openpyxl necessários para testes XLSX")
        
        # Gerar dados como CSV primeiro
        csv_content = PerformanceDataGenerator.generate_large_csv_content(
            target_size_mb, "equipment"
        )
        
        # Converter para DataFrame
        df = pd.read_csv(io.StringIO(csv_content.decode('utf-8')))
        
        # Salvar como XLSX em memória
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            df.to_excel(tmp_file.name, index=False, engine='openpyxl')
            tmp_file.flush()
            
            # Ler conteúdo
            with open(tmp_file.name, 'rb') as f:
                xlsx_content = f.read()
            
            # Limpar arquivo temporário
            os.unlink(tmp_file.name)
            
        return xlsx_content


class PerformanceMonitor:
    """Monitor de performance para testes."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.start_memory = None
        self.peak_memory = None
        self.process = psutil.Process()
    
    def start(self):
        """Inicia monitoramento."""
        self.start_time = time.time()
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.peak_memory = self.start_memory
    
    def update_peak_memory(self):
        """Atualiza pico de memória."""
        current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.peak_memory = max(self.peak_memory, current_memory)
    
    def stop(self) -> Dict[str, float]:
        """Para monitoramento e retorna métricas."""
        self.end_time = time.time()
        self.update_peak_memory()
        
        return {
            "duration_seconds": self.end_time - self.start_time,
            "start_memory_mb": self.start_memory,
            "peak_memory_mb": self.peak_memory,
            "memory_increase_mb": self.peak_memory - self.start_memory
        }


@pytest.mark.performance
class TestUploadPerformance:
    """Testes de performance para upload de arquivos grandes."""
    
    @pytest.fixture
    def mock_settings(self):
        """Settings mock para testes."""
        settings = Mock(spec=Settings)
        settings.upload_allowed_extensions = [".csv", ".xlsx", ".xml"]
        settings.upload_max_size = 50 * 1024 * 1024  # 50MB
        settings.upload_directory = "data/uploads"
        return settings
    
    @pytest.fixture
    def performance_monitor(self):
        """Monitor de performance."""
        return PerformanceMonitor()
    
    @pytest.mark.asyncio
    async def test_upload_large_csv_40mb_performance(self, mock_settings, performance_monitor):
        """Testa performance de upload de CSV de 40MB."""
        monitor = performance_monitor
        monitor.start()
        
        # Gerar arquivo de 40MB
        file_content = PerformanceDataGenerator.generate_large_csv_content(40, "equipment")
        actual_size_mb = len(file_content) / 1024 / 1024
        
        # Criar mock do UploadFile
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "large_equipment_40mb.csv"
        mock_file.read = AsyncMock(return_value=file_content)
        
        # Mock do DataProcessor
        with patch('src.api.endpoints.upload.DataProcessor') as mock_processor_class:
            mock_processor = Mock()
            mock_processor.detect_file_format.return_value = FileFormat.CSV
            mock_processor.detect_data_type.return_value = DataType.EQUIPMENT_DATA
            mock_processor_class.return_value = mock_processor
            
            # Mock do sistema de arquivos e banco
            with patch('src.api.endpoints.upload.Path') as mock_path, \
                 patch('src.api.endpoints.upload.get_async_session') as mock_session, \
                 patch('builtins.open', create=True) as mock_open:
                
                # Configurar mocks
                mock_path_instance = Mock()
                mock_path_instance.mkdir = Mock()
                mock_path_instance.exists.return_value = True
                mock_path_instance.__truediv__ = Mock(return_value=mock_path_instance)
                mock_path.return_value = mock_path_instance
                
                mock_session_instance = Mock()
                mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_instance)
                mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
                
                mock_repo_manager = Mock()
                mock_repo_manager.upload_status.create = AsyncMock()
                mock_repo_manager.commit = AsyncMock()
                
                with patch('src.api.endpoints.upload.RepositoryManager', return_value=mock_repo_manager):
                    # Executar upload
                    monitor.update_peak_memory()
                    
                    result = await upload_file(
                        file=mock_file,
                        file_type=None,
                        description="Teste de performance 40MB",
                        overwrite_existing=False,
                        settings=mock_settings,
                        _=None
                    )
                    
                    monitor.update_peak_memory()
        
        # Coletar métricas
        metrics = monitor.stop()
        
        # Validações de performance
        assert result is not None
        assert result.filename == "large_equipment_40mb.csv"
        assert result.file_size == len(file_content)
        
        # Métricas de performance
        print(f"\n=== MÉTRICAS DE PERFORMANCE - CSV 40MB ===")
        print(f"Tamanho real do arquivo: {actual_size_mb:.2f} MB")
        print(f"Tempo de upload: {metrics['duration_seconds']:.2f} segundos")
        print(f"Memória inicial: {metrics['start_memory_mb']:.2f} MB")
        print(f"Pico de memória: {metrics['peak_memory_mb']:.2f} MB")
        print(f"Aumento de memória: {metrics['memory_increase_mb']:.2f} MB")
        
        # Critérios de performance
        assert metrics['duration_seconds'] < 30, f"Upload muito lento: {metrics['duration_seconds']:.2f}s"
        assert metrics['memory_increase_mb'] < 200, f"Uso excessivo de memória: {metrics['memory_increase_mb']:.2f}MB"
        assert 38 <= actual_size_mb <= 42, f"Tamanho do arquivo fora do esperado: {actual_size_mb:.2f}MB"
    
    @pytest.mark.asyncio
    async def test_upload_large_csv_45mb_performance(self, mock_settings, performance_monitor):
        """Testa performance de upload de CSV de 45MB."""
        monitor = performance_monitor
        monitor.start()
        
        # Gerar arquivo de 45MB
        file_content = PerformanceDataGenerator.generate_large_csv_content(45, "maintenance")
        actual_size_mb = len(file_content) / 1024 / 1024
        
        # Criar mock do UploadFile
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "large_maintenance_45mb.csv"
        mock_file.read = AsyncMock(return_value=file_content)
        
        # Mock do DataProcessor
        with patch('src.api.endpoints.upload.DataProcessor') as mock_processor_class:
            mock_processor = Mock()
            mock_processor.detect_file_format.return_value = FileFormat.CSV
            mock_processor.detect_data_type.return_value = DataType.MAINTENANCE_DATA
            mock_processor_class.return_value = mock_processor
            
            # Mock do sistema de arquivos e banco
            with patch('src.api.endpoints.upload.Path') as mock_path, \
                 patch('src.api.endpoints.upload.get_async_session') as mock_session, \
                 patch('builtins.open', create=True) as mock_open:
                
                # Configurar mocks
                mock_path_instance = Mock()
                mock_path_instance.mkdir = Mock()
                mock_path_instance.exists.return_value = True
                mock_path_instance.__truediv__ = Mock(return_value=mock_path_instance)
                mock_path.return_value = mock_path_instance
                
                mock_session_instance = Mock()
                mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_instance)
                mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
                
                mock_repo_manager = Mock()
                mock_repo_manager.upload_status.create = AsyncMock()
                mock_repo_manager.commit = AsyncMock()
                
                with patch('src.api.endpoints.upload.RepositoryManager', return_value=mock_repo_manager):
                    # Executar upload
                    monitor.update_peak_memory()
                    
                    result = await upload_file(
                        file=mock_file,
                        file_type=None,
                        description="Teste de performance 45MB",
                        overwrite_existing=False,
                        settings=mock_settings,
                        _=None
                    )
                    
                    monitor.update_peak_memory()
        
        # Coletar métricas
        metrics = monitor.stop()
        
        # Validações de performance
        assert result is not None
        assert result.filename == "large_maintenance_45mb.csv"
        assert result.file_size == len(file_content)
        
        # Métricas de performance
        print(f"\n=== MÉTRICAS DE PERFORMANCE - CSV 45MB ===")
        print(f"Tamanho real do arquivo: {actual_size_mb:.2f} MB")
        print(f"Tempo de upload: {metrics['duration_seconds']:.2f} segundos")
        print(f"Memória inicial: {metrics['start_memory_mb']:.2f} MB")
        print(f"Pico de memória: {metrics['peak_memory_mb']:.2f} MB")
        print(f"Aumento de memória: {metrics['memory_increase_mb']:.2f} MB")
        
        # Critérios de performance
        assert metrics['duration_seconds'] < 35, f"Upload muito lento: {metrics['duration_seconds']:.2f}s"
        assert metrics['memory_increase_mb'] < 250, f"Uso excessivo de memória: {metrics['memory_increase_mb']:.2f}MB"
        assert 43 <= actual_size_mb <= 47, f"Tamanho do arquivo fora do esperado: {actual_size_mb:.2f}MB"
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not hasattr(pytest, "importorskip") or 
        pytest.importorskip("pandas", minversion="1.0") is None or
        pytest.importorskip("openpyxl", minversion="3.0") is None,
        reason="pandas e openpyxl necessários para testes XLSX"
    )
    async def test_upload_large_xlsx_42mb_performance(self, mock_settings, performance_monitor):
        """Testa performance de upload de XLSX de ~42MB."""
        monitor = performance_monitor
        monitor.start()
        
        try:
            # Gerar arquivo XLSX de ~42MB
            file_content = PerformanceDataGenerator.generate_large_xlsx_content(42)
            actual_size_mb = len(file_content) / 1024 / 1024
            
            # Criar mock do UploadFile
            mock_file = Mock(spec=UploadFile)
            mock_file.filename = "large_equipment_42mb.xlsx"
            mock_file.read = AsyncMock(return_value=file_content)
            
            # Mock do DataProcessor
            with patch('src.api.endpoints.upload.DataProcessor') as mock_processor_class:
                mock_processor = Mock()
                mock_processor.detect_file_format.return_value = FileFormat.XLSX
                mock_processor.detect_data_type.return_value = DataType.EQUIPMENT_DATA
                mock_processor_class.return_value = mock_processor
                
                # Mock do sistema de arquivos e banco
                with patch('src.api.endpoints.upload.Path') as mock_path, \
                     patch('src.api.endpoints.upload.get_async_session') as mock_session, \
                     patch('builtins.open', create=True) as mock_open:
                    
                    # Configurar mocks
                    mock_path_instance = Mock()
                    mock_path_instance.mkdir = Mock()
                    mock_path_instance.exists.return_value = True
                    mock_path_instance.__truediv__ = Mock(return_value=mock_path_instance)
                    mock_path.return_value = mock_path_instance
                    
                    mock_session_instance = Mock()
                    mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_instance)
                    mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
                    
                    mock_repo_manager = Mock()
                    mock_repo_manager.upload_status.create = AsyncMock()
                    mock_repo_manager.commit = AsyncMock()
                    
                    with patch('src.api.endpoints.upload.RepositoryManager', return_value=mock_repo_manager):
                        # Executar upload
                        monitor.update_peak_memory()
                        
                        result = await upload_file(
                            file=mock_file,
                            file_type=None,
                            description="Teste de performance XLSX 42MB",
                            overwrite_existing=False,
                            settings=mock_settings,
                            _=None
                        )
                        
                        monitor.update_peak_memory()
            
            # Coletar métricas
            metrics = monitor.stop()
            
            # Validações de performance
            assert result is not None
            assert result.filename == "large_equipment_42mb.xlsx"
            assert result.file_size == len(file_content)
            
            # Métricas de performance
            print(f"\n=== MÉTRICAS DE PERFORMANCE - XLSX ~42MB ===")
            print(f"Tamanho real do arquivo: {actual_size_mb:.2f} MB")
            print(f"Tempo de upload: {metrics['duration_seconds']:.2f} segundos")
            print(f"Memória inicial: {metrics['start_memory_mb']:.2f} MB")
            print(f"Pico de memória: {metrics['peak_memory_mb']:.2f} MB")
            print(f"Aumento de memória: {metrics['memory_increase_mb']:.2f} MB")
            
            # Critérios de performance (XLSX é mais pesado)
            assert metrics['duration_seconds'] < 45, f"Upload muito lento: {metrics['duration_seconds']:.2f}s"
            assert metrics['memory_increase_mb'] < 300, f"Uso excessivo de memória: {metrics['memory_increase_mb']:.2f}MB"
            assert actual_size_mb <= 50, f"Arquivo excede limite: {actual_size_mb:.2f}MB"
            
        except ImportError:
            pytest.skip("pandas e openpyxl necessários para testes XLSX")
    
    def test_frontend_large_file_handling(self):
        """Testa como o frontend lida com arquivos grandes."""
        # Mock do APIClient
        mock_api_client = Mock(spec=APIClient)
        mock_api_client.upload_file.return_value = (
            {
                "upload_id": "test-large-file-id",
                "filename": "large_file.csv",
                "file_size": 45 * 1024 * 1024,
                "message": "Upload realizado com sucesso"
            },
            True
        )
        
        # Criar componente
        component = FileUploadComponent(mock_api_client)
        
        # Mock de arquivo grande
        mock_file = Mock()
        mock_file.name = "large_equipment_data.csv"
        mock_file.size = 45 * 1024 * 1024  # 45MB
        mock_file.read = Mock(return_value=b"large file content...")
        
        # Testar validação
        validation_result = component._validate_file(mock_file)
        
        # Deve passar na validação (45MB < 50MB)
        assert validation_result["valid"] is True
        assert "válido" in validation_result["message"].lower()
        
        # Testar detecção de tipo
        detected_type = component._detect_file_type(mock_file.name)
        
        # Deve detectar como equipamento
        from src.api.models.upload import FileType
        assert detected_type == FileType.EQUIPMENT
    
    def test_memory_efficiency_with_large_files(self):
        """Testa eficiência de memória com arquivos grandes."""
        monitor = PerformanceMonitor()
        monitor.start()
        
        # Simular processamento de arquivo grande
        large_data = PerformanceDataGenerator.generate_large_csv_content(40, "equipment")
        
        monitor.update_peak_memory()
        
        # Simular operações que consomem memória
        lines = large_data.decode('utf-8').split('\n')
        processed_lines = [line.strip() for line in lines if line.strip()]
        
        monitor.update_peak_memory()
        
        # Simular limpeza
        del lines
        del processed_lines
        
        metrics = monitor.stop()
        
        print(f"\n=== TESTE DE EFICIÊNCIA DE MEMÓRIA ===")
        print(f"Tamanho dos dados: {len(large_data) / 1024 / 1024:.2f} MB")
        print(f"Aumento de memória: {metrics['memory_increase_mb']:.2f} MB")
        print(f"Eficiência: {(len(large_data) / 1024 / 1024) / max(metrics['memory_increase_mb'], 1):.2f}")
        
        # A memória adicional não deve ser muito maior que o arquivo
        assert metrics['memory_increase_mb'] < 300, f"Uso excessivo de memória: {metrics['memory_increase_mb']:.2f}MB"


@pytest.mark.performance
class TestUploadPerformanceIntegration:
    """Testes de integração de performance."""
    
    def test_concurrent_large_uploads_simulation(self):
        """Simula uploads concorrentes de arquivos grandes."""
        import threading
        import queue
        
        results_queue = queue.Queue()
        
        def simulate_upload(file_size_mb: int, file_id: int):
            """Simula upload de arquivo."""
            monitor = PerformanceMonitor()
            monitor.start()
            
            # Simular geração de dados
            data = PerformanceDataGenerator.generate_large_csv_content(file_size_mb, "equipment")
            
            # Simular processamento
            time.sleep(0.1)  # Simular I/O
            
            metrics = monitor.stop()
            results_queue.put({
                "file_id": file_id,
                "size_mb": file_size_mb,
                "duration": metrics['duration_seconds'],
                "memory_mb": metrics['memory_increase_mb']
            })
        
        # Simular 3 uploads concorrentes
        threads = []
        file_sizes = [35, 40, 42]  # MB
        
        for i, size in enumerate(file_sizes):
            thread = threading.Thread(target=simulate_upload, args=(size, i))
            threads.append(thread)
            thread.start()
        
        # Aguardar conclusão
        for thread in threads:
            thread.join()
        
        # Coletar resultados
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())
        
        # Validar resultados
        assert len(results) == 3
        
        total_duration = sum(r['duration'] for r in results)
        total_memory = sum(r['memory_mb'] for r in results)
        
        print(f"\n=== TESTE DE CONCORRÊNCIA ===")
        for result in results:
            print(f"Arquivo {result['file_id']}: {result['size_mb']}MB, "
                  f"{result['duration']:.2f}s, {result['memory_mb']:.2f}MB")
        
        print(f"Total - Tempo: {total_duration:.2f}s, Memória: {total_memory:.2f}MB")
        
        # Critérios de performance para concorrência
        assert total_duration < 60, f"Processamento concorrente muito lento: {total_duration:.2f}s"
        assert total_memory < 500, f"Uso excessivo de memória concorrente: {total_memory:.2f}MB"


if __name__ == "__main__":
    # Executar testes de performance
    pytest.main([__file__, "-v", "-m", "performance", "--tb=short"])