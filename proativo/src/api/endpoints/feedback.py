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
from ..dependencies import get_database_session, get_current_config, get_repository_manager
from ..config import Settings
from ...database.repositories import RepositoryManager
from ...utils.error_handlers import ValidationError, DataProcessingError

# Configurar logging
logger = logging.getLogger(__name__)

# Criar router para endpoints de feedback
router = APIRouter(prefix="/feedback", tags=["feedback"])


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
    repo_manager: RepositoryManager = Depends(get_repository_manager),
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
        repo_manager: Gerenciador de repositories
        settings: Configurações da aplicação
        
    Returns:
        FeedbackResponse: Confirmação do feedback recebido
        
    Raises:
        HTTPException: Erro de validação ou processamento
    """
    try:
        logger.info(f"Receiving feedback for message {request.message_id} - Helpful: {request.helpful}")
        
        # Verificar se já existe feedback para esta mensagem
        existing_feedback = await repo_manager.user_feedback.get_by_message_id(str(request.message_id))
        if existing_feedback:
            logger.warning(f"Feedback already exists for message {request.message_id}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Feedback já foi enviado para esta mensagem"
            )
        
        # Preparar dados do feedback para o banco
        feedback_data = {
            "session_id": str(request.session_id),
            "message_id": str(request.message_id),
            "rating": request.rating,
            "helpful": request.helpful,
            "comment": request.comment,
            "feedback_category": getattr(request, 'category', None),
            "improvement_priority": "high" if not request.helpful else "low",
            "is_processed": False
        }
        
        # Salvar feedback no banco de dados
        feedback = await repo_manager.user_feedback.create(**feedback_data)
        await repo_manager.commit()
        
        logger.info(f"Feedback stored successfully in database for message {request.message_id}")
        
        # Processar métricas em background
        background_tasks.add_task(
            process_feedback_metrics_background,
            {**feedback_data, "feedback_id": feedback.id}
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
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except ValidationError as e:
        logger.warning(f"Validation error in feedback: {str(e)}")
        await repo_manager.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro de validação: {str(e)}"
        )
    
    except Exception as e:
        logger.error(f"Unexpected error in feedback endpoint: {str(e)}")
        await repo_manager.rollback()
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
    repo_manager: RepositoryManager = Depends(get_repository_manager),
    settings: Settings = Depends(get_current_config)
) -> Dict[str, Any]:
    """
    Retorna estatísticas gerais do sistema de feedback.
    
    Args:
        repo_manager: Gerenciador de repositories
        settings: Configurações da aplicação
        
    Returns:
        Dict com estatísticas de feedback
    """
    try:
        logger.info("Generating feedback statistics from database")
        
        # Obter estatísticas do banco de dados
        stats = await repo_manager.user_feedback.get_stats_summary()
        
        # Se não há feedback, retornar valores padrão
        if stats['total_feedback'] == 0:
            return {
                "total_feedback": 0,
                "positive_feedback": 0,
                "negative_feedback": 0,
                "satisfaction_rate": 0.0,
                "avg_rating": 0.0,
                "most_common_issues": [],
                "improvement_suggestions": [
                    "Sistema novo, aguardando feedback dos usuários",
                    "Implementar análise mais detalhada conforme crescer o volume de dados"
                ]
            }
        
        # Obter feedback negativo para análise de padrões
        negative_feedback_list = await repo_manager.user_feedback.list_helpful(helpful=False)
        
        # Analisar comentários negativos para identificar padrões
        negative_comments = [
            f.comment for f in negative_feedback_list 
            if f.comment and f.comment.strip()
        ]
        
        # Análise simples de palavras-chave em comentários negativos
        common_issues = []
        issue_keywords = {
            "informação incorreta": ["incorreto", "errado", "falso", "impreciso"],
            "resposta incompleta": ["incompleto", "faltou", "superficial", "raso"],
            "não entendeu a pergunta": ["não entendeu", "entendeu errado", "pergunta errada"],
            "lentidão": ["lento", "demora", "demorou", "devagar"],
            "interface": ["difícil", "confuso", "interface", "navegação"],
            "relevância": ["irrelevante", "não relacionado", "fora de contexto"]
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
            "total_feedback": stats['total_feedback'],
            "positive_feedback": stats['positive_feedback'],
            "negative_feedback": stats['negative_feedback'],
            "satisfaction_rate": stats['satisfaction_rate'],
            "avg_rating": stats['avg_rating'],
            "most_common_issues": common_issues[:5],
            "improvement_suggestions": [
                "Melhorar precisão das respostas baseada no feedback",
                "Implementar detecção de intent mais robusta",
                "Adicionar mais fontes de dados para respostas completas",
                "Analisar padrões de feedback negativo para melhorias direcionadas"
            ],
            "data_source": "database",
            "last_updated": datetime.now().isoformat()
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