"""
Sistema de fallback para quando o LLM não consegue responder adequadamente.

Este módulo implementa estratégias de fallback quando:
- LLM retorna resposta inadequada ou vazia
- LLM não consegue processar a consulta
- Erro na comunicação com API externa
- Consulta está fora do domínio
"""

import re
import json
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import logging
from datetime import datetime

from ..config import get_settings
from ...utils.error_handlers import LLMServiceError, DataProcessingError
from ...utils.logger import get_logger

# Configurar logger
logger = get_logger(__name__)


class FallbackTrigger(Enum):
    """Triggers que ativam o sistema de fallback."""
    LLM_ERROR = "llm_error"
    EMPTY_RESPONSE = "empty_response"
    LOW_CONFIDENCE = "low_confidence"
    UNSUPPORTED_QUERY = "unsupported_query"
    TIMEOUT = "timeout"
    API_QUOTA_EXCEEDED = "api_quota_exceeded"
    INVALID_RESPONSE = "invalid_response"
    OUT_OF_DOMAIN = "out_of_domain"


class FallbackStrategy(Enum):
    """Estratégias de fallback disponíveis."""
    PREDEFINED_RESPONSE = "predefined_response"
    TEMPLATE_BASED = "template_based"
    RULE_BASED_SQL = "rule_based_sql"
    HELP_SUGGESTIONS = "help_suggestions"
    ESCALATION = "escalation"


@dataclass
class FallbackResponse:
    """Resposta do sistema de fallback."""
    message: str
    suggestions: List[str]
    strategy_used: FallbackStrategy
    trigger: FallbackTrigger
    confidence: float
    actionable: bool
    metadata: Dict[str, Any]


@dataclass
class FallbackMetrics:
    """Métricas do sistema de fallback."""
    total_fallbacks: int
    fallbacks_by_trigger: Dict[str, int]
    fallbacks_by_strategy: Dict[str, int]
    success_rate: float
    user_satisfaction: float


class LLMResponseValidator:
    """Validador de respostas do LLM para detectar necessidade de fallback."""
    
    def __init__(self):
        """Inicializa o validador de respostas."""
        # Padrões que indicam resposta inadequada
        self.inadequate_patterns = [
            r"não sei",
            r"não consigo",
            r"não tenho informação",
            r"não posso ajudar",
            r"desculpe",
            r"não entendi",
            r"não compreendo",
            r"erro",
            r"falha",
            r"indisponível"
        ]
        
        # Padrões que indicam consulta fora do domínio
        self.out_of_domain_patterns = [
            r"receita",
            r"culinária",
            r"esporte",
            r"política",
            r"entretenimento",
            r"filme",
            r"música",
            r"jogo"
        ]
        
        # Tamanho mínimo esperado para uma resposta útil
        self.min_response_length = 20
        
        # Palavras-chave do domínio que devem estar presentes
        self.domain_keywords = [
            "equipamento", "manutenção", "transformador", "gerador",
            "disjuntor", "falha", "custo", "status", "subestação"
        ]
    
    def validate_response(self, response: str, original_query: str) -> Tuple[bool, FallbackTrigger]:
        """
        Valida se a resposta do LLM é adequada.
        
        Args:
            response: Resposta do LLM
            original_query: Consulta original do usuário
            
        Returns:
            Tuple[bool, FallbackTrigger]: (é_válida, trigger_se_inválida)
        """
        if not response or not response.strip():
            return False, FallbackTrigger.EMPTY_RESPONSE
        
        response_lower = response.lower()
        query_lower = original_query.lower()
        
        # Verificar padrões inadequados
        for pattern in self.inadequate_patterns:
            if re.search(pattern, response_lower):
                return False, FallbackTrigger.INVALID_RESPONSE
        
        # Verificar se consulta está fora do domínio
        for pattern in self.out_of_domain_patterns:
            if re.search(pattern, query_lower):
                return False, FallbackTrigger.OUT_OF_DOMAIN
        
        # Verificar tamanho mínimo
        if len(response.strip()) < self.min_response_length:
            return False, FallbackTrigger.EMPTY_RESPONSE
        
        # Verificar se tem pelo menos uma palavra-chave do domínio
        has_domain_keyword = any(
            keyword in response_lower for keyword in self.domain_keywords
        )
        
        if not has_domain_keyword and not self._is_general_help_response(response_lower):
            return False, FallbackTrigger.OUT_OF_DOMAIN
        
        return True, None
    
    def _is_general_help_response(self, response: str) -> bool:
        """Verifica se é uma resposta de ajuda geral válida."""
        help_indicators = [
            "posso ajudar", "disponível", "consulta", "exemplo",
            "lista", "tipos", "opções", "comandos"
        ]
        return any(indicator in response for indicator in help_indicators)


