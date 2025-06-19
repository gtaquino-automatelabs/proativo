"""
Testes unitários para o LLMService.

Testa a integração com Google Gemini, cache, validação e tratamento de erros.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.api.services.llm_service import LLMService, RESPONSE_CACHE, CACHE_EXPIRY
from src.utils.error_handlers import LLMServiceError as LLMError, ValidationError


class TestLLMService:
    """Testes para o serviço LLM."""
    
    @pytest.fixture
    def llm_service(self):
        """Fixture para instância do LLMService."""
        with patch('src.api.services.llm_service.genai.configure'), \
             patch('src.api.services.llm_service.genai.GenerativeModel') as mock_model, \
             patch('src.api.services.llm_service.get_settings') as mock_settings:
            
            # Mock das configurações
            settings = Mock()
            settings.gemini_api_key = "test_api_key"
            settings.gemini_model = "gemini-2.5-flash"
            settings.gemini_temperature = 0.1
            settings.gemini_max_tokens = 2048
            settings.gemini_timeout = 30
            settings.gemini_max_retries = 3
            mock_settings.return_value = settings
            
            # Mock do modelo Gemini
            mock_instance = Mock()
            mock_model.return_value = mock_instance
            
            service = LLMService()
            service._model = mock_instance
            return service
    
    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Limpa cache antes de cada teste."""
        RESPONSE_CACHE.clear()
        CACHE_EXPIRY.clear()
        yield
        RESPONSE_CACHE.clear()
        CACHE_EXPIRY.clear()
    
    def test_initialize_gemini_success(self):
        """Testa inicialização bem-sucedida do Gemini."""
        with patch('src.api.services.llm_service.genai.configure') as mock_configure, \
             patch('src.api.services.llm_service.genai.GenerativeModel') as mock_model, \
             patch('src.api.services.llm_service.get_settings') as mock_settings:
            
            # Mock das configurações
            settings = Mock()
            settings.gemini_api_key = "test_api_key"
            settings.gemini_model = "gemini-2.5-flash"
            settings.gemini_temperature = 0.1
            settings.gemini_max_tokens = 2048
            mock_settings.return_value = settings
            
            service = LLMService()
            
            # Verificar chamadas
            mock_configure.assert_called_once_with(api_key="test_api_key")
            mock_model.assert_called_once()
    
    def test_initialize_gemini_no_api_key(self):
        """Testa inicialização sem API key."""
        with patch('src.api.services.llm_service.get_settings') as mock_settings:
            settings = Mock()
            settings.gemini_api_key = None
            mock_settings.return_value = settings
            
            with pytest.raises(LLMError, match="Google API Key não configurada"):
                LLMService()
    
    def test_generate_cache_key(self, llm_service):
        """Testa geração de chave de cache."""
        query = "test query"
        context = {"key": "value"}
        
        key1 = llm_service._generate_cache_key(query, context)
        key2 = llm_service._generate_cache_key(query, context)
        key3 = llm_service._generate_cache_key("different query", context)
        
        assert key1 == key2  # Mesma entrada deve gerar mesma chave
        assert key1 != key3  # Entradas diferentes devem gerar chaves diferentes
        assert len(key1) == 32  # Hash MD5 tem 32 caracteres
    
    def test_cache_response_and_retrieval(self, llm_service):
        """Testa armazenamento e recuperação do cache."""
        cache_key = "test_key"
        response = {"response": "test response", "confidence": 0.8}
        
        # Armazenar no cache
        llm_service._cache_response(cache_key, response)
        
        # Recuperar do cache
        cached = llm_service._get_cached_response(cache_key)
        
        assert cached == response
        assert llm_service.cache_hits == 1
    
    def test_cache_expiry(self, llm_service):
        """Testa expiração do cache."""
        cache_key = "test_key"
        response = {"response": "test response"}
        
        # Armazenar no cache com tempo expirado
        RESPONSE_CACHE[cache_key] = response
        CACHE_EXPIRY[cache_key] = datetime.now() - timedelta(hours=2)
        
        # Tentar recuperar (deve retornar None por estar expirado)
        cached = llm_service._get_cached_response(cache_key)
        
        assert cached is None
        assert cache_key not in RESPONSE_CACHE  # Deve ter sido removido
    
    def test_create_system_prompt(self, llm_service):
        """Testa criação do prompt de sistema."""
        prompt = llm_service._create_system_prompt()
        
        assert "assistente especializado em manutenção" in prompt
        assert "português brasileiro" in prompt
        assert "PROAtivo" in prompt
        assert len(prompt) > 100  # Deve ser um prompt substantivo
    
    def test_create_user_prompt_with_data(self, llm_service):
        """Testa criação do prompt do usuário com dados."""
        user_query = "Quais equipamentos precisam manutenção?"
        retrieved_data = [
            {"id": "T001", "status": "maintenance_due"},
            {"id": "T002", "status": "operational"}
        ]
        context = {
            "total_equipment": 100,
            "last_update": "2024-01-15",
            "query_type": "maintenance"
        }
        
        prompt = llm_service._create_user_prompt(user_query, retrieved_data, context)
        
        assert user_query in prompt
        assert "DADOS ENCONTRADOS (2 registros)" in prompt
        assert "T001" in prompt
        assert "T002" in prompt
        assert "100" in prompt  # total_equipment
    
    def test_create_user_prompt_no_data(self, llm_service):
        """Testa criação do prompt do usuário sem dados."""
        user_query = "Teste sem dados"
        retrieved_data = []
        context = {}
        
        prompt = llm_service._create_user_prompt(user_query, retrieved_data, context)
        
        assert user_query in prompt
        assert "Nenhum registro específico encontrado" in prompt
    
    def test_validate_and_clean_response_success(self, llm_service):
        """Testa validação de resposta bem-sucedida."""
        response = "Esta é uma resposta válida do LLM."
        
        cleaned = llm_service._validate_and_clean_response(response)
        
        assert cleaned == response.strip()
    
    def test_validate_and_clean_response_empty(self, llm_service):
        """Testa validação de resposta vazia."""
        with pytest.raises(ValidationError, match="Resposta vazia do LLM"):
            llm_service._validate_and_clean_response("")
        
        with pytest.raises(ValidationError, match="Resposta vazia do LLM"):
            llm_service._validate_and_clean_response("   ")
    
    def test_validate_and_clean_response_too_short(self, llm_service):
        """Testa validação de resposta muito curta."""
        with pytest.raises(ValidationError, match="Resposta muito curta do LLM"):
            llm_service._validate_and_clean_response("ok")
    
    def test_validate_and_clean_response_too_long(self, llm_service):
        """Testa truncamento de resposta muito longa."""
        long_response = "a" * 6000  # Maior que o limite de 5000
        
        cleaned = llm_service._validate_and_clean_response(long_response)
        
        assert len(cleaned) <= 5000 + len("... [resposta truncada]")
        assert "resposta truncada" in cleaned
    
    def test_calculate_confidence_score_high(self, llm_service):
        """Testa cálculo de score de confiança alto."""
        user_query = "test query"
        retrieved_data = [{"id": "T001"}, {"id": "T002"}, {"id": "T003"}]
        response = "Esta é uma resposta detalhada e completa sobre os equipamentos encontrados."
        
        score = llm_service._calculate_confidence_score(user_query, retrieved_data, response)
        
        assert 0.6 <= score <= 1.0  # Deve ser alto
    
    def test_calculate_confidence_score_low(self, llm_service):
        """Testa cálculo de score de confiança baixo."""
        user_query = "test query"
        retrieved_data = []
        response = "Não sei responder essa pergunta."
        
        score = llm_service._calculate_confidence_score(user_query, retrieved_data, response)
        
        assert 0.0 <= score <= 0.4  # Deve ser baixo
    
    def test_generate_suggestions_equipment(self, llm_service):
        """Testa geração de sugestões para consultas sobre equipamentos."""
        user_query = "Status dos transformadores"
        query_results = [{"id": "T001"}]
        
        suggestions = llm_service._generate_suggestions(user_query, query_results)
        
        assert len(suggestions) <= 5
        assert any("histórico de manutenções" in s for s in suggestions)
        assert any("próxima manutenção" in s for s in suggestions)
    
    def test_generate_suggestions_maintenance(self, llm_service):
        """Testa geração de sugestões para consultas sobre manutenção."""
        user_query = "Manutenções pendentes"
        query_results = []
        
        suggestions = llm_service._generate_suggestions(user_query, query_results)
        
        assert len(suggestions) <= 5
        # Verificar se há sugestões relacionadas a manutenção
        suggestion_text = " ".join(suggestions).lower()
        assert any(keyword in suggestion_text for keyword in ["urgente", "custo", "manutenção", "equipamento", "status"])
    
    @pytest.mark.asyncio
    async def test_call_gemini_with_retry_success(self, llm_service):
        """Testa chamada bem-sucedida ao Gemini."""
        # Mock da resposta do Gemini
        mock_response = Mock()
        mock_response.text = "Resposta do Gemini"
        
        with patch('asyncio.to_thread', return_value=mock_response):
            result = await llm_service._call_gemini_with_retry("test prompt")
            
            assert result == "Resposta do Gemini"
    
    @pytest.mark.asyncio
    async def test_call_gemini_with_retry_timeout(self, llm_service):
        """Testa timeout na chamada ao Gemini."""
        with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError):
            with pytest.raises(LLMError, match="Timeout na tentativa"):
                await llm_service._call_gemini_with_retry("test prompt", max_retries=2)
    
    @pytest.mark.asyncio
    async def test_call_gemini_with_retry_empty_response(self, llm_service):
        """Testa resposta vazia do Gemini."""
        mock_response = Mock()
        mock_response.text = ""
        
        with patch('asyncio.to_thread', return_value=mock_response):
            with pytest.raises(LLMError, match="Resposta vazia do Gemini"):
                await llm_service._call_gemini_with_retry("test prompt")
    
    @pytest.mark.asyncio
    async def test_generate_response_success(self, llm_service):
        """Testa geração bem-sucedida de resposta."""
        # Mock da resposta do Gemini
        mock_response = Mock()
        mock_response.text = "Esta é uma resposta completa sobre equipamentos."
        
        with patch('asyncio.to_thread', return_value=mock_response):
            result = await llm_service.generate_response(
                user_query="Status dos equipamentos",
                query_results=[{"id": "T001", "status": "ok"}],
                context={"total_equipment": 10},
                session_id="test_session"
            )
            
            assert "response" in result
            assert "confidence_score" in result
            assert "sources" in result
            assert "suggestions" in result
            assert "processing_time" in result
            assert result["data_records_used"] == 1
            assert not result["cache_used"]
    
    @pytest.mark.asyncio
    async def test_generate_response_cached(self, llm_service):
        """Testa resposta servida do cache."""
        # Pré-popular cache
        cache_key = llm_service._generate_cache_key("test query", {})
        cached_response = {
            "response": "Resposta do cache",
            "confidence_score": 0.8,
            "cache_used": True
        }
        RESPONSE_CACHE[cache_key] = cached_response
        CACHE_EXPIRY[cache_key] = datetime.now() + timedelta(hours=1)
        
        result = await llm_service.generate_response("test query")
        
        assert result == cached_response
        assert llm_service.cache_hits == 1
    
    @pytest.mark.asyncio
    async def test_generate_response_empty_query(self, llm_service):
        """Testa erro com query vazia."""
        with pytest.raises(ValidationError, match="Query do usuário não pode estar vazia"):
            await llm_service.generate_response("")
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, llm_service):
        """Testa health check bem-sucedido."""
        mock_response = Mock()
        mock_response.text = "OK"
        
        with patch('asyncio.to_thread', return_value=mock_response):
            health = await llm_service.health_check()
            
            assert health["status"] == "healthy"
            assert health["gemini_available"] is True
            assert "metrics" in health
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, llm_service):
        """Testa health check com falha."""
        with patch('asyncio.to_thread', side_effect=Exception("Connection error")):
            health = await llm_service.health_check()
            
            assert health["status"] == "unhealthy"
            assert health["gemini_available"] is False
            assert "Connection error" in health["error"]
    
    def test_get_metrics(self, llm_service):
        """Testa obtenção de métricas."""
        # Simular algumas métricas
        llm_service.request_count = 10
        llm_service.cache_hits = 3
        llm_service.error_count = 1
        
        metrics = llm_service.get_metrics()
        
        assert metrics["total_requests"] == 10
        assert metrics["cache_hits"] == 3
        assert metrics["cache_hit_rate"] == 0.3
        assert metrics["error_count"] == 1
        assert metrics["error_rate"] == 0.1
        assert "model_used" in metrics
    
    def test_clear_cache(self, llm_service):
        """Testa limpeza do cache."""
        # Adicionar items no cache
        RESPONSE_CACHE["key1"] = {"response": "test1"}
        RESPONSE_CACHE["key2"] = {"response": "test2"}
        CACHE_EXPIRY["key1"] = datetime.now()
        CACHE_EXPIRY["key2"] = datetime.now()
        
        llm_service.clear_cache()
        
        assert len(RESPONSE_CACHE) == 0
        assert len(CACHE_EXPIRY) == 0
    
    def test_cache_size_limit(self, llm_service):
        """Testa limite de tamanho do cache."""
        # Definir limite baixo para teste
        llm_service.max_cache_size = 2
        
        # Adicionar itens além do limite
        llm_service._cache_response("key1", {"response": "test1"})
        llm_service._cache_response("key2", {"response": "test2"})
        llm_service._cache_response("key3", {"response": "test3"})  # Deve remover key1
        
        assert len(RESPONSE_CACHE) == 2
        assert "key1" not in RESPONSE_CACHE  # Mais antigo deve ter sido removido
        assert "key2" in RESPONSE_CACHE
        assert "key3" in RESPONSE_CACHE


if __name__ == "__main__":
    pytest.main([__file__]) 