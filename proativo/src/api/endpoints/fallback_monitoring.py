"""
Endpoint de monitoramento do sistema de fallback avançado.

Este módulo fornece endpoints para monitorar métricas, status e insights
do sistema de fallback adaptativo do PROAtivo.
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..dependencies import get_availability_router, get_fallback_service, get_current_settings
from ..config import Settings
from ..services.availability_router import AvailabilityRouter, RouteDecision
from ..services.fallback_service import FallbackService
from ...utils.logger import get_logger

# Configurar logging
logger = get_logger(__name__)

# Criar router para endpoints de monitoramento
router = APIRouter(prefix="/fallback", tags=["fallback-monitoring"])


class FeedbackRequest(BaseModel):
    """Request para feedback do usuário."""
    query: str = Field(..., description="Query original do usuário")
    decision: str = Field(..., description="Decisão tomada (llm_sql, rule_based, fallback)")
    satisfaction_score: float = Field(..., ge=1, le=5, description="Score de satisfação (1-5)")
    comment: Optional[str] = Field(None, description="Comentário opcional")


@router.get("/status")
async def get_fallback_status(
    availability_router: AvailabilityRouter = Depends(get_availability_router),
    fallback_service: FallbackService = Depends(get_fallback_service)
) -> Dict[str, Any]:
    """
    Retorna status geral do sistema de fallback.
    
    Returns:
        Dict com status consolidado dos sistemas
    """
    try:
        # Health check do router
        router_health = await availability_router.health_check()
        
        # Status do fallback service
        fallback_health = fallback_service.get_health_status()
        
        # Determinar status geral
        overall_status = "healthy"
        if router_health["status"] == "critical" or fallback_health["status"] == "critical":
            overall_status = "critical"
        elif router_health["status"] == "degraded" or fallback_health["status"] == "warning":
            overall_status = "degraded"
        
        return {
            "overall_status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "components": {
                "availability_router": router_health,
                "fallback_service": fallback_health
            },
            "quick_stats": {
                "llm_available": router_health["llm_available"],
                "adaptive_active": router_health["adaptive_system_active"],
                "circuit_breaker_open": router_health["circuit_breaker"]["open"],
                "total_requests": router_health["metrics_summary"]["total_requests"]
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter status de fallback: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao verificar status do sistema"
        )


@router.get("/metrics")
async def get_fallback_metrics(
    detailed: bool = Query(False, description="Incluir métricas detalhadas"),
    availability_router: AvailabilityRouter = Depends(get_availability_router),
    fallback_service: FallbackService = Depends(get_fallback_service)
) -> Dict[str, Any]:
    """
    Retorna métricas detalhadas do sistema de fallback.
    
    Args:
        detailed: Se deve incluir métricas detalhadas
        
    Returns:
        Dict com métricas consolidadas
    """
    try:
        # Métricas do router
        router_metrics = availability_router.get_metrics()
        
        # Métricas do fallback service
        fallback_metrics = fallback_service.get_metrics()
        
        base_metrics = {
            "summary": {
                "total_requests": router_metrics["total_requests"],
                "fallback_rate": router_metrics["percentages"]["fallback"],
                "llm_success_rate": router_metrics["performance"]["llm_success_rate"],
                "user_satisfaction": router_metrics["performance"]["user_satisfaction_avg"],
                "adaptation_score": router_metrics["performance"]["adaptation_score"]
            },
            "routing": {
                "decisions": router_metrics["routes"],
                "percentages": router_metrics["percentages"]
            },
            "performance": router_metrics["performance"],
            "fallback_service": {
                "total_fallbacks": fallback_metrics.total_fallbacks,
                "triggers": fallback_metrics.fallbacks_by_trigger,
                "strategies": fallback_metrics.fallbacks_by_strategy,
                "success_rate": fallback_metrics.success_rate,
                "user_satisfaction": fallback_metrics.user_satisfaction
            }
        }
        
        if detailed:
            base_metrics.update({
                "circuit_breaker": router_metrics["circuit_breaker"],
                "adaptive_system": router_metrics["adaptive_system"],
                "health": router_metrics["health"],
                "configuration": router_metrics["configuration"]
            })
        
        return base_metrics
        
    except Exception as e:
        logger.error(f"Erro ao obter métricas de fallback: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao obter métricas"
        )


@router.get("/insights")
async def get_adaptive_insights(
    availability_router: AvailabilityRouter = Depends(get_availability_router)
) -> Dict[str, Any]:
    """
    Retorna insights do sistema adaptativo.
    
    Returns:
        Dict com insights e recomendações
    """
    try:
        insights = availability_router.get_adaptive_insights()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "adaptive_insights": insights,
            "recommendations": {
                "immediate": insights.get("recommendations", []),
                "long_term": [
                    "Coletar mais feedback de usuários para melhorar precisão",
                    "Monitorar tendências de performance ao longo do tempo",
                    "Ajustar pesos de decisão baseado em padrões identificados"
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter insights adaptativos: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao obter insights"
        )


@router.post("/feedback")
async def submit_user_feedback(
    feedback: FeedbackRequest,
    availability_router: AvailabilityRouter = Depends(get_availability_router)
) -> Dict[str, str]:
    """
    Registra feedback do usuário para aprendizado adaptativo.
    
    Args:
        feedback: Dados do feedback
        
    Returns:
        Confirmação do registro
    """
    try:
        # Converter string para enum
        decision_map = {
            "llm_sql": RouteDecision.LLM_SQL,
            "rule_based": RouteDecision.RULE_BASED,
            "fallback": RouteDecision.FALLBACK
        }
        
        decision = decision_map.get(feedback.decision.lower())
        if not decision:
            raise HTTPException(
                status_code=400,
                detail=f"Decisão inválida: {feedback.decision}. Use: llm_sql, rule_based, ou fallback"
            )
        
        # Registrar feedback
        availability_router.record_user_feedback(
            query=feedback.query,
            decision=decision,
            satisfaction_score=feedback.satisfaction_score,
            comment=feedback.comment
        )
        
        logger.info("Feedback registrado via API", extra={
            "decision": feedback.decision,
            "satisfaction": feedback.satisfaction_score,
            "has_comment": bool(feedback.comment)
        })
        
        return {
            "message": "Feedback registrado com sucesso",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao registrar feedback: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao registrar feedback"
        )


@router.get("/dashboard")
async def get_dashboard_data(
    availability_router: AvailabilityRouter = Depends(get_availability_router),
    fallback_service: FallbackService = Depends(get_fallback_service)
) -> Dict[str, Any]:
    """
    Retorna dados consolidados para dashboard de monitoramento.
    
    Returns:
        Dict com dados otimizados para visualização
    """
    try:
        # Obter dados consolidados
        router_metrics = availability_router.get_metrics()
        router_health = await availability_router.health_check()
        fallback_metrics = fallback_service.get_metrics()
        insights = availability_router.get_adaptive_insights()
        
        # Preparar dados para dashboard
        dashboard_data = {
            "overview": {
                "status": router_health["status"],
                "total_requests": router_metrics["total_requests"],
                "llm_available": router_health["llm_available"],
                "adaptive_active": router_health["adaptive_system_active"]
            },
            "performance": {
                "llm_success_rate": router_metrics["performance"]["llm_success_rate"],
                "rule_success_rate": router_metrics["performance"]["rule_success_rate"],
                "user_satisfaction": router_metrics["performance"]["user_satisfaction_avg"],
                "adaptation_score": router_metrics["performance"]["adaptation_score"]
            },
            "routing_distribution": router_metrics["percentages"],
            "recent_issues": router_health["issues"],
            "recommendations": router_health["recommendations"],
            "circuit_breaker": {
                "status": "open" if router_metrics["circuit_breaker"]["open"] else "closed",
                "activations": router_metrics["circuit_breaker"]["activations_total"]
            },
            "fallback_stats": {
                "total_fallbacks": fallback_metrics.total_fallbacks,
                "success_rate": fallback_metrics.success_rate,
                "most_common_trigger": max(
                    fallback_metrics.fallbacks_by_trigger.items(), 
                    default=("none", 0)
                )[0]
            },
            "trends": {
                "adaptive_trend": insights.get("periods_analysis", {}).get("trend", "unknown"),
                "learning_active": insights.get("learning_active", False),
                "history_size": insights.get("history_size", 0)
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Erro ao obter dados do dashboard: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao obter dados do dashboard"
        ) 