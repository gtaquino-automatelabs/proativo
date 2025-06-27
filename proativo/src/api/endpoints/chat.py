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
from sqlalchemy import text

from ..models.chat import (
    ChatRequest,
    ChatResponse,
    QueryType,
    ResponseType,
    ChatContext,
    ChatMessage,
)
from ..dependencies import get_database_session, get_current_settings, get_llm_service, get_query_processor, get_availability_router
from ..config import Settings
from ...utils.error_handlers import LLMServiceError, DataProcessingError
from ..services.llm_service import LLMService
from ..services.rag_service import RAGService
from ..services.availability_router import AvailabilityRouter, RouteDecision

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
    llm_service: LLMService = Depends(get_llm_service),
    query_processor = Depends(get_query_processor),
    availability_router: AvailabilityRouter = Depends(get_availability_router),
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
        
        # Processar mensagem com Query Processor, RAG e LLM services integrados
        try:
            # 1. ROTEAMENTO INTELIGENTE (NOVA FUNCIONALIDADE)
            logger.info("Starting intelligent routing")
            route_decision, route_reason = await availability_router.route_query(
                request.message, 
                context={"session_id": str(session_id)}
            )
            
            logger.info(f"Route decision: {route_decision.value}, reason: {route_reason}")
            
            # 2. PROCESSAR BASEADO NA ROTA ESCOLHIDA
            route_result = None
            if route_decision == RouteDecision.LLM_SQL:
                # Usar novo sistema LLM SQL
                logger.info("Processing with LLM SQL system")
                route_result = await availability_router.process_with_llm_sql(request.message)
                
            elif route_decision == RouteDecision.RULE_BASED:
                # Usar sistema baseado em regras existente
                logger.info("Processing with rule-based system")
                route_result = await availability_router.process_with_rule_based(request.message)
                
            else:  # RouteDecision.FALLBACK
                # Sistema de fallback ativo
                logger.info("Using fallback system")
                route_result = {
                    "success": False,
                    "route": RouteDecision.FALLBACK,
                    "message": "Sistema temporariamente em modo de fallback",
                    "suggestions": ["Tente novamente em alguns minutos", "Reformule sua pergunta"],
                    "method": "fallback"
                }
            
            # 3. SE LLM SQL FOI USADO E RETORNOU SQL, EXECUTAR QUERY
            structured_data = None
            if route_result.get("sql"):
                try:
                    logger.info("Executing SQL from LLM")
                    result = await db.execute(text(route_result["sql"]))
                    rows = result.fetchall()
                    
                    if rows:
                        columns = result.keys()
                        structured_data = [dict(zip(columns, row)) for row in rows]
                        logger.info(f"SQL executed successfully: {len(structured_data)} rows")
                    
                except Exception as sql_error:
                    logger.warning(f"SQL execution failed: {sql_error}")
                    # Se SQL falhou, usar fallback
                    from ..services.fallback_service import FallbackService, FallbackTrigger
                    fallback_service = FallbackService()
                    fallback_response = fallback_service.generate_fallback_response(
                        FallbackTrigger.QUERY_EXECUTION_ERROR,
                        request.message
                    )
                    route_result = {
                        "success": False,
                        "route": RouteDecision.FALLBACK,
                        "message": fallback_response.message,
                        "suggestions": fallback_response.suggestions,
                        "method": "fallback_after_sql_error"
                    }
            
            # 4. CONTINUAR COM FLUXO EXISTENTE SE NECESSÁRIO
            query_results = []
            llm_result = None
            
            # Se não temos uma resposta completa ainda, usar RAG + LLM existente
            if not route_result.get("success") or route_decision == RouteDecision.RULE_BASED:
                # ANÁLISE INTELIGENTE DA CONSULTA (mantendo compatibilidade)
                logger.info("Running traditional query analysis")
                query_analysis = await query_processor.process_query(request.message)
                
                logger.info(f"Query analysis: intent={query_analysis.intent.value}, "
                           f"entities={len(query_analysis.entities)}, "
                           f"confidence={query_analysis.confidence_score:.2f}")
                
                # BUSCAR DADOS RELEVANTES VIA RAG
                try:
                    rag_service = RAGService()
                    await rag_service.index_data_sources()
                    rag_context = await rag_service.retrieve_context(
                        query=request.message,
                        max_chunks=5
                    )
                    
                    for chunk in rag_context.chunks:
                        query_results.append({
                            "source": chunk.source,
                            "content": chunk.content,
                            "metadata": chunk.metadata,
                            "relevance_score": chunk.relevance_score
                        })
                    
                    logger.info(f"RAG context retrieved: {len(query_results)} chunks found")
                    
                except Exception as rag_error:
                    logger.warning(f"RAG service error (using fallback): {rag_error}")
                    query_results = []
                
                # EXECUTAR SQL QUERY SE GERADA PELO QUERY PROCESSOR (sistema antigo)
                if not structured_data and query_analysis.sql_query:
                    try:
                        result = await db.execute(
                            text(query_analysis.sql_query),
                            query_analysis.parameters
                        )
                        rows = result.fetchall()
                        
                        if rows:
                            columns = result.keys()
                            structured_data = [dict(zip(columns, row)) for row in rows]
                            logger.info(f"Traditional SQL query executed: {len(structured_data)} rows returned")
                        
                    except Exception as sql_error:
                        logger.warning(f"Traditional SQL query execution failed: {sql_error}")
                        structured_data = None
                
                # USAR LLM COM CONTEXTO ENRIQUECIDO
                llm_result = await llm_service.generate_response(
                    user_query=request.message,
                    query_results=query_results,
                    context={
                        "query_analysis": {
                            "intent": query_analysis.intent.value,
                            "entities": [{"type": e.type.value, "value": e.value} for e in query_analysis.entities],
                            "confidence": query_analysis.confidence_score
                        },
                        "structured_data": structured_data,
                        "session_context": context.dict() if context else None,
                        "route_info": {
                            "decision": route_decision.value,
                            "reason": route_reason,
                            "llm_sql_used": route_decision == RouteDecision.LLM_SQL
                        }
                    },
                    session_id=str(session_id)
                )
            
            # 5. DETERMINAR RESPOSTA FINAL
            if route_result.get("success") and route_decision == RouteDecision.LLM_SQL and structured_data:
                # LLM SQL foi bem-sucedido e temos dados
                final_response = f"Consultei os dados usando IA avançada:\n\n"
                if len(structured_data) > 0:
                    # Formatar dados de forma amigável
                    if len(structured_data) <= 5:
                        for row in structured_data:
                            final_response += f"• {dict(row)}\n"
                    else:
                        final_response += f"Encontrei {len(structured_data)} registros. Primeiros 3:\n"
                        for row in structured_data[:3]:
                            final_response += f"• {dict(row)}\n"
                        final_response += f"\n... e mais {len(structured_data) - 3} registros."
                else:
                    final_response += "Nenhum resultado encontrado para sua consulta."
                
                confidence_score = 0.9  # Alta confiança para LLM SQL
                processing_time_ms = route_result.get("response_time_ms", 1000)
                sources_used = ["llm_sql", "database"]
                
            elif llm_result:
                # Usar resposta do LLM tradicional
                final_response = llm_result["response"]
                confidence_score = max(
                    query_analysis.confidence_score if 'query_analysis' in locals() else 0.8,
                    llm_result.get("confidence_score", 0.8)
                )
                processing_time_ms = llm_result.get("processing_time", 
                                                   int((time.time() - processing_start_time) * 1000))
                sources_used = llm_result.get("sources", ["llm"]) + (["database"] if structured_data else [])
                
            else:
                # Usar resposta de fallback
                final_response = route_result.get("message", "Desculpe, não consegui processar sua consulta no momento.")
                confidence_score = 0.3
                processing_time_ms = route_result.get("response_time_ms", 
                                                     int((time.time() - processing_start_time) * 1000))
                sources_used = ["fallback"]
            
            # Usar tempo de processamento do LLM real ou calcular
            processing_time_ms = llm_result.get("processing_time", int((time.time() - processing_start_time) * 1000))
            
            # Mapear QueryIntent para QueryType
            query_type_mapping = {
                "equipment_search": QueryType.EQUIPMENT_INFO,
                "maintenance_history": QueryType.MAINTENANCE_HISTORY,
                "last_maintenance": QueryType.MAINTENANCE_HISTORY,
                "count_equipment": QueryType.EQUIPMENT_INFO,
                "count_maintenance": QueryType.MAINTENANCE_HISTORY,
                "equipment_status": QueryType.EQUIPMENT_INFO,
                "failure_analysis": QueryType.FAILURE_ANALYSIS,
                "upcoming_maintenance": QueryType.MAINTENANCE_HISTORY,
                "overdue_maintenance": QueryType.MAINTENANCE_HISTORY,
                "general_query": QueryType.GENERAL_QUERY,
            }
            
            # Determinar query type baseado no contexto
            if 'query_analysis' in locals():
                mapped_query_type = query_type_mapping.get(query_analysis.intent.value, QueryType.GENERAL_QUERY)
            else:
                mapped_query_type = QueryType.GENERAL_QUERY
            
            # Calcular dados encontrados: RAG + SQL results
            total_data_found = len(query_results)
            if structured_data:
                total_data_found += len(structured_data)
            
            # Extrair IDs de equipamentos das entidades identificadas
            equipment_ids = []
            if 'query_analysis' in locals():
                equipment_ids = [e.normalized_value for e in query_analysis.entities if e.type.value == "equipment_id"]
            
            # Combinar sugestões do Query Processor com LLM/Route
            combined_suggestions = []
            if 'query_analysis' in locals():
                combined_suggestions.extend(query_analysis.suggestions)
            if llm_result and llm_result.get("suggestions"):
                combined_suggestions.extend(llm_result["suggestions"])
            if route_result and route_result.get("suggestions"):
                combined_suggestions.extend(route_result["suggestions"])
            
            unique_suggestions = list(dict.fromkeys(combined_suggestions))[:4]  # Remover duplicatas e limitar
            
            # Criar resposta enriquecida com análise inteligente
            response = ChatResponse(
                session_id=session_id,
                response=final_response,
                query_type=mapped_query_type,
                response_type=ResponseType.SUCCESS,
                data_found=total_data_found,
                equipment_ids=equipment_ids,
                processing_time_ms=processing_time_ms,
                confidence_score=confidence_score,
                sources_used=sources_used,
                suggested_followup=unique_suggestions,
                context_updated=True,
                debug_info={
                    "llm_service": "real",
                    "routing": {
                        "decision": route_decision.value,
                        "reason": route_reason,
                        "llm_sql_success": route_result.get("success") if route_decision == RouteDecision.LLM_SQL else None,
                        "method_used": route_result.get("method", "unknown")
                    },
                    "query_processor": {
                        "intent": query_analysis.intent.value if 'query_analysis' in locals() else "not_analyzed",
                        "entities_found": len(query_analysis.entities) if 'query_analysis' in locals() else 0,
                        "sql_generated": bool(query_analysis.sql_query) if 'query_analysis' in locals() else False,
                        "structured_data_rows": len(structured_data) if structured_data else 0
                    },
                    "cache_used": llm_result.get("cache_used", False) if llm_result else False
                } if request.include_debug else None
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
        
        except Exception as e:
            logger.error(f"Error in LLM service: {str(e)}")
            raise LLMServiceError(f"Erro no serviço de IA: {str(e)}")
        
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