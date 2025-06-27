"""
Serviço dedicado para geração de SQL usando Google Gemini.

Este módulo implementa a geração de queries SQL a partir de perguntas
em linguagem natural, com foco em simplicidade e segurança.
"""

import re
import time
from typing import Dict, Any, Optional, List
import logging

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from ..config import get_settings
from src.utils.logger import get_logger
from .llm_schema_prompts import LLMSchemaPrompts, QueryCategory

# Configurar logger
logger = get_logger(__name__)


class LLMSQLGenerator:
    """
    Gerador de SQL usando Google Gemini.
    
    Responsabilidades:
    - Receber perguntas em linguagem natural
    - Gerar SQL usando Gemini com prompts especializados
    - Extrair e limpar SQL da resposta
    - Retornar query pronta para validação
    """
    
    def __init__(self):
        """Inicializa o gerador SQL."""
        self.settings = get_settings()
        self._model = None
        self._initialize_gemini()
        
        # Sistema de prompts elaborado
        self.schema_prompts = LLMSchemaPrompts()
        
        logger.info("LLMSQLGenerator inicializado com sistema de prompts elaborado")
    
    def _initialize_gemini(self) -> None:
        """Inicializa o cliente Gemini com configurações específicas para SQL."""
        try:
            if not self.settings.google_api_key:
                raise ValueError("Google API Key não configurada")
            
            genai.configure(api_key=self.settings.google_api_key)
            
            # Configurações otimizadas para geração de SQL
            generation_config = {
                "temperature": self.settings.llm_sql_temperature,  # 0.1 - mais determinístico
                "max_output_tokens": self.settings.llm_sql_max_tokens,  # 1000 - queries são curtas
                "top_p": 0.95,
                "top_k": 40,
            }
            
            self._model = genai.GenerativeModel(
                model_name=self.settings.gemini_model,
                generation_config=generation_config,
            )
            
            logger.info(f"Gemini configurado para SQL: temperature={self.settings.llm_sql_temperature}")
            
        except Exception as e:
            logger.error(f"Erro ao inicializar Gemini: {str(e)}")
            raise
    
    def _extract_sql_from_response(self, response: str) -> Optional[str]:
        """Extrai e limpa o SQL da resposta do Gemini."""
        if not response:
            return None
        
        # Remover blocos de código markdown se existirem
        sql_match = re.search(r'```(?:sql)?\s*(.*?)\s*```', response, re.DOTALL | re.IGNORECASE)
        if sql_match:
            sql = sql_match.group(1).strip()
        else:
            # Se não houver blocos de código, usar a resposta inteira
            sql = response.strip()
        
        # Limpar linhas vazias e espaços extras
        lines = [line.strip() for line in sql.split('\n') if line.strip()]
        sql = ' '.join(lines)
        
        # Garantir que termina com ponto e vírgula
        if sql and not sql.rstrip().endswith(';'):
            sql = sql.rstrip() + ';'
        
        # Validação básica - deve começar com SELECT
        if not sql.upper().startswith('SELECT'):
            logger.warning(f"SQL gerado não começa com SELECT: {sql[:50]}")
            return None
        
        return sql
    
    async def generate_sql(self, user_question: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Gera SQL a partir de uma pergunta em linguagem natural.
        
        Args:
            user_question: Pergunta do usuário
            timeout: Timeout customizado (usa llm_sql_timeout se não especificado)
            
        Returns:
            Dict com:
            - success: Se a geração foi bem-sucedida
            - sql: Query SQL gerada
            - error: Mensagem de erro se houver
            - generation_time_ms: Tempo de geração em ms
            - query_category: Categoria detectada da query
        """
        start_time = time.time()
        
        if not self.settings.llm_sql_feature_enabled:
            return {
                "success": False,
                "sql": None,
                "error": "LLM SQL feature is disabled",
                "generation_time_ms": 0,
                "query_category": None
            }
        
        try:
            # Validar entrada
            if not user_question or not user_question.strip():
                return {
                    "success": False,
                    "sql": None,
                    "error": "Question cannot be empty",
                    "generation_time_ms": 0,
                    "query_category": None
                }
            
            # Usar o sistema de prompts elaborado
            prompt = self.schema_prompts.get_enhanced_prompt(user_question.strip())
            
            # Detectar categoria para logging
            category = self.schema_prompts._detect_category(user_question)
            
            # Usar timeout específico para SQL se não fornecido
            if timeout is None:
                timeout = self.settings.llm_sql_timeout
            
            # Gerar SQL com Gemini
            logger.debug(f"Gerando SQL para: {user_question} | Categoria: {category}")
            
            response = self._model.generate_content(prompt)
            
            if not response:
                raise ValueError("Empty response from Gemini")
            
            # Extrair texto da resposta (pode ser complexa)
            response_text = None
            try:
                response_text = response.text
            except (ValueError, AttributeError) as e:
                # Resposta complexa - tentar múltiplas formas de extração
                logger.debug(f"Resposta complexa detectada: {str(e)}")
                
                # Método 1: Tentar acessar candidatos diretamente
                if hasattr(response, 'candidates') and response.candidates:
                    for candidate in response.candidates:
                        if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                            for part in candidate.content.parts:
                                if hasattr(part, 'text') and part.text:
                                    response_text = part.text
                                    break
                        if response_text:
                            break
                
                # Método 2: Tentar através do iterator de partes
                if not response_text and hasattr(response, '_result'):
                    try:
                        result = response._result
                        if hasattr(result, 'candidates') and result.candidates:
                            candidate = result.candidates[0]
                            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                                parts_text = []
                                for part in candidate.content.parts:
                                    if hasattr(part, 'text'):
                                        parts_text.append(part.text)
                                if parts_text:
                                    response_text = ' '.join(parts_text)
                    except:
                        pass
                
                # Método 3: Última tentativa - forçar conversão
                if not response_text:
                    try:
                        # Tentar gerar novamente com timeout menor
                        logger.debug("Tentando regenerar resposta...")
                        response = self._model.generate_content(prompt, request_options={"timeout": 10})
                        response_text = response.text
                    except:
                        raise ValueError("Could not extract text from complex response after multiple attempts")
            
            if not response_text:
                raise ValueError("Empty response text from Gemini")
            
            # Extrair SQL da resposta
            sql = self._extract_sql_from_response(response_text)
            
            if not sql:
                raise ValueError("Could not extract valid SQL from response")
            
            generation_time = (time.time() - start_time) * 1000  # em ms
            
            logger.info(f"SQL gerado com sucesso em {generation_time:.0f}ms | Categoria: {category}")
            logger.debug(f"SQL: {sql}")
            
            return {
                "success": True,
                "sql": sql,
                "error": None,
                "generation_time_ms": generation_time,
                "query_category": category.value if category else None
            }
            
        except google_exceptions.ResourceExhausted:
            error_msg = "Gemini API quota exceeded"
            logger.error(error_msg)
            return {
                "success": False,
                "sql": None,
                "error": error_msg,
                "generation_time_ms": (time.time() - start_time) * 1000,
                "query_category": None
            }
            
        except Exception as e:
            error_msg = f"Error generating SQL: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "sql": None,
                "error": error_msg,
                "generation_time_ms": (time.time() - start_time) * 1000,
                "query_category": None
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Verifica se o serviço está operacional."""
        try:
            # Teste simples de geração
            result = await self.generate_sql("count all equipments", timeout=2.0)
            
            return {
                "status": "healthy" if result["success"] else "unhealthy",
                "model": self.settings.gemini_model,
                "feature_enabled": self.settings.llm_sql_feature_enabled,
                "response_time_ms": result.get("generation_time_ms", 0),
                "schema_loaded": True,  # Sistema de prompts carregado
                "total_tables": len(self.schema_prompts.schema_tables)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "feature_enabled": self.settings.llm_sql_feature_enabled,
                "schema_loaded": False
            }
    
    def get_schema_info(self) -> Dict[str, Any]:
        """Retorna informações sobre o schema carregado."""
        return self.schema_prompts.get_schema_summary() 