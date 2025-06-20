"""
Endpoint principal de chat para interação com IA do PROAtivo.

Este módulo implementa o endpoint `/chat` que permite aos usuários
fazer consultas em linguagem natural sobre dados de manutenção
de equipamentos elétricos.
"""

import asyncio
import logging
import time
from typing import Dict, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.chat import (
    ChatRequest,
    ChatResponse,
    QueryType,
    ResponseType,
    ChatContext,
    ChatMessage,
)
from ..dependencies import get_database_session, get_current_settings
from ..config import Settings
from ...utils.error_handlers import LLMServiceError, DataProcessingError

# Configurar logging
logger = logging.getLogger(__name__)

# Criar router para endpoints de chat
router = APIRouter(prefix="/chat", tags=["chat"])


async def process_chat_message_background(
    message: str,
    session_id: str,
    processing_start_time: float
) -> None:
    """
    Processa métricas de chat em background.
    
    Args:
        message: Mensagem do usuário
        session_id: ID da sessão
        processing_start_time: Tempo de início do processamento
    """
    processing_time = (time.time() - processing_start_time) * 1000
    logger.info(
        f"Chat processed - Session: {session_id}, "
        f"Message length: {len(message)}, "
        f"Processing time: {processing_time:.2f}ms"
    )


async def mock_llm_service(
    message: str,
    context: ChatContext = None,
    max_results: int = 10
) -> Dict[str, Any]:
    """
    Serviço mock de LLM para desenvolvimento.
    
    Esta função simula o comportamento do serviço LLM real que será
    implementado nas próximas subtarefas.
    
    Args:
        message: Mensagem do usuário
        context: Contexto da conversa
        max_results: Número máximo de resultados
        
    Returns:
        Dict com dados simulados da resposta LLM
    """
    # Simular delay de processamento
    await asyncio.sleep(0.1)
    
    message_lower = message.lower()
    
    # Análise simples de intent
    if any(word in message_lower for word in ["transformador", "equipamento", "ativo"]):
        query_type = QueryType.EQUIPMENT_INFO
        response = f"Encontrei informações sobre equipamentos relacionados à sua consulta: '{message}'. " \
                  f"No momento, estou funcionando em modo de desenvolvimento. " \
                  f"Em breve, terei acesso completo aos dados de manutenção."
        equipment_ids = ["T001", "T002", "T003"] if "transformador" in message_lower else ["EQ001", "EQ002"]
        
    elif any(word in message_lower for word in ["manutenção", "reparo", "conserto"]):
        query_type = QueryType.MAINTENANCE_HISTORY
        response = f"Sua pergunta sobre manutenção foi recebida: '{message}'. " \
                  f"O sistema está em desenvolvimento e em breve fornecerá " \
                  f"informações detalhadas sobre histórico de manutenções."
        equipment_ids = ["T001", "EQ001"]
        
    elif any(word in message_lower for word in ["falha", "problema", "erro", "defeito"]):
        query_type = QueryType.FAILURE_ANALYSIS
        response = f"Identifiquei uma consulta sobre análise de falhas: '{message}'. " \
                  f"O módulo de análise de falhas está sendo desenvolvido para " \
                  f"fornecer insights detalhados sobre problemas em equipamentos."
        equipment_ids = ["T001"]
        
    elif any(word in message_lower for word in ["recomendação", "sugestão", "dica"]):
        query_type = QueryType.RECOMMENDATIONS
        response = f"Sua solicitação por recomendações foi registrada: '{message}'. " \
                  f"O sistema de recomendações inteligentes está sendo desenvolvido " \
                  f"para fornecer sugestões personalizadas de manutenção."
        equipment_ids = []
        
    else:
        query_type = QueryType.GENERAL_QUERY
        response = f"Recebi sua mensagem: '{message}'. " \
                  f"Sou o assistente de IA do PROAtivo, especializado em manutenção " \
                  f"de equipamentos elétricos. Como posso ajudá-lo hoje?"
        equipment_ids = []
    
    # Sugestões de perguntas relacionadas
    followup_suggestions = [
        "Qual é o status atual dos transformadores?",
        "Quando foi a última manutenção do equipamento T001?",
        "Quais equipamentos precisam de manutenção urgente?",
        "Mostre-me o histórico de falhas dos últimos 30 dias"
    ]
    
    return {
        "response": response,
        "query_type": query_type,
        "response_type": ResponseType.SUCCESS,
        "equipment_ids": equipment_ids,
        "data_found": len(equipment_ids),
        "confidence_score": 0.8,
        "sources_used": ["mock_database"],
        "suggested_followup": followup_suggestions[:3],
        "debug_info": {
            "intent_detected": query_type.value,
            "keywords_found": [word for word in message_lower.split() 
                             if word in ["transformador", "manutenção", "falha", "equipamento"]],
            "mock_mode": True
        }
    }


