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
        
        # Schema do banco - versão simplificada para o MVP
        self.db_schema = self._get_database_schema()
        
        # Exemplos few-shot para melhorar a qualidade
        self.few_shot_examples = self._get_few_shot_examples()
        
        logger.info("LLMSQLGenerator inicializado")
    
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
    
    def _get_database_schema(self) -> str:
        """Retorna o schema do banco de dados para contexto."""
        return """
Database: PostgreSQL
Schema: proativo

Table: equipments
- id (INTEGER, PRIMARY KEY)
- name (VARCHAR) - unique identifier like 'T001', 'DJ-001'
- type (VARCHAR) - 'Transformer', 'Circuit Breaker', 'Motor', 'Generator'
- status (VARCHAR) - 'Active', 'Inactive', 'Maintenance', 'Retired'
- criticality (VARCHAR) - 'Low', 'Medium', 'High', 'Critical'
- location (VARCHAR)
- installation_date (DATE)
- last_maintenance (DATE)
- created_at (TIMESTAMP)

Table: maintenances
- id (INTEGER, PRIMARY KEY)
- equipment_id (INTEGER, FOREIGN KEY -> equipments.id)
- maintenance_type (VARCHAR) - 'Preventive', 'Corrective', 'Predictive'
- maintenance_date (DATE)
- description (TEXT)
- cost (DECIMAL)
- duration_hours (INTEGER)
- technician (VARCHAR)
- status (VARCHAR) - 'Scheduled', 'In Progress', 'Completed', 'Cancelled'
- created_at (TIMESTAMP)

Common patterns:
- Equipment names often start with type prefix: 'T' for Transformer, 'DJ' for Circuit Breaker
- Dates are in ISO format: 'YYYY-MM-DD'
- Status values are predefined enums
"""
    
    def _get_few_shot_examples(self) -> List[Dict[str, str]]:
        """Retorna exemplos few-shot para melhorar a geração."""
        return [
            {
                "question": "Quantos transformadores temos?",
                "sql": "SELECT COUNT(*) AS total FROM equipments WHERE type = 'Transformer';"
            },
            {
                "question": "Liste todos os equipamentos em manutenção",
                "sql": "SELECT name, type, location FROM equipments WHERE status = 'Maintenance' ORDER BY name;"
            },
            {
                "question": "Qual foi a última manutenção do transformador T001?",
                "sql": """SELECT e.name, m.maintenance_date, m.maintenance_type, m.description 
FROM equipments e 
JOIN maintenances m ON e.id = m.equipment_id 
WHERE e.name = 'T001' 
ORDER BY m.maintenance_date DESC 
LIMIT 1;"""
            },
            {
                "question": "Equipamentos críticos que estão ativos",
                "sql": "SELECT name, type, location FROM equipments WHERE criticality = 'Critical' AND status = 'Active' ORDER BY name;"
            },
            {
                "question": "Quantas manutenções foram feitas este ano?",
                "sql": "SELECT COUNT(*) AS total FROM maintenances WHERE EXTRACT(YEAR FROM maintenance_date) = EXTRACT(YEAR FROM CURRENT_DATE);"
            }
        ]
    
    def _build_prompt(self, user_question: str) -> str:
        """Constrói o prompt para o Gemini."""
        # Montar exemplos
        examples_text = "\n\n".join([
            f"Question: {ex['question']}\nSQL: {ex['sql']}"
            for ex in self.few_shot_examples
        ])
        
        prompt = f"""You are a PostgreSQL expert. Generate SQL queries based on natural language questions.

DATABASE SCHEMA:
{self.db_schema}

EXAMPLES:
{examples_text}

RULES:
1. Generate ONLY the SQL query, no explanations
2. Use PostgreSQL syntax
3. Always end with semicolon
4. Use appropriate JOINs when needed
5. Add meaningful column aliases
6. Sort results when it makes sense
7. ONLY use SELECT statements (no INSERT, UPDATE, DELETE)

QUESTION: {user_question}

SQL:"""
        
        return prompt
    
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
        """
        start_time = time.time()
        
        if not self.settings.llm_sql_feature_enabled:
            return {
                "success": False,
                "sql": None,
                "error": "LLM SQL feature is disabled",
                "generation_time_ms": 0
            }
        
        try:
            # Validar entrada
            if not user_question or not user_question.strip():
                return {
                    "success": False,
                    "sql": None,
                    "error": "Question cannot be empty",
                    "generation_time_ms": 0
                }
            
            # Construir prompt
            prompt = self._build_prompt(user_question.strip())
            
            # Usar timeout específico para SQL se não fornecido
            if timeout is None:
                timeout = self.settings.llm_sql_timeout
            
            # Gerar SQL com Gemini
            logger.debug(f"Gerando SQL para: {user_question}")
            
            response = self._model.generate_content(prompt)
            
            if not response:
                raise ValueError("Empty response from Gemini")
            
            # Extrair texto da resposta (pode ser complexa)
            try:
                response_text = response.text
            except ValueError:
                # Resposta complexa - extrair o texto do primeiro candidato
                if response.candidates and response.candidates[0].content.parts:
                    response_text = response.candidates[0].content.parts[0].text
                else:
                    raise ValueError("Could not extract text from complex response")
            
            if not response_text:
                raise ValueError("Empty response text from Gemini")
            
            # Extrair SQL da resposta
            sql = self._extract_sql_from_response(response_text)
            
            if not sql:
                raise ValueError("Could not extract valid SQL from response")
            
            generation_time = (time.time() - start_time) * 1000  # em ms
            
            logger.info(f"SQL gerado com sucesso em {generation_time:.0f}ms")
            logger.debug(f"SQL: {sql}")
            
            return {
                "success": True,
                "sql": sql,
                "error": None,
                "generation_time_ms": generation_time
            }
            
        except google_exceptions.ResourceExhausted:
            error_msg = "Gemini API quota exceeded"
            logger.error(error_msg)
            return {
                "success": False,
                "sql": None,
                "error": error_msg,
                "generation_time_ms": (time.time() - start_time) * 1000
            }
            
        except Exception as e:
            error_msg = f"Error generating SQL: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "sql": None,
                "error": error_msg,
                "generation_time_ms": (time.time() - start_time) * 1000
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
                "response_time_ms": result.get("generation_time_ms", 0)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "feature_enabled": self.settings.llm_sql_feature_enabled
            } 