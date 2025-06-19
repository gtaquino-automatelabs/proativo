"""
Processador de queries que converte linguagem natural em SQL.

Este módulo implementa a análise de consultas em linguagem natural,
identificação de intenções, geração de SQL seguro e validação.
"""

import re
import json
import sqlparse
from typing import Dict, Any, List, Optional, Tuple, Union, Set
from enum import Enum
from dataclasses import dataclass
import logging
from datetime import datetime, timedelta

from ..config import get_settings
from ...utils.error_handlers import ValidationError, DataProcessingError
from ...utils.logger import get_logger

# Configurar logger
logger = get_logger(__name__)


class QueryType(Enum):
    """Tipos de consulta identificados."""
    EQUIPMENT_STATUS = "equipment_status"
    MAINTENANCE_SCHEDULE = "maintenance_schedule"
    FAILURE_ANALYSIS = "failure_analysis"
    COST_ANALYSIS = "cost_analysis"
    HISTORICAL_DATA = "historical_data"
    GENERAL_SEARCH = "general_search"
    UNKNOWN = "unknown"


class QueryIntent(Enum):
    """Intenções de consulta identificadas."""
    LIST = "list"  # Listar itens
    COUNT = "count"  # Contar registros
    SEARCH = "search"  # Buscar específico
    AGGREGATE = "aggregate"  # Agregações (soma, média)
    COMPARE = "compare"  # Comparações
    FILTER = "filter"  # Filtros específicos
    REPORT = "report"  # Relatórios
    UNKNOWN = "unknown"


@dataclass
class QueryAnalysis:
    """Resultado da análise de uma query."""
    original_query: str
    query_type: QueryType
    intent: QueryIntent
    entities: Dict[str, Any]
    filters: Dict[str, Any]
    sql_query: str
    confidence: float
    explanation: str


