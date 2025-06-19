"""
Sistema de Fallback para LLM.

Este módulo implementa um sistema robusto de fallback que:
- Detecta quando respostas do LLM são inadequadas
- Gera respostas alternativas baseadas em templates
- Oferece sugestões úteis mesmo quando o LLM falha
- Mantém experiência do usuário consistente
"""

from typing import Dict, Any, List, Optional, Set
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
import re

from ...utils.logger import get_logger

# Configurar logger
logger = get_logger(__name__)


class FallbackTrigger(Enum):
    """Triggers que ativam o sistema de fallback."""
    LLM_ERROR = "llm_error"
    EMPTY_RESPONSE = "empty_response"
    LOW_CONFIDENCE = "low_confidence"
    TIMEOUT = "timeout"
    API_QUOTA_EXCEEDED = "api_quota_exceeded"
    INVALID_RESPONSE = "invalid_response"
    OUT_OF_DOMAIN = "out_of_domain"
    UNSUPPORTED_QUERY = "unsupported_query"


class FallbackStrategy(Enum):
    """Estratégias de fallback disponíveis."""
    PREDEFINED_RESPONSE = "predefined_response"
    TEMPLATE_BASED = "template_based"
    HELP_SUGGESTIONS = "help_suggestions"
    EMERGENCY_FALLBACK = "emergency_fallback"


@dataclass
class FallbackResponse:
    """Resposta gerada pelo sistema de fallback."""
    message: str
    confidence: float
    strategy_used: FallbackStrategy
    suggestions: List[str]
    actionable: bool
    trigger: FallbackTrigger
    metadata: Dict[str, Any]


