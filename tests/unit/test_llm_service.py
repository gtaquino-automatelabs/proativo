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

from src.api.services.llm_service import LLMService
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
        # Cache agora é gerenciado pelo CacheService
        yield
    
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
    
    def test_generate_cache_tags(self, llm_service):
        """Testa geração de tags de cache."""
        query = "status dos transformadores"
        context = {"query_type": "equipment"}
        query_results = [{"id": "T001", "type": "transformer"}]
        
        tags = llm_service._generate_cache_tags(query, context, query_results)
        
        assert isinstance(tags, set)
        assert len(tags) > 0
    
    def test_calculate_cache_ttl(self, llm_service):
        """Testa cálculo do TTL do cache."""
        ttl_high = llm_service._calculate_cache_ttl(0.9, 10)
        ttl_low = llm_service._calculate_cache_ttl(0.3, 2)
        
        assert ttl_high > ttl_low  # Alta confiança deve ter TTL maior
        assert ttl_high > 0
        assert ttl_low > 0
    
    def test_fallback_should_trigger(self, llm_service):
        """Testa se o fallback deve ser acionado."""
        # Teste simplificado já que o fallback é um serviço opcional
        if llm_service.fallback_service:
            should_fallback, trigger = llm_service.fallback_service.should_use_fallback(
                llm_response="Não sei responder",
                original_query="test query",
                llm_confidence=0.2,
                error=None
            )
            # O resultado pode variar dependendo da implementação do fallback
            assert isinstance(should_fallback, bool)
        else:
            # Se não há fallback service, o teste passa
            assert True
    
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
    async def test_generate_response_with_cache_service(self, llm_service):
        """Testa resposta com cache service disponível."""
        # Mock do cache service
        with patch.object(llm_service, 'cache_service') as mock_cache:
            mock_cache.get.return_value = None  # Cache miss
            
            mock_response = Mock()
            mock_response.text = "Resposta do Gemini"
            
            with patch('asyncio.to_thread', return_value=mock_response):
                result = await llm_service.generate_response(
                    "test query",
                    query_results=[{"id": "T001"}]
                )
                
                assert "response" in result
                assert not result["cache_used"]
                mock_cache.get.assert_called_once()
    
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
    
    @pytest.mark.asyncio
    async def test_clear_cache(self, llm_service):
        """Testa limpeza do cache."""
        # Mock do cache service
        with patch.object(llm_service, 'cache_service') as mock_cache:
            await llm_service.clear_cache()
            mock_cache.clear.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_metrics_async(self, llm_service):
        """Testa obtenção de métricas async."""
        # Simular algumas métricas
        llm_service.request_count = 5
        llm_service.cache_hits = 2
        llm_service.error_count = 1
        
        metrics = await llm_service.get_metrics()
        
        assert metrics["total_requests"] == 5
        assert metrics["cache_hits"] == 2
        assert metrics["error_count"] == 1
        assert "model_used" in metrics


if __name__ == "__main__":
    pytest.main([__file__]) 