@dataclass
class ValidationResult:
    """Resultado da validação de uma query SQL."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    sanitized_sql: str
    risk_level: str  # low, medium, high
    complexity_score: int


class SQLSanitizer:
    """Classe responsável pela sanitização de queries SQL."""
    
    def __init__(self):
        """Inicializa o sanitizador SQL."""
        # Caracteres perigosos que devem ser escapados
        self.dangerous_chars = {
            "'": "''",  # Escape de aspas simples
            '"': '""',  # Escape de aspas duplas
            "\\": "\\\\",  # Escape de backslash
            "\x00": "",  # Remove null bytes
            "\x1a": "",  # Remove substitute characters
        }
        
        # Padrões de SQL injection conhecidos
        self.injection_patterns = [
            r"(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b.*?;)",
            r"('|(\\x27)|(\\x2D\\x2D)|;|\\x00)",
            r"(\b(or|and)\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+['\"]?)",
            r"(\/\*.*?\*\/)",  # Comentários SQL
            r"(\-\-.*)",  # Comentários de linha
            r"(\bxp_|\bsp_)",  # Stored procedures
        ]
        
        # Palavras-chave SQL que devem ser controladas
        self.restricted_keywords = {
            "CRITICAL": ["DROP", "DELETE", "UPDATE", "INSERT", "CREATE", "ALTER", "TRUNCATE"],
            "ADMINISTRATIVE": ["EXEC", "EXECUTE", "SP_", "XP_", "GRANT", "REVOKE"],
            "SYSTEM": ["SHUTDOWN", "BACKUP", "RESTORE", "DBCC"],
        }
    
    def sanitize_value(self, value: str) -> str:
        """Sanitiza um valor individual."""
        if not isinstance(value, str):
            return str(value)
        
        # Escapar caracteres perigosos
        sanitized = value
        for char, replacement in self.dangerous_chars.items():
            sanitized = sanitized.replace(char, replacement)
        
        # Remover comentários SQL
        sanitized = re.sub(r'--.*$', '', sanitized, flags=re.MULTILINE)
        sanitized = re.sub(r'/\*.*?\*/', '', sanitized, flags=re.DOTALL)
        
        # Limitar tamanho
        if len(sanitized) > 1000:
            sanitized = sanitized[:1000]
        
        return sanitized.strip()
    
    def detect_injection_attempts(self, sql: str) -> List[str]:
        """Detecta tentativas de SQL injection."""
        threats = []
        sql_lower = sql.lower()
        
        for pattern in self.injection_patterns:
            matches = re.findall(pattern, sql_lower, re.IGNORECASE | re.MULTILINE)
            if matches:
                threats.append(f"Padrão suspeito detectado: {pattern}")
        
        return threats
    
    def validate_keywords(self, sql: str) -> List[str]:
        """Valida palavras-chave perigosas."""
        issues = []
        sql_upper = sql.upper()
        
        for category, keywords in self.restricted_keywords.items():
            for keyword in keywords:
                if keyword in sql_upper:
                    issues.append(f"Palavra-chave {category.lower()} não permitida: {keyword}")
        
        return issues


class SQLStructureValidator:
    """Classe responsável pela validação da estrutura SQL."""
    
    def __init__(self):
        """Inicializa o validador de estrutura."""
        # Schema do banco de dados
        self.database_schema = {
            "equipment": {
                "columns": ["id", "name", "type", "status", "location", "manufacturer", "model", "installation_date", "last_maintenance", "created_at", "updated_at"],
                "types": {
                    "id": "VARCHAR",
                    "name": "VARCHAR",
                    "type": "VARCHAR", 
                    "status": "VARCHAR",
                    "location": "VARCHAR",
                    "manufacturer": "VARCHAR",
                    "model": "VARCHAR",
                    "installation_date": "DATE",
                    "last_maintenance": "DATE",
                    "created_at": "TIMESTAMP",
                    "updated_at": "TIMESTAMP"
                }
            },
            "maintenance_orders": {
                "columns": ["id", "equipment_id", "type", "status", "scheduled_date", "completion_date", "cost", "description", "technician", "created_at", "updated_at"],
                "types": {
                    "id": "VARCHAR",
                    "equipment_id": "VARCHAR",
                    "type": "VARCHAR",
                    "status": "VARCHAR",
                    "scheduled_date": "DATE",
                    "completion_date": "DATE",
                    "cost": "NUMERIC",
                    "description": "TEXT",
                    "technician": "VARCHAR",
                    "created_at": "TIMESTAMP",
                    "updated_at": "TIMESTAMP"
                }
            },
            "failures": {
                "columns": ["id", "equipment_id", "failure_date", "description", "severity", "resolution_time", "cost", "created_at", "updated_at"],
                "types": {
                    "id": "VARCHAR",
                    "equipment_id": "VARCHAR",
                    "failure_date": "DATE",
                    "description": "TEXT",
                    "severity": "VARCHAR",
                    "resolution_time": "INTEGER",
                    "cost": "NUMERIC",
                    "created_at": "TIMESTAMP",
                    "updated_at": "TIMESTAMP"
                }
            }
        }
        
        # Funções SQL permitidas
        self.allowed_functions = {
            "COUNT", "SUM", "AVG", "MAX", "MIN", "COALESCE", "NULLIF",
            "UPPER", "LOWER", "TRIM", "LENGTH", "SUBSTRING",
            "DATE", "EXTRACT", "NOW", "CURRENT_DATE", "CURRENT_TIMESTAMP"
        }
        
        # Operadores permitidos
        self.allowed_operators = {
            "=", "!=", "<>", "<", ">", "<=", ">=", "LIKE", "ILIKE", 
            "IN", "NOT IN", "IS NULL", "IS NOT NULL", "BETWEEN",
            "AND", "OR", "NOT"
        }
    
    def validate_syntax(self, sql: str) -> List[str]:
        """Valida a sintaxe SQL usando sqlparse."""
        errors = []
        
        try:
            parsed = sqlparse.parse(sql)
            if not parsed:
                errors.append("SQL não pôde ser parseado")
                return errors
            
            # Verificar se há múltiplas statements
            if len(parsed) > 1:
                errors.append("Múltiplas statements SQL não são permitidas")
            
            # Verificar estrutura básica
            statement = parsed[0]
            if not str(statement).strip().upper().startswith('SELECT'):
                errors.append("Apenas queries SELECT são permitidas")
            
        except Exception as e:
            errors.append(f"Erro de sintaxe SQL: {str(e)}")
        
        return errors
    
    def validate_tables_and_columns(self, sql: str) -> List[str]:
        """Valida se tabelas e colunas existem no schema."""
        errors = []
        
        try:
            parsed = sqlparse.parse(sql)[0]
            
            # Extrair tabelas mencionadas
            tables = self._extract_tables(parsed)
            for table in tables:
                if table not in self.database_schema:
                    errors.append(f"Tabela não encontrada: {table}")
            
            # Extrair colunas mencionadas
            columns = self._extract_columns(parsed)
            for table, column in columns:
                if table in self.database_schema:
                    if column not in self.database_schema[table]["columns"]:
                        errors.append(f"Coluna não encontrada: {table}.{column}")
                elif table == "":  # Coluna sem tabela especificada
                    # Verificar se existe em alguma tabela
                    found = False
                    for schema_table, schema_info in self.database_schema.items():
                        if column in schema_info["columns"]:
                            found = True
                            break
                    if not found:
                        errors.append(f"Coluna não encontrada: {column}")
        
        except Exception as e:
            errors.append(f"Erro ao validar tabelas/colunas: {str(e)}")
        
        return errors
    
    def validate_functions(self, sql: str) -> List[str]:
        """Valida se as funções usadas são permitidas."""
        errors = []
        
        # Extrair funções do SQL
        function_pattern = r'\b([A-Z_]+)\s*\('
        functions = re.findall(function_pattern, sql.upper())
        
        for function in functions:
            if function not in self.allowed_functions:
                errors.append(f"Função não permitida: {function}")
        
        return errors
    
    def calculate_complexity(self, sql: str) -> int:
        """Calcula score de complexidade da query."""
        complexity = 0
        sql_upper = sql.upper()
        
        # Joins aumentam complexidade
        complexity += sql_upper.count("JOIN") * 2
        
        # Subqueries aumentam complexidade
        complexity += sql_upper.count("SELECT") - 1  # -1 para o SELECT principal
        
        # Funções agregadas
        complexity += len(re.findall(r'\b(COUNT|SUM|AVG|MAX|MIN)\b', sql_upper))
        
        # Condições WHERE
        complexity += sql_upper.count("WHERE")
        complexity += sql_upper.count("AND")
        complexity += sql_upper.count("OR")
        
        # ORDER BY e GROUP BY
        complexity += sql_upper.count("ORDER BY")
        complexity += sql_upper.count("GROUP BY")
        
        return complexity
    
    def _extract_tables(self, parsed_sql) -> Set[str]:
        """Extrai nomes de tabelas do SQL parseado."""
        tables = set()
        
        def extract_from_token(token):
            if hasattr(token, 'tokens'):
                for subtoken in token.tokens:
                    extract_from_token(subtoken)
            elif token.ttype is None and hasattr(token, 'value'):
                # Pode ser nome de tabela
                if token.value.lower() not in ['select', 'from', 'where', 'and', 'or', 'on']:
                    if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', token.value):
                        tables.add(token.value.lower())
        
        extract_from_token(parsed_sql)
        
        # Filtrar apenas tabelas conhecidas
        known_tables = set(self.database_schema.keys())
        return tables.intersection(known_tables)
    
    def _extract_columns(self, parsed_sql) -> List[Tuple[str, str]]:
        """Extrai pares (tabela, coluna) do SQL parseado."""
        columns = []
        
        # Esta é uma implementação simplificada
        # Em um ambiente de produção, seria necessário um parser mais sofisticado
        sql_str = str(parsed_sql)
        
        # Procurar por padrões table.column
        table_column_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\.\s*([a-zA-Z_][a-zA-Z0-9_]*)\b'
        matches = re.findall(table_column_pattern, sql_str)
        
        for table, column in matches:
            columns.append((table.lower(), column.lower()))
        
        return columns


class QueryProcessor:
    """
    Processador principal de queries em linguagem natural.
    
    Responsabilidades:
    - Análise de intenção de consultas
    - Identificação de entidades e filtros
    - Geração de SQL seguro e validado
    - Sanitização e validação avançada de queries
    - Mapeamento de linguagem natural para estrutura de dados
    """
    
    def __init__(self):
        """Inicializa o processador de queries."""
        self.settings = get_settings()
        
        # Inicializar componentes de validação
        self.sanitizer = SQLSanitizer()
        self.structure_validator = SQLStructureValidator()
        
        # Padrões de reconhecimento
        self._load_patterns()
        
        # Métricas
        self.queries_processed = 0
        self.successful_queries = 0
        self.failed_queries = 0
        self.validation_failures = 0
        
        logger.info("QueryProcessor inicializado com validação avançada")
    
    def _load_patterns(self) -> None:
        """Carrega padrões de reconhecimento de linguagem natural."""
        
        # Padrões para tipos de equipamento
        self.equipment_patterns = {
            "transformador": ["transformador", "trafo", "transformer"],
            "gerador": ["gerador", "generator"],
            "disjuntor": ["disjuntor", "breaker"],
            "cabo": ["cabo", "cable"],
            "subestacao": ["subestação", "subestacao", "substation"],
            "linha": ["linha", "line", "lt", "mt", "at"],
        }
        
        # Padrões para status de equipamento
        self.status_patterns = {
            "operacional": ["operacional", "funcionando", "ativo", "ok", "normal"],
            "manutencao": ["manutenção", "manutencao", "maintenance", "preventiva", "corretiva"],
            "falha": ["falha", "defeito", "problema", "fault", "failure", "erro"],
            "desligado": ["desligado", "inativo", "off", "parado"],
        }
        
        # Padrões para intenções
        self.intent_patterns = {
            QueryIntent.LIST: [
                "liste", "mostre", "quais", "show", "list", "exiba",
                "apresente", "relacione"
            ],
            QueryIntent.COUNT: [
                "quantos", "quantidade", "número", "count", "total de",
                "soma", "somar"
            ],
            QueryIntent.SEARCH: [
                "encontre", "busque", "procure", "search", "find",
                "localizar", "identificar"
            ],
            QueryIntent.AGGREGATE: [
                "média", "mediana", "máximo", "mínimo", "total",
                "average", "mean", "max", "min", "sum"
            ],
            QueryIntent.COMPARE: [
                "compare", "comparar", "diferença", "versus", "vs",
                "maior", "menor", "melhor", "pior"
            ],
            QueryIntent.FILTER: [
                "filtrar", "filter", "apenas", "somente", "onde",
                "quando", "com", "sem"
            ],
            QueryIntent.REPORT: [
                "relatório", "report", "resumo", "dashboard",
                "análise", "overview"
            ]
        }
        
        # Padrões temporais
        self.temporal_patterns = {
            "hoje": "CURRENT_DATE",
            "ontem": "CURRENT_DATE - INTERVAL '1 day'",
            "semana": "CURRENT_DATE - INTERVAL '7 days'",
            "mês": "CURRENT_DATE - INTERVAL '30 days'",
            "ano": "CURRENT_DATE - INTERVAL '365 days'",
            "último": "CURRENT_DATE - INTERVAL '30 days'",
            "últimos": "CURRENT_DATE - INTERVAL '30 days'",
        }
        
        # Padrões de custo
        self.cost_patterns = [
            "custo", "cost", "valor", "preço", "price", "gasto",
            "orçamento", "budget"
        ]
        
        # Campos válidos por tabela (para compatibilidade)
        self.valid_fields = {
            "equipment": [
                "id", "name", "type", "status", "location", "manufacturer",
                "model", "installation_date", "last_maintenance"
            ],
            "maintenance_orders": [
                "id", "equipment_id", "type", "status", "scheduled_date",
                "completion_date", "cost", "description", "technician"
            ],
            "failures": [
                "id", "equipment_id", "failure_date", "description",
                "severity", "resolution_time", "cost"
            ]
        }
    
    def analyze_query(self, query: str) -> QueryAnalysis:
        """
        Analisa uma query em linguagem natural.
        
        Args:
            query: Consulta em linguagem natural
            
        Returns:
            QueryAnalysis: Resultado da análise
            
        Raises:
            ValidationError: Se query inválida
        """
        try:
            self.queries_processed += 1
            
            # Validar e sanitizar entrada
            if not query or not query.strip():
                raise ValidationError("Query não pode estar vazia")
            
            # Sanitizar entrada do usuário
            sanitized_input = self.sanitize_user_input(query)
            query = sanitized_input.strip().lower()
            
            # 1. Identificar tipo de consulta
            query_type = self._identify_query_type(query)
            
            # 2. Identificar intenção
            intent = self._identify_intent(query)
            
            # 3. Extrair entidades
            entities = self._extract_entities(query)
            
            # 4. Extrair filtros
            filters = self._extract_filters(query, entities)
            
            # 5. Gerar SQL
            sql_query = self._generate_sql(query_type, intent, entities, filters)
            
            # 6. Calcular confiança
            confidence = self._calculate_confidence(query, query_type, intent, entities)
            
            # 7. Gerar explicação
            explanation = self._generate_explanation(query_type, intent, entities, filters)
            
            self.successful_queries += 1
            
            logger.info("Query analisada com sucesso", extra={
                "original_query": query[:50],
                "query_type": query_type.value,
                "intent": intent.value,
                "confidence": confidence
            })
            
            return QueryAnalysis(
                original_query=query,
                query_type=query_type,
                intent=intent,
                entities=entities,
                filters=filters,
                sql_query=sql_query,
                confidence=confidence,
                explanation=explanation
            )
            
        except Exception as e:
            self.failed_queries += 1
            logger.error(f"Erro ao analisar query: {str(e)}", extra={
                "query": query[:50] if query else "empty"
            })
            
            if isinstance(e, ValidationError):
                raise e
            else:
                raise DataProcessingError(f"Erro no processamento da query: {str(e)}")
    
    def _identify_query_type(self, query: str) -> QueryType:
        """Identifica o tipo principal da consulta."""
        
        # Verificar padrões de equipamento
        for equipment_type, patterns in self.equipment_patterns.items():
            if any(pattern in query for pattern in patterns):
                return QueryType.EQUIPMENT_STATUS
        
        # Verificar padrões de manutenção
        if any(word in query for word in ["manutenção", "manutencao", "maintenance", "preventiva", "corretiva"]):
            return QueryType.MAINTENANCE_SCHEDULE
        
        # Verificar padrões de falha
        if any(word in query for word in ["falha", "defeito", "problema", "fault", "failure"]):
            return QueryType.FAILURE_ANALYSIS
        
        # Verificar padrões de custo
        if any(pattern in query for pattern in self.cost_patterns):
            return QueryType.COST_ANALYSIS
        
        # Verificar padrões temporais (histórico)
        if any(word in query for word in ["histórico", "historico", "history", "passado", "anterior"]):
            return QueryType.HISTORICAL_DATA
        
        # Default para busca geral
        return QueryType.GENERAL_SEARCH
    
    def _identify_intent(self, query: str) -> QueryIntent:
        """Identifica a intenção da consulta."""
        
        for intent, patterns in self.intent_patterns.items():
            if any(pattern in query for pattern in patterns):
                return intent
        
        return QueryIntent.UNKNOWN
    
    def _extract_entities(self, query: str) -> Dict[str, Any]:
        """Extrai entidades da consulta."""
        entities = {}
        
        # Extrair tipos de equipamento
        for equipment_type, patterns in self.equipment_patterns.items():
            if any(pattern in query for pattern in patterns):
                entities["equipment_type"] = equipment_type
                break
        
        # Extrair status
        for status, patterns in self.status_patterns.items():
            if any(pattern in query for pattern in patterns):
                entities["status"] = status
                break
        
        # Extrair IDs específicos (T001, GER-123, etc.)
        id_patterns = re.findall(r'\b[A-Z]+[-_]?\d+\b', query.upper())
        if id_patterns:
            entities["equipment_ids"] = id_patterns
        
        # Extrair datas e períodos temporais
        temporal_entities = {}
        for pattern, sql_date in self.temporal_patterns.items():
            if pattern in query:
                temporal_entities[pattern] = sql_date
        
        if temporal_entities:
            entities["temporal"] = temporal_entities
        
        # Extrair valores numéricos
        numbers = re.findall(r'\b\d+(?:\.\d+)?\b', query)
        if numbers:
            entities["numeric_values"] = [float(n) for n in numbers]
        
        return entities
    
    def _extract_filters(self, query: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Extrai filtros específicos da consulta."""
        filters = {}
        
        # Filtros por localização
        location_keywords = ["local", "localização", "location", "onde", "em"]
        if any(keyword in query for keyword in location_keywords):
            # Tentar extrair nomes de locais
            location_match = re.search(r'(?:em|local|localização)\s+([a-zA-Z\s]+)', query)
            if location_match:
                filters["location"] = location_match.group(1).strip()
        
        # Filtros por data
        if "temporal" in entities:
            filters["date_range"] = entities["temporal"]
        
        # Filtros por valor/custo
        if any(pattern in query for pattern in self.cost_patterns):
            # Procurar por comparações de valor
            cost_comparisons = re.findall(r'(maior|menor|acima|abaixo|superior|inferior)\s+(?:de\s+)?(\d+(?:\.\d+)?)', query)
            if cost_comparisons:
                filters["cost_comparison"] = cost_comparisons
        
        # Filtros por prioridade/urgência
        if any(word in query for word in ["urgente", "urgent", "prioritário", "crítico", "critical"]):
            filters["priority"] = "high"
        
        return filters
    
    def _generate_sql(
        self, 
        query_type: QueryType, 
        intent: QueryIntent, 
        entities: Dict[str, Any], 
        filters: Dict[str, Any]
    ) -> str:
        """Gera SQL baseado na análise da query."""
        
        # Selecionar tabela base
        base_table = self._get_base_table(query_type)
        
        # Construir SELECT
        select_clause = self._build_select_clause(intent, entities, query_type)
        
        # Construir FROM
        from_clause = f"FROM {base_table}"
        
        # Construir JOINs se necessário
        join_clause = self._build_join_clause(query_type, entities)
        
        # Construir WHERE
        where_clause = self._build_where_clause(entities, filters)
        
        # Construir ORDER BY
        order_clause = self._build_order_clause(intent, query_type)
        
        # Construir LIMIT
        limit_clause = self._build_limit_clause(intent)
        
        # Montar query final
        sql_parts = [
            select_clause,
            from_clause,
            join_clause,
            where_clause,
            order_clause,
            limit_clause
        ]
        
        sql_query = " ".join(part for part in sql_parts if part)
        
        # Validar SQL gerado
        self._validate_sql(sql_query)
        
        return sql_query
    
    def _get_base_table(self, query_type: QueryType) -> str:
        """Retorna tabela base para o tipo de consulta."""
        table_mapping = {
            QueryType.EQUIPMENT_STATUS: "equipment",
            QueryType.MAINTENANCE_SCHEDULE: "maintenance_orders",
            QueryType.FAILURE_ANALYSIS: "failures",
            QueryType.COST_ANALYSIS: "maintenance_orders",
            QueryType.HISTORICAL_DATA: "maintenance_orders",
            QueryType.GENERAL_SEARCH: "equipment"
        }
        
        return table_mapping.get(query_type, "equipment")
    
    def _build_select_clause(self, intent: QueryIntent, entities: Dict[str, Any], query_type: QueryType) -> str:
        """Constrói cláusula SELECT."""
        
        if intent == QueryIntent.COUNT:
            return "SELECT COUNT(*) as total"
        
        elif intent == QueryIntent.AGGREGATE:
            if "cost" in str(entities).lower():
                return "SELECT SUM(cost) as total_cost, AVG(cost) as avg_cost, COUNT(*) as count"
            else:
                return "SELECT COUNT(*) as count"
        
        elif query_type == QueryType.EQUIPMENT_STATUS:
            return "SELECT id, name, type, status, location, last_maintenance"
        
        elif query_type == QueryType.MAINTENANCE_SCHEDULE:
            return "SELECT id, equipment_id, type, status, scheduled_date, cost"
        
        elif query_type == QueryType.FAILURE_ANALYSIS:
            return "SELECT id, equipment_id, failure_date, description, severity"
        
        else:
            return "SELECT *"
    
    def _build_join_clause(self, query_type: QueryType, entities: Dict[str, Any]) -> str:
        """Constrói cláusulas JOIN se necessárias."""
        
        if query_type == QueryType.MAINTENANCE_SCHEDULE:
            return "LEFT JOIN equipment e ON maintenance_orders.equipment_id = e.id"
        
        elif query_type == QueryType.FAILURE_ANALYSIS:
            return "LEFT JOIN equipment e ON failures.equipment_id = e.id"
        
        return ""
    
    def _build_where_clause(self, entities: Dict[str, Any], filters: Dict[str, Any]) -> str:
        """Constrói cláusula WHERE."""
        conditions = []
        
        # Filtros por tipo de equipamento
        if "equipment_type" in entities:
            equipment_type = entities["equipment_type"]
            conditions.append(f"type ILIKE '%{equipment_type}%'")
        
        # Filtros por status
        if "status" in entities:
            status = entities["status"]
            conditions.append(f"status = '{status}'")
        
        # Filtros por IDs específicos
        if "equipment_ids" in entities:
            ids = entities["equipment_ids"]
            id_list = "', '".join(ids)
            conditions.append(f"id IN ('{id_list}')")
        
        # Filtros por localização
        if "location" in filters:
            location = filters["location"]
            conditions.append(f"location ILIKE '%{location}%'")
        
        # Filtros temporais
        if "date_range" in filters:
            temporal = filters["date_range"]
            for pattern, sql_date in temporal.items():
                if "último" in pattern or "últimos" in pattern:
                    conditions.append(f"created_at >= {sql_date}")
        
        # Filtros de custo
        if "cost_comparison" in filters:
            for comparison, value in filters["cost_comparison"]:
                if comparison in ["maior", "acima", "superior"]:
                    conditions.append(f"cost > {value}")
                elif comparison in ["menor", "abaixo", "inferior"]:
                    conditions.append(f"cost < {value}")
        
        # Filtros de prioridade
        if "priority" in filters and filters["priority"] == "high":
            conditions.append("(status = 'urgent' OR priority = 'high')")
        
        if conditions:
            return "WHERE " + " AND ".join(conditions)
        
        return ""
    
    def _build_order_clause(self, intent: QueryIntent, query_type: QueryType) -> str:
        """Constrói cláusula ORDER BY."""
        
        if query_type == QueryType.MAINTENANCE_SCHEDULE:
            return "ORDER BY scheduled_date ASC"
        
        elif query_type == QueryType.FAILURE_ANALYSIS:
            return "ORDER BY failure_date DESC"
        
        elif query_type == QueryType.COST_ANALYSIS:
            return "ORDER BY cost DESC"
        
        return "ORDER BY id"
    
    def _build_limit_clause(self, intent: QueryIntent) -> str:
        """Constrói cláusula LIMIT."""
        
        if intent in [QueryIntent.COUNT, QueryIntent.AGGREGATE]:
            return ""  # Não limitar agregações
        
        return "LIMIT 50"  # Limite padrão para evitar resultados muito grandes
    
    def _validate_sql(self, sql: str) -> None:
        """Valida o SQL gerado usando sistema avançado de validação."""
        validation_result = self.validate_sql_advanced(sql)
        
        if not validation_result.is_valid:
            self.validation_failures += 1
            error_msg = "; ".join(validation_result.errors)
            logger.error("Validação SQL falhou", extra={
                "sql": sql[:100],
                "errors": validation_result.errors,
                "risk_level": validation_result.risk_level,
                "complexity": validation_result.complexity_score
            })
            raise ValidationError(f"SQL inválido: {error_msg}")
        
        # Log warnings se existirem
        if validation_result.warnings:
            logger.warning("Avisos de validação SQL", extra={
                "sql": sql[:100],
                "warnings": validation_result.warnings,
                "risk_level": validation_result.risk_level
            })
    
    def validate_sql_advanced(self, sql: str) -> ValidationResult:
        """
        Executa validação avançada completa de SQL.
        
        Args:
            sql: Query SQL para validar
            
        Returns:
            ValidationResult: Resultado detalhado da validação
        """
        errors = []
        warnings = []
        sanitized_sql = sql
        
        try:
            # 1. Sanitização básica
            sanitized_sql = self.sanitizer.sanitize_value(sql)
            
            # 2. Detectar tentativas de injection
            injection_threats = self.sanitizer.detect_injection_attempts(sanitized_sql)
            if injection_threats:
                errors.extend(injection_threats)
            
            # 3. Validar palavras-chave restritas
            keyword_issues = self.sanitizer.validate_keywords(sanitized_sql)
            if keyword_issues:
                errors.extend(keyword_issues)
            
            # 4. Validar sintaxe SQL
            syntax_errors = self.structure_validator.validate_syntax(sanitized_sql)
            if syntax_errors:
                errors.extend(syntax_errors)
            
            # 5. Validar tabelas e colunas
            schema_errors = self.structure_validator.validate_tables_and_columns(sanitized_sql)
            if schema_errors:
                errors.extend(schema_errors)
            
            # 6. Validar funções
            function_errors = self.structure_validator.validate_functions(sanitized_sql)
            if function_errors:
                errors.extend(function_errors)
            
            # 7. Calcular complexidade
            complexity = self.structure_validator.calculate_complexity(sanitized_sql)
            
            # 8. Avaliar nível de risco
            risk_level = self._calculate_risk_level(sanitized_sql, complexity, len(errors))
            
            # 9. Adicionar warnings baseados em complexidade
            if complexity > 10:
                warnings.append(f"Query de alta complexidade (score: {complexity})")
            elif complexity > 5:
                warnings.append(f"Query de complexidade moderada (score: {complexity})")
            
            # 10. Validações adicionais de segurança
            security_warnings = self._additional_security_checks(sanitized_sql)
            warnings.extend(security_warnings)
            
            # Determinar se é válida
            is_valid = len(errors) == 0
            
            if is_valid:
                logger.info("Validação SQL bem-sucedida", extra={
                    "complexity": complexity,
                    "risk_level": risk_level,
                    "warnings_count": len(warnings)
                })
            
            return ValidationResult(
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                sanitized_sql=sanitized_sql,
                risk_level=risk_level,
                complexity_score=complexity
            )
            
        except Exception as e:
            logger.error(f"Erro durante validação SQL: {str(e)}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Erro interno de validação: {str(e)}"],
                warnings=[],
                sanitized_sql=sql,
                risk_level="high",
                complexity_score=0
            )
    
    def _calculate_risk_level(self, sql: str, complexity: int, error_count: int) -> str:
        """Calcula o nível de risco da query."""
        
        # Erro = alto risco
        if error_count > 0:
            return "high"
        
        sql_upper = sql.upper()
        risk_score = 0
        
        # Fatores que aumentam o risco
        if complexity > 10:
            risk_score += 3
        elif complexity > 5:
            risk_score += 1
        
        # Presença de JOINs múltiplos
        if sql_upper.count("JOIN") > 2:
            risk_score += 2
        
        # Presença de subconsultas
        if sql_upper.count("SELECT") > 1:
            risk_score += 1
        
        # Ausência de LIMIT pode ser perigoso
        if "LIMIT" not in sql_upper and "COUNT" not in sql_upper:
            risk_score += 1
        
        # Classificar risco
        if risk_score >= 4:
            return "high"
        elif risk_score >= 2:
            return "medium"
        else:
            return "low"
    
    def _additional_security_checks(self, sql: str) -> List[str]:
        """Executa verificações adicionais de segurança."""
        warnings = []
        sql_upper = sql.upper()
        
        # Verificar queries muito abertas
        if "SELECT *" in sql_upper and "WHERE" not in sql_upper:
            warnings.append("Query muito aberta - considera adicionar filtros WHERE")
        
        # Verificar ausência de LIMIT
        if ("LIMIT" not in sql_upper and 
            "COUNT" not in sql_upper and 
            "LIMIT 50" not in sql):  # Nosso limite padrão
            warnings.append("Query sem LIMIT pode retornar muitos resultados")
        
        # Verificar operações custosas
        if sql_upper.count("JOIN") > 3:
            warnings.append("Múltiplos JOINs podem impactar performance")
        
        # Verificar funções agregadas sem GROUP BY em certas situações
        aggregates = ["SUM", "AVG", "MAX", "MIN"]
        has_aggregate = any(agg in sql_upper for agg in aggregates)
        if has_aggregate and "GROUP BY" not in sql_upper and "COUNT" not in sql_upper:
            warnings.append("Função agregada sem GROUP BY pode produzir resultados inesperados")
        
        return warnings
    
    def sanitize_user_input(self, user_input: str) -> str:
        """
        Sanitiza entrada do usuário antes do processamento.
        
        Args:
            user_input: Entrada em linguagem natural do usuário
            
        Returns:
            str: Entrada sanitizada
        """
        return self.sanitizer.sanitize_value(user_input)
    
    def get_validation_metrics(self) -> Dict[str, Any]:
        """Retorna métricas específicas de validação."""
        total_processed = self.queries_processed
        validation_success_rate = (
            (total_processed - self.validation_failures) / total_processed 
            if total_processed > 0 else 0
        )
        
        return {
            "total_queries_processed": total_processed,
            "validation_failures": self.validation_failures,
            "validation_success_rate": round(validation_success_rate, 3),
            "security_features": {
                "sql_injection_detection": True,
                "keyword_restriction": True,
                "schema_validation": True,
                "complexity_analysis": True,
                "syntax_validation": True
            }
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retorna métricas do processador."""
        success_rate = (self.successful_queries / self.queries_processed) if self.queries_processed > 0 else 0
        
        return {
            "queries_processed": self.queries_processed,
            "successful_queries": self.successful_queries,
            "failed_queries": self.failed_queries,
            "success_rate": round(success_rate, 3),
            "supported_query_types": len(QueryType),
            "supported_intents": len(QueryIntent)
        }
    
    def get_supported_patterns(self) -> Dict[str, Any]:
        """Retorna padrões suportados para documentação."""
        return {
            "equipment_types": list(self.equipment_patterns.keys()),
            "status_types": list(self.status_patterns.keys()),
            "query_types": [qt.value for qt in QueryType],
            "intents": [qi.value for qi in QueryIntent],
            "temporal_patterns": list(self.temporal_patterns.keys())
        }
    
    def _calculate_confidence(
        self, 
        query: str, 
        query_type: QueryType, 
        intent: QueryIntent, 
        entities: Dict[str, Any]
    ) -> float:
        """Calcula score de confiança da análise."""
        confidence = 0.0
        
        # Base score por tipo identificado
        if query_type != QueryType.UNKNOWN:
            confidence += 0.3
        
        # Score por intenção identificada
        if intent != QueryIntent.UNKNOWN:
            confidence += 0.2
        
        # Score por entidades encontradas
        entity_count = len(entities)
        confidence += min(0.3, entity_count * 0.1)
        
        # Score por correspondência de padrões
        pattern_matches = 0
        for patterns in self.equipment_patterns.values():
            if any(pattern in query for pattern in patterns):
                pattern_matches += 1
        
        for patterns in self.status_patterns.values():
            if any(pattern in query for pattern in patterns):
                pattern_matches += 1
        
        confidence += min(0.2, pattern_matches * 0.05)
        
        return min(1.0, confidence)
    
    def _generate_explanation(
        self, 
        query_type: QueryType, 
        intent: QueryIntent, 
        entities: Dict[str, Any], 
        filters: Dict[str, Any]
    ) -> str:
        """Gera explicação da análise realizada."""
        
        parts = []
        
        # Explicar tipo identificado
        type_explanations = {
            QueryType.EQUIPMENT_STATUS: "consulta sobre status de equipamentos",
            QueryType.MAINTENANCE_SCHEDULE: "consulta sobre programação de manutenções",
            QueryType.FAILURE_ANALYSIS: "análise de falhas e problemas",
            QueryType.COST_ANALYSIS: "análise de custos e valores",
            QueryType.HISTORICAL_DATA: "consulta de dados históricos",
            QueryType.GENERAL_SEARCH: "busca geral no sistema"
        }
        
        parts.append(f"Identificada como {type_explanations.get(query_type, 'consulta desconhecida')}")
        
        # Explicar intenção
        intent_explanations = {
            QueryIntent.LIST: "para listar resultados",
            QueryIntent.COUNT: "para contar registros",
            QueryIntent.SEARCH: "para buscar itens específicos",
            QueryIntent.AGGREGATE: "para calcular agregações",
            QueryIntent.COMPARE: "para fazer comparações",
            QueryIntent.FILTER: "para filtrar dados",
            QueryIntent.REPORT: "para gerar relatório"
        }
        
        if intent != QueryIntent.UNKNOWN:
            parts.append(f"com intenção {intent_explanations.get(intent, 'desconhecida')}")
        
        # Explicar entidades encontradas
        if entities:
            entity_parts = []
            if "equipment_type" in entities:
                entity_parts.append(f"tipo '{entities['equipment_type']}'")
            if "status" in entities:
                entity_parts.append(f"status '{entities['status']}'")
            if "equipment_ids" in entities:
                entity_parts.append(f"equipamentos {entities['equipment_ids']}")
            
            if entity_parts:
                parts.append(f"incluindo {', '.join(entity_parts)}")
        
        return ". ".join(parts) + "." 