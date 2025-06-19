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
    
    def _init_optional_services(self):
        """Inicializa serviços opcionais se disponíveis."""
        try:
            from .fallback_service import FallbackService
            self.fallback_service = FallbackService()
            logger.info("FallbackService inicializado")
        except ImportError:
            logger.warning("FallbackService não disponível")
        
        try:
            from .cache_service import CacheService
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
            if not self.settings.gemini_api_key:
                raise LLMError("Google API Key não configurada")
            
            # Configurar API
            genai.configure(api_key=self.settings.gemini_api_key)
            
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
        return """Você é um assistente especializado em manutenção de equipamentos elétricos para o sistema PROAtivo.

CONTEXTO DO SISTEMA:
- Empresa: Setor elétrico/energético  
- Dados: Equipamentos, manutenções, falhas, custos
- Objetivo: Apoio à decisão técnica baseada em dados

INSTRUÇÕES FUNDAMENTAIS:
1. Responda SEMPRE em português brasileiro
2. Use linguagem técnica mas acessível
3. Seja preciso com números, datas e dados técnicos
4. Sugira ações quando apropriado
5. Se não souber ou dados insuficientes, diga claramente
6. Mantenha respostas objetivas e focadas

FORMATO DE RESPOSTA:
- Resposta direta à pergunta
- Dados específicos encontrados
- Análise técnica quando relevante
- Recomendações práticas (se aplicável)

LIMITAÇÕES:
- Responda apenas sobre manutenção e equipamentos
- Não invente dados que não foram fornecidos
- Não dê conselhos fora do escopo técnico"""

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
            retrieved_data: Dados encontrados no banco
            context: Contexto adicional
            
        Returns:
            str: Prompt formatado para o usuário
        """
        # Organizar dados encontrados
        data_summary = ""
        if retrieved_data:
            data_summary = f"DADOS ENCONTRADOS ({len(retrieved_data)} registros):\n"
            for i, record in enumerate(retrieved_data[:10], 1):  # Limitar a 10 registros
                data_summary += f"{i}. {record}\n"
            
            if len(retrieved_data) > 10:
                data_summary += f"... e mais {len(retrieved_data) - 10} registros\n"
        else:
            data_summary = "DADOS ENCONTRADOS: Nenhum registro específico encontrado\n"
        
        # Contexto adicional
        context_info = f"""
CONTEXTO ADICIONAL:
- Total de equipamentos na base: {context.get('total_equipment', 'N/A')}
- Última atualização: {context.get('last_update', 'N/A')}
- Filtros aplicados: {context.get('filters', 'Nenhum')}
- Tipo de consulta: {context.get('query_type', 'Geral')}
"""
        
        return f"""PERGUNTA DO USUÁRIO:
{user_query}

{data_summary}
{context_info}

Responda à pergunta baseando-se nos dados fornecidos. Se os dados forem insuficientes, explique o que seria necessário para uma resposta completa."""

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
        
        # Validar se não está apenas repetindo a pergunta
        if len(cleaned) < 10:
            raise ValidationError("Resposta muito curta do LLM")
        
        return cleaned
    
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
        cache_strategy: str = "normalized_match"
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
            
            # Tentar buscar no cache primeiro (se disponível)
            cached_response = None
            if self.cache_service:
                try:
                    cached_response = await self.cache_service.get(
                        query=user_query,
                        context=context,
                        strategy=cache_strategy
                    )
                except Exception as e:
                    logger.warning(f"Erro no cache: {e}")
            
            if cached_response:
                self.cache_hits += 1
                processing_time = int((time.time() - start_time) * 1000)
                
                logger.info("Resposta servida do cache inteligente", extra={
                    "session_id": session_id,
                    "cache_strategy": cache_strategy,
                    "cache_status": cached_response.get("cache_status"),
                    "processing_time": processing_time
                })
                
                # Atualizar tempo de processamento no cache hit
                cached_response["processing_time"] = processing_time
                return cached_response
            
            logger.info("Gerando resposta com Gemini", extra={
                "session_id": session_id,
                "query_length": len(user_query),
                "data_records": len(query_results),
                "cache_strategy": cache_strategy
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
                    "data_records": len(query_results),
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
                "cache_used": False,
                "fallback_used": True,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
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
                "sources": ["emergency_fallback"],
                "suggestions": [
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
        
        # Métricas básicas do LLM
        llm_metrics = {
            "total_requests": self.request_count,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": round(cache_hit_rate, 3),
            "error_count": self.error_count,
            "error_rate": round(error_rate, 3),
            "fallback_used_count": self.fallback_used_count,
            "fallback_rate": round(fallback_rate, 3),
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