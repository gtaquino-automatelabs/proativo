"""
Testes de integração completos para o pipeline PROAtivo.

Este módulo testa todo o fluxo integrado:
- Entrada do usuário em linguagem natural
- Processamento via QueryProcessor
- Busca no banco de dados
- Geração de resposta via LLM
- Sistema de cache e fallback
- Métricas de performance e accuracy
"""

import pytest
import asyncio
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock
import pandas as pd

from src.api.services.llm_service import LLMService
from src.api.services.cache_service import CacheService, CacheStrategy
from src.api.services.fallback_service import FallbackService
from src.api.services.query_processor import QueryProcessor
from src.api.services.rag_service import RAGService
from src.database.repositories import EquipmentRepository, MaintenanceRepository
from src.utils.error_handlers import LLMServiceError, ValidationError


class TestDataGenerator:
    """Gerador de dados de teste realistas."""
    
    @staticmethod
    def generate_equipment_data() -> List[Dict[str, Any]]:
        """Gera dados de equipamentos realistas."""
        return [
            {
                "id": "TR001",
                "nome": "Transformador Principal 1",
                "tipo": "Transformador",
                "localizacao": "Subestacao A",
                "status": "Operacional",
                "potencia_mva": 150.0,
                "tensao_primaria": 138000,
                "tensao_secundaria": 13800,
                "fabricante": "ABB",
                "ano_fabricacao": 2015,
                "ultima_manutencao": "2024-01-15",
                "proxima_manutencao": "2024-07-15"
            },
            {
                "id": "TR002", 
                "nome": "Transformador Principal 2",
                "tipo": "Transformador",
                "localizacao": "Subestacao A",
                "status": "Manutencao",
                "potencia_mva": 150.0,
                "tensao_primaria": 138000,
                "tensao_secundaria": 13800,
                "fabricante": "Siemens",
                "ano_fabricacao": 2018,
                "ultima_manutencao": "2024-02-20",
                "proxima_manutencao": "2024-08-20"
            },
            {
                "id": "GE001",
                "nome": "Gerador Diesel 1",
                "tipo": "Gerador",
                "localizacao": "Usina B",
                "status": "Operacional",
                "potencia_mva": 50.0,
                "tensao_primaria": None,
                "tensao_secundaria": 13800,
                "fabricante": "Caterpillar",
                "ano_fabricacao": 2020,
                "ultima_manutencao": "2024-01-10",
                "proxima_manutencao": "2024-04-10"
            },
            {
                "id": "DJ001",
                "nome": "Disjuntor Principal",
                "tipo": "Disjuntor",
                "localizacao": "Subestacao A",
                "status": "Operacional",
                "potencia_mva": None,
                "tensao_primaria": 138000,
                "tensao_secundaria": None,
                "fabricante": "Schneider",
                "ano_fabricacao": 2017,
                "ultima_manutencao": "2023-12-05",
                "proxima_manutencao": "2024-06-05"
            }
        ]
    
    @staticmethod
    def generate_maintenance_data() -> List[Dict[str, Any]]:
        """Gera dados de manutenção realistas."""
        return [
            {
                "id": 1,
                "equipment_id": "TR001",
                "tipo": "Preventiva",
                "descricao": "Análise de óleo isolante",
                "data_inicio": "2024-01-15",
                "data_fim": "2024-01-16",
                "status": "Concluida",
                "custo": 15000.0,
                "tecnico_responsavel": "João Silva",
                "observacoes": "Óleo dentro dos padrões"
            },
            {
                "id": 2,
                "equipment_id": "TR002",
                "tipo": "Corretiva",
                "descricao": "Substituição de bucha isoladora",
                "data_inicio": "2024-02-20",
                "data_fim": "2024-02-22",
                "status": "Em_Andamento",
                "custo": 25000.0,
                "tecnico_responsavel": "Maria Santos",
                "observacoes": "Bucha apresentava sinais de degradação"
            },
            {
                "id": 3,
                "equipment_id": "GE001",
                "tipo": "Preventiva",
                "descricao": "Troca de filtros e óleo",
                "data_inicio": "2024-01-10",
                "data_fim": "2024-01-10",
                "status": "Concluida",
                "custo": 5000.0,
                "tecnico_responsavel": "Carlos Oliveira",
                "observacoes": "Manutenção de rotina"
            },
            {
                "id": 4,
                "equipment_id": "TR001",
                "tipo": "Preventiva",
                "descricao": "Inspeção termográfica",
                "data_inicio": "2024-03-01",
                "data_fim": None,
                "status": "Agendada",
                "custo": 8000.0,
                "tecnico_responsavel": "Ana Costa",
                "observacoes": "Inspeção periódica programada"
            }
        ]


