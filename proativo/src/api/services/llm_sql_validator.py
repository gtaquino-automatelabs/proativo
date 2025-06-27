"""
Validador SQL simplificado para queries geradas por LLM.

Este módulo implementa validação essencial de segurança para queries SQL
geradas pelo LLM, com foco em simplicidade e eficiência para o MVP.
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

from ...utils.logger import get_logger

# Configurar logger
logger = get_logger(__name__)


class ValidationStatus(Enum):
    """Status da validação SQL."""
    SAFE = "safe"
    UNSAFE = "unsafe"
    WARNING = "warning"


@dataclass
class ValidationResult:
    """Resultado da validação SQL simplificada."""
    status: ValidationStatus
    is_valid: bool
    cleaned_sql: str
    warnings: List[str]
    error: Optional[str] = None


class LLMSQLValidator:
    """
    Validador SQL simplificado para queries geradas por LLM.
    
    Foco em validações essenciais:
    - Apenas SELECT permitido
    - Sem comandos perigosos
    - Sintaxe SQL básica
    - Prevenção de SQL injection simples
    """
    
    def __init__(self):
        """Inicializa o validador simplificado."""
        # Comandos perigosos que NUNCA devem aparecer
        self.dangerous_keywords = [
            "DROP", "DELETE", "UPDATE", "INSERT", "CREATE", "ALTER",
            "TRUNCATE", "REPLACE", "MERGE", "GRANT", "REVOKE",
            "EXEC", "EXECUTE", "CALL", "LOAD", "INTO OUTFILE",
            "BULK", "OPENROWSET", "OPENDATASOURCE"
        ]
        
        # Padrões suspeitos
        self.suspicious_patterns = [
            r'--.*$',           # Comentários SQL em linha
            r'/\*.*?\*/',       # Comentários de bloco
            r';\s*(?:SELECT|DROP|DELETE)',  # Múltiplos statements perigosos
            r'0x[0-9a-f]+',     # Valores hexadecimais
            r'union\s+all\s+select',  # UNION injection
            r'concat.*\(.*char.*\)',  # Bypass com concat/char
            r'sleep\s*\(',      # Sleep function
            r'waitfor\s+delay', # SQL Server delay
            r'pg_sleep',        # PostgreSQL sleep
            r'benchmark\s*\(',  # MySQL benchmark
        ]
        
        # Tabelas permitidas (as principais do sistema)
        self.allowed_tables = {
            "equipments", "maintenances", "data_history", "user_feedback",
            # Aliases comuns
            "e", "m", "d", "f"
        }
        
        logger.info("LLMSQLValidator inicializado (versão simplificada para MVP)")
    
    def validate(self, sql_query: str) -> ValidationResult:
        """
        Valida uma query SQL gerada pelo LLM.
        
        Args:
            sql_query: Query SQL para validar
            
        Returns:
            ValidationResult: Resultado da validação
        """
        if not sql_query or not sql_query.strip():
            return ValidationResult(
                status=ValidationStatus.UNSAFE,
                is_valid=False,
                cleaned_sql="",
                warnings=[],
                error="Query vazia"
            )
        
        # Limpar e normalizar
        cleaned_sql = self._clean_query(sql_query)
        normalized = cleaned_sql.upper()
        
        # 1. Verificar se é apenas SELECT
        if not self._is_select_only(normalized):
            return ValidationResult(
                status=ValidationStatus.UNSAFE,
                is_valid=False,
                cleaned_sql=cleaned_sql,
                warnings=[],
                error="Apenas queries SELECT são permitidas"
            )
        
        # 2. Verificar comandos perigosos
        dangerous_found = self._check_dangerous_keywords(normalized)
        if dangerous_found:
            return ValidationResult(
                status=ValidationStatus.UNSAFE,
                is_valid=False,
                cleaned_sql=cleaned_sql,
                warnings=[],
                error=f"Comando perigoso detectado: {', '.join(dangerous_found)}"
            )
        
        # 3. Verificar padrões suspeitos
        suspicious_found = self._check_suspicious_patterns(cleaned_sql)
        if suspicious_found:
            return ValidationResult(
                status=ValidationStatus.UNSAFE,
                is_valid=False,
                cleaned_sql=cleaned_sql,
                warnings=[],
                error=f"Padrão suspeito detectado: {suspicious_found[0]}"
            )
        
        # 4. Validações básicas de sintaxe
        syntax_warnings = self._check_basic_syntax(cleaned_sql)
        
        # 5. Verificar limite de complexidade (muito básico)
        complexity_warnings = self._check_complexity(cleaned_sql)
        
        # Compilar warnings
        all_warnings = syntax_warnings + complexity_warnings
        
        # Se chegou aqui, a query é segura
        status = ValidationStatus.WARNING if all_warnings else ValidationStatus.SAFE
        
        logger.debug(f"Query validada: status={status.value}, warnings={len(all_warnings)}")
        
        return ValidationResult(
            status=status,
            is_valid=True,
            cleaned_sql=cleaned_sql,
            warnings=all_warnings,
            error=None
        )
    
    def _clean_query(self, query: str) -> str:
        """Limpa e normaliza a query."""
        # Remover espaços extras
        cleaned = ' '.join(query.split())
        
        # Garantir que termina com ponto-e-vírgula
        if not cleaned.rstrip().endswith(';'):
            cleaned = cleaned.rstrip() + ';'
        
        return cleaned
    
    def _is_select_only(self, normalized_query: str) -> bool:
        """Verifica se a query contém apenas SELECT."""
        # Remover CTEs (WITH) se existirem
        query_without_cte = re.sub(r'^WITH\s+.*?\s+SELECT', 'SELECT', normalized_query, flags=re.DOTALL)
        
        # Verificar se começa com SELECT
        if not query_without_cte.strip().startswith('SELECT'):
            return False
        
        # Verificar se não tem outros comandos DML/DDL
        dml_ddl_commands = [
            'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER',
            'TRUNCATE', 'REPLACE', 'MERGE'
        ]
        
        for cmd in dml_ddl_commands:
            if re.search(rf'\b{cmd}\b', query_without_cte):
                return False
        
        return True
    
    def _check_dangerous_keywords(self, normalized_query: str) -> List[str]:
        """Verifica presença de palavras-chave perigosas."""
        found = []
        
        for keyword in self.dangerous_keywords:
            if re.search(rf'\b{keyword}\b', normalized_query):
                found.append(keyword)
        
        return found
    
    def _check_suspicious_patterns(self, query: str) -> List[str]:
        """Verifica padrões suspeitos de SQL injection."""
        found = []
        
        for pattern in self.suspicious_patterns:
            if re.search(pattern, query, re.IGNORECASE | re.MULTILINE):
                found.append(pattern)
        
        return found
    
    def _check_basic_syntax(self, query: str) -> List[str]:
        """Verificações básicas de sintaxe."""
        warnings = []
        
        # Verificar parênteses balanceados
        if query.count('(') != query.count(')'):
            warnings.append("Parênteses desbalanceados")
        
        # Verificar aspas balanceadas
        single_quotes = query.count("'") % 2
        double_quotes = query.count('"') % 2
        if single_quotes != 0:
            warnings.append("Aspas simples desbalanceadas")
        if double_quotes != 0:
            warnings.append("Aspas duplas desbalanceadas")
        
        # Verificar múltiplos ponto-e-vírgula (possível múltiplas queries)
        if query.count(';') > 1:
            warnings.append("Múltiplos ponto-e-vírgula detectados")
        
        return warnings
    
    def _check_complexity(self, query: str) -> List[str]:
        """Verificações muito básicas de complexidade."""
        warnings = []
        query_upper = query.upper()
        
        # Contar JOINs (aviso se muitos)
        join_count = len(re.findall(r'\bJOIN\b', query_upper))
        if join_count > 10:
            warnings.append(f"Query muito complexa: {join_count} JOINs")
        
        # Verificar subqueries aninhadas profundamente
        nested_selects = len(re.findall(r'\(\s*SELECT', query_upper))
        if nested_selects > 5:
            warnings.append(f"Muitas subqueries aninhadas: {nested_selects}")
        
        # Verificar tamanho da query
        if len(query) > 5000:
            warnings.append("Query muito longa (>5000 caracteres)")
        
        return warnings
    
    def is_read_only(self, sql_query: str) -> bool:
        """
        Verifica rapidamente se a query é somente leitura.
        
        Args:
            sql_query: Query SQL
            
        Returns:
            bool: True se for apenas leitura
        """
        result = self.validate(sql_query)
        return result.is_valid and result.status != ValidationStatus.UNSAFE
    
    def get_safe_query(self, sql_query: str) -> Optional[str]:
        """
        Retorna a query limpa se for segura, None caso contrário.
        
        Args:
            sql_query: Query SQL
            
        Returns:
            Optional[str]: Query limpa ou None
        """
        result = self.validate(sql_query)
        
        if result.is_valid:
            return result.cleaned_sql
        else:
            logger.warning(f"Query rejeitada: {result.error}")
            return None
    
    def explain_rejection(self, sql_query: str) -> str:
        """
        Explica por que uma query foi rejeitada.
        
        Args:
            sql_query: Query SQL
            
        Returns:
            str: Explicação da rejeição
        """
        result = self.validate(sql_query)
        
        if result.is_valid:
            return "Query aceita"
        
        explanation = f"Query rejeitada: {result.error}"
        
        if result.warnings:
            explanation += f"\nAvisos adicionais: {', '.join(result.warnings)}"
        
        return explanation 