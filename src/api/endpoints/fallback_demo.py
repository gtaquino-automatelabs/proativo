"""
Endpoint para demonstração do sistema de fallback.

Este endpoint permite testar diferentes cenários de fallback
sem depender de falhas reais do sistema LLM.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from ..services.fallback_service import FallbackService, FallbackTrigger
from ..dependencies import get_fallback_service
from ...utils.logger import get_logger

# Configurar logger e router
logger = get_logger(__name__)
router = APIRouter(prefix="/fallback", tags=["fallback", "demo"])


class FallbackDemoRequest(BaseModel):
    """Request para demonstração de fallback."""
    user_query: str
    trigger_type: str  # Tipo de trigger para simular
    context: Optional[Dict[str, Any]] = None


class FallbackDemoResponse(BaseModel):
    """Response da demonstração de fallback."""
    message: str
    suggestions: List[str]
    strategy_used: str
    trigger: str
    confidence: float
    actionable: bool
    metadata: Dict[str, Any]


@router.get("/triggers")
async def list_available_triggers() -> Dict[str, List[str]]:
    """
    Lista todos os triggers de fallback disponíveis para teste.
    
    Returns:
        Dict com triggers disponíveis e suas descrições
    """
    triggers_info = {
        "available_triggers": [
            {
                "name": "llm_error",
                "description": "Simula erro geral do LLM"
            },
            {
                "name": "empty_response", 
                "description": "Simula resposta vazia do LLM"
            },
            {
                "name": "low_confidence",
                "description": "Simula resposta com baixa confiança"
            },
            {
                "name": "unsupported_query",
                "description": "Simula consulta não suportada"
            },
            {
                "name": "timeout",
                "description": "Simula timeout na API"
            },
            {
                "name": "api_quota_exceeded",
                "description": "Simula quota da API excedida"
            },
            {
                "name": "invalid_response",
                "description": "Simula resposta inadequada do LLM"
            },
            {
                "name": "out_of_domain",
                "description": "Simula consulta fora do domínio"
            }
        ]
    }
    
    return triggers_info


@router.post("/test", response_model=FallbackDemoResponse)
async def test_fallback_scenario(
    request: FallbackDemoRequest,
    fallback_service: FallbackService = Depends(get_fallback_service)
) -> FallbackDemoResponse:
    """
    Testa um cenário específico de fallback.
    
    Args:
        request: Dados do teste incluindo query e trigger
        fallback_service: Serviço de fallback injetado
        
    Returns:
        Resposta de fallback gerada
        
    Raises:
        HTTPException: Se trigger inválido ou erro no processamento
    """
    try:
        # Validar trigger
        try:
            trigger = FallbackTrigger(request.trigger_type)
        except ValueError:
            available = [t.value for t in FallbackTrigger]
            raise HTTPException(
                status_code=400,
                detail=f"Trigger inválido. Disponíveis: {available}"
            )
        
        logger.info("Testando cenário de fallback", extra={
            "trigger": trigger.value,
            "query": request.user_query[:50]
        })
        
        # Gerar resposta de fallback
        fallback_response = fallback_service.generate_fallback_response(
            trigger=trigger,
            original_query=request.user_query,
            context=request.context or {}
        )
        
        # Converter para formato de resposta
        response = FallbackDemoResponse(
            message=fallback_response.message,
            suggestions=fallback_response.suggestions,
            strategy_used=fallback_response.strategy_used.value,
            trigger=fallback_response.trigger.value,
            confidence=fallback_response.confidence,
            actionable=fallback_response.actionable,
            metadata=fallback_response.metadata
        )
        
        logger.info("Teste de fallback concluído", extra={
            "strategy": fallback_response.strategy_used.value,
            "confidence": fallback_response.confidence
        })
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no teste de fallback: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno no teste de fallback: {str(e)}"
        )


@router.get("/metrics")
async def get_fallback_metrics(
    fallback_service: FallbackService = Depends(get_fallback_service)
) -> Dict[str, Any]:
    """
    Retorna métricas do sistema de fallback.
    
    Returns:
        Dict com métricas detalhadas
    """
    try:
        metrics = fallback_service.get_metrics()
        
        return {
            "total_fallbacks": metrics.total_fallbacks,
            "fallbacks_by_trigger": metrics.fallbacks_by_trigger,
            "fallbacks_by_strategy": metrics.fallbacks_by_strategy,
            "success_rate": metrics.success_rate,
            "user_satisfaction": metrics.user_satisfaction,
            "health_status": fallback_service.get_health_status()
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter métricas: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao obter métricas: {str(e)}"
        )


@router.post("/feedback")
async def submit_fallback_feedback(
    response_id: str,
    rating: int,
    comment: Optional[str] = None,
    fallback_service: FallbackService = Depends(get_fallback_service)
) -> Dict[str, str]:
    """
    Submete feedback sobre uma resposta de fallback.
    
    Args:
        response_id: ID da resposta
        rating: Avaliação de 1-5
        comment: Comentário opcional
        fallback_service: Serviço de fallback
        
    Returns:
        Confirmação do feedback
        
    Raises:
        HTTPException: Se dados inválidos
    """
    try:
        if not 1 <= rating <= 5:
            raise HTTPException(
                status_code=400,
                detail="Rating deve estar entre 1 e 5"
            )
        
        fallback_service.record_user_feedback(response_id, rating, comment)
        
        logger.info("Feedback registrado", extra={
            "response_id": response_id,
            "rating": rating,
            "has_comment": bool(comment)
        })
        
        return {
            "status": "success",
            "message": "Feedback registrado com sucesso"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao registrar feedback: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao registrar feedback: {str(e)}"
        )


@router.get("/health")
async def fallback_health_check(
    fallback_service: FallbackService = Depends(get_fallback_service)
) -> Dict[str, Any]:
    """
    Verifica a saúde do sistema de fallback.
    
    Returns:
        Status de saúde detalhado
    """
    try:
        health_status = fallback_service.get_health_status()
        
        return {
            "service": "fallback_system",
            "timestamp": "2024-01-01T00:00:00Z",  # Placeholder
            **health_status
        }
        
    except Exception as e:
        logger.error(f"Erro no health check: {str(e)}")
        return {
            "service": "fallback_system",
            "status": "critical",
            "error": str(e)
        }


# Exemplo de consultas para teste
EXAMPLE_QUERIES = [
    "Status dos transformadores da subestação Norte",
    "Manutenções programadas para amanhã", 
    "Qual a receita do bolo de chocolate?",  # Fora do domínio
    "Equipamentos com mais falhas",
    "Como fazer um curso de culinária?",  # Fora do domínio
    "Custos de manutenção este mês",
    "Transformador T001 precisa de reparo?",
    "Histórico de falhas dos geradores"
]


@router.get("/examples")
async def get_example_queries() -> Dict[str, List[str]]:
    """
    Retorna exemplos de consultas para teste.
    
    Returns:
        Lista de consultas de exemplo
    """
    return {
        "example_queries": EXAMPLE_QUERIES,
        "usage": "Use essas consultas com diferentes triggers para testar cenários de fallback"
    } 