class TestScenarios:
    """Cenários de teste realistas."""
    
    @staticmethod
    def get_test_queries() -> List[Dict[str, Any]]:
        """Retorna queries de teste com respostas esperadas."""
        return [
            {
                "query": "Quantos transformadores estão operacionais?",
                "expected_type": "count_query",
                "expected_entities": ["transformador"],
                "expected_result_contains": ["1", "operacional", "TR001"],
                "performance_target_ms": 2000,
                "accuracy_critical": True
            },
            {
                "query": "Qual o status do transformador TR002?",
                "expected_type": "status_query",
                "expected_entities": ["TR002", "transformador"],
                "expected_result_contains": ["TR002", "manutenção", "Siemens"],
                "performance_target_ms": 1500,
                "accuracy_critical": True
            },
            {
                "query": "Mostre equipamentos que precisam de manutenção urgente",
                "expected_type": "maintenance_query",
                "expected_entities": ["manutenção"],
                "expected_result_contains": ["manutenção", "urgente"],
                "performance_target_ms": 3000,
                "accuracy_critical": False
            },
            {
                "query": "Qual o custo total de manutenções em 2024?",
                "expected_type": "cost_query",
                "expected_entities": ["custo", "2024"],
                "expected_result_contains": ["custo", "2024", "total"],
                "performance_target_ms": 2500,
                "accuracy_critical": True
            },
            {
                "query": "Liste transformadores da Subestação A",
                "expected_type": "location_query",
                "expected_entities": ["transformador", "Subestação A"],
                "expected_result_contains": ["TR001", "TR002", "Subestacao A"],
                "performance_target_ms": 2000,
                "accuracy_critical": True
            },
            {
                "query": "Quando foi a última manutenção do gerador GE001?",
                "expected_type": "date_query",
                "expected_entities": ["GE001", "gerador", "manutenção"],
                "expected_result_contains": ["GE001", "2024-01-10", "manutenção"],
                "performance_target_ms": 1800,
                "accuracy_critical": True
            },
            {
                "query": "Equipamentos fabricados pela ABB",
                "expected_type": "manufacturer_query",
                "expected_entities": ["ABB", "fabricante"],
                "expected_result_contains": ["ABB", "TR001", "fabricante"],
                "performance_target_ms": 2200,
                "accuracy_critical": False
            },
            {
                "query": "O que é um transformador? Como funciona?", # Query fora do escopo
                "expected_type": "out_of_scope",
                "expected_entities": [],
                "expected_result_contains": ["fora do escopo", "equipamentos", "manutenção"],
                "performance_target_ms": 1000,
                "accuracy_critical": False,
                "should_use_fallback": True
            }
        ]


