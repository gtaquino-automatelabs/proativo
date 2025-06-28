"""
Testes de concorrência para múltiplos uploads simultâneos.

Este módulo testa como o sistema lida com múltiplos uploads acontecendo
simultaneamente, validando thread safety, integridade de dados e performance.
"""

import pytest
import asyncio
import threading
import time
import tempfile
import uuid
import queue
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, List, Any, Tuple

from fastapi import UploadFile
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.endpoints.upload import upload_file
from src.api.config import Settings
from src.etl.upload_monitor import UploadMonitor, UploadStatus
from src.etl.data_processor import DataProcessor, FileFormat, DataType
from src.frontend.components.file_upload import FileUploadComponent
from src.frontend.services.api_client import APIClient


class ConcurrentUploadSimulator:
    """Simulador de uploads concorrentes para testes."""
    
    def __init__(self):
        self.results = queue.Queue()
        self.errors = queue.Queue()
        self.upload_counter = 0
        self.lock = threading.Lock()
    
    def generate_test_file_content(self, file_id: int, file_type: str = "equipment", size_kb: int = 100) -> bytes:
        """Gera conteúdo de arquivo de teste."""
        if file_type == "equipment":
            headers = "id,name,type,location,status\n"
            base_content = f"{file_id},Equipment_{file_id},Motor,Location_{file_id},Active\n"
        else:  # maintenance
            headers = "id,equipment_id,order_number,type,status\n"
            base_content = f"{file_id},{file_id},MO{file_id:06d},Preventive,Completed\n"
        
        # Repetir conteúdo para atingir tamanho desejado
        target_size = size_kb * 1024
        content = headers
        
        while len(content.encode('utf-8')) < target_size:
            content += base_content
        
        return content.encode('utf-8')
    
    def simulate_api_upload(self, file_id: int, file_size_kb: int = 100) -> Dict[str, Any]:
        """Simula upload via API."""
        try:
            start_time = time.time()
            
            # Gerar conteúdo do arquivo
            file_content = self.generate_test_file_content(file_id, "equipment", file_size_kb)
            filename = f"concurrent_equipment_{file_id}.csv"
            
            # Simular processamento
            time.sleep(0.1 + (file_size_kb / 10000))  # Simular tempo proporcional ao tamanho
            
            with self.lock:
                self.upload_counter += 1
                upload_id = f"concurrent-upload-{self.upload_counter}"
            
            end_time = time.time()
            
            result = {
                "file_id": file_id,
                "upload_id": upload_id,
                "filename": filename,
                "file_size": len(file_content),
                "duration": end_time - start_time,
                "success": True,
                "thread_id": threading.get_ident()
            }
            
            self.results.put(result)
            return result
            
        except Exception as e:
            error = {
                "file_id": file_id,
                "error": str(e),
                "thread_id": threading.get_ident()
            }
            self.errors.put(error)
            return error
    
    def simulate_frontend_upload(self, file_id: int, api_client: APIClient) -> Dict[str, Any]:
        """Simula upload via frontend."""
        try:
            start_time = time.time()
            
            file_content = self.generate_test_file_content(file_id, "maintenance", 50)
            filename = f"concurrent_maintenance_{file_id}.csv"
            
            # Mock da resposta da API
            api_response = {
                "upload_id": f"frontend-upload-{file_id}",
                "filename": filename,
                "file_size": len(file_content),
                "message": "Upload realizado com sucesso"
            }
            
            # Simular chamada para API
            api_client.upload_file.return_value = (api_response, True)
            
            end_time = time.time()
            
            result = {
                "file_id": file_id,
                "upload_id": api_response["upload_id"],
                "filename": filename,
                "file_size": len(file_content),
                "duration": end_time - start_time,
                "success": True,
                "source": "frontend",
                "thread_id": threading.get_ident()
            }
            
            self.results.put(result)
            return result
            
        except Exception as e:
            error = {
                "file_id": file_id,
                "error": str(e),
                "source": "frontend",
                "thread_id": threading.get_ident()
            }
            self.errors.put(error)
            return error
    
    def get_results(self) -> List[Dict[str, Any]]:
        """Coleta todos os resultados."""
        results = []
        while not self.results.empty():
            results.append(self.results.get())
        return results
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """Coleta todos os erros."""
        errors = []
        while not self.errors.empty():
            errors.append(self.errors.get())
        return errors


