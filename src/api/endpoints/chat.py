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
from ..dependencies import get_database_session, get_current_settings, get_llm_service, get_query_processor, get_repository_manager 
from ..config import Settings
from ...utils.error_handlers import LLMServiceError, DataProcessingError
from ..services.llm_service import LLMService
from ..services.rag_service import RAGService
from ...database.repositories import RepositoryManager 

# IMPORTANTE: Importe QueryEntity diretamente do módulo query_processor
from ..services.query_processor import QueryEntity # <--- ADICIONE ESTA LINHA

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
    repo_manager: RepositoryManager = Depends(get_repository_manager), 
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
        llm_service: Serviço LLM
        query_processor: Processador de consultas
        repo_manager: Gerenciador de repositórios (NOVO)
        
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
            # 1. ANÁLISE INTELIGENTE DA CONSULTA
            logger.info("Starting intelligent query analysis")
            query_analysis = await query_processor.process_query(request.message)
            
            logger.info(f"Query analysis: intent={query_analysis.intent.value}, "
                       f"entities={len(query_analysis.entities)}, "
                       f"confidence={query_analysis.confidence_score:.2f}, "
                       f"method={query_analysis.processing_method}")
            
            # Inicializar variáveis comuns para ambos os fluxos
            query_results = []
            structured_data = None
            
            # Se Vanna complete workflow foi usado, pular RAG/LLM e usar resposta direta
            if query_analysis.processing_method == "vanna_complete":
                logger.info("Using Vanna complete workflow response directly")
                
                # Extrair resposta já pronta do QueryAnalysis
                llm_result = {
                    "response": query_analysis.explanation or "Resposta processada pelo Vanna.ai",
                    "confidence_score": query_analysis.confidence_score,
                    "suggestions": query_analysis.suggestions,
                    "sources": ["vanna_complete"],
                    "processing_time": int((time.time() - processing_start_time) * 1000)
                }
                
                # Pular para criação da resposta final
                processing_time_ms = llm_result["processing_time"]
                
            else:
                # Fluxo tradicional: RAG + LLM Service
                logger.info("Using traditional RAG + LLM workflow")
                
                # NOVO: Resolver SAP Location ID a partir da abreviação (se houver)
                # Este passo é crucial para que o SQL possa usar o UUID
                sap_location_id_filter = None
                # Acessando QueryEntity diretamente da classe importada
                sap_location_abbreviations = [e.normalized_value for e in query_analysis.entities if e.type == QueryEntity.SAP_LOCATION_ABBREVIATION]
                
                if sap_location_abbreviations:
                    # Assumimos que o primeiro é o mais relevante
                    abbreviation_to_search = sap_location_abbreviations[0]
                    sap_location_obj = await repo_manager.sap_location.get_by_abbreviation(abbreviation_to_search)
                    if sap_location_obj:
                        sap_location_id_filter = str(sap_location_obj.id)
                        logger.info(f"Resolved SAP Location ID for {abbreviation_to_search}: {sap_location_id_filter}")
                    else:
                        logger.warning(f"SAP Location object not found for abbreviation: {abbreviation_to_search}")


                # 2. BUSCAR DADOS RELEVANTES VIA RAG
                try:
                    # Inicializar RAG service
                    rag_service = RAGService()
                    
                    # Indexar dados (cache interno do RAG service evita reindexação)
                    await rag_service.index_data_sources()
                    logger.info("RAG service initialized successfully")
                    
                    # Recuperar contexto relevante
                    rag_context = await rag_service.retrieve_context(
                        query=request.message,
                        max_chunks=5
                    )
                    
                    # Preparar dados para o LLM
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
                
                # 3. EXECUTAR SQL QUERY SE GERADA PELO QUERY PROCESSOR
                structured_data = None
                if query_analysis.sql_query:
                    try:
                        # Passar o sap_location_id_filter para os parâmetros da query
                        sql_parameters = query_analysis.parameters.copy()
                        if sap_location_id_filter:
                            sql_parameters['sap_location_id'] = sap_location_id_filter
                        
                        # Debug logging detalhado
                        logger.info(f"SQL Debug - Query: {query_analysis.sql_query[:200]}...")
                        logger.info(f"SQL Debug - Parameters: {sql_parameters}")
                        
                        # Executar consulta SQL do Query Processor
                        result = await db.execute(
                            text(query_analysis.sql_query),
                            sql_parameters # Usar os parâmetros atualizados
                        )
                        rows = result.fetchall()
                        
                        # Converter resultado para formato estruturado
                        if rows:
                            columns = result.keys()
                            structured_data = [dict(zip(columns, row)) for row in rows]
                            logger.info(f"SQL query executed: {len(structured_data)} rows returned")
                        else:
                            logger.info("SQL query executed successfully but returned no rows")
                        
                    except Exception as sql_error:
                        logger.error(f"SQL query execution failed: {sql_error}")
                        logger.error(f"SQL Query: {query_analysis.sql_query}")
                        logger.error(f"SQL Parameters: {sql_parameters}")
                        import traceback
                        logger.error(f"Stack trace: {traceback.format_exc()}")
                        structured_data = None
                
                # 4. USAR LLM COM CONTEXTO ENRICHED
                llm_result = await llm_service.generate_response(
                    user_query=request.message,
                    sql_query=query_analysis.sql_query, # Passar a SQL gerada para o LLMService para debugging
                    query_results=query_results,
                    context={
                        "query_analysis": {
                            "intent": query_analysis.intent.value,
                            "entities": [{"type": e.type.value, "value": e.value} for e in query_analysis.entities],
                            "confidence": query_analysis.confidence_score
                        },
                        "structured_data": structured_data,
                        "session_context": context.dict() if context else None
                    },
                    session_id=str(session_id)
                )
            
        except Exception as e:
            logger.error(f"Error in LLM service: {str(e)}")
            raise LLMServiceError(f"Erro no serviço de IA: {str(e)}")
        
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
            "upcoming_maintenance": QueryType.MAINTENANCE_SCHEDULE, # Mapear para MAINTENANCE_SCHEDULE
            "overdue_maintenance": QueryType.MAINTENANCE_HISTORY,
            "general_query": QueryType.GENERAL_QUERY,
            # NOVOS MAPPINGS PARA AS NOVAS INTENÇÕES
            "pmm2_plan_search": QueryType.MAINTENANCE_SCHEDULE, # Usar MAINTENANCE_SCHEDULE para PMM2
            "sap_location_search": QueryType.EQUIPMENT_INFO, # Pode ser GENERAL_QUERY ou um novo SAP_LOCATION_INFO
            "equipment_by_location": QueryType.EQUIPMENT_INFO,
        }
        
        mapped_query_type = query_type_mapping.get(query_analysis.intent.value, QueryType.UNKNOWN) # Use QueryType.UNKNOWN for unmapped
        
        # Calcular dados encontrados: RAG + SQL results
        total_data_found = len(query_results)
        if structured_data:
            total_data_found += len(structured_data)
        
        # Extrair IDs de equipamentos das entidades identificadas
        equipment_ids = [e.normalized_value for e in query_analysis.entities if e.type.value == "equipment_id"]
        
        # Combinar sugestões do Query Processor com LLM
        combined_suggestions = query_analysis.suggestions + llm_result.get("suggestions", [])
        unique_suggestions = list(dict.fromkeys(combined_suggestions))[:4]  # Remover duplicatas e limitar
        
        # Criar resposta enriquecida com análise inteligente
        response = ChatResponse(
            session_id=session_id,
            response=llm_result["response"],
            query_type=mapped_query_type,
            response_type=ResponseType.SUCCESS,
            data_found=total_data_found,
            equipment_ids=equipment_ids,
            processing_time_ms=processing_time_ms,
            confidence_score=max(query_analysis.confidence_score, llm_result.get("confidence_score", 0.8)),
            sources_used=llm_result.get("sources", ["llm"]) + (["database"] if structured_data else []),
            suggested_followup=unique_suggestions,
            context_updated=True,
            debug_info={
                "llm_service": "real",
                "query_processor": {
                    "intent": query_analysis.intent.value,
                    "entities_found": len(query_analysis.entities),
                    "sql_generated": bool(query_analysis.sql_query),
                    "structured_data_rows": len(structured_data) if structured_data else 0,
                    "sql_query": query_analysis.sql_query, # Adicionado para debug
                    "sql_parameters": str(query_analysis.parameters), # Adicionado para debug
                },
                "cache_used": llm_result.get("cache_used", False)
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
        
    except LLMServiceError:
        # Re-raise LLM errors
        raise
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Erro interno do servidor ao processar sua mensagem"
        )