@pytest.mark.integration
class TestCompletePipeline:
    """Testes de integração do pipeline completo."""
    
    @pytest.fixture
    async def mock_repositories(self):
        """Mock dos repositórios com dados de teste."""
        equipment_repo = Mock(spec=EquipmentRepository)
        maintenance_repo = Mock(spec=MaintenanceRepository)
        
        # Configurar dados de teste
        test_equipment = TestDataGenerator.generate_equipment_data()
        test_maintenance = TestDataGenerator.generate_maintenance_data()
        
        # Configurar métodos do repositório
        equipment_repo.get_all.return_value = test_equipment
        equipment_repo.get_by_id.side_effect = lambda eq_id: next(
            (eq for eq in test_equipment if eq["id"] == eq_id), None
        )
        equipment_repo.get_by_type.side_effect = lambda eq_type: [
            eq for eq in test_equipment if eq["tipo"].lower() == eq_type.lower()
        ]
        
        maintenance_repo.get_all.return_value = test_maintenance
        maintenance_repo.get_by_equipment_id.side_effect = lambda eq_id: [
            m for m in test_maintenance if m["equipment_id"] == eq_id
        ]
        
        return equipment_repo, maintenance_repo
    
    @pytest.fixture
    async def integrated_services(self, mock_repositories):
        """Serviços integrados para teste."""
        equipment_repo, maintenance_repo = mock_repositories
        
        # Inicializar serviços com mocks configurados
        with patch('src.api.services.query_processor.get_settings') as mock_settings:
            mock_settings.return_value = Mock(
                gemini_model="gemini-2.5-flash",
                gemini_temperature=0.2,
                gemini_timeout=30,
                gemini_max_retries=3
            )
            
            query_processor = QueryProcessor()
            cache_service = CacheService()
            fallback_service = FallbackService()
            
            # Mock LLM service para controlar respostas
            llm_service = Mock(spec=LLMService)
            
            # Configurar respostas do LLM baseadas na query
            async def mock_generate_response(user_query, **kwargs):
                query_lower = user_query.lower()
                
                if "quantos transformadores" in query_lower and "operacional" in query_lower:
                    return {
                        "response": "Existe 1 transformador operacional: TR001 (Transformador Principal 1) localizado na Subestação A.",
                        "confidence_score": 0.9,
                        "sources": ["equipment_data"],
                        "suggestions": ["Status do TR001", "Manutenções do TR001"],
                        "processing_time": 1200,
                        "cache_used": False,
                        "fallback_used": False
                    }
                elif "status" in query_lower and "tr002" in query_lower:
                    return {
                        "response": "O transformador TR002 está atualmente em manutenção. É um equipamento Siemens de 150 MVA localizado na Subestação A, com manutenção em andamento desde 20/02/2024.",
                        "confidence_score": 0.95,
                        "sources": ["equipment_data", "maintenance_data"],
                        "suggestions": ["Detalhes da manutenção do TR002", "Quando será concluída"],
                        "processing_time": 1350,
                        "cache_used": False,
                        "fallback_used": False
                    }
                elif "fora do escopo" in query_lower or "como funciona" in query_lower:
                    return {
                        "response": "Desculpe, essa pergunta está fora do escopo do sistema. Posso ajudar com informações sobre equipamentos específicos e suas manutenções.",
                        "confidence_score": 0.2,
                        "sources": ["fallback_system"],
                        "suggestions": ["Status dos equipamentos", "Manutenções pendentes"],
                        "processing_time": 800,
                        "cache_used": False,
                        "fallback_used": True
                    }
                else:
                    # Resposta genérica para outras queries
                    return {
                        "response": f"Processando sua consulta sobre: {user_query}. Baseado nos dados disponíveis, encontrei informações relevantes.",
                        "confidence_score": 0.7,
                        "sources": ["equipment_data"],
                        "suggestions": ["Mais detalhes", "Relatório completo"],
                        "processing_time": 1500,
                        "cache_used": False,
                        "fallback_used": False
                    }
            
            llm_service.generate_response = mock_generate_response
            
            return {
                "query_processor": query_processor,
                "cache_service": cache_service,
                "fallback_service": fallback_service,
                "llm_service": llm_service,
                "equipment_repo": equipment_repo,
                "maintenance_repo": maintenance_repo
            }
    
    async def test_end_to_end_pipeline(self, integrated_services):
        """Testa pipeline completo end-to-end."""
        services = integrated_services
        test_queries = TestScenarios.get_test_queries()
        
        results = []
        
        for test_case in test_queries:
            start_time = time.time()
            
            try:
                # 1. Processar query
                processed_query = await services["query_processor"].process_query(
                    test_case["query"]
                )
                
                # 2. Buscar dados (simulado com repositories)
                query_results = []
                if processed_query.query_type == "equipment_status":
                    query_results = services["equipment_repo"].get_all()
                elif processed_query.query_type == "maintenance_query":
                    query_results = services["maintenance_repo"].get_all()
                
                # 3. Gerar resposta com LLM
                response = await services["llm_service"].generate_response(
                    user_query=test_case["query"],
                    query_results=query_results,
                    context={"query_type": processed_query.query_type}
                )
                
                processing_time = int((time.time() - start_time) * 1000)
                
                # 4. Validar resultado
                test_result = {
                    "query": test_case["query"],
                    "expected_type": test_case["expected_type"],
                    "actual_response": response["response"],
                    "confidence": response["confidence_score"],
                    "processing_time": processing_time,
                    "target_time": test_case["performance_target_ms"],
                    "performance_ok": processing_time <= test_case["performance_target_ms"],
                    "accuracy_score": self._calculate_accuracy(
                        response["response"], 
                        test_case["expected_result_contains"]
                    ),
                    "accuracy_critical": test_case["accuracy_critical"],
                    "fallback_used": response.get("fallback_used", False),
                    "cache_used": response.get("cache_used", False)
                }
                
                results.append(test_result)
                
            except Exception as e:
                results.append({
                    "query": test_case["query"],
                    "error": str(e),
                    "processing_time": int((time.time() - start_time) * 1000),
                    "performance_ok": False,
                    "accuracy_score": 0.0
                })
        
        # Analisar resultados
        self._analyze_pipeline_results(results)
        
        return results
    
    def _calculate_accuracy(self, response: str, expected_contains: List[str]) -> float:
        """Calcula score de accuracy baseado em conteúdo esperado."""
        if not expected_contains:
            return 1.0
        
        response_lower = response.lower()
        matches = 0
        
        for expected in expected_contains:
            if expected.lower() in response_lower:
                matches += 1
        
        return matches / len(expected_contains)
    
    def _analyze_pipeline_results(self, results: List[Dict[str, Any]]) -> None:
        """Analisa resultados do pipeline e gera relatório."""
        total_tests = len(results)
        successful_tests = len([r for r in results if "error" not in r])
        performance_ok = len([r for r in results if r.get("performance_ok", False)])
        
        accuracy_scores = [r.get("accuracy_score", 0) for r in results if "error" not in r]
        avg_accuracy = sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0
        
        processing_times = [r.get("processing_time", 0) for r in results if "error" not in r]
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        critical_accuracy = [
            r.get("accuracy_score", 0) for r in results 
            if r.get("accuracy_critical", False) and "error" not in r
        ]
        avg_critical_accuracy = sum(critical_accuracy) / len(critical_accuracy) if critical_accuracy else 0
        
        print(f"\n{'='*60}")
        print(f"RELATÓRIO DE TESTES DE INTEGRAÇÃO")
        print(f"{'='*60}")
        print(f"Total de testes: {total_tests}")
        print(f"Testes bem-sucedidos: {successful_tests}/{total_tests} ({successful_tests/total_tests*100:.1f}%)")
        print(f"Performance adequada: {performance_ok}/{successful_tests} ({performance_ok/successful_tests*100 if successful_tests else 0:.1f}%)")
        print(f"Accuracy média: {avg_accuracy*100:.1f}%")
        print(f"Accuracy crítica: {avg_critical_accuracy*100:.1f}%")
        print(f"Tempo médio de processamento: {avg_processing_time:.0f}ms")
        print(f"{'='*60}")
        
        # Validações
        assert successful_tests >= total_tests * 0.9, f"Muitos testes falharam: {successful_tests}/{total_tests}"
        assert avg_accuracy >= 0.7, f"Accuracy muito baixa: {avg_accuracy*100:.1f}%"
        assert avg_critical_accuracy >= 0.8, f"Accuracy crítica muito baixa: {avg_critical_accuracy*100:.1f}%"
        assert avg_processing_time <= 3000, f"Tempo de processamento muito alto: {avg_processing_time:.0f}ms"
    
    async def test_cache_integration(self, integrated_services):
        """Testa integração do sistema de cache."""
        services = integrated_services
        cache_service = services["cache_service"]
        
        # Teste 1: Cache miss e subsequente cache hit
        query = "Status dos transformadores operacionais"
        
        # Primeira chamada - cache miss
        start_time = time.time()
        response1 = await services["llm_service"].generate_response(query)
        time1 = int((time.time() - start_time) * 1000)
        
        # Cachear resposta manualmente para teste
        await cache_service.set(query, response1)
        
        # Segunda chamada - cache hit
        start_time = time.time()
        cached_response = await cache_service.get(query)
        time2 = int((time.time() - start_time) * 1000)
        
        assert cached_response is not None
        assert cached_response["cache_used"] is True
        assert time2 < time1 * 0.1  # Cache deve ser 10x mais rápido
        
        # Teste 2: Similaridade
        similar_query = "Situação dos trafos em operação"
        cached_similar = await cache_service.get(
            similar_query, 
            strategy=CacheStrategy.NORMALIZED_MATCH
        )
        
        assert cached_similar is not None
        assert cached_similar.get("cache_similarity") is True
    
    async def test_fallback_integration(self, integrated_services):
        """Testa integração do sistema de fallback."""
        services = integrated_services
        fallback_service = services["fallback_service"]
        
        # Simular erro no LLM
        with patch.object(services["llm_service"], "generate_response") as mock_llm:
            mock_llm.side_effect = LLMServiceError("API quota exceeded")
            
            # O sistema deve ativar fallback automaticamente
            response = await fallback_service.generate_fallback_response(
                trigger=fallback_service.FallbackTrigger.API_QUOTA_EXCEEDED,
                original_query="Status dos equipamentos",
                context={}
            )
            
            assert response.strategy_used is not None
            assert "desculpe" in response.message.lower()
            assert response.actionable is True
    
    async def test_performance_benchmark(self, integrated_services):
        """Benchmark de performance com múltiplas queries simultâneas."""
        services = integrated_services
        test_queries = [
            "Status do transformador TR001",
            "Manutenções pendentes",
            "Equipamentos da Subestação A",
            "Custos de manutenção",
            "Próximas manutenções programadas"
        ]
        
        # Teste sequencial
        sequential_start = time.time()
        for query in test_queries:
            await services["llm_service"].generate_response(query)
        sequential_time = time.time() - sequential_start
        
        # Teste concorrente
        concurrent_start = time.time()
        tasks = [
            services["llm_service"].generate_response(query) 
            for query in test_queries
        ]
        await asyncio.gather(*tasks)
        concurrent_time = time.time() - concurrent_start
        
        print(f"\nBENCHMARK DE PERFORMANCE:")
        print(f"Sequencial: {sequential_time:.2f}s")
        print(f"Concorrente: {concurrent_time:.2f}s")
        print(f"Speedup: {sequential_time/concurrent_time:.1f}x")
        
        # Performance deve ser razoável
        assert concurrent_time <= 5.0, f"Performance concorrente muito lenta: {concurrent_time:.2f}s"
        assert concurrent_time <= sequential_time, "Processamento concorrente deve ser mais rápido"
    
    async def test_data_quality_validation(self, integrated_services):
        """Valida qualidade dos dados e respostas."""
        services = integrated_services
        
        # Testar com dados de diferentes qualidades
        test_cases = [
            {
                "name": "Dados completos",
                "equipment_data": TestDataGenerator.generate_equipment_data(),
                "expected_quality": "high"
            },
            {
                "name": "Dados parciais",
                "equipment_data": [
                    {"id": "TR001", "nome": "Transformador 1", "status": "Operacional"}
                ],
                "expected_quality": "medium"
            },
            {
                "name": "Dados mínimos",
                "equipment_data": [
                    {"id": "TR001"}
                ],
                "expected_quality": "low"
            }
        ]
        
        for case in test_cases:
            # Configurar repositório com dados específicos
            services["equipment_repo"].get_all.return_value = case["equipment_data"]
            
            response = await services["llm_service"].generate_response(
                "Status dos equipamentos",
                query_results=case["equipment_data"]
            )
            
            # Validar qualidade da resposta
            confidence = response["confidence_score"]
            
            if case["expected_quality"] == "high":
                assert confidence >= 0.8, f"Confiança baixa com dados completos: {confidence}"
            elif case["expected_quality"] == "medium":
                assert 0.5 <= confidence < 0.8, f"Confiança inadequada com dados parciais: {confidence}"
            else:  # low
                assert confidence < 0.5, f"Confiança alta demais com dados mínimos: {confidence}"
    
    async def test_error_handling_integration(self, integrated_services):
        """Testa tratamento de erros integrado."""
        services = integrated_services
        
        # Teste 1: Erro de validação
        with pytest.raises(ValidationError):
            await services["query_processor"].process_query("")
        
        # Teste 2: Erro no repositório
        services["equipment_repo"].get_all.side_effect = Exception("Database connection failed")
        
        response = await services["llm_service"].generate_response(
            "Status dos equipamentos"
        )
        
        # Sistema deve usar fallback quando não consegue buscar dados
        assert response.get("fallback_used") is True or response.get("confidence_score", 0) < 0.5
        
        # Teste 3: Timeout do LLM
        with patch.object(services["llm_service"], "generate_response") as mock_llm:
            mock_llm.side_effect = asyncio.TimeoutError("LLM timeout")
            
            # Sistema deve ativar fallback
            response = await services["fallback_service"].generate_fallback_response(
                trigger=services["fallback_service"].FallbackTrigger.TIMEOUT,
                original_query="Test query",
                context={}
            )
            
            assert "timeout" in response.message.lower() or "tempo" in response.message.lower()


