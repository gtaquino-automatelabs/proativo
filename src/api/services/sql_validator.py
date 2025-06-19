"""
Sistema de validação e sanitização de queries SQL.

Este módulo implementa validação rigorosa de segurança para queries SQL
geradas automaticamente, prevenindo injeções e comandos perigosos.
"""

import re
import hashlib
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

from ...utils.error_handlers import ValidationError, SecurityError
from ...utils.logger import get_logger

# Configurar logger
logger = get_logger(__name__)


class SQLSecurityLevel(Enum):
    """Níveis de segurança para validação SQL."""
    STRICT = "strict"      # Máxima segurança - apenas SELECT básico
    MODERATE = "moderate"  # Segurança moderada - JOINs e funções simples
    PERMISSIVE = "permissive"  # Mais permissivo - mais funções SQL


class SQLValidationResult(Enum):
    """Resultado da validação SQL."""
    VALID = "valid"
    INVALID = "invalid"
    SANITIZED = "sanitized"
    BLOCKED = "blocked"


@dataclass
class SQLAnalysis:
    """Resultado da análise de uma query SQL."""
    original_query: str
    sanitized_query: str
    validation_result: SQLValidationResult
    security_level: SQLSecurityLevel
    issues_found: List[str]
    suggestions: List[str]
    complexity_score: int
    tables_accessed: List[str]
    columns_accessed: List[str]
    functions_used: List[str]


