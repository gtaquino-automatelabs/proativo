"""
Availability Router para roteamento inteligente entre LLM SQL e sistema de fallback.

Este módulo implementa a lógica de decisão para escolher automaticamente
entre usar o LLM SQL Generator ou o sistema baseado em regras existente,
baseado em disponibilidade, performance e contexto.

VERSÃO 2.0: Sistema Adaptativo com Aprendizado
"""

import re
import time
import asyncio
from typing import Dict, Any, Optional, Tuple, List, Deque
from enum import Enum
from dataclasses import dataclass, field
import logging
from datetime import datetime, timedelta
from collections import deque, Counter

from ..config import get_settings
from .llm_sql_generator import LLMSQLGenerator
from .fallback_service import FallbackService, FallbackTrigger
from .query_processor import QueryProcessor
from ...utils.logger import get_logger
from ...utils.error_handlers import LLMServiceError

# Configurar logger
logger = get_logger(__name__)


class RouteDecision(Enum):
    """Decisões de roteamento possíveis."""
    LLM_SQL = "llm_sql"
    RULE_BASED = "rule_based"
    FALLBACK = "fallback"


@dataclass
class QueryOutcome:
    """Resultado de uma query processada."""
    decision: RouteDecision
    success: bool
    response_time: float
    confidence: float
    user_satisfaction: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    query_complexity: str = "unknown"
    fallback_trigger: Optional[str] = None


@dataclass
class RouteMetrics:
    """Métricas de roteamento aprimoradas."""
    total_requests: int = 0
    llm_routes: int = 0
    rule_based_routes: int = 0
    fallback_routes: int = 0
    llm_success_rate: float = 0.0
    rule_based_success_rate: float = 0.0
    average_llm_response_time: float = 0.0
    average_rule_response_time: float = 0.0
    health_check_failures: int = 0
    last_health_check: Optional[datetime] = None
    adaptation_score: float = 0.0
    user_satisfaction_avg: float = 0.0
    circuit_breaker_activations: int = 0


@dataclass
class AdaptiveDecisionEngine:
    """Engine de decisão adaptativa baseado em histórico."""
    success_history: Deque[QueryOutcome] = field(default_factory=lambda: deque(maxlen=100))
    complexity_patterns: Dict[str, List[str]] = field(default_factory=dict)
    decision_weights: Dict[str, float] = field(default_factory=lambda: {
        "llm_success": 0.4,
        "response_time": 0.3,
        "user_satisfaction": 0.2,
        "availability": 0.1
    })
    
    def add_outcome(self, outcome: QueryOutcome):
        """Adiciona resultado à história."""
        self.success_history.append(outcome)
        self._update_patterns(outcome)
    
    def _update_patterns(self, outcome: QueryOutcome):
        """Atualiza padrões de complexidade."""
        complexity = outcome.query_complexity
        if complexity not in self.complexity_patterns:
            self.complexity_patterns[complexity] = []
        
        # Manter apenas padrões recentes
        if len(self.complexity_patterns[complexity]) > 20:
            self.complexity_patterns[complexity] = self.complexity_patterns[complexity][-20:]
        
        self.complexity_patterns[complexity].append(outcome.decision.value)
    
    def recommend_decision(
        self, 
        query_complexity: str,
        llm_available: bool,
        current_llm_performance: float
    ) -> Tuple[RouteDecision, float, str]:
        """
        Recomenda decisão baseada em aprendizado histórico.
        
        Returns:
            Tuple[RouteDecision, confiança, razão]
        """
        if not llm_available:
            return RouteDecision.RULE_BASED, 1.0, "LLM indisponível"
        
        # Análise baseada em histórico de complexidade
        historical_success = self._analyze_complexity_history(query_complexity)
        
        # Análise de performance recente
        recent_performance = self._analyze_recent_performance()
        
        # Calcular score para cada decisão
        llm_score = (
            historical_success.get("llm_sql", 0.5) * self.decision_weights["llm_success"] +
            current_llm_performance * self.decision_weights["response_time"] +
            recent_performance.get("llm_satisfaction", 0.5) * self.decision_weights["user_satisfaction"] +
            (1.0 if llm_available else 0.0) * self.decision_weights["availability"]
        )
        
        rule_score = (
            historical_success.get("rule_based", 0.7) * self.decision_weights["llm_success"] +
            0.9 * self.decision_weights["response_time"] +  # Rules são sempre rápidas
            recent_performance.get("rule_satisfaction", 0.7) * self.decision_weights["user_satisfaction"] +
            1.0 * self.decision_weights["availability"]  # Rules sempre disponíveis
        )
        
        # Decidir baseado nos scores
        if llm_score > rule_score:
            confidence = min(1.0, llm_score / rule_score)
            return RouteDecision.LLM_SQL, confidence, f"Adaptativo: LLM score {llm_score:.2f} > Rule score {rule_score:.2f}"
        else:
            confidence = min(1.0, rule_score / llm_score)
            return RouteDecision.RULE_BASED, confidence, f"Adaptativo: Rule score {rule_score:.2f} > LLM score {llm_score:.2f}"
    
    def _analyze_complexity_history(self, complexity: str) -> Dict[str, float]:
        """Analisa histórico de sucesso por complexidade."""
        if complexity not in self.complexity_patterns:
            return {"llm_sql": 0.5, "rule_based": 0.7}  # Defaults conservadores
        
        patterns = self.complexity_patterns[complexity]
        counter = Counter(patterns)
        total = len(patterns)
        
        if total == 0:
            return {"llm_sql": 0.5, "rule_based": 0.7}
        
        return {
            "llm_sql": counter.get("llm_sql", 0) / total,
            "rule_based": counter.get("rule_based", 0) / total
        }
    
    def _analyze_recent_performance(self) -> Dict[str, float]:
        """Analisa performance recente por tipo de decisão."""
        recent_outcomes = list(self.success_history)[-20:]  # Últimas 20
        
        llm_outcomes = [o for o in recent_outcomes if o.decision == RouteDecision.LLM_SQL]
        rule_outcomes = [o for o in recent_outcomes if o.decision == RouteDecision.RULE_BASED]
        
        llm_satisfaction = (
            sum(o.user_satisfaction or 3.0 for o in llm_outcomes) / 
            max(1, len(llm_outcomes)) / 5.0  # Normalizar para 0-1
        ) if llm_outcomes else 0.5
        
        rule_satisfaction = (
            sum(o.user_satisfaction or 3.5 for o in rule_outcomes) / 
            max(1, len(rule_outcomes)) / 5.0  # Normalizar para 0-1
        ) if rule_outcomes else 0.7
        
        return {
            "llm_satisfaction": llm_satisfaction,
            "rule_satisfaction": rule_satisfaction
        }


