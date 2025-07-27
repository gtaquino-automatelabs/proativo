"""
Endpoints de gerenciamento do sistema de fallback.

Este módulo fornece endpoints para:
- Monitorar métricas do sistema de fallback
- Coletar feedback específico sobre respostas de fallback
- Documentar triggers disponíveis no sistema
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
# Pydantic removido - modelos não mais necessários

from ..services.fallback_service import FallbackService
from ..dependencies import get_fallback_service
from ...utils.logger import get_logger

# Configurar logger e router
logger = get_logger(__name__)
router = APIRouter(prefix="/fallback", tags=["Fallback Management"])


# Modelos removidos - não mais necessários após limpeza


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





 