class FallbackResponseGenerator:
    """Gerador de respostas de fallback baseadas em regras."""
    
    def __init__(self):
        """Inicializa o gerador de respostas."""
        # Respostas predefinidas por tipo de trigger
        self.predefined_responses = {
            FallbackTrigger.LLM_ERROR: {
                "message": "Desculpe, estou com dificuldades técnicas no momento. Mas posso tentar ajudar de outra forma!",
                "suggestions": [
                    "Tente reformular sua pergunta de forma mais específica",
                    "Pergunte sobre status de equipamentos específicos",
                    "Consulte dados de manutenção recentes"
                ]
            },
            FallbackTrigger.EMPTY_RESPONSE: {
                "message": "Não consegui gerar uma resposta completa para sua consulta.",
                "suggestions": [
                    "Seja mais específico sobre qual equipamento ou informação você precisa",
                    "Tente perguntas como 'Status dos transformadores' ou 'Manutenções pendentes'"
                ]
            },
            FallbackTrigger.OUT_OF_DOMAIN: {
                "message": "Esta pergunta está fora do meu domínio de conhecimento. Sou especializado em dados de manutenção e equipamentos elétricos.",
                "suggestions": [
                    "Pergunte sobre status de equipamentos",
                    "Consulte histórico de manutenções",
                    "Analise custos de manutenção",
                    "Verifique falhas de equipamentos"
                ]
            },
            FallbackTrigger.UNSUPPORTED_QUERY: {
                "message": "Este tipo de consulta ainda não é suportado pelo sistema.",
                "suggestions": [
                    "Tente consultas sobre equipamentos específicos",
                    "Pergunte sobre manutenções programadas",
                    "Solicite relatórios de custos"
                ]
            },
            FallbackTrigger.TIMEOUT: {
                "message": "A consulta está demorando mais que o esperado. Vou tentar uma abordagem mais simples.",
                "suggestions": [
                    "Tente uma pergunta mais específica",
                    "Limite o escopo da consulta a um tipo de equipamento"
                ]
            }
        }
        
        # Templates baseados em padrões de consulta
        self.query_templates = {
            "status_equipamento": {
                "pattern": r"status|situação|condição",
                "response": "Para consultar status de equipamentos, você pode perguntar:\n- 'Qual o status dos transformadores?'\n- 'Equipamentos em manutenção'\n- 'Quantos equipamentos estão operacionais?'"
            },
            "manutencao": {
                "pattern": r"manutenção|manutenções|maintenance",
                "response": "Para consultas sobre manutenção, tente:\n- 'Manutenções programadas para esta semana'\n- 'Histórico de manutenções do equipamento X'\n- 'Custos de manutenção por tipo'"
            },
            "falhas": {
                "pattern": r"falha|falhas|problema|defeito",
                "response": "Para análise de falhas, você pode perguntar:\n- 'Falhas mais comuns por tipo de equipamento'\n- 'Equipamentos com mais falhas'\n- 'Tempo médio de resolução de falhas'"
            },
            "custos": {
                "pattern": r"custo|valor|preço|gasto",
                "response": "Para análise de custos, tente:\n- 'Custo total de manutenções este mês'\n- 'Equipamentos com maior custo de manutenção'\n- 'Comparação de custos por tipo'"
            }
        }
        
        # Exemplos de consultas por categoria
        self.example_queries = {
            "equipamentos": [
                "Liste todos os transformadores",
                "Quantos geradores estão operacionais?",
                "Status dos equipamentos na subestação X"
            ],
            "manutencoes": [
                "Manutenções programadas para amanhã",
                "Histórico de manutenções preventivas",
                "Técnicos com mais manutenções realizadas"
            ],
            "analises": [
                "Equipamentos com mais falhas",
                "Custo médio de manutenção por tipo",
                "Tempo médio entre falhas"
            ]
        }
    
    def generate_response(
        self, 
        trigger: FallbackTrigger, 
        original_query: str,
        strategy: FallbackStrategy = None
    ) -> FallbackResponse:
        """
        Gera resposta de fallback baseada no trigger e estratégia.
        
        Args:
            trigger: O que disparou o fallback
            original_query: Consulta original do usuário
            strategy: Estratégia específica a usar (opcional)
            
        Returns:
            FallbackResponse: Resposta de fallback gerada
        """
        if strategy is None:
            strategy = self._select_strategy(trigger, original_query)
        
        if strategy == FallbackStrategy.PREDEFINED_RESPONSE:
            return self._generate_predefined_response(trigger, original_query)
        
        elif strategy == FallbackStrategy.TEMPLATE_BASED:
            return self._generate_template_response(original_query)
        
        elif strategy == FallbackStrategy.HELP_SUGGESTIONS:
            return self._generate_help_response(original_query)
        
        else:
            # Fallback do fallback - resposta padrão
            return self._generate_default_response(trigger)
    
    def _select_strategy(self, trigger: FallbackTrigger, query: str) -> FallbackStrategy:
        """Seleciona a melhor estratégia baseada no contexto."""
        query_lower = query.lower()
        
        # Se é claramente fora do domínio, usar help suggestions
        if trigger == FallbackTrigger.OUT_OF_DOMAIN:
            return FallbackStrategy.HELP_SUGGESTIONS
        
        # Se tem palavras-chave do domínio, usar template
        domain_keywords = ["equipamento", "manutenção", "status", "falha", "custo"]
        if any(keyword in query_lower for keyword in domain_keywords):
            return FallbackStrategy.TEMPLATE_BASED
        
        # Para erros técnicos, usar predefinida
        if trigger in [FallbackTrigger.LLM_ERROR, FallbackTrigger.TIMEOUT]:
            return FallbackStrategy.PREDEFINED_RESPONSE
        
        # Default para help suggestions
        return FallbackStrategy.HELP_SUGGESTIONS
    
    def _generate_predefined_response(self, trigger: FallbackTrigger, query: str) -> FallbackResponse:
        """Gera resposta predefinida."""
        response_data = self.predefined_responses.get(trigger, {
            "message": "Desculpe, não consegui processar sua consulta no momento.",
            "suggestions": ["Tente reformular sua pergunta"]
        })
        
        return FallbackResponse(
            message=response_data["message"],
            suggestions=response_data["suggestions"],
            strategy_used=FallbackStrategy.PREDEFINED_RESPONSE,
            trigger=trigger,
            confidence=0.8,
            actionable=True,
            metadata={"original_query": query}
        )
    
    def _generate_template_response(self, query: str) -> FallbackResponse:
        """Gera resposta baseada em templates."""
        query_lower = query.lower()
        
        # Encontrar template correspondente
        for category, template_data in self.query_templates.items():
            if re.search(template_data["pattern"], query_lower):
                return FallbackResponse(
                    message=f"Entendi que você quer saber sobre {category.replace('_', ' ')}. {template_data['response']}",
                    suggestions=self._get_category_suggestions(category),
                    strategy_used=FallbackStrategy.TEMPLATE_BASED,
                    trigger=FallbackTrigger.UNSUPPORTED_QUERY,
                    confidence=0.7,
                    actionable=True,
                    metadata={"category": category, "original_query": query}
                )
        
        # Se não encontrou template específico, usar sugestões gerais
        return self._generate_help_response(query)
    
    def _generate_help_response(self, query: str) -> FallbackResponse:
        """Gera resposta de ajuda com sugestões."""
        message = """Não consegui entender exatamente o que você precisa, mas posso ajudar com consultas sobre:

🔧 **Equipamentos**: Status, localização, tipo
⚙️ **Manutenções**: Programadas, histórico, custos  
⚠️ **Falhas**: Análises, frequência, resolução
📊 **Relatórios**: Custos, performance, estatísticas

Experimente uma dessas consultas:"""
        
        # Sugestões aleatórias de diferentes categorias
        suggestions = []
        for category, examples in self.example_queries.items():
            suggestions.extend(examples[:2])  # Pegar 2 exemplos de cada
        
        return FallbackResponse(
            message=message,
            suggestions=suggestions[:6],  # Limitar a 6 sugestões
            strategy_used=FallbackStrategy.HELP_SUGGESTIONS,
            trigger=FallbackTrigger.UNSUPPORTED_QUERY,
            confidence=0.9,
            actionable=True,
            metadata={"help_type": "general", "original_query": query}
        )
    
    def _generate_default_response(self, trigger: FallbackTrigger) -> FallbackResponse:
        """Gera resposta padrão quando outras estratégias falham."""
        return FallbackResponse(
            message="Desculpe, não consegui processar sua consulta. Tente reformular ou use uma das sugestões abaixo.",
            suggestions=[
                "Liste equipamentos operacionais",
                "Manutenções desta semana", 
                "Status dos transformadores"
            ],
            strategy_used=FallbackStrategy.PREDEFINED_RESPONSE,
            trigger=trigger,
            confidence=0.5,
            actionable=True,
            metadata={"fallback_level": "default"}
        )
    
    def _get_category_suggestions(self, category: str) -> List[str]:
        """Retorna sugestões específicas para uma categoria."""
        return self.example_queries.get(category, [
            "Tente ser mais específico na sua consulta"
        ])


