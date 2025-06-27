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
    
    def __init__(self, security_level: SQLSecurityLevel = SQLSecurityLevel.MODERATE):
        """
        Inicializa o validador SQL.
        
        Args:
            security_level: Nível de segurança a aplicar (padrão: MODERATE para protótipo)
        """
        self.security_level = security_level
        
        # Carregar regras de validação
        self._load_validation_rules()
        
        # Métricas
        self.queries_validated = 0
        self.queries_blocked = 0
        self.queries_sanitized = 0
        
        logger.info(f"SQLValidator inicializado com nível {security_level.value}")
    
    @classmethod
    def for_prototype(cls) -> 'SQLValidator':
        """
        Cria instância do validador configurada para ambiente de protótipo.
        
        Returns:
            SQLValidator: Instância configurada para ser menos restritiva
        """
        return cls(security_level=SQLSecurityLevel.MODERATE)
    
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
        
        # Funções permitidas por nível (expandidas para protótipo)
        self.allowed_functions = {
            SQLSecurityLevel.STRICT: {
                "COUNT", "SUM", "AVG", "MIN", "MAX", "ROUND",
                "UPPER", "LOWER", "TRIM", "SUBSTRING", "LENGTH",
                "CURRENT_DATE", "CURRENT_TIME", "NOW",
                # Funções adicionais para análise de dados
                "COALESCE", "ISNULL", "CASE", "CAST", "CONVERT",
                "DATE_PART", "EXTRACT", "DATE_TRUNC"
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
        
        # Tabelas permitidas (whitelist) - Nomes reais do banco
        self.allowed_tables = {
            # Nomes reais das tabelas no banco de dados
            "equipments", "maintenances", "data_history", "user_feedback",
            # Nomes alternativos e sinônimos para compatibilidade
            "equipment", "maintenance", "maintenance_orders", "failures", 
            "spare_parts", "technicians", "locations",
            "manufacturers", "equipment_types", "assets"
        }
        
        # Campos permitidos por tabela
        self.allowed_fields = {
            "equipments": {
                "id", "code", "name", "description", "equipment_type", "category",
                "criticality", "location", "substation", "manufacturer", "model",
                "serial_number", "manufacturing_year", "installation_date",
                "rated_voltage", "rated_power", "rated_current", "status", "is_critical",
                "metadata_json", "created_at", "updated_at"
            },
            "maintenances": {
                "id", "equipment_id", "maintenance_code", "maintenance_type", "priority",
                "title", "description", "work_performed", "scheduled_date", "start_date",
                "completion_date", "duration_hours", "status", "result", "technician",
                "team", "contractor", "estimated_cost", "actual_cost", "parts_replaced",
                "materials_used", "observations", "requires_followup", "followup_date",
                "metadata_json", "created_at", "updated_at"
            },
            "data_history": {
                "id", "equipment_id", "data_source", "data_type", "timestamp",
                "measurement_type", "measurement_value", "measurement_unit",
                "text_value", "condition_status", "alert_level", "inspector",
                "collection_method", "source_file", "source_row", "is_validated",
                "validation_status", "quality_score", "raw_data", "processed_data",
                "metadata_json", "created_at"
            },
            "user_feedback": {
                "id", "session_id", "message_id", "rating", "helpful", "comment",
                "user_id", "user_agent", "ip_address", "original_query",
                "response_snippet", "confidence_score", "feedback_category",
                "improvement_priority", "is_processed", "processed_at",
                "metadata_json", "created_at", "updated_at"
            },
            # Manter compatibilidade com nomes antigos
            "equipment": {
                "id", "name", "type", "status", "location", "manufacturer",
                "model", "installation_date", "last_maintenance", "created_at"
            },
            "maintenance_orders": {
                "id", "equipment_id", "type", "status", "scheduled_date",
                "completion_date", "cost", "description", "technician", "created_at"
            }
        }
        
        # Padrões perigosos para detectar
        self.dangerous_patterns = [
            r'--.*',  # Comentários SQL
            r'/\*.*?\*/',  # Comentários de bloco
            r';.+',  # Múltiplas statements (mas não semicolon no final)
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
        
        # Limites de complexidade (suavizados para protótipo)
        self.complexity_limits = {
            SQLSecurityLevel.STRICT: {
                "max_joins": 5,        # Era 2, agora 5
                "max_subqueries": 3,   # Era 1, agora 3  
                "max_where_conditions": 10,  # Era 5, agora 10
                "max_order_by": 3,     # Era 2, agora 3
                "max_group_by": 5      # Era 3, agora 5
            },
            SQLSecurityLevel.MODERATE: {
                "max_joins": 8,        # Era 5, agora 8
                "max_subqueries": 5,   # Era 2, agora 5
                "max_where_conditions": 15,  # Era 10, agora 15
                "max_order_by": 5,     # Era 3, agora 5
                "max_group_by": 8      # Era 5, agora 8
            },
            SQLSecurityLevel.PERMISSIVE: {
                "max_joins": 15,       # Era 10, agora 15
                "max_subqueries": 8,   # Era 3, agora 8
                "max_where_conditions": 25,  # Era 15, agora 25
                "max_order_by": 8,     # Era 5, agora 8
                "max_group_by": 12     # Era 8, agora 12
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
        
        # Verificar tabelas (case-insensitive)
        for table in structure["tables"]:
            if table.lower() not in self.allowed_tables:
                issues.append(f"Tabela não permitida: {table}")
        
        # Verificar campos (mais permissivo - apenas aliases muito curtos)
        for column in structure["columns"]:
            # Permitir *, números, palavras normais e aliases comuns (e, m, d, etc.)
            if (column not in ["*", "id", "count"] and 
                len(column) == 1 and 
                not column.isalpha()):
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
        
        # Remover múltiplas statements (mas permitir semicolon final)
        if ';' in sanitized:
            # Conta quantos semicolons existem
            semicolon_count = sanitized.count(';')
            # Se há mais de um semicolon OU semicolon não está no final, sanitizar
            if semicolon_count > 1 or (semicolon_count == 1 and not sanitized.strip().endswith(';')):
                parts = sanitized.split(';')
                sanitized = parts[0].strip()
                # Adiciona semicolon final se a query original terminava com ele
                if sanitized and not sanitized.endswith(';'):
                    sanitized += ';'
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