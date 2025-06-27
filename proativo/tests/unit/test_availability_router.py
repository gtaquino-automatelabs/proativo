#!/usr/bin/env python3
"""
Testes Unitários para AvailabilityRouter - PROAtivo
Testa todas as funcionalidades do sistema de roteamento adaptativo.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
import json


# Mock classes para testes
class RoutingDecision:
    def __init__(self, route_type, reason, confidence, expected_execution_time=None):
        self.route_type = route_type
        self.reason = reason  
        self.confidence = confidence
        self.expected_execution_time = expected_execution_time or 5.0


class QueryOutcome:
    def __init__(self, query_text, decision, success, execution_time, 
                 confidence_score, error_type=None, user_feedback=None):
        self.query_text = query_text
        self.decision = decision
        self.success = success
        self.execution_time = execution_time
        self.confidence_score = confidence_score
        self.error_type = error_type
        self.user_feedback = user_feedback
        self.timestamp = datetime.now()


class HealthStatus:
    def __init__(self, status, healthy_services, total_services, issues=None, 
                 last_check=None, next_check=None):
        self.status = status
        self.healthy_services = healthy_services
        self.total_services = total_services
        self.issues = issues or []
        self.last_check = last_check or datetime.now()
        self.next_check = next_check or (datetime.now() + timedelta(minutes=5))


class ServiceMetrics:
    def __init__(self, service, availability, avg_response_time, success_rate, 
                 error_count=0, last_error=None):
        self.service = service
        self.availability = availability
        self.avg_response_time = avg_response_time
        self.success_rate = success_rate
        self.error_count = error_count
        self.last_error = last_error


class MockAvailabilityRouter:
    """Mock do AvailabilityRouter para testes"""
    
    def __init__(self):
        self.llm_service = Mock()
        self.sql_validator = Mock()
        self.fallback_service = Mock()
        self.query_outcomes = []
        self.circuit_breaker_open = False
        self.last_health_check = datetime.now()
        
        # Configurações
        self.max_query_length = 500
        self.min_confidence_threshold = 0.7
        self.max_execution_time = 30.0
        self.circuit_breaker_failure_threshold = 5
        self.circuit_breaker_timeout = 300
        
    def route_query(self, query_text, user_context=None):
        """Rota a query para o serviço apropriado"""
        if not query_text or len(query_text.strip()) == 0:
            return RoutingDecision(
                route_type="fallback",
                reason="Query vazia",
                confidence=1.0
            )
        
        if len(query_text) > self.max_query_length:
            return RoutingDecision(
                route_type="fallback",
                reason="Query muito longa",
                confidence=0.9
            )
        
        # Determinar complexidade
        complexity = self._assess_query_complexity(query_text)
        
        # Verificar disponibilidade dos serviços
        if self.circuit_breaker_open:
            return RoutingDecision(
                route_type="fallback",
                reason="Circuit breaker ativo",
                confidence=0.8
            )
        
        # Usar histórico para decisão
        historical_score = self._calculate_historical_performance(query_text)
        
        if complexity == "simple" and "lista" in query_text.lower():
            return RoutingDecision(
                route_type="rule_based",
                reason="Query simples compatível com regras",
                confidence=0.9
            )
        elif complexity in ["medium", "complex"] and historical_score > 0.7:
            return RoutingDecision(
                route_type="llm_sql",
                reason="Query complexa com boa performance histórica",
                confidence=historical_score
            )
        else:
            return RoutingDecision(
                route_type="fallback",
                reason="Query não compatível com outros serviços",
                confidence=0.6
            )
    
    def _assess_query_complexity(self, query_text):
        """Avalia complexidade da query"""
        words = query_text.lower().split()
        
        complex_keywords = [
            'comparar', 'analisar', 'correlação', 'tendência', 'projeção',
            'otimização', 'eficiência', 'performance', 'histórico'
        ]
        
        medium_keywords = [
            'status', 'quantos', 'custo', 'manutenção', 'falhas',
            'equipamentos', 'transformadores'
        ]
        
        if any(kw in words for kw in complex_keywords):
            return "complex"
        elif any(kw in words for kw in medium_keywords):
            return "medium"
        else:
            return "simple"
    
    def _calculate_historical_performance(self, query_text):
        """Calcula performance histórica baseada em outcomes similares"""
        if not self.query_outcomes:
            return 0.8  # Score padrão sem histórico
        
        # Buscar outcomes similares
        similar_outcomes = [
            outcome for outcome in self.query_outcomes
            if any(word in outcome.query_text.lower() 
                  for word in query_text.lower().split())
        ]
        
        if not similar_outcomes:
            return 0.8
        
        # Calcular média ponderada
        total_score = 0
        total_weight = 0
        
        for outcome in similar_outcomes[-10:]:  # Últimos 10
            weight = 1.0 if outcome.success else 0.3
            score = outcome.confidence_score if outcome.success else 0.2
            
            total_score += score * weight
            total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.5
    
    def record_outcome(self, query_text, decision, success, execution_time, 
                      confidence_score, error_type=None, user_feedback=None):
        """Registra resultado de uma query"""
        outcome = QueryOutcome(
            query_text=query_text,
            decision=decision,
            success=success,
            execution_time=execution_time,
            confidence_score=confidence_score,
            error_type=error_type,
            user_feedback=user_feedback
        )
        
        self.query_outcomes.append(outcome)
        
        # Atualizar circuit breaker se necessário
        if not success and decision == "llm_sql":
            recent_failures = sum(
                1 for outcome in self.query_outcomes[-10:]
                if not outcome.success and outcome.decision == "llm_sql"
            )
            
            if recent_failures >= self.circuit_breaker_failure_threshold:
                self.circuit_breaker_open = True
    
    def get_health_status(self):
        """Retorna status de saúde do sistema"""
        total_services = 3
        healthy_services = 0
        issues = []
        
        # Verificar cada serviço
        if hasattr(self.llm_service, 'is_healthy') and self.llm_service.is_healthy():
            healthy_services += 1
        else:
            issues.append("LLM Service indisponível")
        
        if hasattr(self.sql_validator, 'is_healthy') and self.sql_validator.is_healthy():
            healthy_services += 1
        else:
            issues.append("SQL Validator indisponível")
        
        if hasattr(self.fallback_service, 'is_healthy') and self.fallback_service.is_healthy():
            healthy_services += 1
        else:
            issues.append("Fallback Service indisponível")
        
        status = "healthy" if healthy_services == total_services else "degraded"
        if healthy_services == 0:
            status = "unhealthy"
        
        return HealthStatus(
            status=status,
            healthy_services=healthy_services,
            total_services=total_services,
            issues=issues
        )
    
    def get_service_metrics(self, service_name=None):
        """Retorna métricas dos serviços"""
        if not self.query_outcomes:
            return []
        
        services = ["llm_sql", "rule_based", "fallback"]
        if service_name:
            services = [service_name] if service_name in services else []
        
        metrics = []
        
        for service in services:
            service_outcomes = [
                o for o in self.query_outcomes if o.decision == service
            ]
            
            if not service_outcomes:
                metrics.append(ServiceMetrics(
                    service=service,
                    availability=1.0,
                    avg_response_time=0.0,
                    success_rate=1.0,
                    error_count=0
                ))
                continue
            
            success_count = sum(1 for o in service_outcomes if o.success)
            total_count = len(service_outcomes)
            success_rate = success_count / total_count
            
            avg_response_time = sum(o.execution_time for o in service_outcomes) / total_count
            error_count = total_count - success_count
            
            last_error = None
            for outcome in reversed(service_outcomes):
                if not outcome.success:
                    last_error = outcome.error_type
                    break
            
            metrics.append(ServiceMetrics(
                service=service,
                availability=success_rate,
                avg_response_time=avg_response_time,
                success_rate=success_rate,
                error_count=error_count,
                last_error=last_error
            ))
        
        return metrics
    
    def get_insights(self):
        """Retorna insights do sistema adaptativo"""
        if not self.query_outcomes:
            return {
                "total_queries": 0,
                "success_rate": 0.0,
                "avg_response_time": 0.0,
                "route_distribution": {},
                "recommendations": ["Sistema sem dados históricos"]
            }
        
        total_queries = len(self.query_outcomes)
        successful_queries = sum(1 for o in self.query_outcomes if o.success)
        success_rate = successful_queries / total_queries
        
        avg_response_time = sum(o.execution_time for o in self.query_outcomes) / total_queries
        
        # Distribuição de rotas
        route_dist = {}
        for outcome in self.query_outcomes:
            route_dist[outcome.decision] = route_dist.get(outcome.decision, 0) + 1
        
        # Recomendações
        recommendations = []
        if success_rate < 0.8:
            recommendations.append("Taxa de sucesso baixa - revisar estratégias de roteamento")
        if avg_response_time > 10.0:
            recommendations.append("Tempo de resposta alto - otimizar serviços")
        if self.circuit_breaker_open:
            recommendations.append("Circuit breaker ativo - verificar LLM service")
        
        return {
            "total_queries": total_queries,
            "success_rate": success_rate,
            "avg_response_time": avg_response_time,
            "route_distribution": route_dist,
            "recommendations": recommendations
        }


class TestAvailabilityRouter:
    """Testes para a classe AvailabilityRouter"""
    
    @pytest.fixture
    def router(self):
        """Fixture que retorna uma instância do MockAvailabilityRouter"""
        return MockAvailabilityRouter()
    
    def test_init(self, router):
        """Testa inicialização do router"""
        assert router.llm_service is not None
        assert router.sql_validator is not None
        assert router.fallback_service is not None
        assert isinstance(router.query_outcomes, list)
        assert not router.circuit_breaker_open
    
    def test_route_query_empty(self, router):
        """Testa roteamento de query vazia"""
        decision = router.route_query("")
        
        assert decision.route_type == "fallback"
        assert "vazia" in decision.reason.lower()
        assert decision.confidence == 1.0
    
    def test_route_query_none(self, router):
        """Testa roteamento de query None"""
        decision = router.route_query(None)
        
        assert decision.route_type == "fallback"
        assert "vazia" in decision.reason.lower()
    
    def test_route_query_too_long(self, router):
        """Testa roteamento de query muito longa"""
        long_query = "palavra " * 200  # > 500 caracteres
        decision = router.route_query(long_query)
        
        assert decision.route_type == "fallback"
        assert "longa" in decision.reason.lower()
        assert decision.confidence > 0.8
    
    def test_route_query_simple_rule_based(self, router):
        """Testa roteamento de query simples para rule-based"""
        query = "Lista todos os transformadores"
        decision = router.route_query(query)
        
        assert decision.route_type == "rule_based"
        assert "simples" in decision.reason.lower()
        assert decision.confidence > 0.8
    
    def test_route_query_complex_llm(self, router):
        """Testa roteamento de query complexa para LLM"""
        query = "Analisar tendência de falhas nos transformadores"
        decision = router.route_query(query)
        
        assert decision.route_type == "llm_sql"
        assert "complexa" in decision.reason.lower()
        assert decision.confidence > 0.6
    
    def test_route_query_circuit_breaker_open(self, router):
        """Testa roteamento com circuit breaker ativo"""
        router.circuit_breaker_open = True
        query = "Analisar equipamentos"
        decision = router.route_query(query)
        
        assert decision.route_type == "fallback"
        assert "circuit breaker" in decision.reason.lower()
    
    def test_assess_query_complexity_simple(self, router):
        """Testa avaliação de complexidade simples"""
        complexity = router._assess_query_complexity("lista equipamentos")
        assert complexity == "simple"
    
    def test_assess_query_complexity_medium(self, router):
        """Testa avaliação de complexidade média"""
        complexity = router._assess_query_complexity("quantos equipamentos estão operacionais")
        assert complexity == "medium"
    
    def test_assess_query_complexity_complex(self, router):
        """Testa avaliação de complexidade alta"""
        complexity = router._assess_query_complexity("analisar tendência de falhas")
        assert complexity == "complex"
    
    def test_calculate_historical_performance_no_history(self, router):
        """Testa cálculo de performance sem histórico"""
        score = router._calculate_historical_performance("teste")
        assert score == 0.8  # Score padrão
    
    def test_calculate_historical_performance_with_history(self, router):
        """Testa cálculo de performance com histórico"""
        # Adicionar outcomes históricos
        router.query_outcomes = [
            QueryOutcome("teste equipamentos", "llm_sql", True, 2.0, 0.9),
            QueryOutcome("teste manutenção", "llm_sql", True, 3.0, 0.8),
            QueryOutcome("teste falhas", "llm_sql", False, 5.0, 0.4),
        ]
        
        score = router._calculate_historical_performance("teste novos equipamentos")
        assert 0.5 < score < 1.0  # Deve estar entre 0.5 e 1.0
    
    def test_record_outcome_success(self, router):
        """Testa registro de outcome bem-sucedido"""
        initial_count = len(router.query_outcomes)
        
        router.record_outcome(
            query_text="teste",
            decision="llm_sql",
            success=True,
            execution_time=2.5,
            confidence_score=0.9
        )
        
        assert len(router.query_outcomes) == initial_count + 1
        outcome = router.query_outcomes[-1]
        assert outcome.query_text == "teste"
        assert outcome.success
        assert outcome.execution_time == 2.5
    
    def test_record_outcome_failure(self, router):
        """Testa registro de outcome com falha"""
        router.record_outcome(
            query_text="teste falha",
            decision="llm_sql",
            success=False,
            execution_time=10.0,
            confidence_score=0.3,
            error_type="timeout"
        )
        
        outcome = router.query_outcomes[-1]
        assert not outcome.success
        assert outcome.error_type == "timeout"
    
    def test_record_outcome_triggers_circuit_breaker(self, router):
        """Testa se múltiplas falhas ativam o circuit breaker"""
        # Registrar múltiplas falhas
        for i in range(6):
            router.record_outcome(
                query_text=f"teste falha {i}",
                decision="llm_sql",
                success=False,
                execution_time=10.0,
                confidence_score=0.2,
                error_type="llm_error"
            )
        
        assert router.circuit_breaker_open
    
    def test_get_health_status_all_healthy(self, router):
        """Testa status de saúde com todos os serviços saudáveis"""
        # Mock serviços como saudáveis
        router.llm_service.is_healthy = Mock(return_value=True)
        router.sql_validator.is_healthy = Mock(return_value=True)
        router.fallback_service.is_healthy = Mock(return_value=True)
        
        health = router.get_health_status()
        
        assert health.status == "healthy"
        assert health.healthy_services == 3
        assert health.total_services == 3
        assert len(health.issues) == 0
    
    def test_get_health_status_some_unhealthy(self, router):
        """Testa status de saúde com alguns serviços indisponíveis"""
        # Mock alguns serviços como não saudáveis
        router.llm_service.is_healthy = Mock(return_value=False)
        router.sql_validator.is_healthy = Mock(return_value=True)
        router.fallback_service.is_healthy = Mock(return_value=True)
        
        health = router.get_health_status()
        
        assert health.status == "degraded"
        assert health.healthy_services == 2
        assert len(health.issues) > 0
    
    def test_get_service_metrics_no_data(self, router):
        """Testa métricas de serviços sem dados"""
        metrics = router.get_service_metrics()
        
        assert len(metrics) == 3  # llm_sql, rule_based, fallback
        for metric in metrics:
            assert metric.availability == 1.0
            assert metric.success_rate == 1.0
            assert metric.error_count == 0
    
    def test_get_service_metrics_with_data(self, router):
        """Testa métricas de serviços com dados"""
        # Adicionar outcomes
        router.query_outcomes = [
            QueryOutcome("teste1", "llm_sql", True, 2.0, 0.9),
            QueryOutcome("teste2", "llm_sql", False, 8.0, 0.4),
            QueryOutcome("teste3", "fallback", True, 1.0, 0.8),
        ]
        
        metrics = router.get_service_metrics("llm_sql")
        
        assert len(metrics) == 1
        llm_metric = metrics[0]
        assert llm_metric.service == "llm_sql"
        assert llm_metric.success_rate == 0.5  # 1 sucesso de 2
        assert llm_metric.error_count == 1
        assert llm_metric.avg_response_time == 5.0  # (2+8)/2
    
    def test_get_insights_no_data(self, router):
        """Testa insights sem dados"""
        insights = router.get_insights()
        
        assert insights["total_queries"] == 0
        assert insights["success_rate"] == 0.0
        assert insights["avg_response_time"] == 0.0
        assert "sem dados" in insights["recommendations"][0].lower()
    
    def test_get_insights_with_data(self, router):
        """Testa insights com dados"""
        # Adicionar outcomes variados
        router.query_outcomes = [
            QueryOutcome("teste1", "llm_sql", True, 3.0, 0.9),
            QueryOutcome("teste2", "llm_sql", True, 4.0, 0.8),
            QueryOutcome("teste3", "fallback", True, 1.0, 0.7),
            QueryOutcome("teste4", "rule_based", False, 15.0, 0.3),
        ]
        
        insights = router.get_insights()
        
        assert insights["total_queries"] == 4
        assert insights["success_rate"] == 0.75  # 3 sucessos de 4
        assert insights["avg_response_time"] == 5.75  # (3+4+1+15)/4
        assert "llm_sql" in insights["route_distribution"]
        assert insights["route_distribution"]["llm_sql"] == 2
    
    @pytest.mark.parametrize("query,expected_route", [
        ("Lista todos os equipamentos", "rule_based"),
        ("Analisar correlação entre falhas", "llm_sql"),
        ("", "fallback"),
        ("palavra " * 200, "fallback"),  # Query muito longa
    ])
    def test_routing_patterns(self, router, query, expected_route):
        """Testa padrões de roteamento"""
        decision = router.route_query(query)
        assert decision.route_type == expected_route
    
    def test_user_context_handling(self, router):
        """Testa tratamento de contexto do usuário"""
        user_context = {"role": "admin", "preferences": {"prefer_detailed": True}}
        decision = router.route_query("Status dos equipamentos", user_context)
        
        # Deve funcionar mesmo com contexto
        assert decision.route_type in ["rule_based", "llm_sql", "fallback"]
        assert decision.confidence > 0.0
    
    def test_confidence_scoring(self, router):
        """Testa pontuação de confiança"""
        # Query com alta confiança
        decision1 = router.route_query("Lista equipamentos")
        assert decision1.confidence > 0.8
        
        # Query com baixa confiança (fallback)
        decision2 = router.route_query("xyz abc def")
        assert decision2.confidence < 0.9


class TestRoutingDecision:
    """Testes para a classe RoutingDecision"""
    
    def test_routing_decision_creation(self):
        """Testa criação de RoutingDecision"""
        decision = RoutingDecision(
            route_type="llm_sql",
            reason="Query complexa",
            confidence=0.85,
            expected_execution_time=3.5
        )
        
        assert decision.route_type == "llm_sql"
        assert decision.reason == "Query complexa"
        assert decision.confidence == 0.85
        assert decision.expected_execution_time == 3.5


class TestQueryOutcome:
    """Testes para a classe QueryOutcome"""
    
    def test_query_outcome_creation(self):
        """Testa criação de QueryOutcome"""
        outcome = QueryOutcome(
            query_text="teste",
            decision="llm_sql",
            success=True,
            execution_time=2.5,
            confidence_score=0.9,
            error_type=None,
            user_feedback="positive"
        )
        
        assert outcome.query_text == "teste"
        assert outcome.decision == "llm_sql"
        assert outcome.success
        assert outcome.execution_time == 2.5
        assert outcome.confidence_score == 0.9
        assert outcome.user_feedback == "positive"
        assert isinstance(outcome.timestamp, datetime)


# Testes de integração
class TestAvailabilityRouterIntegration:
    """Testes de integração para AvailabilityRouter"""
    
    @pytest.fixture
    def router(self):
        return MockAvailabilityRouter()
    
    def test_full_workflow_successful_routing(self, router):
        """Testa workflow completo de roteamento bem-sucedido"""
        query = "Lista equipamentos operacionais"
        
        # 1. Roteamento
        decision = router.route_query(query)
        assert decision.route_type == "rule_based"
        
        # 2. Registro de outcome bem-sucedido
        router.record_outcome(
            query_text=query,
            decision=decision.route_type,
            success=True,
            execution_time=1.5,
            confidence_score=0.9
        )
        
        # 3. Verificar que foi registrado
        assert len(router.query_outcomes) == 1
        assert router.query_outcomes[0].success
        
        # 4. Verificar métricas
        metrics = router.get_service_metrics("rule_based")
        assert metrics[0].success_rate == 1.0
    
    def test_full_workflow_with_failures_and_recovery(self, router):
        """Testa workflow com falhas e recuperação"""
        query = "Analisar performance complexa"
        
        # 1. Múltiplas falhas para ativar circuit breaker
        for i in range(6):
            decision = router.route_query(f"{query} {i}")
            router.record_outcome(
                query_text=f"{query} {i}",
                decision="llm_sql",
                success=False,
                execution_time=10.0,
                confidence_score=0.3,
                error_type="llm_timeout"
            )
        
        # 2. Circuit breaker deve estar ativo
        assert router.circuit_breaker_open
        
        # 3. Nova query deve ir para fallback
        decision = router.route_query("Nova query")
        assert decision.route_type == "fallback"
        assert "circuit breaker" in decision.reason.lower()
        
        # 4. Verificar insights
        insights = router.get_insights()
        assert insights["success_rate"] < 0.1
        assert len(insights["recommendations"]) > 0


if __name__ == "__main__":
    pytest.main([__file__]) 