class FallbackService:
    """
    Serviço principal de fallback para o sistema.
    
    Responsabilidades:
    - Detectar quando usar fallback
    - Coordenar estratégias de fallback
    - Coletar métricas de uso
    - Integrar com outros serviços
    """
    
    def __init__(self):
        """Inicializa o serviço de fallback."""
        self.settings = get_settings()
        self.validator = LLMResponseValidator()
        self.response_generator = FallbackResponseGenerator()
        
        # Métricas
        self.total_fallbacks = 0
        self.fallbacks_by_trigger = {}
        self.fallbacks_by_strategy = {}
        self.user_feedback_scores = []
        
        logger.info("FallbackService inicializado")
    
    def should_use_fallback(
        self, 
        llm_response: str, 
        original_query: str,
        llm_confidence: float = None,
        error: Exception = None
    ) -> Tuple[bool, Optional[FallbackTrigger]]:
        """
        Determina se deve usar fallback baseado na resposta e contexto.
        
        Args:
            llm_response: Resposta do LLM (pode ser None se erro)
            original_query: Consulta original
            llm_confidence: Score de confiança do LLM (opcional)
            error: Exceção se houve erro (opcional)
            
        Returns:
            Tuple[bool, Optional[FallbackTrigger]]: (usar_fallback, trigger)
        """
        # Verificar erros primeiro
        if error:
            if isinstance(error, LLMServiceError):
                if "quota" in str(error).lower():
                    return True, FallbackTrigger.API_QUOTA_EXCEEDED
                elif "timeout" in str(error).lower():
                    return True, FallbackTrigger.TIMEOUT
                else:
                    return True, FallbackTrigger.LLM_ERROR
            else:
                return True, FallbackTrigger.LLM_ERROR
        
        # Verificar confiança baixa
        if llm_confidence is not None and llm_confidence < 0.3:
            return True, FallbackTrigger.LOW_CONFIDENCE
        
        # Validar resposta do LLM
        if llm_response:
            is_valid, trigger = self.validator.validate_response(llm_response, original_query)
            if not is_valid:
                return True, trigger
        else:
            return True, FallbackTrigger.EMPTY_RESPONSE
        
        return False, None
    
    def generate_fallback_response(
        self, 
        trigger: FallbackTrigger,
        original_query: str,
        context: Dict[str, Any] = None
    ) -> FallbackResponse:
        """
        Gera resposta de fallback.
        
        Args:
            trigger: O que disparou o fallback
            original_query: Consulta original
            context: Contexto adicional (opcional)
            
        Returns:
            FallbackResponse: Resposta de fallback
        """
        try:
            # Atualizar métricas
            self.total_fallbacks += 1
            trigger_name = trigger.value
            self.fallbacks_by_trigger[trigger_name] = self.fallbacks_by_trigger.get(trigger_name, 0) + 1
            
            # Gerar resposta
            response = self.response_generator.generate_response(trigger, original_query)
            
            # Atualizar métricas de estratégia
            strategy_name = response.strategy_used.value
            self.fallbacks_by_strategy[strategy_name] = self.fallbacks_by_strategy.get(strategy_name, 0) + 1
            
            # Log da ativação do fallback
            logger.info("Fallback ativado", extra={
                "trigger": trigger_name,
                "strategy": strategy_name,
                "query": original_query[:50],
                "confidence": response.confidence
            })
            
            return response
            
        except Exception as e:
            logger.error(f"Erro ao gerar resposta de fallback: {str(e)}")
            
            # Fallback do fallback - resposta de emergência
            return FallbackResponse(
                message="Desculpe, estou com dificuldades técnicas. Tente novamente em alguns instantes.",
                suggestions=["Recarregue a página", "Tente uma consulta mais simples"],
                strategy_used=FallbackStrategy.PREDEFINED_RESPONSE,
                trigger=trigger,
                confidence=0.1,
                actionable=False,
                metadata={"emergency_fallback": True, "error": str(e)}
            )
    
    def record_user_feedback(self, response_id: str, rating: int, comment: str = None):
        """
        Registra feedback do usuário sobre resposta de fallback.
        
        Args:
            response_id: ID da resposta
            rating: Avaliação (1-5)
            comment: Comentário opcional
        """
        self.user_feedback_scores.append(rating)
        
        logger.info("Feedback de fallback registrado", extra={
            "response_id": response_id,
            "rating": rating,
            "has_comment": bool(comment)
        })
    
    def get_metrics(self) -> FallbackMetrics:
        """Retorna métricas do sistema de fallback."""
        total_queries = max(1, self.total_fallbacks)  # Evitar divisão por zero
        
        success_rate = (
            len([score for score in self.user_feedback_scores if score >= 3]) / 
            max(1, len(self.user_feedback_scores))
        )
        
        user_satisfaction = (
            sum(self.user_feedback_scores) / max(1, len(self.user_feedback_scores))
        ) if self.user_feedback_scores else 0.0
        
        return FallbackMetrics(
            total_fallbacks=self.total_fallbacks,
            fallbacks_by_trigger=self.fallbacks_by_trigger.copy(),
            fallbacks_by_strategy=self.fallbacks_by_strategy.copy(),
            success_rate=round(success_rate, 3),
            user_satisfaction=round(user_satisfaction, 2)
        )
    
    def get_health_status(self) -> Dict[str, Any]:
        """Retorna status de saúde do sistema de fallback."""
        metrics = self.get_metrics()
        
        # Calcular taxa de fallback (assumindo que conhecemos total de queries)
        fallback_rate = 0.0  # Seria calculado com total de queries do sistema
        
        # Determinar status geral
        if metrics.user_satisfaction >= 3.5 and fallback_rate < 0.2:
            status = "healthy"
        elif metrics.user_satisfaction >= 2.5 and fallback_rate < 0.4:
            status = "warning"
        else:
            status = "critical"
        
        return {
            "status": status,
            "fallback_rate": round(fallback_rate, 3),
            "user_satisfaction": metrics.user_satisfaction,
            "total_fallbacks": metrics.total_fallbacks,
            "most_common_trigger": max(metrics.fallbacks_by_trigger.items(), default=("none", 0))[0],
            "most_used_strategy": max(metrics.fallbacks_by_strategy.items(), default=("none", 0))[0]
        } 