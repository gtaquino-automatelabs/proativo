"""
Processador de queries que converte linguagem natural em SQL.

Este módulo implementa a análise de consultas em linguagem natural,
identificação de intenções, geração de SQL seguro e validação.
"""

import re
import json
from typing import Dict, Any, List, Optional, Tuple, Union
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


class QueryProcessor:
    """
    Processador principal de queries em linguagem natural.
    
    Responsabilidades:
    - Análise de intenção de consultas
    - Identificação de entidades e filtros
    - Geração de SQL seguro e validado
    - Sanitização e validação de queries
    - Mapeamento de linguagem natural para estrutura de dados
    """
    
    def __init__(self):
        """Inicializa o processador de queries."""
        self.settings = get_settings()
        
        # Padrões de reconhecimento
        self._load_patterns()
        
        # Métricas
        self.queries_processed = 0
        self.successful_queries = 0
        self.failed_queries = 0
        
        logger.info("QueryProcessor inicializado com sucesso")
    
    async def process_query(self, query: str) -> QueryAnalysis:
        """
        Processa uma query (wrapper para analyze_query).
        
        Args:
            query: Consulta em linguagem natural
            
        Returns:
            QueryAnalysis: Resultado da análise
        """
        return self.analyze_query(query)
    
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
        
        # Campos válidos por tabela
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
            
            # Validar entrada
            if not query or not query.strip():
                raise ValidationError("Query não pode estar vazia")
            
            query = query.strip().lower()
            
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
        """Valida o SQL gerado."""
        
        # Verificar se não há comandos perigosos
        dangerous_keywords = [
            "DROP", "DELETE", "UPDATE", "INSERT", "CREATE", "ALTER",
            "TRUNCATE", "EXEC", "EXECUTE", "SP_", "XP_"
        ]
        
        sql_upper = sql.upper()
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                raise ValidationError(f"SQL contém comando não permitido: {keyword}")
        
        # Verificar se é uma query SELECT válida
        if not sql_upper.strip().startswith("SELECT"):
            raise ValidationError("Apenas queries SELECT são permitidas")
        
        # Verificar se não há múltiplas statements
        if ";" in sql and not sql.strip().endswith(";"):
            raise ValidationError("Múltiplas statements SQL não são permitidas")
    
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