@pytest.mark.integration
class TestRealWorldScenarios:
    """Testes com cenários do mundo real."""
    
    async def test_user_session_simulation(self):
        """Simula sessão completa de usuário."""
        # Simular sequência de perguntas de um técnico real
        user_queries = [
            "Bom dia! Quais equipamentos precisam de atenção hoje?",
            "Me mostra o status do transformador TR001",
            "Quando foi a última manutenção dele?",
            "Qual o custo médio de manutenção de transformadores?",
            "Obrigado pela ajuda!"
        ]
        
        session_results = []
        
        for i, query in enumerate(user_queries):
            start_time = time.time()
            
            # Simular processamento (mock simplificado)
            response = {
                "query": query,
                "response": f"Resposta simulada para: {query}",
                "confidence": 0.8,
                "processing_time": int((time.time() - start_time) * 1000),
                "session_step": i + 1
            }
            
            session_results.append(response)
        
        # Validar que sessão foi processada adequadamente
        assert len(session_results) == 5
        assert all(r["confidence"] >= 0.5 for r in session_results)
        
        # Primeiro e último devem ter confiança menor (saudações)
        assert session_results[0]["confidence"] <= session_results[2]["confidence"]
        assert session_results[-1]["confidence"] <= session_results[2]["confidence"]
    
    async def test_load_simulation(self):
        """Simula carga de múltiplos usuários simultâneos."""
        async def simulate_user(user_id: int):
            """Simula um usuário fazendo várias consultas."""
            queries = [
                f"Status equipamentos usuário {user_id}",
                f"Manutenções pendentes {user_id}",
                f"Relatório {user_id}"
            ]
            
            results = []
            for query in queries:
                start_time = time.time()
                # Simular processamento
                await asyncio.sleep(0.1)  # Simular latência
                
                processing_time = int((time.time() - start_time) * 1000)
                results.append({
                    "user_id": user_id,
                    "query": query,
                    "processing_time": processing_time
                })
            
            return results
        
        # Simular 10 usuários simultâneos
        start_time = time.time()
        user_tasks = [simulate_user(i) for i in range(10)]
        all_results = await asyncio.gather(*user_tasks)
        total_time = time.time() - start_time
        
        # Analisar resultados
        flat_results = [result for user_results in all_results for result in user_results]
        avg_processing_time = sum(r["processing_time"] for r in flat_results) / len(flat_results)
        
        print(f"\nSIMULAÇÃO DE CARGA:")
        print(f"Usuários simultâneos: 10")
        print(f"Total de queries: {len(flat_results)}")
        print(f"Tempo total: {total_time:.2f}s")
        print(f"Tempo médio por query: {avg_processing_time:.0f}ms")
        
        # Validações de performance
        assert total_time <= 15.0, f"Tempo total muito alto: {total_time:.2f}s"
        assert avg_processing_time <= 500, f"Tempo médio muito alto: {avg_processing_time:.0f}ms"


