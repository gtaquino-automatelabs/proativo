"""
Testes unitários para o CacheService.

Este módulo testa todas as funcionalidades do sistema de cache inteligente:
- Normalização de queries
- Detecção de similaridade
- Operações básicas de cache (get/set)
- Limpeza automática e eviction
- Invalidação por critérios
- Métricas e health check
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock

from src.api.services.cache_service import (
    CacheService, 
    QueryNormalizer, 
    CacheEntry, 
    CacheStrategy,
    CacheStatus
)


class TestQueryNormalizer:
    """Testes para o normalizador de consultas."""
    
    @pytest.fixture
    def normalizer(self):
        """Fixture com normalizador inicializado."""
        return QueryNormalizer()
    
    def test_normalize_basic_query(self, normalizer):
        """Testa normalização básica de consulta."""
        query = "Mostre os TRANSFORMADORES com problemas"
        normalized = normalizer.normalize(query)
        
        # Deve remover stop words e normalizar para lowercase
        assert "mostre" not in normalized
        assert "os" not in normalized  
        assert "com" not in normalized
        assert "transformador" in normalized
        assert "problema" in normalized
    
    def test_normalize_with_synonyms(self, normalizer):
        """Testa normalização com expansão de sinônimos."""
        query1 = "Status dos trafos principais"
        query2 = "Situação dos transformadores principais"
        
        norm1 = normalizer.normalize(query1)
        norm2 = normalizer.normalize(query2)
        
        # Ambas devem conter "transformador" e "status"
        assert "transformador" in norm1
        assert "transformador" in norm2
        assert "status" in norm1
        assert "status" in norm2
    
    def test_normalize_with_numbers_and_dates(self, normalizer):
        """Testa normalização de números e datas."""
        query = "Equipamento TR123 com falha em 2024-01-15"
        normalized = normalizer.normalize(query)
        
        # Números e datas devem ser generalizados
        assert "ID_EQUIPAMENTO" in normalized
        assert "DATA" in normalized
        assert "TR123" not in normalized
        assert "2024-01-15" not in normalized
    
    def test_calculate_similarity_identical(self, normalizer):
        """Testa similaridade de queries idênticas."""
        query1 = "Status dos transformadores"
        query2 = "Status dos transformadores"
        
        similarity = normalizer.calculate_similarity(query1, query2)
        assert similarity == 1.0
    
    def test_calculate_similarity_synonyms(self, normalizer):
        """Testa similaridade com sinônimos."""
        query1 = "Status dos trafos"
        query2 = "Situação dos transformadores"
        
        similarity = normalizer.calculate_similarity(query1, query2)
        assert similarity > 0.8  # Deve ser alta similaridade
    
    def test_calculate_similarity_different(self, normalizer):
        """Testa similaridade de queries diferentes."""
        query1 = "Status dos transformadores"
        query2 = "Custos de manutenção"
        
        similarity = normalizer.calculate_similarity(query1, query2)
        assert similarity < 0.3  # Deve ser baixa similaridade
    
    def test_normalize_empty_query(self, normalizer):
        """Testa normalização de query vazia."""
        assert normalizer.normalize("") == ""
        assert normalizer.normalize("   ") == ""
        assert normalizer.normalize(None) == ""
    
    def test_normalize_order_independence(self, normalizer):
        """Testa que ordem das palavras não afeta normalização."""
        query1 = "transformador gerador status"
        query2 = "status gerador transformador"
        
        norm1 = normalizer.normalize(query1)
        norm2 = normalizer.normalize(query2)
        
        # Normalizações devem ser iguais (palavras ordenadas)
        assert norm1 == norm2


class TestCacheEntry:
    """Testes para CacheEntry."""
    
    @pytest.fixture
    def cache_entry(self):
        """Fixture com entrada de cache."""
        return CacheEntry(
            key="test_key",
            original_query="test query",
            normalized_query="test query",
            response={"answer": "test response"},
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            access_count=1,
            ttl_seconds=3600,
            tags={"test"},
            confidence_score=0.8
        )
    
    def test_cache_entry_creation(self, cache_entry):
        """Testa criação de entrada do cache."""
        assert cache_entry.key == "test_key"
        assert cache_entry.original_query == "test query"
        assert cache_entry.access_count == 1
        assert cache_entry.confidence_score == 0.8
    
    def test_cache_entry_expiration(self):
        """Testa lógica de expiração."""
        # Entrada expirada
        expired_entry = CacheEntry(
            key="expired",
            original_query="test",
            normalized_query="test",
            response={},
            created_at=datetime.now() - timedelta(hours=2),
            last_accessed=datetime.now(),
            access_count=1,
            ttl_seconds=3600,  # 1 hora
            tags=set(),
            confidence_score=0.5
        )
        
        assert expired_entry.is_expired
        assert expired_entry.status == CacheStatus.EXPIRED
    
    def test_cache_entry_stale(self):
        """Testa lógica de entrada obsoleta."""
        # Entrada obsoleta (75% do TTL)
        stale_entry = CacheEntry(
            key="stale",
            original_query="test",
            normalized_query="test",
            response={},
            created_at=datetime.now() - timedelta(minutes=46),  # 76% de 1 hora
            last_accessed=datetime.now(),
            access_count=1,
            ttl_seconds=3600,
            tags=set(),
            confidence_score=0.5
        )
        
        assert stale_entry.is_stale
        assert not stale_entry.is_expired
        assert stale_entry.status == CacheStatus.STALE
    
    def test_cache_entry_fresh(self, cache_entry):
        """Testa entrada fresca."""
        assert not cache_entry.is_expired
        assert not cache_entry.is_stale
        assert cache_entry.status == CacheStatus.FRESH
    
    def test_cache_entry_update_access(self, cache_entry):
        """Testa atualização de acesso."""
        old_count = cache_entry.access_count
        old_time = cache_entry.last_accessed
        
        cache_entry.update_access()
        
        assert cache_entry.access_count == old_count + 1
        assert cache_entry.last_accessed > old_time


class TestCacheService:
    """Testes para o CacheService principal."""
    
    @pytest.fixture
    async def cache_service(self):
        """Fixture com CacheService inicializado."""
        with patch('src.api.services.cache_service.get_settings') as mock_settings:
            mock_settings.return_value = Mock(
                gemini_model="gemini-2.5-flash",
                gemini_temperature=0.2
            )
            
            service = CacheService()
            # Não iniciar task de limpeza automática nos testes
            service._start_cleanup_task = Mock()
            yield service
            
            # Limpar cache após teste
            await service.clear()
    
    async def test_cache_service_initialization(self, cache_service):
        """Testa inicialização do CacheService."""
        assert cache_service.max_cache_size == 1000
        assert cache_service.default_ttl == 3600
        assert cache_service.similarity_threshold == 0.8
        assert len(cache_service.cache) == 0
    
    async def test_cache_set_and_get_exact_match(self, cache_service):
        """Testa set e get com correspondência exata."""
        query = "Status dos transformadores"
        response = {"answer": "Todos funcionando", "confidence": 0.9}
        context = {"user_type": "technician"}
        
        # Armazenar no cache
        cache_key = await cache_service.set(
            query=query,
            response=response,
            context=context
        )
        
        assert cache_key is not None
        assert len(cache_service.cache) == 1
        
        # Buscar do cache
        cached_response = await cache_service.get(
            query=query,
            context=context,
            strategy=CacheStrategy.EXACT_MATCH
        )
        
        assert cached_response is not None
        assert cached_response["answer"] == "Todos funcionando"
        assert cached_response["cache_used"] is True
    
    async def test_cache_get_similar_match(self, cache_service):
        """Testa busca por similaridade."""
        # Armazenar uma resposta
        await cache_service.set(
            query="Status dos transformadores principais",
            response={"answer": "Funcionando normalmente"},
            context={}
        )
        
        # Buscar com query similar
        cached_response = await cache_service.get(
            query="Situação dos trafos principais",
            context={},
            strategy=CacheStrategy.NORMALIZED_MATCH
        )
        
        assert cached_response is not None
        assert cached_response["cache_similarity"] is True
        assert cached_response["answer"] == "Funcionando normalmente"
    
    async def test_cache_miss(self, cache_service):
        """Testa cache miss."""
        # Buscar query que não existe
        cached_response = await cache_service.get(
            query="Query que não existe no cache",
            context={},
            strategy=CacheStrategy.NORMALIZED_MATCH
        )
        
        assert cached_response is None
    
    async def test_cache_with_ttl(self, cache_service):
        """Testa TTL customizado."""
        query = "Test query"
        response = {"answer": "Test response"}
        
        # Armazenar com TTL baixo
        await cache_service.set(
            query=query,
            response=response,
            ttl=1  # 1 segundo
        )
        
        # Deve estar no cache inicialmente
        cached = await cache_service.get(query=query)
        assert cached is not None
        
        # Aguardar expiração
        await asyncio.sleep(1.1)
        
        # Deve estar expirado
        cached = await cache_service.get(query=query)
        assert cached is None
    
    async def test_cache_with_tags(self, cache_service):
        """Testa cache com tags."""
        await cache_service.set(
            query="Query com tags",
            response={"answer": "Response"},
            tags={"transformador", "status"}
        )
        
        assert len(cache_service.cache) == 1
        
        # Verificar se tags foram armazenadas
        entry = list(cache_service.cache.values())[0]
        assert "transformador" in entry.tags
        assert "status" in entry.tags
    
    async def test_cache_eviction(self, cache_service):
        """Testa remoção de entradas por tamanho."""
        # Definir tamanho máximo baixo
        cache_service.max_cache_size = 3
        
        # Adicionar mais entradas que o máximo
        for i in range(5):
            await cache_service.set(
                query=f"Query {i}",
                response={"answer": f"Response {i}"}
            )
        
        # Deve manter apenas 3 entradas
        assert len(cache_service.cache) <= 3
    
    async def test_cache_invalidation_by_pattern(self, cache_service):
        """Testa invalidação por padrão regex."""
        # Adicionar várias entradas
        await cache_service.set("Status transformador TR1", {"answer": "OK"})
        await cache_service.set("Status transformador TR2", {"answer": "OK"})
        await cache_service.set("Custo manutenção", {"answer": "R$ 1000"})
        
        assert len(cache_service.cache) == 3
        
        # Invalidar entradas com "transformador"
        invalidated = await cache_service.invalidate(pattern="transformador")
        
        assert invalidated == 2
        assert len(cache_service.cache) == 1
    
    async def test_cache_invalidation_by_tags(self, cache_service):
        """Testa invalidação por tags."""
        await cache_service.set(
            "Query 1", 
            {"answer": "Answer 1"}, 
            tags={"transformador"}
        )
        await cache_service.set(
            "Query 2", 
            {"answer": "Answer 2"}, 
            tags={"gerador"}
        )
        await cache_service.set(
            "Query 3", 
            {"answer": "Answer 3"}, 
            tags={"transformador", "status"}
        )
        
        # Invalidar por tag "transformador"
        invalidated = await cache_service.invalidate(tags={"transformador"})
        
        assert invalidated == 2
        assert len(cache_service.cache) == 1
    
    async def test_cache_invalidation_by_age(self, cache_service):
        """Testa invalidação por idade."""
        # Adicionar entrada com data passada
        old_time = datetime.now() - timedelta(hours=2)
        
        # Mock da entrada antiga
        with patch('src.api.services.cache_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = old_time
            
            await cache_service.set(
                "Old query",
                {"answer": "Old response"}
            )
        
        # Adicionar entrada nova
        await cache_service.set(
            "New query",
            {"answer": "New response"}
        )
        
        assert len(cache_service.cache) == 2
        
        # Invalidar entradas mais antigas que 1 hora
        older_than = datetime.now() - timedelta(hours=1)
        invalidated = await cache_service.invalidate(older_than=older_than)
        
        assert invalidated == 1
        assert len(cache_service.cache) == 1
    
    async def test_cache_clear(self, cache_service):
        """Testa limpeza completa do cache."""
        # Adicionar várias entradas
        for i in range(5):
            await cache_service.set(f"Query {i}", {"answer": f"Answer {i}"})
        
        assert len(cache_service.cache) == 5
        
        # Limpar cache
        await cache_service.clear()
        
        assert len(cache_service.cache) == 0
        assert len(cache_service.query_index) == 0
    
    async def test_cache_metrics(self, cache_service):
        """Testa coleta de métricas."""
        # Simular algumas operações
        cache_service.total_requests = 10
        cache_service.cache_hits = 3
        cache_service.cache_misses = 7
        
        # Adicionar algumas entradas
        await cache_service.set("Query 1", {"answer": "Answer 1"})
        await cache_service.set("Query 2", {"answer": "Answer 2"})
        
        metrics = await cache_service.get_metrics()
        
        assert metrics.total_requests == 10
        assert metrics.cache_hits == 3
        assert metrics.cache_misses == 7
        assert metrics.hit_rate == 0.3
        assert metrics.miss_rate == 0.7
        assert metrics.cache_size == 2
        assert metrics.max_cache_size == 1000
    
    async def test_cache_health_status(self, cache_service):
        """Testa health check do cache."""
        # Simular boa performance
        cache_service.total_requests = 100
        cache_service.cache_hits = 70
        cache_service.cache_misses = 30
        
        health = await cache_service.get_health_status()
        
        assert health["status"] == "healthy"
        assert health["hit_rate"] == 0.7
        assert "recommendations" in health
    
    async def test_cache_info_for_query(self, cache_service):
        """Testa informações de cache para query específica."""
        query = "Status dos equipamentos"
        
        # Query não existe no cache
        info = await cache_service.get_cache_info(query)
        
        assert info["exists_in_cache"] is False
        assert info["normalized_query"] is not None
        assert info["cache_key"] is not None
        
        # Adicionar query ao cache
        await cache_service.set(query, {"answer": "Todos OK"})
        
        # Verificar novamente
        info = await cache_service.get_cache_info(query)
        
        assert info["exists_in_cache"] is True
        assert "status" in info
        assert "created_at" in info
    
    async def test_generate_cache_tags(self, cache_service):
        """Testa geração de tags do cache."""
        query = "Status dos transformadores com falhas"
        context = {"query_type": "equipment_status"}
        query_results = [{"id": 1}, {"id": 2}]
        
        tags = cache_service._generate_cache_tags(query, context, query_results)
        
        assert "transformador" in tags
        assert "falha" in tags
        assert "status" in tags
        assert "type_equipment_status" in tags
        assert "with_data" in tags
    
    async def test_calculate_cache_ttl(self, cache_service):
        """Testa cálculo de TTL dinâmico."""
        # Alta confiança e muitos dados
        ttl_high = cache_service._calculate_cache_ttl(0.9, 50)
        
        # Baixa confiança e poucos dados
        ttl_low = cache_service._calculate_cache_ttl(0.3, 5)
        
        # TTL alto deve ser maior que TTL baixo
        assert ttl_high > ttl_low
        
        # Ambos devem estar dentro dos limites
        assert 1800 <= ttl_high <= 14400  # 30min - 4h
        assert 1800 <= ttl_low <= 14400
    
    async def test_cleanup_expired_entries(self, cache_service):
        """Testa limpeza automática de entradas expiradas."""
        # Adicionar entrada que expira rapidamente
        await cache_service.set(
            "Expiring query",
            {"answer": "Will expire"},
            ttl=1
        )
        
        assert len(cache_service.cache) == 1
        
        # Aguardar expiração
        await asyncio.sleep(1.1)
        
        # Executar limpeza manualmente
        await cache_service._cleanup_expired()
        
        assert len(cache_service.cache) == 0
    
    async def test_find_similar_entry(self, cache_service):
        """Testa busca de entrada similar."""
        # Adicionar entrada
        await cache_service.set(
            "Status dos transformadores principais",
            {"answer": "Funcionando"}
        )
        
        # Buscar similar
        similar = await cache_service._find_similar_entry(
            "Situação dos trafos principais",
            {}
        )
        
        assert similar is not None
        assert similar.original_query == "Status dos transformadores principais"
    
    async def test_cache_concurrent_access(self, cache_service):
        """Testa acesso concorrente ao cache."""
        async def add_entries(start_idx):
            """Adiciona entradas concorrentemente."""
            for i in range(start_idx, start_idx + 10):
                await cache_service.set(f"Query {i}", {"answer": f"Answer {i}"})
        
        # Executar múltiplas corrotinas concorrentemente
        await asyncio.gather(
            add_entries(0),
            add_entries(10),
            add_entries(20)
        )
        
        # Verificar que todas as entradas foram adicionadas
        assert len(cache_service.cache) == 30


@pytest.mark.integration
class TestCacheServiceIntegration:
    """Testes de integração para CacheService."""
    
    @pytest.fixture
    async def cache_service(self):
        """Cache service para testes de integração."""
        with patch('src.api.services.cache_service.get_settings') as mock_settings:
            mock_settings.return_value = Mock(
                gemini_model="gemini-2.5-flash",
                gemini_temperature=0.2
            )
            
            service = CacheService()
            service._start_cleanup_task = Mock()  # Desabilitar limpeza automática
            yield service
            await service.clear()
    
    async def test_real_world_scenario(self, cache_service):
        """Testa cenário do mundo real com múltiplas operações."""
        # Simular sessão de usuário com várias consultas
        
        # 1. Primeira consulta - cache miss
        query1 = "Quais transformadores precisam de manutenção?"
        response1 = {"answer": "TR1, TR2, TR3", "confidence": 0.9}
        
        cached = await cache_service.get(query1)
        assert cached is None  # Cache miss
        
        await cache_service.set(query1, response1, tags={"transformador", "manutencao"})
        
        # 2. Segunda consulta similar - cache hit por similaridade
        query2 = "Que trafos precisam de manutenção urgente?"
        
        cached = await cache_service.get(query2, strategy=CacheStrategy.NORMALIZED_MATCH)
        assert cached is not None  # Cache hit por similaridade
        assert cached["cache_similarity"] is True
        
        # 3. Consulta diferente - cache miss
        query3 = "Qual o custo total de manutenções este ano?"
        response3 = {"answer": "R$ 150.000", "confidence": 0.8}
        
        cached = await cache_service.get(query3)
        assert cached is None  # Cache miss
        
        await cache_service.set(query3, response3, tags={"custo", "manutencao"})
        
        # 4. Invalidar cache de transformadores
        invalidated = await cache_service.invalidate(tags={"transformador"})
        assert invalidated >= 1
        
        # 5. Verificar métricas finais
        metrics = await cache_service.get_metrics()
        assert metrics.total_requests >= 3
        assert metrics.cache_hits >= 1
        assert metrics.cache_misses >= 2
    
    async def test_performance_large_cache(self, cache_service):
        """Testa performance com cache grande."""
        import time
        
        # Adicionar muitas entradas
        start_time = time.time()
        
        for i in range(100):
            await cache_service.set(
                f"Query número {i} sobre equipamentos",
                {"answer": f"Resposta {i}", "confidence": 0.7}
            )
        
        add_time = time.time() - start_time
        
        # Buscar entradas
        start_time = time.time()
        
        for i in range(0, 100, 10):  # Buscar 10 entradas
            cached = await cache_service.get(f"Query número {i} sobre equipamentos")
            assert cached is not None
        
        get_time = time.time() - start_time
        
        # Performance deve ser razoável
        assert add_time < 5.0  # Menos de 5 segundos para adicionar 100 entradas
        assert get_time < 1.0   # Menos de 1 segundo para buscar 10 entradas
        
        print(f"Add time: {add_time:.2f}s, Get time: {get_time:.2f}s")
    
    async def test_memory_usage(self, cache_service):
        """Testa uso de memória do cache."""
        # Adicionar entradas com diferentes tamanhos
        small_response = {"answer": "OK"}
        large_response = {"answer": "A" * 1000, "details": ["Item"] * 100}
        
        await cache_service.set("Small query", small_response)
        await cache_service.set("Large query", large_response)
        
        metrics = await cache_service.get_metrics()
        
        # Verificar que métricas de memória fazem sentido
        assert metrics.memory_usage_mb > 0
        assert metrics.average_response_size > 0
        assert metrics.cache_size == 2
``` 