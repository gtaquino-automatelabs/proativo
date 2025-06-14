"""
Endpoint para sistema de feedback de usuários do PROAtivo.

Este módulo implementa endpoints para coletar feedback dos usuários
sobre as respostas da IA, permitindo avaliações 👍/👎 e comentários.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.chat import FeedbackRequest, FeedbackResponse
from ..dependencies import get_database_session, get_current_config
from ..config import Settings
from ...utils.error_handlers import ValidationError, DataProcessingError

# Configurar logging
logger = logging.getLogger(__name__)

# Criar router para endpoints de feedback
router = APIRouter(prefix="/feedback", tags=["feedback"])

# Armazenamento temporário em memória para feedback (até implementar banco)
feedback_storage: Dict[str, Dict[str, Any]] = {}


async def process_feedback_metrics_background(
    feedback_data: Dict[str, Any]
) -> None:
    """
    Processa métricas de feedback em background.
    
    Args:
        feedback_data: Dados do feedback para processamento
    """
    try:
        logger.info(
            f"Processing feedback metrics - "
            f"Helpful: {feedback_data['helpful']}, "
            f"Session: {feedback_data['session_id']}"
        )
        
        # TODO: Implementar análise de sentimento no comentário
        # TODO: Atualizar métricas de qualidade da IA
        # TODO: Identificar padrões de feedback negativo
        
    except Exception as e:
        logger.error(f"Error processing feedback metrics: {str(e)}")


@router.post("/", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_database_session),
    settings: Settings = Depends(get_current_config),
) -> FeedbackResponse:
    """
    Submete feedback do usuário sobre uma resposta da IA.
    
    Este endpoint permite aos usuários:
    - Avaliar respostas com 👍 (helpful=True) ou 👎 (helpful=False)
    - Adicionar comentários explicativos
    - Fornecer contexto adicional sobre problemas
    
    Args:
        request: Dados do feedback incluindo avaliação e comentário
        background_tasks: Tarefas em background do FastAPI
        db: Sessão do banco de dados
        settings: Configurações da aplicação
        
    Returns:
        FeedbackResponse: Confirmação do feedback recebido
        
    Raises:
        HTTPException: Erro de validação ou processamento
    """
    try:
        logger.info(f"Receiving feedback for message {request.message_id} - Helpful: {request.helpful}")
        
        # Preparar dados do feedback
        feedback_data = {
            "feedback_id": str(request.message_id),
            "message_id": str(request.message_id),
            "session_id": str(request.session_id),
            "helpful": request.helpful,
            "comment": request.comment,
            "timestamp": datetime.now(),
            "rating": request.rating if hasattr(request, 'rating') else None,
            "category": request.category if hasattr(request, 'category') else None
        }
        
        # Armazenar feedback (temporariamente em memória)
        feedback_storage[str(request.message_id)] = feedback_data
        
        logger.info(f"Feedback stored successfully for message {request.message_id}")
        
        # Processar métricas em background
        background_tasks.add_task(
            process_feedback_metrics_background,
            feedback_data
        )
        
        # Criar resposta personalizada baseada no feedback
        if request.helpful:
            message = "Obrigado pelo feedback positivo! Continuaremos melhorando para atendê-lo melhor."
        else:
            message = "Obrigado pelo feedback. Suas observações nos ajudam a melhorar nosso sistema."
            
        if request.comment:
            message += " Seu comentário foi registrado e será analisado pela nossa equipe."
        
        response = FeedbackResponse(
            message=message,
            timestamp=datetime.now()
        )
        
        logger.info(f"Feedback response sent for message {request.message_id}")
        return response
        
    except ValidationError as e:
        logger.warning(f"Validation error in feedback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro de validação: {str(e)}"
        )
    
    except Exception as e:
        logger.error(f"Unexpected error in feedback endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao processar feedback"
        )


@router.get("/session/{session_id}")
async def get_session_feedback(
    session_id: UUID,
    settings: Settings = Depends(get_current_config)
) -> Dict[str, Any]:
    """
    Recupera todo o feedback de uma sessão específica.
    
    Args:
        session_id: ID da sessão para recuperar feedback
        settings: Configurações da aplicação
        
    Returns:
        Dict com feedback da sessão
    """
    try:
        logger.info(f"Retrieving feedback for session: {session_id}")
        
        # Filtrar feedback por sessão
        session_feedback = {
            feedback_id: feedback_data
            for feedback_id, feedback_data in feedback_storage.items()
            if feedback_data.get("session_id") == str(session_id)
        }
        
        # Calcular estatísticas
        total_feedback = len(session_feedback)
        positive_feedback = sum(1 for f in session_feedback.values() if f.get("helpful", False))
        negative_feedback = total_feedback - positive_feedback
        
        return {
            "session_id": str(session_id),
            "total_feedback": total_feedback,
            "positive_feedback": positive_feedback,
            "negative_feedback": negative_feedback,
            "satisfaction_rate": positive_feedback / total_feedback if total_feedback > 0 else 0,
            "feedback_items": list(session_feedback.values())
        }
        
    except Exception as e:
        logger.error(f"Error retrieving session feedback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao recuperar feedback da sessão"
        )


@router.get("/stats")
async def get_feedback_stats(
    settings: Settings = Depends(get_current_config)
) -> Dict[str, Any]:
    """
    Retorna estatísticas gerais do sistema de feedback.
    
    Args:
        settings: Configurações da aplicação
        
    Returns:
        Dict com estatísticas de feedback
    """
    try:
        logger.info("Generating feedback statistics")
        
        if not feedback_storage:
            return {
                "total_feedback": 0,
                "satisfaction_rate": 0,
                "most_common_issues": [],
                "improvement_suggestions": []
            }
        
        # Calcular estatísticas básicas
        total_feedback = len(feedback_storage)
        positive_feedback = sum(1 for f in feedback_storage.values() if f.get("helpful", False))
        satisfaction_rate = positive_feedback / total_feedback if total_feedback > 0 else 0
        
        # Analisar comentários negativos para identificar padrões
        negative_comments = [
            f.get("comment", "")
            for f in feedback_storage.values()
            if not f.get("helpful", True) and f.get("comment")
        ]
        
        # Análise simples de palavras-chave em comentários negativos
        common_issues = []
        issue_keywords = {
            "informação incorreta": ["incorreto", "errado", "falso"],
            "resposta incompleta": ["incompleto", "faltou", "superficial"],
            "não entendeu a pergunta": ["não entendeu", "entendeu errado", "pergunta errada"],
            "lentidão": ["lento", "demora", "demorou"],
            "interface": ["difícil", "confuso", "interface"]
        }
        
        for issue, keywords in issue_keywords.items():
            count = sum(
                1 for comment in negative_comments
                if any(keyword in comment.lower() for keyword in keywords)
            )
            if count > 0:
                common_issues.append({"issue": issue, "count": count})
        
        # Ordenar por frequência
        common_issues.sort(key=lambda x: x["count"], reverse=True)
        
        return {
            "total_feedback": total_feedback,
            "positive_feedback": positive_feedback,
            "negative_feedback": total_feedback - positive_feedback,
            "satisfaction_rate": round(satisfaction_rate, 3),
            "most_common_issues": common_issues[:5],
            "recent_feedback": list(feedback_storage.values())[-10:],  # Últimos 10
            "improvement_suggestions": [
                "Melhorar precisão das respostas baseada no feedback",
                "Implementar detecção de intent mais robusta",
                "Adicionar mais fontes de dados para respostas completas"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error generating feedback stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao gerar estatísticas de feedback"
        )


@router.delete("/session/{session_id}")
async def clear_session_feedback(
    session_id: UUID,
    settings: Settings = Depends(get_current_config)
) -> Dict[str, str]:
    """
    Remove todo o feedback de uma sessão específica.
    
    Args:
        session_id: ID da sessão para limpar feedback
        settings: Configurações da aplicação
        
    Returns:
        Dict com confirmação da operação
    """
    try:
        logger.info(f"Clearing feedback for session: {session_id}")
        
        # Remover feedback da sessão
        session_feedback_ids = [
            feedback_id
            for feedback_id, feedback_data in feedback_storage.items()
            if feedback_data.get("session_id") == str(session_id)
        ]
        
        for feedback_id in session_feedback_ids:
            del feedback_storage[feedback_id]
        
        logger.info(f"Cleared {len(session_feedback_ids)} feedback items for session {session_id}")
        
        return {
            "message": f"Feedback da sessão {session_id} removido com sucesso",
            "session_id": str(session_id),
            "items_removed": len(session_feedback_ids)
        }
        
    except Exception as e:
        logger.error(f"Error clearing session feedback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao limpar feedback da sessão"
        )


@router.get("/message/{message_id}")
async def get_message_feedback(
    message_id: UUID,
    settings: Settings = Depends(get_current_config)
) -> Dict[str, Any]:
    """
    Recupera feedback específico de uma mensagem.
    
    Args:
        message_id: ID da mensagem para recuperar feedback
        settings: Configurações da aplicação
        
    Returns:
        Dict com feedback da mensagem ou None se não encontrado
    """
    try:
        logger.info(f"Retrieving feedback for message: {message_id}")
        
        feedback_data = feedback_storage.get(str(message_id))
        
        if not feedback_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Feedback não encontrado para esta mensagem"
            )
        
        return {
            "message_id": str(message_id),
            "feedback": feedback_data,
            "found": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving message feedback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao recuperar feedback da mensagem"
        ) 