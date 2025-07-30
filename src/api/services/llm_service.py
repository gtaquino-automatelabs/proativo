"""
Serviço de integração com Google Gemini LLM.

Este módulo implementa a integração completa com o Google Gemini 2.5 Flash,
incluindo prompts estruturados, validação, cache inteligente, tratamento de erros e fallback
"""

import asyncio
import json
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
import logging

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.api_core import exceptions as google_exceptions

from ..config import get_settings
from ...utils.error_handlers import LLMServiceError as LLMError, ValidationError
from ...utils.logger import get_logger
from .cache_service import CacheService, CacheStrategy, CacheStatus # Import CacheStatus here
# Fallback e cache services serão importados dinamicamente quando disponíveis

# Configurar logger
logger = get_logger(__name__)


class LLMService:
    """
    Serviço principal de integração com Google Gemini LLM.
    
    Responsabilidades:
    - Integração com Google Gemini 2.5 Flash API
    - Prompts estruturados por tipo de consulta
    - Cache inteligente com detecção de similaridade
    - Validação e sanitização de respostas
    - Sistema de fallback e retry automático
    - Monitoramento de custos e performance
    """
    
    def __init__(self):
        """Inicializa o serviço LLM."""
        self.settings = get_settings()
        self._client = None
        self._model = None
        self._initialize_gemini()
        
        # Inicializar sistemas opcionais
        self.fallback_service = None
        self.cache_service = None
        
        # Tentar inicializar fallback e cache se disponíveis
        self._init_optional_services()
        
        # Métricas
        self.request_count = 0
        self.cache_hits = 0
        self.error_count = 0
        self.fallback_used_count = 0
        
        # Métricas de queries "não sei"
        self.unknown_query_count = 0
        self.unknown_query_categories = {
            "knowledge_gap": 0,
            "data_gap": 0,
            "capability_limitation": 0,
            "unsupported_query_type": 0,
            "insufficient_context": 0,
            "general_unknown": 0
        }
    
    def _init_optional_services(self):
        """Inicializa serviços opcionais se disponíveis."""
        try:
            from .fallback_service import FallbackService
            self.fallback_service = FallbackService()
            logger.info("FallbackService inicializado")
        except ImportError:
            logger.warning("FallbackService não disponível")
        
        try:
            #from .cache_service import CacheService
            self.cache_service = CacheService()
            logger.info("CacheService inicializado")
        except ImportError:
            logger.warning("CacheService não disponível")
        
    def _initialize_gemini(self) -> None:
        """
        Inicializa o cliente Google Gemini.
        
        Raises:
            LLMError: Se não conseguir inicializar o cliente
        """
        try:
            if not self.settings.google_api_key:
                raise LLMError("Google API Key não configurada")
            
            # Configurar API
            genai.configure(api_key=self.settings.google_api_key)
            
            # Configurações de segurança
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
            
            # Configurações de geração
            generation_config = {
                "temperature": self.settings.gemini_temperature,
                "max_output_tokens": self.settings.gemini_max_tokens,
                "top_p": 0.95,
                "top_k": 40,
            }
            
            # Inicializar modelo
            self._model = genai.GenerativeModel(
                model_name=self.settings.gemini_model,
                generation_config=generation_config,
                safety_settings=safety_settings,
            )
            
            logger.info("Google Gemini inicializado com sucesso", extra={
                "model": self.settings.gemini_model,
                "temperature": self.settings.gemini_temperature,
                "max_tokens": self.settings.gemini_max_tokens
            })
            
        except Exception as e:
            logger.error(f"Erro ao inicializar Google Gemini: {str(e)}")
            raise LLMError(f"Falha na inicialização do Gemini: {str(e)}")
    

    
    def _create_system_prompt(self) -> str:
        """
        Cria prompt de sistema para o Gemini.
        
        Returns:
            str: Prompt de sistema estruturado
        """
        return """Você é um especialista técnico em equipamentos elétricos. Responda como um engenheiro experiente.

REGRAS OBRIGATÓRIAS:
1. NUNCA mencione "sistema", "banco de dados", "registros encontrados" ou "sua consulta"
2. NUNCA use frases como "Com base nos dados" ou "Encontrei X registros"
3. Seja DIRETO - responda como se soubesse a informação naturalmente
4. Use linguagem técnica profissional, mas clara
5. Foque na RESPOSTA, não no processo de busca

REGRAS TEMPORAIS ESPECÍFICAS:
6. Para perguntas sobre EXECUÇÃO passada (ex: "Quando foi executado...?"):
   - Se NÃO há dados de execução: "Não há registro de execução deste teste/manutenção"
   - Se há dados planejados mas não executados: "Este teste estava planejado para [data], mas não há registro de execução"
   - NUNCA diga que algo passado "está planejado"

7. Para perguntas sobre PLANEJAMENTO futuro (ex: "Quando está planejado...?"):
   - Responda com as datas planejadas encontradas
   - Se não há planejamento: "Não há planejamento registrado para este teste/manutenção"

8. Para datas específicas mencionadas na pergunta:
   - Se a data está no passado e não há execução registrada: "Não há registro de execução em [data]"
   - Se a data está no futuro e há planejamento: "Está planejado para [data]"

EXEMPLOS DO QUE NÃO FAZER:
❌ "Com base nos dados do sistema, encontrei 5 registros..."
❌ "Sua consulta sobre equipamentos retornou..."
❌ "Encontrei informações relevantes no banco..."
❌ "O teste operativo está planejado para..." (quando perguntado sobre execução passada)

EXEMPLOS CORRETOS:
✅ "No parque elétrico temos 8 transformadores e 12 disjuntores."
✅ "O transformador T001 teve manutenção preventiva em 15/12/2024."
✅ "Os disjuntores críticos são: DJ-001, DJ-005 e DJ-012."
✅ "Não há registro de execução do teste operativo em 11/04/2025."
✅ "O teste estava planejado para 11/04/2025, mas não foi executado."

RESPONDA SEMPRE como um especialista que conhece os dados, nunca como um sistema fazendo busca."""

    def _create_user_prompt(
        self, 
        user_query: str, 
        retrieved_data: List[Dict[str, Any]], 
        context: Dict[str, Any]
    ) -> str:
        """
        Cria prompt do usuário com dados relevantes.
        
        Args:
            user_query: Pergunta do usuário
            retrieved_data: Dados encontrados no banco (RAG)
            context: Contexto adicional incluindo structured_data (SQL)
            
        Returns:
            str: Prompt formatado para o usuário
        """
        # Organizar dados relevantes
        equipment_info = ""
        maintenance_info = ""
        
        # Processar dados do RAG
        if retrieved_data:
            for record in retrieved_data[:10]:  # Limitar a 10 registros
                # Extrair informações úteis sem expor estrutura técnica
                if isinstance(record, dict):
                    if 'source' in record:
                        if record['source'] == 'equipment':
                            equipment_info += f"- {record.get('content', '')}\n"
                        elif record['source'] == 'maintenance':
                            maintenance_info += f"- {record.get('content', '')}\n"
                    else:
                        # Formato genérico para outros tipos de dados
                        equipment_info += f"- {str(record)}\n"
        
        # Processar dados estruturados do SQL (com contexto temporal)
        structured_data = context.get('structured_data', [])
        query_analysis = context.get('query_analysis', {})
        query_intent = query_analysis.get('intent', '')
        
        # Determinar tipo de consulta temporal
        temporal_context = ""
        if 'foi executado' in user_query.lower() or 'foi realizado' in user_query.lower():
            temporal_context = "\n**TIPO DE CONSULTA:** Busca por execução passada (dados de completion_date)\n"
        elif 'está planejado' in user_query.lower() or 'quando será' in user_query.lower():
            temporal_context = "\n**TIPO DE CONSULTA:** Busca por planejamento futuro (dados de planned_date)\n"
        elif 'quando' in user_query.lower():
            # Consulta ambígua sobre tempo - fornecer contexto sobre o que foi encontrado
            if query_intent == 'last_maintenance':
                temporal_context = "\n**TIPO DE CONSULTA:** Busca por execução passada (somente manutenções completadas)\n"
            elif query_intent == 'upcoming_maintenance':
                temporal_context = "\n**TIPO DE CONSULTA:** Busca por planejamento futuro (manutenções agendadas)\n"
        
        if structured_data:
            # Determinar qual seção usar baseado no intent
            is_equipment_query = query_intent in ['count_equipment', 'equipment_search', 'equipment_status', 'general_query']
            
            # Add header baseado no tipo de consulta
            if is_equipment_query:
                equipment_info += "\n**DADOS DE EQUIPAMENTOS:**\n"
            elif query_intent == 'last_maintenance':
                maintenance_info += "\n**MANUTENÇÕES EXECUTADAS:**\n"
            elif query_intent == 'upcoming_maintenance':
                maintenance_info += "\n**MANUTENÇÕES PLANEJADAS:**\n"
            else:
                maintenance_info += "\n**DADOS DE MANUTENÇÃO:**\n"
            
            for record in structured_data:
                if isinstance(record, dict):
                    # Determinar onde adicionar as informações
                    target_info = equipment_info if is_equipment_query else maintenance_info
                    
                    # Formatar registros de manutenção com contexto temporal claro
                    if 'maintenance_plan_code' in record:
                        item_text = record.get('maintenance_item_text', 'Item não especificado')
                        eq_name = record.get('equipment_name', record.get('equipment_code', 'Equipamento não identificado'))
                        location_abbr = record.get('location_abbreviation', '')
                        
                        # Dados de execução (completion_date)
                        if record.get('completion_date'):
                            completion_date_str = record['completion_date'].strftime('%d/%m/%Y') if isinstance(record['completion_date'], datetime) else str(record['completion_date'])
                            maintenance_info += f"- Plano **{record['maintenance_plan_code']}**: {item_text} no equipamento **{eq_name}** ({location_abbr}). **EXECUTADO em: {completion_date_str}**.\n"
                        
                        # Dados de planejamento (planned_date)
                        elif record.get('planned_date'):
                            planned_date_str = record['planned_date'].strftime('%d/%m/%Y') if isinstance(record['planned_date'], datetime) else str(record['planned_date'])
                            maintenance_info += f"- Plano **{record['maintenance_plan_code']}**: {item_text} no equipamento **{eq_name}** ({location_abbr}). **PLANEJADO para: {planned_date_str}**.\n"
                        
                        else:
                            maintenance_info += f"- Plano **{record['maintenance_plan_code']}**: {item_text} no equipamento **{eq_name}** ({location_abbr}). **Sem data definida**.\n"
                    
                    # Formatar queries de COUNT e agregação
                    elif 'count' in record:
                        count_value = record['count'] if isinstance(record['count'], int) else record.get('count', 0)
                        if is_equipment_query:
                            equipment_info += f"**TOTAL DE EQUIPAMENTOS**: {count_value}\n"
                        else:
                            maintenance_info += f"**TOTAL DE RESULTADOS**: {count_value}\n"
                    
                    # Formatar outros tipos de registros estruturados  
                    else:
                        # Tentar extrair valores numéricos importantes
                        for key, value in record.items():
                            if isinstance(value, (int, float)) and value > 0:
                                if 'count' in key.lower() or 'total' in key.lower():
                                    if is_equipment_query:
                                        equipment_info += f"**{key.upper()}**: {value}\n"
                                    else:
                                        maintenance_info += f"**{key.upper()}**: {value}\n"
                                else:
                                    if is_equipment_query:
                                        equipment_info += f"- {key}: {value}\n"
                                    else:
                                        maintenance_info += f"- {key}: {value}\n"
                            else:
                                if is_equipment_query:
                                    equipment_info += f"- {key}: {value}\n"
                                else:
                                    maintenance_info += f"- {key}: {value}\n"
        
        # Montar contexto limpo
        context_parts = []
        
        if equipment_info.strip():
            context_parts.append(f"EQUIPAMENTOS:\n{equipment_info}")
        
        if maintenance_info.strip():
            context_parts.append(f"MANUTENÇÕES:\n{maintenance_info}")
        
        context_section = "\n".join(context_parts) if context_parts else ""
        
        # Debug: Log dos dados formatados para o LLM
        logger.info(f"LLM Context Debug - Equipment info: {equipment_info[:200]}...")
        logger.info(f"LLM Context Debug - Maintenance info: {maintenance_info[:200]}...")
        logger.info(f"LLM Context Debug - Query intent: {query_intent}")
        
        # Adicionar orientação específica baseada no contexto temporal
        guidance = ""
        if not structured_data and 'foi executado' in user_query.lower():
            guidance = "\n**ORIENTAÇÃO:** Como não há dados de execução, responda que não há registro de execução."
        elif not structured_data and ('está planejado' in user_query.lower() or 'quando será' in user_query.lower()):
            guidance = "\n**ORIENTAÇÃO:** Como não há dados de planejamento, responda que não há planejamento registrado."
        else:
            guidance = ""
        
        # Adicionar orientação específica para queries de contagem
        if structured_data and any('count' in str(record).lower() for record in structured_data):
            count_guidance = "\n**IMPORTANTE:** Use APENAS os números mostrados em **TOTAL DE EQUIPAMENTOS** ou valores similares em negrito. Ignore qualquer outro número."
        else:
            count_guidance = ""
        
        return f"""PERGUNTA: {user_query}

{temporal_context}{context_section}{guidance}{count_guidance}

Responda diretamente baseado nas informações disponíveis."""

    async def _call_gemini_with_retry(
        self, 
        prompt: str, 
        max_retries: int = 3
    ) -> str:
        """
        Chama Gemini com sistema de retry.
        
        Args:
            prompt: Prompt completo para enviar
            max_retries: Número máximo de tentativas
            
        Returns:
            str: Resposta do Gemini
            
        Raises:
            LLMError: Se todas as tentativas falharem
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"Tentativa {attempt + 1} de chamada ao Gemini")
                
                # Usar timeout
                response = await asyncio.wait_for(
                    asyncio.to_thread(self._model.generate_content, prompt),
                    timeout=self.settings.gemini_timeout
                )
                
                if response.text:
                    logger.debug("Resposta recebida do Gemini com sucesso")
                    return response.text.strip()
                else:
                    raise LLMError("Resposta vazia do Gemini")
                    
            except asyncio.TimeoutError:
                last_error = LLMError(f"Timeout na tentativa {attempt + 1}")
                logger.warning(f"Timeout no Gemini - tentativa {attempt + 1}")
                
            except google_exceptions.ResourceExhausted:
                last_error = LLMError("Quota de API do Gemini excedida")
                logger.error("Quota de API excedida")
                break  # Não adianta tentar novamente
                
            except google_exceptions.InvalidArgument as e:
                last_error = LLMError(f"Argumento inválido para Gemini: {str(e)}")
                logger.error(f"Argumento inválido: {str(e)}")
                break  # Não adianta tentar novamente
                
            except Exception as e:
                last_error = LLMError(f"Erro no Gemini: {str(e)}")
                logger.warning(f"Erro na tentativa {attempt + 1}: {str(e)}")
            
            # Aguardar antes da próxima tentativa
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Backoff exponencial
        
        # Se chegou aqui, todas as tentativas falharam
        self.error_count += 1
        raise last_error or LLMError("Falha em todas as tentativas de chamada ao Gemini")
    
    def _validate_and_clean_response(self, response: str) -> str:
        """
        Valida e limpa resposta do Gemini.
        
        Args:
            response: Resposta bruta do Gemini
            
        Returns:
            str: Resposta validada e limpa
            
        Raises:
            ValidationError: Se resposta inválida
        """
        if not response or not response.strip():
            raise ValidationError("Resposta vazia do LLM")
        
        # Limpar resposta
        cleaned = response.strip()
        
        # Validar tamanho
        if len(cleaned) > 5000:  # Limite razoável
            logger.warning("Resposta muito longa, truncando")
            cleaned = cleaned[:5000] + "... [resposta truncada]"
        
        # Verificar e registrar respostas "não sei" - Sistema de Logging Específico
        cleaned_lower = cleaned.lower()
        unknown_patterns = [
            "não sei",
            "não consigo", 
            "não tenho informação",
            "não posso fornecer",
            "informação não disponível",
            "dados insuficientes",
            "não há dados",
            "consulta não suportada",
            "fora do meu conhecimento",
            "preciso de mais informações"
        ]
        
        # Log específico para queries "não sei" com detalhamento
        for pattern in unknown_patterns:
            if pattern in cleaned_lower:
                category = self._categorize_unknown_response(pattern)
                
                # Incrementar métricas
                self.unknown_query_count += 1
                self.unknown_query_categories[category] += 1
                
                logger.warning("Query resultou em resposta 'não sei' - Requer melhoria da base de conhecimento", extra={
                    "event_type": "unknown_query_response",
                    "pattern_matched": pattern,
                    "response_snippet": cleaned[:150],
                    "response_length": len(cleaned),
                    "timestamp": datetime.now().isoformat(),
                    "requires_knowledge_improvement": True,
                    "knowledge_gap_category": category,
                    "improvement_priority": "high" if pattern in ["não sei", "não tenho informação"] else "medium",
                    "total_unknown_queries": self.unknown_query_count
                })
                break
        
        # Validar se não está apenas repetindo a pergunta
        if len(cleaned) < 10:
            raise ValidationError("Resposta muito curta do LLM")
        
        return cleaned
    
    def _categorize_unknown_response(self, pattern: str) -> str:
        """
        Categoriza o tipo de resposta 'não sei' para análise posterior.
        
        Args:
            pattern: Padrão que foi identificado na resposta
            
        Returns:
            str: Categoria da lacuna de conhecimento
        """
        if pattern in ["não sei", "fora do meu conhecimento"]:
            return "knowledge_gap"
        elif pattern in ["não tenho informação", "dados insuficientes", "não há dados"]:
            return "data_gap"
        elif pattern in ["não consigo", "não posso fornecer"]:
            return "capability_limitation"
        elif pattern in ["consulta não suportada"]:
            return "unsupported_query_type"
        elif pattern in ["preciso de mais informações"]:
            return "insufficient_context"
        else:
            return "general_unknown"
    
    def _calculate_confidence_score(
        self, 
        user_query: str, 
        retrieved_data: List[Dict[str, Any]], 
        response: str
    ) -> float:
        """
        Calcula score de confiança da resposta.
        
        Args:
            user_query: Query original
            retrieved_data: Dados encontrados
            response: Resposta gerada
            
        Returns:
            float: Score entre 0.0 e 1.0
        """
        score = 0.0
        
        # Base score se há dados
        if retrieved_data:
            score += 0.4
        
        # Score baseado na quantidade de dados
        data_count = len(retrieved_data)
        if data_count > 0:
            score += min(0.3, data_count * 0.05)
        
        # Score baseado no tamanho da resposta (indica detalhamento)
        response_length = len(response)
        if response_length > 100:
            score += 0.2
        elif response_length > 50:
            score += 0.1
        
        # Penalizar se resposta indica incerteza
        uncertainty_phrases = [
            "não sei", "não tenho", "não posso", "incerto", 
            "talvez", "possivelmente", "não disponível"
        ]
        if any(phrase in response.lower() for phrase in uncertainty_phrases):
            score -= 0.2
        
        # Garantir que está entre 0 e 1
        return max(0.0, min(1.0, score))
    
    async def generate_response(        
        self,
        user_query: str,
        sql_query: Optional[str] = None,
        query_results: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        cache_strategy: Union[str, CacheStrategy] = "normalized_match" # Permite str ou Enum
    ) -> Dict[str, Any]:
        """
        Gera resposta usando Google Gemini com cache inteligente e fallback automático.
        
        Args:
            user_query: Pergunta do usuário em linguagem natural
            sql_query: Query SQL gerada (opcional)
            query_results: Resultados da query SQL
            context: Contexto adicional da conversa
            session_id: ID da sessão para tracking
            cache_strategy: Estratégia de cache a usar
            
        Returns:
            Dict com resposta estruturada incluindo:
            - response: Resposta em linguagem natural
            - confidence_score: Nível de confiança (0.0-1.0)
            - sources: Fontes de dados utilizadas
            - suggestions: Sugestões de próximas perguntas
            - processing_time: Tempo de processamento em ms
            - cache_used: Se foi usado cache
            - cache_status: Status do cache se usado
            - fallback_used: Se foi usado sistema de fallback
            - fallback_reason: Motivo do fallback (se aplicável)
            
        Raises:
            LLMError: Se falhar na geração da resposta e fallback
            ValidationError: Se dados de entrada inválidos
        """
        start_time = time.time()
        self.request_count += 1
        llm_response = None
        llm_error = None
        
        try:
            # Validar entrada
            if not user_query or not user_query.strip():
                raise ValidationError("Query do usuário não pode estar vazia")
            
            # Preparar contexto padrão
            if context is None:
                context = {}
            
            if query_results is None:
                query_results = []
            
            # Converter cache_strategy para o tipo Enum se for string
            if isinstance(cache_strategy, str):
                try:
                    cache_strategy_enum = CacheStrategy(cache_strategy)
                except ValueError:
                    logger.warning(f"Estratégia de cache '{cache_strategy}' inválida. Usando NORMALIZED_MATCH.")
                    cache_strategy_enum = CacheStrategy.NORMALIZED_MATCH
            else:
                cache_strategy_enum = cache_strategy # Já é um Enum
                
            # Tentar buscar no cache primeiro (se disponível)
            cached_response = None
            if self.cache_service:
                try:
                    cached_response = await self.cache_service.get(
                        query=user_query,
                        context=context,
                        strategy=cache_strategy_enum # Use o Enum aqui
                    )
                except Exception as e:
                    logger.warning(f"Erro no cache: {e}")
            
            if cached_response:
                self.cache_hits += 1
                processing_time = int((time.time() - start_time) * 1000)
                
                logger.info("Resposta servida do cache inteligente", extra={
                    "session_id": session_id,
                    "cache_strategy": cache_strategy_enum.value, # Use .value aqui
                    "cache_status": cached_response.get("cache_status"),
                    "processing_time": processing_time
                })
                
                # Atualizar tempo de processamento no cache hit
                cached_response["processing_time"] = processing_time
                return cached_response
            
            logger.info("Gerando resposta com Gemini", extra={
                "session_id": session_id,
                "query_length": len(user_query),
                "rag_chunks": len(query_results),  # Renomeado para clareza
                "sql_records": len(context.get('structured_data', [])) if context else 0,
                "cache_strategy": cache_strategy_enum.value # Use .value aqui
            })
            
            try:
                # Tentar gerar resposta com Gemini
                system_prompt = self._create_system_prompt()
                user_prompt = self._create_user_prompt(user_query, query_results, context)
                full_prompt = f"{system_prompt}\n\n{user_prompt}"
                
                # Chamar Gemini
                response_text = await self._call_gemini_with_retry(
                    full_prompt, 
                    max_retries=self.settings.gemini_max_retries
                )
                
                # Validar e limpar resposta
                llm_response = self._validate_and_clean_response(response_text)
                
                # Calcular confiança da resposta do LLM
                confidence_score = self._calculate_confidence_score(
                    user_query, query_results, llm_response
                )
                
                # Verificar se deve usar fallback (se disponível)
                should_fallback = False
                if self.fallback_service:
                    try:
                        should_fallback, fallback_trigger = self.fallback_service.should_use_fallback(
                            llm_response=llm_response,
                            original_query=user_query,
                            llm_confidence=confidence_score,
                            error=None
                        )
                        
                        if should_fallback:
                            logger.info("Fallback ativado por resposta inadequada do LLM", extra={
                                "trigger": fallback_trigger.value,
                                "confidence": confidence_score,
                                "session_id": session_id
                            })
                            return await self._generate_fallback_response(
                                user_query, fallback_trigger, start_time, session_id, context
                            )
                    except Exception as e:
                        logger.warning(f"Erro no fallback service: {e}")
                
                # Resposta do LLM é adequada, processar e cachear
                processing_time = int((time.time() - start_time) * 1000)
                suggestions = self._generate_suggestions(user_query, query_results)
                
                sources = ["gemini_llm"]
                if query_results:
                    sources.extend(["equipment_data", "maintenance_data"])
                if sql_query:
                    sources.append("sql_database")
                
                final_response = {
                    "response": llm_response,
                    "confidence_score": confidence_score,
                    "sources": list(set(sources)),
                    "suggestions": suggestions,
                    "processing_time": processing_time,
                    "data_records_used": len(query_results),
                    "cache_used": False,
                    "fallback_used": False,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Armazenar no cache inteligente (se disponível)
                if self.cache_service:
                    try:
                        cache_tags = self._generate_cache_tags(user_query, context, query_results)
                        await self.cache_service.set(
                            query=user_query,
                            response=final_response,
                            context=context,
                            ttl=self._calculate_cache_ttl(confidence_score, len(query_results)),
                            tags=cache_tags
                        )
                    except Exception as e:
                        logger.warning(f"Erro ao armazenar no cache: {e}")
                
                logger.info("Resposta gerada e cacheada com sucesso", extra={
                    "session_id": session_id,
                    "confidence": confidence_score,
                    "processing_time": processing_time,
                    "rag_chunks": len(query_results),
                    "sql_records": len(context.get('structured_data', [])) if context else 0,
                    "cache_ttl": self._calculate_cache_ttl(confidence_score, len(query_results))
                })
                
                return final_response
                
            except Exception as e:
                # Erro na geração com LLM - ativar fallback
                llm_error = e
                logger.warning(f"Erro no LLM, ativando fallback: {str(e)}", extra={
                    "session_id": session_id,
                    "error_type": type(e).__name__
                })
                
                # Usar fallback se disponível, senão retornar erro simples
                if self.fallback_service:
                    try:
                        # Determinar trigger de fallback baseado no erro
                        should_fallback, fallback_trigger = self.fallback_service.should_use_fallback(
                            llm_response=None,
                            original_query=user_query,
                            llm_confidence=None,
                            error=e
                        )
                        
                        if should_fallback:
                            return await self._generate_fallback_response(
                                user_query, fallback_trigger, start_time, session_id, context, str(e)
                            )
                    except Exception as fb_error:
                        logger.error(f"Erro no fallback service: {fb_error}")
                
                # Se fallback não disponível ou falhou, retornar resposta de erro simples
                processing_time = int((time.time() - start_time) * 1000)
                return {
                    "response": "Desculpe, não consegui processar sua solicitação no momento. Tente novamente mais tarde.",
                    "confidence_score": 0.1,
                    "sources": ["error_fallback"],
                    "suggestions": ["Tente uma pergunta mais simples", "Verifique sua conexão"],
                    "processing_time": processing_time,
                    "cache_used": False,
                    "fallback_used": True,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
        
        except ValidationError:
            # Erros de validação não devem usar fallback
            raise
        except Exception as e:
            # Último recurso - erro geral
            logger.error(f"Erro geral no LLMService: {str(e)}", extra={
                "session_id": session_id
            })
            
            # Fallback de emergência
            processing_time = int((time.time() - start_time) * 1000)
            return {
                "response": "Desculpe, estou com dificuldades técnicas no momento. Tente novamente mais tarde.",
                "confidence_score": 0.1,
                "sources": ["emergency_fallback"],
                "suggestions": ["Tente uma pergunta mais simples", "Recarregue a página"],
                "processing_time": processing_time,
                "data_records_used": 0,
                "cache_used": False,
                "fallback_used": True,
                "fallback_reason": "emergency_fallback",
                "actionable": False,
                "timestamp": datetime.now().isoformat(),
                "error": "Sistema de fallback falhou"
            }
    
    def _generate_cache_tags(
        self, 
        user_query: str, 
        context: Dict[str, Any], 
        query_results: List[Dict[str, Any]]
    ) -> set:
        """
        Gera tags para categorização no cache.
        
        Args:
            user_query: Query do usuário
            context: Contexto da consulta
            query_results: Resultados da consulta
            
        Returns:
            set: Tags para o cache
        """
        tags = set()
        
        # Tags baseadas no tipo de consulta
        query_lower = user_query.lower()
        
        if any(word in query_lower for word in ["transformador", "trafo"]):
            tags.add("transformador")
        if any(word in query_lower for word in ["gerador", "generator"]):
            tags.add("gerador")
        if any(word in query_lower for word in ["manutenção", "maintenance"]):
            tags.add("manutencao")
        if any(word in query_lower for word in ["falha", "problema", "failure"]):
            tags.add("falha")
        if any(word in query_lower for word in ["custo", "valor", "cost"]):
            tags.add("custo")
        if any(word in query_lower for word in ["status", "situação"]):
            tags.add("status")
        
        # Tags baseadas no contexto
        if context.get("query_type"):
            tags.add(f"type_{context['query_type']}")
        
        # Tags baseadas nos dados
        if query_results:
            tags.add("with_data")
            if len(query_results) > 10:
                tags.add("large_dataset")
        else:
            tags.add("no_data")
        
        return tags
    
    def _calculate_cache_ttl(self, confidence_score: float, data_records: int) -> int:
        """
        Calcula TTL do cache baseado na confiança e quantidade de dados.
        
        Args:
            confidence_score: Score de confiança da resposta
            data_records: Número de registros de dados
            
        Returns:
            int: TTL em segundos
        """
        base_ttl = 3600  # 1 hora
        
        # Respostas mais confiáveis ficam mais tempo no cache
        confidence_multiplier = 0.5 + (confidence_score * 1.5)
        
        # Respostas com mais dados ficam mais tempo no cache
        data_multiplier = 1.0 + min(0.5, data_records / 20)
        
        ttl = int(base_ttl * confidence_multiplier * data_multiplier)
        
        # Limitar entre 30 minutos e 4 horas
        return max(1800, min(14400, ttl))
    
    async def _generate_fallback_response(
        self,
        user_query: str,
        trigger: str,
        start_time: float,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        error_details: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Gera resposta usando sistema de fallback.
        
        Args:
            user_query: Query original do usuário
            trigger: Motivo do fallback
            start_time: Timestamp do início do processamento
            session_id: ID da sessão
            context: Contexto adicional
            error_details: Detalhes do erro (opcional)
            
        Returns:
            Dict: Resposta de fallback estruturada
        """
        try:
            self.fallback_used_count += 1
            
            # Gerar resposta de fallback
            fallback_response = self.fallback_service.generate_fallback_response(
                trigger=trigger,
                original_query=user_query,
                context=context or {}
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # Estruturar resposta no formato esperado
            final_response = {
                "response": fallback_response.message,
                "confidence_score": fallback_response.confidence,
                "sources": ["fallback_system"],
                "suggestions": fallback_response.suggestions,
                "processing_time": processing_time,
                "data_records_used": 0,
                "cache_used": False,
                "fallback_used": True,
                "fallback_reason": trigger,
                "fallback_strategy": fallback_response.strategy_used.value if hasattr(fallback_response, 'strategy_used') else "unknown",
                "actionable": fallback_response.actionable,
                "timestamp": datetime.now().isoformat()
            }
            
            if error_details:
                final_response["error_details"] = error_details
            
            logger.info("Resposta de fallback gerada", extra={
                "session_id": session_id,
                "trigger": trigger,
                "strategy": fallback_response.strategy_used.value if hasattr(fallback_response, 'strategy_used') else "unknown",
                "confidence": fallback_response.confidence
            })
            
            return final_response
            
        except Exception as e:
            # Fallback do fallback - resposta de emergência
            logger.error(f"Erro no sistema de fallback: {str(e)}", extra={
                "session_id": session_id
            })
            
            processing_time = int((time.time() - start_time) * 1000)
            
            return {
                "response": "Desculpe, estou com dificuldades técnicas no momento. Tente novamente em alguns instantes ou reformule sua pergunta.",
                "confidence_score": 0.1,
                "sources": [
                    "Recarregue a página",
                    "Tente uma pergunta mais simples",
                    "Verifique sua conexão"
                ],
                "processing_time": processing_time,
                "data_records_used": 0,
                "cache_used": False,
                "fallback_used": True,
                "fallback_reason": "emergency_fallback",
                "actionable": False,
                "timestamp": datetime.now().isoformat(),
                "error": "Sistema de fallback falhou"
            }
    
    def _generate_suggestions(
        self, 
        user_query: str, 
        query_results: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Gera sugestões de próximas perguntas baseadas no contexto.
        
        Args:
            user_query: Query original do usuário
            query_results: Resultados encontrados
            
        Returns:
            List[str]: Lista de sugestões
        """
        suggestions = []
        
        query_lower = user_query.lower()
        
        # Sugestões baseadas no tipo de consulta
        if "equipamento" in query_lower or "transformador" in query_lower:
            suggestions.extend([
                "Qual o histórico de manutenções deste equipamento?",
                "Quando será a próxima manutenção prevista?",
                "Quais são os custos de manutenção deste equipamento?"
            ])
        
        if "manutenção" in query_lower:
            suggestions.extend([
                "Quais equipamentos precisam de manutenção urgente?",
                "Qual o custo total de manutenções este mês?",
                "Mostre equipamentos com manutenção atrasada"
            ])
        
        if "custo" in query_lower or "valor" in query_lower:
            suggestions.extend([
                "Compare custos por tipo de equipamento",
                "Qual o equipamento mais caro para manter?",
                "Mostre tendência de custos nos últimos meses"
            ])
        
        if "falha" in query_lower or "problema" in query_lower:
            suggestions.extend([
                "Quais são as falhas mais comuns?",
                "Equipamentos com histórico de problemas",
                "Análise de padrões de falhas por período"
            ])
        
        # Sugestões baseadas nos resultados
        if query_results:
            suggestions.append("Gere relatório detalhado sobre estes resultados")
            suggestions.append("Quais são as recomendações para estes equipamentos?")
        
        # Sugestões gerais sempre disponíveis
        general_suggestions = [
            "Status geral dos equipamentos",
            "Resumo de manutenções pendentes",
            "Indicadores de performance do mês"
        ]
        
        suggestions.extend(general_suggestions)
        
        # Remover duplicatas e limitar
        unique_suggestions = list(dict.fromkeys(suggestions))
        return unique_suggestions[:5]  # Máximo 5 sugestões
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Retorna métricas detalhadas do serviço LLM.
        
        Returns:
            Dict com métricas incluindo:
            - Estatísticas de uso do LLM
            - Performance de cache inteligente
            - Métricas de fallback
            - Taxa de sucesso geral
        """
        cache_hit_rate = (self.cache_hits / self.request_count) if self.request_count > 0 else 0
        error_rate = (self.error_count / self.request_count) if self.request_count > 0 else 0
        fallback_rate = (self.fallback_used_count / self.request_count) if self.request_count > 0 else 0
        
        # Obter métricas do cache inteligente (se disponível)
        cache_metrics = None
        if self.cache_service:
            try:
                cache_metrics = await self.cache_service.get_metrics()
            except Exception as e:
                logger.warning(f"Erro ao obter métricas de cache: {e}")
        
        # Calcular taxas de queries "não sei"
        unknown_query_rate = (self.unknown_query_count / self.request_count) if self.request_count > 0 else 0
        
        # Métricas básicas do LLM
        llm_metrics = {
            "total_requests": self.request_count,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": round(cache_hit_rate, 3),
            "error_count": self.error_count,
            "error_rate": round(error_rate, 3),
            "fallback_used_count": self.fallback_used_count,
            "fallback_rate": round(fallback_rate, 3),
            "unknown_queries": {
                "total_unknown_queries": self.unknown_query_count,
                "unknown_query_rate": round(unknown_query_rate, 3),
                "categories": self.unknown_query_categories.copy(),
                "most_common_category": max(self.unknown_query_categories.items(), key=lambda x: x[1])[0] if any(self.unknown_query_categories.values()) else "none",
                "knowledge_improvement_needed": self.unknown_query_count > 0
            },
            "model_config": {
                "model": self.settings.gemini_model,
                "temperature": self.settings.gemini_temperature,
                "max_tokens": self.settings.gemini_max_tokens,
                "timeout": self.settings.gemini_timeout
            },
            "intelligent_cache": {
                "cache_size": cache_metrics.cache_size if cache_metrics else 0,
                "max_cache_size": cache_metrics.max_cache_size if cache_metrics else 0,
                "hit_rate": cache_metrics.hit_rate if cache_metrics else 0,
                "miss_rate": cache_metrics.miss_rate if cache_metrics else 0,
                "expired_entries": cache_metrics.expired_entries if cache_metrics else 0,
                "stale_entries": cache_metrics.stale_entries if cache_metrics else 0,
                "memory_usage_mb": cache_metrics.memory_usage_mb if cache_metrics else 0,
                "average_response_size": cache_metrics.average_response_size if cache_metrics else 0,
                "available": cache_metrics is not None
            }
        }
        
        # Integrar métricas do sistema de fallback (se disponível)
        if self.fallback_service:
            try:
                fallback_metrics = self.fallback_service.get_metrics()
                llm_metrics["fallback_system"] = {
                    "total_fallbacks": fallback_metrics.total_fallbacks,
                    "success_rate": fallback_metrics.success_rate,
                    "user_satisfaction": fallback_metrics.user_satisfaction,
                    "triggers": fallback_metrics.fallbacks_by_trigger,
                    "strategies": fallback_metrics.fallbacks_by_strategy,
                    "available": True
                }
            except Exception as e:
                logger.warning(f"Erro ao obter métricas de fallback: {str(e)}")
                llm_metrics["fallback_system"] = {"error": "Métricas não disponíveis", "available": False}
        else:
            llm_metrics["fallback_system"] = {"available": False, "message": "Serviço não inicializado"}
        
        return llm_metrics
    
    async def clear_cache(self) -> None:
        """Limpa o cache inteligente de respostas (se disponível)."""
        if self.cache_service:
            await self.cache_service.clear()
            logger.info("Cache inteligente de respostas LLM limpo")
        else:
            logger.warning("Cache service não disponível")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Verifica saúde do serviço LLM e sistema de fallback.
        
        Returns:
            Dict com status de saúde completo
        """
        try:
            # Testar conexão básica com Gemini
            test_prompt = "Test"
            start_time = time.time()
            
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(self._model.generate_content, test_prompt),
                    timeout=5.0  # Timeout mais baixo para health check
                )
                gemini_status = "healthy"
                response_time = int((time.time() - start_time) * 1000)
            except asyncio.TimeoutError:
                gemini_status = "timeout"
                response_time = 5000
            except Exception as e:
                gemini_status = "error"
                response_time = int((time.time() - start_time) * 1000)
                logger.warning(f"Health check Gemini falhou: {str(e)}")
            
            # Verificar métricas gerais
            metrics = await self.get_metrics()
            error_rate = metrics.get("error_rate", 0)
            fallback_rate = metrics.get("fallback_rate", 0)
            
            # Determinar status geral do LLM
            if gemini_status == "healthy" and error_rate < 0.1:
                llm_overall_status = "healthy"
            elif gemini_status == "healthy" and error_rate < 0.3:
                llm_overall_status = "warning"
            else:
                llm_overall_status = "critical"
            
            # Verificar saúde do sistema de fallback (se disponível)
            if self.fallback_service:
                try:
                    fallback_health = self.fallback_service.get_health_status()
                    fallback_status = fallback_health.get("status", "unknown")
                except Exception as e:
                    logger.warning(f"Erro ao verificar saúde do fallback: {str(e)}")
                    fallback_status = "error"
                    fallback_health = {"status": "error", "error": str(e)}
            else:
                fallback_status = "unavailable"
                fallback_health = {"status": "unavailable", "message": "Serviço não inicializado"}
            
            # Status geral do sistema
            if llm_overall_status == "healthy" and fallback_status in ["healthy", "warning"]:
                overall_status = "healthy"
            elif llm_overall_status in ["healthy", "warning"] and fallback_status != "critical":
                overall_status = "warning"
            else:
                overall_status = "critical"
            
            return {
                "overall_status": overall_status,
                "llm_service": {
                    "status": llm_overall_status,
                    "gemini_connection": gemini_status,
                    "response_time_ms": response_time,
                    "error_rate": error_rate,
                    "total_requests": metrics.get("total_requests", 0),
                    "cache_hit_rate": metrics.get("cache_hit_rate", 0)
                },
                "fallback_system": fallback_health,
                "cache": {
                    "size": metrics.get("intelligent_cache", {}).get("cache_size", 0),
                    "max_size": metrics.get("intelligent_cache", {}).get("max_cache_size", 0),
                    "hit_rate": metrics.get("intelligent_cache", {}).get("hit_rate", 0),
                    "memory_usage_mb": metrics.get("intelligent_cache", {}).get("memory_usage_mb", 0)
                },
                "configuration": {
                    "model": self.settings.gemini_model,
                    "timeout": self.settings.gemini_timeout,
                    "max_retries": self.settings.gemini_max_retries
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro no health check: {str(e)}")
            return {
                "overall_status": "critical",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            } 