class SQLValidator:
    """
    Validador robusto de queries SQL com foco em segurança.
    
    Implementa:
    - Whitelist/blacklist de comandos SQL
    - Análise de padrões perigosos
    - Sanitização automática
    - Validação de estrutura
    - Análise de complexidade
    """
    
    def __init__(self, security_level: SQLSecurityLevel = SQLSecurityLevel.STRICT):
        """
        Inicializa o validador SQL.
        
        Args:
            security_level: Nível de segurança a aplicar
        """
        self.security_level = security_level
        
        # Carregar regras de validação
        self._load_validation_rules()
        
        # Métricas
        self.queries_validated = 0
        self.queries_blocked = 0
        self.queries_sanitized = 0
        
        logger.info(f"SQLValidator inicializado com nível {security_level.value}")
    
    def _load_validation_rules(self) -> None:
        """Carrega regras de validação baseadas no nível de segurança."""
        
        # Comandos SQL permitidos por nível
        self.allowed_commands = {
            SQLSecurityLevel.STRICT: {"SELECT"},
            SQLSecurityLevel.MODERATE: {"SELECT", "WITH"},
            SQLSecurityLevel.PERMISSIVE: {"SELECT", "WITH", "EXPLAIN"}
        }
        
        # Comandos sempre bloqueados (independente do nível)
        self.blocked_commands = {
            "DROP", "DELETE", "UPDATE", "INSERT", "CREATE", "ALTER",
            "TRUNCATE", "REPLACE", "MERGE", "GRANT", "REVOKE",
            "EXEC", "EXECUTE", "SP_", "XP_", "CALL", "LOAD",
            "BULK", "OPENROWSET", "OPENDATASOURCE", "OPENXML"
        }
        
        # Funções permitidas por nível
        self.allowed_functions = {
            SQLSecurityLevel.STRICT: {
                "COUNT", "SUM", "AVG", "MIN", "MAX", "ROUND",
                "UPPER", "LOWER", "TRIM", "SUBSTRING", "LENGTH",
                "CURRENT_DATE", "CURRENT_TIME", "NOW"
            },
            SQLSecurityLevel.MODERATE: {
                "COUNT", "SUM", "AVG", "MIN", "MAX", "ROUND",
                "UPPER", "LOWER", "TRIM", "SUBSTRING", "LENGTH",
                "CURRENT_DATE", "CURRENT_TIME", "NOW",
                "COALESCE", "ISNULL", "CASE", "CAST", "CONVERT",
                "DATE_ADD", "DATE_SUB", "DATEDIFF", "EXTRACT"
            },
            SQLSecurityLevel.PERMISSIVE: {
                "COUNT", "SUM", "AVG", "MIN", "MAX", "ROUND",
                "UPPER", "LOWER", "TRIM", "SUBSTRING", "LENGTH",
                "CURRENT_DATE", "CURRENT_TIME", "NOW",
                "COALESCE", "ISNULL", "CASE", "CAST", "CONVERT",
                "DATE_ADD", "DATE_SUB", "DATEDIFF", "EXTRACT",
                "ROW_NUMBER", "RANK", "DENSE_RANK", "LAG", "LEAD"
            }
        }
        
        # Tabelas permitidas (whitelist)
        self.allowed_tables = {
            "equipment", "maintenance_orders", "failures", 
            "spare_parts", "technicians", "locations",
            "manufacturers", "equipment_types"
        }
        
        # Campos permitidos por tabela
        self.allowed_fields = {
            "equipment": {
                "id", "name", "type", "status", "location", "manufacturer",
                "model", "installation_date", "last_maintenance", "created_at"
            },
            "maintenance_orders": {
                "id", "equipment_id", "type", "status", "scheduled_date",
                "completion_date", "cost", "description", "technician", "created_at"
            },
            "failures": {
                "id", "equipment_id", "failure_date", "description",
                "severity", "resolution_time", "cost", "created_at"
            }
        }
        
        # Padrões perigosos para detectar
        self.dangerous_patterns = [
            r'--.*',  # Comentários SQL
            r'/\*.*?\*/',  # Comentários de bloco
            r';.*',  # Múltiplas statements
            r'@@\w+',  # Variáveis do sistema
            r'xp_\w+',  # Extended procedures
            r'sp_\w+',  # System procedures
            r'union\s+select',  # UNION injection
            r'0x[0-9a-f]+',  # Hex values
            r'char\s*\(',  # CHAR function (usado em injection)
            r'ascii\s*\(',  # ASCII function
            r'concat\s*\(',  # CONCAT para bypass
            r'sleep\s*\(',  # Sleep function
            r'benchmark\s*\(',  # Benchmark function
            r'load_file\s*\(',  # Load file
            r'into\s+outfile',  # File output
            r'information_schema',  # System schema
            r'pg_\w+',  # PostgreSQL system functions
            r'version\s*\(',  # Version function
            r'current_user',  # Current user
            r'session_user',  # Session user
        ]
        
        # Limites de complexidade
        self.complexity_limits = {
            SQLSecurityLevel.STRICT: {
                "max_joins": 2,
                "max_subqueries": 1,
                "max_where_conditions": 5,
                "max_order_by": 2,
                "max_group_by": 3
            },
            SQLSecurityLevel.MODERATE: {
                "max_joins": 5,
                "max_subqueries": 2,
                "max_where_conditions": 10,
                "max_order_by": 3,
                "max_group_by": 5
            },
            SQLSecurityLevel.PERMISSIVE: {
                "max_joins": 10,
                "max_subqueries": 3,
                "max_where_conditions": 15,
                "max_order_by": 5,
                "max_group_by": 8
            }
        }
    
    def validate_sql(self, sql_query: str) -> SQLAnalysis:
        """
        Valida e analisa uma query SQL completa.
        
        Args:
            sql_query: Query SQL para validar
            
        Returns:
            SQLAnalysis: Resultado completo da análise
            
        Raises:
            ValidationError: Se query for inválida
            SecurityError: Se query for considerada perigosa
        """
        try:
            self.queries_validated += 1
            
            # Normalizar query
            normalized_query = self._normalize_query(sql_query)
            
            # Verificar padrões perigosos
            dangerous_issues = self._check_dangerous_patterns(normalized_query)
            if dangerous_issues:
                self.queries_blocked += 1
                raise SecurityError(f"Query contém padrões perigosos: {dangerous_issues}")
            
            # Verificar comandos bloqueados
            blocked_commands = self._check_blocked_commands(normalized_query)
            if blocked_commands:
                self.queries_blocked += 1
                raise SecurityError(f"Query contém comandos bloqueados: {blocked_commands}")
            
            # Verificar comandos permitidos
            command_issues = self._check_allowed_commands(normalized_query)
            
            # Analisar estrutura SQL
            structure_analysis = self._analyze_sql_structure(normalized_query)
            
            # Verificar complexidade
            complexity_issues = self._check_complexity(structure_analysis)
            
            # Verificar tabelas e campos
            table_field_issues = self._check_tables_and_fields(structure_analysis)
            
            # Sanitizar query se necessário
            sanitized_query, sanitization_applied = self._sanitize_query(normalized_query)
            
            # Compilar todos os issues
            all_issues = command_issues + complexity_issues + table_field_issues
            
            # Determinar resultado da validação
            if all_issues:
                if sanitization_applied:
                    self.queries_sanitized += 1
                    validation_result = SQLValidationResult.SANITIZED
                else:
                    validation_result = SQLValidationResult.INVALID
            else:
                validation_result = SQLValidationResult.VALID
            
            # Gerar sugestões
            suggestions = self._generate_suggestions(all_issues, structure_analysis)
            
            # Calcular score de complexidade
            complexity_score = self._calculate_complexity_score(structure_analysis)
            
            analysis = SQLAnalysis(
                original_query=sql_query,
                sanitized_query=sanitized_query,
                validation_result=validation_result,
                security_level=self.security_level,
                issues_found=all_issues,
                suggestions=suggestions,
                complexity_score=complexity_score,
                tables_accessed=structure_analysis.get("tables", []),
                columns_accessed=structure_analysis.get("columns", []),
                functions_used=structure_analysis.get("functions", [])
            )
            
            logger.info("Query SQL validada", extra={
                "result": validation_result.value,
                "issues_count": len(all_issues),
                "complexity_score": complexity_score
            })
            
            return analysis
            
        except Exception as e:
            logger.error(f"Erro na validação SQL: {str(e)}")
            if isinstance(e, (ValidationError, SecurityError)):
                raise e
            else:
                raise ValidationError(f"Falha na validação SQL: {str(e)}")
    
    def _normalize_query(self, query: str) -> str:
        """Normaliza a query para análise."""
        # Remover espaços extras
        normalized = re.sub(r'\s+', ' ', query.strip())
        
        # Converter para maiúsculo para análise (preservar original)
        return normalized
    
    def _check_dangerous_patterns(self, query: str) -> List[str]:
        """Verifica padrões perigosos na query."""
        issues = []
        query_upper = query.upper()
        
        for pattern in self.dangerous_patterns:
            if re.search(pattern, query_upper, re.IGNORECASE):
                issues.append(f"Padrão perigoso detectado: {pattern}")
        
        return issues
    
    def _check_blocked_commands(self, query: str) -> List[str]:
        """Verifica comandos bloqueados."""
        issues = []
        query_upper = query.upper()
        
        for command in self.blocked_commands:
            # Verificar comando como palavra completa
            pattern = r'\b' + re.escape(command) + r'\b'
            if re.search(pattern, query_upper):
                issues.append(f"Comando bloqueado: {command}")
        
        return issues
    
    def _check_allowed_commands(self, query: str) -> List[str]:
        """Verifica se apenas comandos permitidos são usados."""
        issues = []
        query_upper = query.upper()
        
        allowed = self.allowed_commands[self.security_level]
        
        # Extrair comandos SQL principais
        sql_commands = re.findall(r'\b(?:SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|TRUNCATE|WITH|EXPLAIN)\b', query_upper)
        
        for command in sql_commands:
            if command not in allowed:
                issues.append(f"Comando não permitido no nível {self.security_level.value}: {command}")
        
        return issues
    
    def _analyze_sql_structure(self, query: str) -> Dict[str, Any]:
        """Analisa estrutura da query SQL."""
        query_upper = query.upper()
        
        # Extrair tabelas
        tables = self._extract_tables(query_upper)
        
        # Extrair colunas
        columns = self._extract_columns(query)
        
        # Extrair funções
        functions = self._extract_functions(query_upper)
        
        # Contar elementos estruturais
        joins = len(re.findall(r'\bJOIN\b', query_upper))
        subqueries = len(re.findall(r'\(\s*SELECT\b', query_upper))
        where_conditions = len(re.findall(r'\bAND\b|\bOR\b', query_upper)) + (1 if 'WHERE' in query_upper else 0)
        order_by = len(re.findall(r'\bORDER\s+BY\b', query_upper))
        group_by = len(re.findall(r'\bGROUP\s+BY\b', query_upper))
        
        return {
            "tables": tables,
            "columns": columns,
            "functions": functions,
            "joins": joins,
            "subqueries": subqueries,
            "where_conditions": where_conditions,
            "order_by": order_by,
            "group_by": group_by
        }
    
    def _extract_tables(self, query: str) -> List[str]:
        """Extrai nomes de tabelas da query."""
        tables = []
        
        # Padrões para extrair tabelas
        patterns = [
            r'\bFROM\s+(\w+)',
            r'\bJOIN\s+(\w+)',
            r'\bUPDATE\s+(\w+)',
            r'\bINTO\s+(\w+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, query)
            tables.extend(matches)
        
        return list(set(tables))
    
    def _extract_columns(self, query: str) -> List[str]:
        """Extrai nomes de colunas da query."""
        columns = []
        
        # Extrair colunas do SELECT
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', query, re.IGNORECASE | re.DOTALL)
        if select_match:
            select_part = select_match.group(1)
            # Dividir por vírgula e limpar
            column_parts = select_part.split(',')
            for part in column_parts:
                part = part.strip()
                # Extrair nome da coluna (ignorar funções e aliases)
                column_match = re.search(r'\b(\w+)\b', part)
                if column_match and column_match.group(1).upper() not in ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX']:
                    columns.append(column_match.group(1))
        
        return list(set(columns))
    
    def _extract_functions(self, query: str) -> List[str]:
        """Extrai funções SQL usadas."""
        functions = []
        
        # Padrão para funções SQL
        function_pattern = r'\b(\w+)\s*\('
        matches = re.findall(function_pattern, query)
        
        for match in matches:
            if match.upper() in self.allowed_functions[self.security_level]:
                functions.append(match.upper())
        
        return list(set(functions))
    
    def _check_complexity(self, structure: Dict[str, Any]) -> List[str]:
        """Verifica complexidade da query."""
        issues = []
        limits = self.complexity_limits[self.security_level]
        
        checks = [
            ("joins", "max_joins", "JOINs"),
            ("subqueries", "max_subqueries", "subqueries"),
            ("where_conditions", "max_where_conditions", "condições WHERE"),
            ("order_by", "max_order_by", "cláusulas ORDER BY"),
            ("group_by", "max_group_by", "cláusulas GROUP BY")
        ]
        
        for key, limit_key, description in checks:
            if structure[key] > limits[limit_key]:
                issues.append(f"Muitos {description}: {structure[key]} > {limits[limit_key]}")
        
        return issues
    
    def _check_tables_and_fields(self, structure: Dict[str, Any]) -> List[str]:
        """Verifica se tabelas e campos são permitidos."""
        issues = []
        
        # Verificar tabelas
        for table in structure["tables"]:
            if table.lower() not in self.allowed_tables:
                issues.append(f"Tabela não permitida: {table}")
        
        # Verificar campos (básico)
        for column in structure["columns"]:
            if column not in ["*", "id", "count"] and len(column) < 2:
                issues.append(f"Nome de coluna suspeito: {column}")
        
        return issues
    
    def _sanitize_query(self, query: str) -> Tuple[str, bool]:
        """Sanitiza a query removendo elementos perigosos."""
        sanitized = query
        sanitization_applied = False
        
        # Remover comentários
        if re.search(r'--', sanitized):
            sanitized = re.sub(r'--.*$', '', sanitized, flags=re.MULTILINE)
            sanitization_applied = True
        
        if re.search(r'/\*.*?\*/', sanitized):
            sanitized = re.sub(r'/\*.*?\*/', '', sanitized, flags=re.DOTALL)
            sanitization_applied = True
        
        # Remover múltiplas statements
        if ';' in sanitized and not sanitized.strip().endswith(';'):
            parts = sanitized.split(';')
            sanitized = parts[0] + ';'
            sanitization_applied = True
        
        # Limitar query a uma linha em casos extremos
        if '\n' in sanitized and sanitization_applied:
            sanitized = ' '.join(sanitized.split())
        
        return sanitized.strip(), sanitization_applied
    
    def _generate_suggestions(self, issues: List[str], structure: Dict[str, Any]) -> List[str]:
        """Gera sugestões para melhorar a query."""
        suggestions = []
        
        if any("JOINs" in issue for issue in issues):
            suggestions.append("Considere simplificar os JOINs ou dividir em consultas menores")
        
        if any("subqueries" in issue for issue in issues):
            suggestions.append("Tente reescrever subqueries como JOINs quando possível")
        
        if any("WHERE" in issue for issue in issues):
            suggestions.append("Simplifique as condições WHERE usando operadores mais eficientes")
        
        if structure["tables"] and not structure["columns"]:
            suggestions.append("Especifique colunas específicas em vez de usar SELECT *")
        
        if not suggestions:
            suggestions.append("Query está dentro dos padrões de segurança")
        
        return suggestions
    
    def _calculate_complexity_score(self, structure: Dict[str, Any]) -> int:
        """Calcula score de complexidade da query."""
        score = 0
        
        # Pesos para diferentes elementos
        weights = {
            "tables": 2,
            "joins": 3,
            "subqueries": 5,
            "where_conditions": 1,
            "functions": 2,
            "order_by": 1,
            "group_by": 2
        }
        
        for key, weight in weights.items():
            if key in structure:
                if isinstance(structure[key], list):
                    score += len(structure[key]) * weight
                else:
                    score += structure[key] * weight
        
        return score
    
    def get_security_summary(self) -> Dict[str, Any]:
        """Retorna resumo de segurança do validador."""
        total_queries = self.queries_validated
        
        return {
            "security_level": self.security_level.value,
            "total_queries_validated": total_queries,
            "queries_blocked": self.queries_blocked,
            "queries_sanitized": self.queries_sanitized,
            "queries_passed": total_queries - self.queries_blocked - self.queries_sanitized,
            "block_rate": round(self.queries_blocked / total_queries, 3) if total_queries > 0 else 0,
            "sanitization_rate": round(self.queries_sanitized / total_queries, 3) if total_queries > 0 else 0,
            "allowed_tables": list(self.allowed_tables),
            "allowed_commands": list(self.allowed_commands[self.security_level])
        } 