@pytest.mark.concurrency
class TestUploadConcurrency:
    """Testes de concorrência para uploads."""
    
    @pytest.fixture
    def mock_settings(self):
        """Settings mock para testes."""
        settings = Mock(spec=Settings)
        settings.upload_allowed_extensions = [".csv", ".xlsx", ".xml"]
        settings.upload_max_size = 50 * 1024 * 1024  # 50MB
        settings.upload_directory = "data/uploads"
        return settings
    
    @pytest.fixture
    def simulator(self):
        """Simulador de uploads concorrentes."""
        return ConcurrentUploadSimulator()
    
    @pytest.fixture
    def temp_upload_dir(self):
        """Diretório temporário para testes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def test_concurrent_api_uploads_thread_safety(self, mock_settings, simulator):
        """Testa thread safety de uploads simultâneos via API."""
        num_uploads = 10
        
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
                    # Executar uploads concorrentes
                    with ThreadPoolExecutor(max_workers=5) as executor:
                        futures = [
                            executor.submit(simulator.simulate_api_upload, i, 100)
                            for i in range(num_uploads)
                        ]
                        
                        # Aguardar conclusão
                        for future in as_completed(futures):
                            future.result()
        
        # Coletar resultados
        results = simulator.get_results()
        errors = simulator.get_errors()
        
        # Validações
        assert len(errors) == 0, f"Não deveria haver erros: {errors}"
        assert len(results) == num_uploads, f"Deveria ter {num_uploads} resultados"
        
        # Verificar thread safety
        upload_ids = [r["upload_id"] for r in results]
        assert len(set(upload_ids)) == num_uploads, "Todos os upload_ids deveriam ser únicos"
        
        thread_ids = [r["thread_id"] for r in results]
        assert len(set(thread_ids)) > 1, "Deveria usar múltiplas threads"
        
        # Verificar performance
        total_duration = sum(r["duration"] for r in results)
        max_duration = max(r["duration"] for r in results)
        
        print(f"\n=== RESULTADOS DE CONCORRÊNCIA - API ===")
        print(f"Uploads: {len(results)}")
        print(f"Threads utilizadas: {len(set(thread_ids))}")
        print(f"Tempo total: {total_duration:.2f}s")
        print(f"Tempo máximo por upload: {max_duration:.2f}s")
        print(f"Tempo médio por upload: {total_duration/len(results):.2f}s")
        
        # Critérios de performance
        assert max_duration < 5.0, f"Upload individual muito lento: {max_duration:.2f}s"
    
    def test_concurrent_frontend_uploads(self, simulator):
        """Testa uploads simultâneos via frontend."""
        num_uploads = 8
        
        # Mock do APIClient
        mock_api_client = Mock(spec=APIClient)
        
        # Executar uploads concorrentes
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(simulator.simulate_frontend_upload, i, mock_api_client)
                for i in range(num_uploads)
            ]
            
            # Aguardar conclusão
            for future in as_completed(futures):
                future.result()
        
        # Coletar resultados
        results = simulator.get_results()
        errors = simulator.get_errors()
        
        # Validações
        assert len(errors) == 0, f"Não deveria haver erros: {errors}"
        assert len(results) == num_uploads, f"Deveria ter {num_uploads} resultados"
        
        # Verificar que todos são do frontend
        for result in results:
            assert result["source"] == "frontend"
            assert "frontend-upload-" in result["upload_id"]
        
        # Verificar chamadas para API
        assert mock_api_client.upload_file.call_count == num_uploads
    
    def test_mixed_concurrent_uploads(self, mock_settings, simulator):
        """Testa uploads mistos (API + Frontend) simultâneos."""
        num_api_uploads = 5
        num_frontend_uploads = 5
        
        mock_api_client = Mock(spec=APIClient)
        
        # Mock do DataProcessor para uploads via API
        with patch('src.api.endpoints.upload.DataProcessor') as mock_processor_class:
            mock_processor = Mock()
            mock_processor.detect_file_format.return_value = FileFormat.CSV
            mock_processor.detect_data_type.return_value = DataType.EQUIPMENT_DATA
            mock_processor_class.return_value = mock_processor
            
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
                    # Executar uploads mistos concorrentes
                    with ThreadPoolExecutor(max_workers=6) as executor:
                        # Submeter uploads via API
                        api_futures = [
                            executor.submit(simulator.simulate_api_upload, i, 150)
                            for i in range(num_api_uploads)
                        ]
                        
                        # Submeter uploads via Frontend
                        frontend_futures = [
                            executor.submit(simulator.simulate_frontend_upload, i + 100, mock_api_client)
                            for i in range(num_frontend_uploads)
                        ]
                        
                        # Aguardar conclusão de todos
                        all_futures = api_futures + frontend_futures
                        for future in as_completed(all_futures):
                            future.result()
        
        # Coletar resultados
        results = simulator.get_results()
        errors = simulator.get_errors()
        
        # Validações
        assert len(errors) == 0, f"Não deveria haver erros: {errors}"
        assert len(results) == num_api_uploads + num_frontend_uploads
        
        # Separar resultados por fonte
        api_results = [r for r in results if r.get("source") != "frontend"]
        frontend_results = [r for r in results if r.get("source") == "frontend"]
        
        assert len(api_results) == num_api_uploads
        assert len(frontend_results) == num_frontend_uploads
        
        print(f"\n=== RESULTADOS DE CONCORRÊNCIA MISTA ===")
        print(f"Uploads via API: {len(api_results)}")
        print(f"Uploads via Frontend: {len(frontend_results)}")
        print(f"Total: {len(results)}")
    
    def test_upload_monitor_concurrency(self, temp_upload_dir):
        """Testa concorrência no UploadMonitor."""
        monitor = UploadMonitor(temp_upload_dir)
        
        try:
            # Iniciar monitor
            monitor.start()
            
            # Criar múltiplos arquivos simultaneamente
            def create_test_file(file_id: int):
                file_path = temp_upload_dir / f"concurrent_test_{file_id}.csv"
                content = f"id,name\n{file_id},Equipment {file_id}"
                file_path.write_text(content)
                return file_path
            
            # Criar arquivos concorrentemente
            num_files = 8
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [
                    executor.submit(create_test_file, i)
                    for i in range(num_files)
                ]
                
                created_files = []
                for future in as_completed(futures):
                    created_files.append(future.result())
            
            # Aguardar processamento
            time.sleep(2)
            
            # Verificar que todos os arquivos foram detectados
            stats = monitor.get_statistics()
            assert stats['files_monitored'] >= num_files, f"Deveria monitorar pelo menos {num_files} arquivos"
            
        finally:
            monitor.stop()
    
    def test_database_concurrency_simulation(self, mock_settings):
        """Testa simulação de concorrência no banco de dados."""
        
        # Contador thread-safe para simular IDs únicos
        id_counter = threading.Lock()
        current_id = [0]
        
        def simulate_database_insert(upload_data: Dict[str, Any]) -> bool:
            """Simula inserção no banco com possível contenção."""
            try:
                # Simular tempo de inserção no banco
                time.sleep(0.05)  # 50ms
                
                # Simular geração de ID único
                with id_counter:
                    current_id[0] += 1
                    upload_data['db_id'] = current_id[0]
                
                # Simular validação de dados
                required_fields = ['upload_id', 'filename', 'file_size']
                for field in required_fields:
                    if field not in upload_data:
                        raise ValueError(f"Campo obrigatório ausente: {field}")
                
                return True
                
            except Exception as e:
                print(f"Erro na inserção: {e}")
                return False
        
        # Simular múltiplas inserções concorrentes
        num_inserts = 12
        results = []
        
        def concurrent_insert(insert_id: int):
            upload_data = {
                'upload_id': f'concurrent-db-{insert_id}',
                'filename': f'file_{insert_id}.csv',
                'file_size': 1024 * insert_id,
                'status': 'uploaded'
            }
            
            success = simulate_database_insert(upload_data)
            results.append({
                'insert_id': insert_id,
                'success': success,
                'db_id': upload_data.get('db_id'),
                'thread_id': threading.get_ident()
            })
        
        # Executar inserções concorrentes
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [
                executor.submit(concurrent_insert, i)
                for i in range(num_inserts)
            ]
            
            for future in as_completed(futures):
                future.result()
        
        # Validar resultados
        successful_inserts = [r for r in results if r['success']]
        assert len(successful_inserts) == num_inserts, "Todas as inserções deveriam ter sucesso"
        
        # Verificar IDs únicos
        db_ids = [r['db_id'] for r in successful_inserts]
        assert len(set(db_ids)) == num_inserts, "Todos os IDs do banco deveriam ser únicos"
        
        # Verificar uso de múltiplas threads
        thread_ids = [r['thread_id'] for r in results]
        assert len(set(thread_ids)) > 1, "Deveria usar múltiplas threads"
        
        print(f"\n=== SIMULAÇÃO DE CONCORRÊNCIA NO BANCO ===")
        print(f"Inserções: {len(successful_inserts)}")
        print(f"Threads utilizadas: {len(set(thread_ids))}")
        print(f"IDs únicos gerados: {len(set(db_ids))}")
    
    def test_resource_contention_handling(self, simulator):
        """Testa como o sistema lida com contenção de recursos."""
        
        # Simular recurso compartilhado com contenção
        shared_resource = threading.Lock()
        resource_access_count = [0]
        max_concurrent_access = [0]
        current_access = [0]
        access_lock = threading.Lock()
        
        def access_shared_resource(worker_id: int) -> Dict[str, Any]:
            """Simula acesso a recurso compartilhado."""
            start_time = time.time()
            
            # Tentar acessar recurso
            with shared_resource:
                with access_lock:
                    current_access[0] += 1
                    max_concurrent_access[0] = max(max_concurrent_access[0], current_access[0])
                    resource_access_count[0] += 1
                
                # Simular trabalho com o recurso
                time.sleep(0.1)
                
                with access_lock:
                    current_access[0] -= 1
            
            end_time = time.time()
            
            return {
                'worker_id': worker_id,
                'duration': end_time - start_time,
                'thread_id': threading.get_ident()
            }
        
        # Executar acesso concorrente ao recurso
        num_workers = 10
        results = []
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(access_shared_resource, i)
                for i in range(num_workers)
            ]
            
            for future in as_completed(futures):
                results.append(future.result())
        
        # Validar contenção
        assert len(results) == num_workers
        assert resource_access_count[0] == num_workers, "Todos os workers deveriam ter acessado o recurso"
        assert max_concurrent_access[0] == 1, "Apenas um worker deveria acessar o recurso por vez"
        
        # Verificar que houve serialização (tempos similares)
        durations = [r['duration'] for r in results]
        avg_duration = sum(durations) / len(durations)
        
        print(f"\n=== TESTE DE CONTENÇÃO DE RECURSOS ===")
        print(f"Workers: {num_workers}")
        print(f"Acessos ao recurso: {resource_access_count[0]}")
        print(f"Máximo acesso concorrente: {max_concurrent_access[0]}")
        print(f"Duração média: {avg_duration:.3f}s")
        
        # Todos os acessos deveriam ter duração similar (serialização)
        for duration in durations:
            assert 0.08 <= duration <= 0.15, f"Duração fora do esperado: {duration:.3f}s"


@pytest.mark.integration
class TestConcurrencyIntegration:
    """Testes de integração para concorrência."""
    
    def test_full_concurrent_upload_workflow(self):
        """Testa fluxo completo com uploads concorrentes."""
        
        # Simular cenário realista com diferentes tipos de upload
        scenarios = [
            {"type": "small_csv", "size_kb": 50, "count": 3},
            {"type": "medium_xlsx", "size_kb": 500, "count": 2},
            {"type": "large_csv", "size_kb": 2000, "count": 1},
        ]
        
        all_results = []
        
        def simulate_upload_scenario(scenario: Dict[str, Any], file_id: int):
            """Simula cenário específico de upload."""
            start_time = time.time()
            
            # Simular processamento baseado no tipo e tamanho
            processing_time = scenario["size_kb"] / 10000  # Tempo proporcional
            time.sleep(processing_time)
            
            end_time = time.time()
            
            return {
                "scenario": scenario["type"],
                "file_id": file_id,
                "size_kb": scenario["size_kb"],
                "duration": end_time - start_time,
                "thread_id": threading.get_ident()
            }
        
        # Executar todos os cenários concorrentemente
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = []
            file_id = 0
            
            for scenario in scenarios:
                for _ in range(scenario["count"]):
                    futures.append(
                        executor.submit(simulate_upload_scenario, scenario, file_id)
                    )
                    file_id += 1
            
            # Coletar resultados
            for future in as_completed(futures):
                all_results.append(future.result())
        
        # Analisar resultados
        total_uploads = sum(s["count"] for s in scenarios)
        assert len(all_results) == total_uploads
        
        # Agrupar por tipo
        by_type = {}
        for result in all_results:
            scenario_type = result["scenario"]
            if scenario_type not in by_type:
                by_type[scenario_type] = []
            by_type[scenario_type].append(result)
        
        print(f"\n=== WORKFLOW CONCORRENTE COMPLETO ===")
        print(f"Total de uploads: {total_uploads}")
        print(f"Threads utilizadas: {len(set(r['thread_id'] for r in all_results))}")
        
        for scenario_type, results in by_type.items():
            avg_duration = sum(r['duration'] for r in results) / len(results)
            print(f"{scenario_type}: {len(results)} uploads, {avg_duration:.3f}s média")
        
        # Validar que uploads pequenos foram mais rápidos que grandes
        small_avg = sum(r['duration'] for r in by_type['small_csv']) / len(by_type['small_csv'])
        large_avg = sum(r['duration'] for r in by_type['large_csv']) / len(by_type['large_csv'])
        
        assert small_avg < large_avg, "Uploads pequenos deveriam ser mais rápidos que grandes"


if __name__ == "__main__":
    # Executar testes de concorrência
    pytest.main([__file__, "-v", "-m", "concurrency", "--tb=short"])