@router.post("/", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_database_session),
    settings: Settings = Depends(get_current_settings),
) -> ChatResponse:
    """
    Endpoint principal para chat com IA sobre manutenção de equipamentos.
    
    Este endpoint:
    - Recebe mensagens em linguagem natural
    - Processa através do sistema RAG (futuro)
    - Retorna respostas inteligentes sobre equipamentos
    - Mantém contexto da conversa
    - Registra métricas e feedback
    
    Args:
        request: Dados da requisição de chat
        background_tasks: Tarefas em background do FastAPI
        db: Sessão do banco de dados
        settings: Configurações da aplicação
        
    Returns:
        ChatResponse com resposta da IA
        
    Raises:
        HTTPException: Erro de validação ou processamento
        LLMServiceError: Erro no serviço de IA
        DataProcessingError: Erro no processamento de dados
    """
    processing_start_time = time.time()
    
    # Gerar ou usar session_id
    session_id = request.session_id or uuid4()
    
    logger.info(f"Processing chat request - Session: {session_id}, Message: {request.message[:100]}...")
    
    try:
        # Validar contexto se fornecido
        context = request.context
        if not context:
            context = ChatContext(session_id=session_id)
        
        # Adicionar mensagem do usuário ao contexto
        user_message = ChatMessage(
            content=request.message,
            role="user"
        )
        context.conversation_history.append(user_message)
        
        # Processar mensagem com serviço mock de LLM
        try:
            llm_result = await mock_llm_service(
                message=request.message,
                context=context,
                max_results=request.max_results
            )
        except Exception as e:
            logger.error(f"Error in LLM service: {str(e)}")
            raise LLMServiceError(f"Erro no serviço de IA: {str(e)}")
        
        # Calcular tempo de processamento
        processing_time_ms = int((time.time() - processing_start_time) * 1000)
        
        # Criar resposta
        response = ChatResponse(
            session_id=session_id,
            response=llm_result["response"],
            query_type=llm_result["query_type"],
            response_type=llm_result["response_type"],
            data_found=llm_result["data_found"],
            equipment_ids=llm_result["equipment_ids"],
            processing_time_ms=processing_time_ms,
            confidence_score=llm_result["confidence_score"],
            sources_used=llm_result["sources_used"],
            suggested_followup=llm_result["suggested_followup"],
            context_updated=True,
            debug_info=llm_result.get("debug_info") if request.include_debug else None
        )
        
        # Adicionar resposta ao contexto
        assistant_message = ChatMessage(
            content=response.response,
            role="assistant",
            metadata={
                "query_type": response.query_type.value,
                "confidence_score": response.confidence_score,
                "processing_time_ms": processing_time_ms
            }
        )
        context.conversation_history.append(assistant_message)
        context.last_query_type = response.query_type
        
        # Registrar métricas em background
        background_tasks.add_task(
            process_chat_message_background,
            request.message,
            str(session_id),
            processing_start_time
        )
        
        logger.info(f"Chat response generated - Session: {session_id}, Type: {response.query_type}")
        
        return response
        
    except LLMServiceError:
        # Re-raise LLM errors
        raise
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Erro interno do servidor ao processar sua mensagem"
        )


@router.get("/session/{session_id}/history")
async def get_chat_history(
    session_id: str,
    limit: int = 50,
    settings: Settings = Depends(get_current_settings)
) -> Dict[str, Any]:
    """
    Recupera histórico de chat de uma sessão.
    
    Args:
        session_id: ID da sessão
        limit: Número máximo de mensagens (padrão: 50)
        settings: Configurações da aplicação
        
    Returns:
        Dict com histórico da conversa
    """
    logger.info(f"Retrieving chat history for session: {session_id}")
    
    # Por enquanto, retorna mock data
    # Futuramente, irá buscar do banco de dados
    return {
        "session_id": session_id,
        "message_count": 0,
        "messages": [],
        "status": "mock_data",
        "note": "Histórico de chat será implementado quando o banco de dados estiver conectado"
    }


@router.delete("/session/{session_id}")
async def clear_chat_session(
    session_id: str,
    settings: Settings = Depends(get_current_settings)
) -> Dict[str, str]:
    """
    Limpa histórico de uma sessão de chat.
    
    Args:
        session_id: ID da sessão a ser limpa
        settings: Configurações da aplicação
        
    Returns:
        Dict com confirmação da operação
    """
    logger.info(f"Clearing chat session: {session_id}")
    
    return {
        "message": f"Sessão {session_id} limpa com sucesso",
        "session_id": session_id,
        "status": "cleared"
    }


@router.get("/types")
async def get_query_types() -> Dict[str, Any]:
    """
    Retorna tipos de consulta suportados pelo sistema.
    
    Returns:
        Dict com tipos de consulta disponíveis
    """
    return {
        "query_types": [
            {
                "type": QueryType.EQUIPMENT_INFO.value,
                "description": "Informações sobre equipamentos específicos",
                "examples": ["Status do transformador T001", "Dados do equipamento EQ123"]
            },
            {
                "type": QueryType.MAINTENANCE_HISTORY.value,
                "description": "Histórico de manutenções realizadas",
                "examples": ["Últimas manutenções do T001", "Histórico de reparos"]
            },
            {
                "type": QueryType.FAILURE_ANALYSIS.value,
                "description": "Análise de falhas e problemas",
                "examples": ["Falhas recentes", "Problemas no transformador"]
            },
            {
                "type": QueryType.PERFORMANCE_METRICS.value,
                "description": "Métricas de performance dos equipamentos",
                "examples": ["Performance do último mês", "Índices de eficiência"]
            },
            {
                "type": QueryType.RECOMMENDATIONS.value,
                "description": "Recomendações de manutenção",
                "examples": ["Sugestões de manutenção", "Próximas ações recomendadas"]
            },
            {
                "type": QueryType.GENERAL_QUERY.value,
                "description": "Consultas gerais sobre o sistema",
                "examples": ["Como funciona o sistema?", "Ajuda com navegação"]
            }
        ],
        "total_types": len(QueryType),
        "status": "active"
    } 