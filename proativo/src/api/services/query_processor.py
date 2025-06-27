"""
Query Processor para o sistema PROAtivo.

Este módulo implementa processamento inteligente de consultas em linguagem natural
para dados de manutenção de equipamentos elétricos, com reconhecimento de entidades,
extração de intenções e geração de consultas SQL otimizadas.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from ..config import get_settings

logger = logging.getLogger(__name__)

# =============================================================================
# TIPOS E ENUMS
# =============================================================================

class QueryIntent(Enum):
    """Tipos de intenção identificados em consultas."""
    EQUIPMENT_SEARCH = "equipment_search"
    MAINTENANCE_HISTORY = "maintenance_history"
    LAST_MAINTENANCE = "last_maintenance"
    COUNT_EQUIPMENT = "count_equipment"
    COUNT_MAINTENANCE = "count_maintenance"
    EQUIPMENT_STATUS = "equipment_status"
    FAILURE_ANALYSIS = "failure_analysis"
    UPCOMING_MAINTENANCE = "upcoming_maintenance"
    OVERDUE_MAINTENANCE = "overdue_maintenance"
    GENERAL_QUERY = "general_query"

class QueryEntity(Enum):
    """Tipos de entidades reconhecidas."""
    EQUIPMENT_TYPE = "equipment_type"
    EQUIPMENT_ID = "equipment_id"
    EQUIPMENT_NAME = "equipment_name"
    DATE_RANGE = "date_range"
    TIME_PERIOD = "time_period"
    MAINTENANCE_TYPE = "maintenance_type"
    STATUS = "status"
    COUNT = "count"

@dataclass
class ExtractedEntity:
    """Entidade extraída da consulta."""
    type: QueryEntity
    value: str
    normalized_value: Any
    confidence: float
    start_char: int
    end_char: int

@dataclass
class QueryAnalysis:
    """Resultado da análise de uma consulta."""
    original_query: str
    intent: QueryIntent
    entities: List[ExtractedEntity]
    temporal_context: Optional[Dict[str, Any]]
    sql_query: Optional[str]
    parameters: Dict[str, Any]
    confidence_score: float
    suggestions: List[str]

# =============================================================================
# QUERY PROCESSOR PRINCIPAL
# =============================================================================

class QueryProcessor:
    """
    Processador inteligente de consultas em linguagem natural.
    
    Utiliza spaCy para processamento de NLP com padrões customizados
    para o domínio de manutenção de equipamentos elétricos.
    """
    
    def __init__(self):
        """Inicializa o processador com configurações e modelos."""
        self.settings = get_settings()
        self.nlp = None
        self._initialize_nlp()
        self._setup_patterns()
        
    def _initialize_nlp(self):
        """Inicializa spaCy com modelo em português."""
        try:
            import spacy
            from spacy.lang.pt import Portuguese
            from spacy.matcher import Matcher
            
            # Tentar carregar modelo português, senão usar base
            try:
                self.nlp = spacy.load("pt_core_news_sm")
                logger.info("Portuguese spaCy model loaded successfully")
            except OSError:
                logger.warning("Portuguese model not found, using base Portuguese")
                self.nlp = Portuguese()
                # NÃO adicionar componentes que não estão disponíveis
                # O modelo base já tem o mínimo necessário
                
            # Inicializar matcher
            self.matcher = Matcher(self.nlp.vocab)
            
            # Tentar adicionar entity_ruler apenas se for seguro
            try:
                if "entity_ruler" not in self.nlp.pipe_names:
                    self.entity_ruler = self.nlp.add_pipe("entity_ruler", name="query_entities", last=True)
                else:
                    self.entity_ruler = self.nlp.get_pipe("entity_ruler")
                logger.info("Entity ruler added successfully")
            except Exception as e:
                logger.warning(f"Could not add entity ruler: {e}. Will use regex-based extraction.")
                self.entity_ruler = None
            
        except ImportError:
            logger.error("spaCy not installed. Install with: pip install spacy")
            # Fallback para modo simples sem spaCy
            self.nlp = None
            self.matcher = None
            self.entity_ruler = None
    
    def _setup_patterns(self):
        """Configura padrões de reconhecimento de entidades e intenções."""
        if not self.nlp:
            return
        
        try:
            # =============================================================================
            # PADRÕES DE EQUIPAMENTOS
            # =============================================================================
            equipment_patterns = [
                # Tipos de equipamentos
                {"label": "EQUIPMENT_TYPE", "pattern": "transformador", "id": "transformer"},
                {"label": "EQUIPMENT_TYPE", "pattern": "transformadores", "id": "transformer"},
                {"label": "EQUIPMENT_TYPE", "pattern": "disjuntor", "id": "circuit_breaker"},
                {"label": "EQUIPMENT_TYPE", "pattern": "disjuntores", "id": "circuit_breaker"},
                {"label": "EQUIPMENT_TYPE", "pattern": "seccionadora", "id": "switch"},
                {"label": "EQUIPMENT_TYPE", "pattern": "seccionadoras", "id": "switch"},
                {"label": "EQUIPMENT_TYPE", "pattern": "motor", "id": "motor"},
                {"label": "EQUIPMENT_TYPE", "pattern": "motores", "id": "motor"},
                {"label": "EQUIPMENT_TYPE", "pattern": "gerador", "id": "generator"},
                {"label": "EQUIPMENT_TYPE", "pattern": "geradores", "id": "generator"},
                {"label": "EQUIPMENT_TYPE", "pattern": "equipamento", "id": "equipment"},
                {"label": "EQUIPMENT_TYPE", "pattern": "equipamentos", "id": "equipment"},
                
                # IDs específicos com padrões
                {"label": "EQUIPMENT_ID", "pattern": [
                    {"TEXT": {"REGEX": r"^(T|TR|EQ|DIS|SEC|MOT|GER)-?\d+$"}}
                ]},
            ]
            
            # =============================================================================
            # PADRÕES DE MANUTENÇÃO
            # =============================================================================
            maintenance_patterns = [
                {"label": "MAINTENANCE_TYPE", "pattern": "preventiva", "id": "preventive"},
                {"label": "MAINTENANCE_TYPE", "pattern": "corretiva", "id": "corrective"},
                {"label": "MAINTENANCE_TYPE", "pattern": "preditiva", "id": "predictive"},
                {"label": "MAINTENANCE_TYPE", "pattern": "emergencial", "id": "emergency"},
                {"label": "MAINTENANCE_TYPE", "pattern": "manutenção", "id": "maintenance"},
                {"label": "MAINTENANCE_TYPE", "pattern": "manutenções", "id": "maintenance"},
                {"label": "MAINTENANCE_TYPE", "pattern": "reparo", "id": "repair"},
                {"label": "MAINTENANCE_TYPE", "pattern": "reparos", "id": "repair"},
                {"label": "MAINTENANCE_TYPE", "pattern": "inspeção", "id": "inspection"},
                {"label": "MAINTENANCE_TYPE", "pattern": "inspeções", "id": "inspection"},
            ]
            
            # =============================================================================
            # PADRÕES TEMPORAIS
            # =============================================================================
            temporal_patterns = [
                {"label": "TIME_PERIOD", "pattern": "hoje", "id": "today"},
                {"label": "TIME_PERIOD", "pattern": "ontem", "id": "yesterday"},
                {"label": "TIME_PERIOD", "pattern": "semana", "id": "week"},
                {"label": "TIME_PERIOD", "pattern": "mês", "id": "month"},
                {"label": "TIME_PERIOD", "pattern": "ano", "id": "year"},
                {"label": "TIME_PERIOD", "pattern": [{"LOWER": "último"}, {"LOWER": "mês"}], "id": "last_month"},
                {"label": "TIME_PERIOD", "pattern": [{"LOWER": "última"}, {"LOWER": "semana"}], "id": "last_week"},
                {"label": "TIME_PERIOD", "pattern": [{"LOWER": "último"}, {"LOWER": "ano"}], "id": "last_year"},
                {"label": "TIME_PERIOD", "pattern": [{"LOWER": "próximo"}, {"LOWER": "mês"}], "id": "next_month"},
                {"label": "TIME_PERIOD", "pattern": [{"LOWER": "próxima"}, {"LOWER": "semana"}], "id": "next_week"},
            ]
            
            # =============================================================================
            # PADRÕES DE STATUS
            # =============================================================================
            status_patterns = [
                {"label": "STATUS", "pattern": "crítico", "id": "critical"},
                {"label": "STATUS", "pattern": "crítica", "id": "critical"},
                {"label": "STATUS", "pattern": "ativo", "id": "active"},
                {"label": "STATUS", "pattern": "ativa", "id": "active"},
                {"label": "STATUS", "pattern": "inativo", "id": "inactive"},
                {"label": "STATUS", "pattern": "inativa", "id": "inactive"},
                {"label": "STATUS", "pattern": "operacional", "id": "operational"},
                {"label": "STATUS", "pattern": "fora de serviço", "id": "out_of_service"},
                {"label": "STATUS", "pattern": "em manutenção", "id": "under_maintenance"},
            ]
            
            # Tentar adicionar padrões ao entity ruler
            all_patterns = equipment_patterns + maintenance_patterns + temporal_patterns + status_patterns
            
            # Adicionar padrões com tratamento de erro
            try:
                self.entity_ruler.add_patterns(all_patterns)
                logger.info("Entity patterns added successfully")
            except Exception as e:
                logger.warning(f"Could not add entity patterns: {e}. Using basic matching instead.")
                self.entity_ruler = None
            
            # =============================================================================
            # PADRÕES DE INTENÇÃO COM MATCHER
            # =============================================================================
            
            if self.matcher:
                try:
                    # Último/Mais recente
                    last_patterns = [
                        [{"LOWER": {"IN": ["último", "última", "mais", "recente"]}},
                         {"LOWER": {"IN": ["equipamento", "manutenção", "reparo", "inspeção"]}}],
                        [{"LOWER": "quando"}, {"LOWER": "foi"}, {"LOWER": {"IN": ["a", "o"]}}, 
                         {"LOWER": {"IN": ["última", "último"]}}],
                    ]
                    
                    # Contagem
                    count_patterns = [
                        [{"LOWER": {"IN": ["quantos", "quantas"]}}, 
                         {"LOWER": {"IN": ["equipamentos", "manutenções", "reparos"]}}],
                        [{"LOWER": "número"}, {"LOWER": "de"}, 
                         {"LOWER": {"IN": ["equipamentos", "manutenções"]}}],
                    ]
                    
                    # Status/Estado
                    status_patterns_matcher = [
                        [{"LOWER": {"IN": ["status", "estado", "situação"]}}, 
                         {"LOWER": {"IN": ["do", "da", "dos", "das"]}}],
                        [{"LOWER": {"IN": ["como", "qual"]}}, {"LOWER": "está"}, 
                         {"LOWER": {"IN": ["o", "a"]}}],
                    ]
                    
                    # Adicionar padrões ao matcher
                    self.matcher.add("LAST_MAINTENANCE", last_patterns)
                    self.matcher.add("COUNT_QUERY", count_patterns)
                    self.matcher.add("STATUS_QUERY", status_patterns_matcher)
                    
                    logger.info("Matcher patterns added successfully")
                except Exception as e:
                    logger.warning(f"Could not add matcher patterns: {e}. Using fallback matching.")
                    self.matcher = None
            
            logger.info("Query patterns configuration completed")
            
        except Exception as e:
            logger.error(f"Error setting up patterns: {e}. Will use simple fallback processing.")
            # Se tudo falhar, desabilitar componentes avançados
            self.entity_ruler = None
            self.matcher = None
    
    async def process_query(self, query: str) -> QueryAnalysis:
        """
        Processa uma consulta em linguagem natural.
        
        Args:
            query: Consulta do usuário em português
            
        Returns:
            QueryAnalysis: Análise completa da consulta
        """
        logger.debug(f"Processing query: {query}")
        
        if not self.nlp:
            # Fallback simples sem spaCy
            return self._simple_fallback_processing(query)
        
        # Processar com spaCy
        doc = self.nlp(query.lower())
        
        # Extrair entidades
        entities = self._extract_entities(doc, query)
        
        # Identificar intenção
        intent = self._identify_intent(doc, entities)
        
        # Extrair contexto temporal
        temporal_context = self._extract_temporal_context(doc, entities)
        
        # Gerar SQL query
        sql_query, parameters = self._generate_sql_query(intent, entities, temporal_context)
        
        # Calcular confiança
        confidence = self._calculate_confidence(intent, entities, sql_query)
        
        # Gerar sugestões
        suggestions = self._generate_suggestions(intent, entities)
        
        analysis = QueryAnalysis(
            original_query=query,
            intent=intent,
            entities=entities,
            temporal_context=temporal_context,
            sql_query=sql_query,
            parameters=parameters,
            confidence_score=confidence,
            suggestions=suggestions
        )
        
        logger.info(f"Query processed: intent={intent.value}, entities={len(entities)}, confidence={confidence:.2f}")
        return analysis
    
    def _simple_fallback_processing(self, query: str) -> QueryAnalysis:
        """Processamento simples quando spaCy não está disponível."""
        query_lower = query.lower()
        
        # Identificação simples de intenção baseada em palavras-chave
        if any(word in query_lower for word in ["último", "última", "ultimo", "ultima", "recente", "mais recent"]):
            intent = QueryIntent.LAST_MAINTENANCE
        elif any(word in query_lower for word in ["quantos", "quantas", "número"]):
            if "equipamento" in query_lower:
                intent = QueryIntent.COUNT_EQUIPMENT
            else:
                intent = QueryIntent.COUNT_MAINTENANCE
        elif any(word in query_lower for word in ["status", "estado", "situação"]):
            intent = QueryIntent.EQUIPMENT_STATUS
        else:
            intent = QueryIntent.GENERAL_QUERY
        
        # Entidades simples usando regex
        entities = self._extract_numbers_and_dates(query)
        
        # SQL básico
        sql_query, parameters = self._generate_sql_query(intent, entities, None)
        
        return QueryAnalysis(
            original_query=query,
            intent=intent,
            entities=entities,
            temporal_context=None,
            sql_query=sql_query,
            parameters=parameters,
            confidence_score=0.6,  # Confiança média para fallback
            suggestions=self._generate_suggestions(intent, entities)
        )
    
    def _extract_entities(self, doc, original_query: str) -> List[ExtractedEntity]:
        """Extrai entidades reconhecidas do documento processado."""
        entities = []
        
        # Extrair entidades reconhecidas pelo spaCy apenas se entity_ruler estiver disponível
        if self.entity_ruler:
            try:
                for ent in doc.ents:
                    entity_type = self._map_spacy_to_query_entity(ent.label_)
                    if entity_type:
                        normalized_value = self._normalize_entity_value(ent.text, entity_type, ent.ent_id_)
                        
                        entity = ExtractedEntity(
                            type=entity_type,
                            value=ent.text,
                            normalized_value=normalized_value,
                            confidence=0.9,  # Alta confiança para entidades reconhecidas por padrões
                            start_char=ent.start_char,
                            end_char=ent.end_char
                        )
                        entities.append(entity)
            except Exception as e:
                logger.debug(f"Error in entity extraction: {e}")
        
        # Sempre usar extração básica com regex (fallback)
        entities.extend(self._extract_numbers_and_dates(original_query))
        
        # Extração básica de entidades usando regex (sempre disponível)
        entities.extend(self._extract_basic_entities_regex(original_query))
        
        return entities
    
    def _map_spacy_to_query_entity(self, spacy_label: str) -> Optional[QueryEntity]:
        """Mapeia labels do spaCy para tipos de entidade do query."""
        mapping = {
            "EQUIPMENT_TYPE": QueryEntity.EQUIPMENT_TYPE,
            "EQUIPMENT_ID": QueryEntity.EQUIPMENT_ID,
            "EQUIPMENT_NAME": QueryEntity.EQUIPMENT_NAME,
            "MAINTENANCE_TYPE": QueryEntity.MAINTENANCE_TYPE,
            "TIME_PERIOD": QueryEntity.TIME_PERIOD,
            "STATUS": QueryEntity.STATUS,
        }
        return mapping.get(spacy_label)
    
    def _normalize_entity_value(self, text: str, entity_type: QueryEntity, entity_id: Optional[str] = None) -> Any:
        """Normaliza valor da entidade para uso em consultas."""
        if entity_id:
            return entity_id
            
        if entity_type == QueryEntity.EQUIPMENT_TYPE:
            type_mapping = {
                "transformador": "transformer",
                "transformadores": "transformer",
                "disjuntor": "circuit_breaker",
                "disjuntores": "circuit_breaker",
                "seccionadora": "switch",
                "seccionadoras": "switch",
                "motor": "motor",
                "motores": "motor",
                "gerador": "generator",
                "geradores": "generator",
                # Removido "equipamento": "equipment" para evitar filtros incorretos
            }
            return type_mapping.get(text.lower(), text.lower())
        
        elif entity_type == QueryEntity.MAINTENANCE_TYPE:
            maintenance_mapping = {
                "preventiva": "preventive",
                "corretiva": "corrective",
                "preditiva": "predictive",
                "emergencial": "emergency",
                "manutenção": "maintenance",
                "manutenções": "maintenance",
                "reparo": "repair",
                "reparos": "repair",
                "inspeção": "inspection",
                "inspeções": "inspection",
            }
            return maintenance_mapping.get(text.lower(), text.lower())
        
        elif entity_type == QueryEntity.TIME_PERIOD:
            return self._normalize_time_period(text)
        
        return text.lower()
    
    def _normalize_time_period(self, text: str) -> Dict[str, Any]:
        """Normaliza períodos temporais para datas específicas."""
        today = datetime.now()
        
        time_mapping = {
            "hoje": {"start": today.replace(hour=0, minute=0, second=0, microsecond=0),
                    "end": today.replace(hour=23, minute=59, second=59, microsecond=999999)},
            "ontem": {"start": (today - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0),
                     "end": (today - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)},
            "semana": {"start": today - timedelta(days=7), "end": today},
            "mês": {"start": today - timedelta(days=30), "end": today},
            "ano": {"start": today - timedelta(days=365), "end": today},
            "last_month": {"start": today - timedelta(days=60), "end": today - timedelta(days=30)},
            "last_week": {"start": today - timedelta(days=14), "end": today - timedelta(days=7)},
            "last_year": {"start": today - timedelta(days=730), "end": today - timedelta(days=365)},
            "next_month": {"start": today + timedelta(days=30), "end": today + timedelta(days=60)},
            "next_week": {"start": today + timedelta(days=7), "end": today + timedelta(days=14)},
        }
        
        return time_mapping.get(text.lower(), {
            "start": today - timedelta(days=30), 
            "end": today,
            "raw_text": text
        })
    
    def _extract_numbers_and_dates(self, query: str) -> List[ExtractedEntity]:
        """Extrai números e datas usando regex."""
        entities = []
        
        # Detectar números
        number_pattern = r'\b(\d+)\b'
        for match in re.finditer(number_pattern, query):
            entities.append(ExtractedEntity(
                type=QueryEntity.COUNT,
                value=match.group(1),
                normalized_value=int(match.group(1)),
                confidence=0.8,
                start_char=match.start(),
                end_char=match.end()
            ))
        
        # Detectar datas (formato brasileiro)
        date_pattern = r'\b(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})\b'
        for match in re.finditer(date_pattern, query):
            try:
                day, month, year = match.groups()
                if len(year) == 2:
                    year = "20" + year
                
                date_obj = datetime(int(year), int(month), int(day))
                entities.append(ExtractedEntity(
                    type=QueryEntity.DATE_RANGE,
                    value=match.group(0),
                    normalized_value=date_obj,
                    confidence=0.9,
                    start_char=match.start(),
                    end_char=match.end()
                ))
            except ValueError:
                # Data inválida, ignorar
                pass
        
        return entities
    
    def _extract_basic_entities_regex(self, query: str) -> List[ExtractedEntity]:
        """Extrai entidades básicas usando regex (fallback quando spaCy não está disponível)."""
        entities = []
        query_lower = query.lower()
        
        # Detectar tipos de equipamentos específicos (não incluir "equipamento" genérico)
        equipment_patterns = {
            r'\btransformador[es]?\b': 'transformer',
            r'\bdisjuntor[es]?\b': 'circuit_breaker', 
            r'\bseccionadora[s]?\b': 'switch',
            r'\bmotor[es]?\b': 'motor',
            r'\bgerador[es]?\b': 'generator',
        }
        
        for pattern, eq_type in equipment_patterns.items():
            for match in re.finditer(pattern, query_lower):
                entities.append(ExtractedEntity(
                    type=QueryEntity.EQUIPMENT_TYPE,
                    value=match.group(0),
                    normalized_value=eq_type,
                    confidence=0.8,
                    start_char=match.start(),
                    end_char=match.end()
                ))
        
        # Detectar IDs de equipamentos
        equipment_id_pattern = r'\b(T|TR|EQ|DIS|SEC|MOT|GER)-?\d+\b'
        for match in re.finditer(equipment_id_pattern, query, re.IGNORECASE):
            entities.append(ExtractedEntity(
                type=QueryEntity.EQUIPMENT_ID,
                value=match.group(0),
                normalized_value=match.group(0).upper(),
                confidence=0.9,
                start_char=match.start(),
                end_char=match.end()
            ))
        
        # Detectar tipos de manutenção
        maintenance_patterns = {
            r'\bmanutenção\b': 'maintenance',
            r'\bmanutenções\b': 'maintenance',
            r'\bpreventiva\b': 'preventive',
            r'\bcorretiva\b': 'corrective',
            r'\breparo\b': 'repair',
            r'\breparos\b': 'repair',
            r'\binspeção\b': 'inspection',
        }
        
        for pattern, maint_type in maintenance_patterns.items():
            for match in re.finditer(pattern, query_lower):
                entities.append(ExtractedEntity(
                    type=QueryEntity.MAINTENANCE_TYPE,
                    value=match.group(0),
                    normalized_value=maint_type,
                    confidence=0.8,
                    start_char=match.start(),
                    end_char=match.end()
                ))
        
        return entities
    
    def _identify_intent(self, doc, entities: List[ExtractedEntity]) -> QueryIntent:
        """Identifica a intenção da consulta baseada em padrões e entidades."""
        
        # Verificar matches do matcher apenas se disponível
        if self.matcher:
            try:
                matches = self.matcher(doc)
                
                for match_id, start, end in matches:
                    label = self.nlp.vocab.strings[match_id]
                    
                    if label == "LAST_MAINTENANCE":
                        return QueryIntent.LAST_MAINTENANCE
                    elif label == "COUNT_QUERY":
                        # Determinar se é contagem de equipamentos ou manutenções
                        has_equipment = any(e.type == QueryEntity.EQUIPMENT_TYPE for e in entities)
                        has_maintenance = any(e.type == QueryEntity.MAINTENANCE_TYPE for e in entities)
                        
                        if has_equipment or "equipamento" in doc.text:
                            return QueryIntent.COUNT_EQUIPMENT
                        elif has_maintenance or any(word in doc.text for word in ["manutenção", "reparo"]):
                            return QueryIntent.COUNT_MAINTENANCE
                        else:
                            return QueryIntent.COUNT_EQUIPMENT  # Default
                    
                    elif label == "STATUS_QUERY":
                        return QueryIntent.EQUIPMENT_STATUS
            except Exception as e:
                logger.debug(f"Error in matcher processing: {e}")
        
        # Análise baseada em palavras-chave (fallback sempre disponível)
        text = doc.text.lower()
        
        # Palavras-chave para diferentes intenções
        if any(word in text for word in ["último", "última", "ultimo", "ultima", "recente", "mais recent"]):
            if any(word in text for word in ["manutenção", "manutencao", "reparo", "inspeção", "inspecao"]):
                return QueryIntent.LAST_MAINTENANCE
            else:
                return QueryIntent.MAINTENANCE_HISTORY
        
        elif any(word in text for word in ["quantos", "quantas", "número", "total"]):
            if any(word in text for word in ["equipamento", "equipamentos"]):
                return QueryIntent.COUNT_EQUIPMENT
            else:
                return QueryIntent.COUNT_MAINTENANCE
        
        elif any(word in text for word in ["status", "estado", "situação", "como está"]):
            return QueryIntent.EQUIPMENT_STATUS
        
        elif any(word in text for word in ["falha", "problema", "erro", "defeito"]):
            return QueryIntent.FAILURE_ANALYSIS
        
        elif any(word in text for word in ["próxim", "programad", "agendar"]):
            return QueryIntent.UPCOMING_MAINTENANCE
        
        elif any(word in text for word in ["atras", "vencid", "pendente"]):
            return QueryIntent.OVERDUE_MAINTENANCE
        
        elif any(word in text for word in ["histórico", "history", "passad"]):
            return QueryIntent.MAINTENANCE_HISTORY
        
        elif any(e.type == QueryEntity.EQUIPMENT_TYPE for e in entities):
            return QueryIntent.EQUIPMENT_SEARCH
        
        else:
            return QueryIntent.GENERAL_QUERY
    
    def _extract_temporal_context(self, doc, entities: List[ExtractedEntity]) -> Optional[Dict[str, Any]]:
        """Extrai contexto temporal da consulta."""
        temporal_entities = [e for e in entities if e.type in [QueryEntity.TIME_PERIOD, QueryEntity.DATE_RANGE]]
        
        if not temporal_entities:
            return None
        
        # Usar a primeira entidade temporal encontrada
        temporal_entity = temporal_entities[0]
        
        if temporal_entity.type == QueryEntity.TIME_PERIOD:
            return {
                "type": "period",
                "period": temporal_entity.normalized_value,
                "raw_text": temporal_entity.value
            }
        elif temporal_entity.type == QueryEntity.DATE_RANGE:
            return {
                "type": "specific_date",
                "date": temporal_entity.normalized_value,
                "raw_text": temporal_entity.value
            }
        
        return None
    
    def _generate_sql_query(self, intent: QueryIntent, entities: List[ExtractedEntity], 
                          temporal_context: Optional[Dict[str, Any]]) -> Tuple[Optional[str], Dict[str, Any]]:
        """Gera consulta SQL baseada na intenção e entidades."""
        
        parameters = {}
        
        # Coletar filtros das entidades - EXCLUIR "equipamento" genérico
        all_equipment_entities = [e for e in entities if e.type == QueryEntity.EQUIPMENT_TYPE]
        equipment_types = [
            e.normalized_value for e in entities 
            if e.type == QueryEntity.EQUIPMENT_TYPE 
            and e.normalized_value not in ["equipment", "equipamento", "equipamentos"]
        ]
        equipment_ids = [e.normalized_value for e in entities if e.type == QueryEntity.EQUIPMENT_ID]
        maintenance_types = [e.normalized_value for e in entities if e.type == QueryEntity.MAINTENANCE_TYPE]
        
        # Debug logging
        logger.info(f"SQL Generation Debug - Intent: {intent.value}")
        logger.info(f"All entities: {[(e.type.value, e.value, e.normalized_value) for e in entities]}")
        logger.info(f"All equipment entities found: {[(e.value, e.normalized_value) for e in all_equipment_entities]}")
        logger.info(f"Equipment types after filtering: {equipment_types}")
        logger.info(f"Equipment IDs: {equipment_ids}")
        logger.info(f"Maintenance types: {maintenance_types}")
        
        if intent == QueryIntent.LAST_MAINTENANCE:
            sql = """
            SELECT e.name, e.equipment_type, 
                   COALESCE(m.completion_date, m.start_date, m.scheduled_date) as maintenance_date,
                   m.maintenance_type, m.status, m.title
            FROM equipments e
            JOIN maintenances m ON e.id = m.equipment_id
            WHERE m.completion_date IS NOT NULL
            """
            
            # Para queries genéricas sobre "equipamento", não aplicar filtros de tipo
            # Apenas aplicar filtros se forem tipos específicos ou IDs
            if equipment_types:
                sql += " AND e.equipment_type = ANY(%(equipment_types)s)"
                parameters['equipment_types'] = equipment_types
                logger.info(f"LAST_MAINTENANCE query with equipment_types filter: {equipment_types}")
            
            if equipment_ids:
                sql += " AND e.id = ANY(%(equipment_ids)s)"
                parameters['equipment_ids'] = equipment_ids
                logger.info(f"LAST_MAINTENANCE query with equipment_ids filter: {equipment_ids}")
            
            # Log para debug quando não há filtros (comportamento esperado para "equipamento" genérico)
            if not equipment_types and not equipment_ids:
                logger.info("LAST_MAINTENANCE query without filters - querying all equipment types")
            
            sql += " ORDER BY m.completion_date DESC LIMIT 1"
        
        elif intent == QueryIntent.COUNT_EQUIPMENT:
            sql = "SELECT COUNT(*) as total FROM equipments WHERE 1=1"
            
            if equipment_types:
                sql += " AND equipment_type = ANY(%(equipment_types)s)"
                parameters['equipment_types'] = equipment_types
        
        elif intent == QueryIntent.COUNT_MAINTENANCE:
            sql = "SELECT COUNT(*) as total FROM maintenances WHERE 1=1"
            
            if maintenance_types:
                sql += " AND maintenance_type = ANY(%(maintenance_types)s)"
                parameters['maintenance_types'] = maintenance_types
            
            if temporal_context and temporal_context['type'] == 'period':
                period = temporal_context['period']
                if 'start' in period and 'end' in period:
                    sql += " AND COALESCE(m.completion_date, m.start_date, m.scheduled_date) BETWEEN %(start_date)s AND %(end_date)s"
                    parameters['start_date'] = period['start']
                    parameters['end_date'] = period['end']
        
        elif intent == QueryIntent.EQUIPMENT_STATUS:
            sql = """
            SELECT e.name, e.equipment_type, e.status, e.criticality,
                   COALESCE(last_maint.last_maintenance, 'Nunca') as last_maintenance
            FROM equipments e
            LEFT JOIN (
                SELECT equipment_id, MAX(COALESCE(completion_date, start_date, scheduled_date)) as last_maintenance
                FROM maintenances 
                WHERE completion_date IS NOT NULL
                GROUP BY equipment_id
            ) last_maint ON e.id = last_maint.equipment_id
            WHERE 1=1
            """
            
            if equipment_types:
                sql += " AND e.equipment_type = ANY(%(equipment_types)s)"
                parameters['equipment_types'] = equipment_types
        
        elif intent == QueryIntent.MAINTENANCE_HISTORY:
            sql = """
            SELECT e.name, e.equipment_type, 
                   COALESCE(m.completion_date, m.start_date, m.scheduled_date) as maintenance_date,
                   m.maintenance_type, m.description, m.status
            FROM equipments e
            JOIN maintenances m ON e.id = m.equipment_id
            WHERE 1=1
            """
            
            if equipment_types:
                sql += " AND e.equipment_type = ANY(%(equipment_types)s)"
                parameters['equipment_types'] = equipment_types
            
            if temporal_context and temporal_context['type'] == 'period':
                period = temporal_context['period']
                if 'start' in period and 'end' in period:
                    sql += " AND COALESCE(m.completion_date, m.start_date, m.scheduled_date) BETWEEN %(start_date)s AND %(end_date)s"
                    parameters['start_date'] = period['start']
                    parameters['end_date'] = period['end']
            
            sql += " ORDER BY COALESCE(m.completion_date, m.start_date, m.scheduled_date) DESC"
        
        else:
            # Para outras intenções, retornar consulta genérica
            return None, parameters
        
        return sql, parameters
    
    def _calculate_confidence(self, intent: QueryIntent, entities: List[ExtractedEntity], 
                            sql_query: Optional[str]) -> float:
        """Calcula score de confiança da análise."""
        base_confidence = 0.5
        
        # Bônus por intenção identificada claramente
        if intent != QueryIntent.GENERAL_QUERY:
            base_confidence += 0.2
        
        # Bônus por entidades encontradas
        entity_bonus = min(len(entities) * 0.1, 0.3)
        base_confidence += entity_bonus
        
        # Bônus por SQL gerado
        if sql_query:
            base_confidence += 0.2
        
        # Penalização se não há entidades relevantes
        relevant_entities = [e for e in entities if e.type in [
            QueryEntity.EQUIPMENT_TYPE, QueryEntity.MAINTENANCE_TYPE, QueryEntity.TIME_PERIOD
        ]]
        if not relevant_entities and intent != QueryIntent.GENERAL_QUERY:
            base_confidence -= 0.2
        
        return min(max(base_confidence, 0.0), 1.0)
    
    def _generate_suggestions(self, intent: QueryIntent, entities: List[ExtractedEntity]) -> List[str]:
        """Gera sugestões baseadas na análise."""
        suggestions = []
        
        if intent == QueryIntent.LAST_MAINTENANCE:
            suggestions.extend([
                "Histórico completo de manutenções",
                "Próximas manutenções programadas",
                "Equipamentos com manutenção em atraso"
            ])
        
        elif intent == QueryIntent.COUNT_EQUIPMENT:
            suggestions.extend([
                "Lista detalhada dos equipamentos",
                "Equipamentos por categoria",
                "Status de cada equipamento"
            ])
        
        elif intent == QueryIntent.EQUIPMENT_STATUS:
            suggestions.extend([
                "Manutenções pendentes",
                "Equipamentos críticos",
                "Histórico de falhas"
            ])
        
        elif intent == QueryIntent.GENERAL_QUERY:
            suggestions.extend([
                "Status dos equipamentos",
                "Últimas manutenções realizadas",
                "Equipamentos que precisam de atenção",
                "Relatório de falhas recentes"
            ])
        
        else:
            suggestions.extend([
                "Resumo geral do sistema",
                "Equipamentos críticos",
                "Próximas manutenções"
            ])
        
        return suggestions[:3]  # Limitar a 3 sugestões 