class FallbackService:
    """
    Serviço principal de fallback para o LLM.
    
    Responsabilidades:
    - Detectar respostas inadequadas do LLM
    - Gerar respostas alternativas contextuais
    - Manter experiência do usuário positiva
    - Coletar métricas de uso do fallback
    """
    
    def __init__(self):
        """Inicializa o serviço de fallback."""
        self.total_fallbacks = 0
        self.fallbacks_by_trigger = {}
        self.fallbacks_by_strategy = {}
        self.user_feedback_scores = []
        
        # Templates de resposta por trigger
        self.response_templates = self._initialize_response_templates()
        
        logger.info("FallbackService inicializado com sucesso")
    
    def _initialize_response_templates(self) -> Dict[FallbackTrigger, Dict[str, Any]]:
        """Inicializa templates de resposta para cada trigger."""
        return {
            FallbackTrigger.LLM_ERROR: {
                "message": "Desculpe, estou com dificuldades técnicas no momento. Posso ajudá-lo de outra forma?",
                "suggestions": [
                    "Tente reformular sua pergunta",
                    "Verifique o status dos equipamentos",
                    "Consulte manutenções pendentes"
                ],
                "strategy": FallbackStrategy.PREDEFINED_RESPONSE
            },
            FallbackTrigger.EMPTY_RESPONSE: {
                "message": "Não consegui processar sua pergunta. Pode ser mais específico sobre o que deseja saber?",
                "suggestions": [
                    "Status de um equipamento específico",
                    "Informações sobre manutenções",
                    "Relatórios de custos"
                ],
                "strategy": FallbackStrategy.HELP_SUGGESTIONS
            },
            FallbackTrigger.LOW_CONFIDENCE: {
                "message": "Não tenho certeza sobre esta informação. Posso ajudar com algo mais específico sobre equipamentos ou manutenções?",
                "suggestions": [
                    "Consulta mais específica",
                    "Verificar dados disponíveis",
                    "Contatar suporte técnico"
                ],
                "strategy": FallbackStrategy.TEMPLATE_BASED
            },
            FallbackTrigger.TIMEOUT: {
                "message": "A consulta está demorando mais que o esperado. Tente uma pergunta mais simples ou aguarde um momento.",
                "suggestions": [
                    "Simplifique sua pergunta",
                    "Tente novamente em alguns instantes",
                    "Consulte informações básicas"
                ],
                "strategy": FallbackStrategy.PREDEFINED_RESPONSE
            },
            FallbackTrigger.API_QUOTA_EXCEEDED: {
                "message": "Atingimos o limite de consultas por hoje. Funcionalidades básicas ainda estão disponíveis.",
                "suggestions": [
                    "Consulte dados em cache",
                    "Tente novamente mais tarde",
                    "Use relatórios pré-definidos"
                ],
                "strategy": FallbackStrategy.EMERGENCY_FALLBACK
            },
            FallbackTrigger.OUT_OF_DOMAIN: {
                "message": "Esta pergunta está fora do meu escopo. Posso ajudar com informações sobre equipamentos elétricos e manutenções.",
                "suggestions": [
                    "Status dos equipamentos",
                    "Programação de manutenções",
                    "Histórico de falhas",
                    "Custos de manutenção"
                ],
                "strategy": FallbackStrategy.HELP_SUGGESTIONS
            },
            FallbackTrigger.UNSUPPORTED_QUERY: {
                "message": "Ainda não consigo processar este tipo de consulta. Posso ajudar com informações sobre:",
                "suggestions": [
                    "Status e localização de equipamentos",
                    "Histórico de manutenções",
                    "Análise de custos",
                    "Programação de atividades"
                ],
                "strategy": FallbackStrategy.TEMPLATE_BASED
            }
        }
    
    def should_use_fallback(
        self,
        llm_response: Optional[str] = None,
        original_query: str = "",
        llm_confidence: Optional[float] = None,
        error: Optional[Exception] = None
    ) -> tuple[bool, Optional[FallbackTrigger]]:
        """
        Determina se deve usar fallback baseado na resposta do LLM.
        
        Args:
            llm_response: Resposta do LLM (se disponível)
            original_query: Query original do usuário
            llm_confidence: Score de confiança do LLM
            error: Erro ocorrido (se houver)
            
        Returns:
            Tuple: (should_use_fallback, trigger)
        """
        # 1. Verificar erros críticos
        if error:
            error_str = str(error).lower()
            if "quota" in error_str or "limit" in error_str:
                return True, FallbackTrigger.API_QUOTA_EXCEEDED
            elif "timeout" in error_str:
                return True, FallbackTrigger.TIMEOUT
            else:
                return True, FallbackTrigger.LLM_ERROR
        
        # 2. Verificar resposta vazia ou muito curta
        if not llm_response or len(llm_response.strip()) < 10:
            return True, FallbackTrigger.EMPTY_RESPONSE
        
        # 3. Verificar confiança baixa
        if llm_confidence is not None and llm_confidence < 0.5:
            return True, FallbackTrigger.LOW_CONFIDENCE
        
        # 4. Verificar se resposta está fora do domínio
        if self._is_out_of_domain(original_query, llm_response):
            return True, FallbackTrigger.OUT_OF_DOMAIN
        
        # 5. Verificar resposta inválida
        if self._is_invalid_response(llm_response):
            return True, FallbackTrigger.INVALID_RESPONSE
        
        return False, None
    
    def _is_out_of_domain(self, query: str, response: str) -> bool:
        """Verifica se query/resposta está fora do domínio."""
        # Palavras que indicam domínio correto
        domain_keywords = [
            "equipamento", "transformador", "gerador", "disjuntor",
            "manutenção", "falha", "custo", "status", "operacional",
            "técnico", "elétrico", "energia", "potência", "tensão"
        ]
        
        query_lower = query.lower()
        response_lower = response.lower() if response else ""
        
        # Verificar se query tem palavras do domínio
        has_domain_keywords = any(keyword in query_lower for keyword in domain_keywords)
        
        # Se não tem palavras do domínio, pode estar fora do escopo
        if not has_domain_keywords:
            # Verificar padrões comuns de queries fora do domínio
            out_of_domain_patterns = [
                r"como está o tempo",
                r"que horas são",
                r"o que é.*\?",
                r"como funciona.*\?",
                r"explique.*conceito",
                r"definição de",
                r"receita de",
                r"como cozinhar"
            ]
            
            for pattern in out_of_domain_patterns:
                if re.search(pattern, query_lower):
                    return True
        
        return False
    
    def _is_invalid_response(self, response: str) -> bool:
        """Verifica se resposta é inválida."""
        if not response:
            return True
        
        # Padrões de resposta inválida
        invalid_patterns = [
            r"^(ok|sim|não)$",
            r"^[\.!?]{3,}$",
            r"^(erro|error)",
            r"não sei.*não sei",
            r"(desculpe.*){3,}"
        ]
        
        response_lower = response.lower().strip()
        
        for pattern in invalid_patterns:
            if re.search(pattern, response_lower):
                return True
        
        return False
    
    def generate_fallback_response(
        self,
        trigger: FallbackTrigger,
        original_query: str,
        context: Dict[str, Any]
    ) -> FallbackResponse:
        """
        Gera resposta de fallback baseada no trigger.
        
        Args:
            trigger: Motivo do fallback
            original_query: Query original do usuário
            context: Contexto adicional
            
        Returns:
            FallbackResponse: Resposta estruturada de fallback
        """
        self.total_fallbacks += 1
        self.fallbacks_by_trigger[trigger.value] = self.fallbacks_by_trigger.get(trigger.value, 0) + 1
        
        template = self.response_templates.get(trigger)
        if not template:
            # Fallback do fallback
            template = {
                "message": "Desculpe, não consigo processar sua solicitação no momento.",
                "suggestions": ["Tente novamente mais tarde"],
                "strategy": FallbackStrategy.EMERGENCY_FALLBACK
            }
        
        # Personalizar resposta baseada no contexto
        personalized_message = self._personalize_message(
            template["message"],
            original_query,
            context
        )
        
        # Gerar sugestões contextuais
        contextual_suggestions = self._generate_contextual_suggestions(
            template["suggestions"],
            original_query,
            context
        )
        
        strategy = template["strategy"]
        self.fallbacks_by_strategy[strategy.value] = self.fallbacks_by_strategy.get(strategy.value, 0) + 1
        
        # Calcular confiança da resposta de fallback
        confidence = self._calculate_fallback_confidence(trigger, context)
        
        response = FallbackResponse(
            message=personalized_message,
            confidence=confidence,
            strategy_used=strategy,
            suggestions=contextual_suggestions,
            actionable=self._is_actionable_response(trigger),
            trigger=trigger,
            metadata={
                "original_query": original_query,
                "timestamp": datetime.now().isoformat(),
                "context_size": len(str(context)),
                "total_fallbacks": self.total_fallbacks
            }
        )
        
        logger.info(f"Fallback response gerada: trigger={trigger.value}, strategy={strategy.value}")
        
        return response
    
    def _personalize_message(
        self,
        base_message: str,
        query: str,
        context: Dict[str, Any]
    ) -> str:
        """Personaliza mensagem baseada no contexto."""
        # Extrair entidades da query para personalização
        entities = self._extract_entities(query)
        
        personalized = base_message
        
        # Adicionar referência a equipamentos específicos se mencionados
        if entities.get("equipment_ids"):
            equipment_ref = ", ".join(entities["equipment_ids"][:2])
            personalized += f" (Equipamentos mencionados: {equipment_ref})"
        
        return personalized
    
    def _extract_entities(self, query: str) -> Dict[str, List[str]]:
        """Extrai entidades básicas da query."""
        entities = {"equipment_ids": [], "equipment_types": []}
        
        # Padrões para IDs de equipamento
        equipment_id_pattern = r'\b[A-Z]{2}\d{3}\b'
        equipment_ids = re.findall(equipment_id_pattern, query.upper())
        entities["equipment_ids"] = equipment_ids
        
        # Tipos de equipamento
        equipment_types = ["transformador", "gerador", "disjuntor", "motor"]
        for eq_type in equipment_types:
            if eq_type in query.lower():
                entities["equipment_types"].append(eq_type)
        
        return entities
    
    def _generate_contextual_suggestions(
        self,
        base_suggestions: List[str],
        query: str,
        context: Dict[str, Any]
    ) -> List[str]:
        """Gera sugestões contextuais."""
        suggestions = base_suggestions.copy()
        
        # Adicionar sugestões baseadas na query
        query_lower = query.lower()
        
        if "transformador" in query_lower:
            suggestions.append("Listar todos os transformadores")
            suggestions.append("Status dos transformadores")
        
        if "manutenção" in query_lower:
            suggestions.append("Manutenções pendentes")
            suggestions.append("Histórico de manutenções")
        
        if "custo" in query_lower:
            suggestions.append("Relatório de custos")
            suggestions.append("Análise financeira")
        
        # Limitar número de sugestões
        return suggestions[:5]
    
    def _calculate_fallback_confidence(
        self,
        trigger: FallbackTrigger,
        context: Dict[str, Any]
    ) -> float:
        """Calcula confiança da resposta de fallback."""
        base_confidence = {
            FallbackTrigger.LLM_ERROR: 0.3,
            FallbackTrigger.EMPTY_RESPONSE: 0.5,
            FallbackTrigger.LOW_CONFIDENCE: 0.4,
            FallbackTrigger.TIMEOUT: 0.6,
            FallbackTrigger.API_QUOTA_EXCEEDED: 0.7,
            FallbackTrigger.OUT_OF_DOMAIN: 0.8,
            FallbackTrigger.UNSUPPORTED_QUERY: 0.6,
            FallbackTrigger.INVALID_RESPONSE: 0.4
        }
        
        return base_confidence.get(trigger, 0.5)
    
    def _is_actionable_response(self, trigger: FallbackTrigger) -> bool:
        """Verifica se resposta de fallback é acionável."""
        actionable_triggers = {
            FallbackTrigger.OUT_OF_DOMAIN,
            FallbackTrigger.UNSUPPORTED_QUERY,
            FallbackTrigger.EMPTY_RESPONSE
        }
        return trigger in actionable_triggers
    
    def record_user_feedback(self, response_id: str, rating: float, comments: str = ""):
        """Registra feedback do usuário sobre resposta de fallback."""
        self.user_feedback_scores.append(rating)
        
        logger.info(f"Feedback registrado: rating={rating}, response_id={response_id}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retorna métricas do sistema de fallback."""
        avg_satisfaction = (
            sum(self.user_feedback_scores) / len(self.user_feedback_scores)
            if self.user_feedback_scores else 0.0
        )
        
        return {
            "total_fallbacks": self.total_fallbacks,
            "fallbacks_by_trigger": self.fallbacks_by_trigger,
            "fallbacks_by_strategy": self.fallbacks_by_strategy,
            "user_satisfaction": round(avg_satisfaction, 2),
            "feedback_count": len(self.user_feedback_scores),
            "success_rate": 1.0 if self.total_fallbacks > 0 else 0.0  # Fallback sempre "succeed"
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Retorna status de saúde do sistema de fallback."""
        metrics = self.get_metrics()
        
        # Fallback system está sempre "healthy" pois é o último recurso
        status = "healthy"
        
        return {
            "status": status,
            "total_fallbacks": metrics["total_fallbacks"],
            "user_satisfaction": metrics["user_satisfaction"],
            "most_common_trigger": max(
                self.fallbacks_by_trigger, 
                key=self.fallbacks_by_trigger.get
            ) if self.fallbacks_by_trigger else "none",
            "recommendations": self._generate_health_recommendations()
        }
    
    def _generate_health_recommendations(self) -> List[str]:
        """Gera recomendações para melhorar sistema de fallback."""
        recommendations = []
        
        if self.total_fallbacks > 100:
            recommendations.append("Alto número de fallbacks - revisar qualidade do LLM")
        
        if self.user_feedback_scores:
            avg_rating = sum(self.user_feedback_scores) / len(self.user_feedback_scores)
            if avg_rating < 3.0:
                recommendations.append("Baixa satisfação - melhorar templates de resposta")
        
        # Análise por trigger
        if self.fallbacks_by_trigger.get(FallbackTrigger.LLM_ERROR.value, 0) > 10:
            recommendations.append("Muitos erros de LLM - verificar configuração da API")
        
        if not recommendations:
            recommendations.append("Sistema de fallback funcionando adequadamente")
        
        return recommendations 