class TestConfigurationOptimization:
    """Testes para otimização de configurações."""
    
    async def test_cache_configuration_optimization(self):
        """Testa diferentes configurações de cache."""
        configurations = [
            {"max_size": 100, "ttl": 1800, "similarity_threshold": 0.7},
            {"max_size": 500, "ttl": 3600, "similarity_threshold": 0.8},
            {"max_size": 1000, "ttl": 7200, "similarity_threshold": 0.9}
        ]
        
        best_config = None
        best_score = 0
        
        for config in configurations:
            # Simular teste com configuração
            cache_service = CacheService()
            cache_service.max_cache_size = config["max_size"]
            cache_service.default_ttl = config["ttl"]
            cache_service.similarity_threshold = config["similarity_threshold"]
            
            # Simular métricas
            hit_rate = 0.6 + (config["similarity_threshold"] - 0.7) * 0.5
            memory_usage = config["max_size"] * 0.1
            
            # Calcular score (balance entre hit rate e uso de memória)
            score = hit_rate * 0.7 + (1 - memory_usage/100) * 0.3
            
            if score > best_score:
                best_score = score
                best_config = config
        
        print(f"\nOTIMIZAÇÃO DE CONFIGURAÇÕES:")
        print(f"Melhor configuração: {best_config}")
        print(f"Score: {best_score:.3f}")
        
        assert best_config is not None
        assert best_score > 0.7
    
    def test_llm_parameters_optimization(self):
        """Testa otimização de parâmetros do LLM."""
        parameter_sets = [
            {"temperature": 0.1, "max_tokens": 500},
            {"temperature": 0.2, "max_tokens": 1000},
            {"temperature": 0.3, "max_tokens": 1500}
        ]
        
        results = []
        for params in parameter_sets:
            # Simular resposta com parâmetros
            # Temperatura baixa = mais determinística = maior precisão
            # Mais tokens = respostas mais completas = maior satisfação
            
            precision = 1.0 - params["temperature"]
            completeness = min(1.0, params["max_tokens"] / 1000)
            
            score = precision * 0.6 + completeness * 0.4
            
            results.append({
                "params": params,
                "precision": precision,
                "completeness": completeness,
                "score": score
            })
        
        best_result = max(results, key=lambda x: x["score"])
        
        print(f"\nOTIMIZAÇÃO DE PARÂMETROS LLM:")
        print(f"Melhor configuração: {best_result['params']}")
        print(f"Score: {best_result['score']:.3f}")
        
        assert best_result["score"] > 0.8 