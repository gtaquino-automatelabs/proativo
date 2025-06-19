"""
Testes unitários para o FallbackService.

Este módulo testa o sistema de fallback incluindo:
- Validação de respostas do LLM
- Geração de respostas de fallback
- Detecção de triggers
- Métricas e health check
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.api.services.fallback_service import (
    FallbackService, 
    FallbackTrigger, 
    FallbackStrategy,
    LLMResponseValidator,
    FallbackResponseGenerator,
    FallbackResponse,
    FallbackMetrics
)
from src.utils.error_handlers import LLMServiceError


class TestLLMResponseValidator:
    """Testes para o validador de respostas do LLM."""
    
    def setup_method(self):
        """Configuração dos testes."""
        self.validator = LLMResponseValidator()
    
    def test_valid_response_equipment_domain(self):
        """Testa validação de resposta válida no domínio de equipamentos."""
        response = "O transformador T001 está operacional e sua última manutenção foi realizada em janeiro de 2024."
        query = "Status do transformador T001"
        
        is_valid, trigger = self.validator.validate_response(response, query)
        
        assert is_valid
        assert trigger is None
    
    def test_empty_response(self):
        """Testa detecção de resposta vazia."""
        response = ""
        query = "Status dos equipamentos"
        
        is_valid, trigger = self.validator.validate_response(response, query)
        
        assert not is_valid
        assert trigger == FallbackTrigger.EMPTY_RESPONSE
    
    def test_inadequate_response_patterns(self):
        """Testa detecção de padrões inadequados."""
        inadequate_responses = [
            "Não sei responder isso",
            "Desculpe, não consegui processar",
            "Não tenho informação sobre isso",
            "Erro ao processar consulta"
        ]
        
        for response in inadequate_responses:
            is_valid, trigger = self.validator.validate_response(response, "teste query")
            assert not is_valid
            assert trigger == FallbackTrigger.INVALID_RESPONSE
    
    def test_out_of_domain_query(self):
        """Testa detecção de consultas fora do domínio."""
        out_of_domain_queries = [
            "Qual a melhor receita de bolo?",
            "Quem ganhou o jogo de futebol?",
            "Qual filme está passando no cinema?"
        ]
        
        for query in out_of_domain_queries:
            is_valid, trigger = self.validator.validate_response("Resposta qualquer", query)
            assert not is_valid
            assert trigger == FallbackTrigger.OUT_OF_DOMAIN
    
    def test_response_too_short(self):
        """Testa detecção de resposta muito curta."""
        short_response = "Ok"
        query = "Status dos transformadores"
        
        is_valid, trigger = self.validator.validate_response(short_response, query)
        
        assert not is_valid
        assert trigger == FallbackTrigger.EMPTY_RESPONSE
    
    def test_response_without_domain_keywords(self):
        """Testa resposta sem palavras-chave do domínio."""
        response = "Esta é uma resposta genérica sem termos técnicos específicos do setor elétrico."
        query = "Consulta sobre equipamentos"
        
        is_valid, trigger = self.validator.validate_response(response, query)
        
        assert not is_valid
        assert trigger == FallbackTrigger.OUT_OF_DOMAIN
    
    def test_valid_help_response(self):
        """Testa resposta de ajuda válida."""
        help_response = "Posso ajudar com consultas sobre equipamentos. Tente perguntar sobre status ou manutenções."
        query = "Como você pode me ajudar?"
        
        is_valid, trigger = self.validator.validate_response(help_response, query)
        
        assert is_valid
        assert trigger is None


class TestFallbackResponseGenerator:
    """Testes para o gerador de respostas de fallback."""
    
    def setup_method(self):
        """Configuração dos testes."""
        self.generator = FallbackResponseGenerator()
    
    def test_predefined_response_llm_error(self):
        """Testa geração de resposta predefinida para erro de LLM."""
        response = self.generator.generate_response(
            FallbackTrigger.LLM_ERROR, 
            "Consulta teste",
            FallbackStrategy.PREDEFINED_RESPONSE
        )
        
        assert isinstance(response, FallbackResponse)
        assert response.strategy_used == FallbackStrategy.PREDEFINED_RESPONSE
        assert response.trigger == FallbackTrigger.LLM_ERROR
        assert "dificuldades técnicas" in response.message.lower()
        assert len(response.suggestions) > 0
        assert response.confidence > 0.5
        assert response.actionable
    
    def test_template_based_response(self):
        """Testa resposta baseada em template."""
        # Query sobre manutenção deve usar template específico
        response = self.generator.generate_response(
            FallbackTrigger.UNSUPPORTED_QUERY,
            "Sobre manutenções preventivas",
            FallbackStrategy.TEMPLATE_BASED
        )
        
        assert response.strategy_used == FallbackStrategy.TEMPLATE_BASED
        assert "manutenção" in response.message.lower()
        assert len(response.suggestions) > 0
        assert "manutencoes" in response.metadata.get("category", "")
    
    def test_help_suggestions_response(self):
        """Testa resposta de sugestões de ajuda."""
        response = self.generator.generate_response(
            FallbackTrigger.UNSUPPORTED_QUERY,
            "Consulta desconhecida",
            FallbackStrategy.HELP_SUGGESTIONS
        )
        
        assert response.strategy_used == FallbackStrategy.HELP_SUGGESTIONS
        assert "🔧" in response.message or "equipamentos" in response.message.lower()
        assert len(response.suggestions) >= 3
        assert response.confidence >= 0.8
    
    def test_strategy_selection_out_of_domain(self):
        """Testa seleção automática de estratégia para consulta fora do domínio."""
        response = self.generator.generate_response(
            FallbackTrigger.OUT_OF_DOMAIN,
            "Receita de culinária"
        )
        
        assert response.strategy_used == FallbackStrategy.HELP_SUGGESTIONS
        assert "domínio" in response.message.lower()
    
    def test_strategy_selection_with_domain_keywords(self):
        """Testa seleção de estratégia com palavras-chave do domínio."""
        response = self.generator.generate_response(
            FallbackTrigger.UNSUPPORTED_QUERY,
            "Quero saber sobre status de equipamentos"
        )
        
        assert response.strategy_used == FallbackStrategy.TEMPLATE_BASED
        assert "status" in response.message.lower()
    
    def test_default_response_fallback(self):
        """Testa resposta padrão quando outras estratégias falham."""
        response = self.generator._generate_default_response(FallbackTrigger.LLM_ERROR)
        
        assert response.strategy_used == FallbackStrategy.PREDEFINED_RESPONSE
        assert response.confidence <= 0.6
        assert len(response.suggestions) > 0


class TestFallbackService:
    """Testes para o serviço principal de fallback."""
    
    def setup_method(self):
        """Configuração dos testes."""
        self.service = FallbackService()
    
    def test_should_use_fallback_with_llm_error(self):
        """Testa detecção de necessidade de fallback com erro do LLM."""
        error = LLMServiceError("API quota exceeded")
        
        should_fallback, trigger = self.service.should_use_fallback(
            llm_response=None,
            original_query="Consulta teste",
            error=error
        )
        
        assert should_fallback
        assert trigger == FallbackTrigger.API_QUOTA_EXCEEDED
    
    def test_should_use_fallback_with_timeout_error(self):
        """Testa detecção de timeout."""
        error = LLMServiceError("Request timeout")
        
        should_fallback, trigger = self.service.should_use_fallback(
            llm_response=None,
            original_query="Consulta teste",
            error=error
        )
        
        assert should_fallback
        assert trigger == FallbackTrigger.TIMEOUT
    
    def test_should_use_fallback_with_low_confidence(self):
        """Testa detecção de confiança baixa."""
        should_fallback, trigger = self.service.should_use_fallback(
            llm_response="Resposta com baixa confiança",
            original_query="Consulta teste",
            llm_confidence=0.2
        )
        
        assert should_fallback
        assert trigger == FallbackTrigger.LOW_CONFIDENCE
    
    def test_should_use_fallback_with_invalid_response(self):
        """Testa detecção de resposta inválida."""
        should_fallback, trigger = self.service.should_use_fallback(
            llm_response="Não sei responder isso",
            original_query="Status dos equipamentos"
        )
        
        assert should_fallback
        assert trigger == FallbackTrigger.INVALID_RESPONSE
    
    def test_should_not_use_fallback_with_good_response(self):
        """Testa que fallback não é ativado com resposta adequada."""
        good_response = "O equipamento T001 está operacional e foi inspecionado na última semana."
        
        should_fallback, trigger = self.service.should_use_fallback(
            llm_response=good_response,
            original_query="Status do equipamento T001",
            llm_confidence=0.8
        )
        
        assert not should_fallback
        assert trigger is None
    
    def test_generate_fallback_response(self):
        """Testa geração completa de resposta de fallback."""
        response = self.service.generate_fallback_response(
            trigger=FallbackTrigger.LLM_ERROR,
            original_query="Status dos transformadores"
        )
        
        assert isinstance(response, FallbackResponse)
        assert response.trigger == FallbackTrigger.LLM_ERROR
        assert len(response.message) > 0
        assert len(response.suggestions) > 0
        assert response.confidence > 0
        assert self.service.total_fallbacks == 1
        assert FallbackTrigger.LLM_ERROR.value in self.service.fallbacks_by_trigger
    
    def test_record_user_feedback(self):
        """Testa registro de feedback do usuário."""
        initial_scores = len(self.service.user_feedback_scores)
        
        self.service.record_user_feedback("response_123", 4, "Resposta útil")
        
        assert len(self.service.user_feedback_scores) == initial_scores + 1
        assert self.service.user_feedback_scores[-1] == 4
    
    def test_get_metrics(self):
        """Testa obtenção de métricas."""
        # Simular alguns fallbacks
        self.service.total_fallbacks = 10
        self.service.fallbacks_by_trigger = {"llm_error": 5, "timeout": 3, "low_confidence": 2}
        self.service.fallbacks_by_strategy = {"predefined_response": 6, "help_suggestions": 4}
        self.service.user_feedback_scores = [4, 3, 5, 2, 4]
        
        metrics = self.service.get_metrics()
        
        assert isinstance(metrics, FallbackMetrics)
        assert metrics.total_fallbacks == 10
        assert metrics.fallbacks_by_trigger["llm_error"] == 5
        assert metrics.success_rate > 0  # 3 scores >= 3 out of 5
        assert metrics.user_satisfaction > 0
    
    def test_get_health_status(self):
        """Testa verificação de saúde."""
        # Simular métricas positivas
        self.service.user_feedback_scores = [4, 4, 5, 3, 4]
        
        health = self.service.get_health_status()
        
        assert "status" in health
        assert health["status"] in ["healthy", "warning", "critical"]
        assert "user_satisfaction" in health
        assert "total_fallbacks" in health


class TestFallbackServiceIntegration:
    """Testes de integração do sistema de fallback."""
    
    def setup_method(self):
        """Configuração dos testes de integração."""
        self.service = FallbackService()
    
    def test_full_fallback_flow_llm_error(self):
        """Testa fluxo completo de fallback para erro de LLM."""
        # Simular erro de LLM
        error = LLMServiceError("Connection failed")
        
        # Verificar se deve usar fallback
        should_fallback, trigger = self.service.should_use_fallback(
            llm_response=None,
            original_query="Lista de equipamentos em manutenção",
            error=error
        )
        
        assert should_fallback
        assert trigger == FallbackTrigger.LLM_ERROR
        
        # Gerar resposta de fallback
        response = self.service.generate_fallback_response(
            trigger=trigger,
            original_query="Lista de equipamentos em manutenção"
        )
        
        assert response.trigger == FallbackTrigger.LLM_ERROR
        assert "dificuldades técnicas" in response.message.lower()
        assert len(response.suggestions) > 0
        assert response.actionable
        
        # Verificar métricas atualizadas
        metrics = self.service.get_metrics()
        assert metrics.total_fallbacks == 1
        assert "llm_error" in metrics.fallbacks_by_trigger
    
    def test_full_fallback_flow_out_of_domain(self):
        """Testa fluxo completo para consulta fora do domínio."""
        query = "Qual a receita do bolo de chocolate?"
        response = "Você vai precisar de chocolate, farinha, ovos..."
        
        # Verificar necessidade de fallback
        should_fallback, trigger = self.service.should_use_fallback(
            llm_response=response,
            original_query=query
        )
        
        assert should_fallback
        assert trigger == FallbackTrigger.OUT_OF_DOMAIN
        
        # Gerar resposta de fallback
        fallback_response = self.service.generate_fallback_response(
            trigger=trigger,
            original_query=query
        )
        
        assert "domínio" in fallback_response.message.lower()
        assert "equipamentos" in fallback_response.message.lower()
        assert FallbackStrategy.HELP_SUGGESTIONS == fallback_response.strategy_used
    
    def test_fallback_with_context(self):
        """Testa fallback com contexto adicional."""
        context = {
            "user_type": "engineer",
            "session_duration": 300,
            "previous_queries": 5
        }
        
        response = self.service.generate_fallback_response(
            trigger=FallbackTrigger.UNSUPPORTED_QUERY,
            original_query="Consulta complexa não suportada",
            context=context
        )
        
        assert response.metadata.get("original_query") == "Consulta complexa não suportada"
        assert len(response.suggestions) > 0
    
    def test_fallback_metrics_tracking(self):
        """Testa rastreamento de métricas durante fallbacks."""
        initial_fallbacks = self.service.total_fallbacks
        
        # Gerar vários fallbacks
        triggers = [
            FallbackTrigger.LLM_ERROR,
            FallbackTrigger.TIMEOUT, 
            FallbackTrigger.OUT_OF_DOMAIN,
            FallbackTrigger.LLM_ERROR
        ]
        
        for trigger in triggers:
            self.service.generate_fallback_response(trigger, f"Query for {trigger.value}")
        
        # Verificar métricas
        assert self.service.total_fallbacks == initial_fallbacks + 4
        assert self.service.fallbacks_by_trigger["llm_error"] == 2
        assert self.service.fallbacks_by_trigger["timeout"] == 1
        assert self.service.fallbacks_by_trigger["out_of_domain"] == 1
    
    def test_emergency_fallback(self):
        """Testa fallback de emergência quando sistema de fallback falha."""
        # Mockar erro no sistema de fallback
        with patch.object(self.service.response_generator, 'generate_response') as mock_gen:
            mock_gen.side_effect = Exception("Fallback system error")
            
            response = self.service.generate_fallback_response(
                trigger=FallbackTrigger.LLM_ERROR,
                original_query="Test query"
            )
            
            # Deve retornar resposta de emergência
            assert "dificuldades técnicas" in response.message.lower()
            assert response.confidence == 0.1
            assert not response.actionable
            assert response.metadata.get("emergency_fallback") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 