class AvailabilityRouter:
    """
    Roteador de disponibilidade ADAPTATIVO para escolher entre LLM SQL e sistema de regras.
    
    VERSÃO 2.0 - Recursos Adaptativos:
    - Aprendizado baseado em histórico
    - Circuit breaker configurável
    - Métricas avançadas de performance
    - Sistema de alerta automático
    - Decisões baseadas em ML básico
    """
    
    def __init__(self):
        """Inicializa o roteador adaptativo."""
        self.settings = get_settings()
        
        # Serviços
        self._llm_sql_generator = None
        self._fallback_service = FallbackService()
        self._query_processor = QueryProcessor()
        
        # Estado e métricas
        self.metrics = RouteMetrics()
        self._llm_available = False
        self._last_availability_check = None
        self._availability_check_interval = timedelta(
            seconds=self.settings.fallback_health_check_interval
        )
        
        # Circuit breaker configurável
        self._consecutive_failures = 0
        self._failure_threshold = self.settings.fallback_failure_threshold
        self._circuit_open = False
        self._circuit_open_until = None
        self._circuit_cooldown = timedelta(seconds=self.settings.fallback_circuit_timeout)
        
        # Sistema adaptativo
        self._adaptive_engine = AdaptiveDecisionEngine()
        self._response_times = deque(maxlen=100)
        self._user_feedback = deque(maxlen=50)
        
        # Alertas
        self._last_alert_check = datetime.now()
        self._alert_cooldown = timedelta(minutes=30)
        
        logger.info("AvailabilityRouter v2.0 (Adaptativo) inicializado", extra={
            "failure_threshold": self._failure_threshold,
            "circuit_timeout": self.settings.fallback_circuit_timeout,
            "adaptive_enabled": self.settings.fallback_learning_enabled
        })
    
    async def _initialize_llm_sql(self) -> bool:
        """Inicializa o LLM SQL Generator se ainda não foi feito."""
        if self._llm_sql_generator is None:
            try:
                self._llm_sql_generator = LLMSQLGenerator()
                logger.info("LLM SQL Generator inicializado com sucesso")
                return True
            except Exception as e:
                logger.error(f"Erro ao inicializar LLM SQL Generator: {str(e)}")
                return False
        return True
    
    async def check_llm_availability(self, force: bool = False) -> bool:
        """
        Verifica se o LLM SQL está disponível com cache inteligente.
        
        Args:
            force: Forçar verificação mesmo se recente
            
        Returns:
            bool: True se disponível
        """
        # Usar cache se verificação recente e não forçada
        if not force and self._last_availability_check:
            if datetime.now() - self._last_availability_check < self._availability_check_interval:
                return self._llm_available
        
        try:
            # Verificar configurações primeiro
            if not self.settings.llm_sql_feature_enabled:
                logger.debug("LLM SQL desabilitado por feature flag")
                self._llm_available = False
                return False
            
            if not self.settings.google_api_key:
                logger.debug("Google API Key não configurada")
                self._llm_available = False
                return False
            
            # Circuit breaker check
            if self._circuit_open:
                if datetime.now() < self._circuit_open_until:
                    logger.debug("Circuit breaker ainda aberto")
                    return False
                else:
                    # Tentar fechar o circuit
                    logger.info("Tentando fechar circuit breaker")
                    self._circuit_open = False
            
            # Inicializar LLM SQL se necessário
            if not await self._initialize_llm_sql():
                self._llm_available = False
                return False
            
            # Fazer health check com timeout configurável
            health_result = await asyncio.wait_for(
                self._llm_sql_generator.health_check(),
                timeout=self.settings.fallback_response_timeout
            )
            
            if health_result.get("status") == "healthy":
                self._llm_available = True
                self._consecutive_failures = 0  # Reset contador
                self.metrics.last_health_check = datetime.now()
                logger.debug("LLM SQL health check: healthy")
            else:
                self._llm_available = False
                self._handle_health_check_failure()
                logger.warning(f"LLM SQL health check failed: {health_result}")
            
        except asyncio.TimeoutError:
            logger.warning("Health check timeout")
            self._llm_available = False
            self._handle_health_check_failure()
        except Exception as e:
            logger.error(f"Erro durante verificação de disponibilidade: {str(e)}")
            self._llm_available = False
            self._handle_health_check_failure()
        
        self._last_availability_check = datetime.now()
        return self._llm_available
    
    def _handle_health_check_failure(self):
        """Lida com falha no health check com configurações personalizadas."""
        self.metrics.health_check_failures += 1
        self._consecutive_failures += 1
        
        # Ativar circuit breaker se muitas falhas consecutivas
        if self._consecutive_failures >= self._failure_threshold:
            self._circuit_open = True
            self._circuit_open_until = datetime.now() + self._circuit_cooldown
            self.metrics.circuit_breaker_activations += 1
            
            logger.warning(
                f"Circuit breaker ativado após {self._consecutive_failures} falhas",
                extra={
                    "cooldown_until": self._circuit_open_until.isoformat(),
                    "total_activations": self.metrics.circuit_breaker_activations
                }
            )
            
            # Verificar se deve enviar alerta
            self._check_alert_threshold()
    
    def _check_alert_threshold(self):
        """Verifica se deve disparar alertas baseado nos thresholds."""
        now = datetime.now()
        if now - self._last_alert_check < self._alert_cooldown:
            return
        
        # Calcular taxa de fallback recente
        recent_outcomes = list(self._adaptive_engine.success_history)[-20:]
        if len(recent_outcomes) < 10:
            return
        
        fallback_rate = len([o for o in recent_outcomes if o.decision == RouteDecision.FALLBACK]) / len(recent_outcomes)
        
        if fallback_rate > self.settings.fallback_alert_threshold:
            logger.error(
                f"ALERTA: Taxa de fallback alta ({fallback_rate:.1%})",
                extra={
                    "threshold": self.settings.fallback_alert_threshold,
                    "circuit_activations": self.metrics.circuit_breaker_activations,
                    "consecutive_failures": self._consecutive_failures
                }
            )
            self._last_alert_check = now
    
    async def route_query(
        self, 
        query: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[RouteDecision, str]:
        """
        Roteia uma query usando sistema adaptativo inteligente.
        
        Args:
            query: Query do usuário
            context: Contexto adicional
            
        Returns:
            Tuple[RouteDecision, str]: (decisão, motivo)
        """
        self.metrics.total_requests += 1
        
        # Verificar disponibilidade do LLM
        llm_available = await self.check_llm_availability()
        
        # Analisar complexidade da query
        query_complexity = self._analyze_query_complexity(query)
        
        # Calcular performance atual do LLM
        current_llm_performance = self._calculate_current_llm_performance()
        
        # Usar sistema adaptativo se habilitado
        if self.settings.fallback_learning_enabled and len(self._adaptive_engine.success_history) >= 10:
            decision, confidence, reason = self._adaptive_engine.recommend_decision(
                query_complexity, llm_available, current_llm_performance
            )
            
            logger.info(f"Decisão adaptativa: {decision.value}", extra={
                "confidence": confidence,
                "reason": reason,
                "complexity": query_complexity,
                "history_size": len(self._adaptive_engine.success_history)
            })
            
            return decision, f"Adaptativo ({confidence:.2f}): {reason}"
        
        # Fallback para lógica original se sistema adaptativo não disponível
        if not llm_available:
            self.metrics.rule_based_routes += 1
            reasons = self._get_unavailability_reasons()
            reason = f"LLM SQL não disponível: {', '.join(reasons)}"
            logger.info(f"Roteando para sistema baseado em regras: {reason}")
            return RouteDecision.RULE_BASED, reason
        
        # Para queries muito simples, usar sistema de regras (mais rápido)
        if query_complexity == "simple":
            self.metrics.rule_based_routes += 1
            reason = "Query simples, usando sistema otimizado"
            logger.debug(f"Query simples detectada, usando regras: {query[:50]}")
            return RouteDecision.RULE_BASED, reason
        
        # Para queries complexas ou médias, usar LLM
        self.metrics.llm_routes += 1
        reason = f"Query {query_complexity}, usando LLM SQL"
        logger.info(f"Roteando para LLM SQL: {reason}")
        return RouteDecision.LLM_SQL, reason
    
    def _get_unavailability_reasons(self) -> List[str]:
        """Retorna lista de razões pelas quais LLM não está disponível."""
        reasons = []
        if not self.settings.llm_sql_feature_enabled:
            reasons.append("feature desabilitada")
        if self._circuit_open:
            reasons.append("circuit breaker ativo")
        if not self.settings.google_api_key:
            reasons.append("API key não configurada")
        if self.metrics.health_check_failures > 0:
            reasons.append("health check falhou")
        return reasons or ["status desconhecido"]
    
    def _calculate_current_llm_performance(self) -> float:
        """Calcula performance atual do LLM baseada em métricas recentes."""
        if not self._response_times:
            return 0.5  # Performance neutra
        
        # Normalizar tempo de resposta (0-1, onde 1 é melhor)
        avg_response_time = sum(self._response_times) / len(self._response_times)
        max_acceptable_time = 10000  # 10 segundos em ms
        
        # Performance baseada em tempo (inverso normalizado)
        time_performance = max(0, 1 - (avg_response_time / max_acceptable_time))
        
        # Performance baseada em taxa de sucesso
        success_performance = self.metrics.llm_success_rate
        
        # Média ponderada
        return (time_performance * 0.4 + success_performance * 0.6)
    
    def _analyze_query_complexity(self, query: str) -> str:
        """
        Analisa a complexidade de uma query.
        
        Returns:
            str: "simple", "medium", ou "complex"
        """
        query_lower = query.lower()
        
        # Queries simples que o sistema de regras faz bem
        simple_patterns = [
            r"^quantos?\s+\w+",  # "quantos equipamentos"
            r"^liste?\s+todos?\s+os?\s+\w+$",  # "liste todos os transformadores"
            r"^status\s+do?\s+\w+$",  # "status do equipamento"
            r"^total\s+de\s+\w+$"  # "total de manutenções"
        ]
        
        for pattern in simple_patterns:
            if re.match(pattern, query_lower):
                return "simple"
        
        # Indicadores de complexidade
        complex_indicators = [
            " join ", " média ", " entre ", " por ", 
            " agrupar ", " comparar ", " evolução ",
            " tendência ", " análise ", " correlação"
        ]
        
        complexity_score = sum(1 for indicator in complex_indicators if indicator in query_lower)
        
        if complexity_score >= 2:
            return "complex"
        elif complexity_score == 1:
            return "medium"
        else:
            # Verificar tamanho da query
            return "medium" if len(query.split()) > 5 else "simple"
    
    async def process_with_llm_sql(
        self, 
        query: str,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Processa query usando LLM SQL Generator com tracking adaptativo.
        
        Args:
            query: Query do usuário
            timeout: Timeout customizado
            
        Returns:
            Dict com resultado do processamento
        """
        start_time = time.time()
        outcome = QueryOutcome(
            decision=RouteDecision.LLM_SQL,
            success=False,
            response_time=0.0,
            confidence=0.0,
            query_complexity=self._analyze_query_complexity(query)
        )
        
        try:
            # Usar timeout configurável
            effective_timeout = timeout or self.settings.llm_sql_timeout
            
            # Gerar SQL
            result = await asyncio.wait_for(
                self._llm_sql_generator.generate_sql(query, effective_timeout),
                timeout=effective_timeout + 2.0  # Buffer adicional
            )
            
            # Registrar tempo de resposta
            response_time = (time.time() - start_time) * 1000
            self._track_response_time(response_time)
            outcome.response_time = response_time
            
            if result["success"]:
                # Atualizar taxa de sucesso
                self._update_success_rate(True)
                outcome.success = True
                outcome.confidence = result.get("confidence", 0.8)
                
                # Adicionar outcome ao histórico adaptativo
                self._adaptive_engine.add_outcome(outcome)
                
                return {
                    "success": True,
                    "route": RouteDecision.LLM_SQL,
                    "sql": result["sql"],
                    "response_time_ms": response_time,
                    "method": "llm_sql_generation",
                    "confidence": outcome.confidence
                }
            else:
                # Falha na geração, usar fallback
                self._update_success_rate(False)
                self.metrics.fallback_routes += 1
                outcome.fallback_trigger = "llm_generation_failed"
                
                # Adicionar outcome falhado ao histórico
                self._adaptive_engine.add_outcome(outcome)
                
                # Gerar resposta de fallback
                fallback_response = self._fallback_service.generate_fallback_response(
                    FallbackTrigger.LLM_ERROR,
                    query
                )
                
                return {
                    "success": False,
                    "route": RouteDecision.FALLBACK,
                    "message": fallback_response.message,
                    "suggestions": fallback_response.suggestions,
                    "error": result.get("error"),
                    "response_time_ms": response_time,
                    "method": "fallback"
                }
                
        except asyncio.TimeoutError:
            logger.warning(f"Timeout ao processar com LLM SQL: {effective_timeout}s")
            self._update_success_rate(False)
            self.metrics.fallback_routes += 1
            outcome.fallback_trigger = "timeout"
            self._adaptive_engine.add_outcome(outcome)
            
            fallback_response = self._fallback_service.generate_fallback_response(
                FallbackTrigger.TIMEOUT,
                query
            )
            
            return {
                "success": False,
                "route": RouteDecision.FALLBACK,
                "message": fallback_response.message,
                "suggestions": fallback_response.suggestions,
                "error": "timeout",
                "response_time_ms": (time.time() - start_time) * 1000,
                "method": "fallback"
            }
            
        except Exception as e:
            logger.error(f"Erro ao processar com LLM SQL: {str(e)}")
            self._update_success_rate(False)
            self.metrics.fallback_routes += 1
            outcome.fallback_trigger = "exception"
            
            # Incrementar falhas consecutivas
            self._consecutive_failures += 1
            if self._consecutive_failures >= self._failure_threshold:
                self._handle_health_check_failure()
            
            # Adicionar outcome falhado
            self._adaptive_engine.add_outcome(outcome)
            
            # Usar fallback
            fallback_response = self._fallback_service.generate_fallback_response(
                FallbackTrigger.LLM_ERROR,
                query
            )
            
            return {
                "success": False,
                "route": RouteDecision.FALLBACK,
                "message": fallback_response.message,
                "suggestions": fallback_response.suggestions,
                "error": str(e),
                "response_time_ms": (time.time() - start_time) * 1000,
                "method": "fallback"
            }
    
    async def process_with_rule_based(self, query: str) -> Dict[str, Any]:
        """
        Processa query usando sistema baseado em regras com tracking.
        
        Args:
            query: Query do usuário
            
        Returns:
            Dict com resultado do processamento
        """
        start_time = time.time()
        outcome = QueryOutcome(
            decision=RouteDecision.RULE_BASED,
            success=False,
            response_time=0.0,
            confidence=0.0,
            query_complexity=self._analyze_query_complexity(query)
        )
        
        try:
            # Usar o QueryProcessor existente
            result = await self._query_processor.process_query(query)
            
            response_time = (time.time() - start_time) * 1000
            outcome.response_time = response_time
            outcome.success = True
            outcome.confidence = result.confidence_score if hasattr(result, 'confidence_score') else 0.7
            
            # Atualizar métricas
            self.metrics.average_rule_response_time = (
                (self.metrics.average_rule_response_time * (self.metrics.rule_based_routes - 1) + response_time) / 
                max(1, self.metrics.rule_based_routes)
            )
            
            # Adicionar ao histórico adaptativo
            self._adaptive_engine.add_outcome(outcome)
            
            return {
                "success": True,
                "route": RouteDecision.RULE_BASED,
                "response": result,
                "response_time_ms": response_time,
                "method": "rule_based",
                "confidence": outcome.confidence
            }
            
        except Exception as e:
            logger.error(f"Erro no sistema baseado em regras: {str(e)}")
            self.metrics.fallback_routes += 1
            outcome.fallback_trigger = "rule_based_error"
            self._adaptive_engine.add_outcome(outcome)
            
            # Usar fallback
            fallback_response = self._fallback_service.generate_fallback_response(
                FallbackTrigger.LLM_ERROR,
                query
            )
            
            return {
                "success": False,
                "route": RouteDecision.FALLBACK,
                "message": fallback_response.message,
                "suggestions": fallback_response.suggestions,
                "error": str(e),
                "response_time_ms": (time.time() - start_time) * 1000,
                "method": "fallback"
            }
    
    def record_user_feedback(
        self, 
        query: str, 
        decision: RouteDecision, 
        satisfaction_score: float,
        comment: Optional[str] = None
    ):
        """
        Registra feedback do usuário para aprendizado adaptativo.
        
        Args:
            query: Query original
            decision: Decisão que foi tomada
            satisfaction_score: Score de 1-5
            comment: Comentário opcional
        """
        # Atualizar histórico de feedback
        self._user_feedback.append(satisfaction_score)
        
        # Atualizar outcome mais recente se disponível
        recent_outcomes = [o for o in self._adaptive_engine.success_history 
                          if o.decision == decision]
        if recent_outcomes:
            # Atualizar o mais recente
            recent_outcomes[-1].user_satisfaction = satisfaction_score
        
        # Atualizar métricas globais
        if self._user_feedback:
            self.metrics.user_satisfaction_avg = sum(self._user_feedback) / len(self._user_feedback)
        
        logger.info("Feedback registrado", extra={
            "decision": decision.value,
            "satisfaction": satisfaction_score,
            "avg_satisfaction": self.metrics.user_satisfaction_avg,
            "has_comment": bool(comment)
        })
    
    def _track_response_time(self, response_time: float):
        """Registra tempo de resposta para métricas."""
        self._response_times.append(response_time)
        
        # Atualizar média
        if self._response_times:
            self.metrics.average_llm_response_time = sum(self._response_times) / len(self._response_times)
    
    def _update_success_rate(self, success: bool):
        """Atualiza taxa de sucesso do LLM."""
        # Implementação mais sofisticada baseada em histórico
        recent_llm_outcomes = [
            o for o in list(self._adaptive_engine.success_history)[-50:] 
            if o.decision == RouteDecision.LLM_SQL
        ]
        
        if recent_llm_outcomes:
            successes = len([o for o in recent_llm_outcomes if o.success])
            self.metrics.llm_success_rate = successes / len(recent_llm_outcomes)
        else:
            # Fallback para método incremental
            if success:
                self.metrics.llm_success_rate = min(1.0, self.metrics.llm_success_rate + 0.01)
            else:
                self.metrics.llm_success_rate = max(0.0, self.metrics.llm_success_rate - 0.05)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retorna métricas avançadas de roteamento."""
        # Calcular métricas adaptativas
        recent_outcomes = list(self._adaptive_engine.success_history)[-50:]  # Últimos 50
        
        # Estatísticas por tipo de decisão
        decision_stats = {
            "llm_sql": {"count": 0, "success": 0, "avg_time": 0},
            "rule_based": {"count": 0, "success": 0, "avg_time": 0},
            "fallback": {"count": 0, "success": 0, "avg_time": 0}
        }
        
        for outcome in recent_outcomes:
            decision_key = outcome.decision.value
            if decision_key in decision_stats:
                decision_stats[decision_key]["count"] += 1
                if outcome.success:
                    decision_stats[decision_key]["success"] += 1
                decision_stats[decision_key]["avg_time"] += outcome.response_time
        
        # Calcular médias
        for stats in decision_stats.values():
            if stats["count"] > 0:
                stats["success_rate"] = stats["success"] / stats["count"]
                stats["avg_time"] = stats["avg_time"] / stats["count"]
            else:
                stats["success_rate"] = 0.0
                stats["avg_time"] = 0.0
        
        # Métricas de complexidade
        complexity_distribution = {}
        for outcome in recent_outcomes:
            complexity = outcome.query_complexity
            if complexity not in complexity_distribution:
                complexity_distribution[complexity] = 0
            complexity_distribution[complexity] += 1
        
        # Score de adaptação (baseado na consistência das decisões)
        adaptation_score = self._calculate_adaptation_score()
        
        return {
            "total_requests": self.metrics.total_requests,
            "routes": {
                "llm_sql": self.metrics.llm_routes,
                "rule_based": self.metrics.rule_based_routes,
                "fallback": self.metrics.fallback_routes
            },
            "percentages": {
                "llm_sql": (self.metrics.llm_routes / max(1, self.metrics.total_requests)) * 100,
                "rule_based": (self.metrics.rule_based_routes / max(1, self.metrics.total_requests)) * 100,
                "fallback": (self.metrics.fallback_routes / max(1, self.metrics.total_requests)) * 100
            },
            "performance": {
                "llm_success_rate": self.metrics.llm_success_rate * 100,
                "rule_success_rate": decision_stats["rule_based"]["success_rate"] * 100,
                "average_llm_response_time_ms": self.metrics.average_llm_response_time,
                "average_rule_response_time_ms": self.metrics.average_rule_response_time,
                "user_satisfaction_avg": self.metrics.user_satisfaction_avg,
                "adaptation_score": adaptation_score
            },
            "circuit_breaker": {
                "open": self._circuit_open,
                "consecutive_failures": self._consecutive_failures,
                "activations_total": self.metrics.circuit_breaker_activations,
                "open_until": self._circuit_open_until.isoformat() if self._circuit_open_until else None
            },
            "adaptive_system": {
                "enabled": self.settings.fallback_learning_enabled,
                "history_size": len(self._adaptive_engine.success_history),
                "decision_stats": decision_stats,
                "complexity_distribution": complexity_distribution,
                "patterns_learned": len(self._adaptive_engine.complexity_patterns)
            },
            "health": {
                "llm_available": self._llm_available,
                "last_health_check": self.metrics.last_health_check.isoformat() if self.metrics.last_health_check else None,
                "health_check_failures": self.metrics.health_check_failures
            },
            "configuration": {
                "failure_threshold": self._failure_threshold,
                "circuit_timeout_seconds": self.settings.fallback_circuit_timeout,
                "health_check_interval_seconds": self.settings.fallback_health_check_interval,
                "min_confidence": self.settings.fallback_min_confidence
            }
        }
    
    def _calculate_adaptation_score(self) -> float:
        """Calcula score de adaptação baseado na evolução das decisões."""
        if len(self._adaptive_engine.success_history) < 20:
            return 0.0
        
        recent = list(self._adaptive_engine.success_history)[-20:]
        
        # Calcular consistência das decisões bem-sucedidas
        successful_decisions = [o.decision for o in recent if o.success]
        if not successful_decisions:
            return 0.0
        
        # Diversidade balanceada (não muito focada em uma só decisão)
        decision_counts = Counter(successful_decisions)
        total_decisions = len(successful_decisions)
        
        # Score baseado em distribuição equilibrada e taxa de sucesso
        diversity_score = 1.0 - max(decision_counts.values()) / total_decisions
        success_rate = len(successful_decisions) / len(recent)
        
        # Combinar scores (50% taxa de sucesso, 50% diversidade)
        return (success_rate * 0.7 + diversity_score * 0.3) * 100
    
    async def health_check(self) -> Dict[str, Any]:
        """Verifica saúde avançada do roteador."""
        llm_available = await self.check_llm_availability()
        
        # Determinar status geral do sistema
        status = "healthy"
        issues = []
        
        # Verificar problemas potenciais
        if self._circuit_open:
            status = "degraded"
            issues.append("Circuit breaker ativo")
        
        if self.metrics.health_check_failures > 5:
            status = "degraded" if status == "healthy" else "critical"
            issues.append(f"Múltiplas falhas de health check ({self.metrics.health_check_failures})")
        
        if not llm_available and self.settings.llm_sql_feature_enabled:
            status = "degraded" if status == "healthy" else "critical"
            issues.append("LLM SQL indisponível")
        
        # Verificar taxa de fallback recente
        recent_outcomes = list(self._adaptive_engine.success_history)[-20:]
        if recent_outcomes:
            fallback_rate = len([o for o in recent_outcomes if o.decision == RouteDecision.FALLBACK]) / len(recent_outcomes)
            if fallback_rate > self.settings.fallback_alert_threshold:
                status = "degraded" if status == "healthy" else "critical"
                issues.append(f"Taxa de fallback alta ({fallback_rate:.1%})")
        
        # Verificar satisfação do usuário
        if self.metrics.user_satisfaction_avg < self.settings.fallback_user_satisfaction_min:
            status = "degraded" if status == "healthy" else "critical"
            issues.append(f"Satisfação do usuário baixa ({self.metrics.user_satisfaction_avg:.1f}/5.0)")
        
        return {
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "llm_available": llm_available,
            "adaptive_system_active": (
                self.settings.fallback_learning_enabled and 
                len(self._adaptive_engine.success_history) >= 10
            ),
            "circuit_breaker": {
                "open": self._circuit_open,
                "consecutive_failures": self._consecutive_failures,
                "open_until": self._circuit_open_until.isoformat() if self._circuit_open_until else None
            },
            "metrics_summary": {
                "total_requests": self.metrics.total_requests,
                "llm_success_rate": f"{self.metrics.llm_success_rate * 100:.1f}%",
                "user_satisfaction": f"{self.metrics.user_satisfaction_avg:.1f}/5.0",
                "adaptation_score": f"{self._calculate_adaptation_score():.1f}%"
            },
            "issues": issues,
            "recommendations": self._get_health_recommendations(status, issues)
        }
    
    def _get_health_recommendations(self, status: str, issues: List[str]) -> List[str]:
        """Gera recomendações baseadas no status de saúde."""
        recommendations = []
        
        if self._circuit_open:
            recommendations.append("Aguardar cooldown do circuit breaker ou verificar conectividade LLM")
        
        if "LLM SQL indisponível" in issues:
            recommendations.append("Verificar configuração da API Google Gemini")
            recommendations.append("Confirmar que GOOGLE_API_KEY está configurada corretamente")
        
        if "Taxa de fallback alta" in issues:
            recommendations.append("Investigar qualidade das queries ou ajustar thresholds")
            recommendations.append("Considerar retreinar o sistema adaptativo")
        
        if "Satisfação do usuário baixa" in issues:
            recommendations.append("Revisar respostas de fallback e melhorar templates")
            recommendations.append("Coletar mais feedback específico dos usuários")
        
        if status == "healthy":
            recommendations.append("Sistema funcionando normalmente")
        
        return recommendations
    
    def get_adaptive_insights(self) -> Dict[str, Any]:
        """Retorna insights do sistema adaptativo para análise."""
        if not self.settings.fallback_learning_enabled:
            return {"enabled": False, "message": "Sistema adaptativo desabilitado"}
        
        history = list(self._adaptive_engine.success_history)
        if len(history) < 5:
            return {"enabled": True, "message": "Dados insuficientes para insights", "history_size": len(history)}
        
        # Análise de tendências
        recent_20 = history[-20:] if len(history) >= 20 else history
        older_20 = history[-40:-20] if len(history) >= 40 else []
        
        # Comparar performance entre períodos
        def analyze_period(outcomes):
            if not outcomes:
                return {"success_rate": 0, "avg_satisfaction": 0, "dominant_decision": "none"}
            
            success_rate = len([o for o in outcomes if o.success]) / len(outcomes)
            avg_satisfaction = sum(o.user_satisfaction or 3.0 for o in outcomes) / len(outcomes)
            decisions = [o.decision.value for o in outcomes]
            dominant_decision = Counter(decisions).most_common(1)[0][0] if decisions else "none"
            
            return {
                "success_rate": success_rate,
                "avg_satisfaction": avg_satisfaction,
                "dominant_decision": dominant_decision,
                "count": len(outcomes)
            }
        
        recent_analysis = analyze_period(recent_20)
        older_analysis = analyze_period(older_20) if older_20 else None
        
        # Detectar padrões de complexidade
        complexity_insights = {}
        for complexity, patterns in self._adaptive_engine.complexity_patterns.items():
            counter = Counter(patterns)
            total = len(patterns)
            complexity_insights[complexity] = {
                "total_queries": total,
                "preferred_route": counter.most_common(1)[0][0] if patterns else "unknown",
                "distribution": dict(counter)
            }
        
        return {
            "enabled": True,
            "history_size": len(history),
            "learning_active": len(history) >= 10,
            "periods_analysis": {
                "recent": recent_analysis,
                "previous": older_analysis,
                "trend": self._analyze_trend(recent_analysis, older_analysis) if older_analysis else "insufficient_data"
            },
            "complexity_insights": complexity_insights,
            "decision_weights": self._adaptive_engine.decision_weights,
            "recommendations": self._get_adaptive_recommendations(recent_analysis, complexity_insights)
        }
    
    def _analyze_trend(self, recent, older) -> str:
        """Analisa tendência entre dois períodos."""
        success_trend = recent["success_rate"] - older["success_rate"]
        satisfaction_trend = recent["avg_satisfaction"] - older["avg_satisfaction"]
        
        if success_trend > 0.1 and satisfaction_trend > 0.3:
            return "improving"
        elif success_trend < -0.1 or satisfaction_trend < -0.3:
            return "degrading"
        else:
            return "stable"
    
    def _get_adaptive_recommendations(self, recent_analysis, complexity_insights) -> List[str]:
        """Gera recomendações baseadas em insights adaptativos."""
        recommendations = []
        
        if recent_analysis["success_rate"] < 0.7:
            recommendations.append("Taxa de sucesso baixa - considerar ajustar pesos de decisão")
        
        if recent_analysis["avg_satisfaction"] < 3.0:
            recommendations.append("Satisfação baixa - revisar estratégias de fallback")
        
        # Analisar distribuição de complexidade
        simple_queries = complexity_insights.get("simple", {})
        complex_queries = complexity_insights.get("complex", {})
        
        if simple_queries.get("preferred_route") == "llm_sql":
            recommendations.append("Queries simples usando LLM - considerar otimizar para rule-based")
        
        if complex_queries.get("preferred_route") == "rule_based":
            recommendations.append("Queries complexas usando rules - investigar problemas com LLM")
        
        if not recommendations:
            recommendations.append("Sistema adaptativo funcionando adequadamente")
        
        return recommendations 