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
    # NOVAS INTENÇÕES
    PMM2_PLAN_SEARCH = "pmm2_plan_search"
    SAP_LOCATION_SEARCH = "sap_location_search"
    EQUIPMENT_BY_LOCATION = "equipment_by_location" # Para buscar equipamentos em uma localidade
    # TESTE OPERATIVO É UM TIPO ESPECÍFICO DE UPCOMING_MAINTENANCE ou PMM2_PLAN_SEARCH

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
    # NOVAS ENTIDADES
    WORK_CENTER = "work_center"
    PLAN_CODE = "plan_code"
    SAP_LOCATION_CODE = "sap_location_code"
    SAP_LOCATION_DENOMINATION = "sap_location_denomination"
    SAP_LOCATION_ABBREVIATION = "sap_location_abbreviation"
    REGION = "region"


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
                {"label": "EQUIPMENT_TYPE", "pattern": "transformador", "id": "Transformador"},
                {"label": "EQUIPMENT_TYPE", "pattern": "transformadores", "id": "Transformador"},
                {"label": "EQUIPMENT_TYPE", "pattern": "disjuntor", "id": "Disjuntor"},
                {"label": "EQUIPMENT_TYPE", "pattern": "disjuntores", "id": "Disjuntor"},
                {"label": "EQUIPMENT_TYPE", "pattern": "seccionadora", "id": "Seccionadora"},
                {"label": "EQUIPMENT_TYPE", "pattern": "seccionadoras", "id": "Seccionadora"},
                {"label": "EQUIPMENT_TYPE", "pattern": "motor", "id": "Motor"},
                {"label": "EQUIPMENT_TYPE", "pattern": "motores", "id": "Motor"},
                {"label": "EQUIPMENT_TYPE", "pattern": "gerador", "id": "Gerador"},
                {"label": "EQUIPMENT_TYPE", "pattern": "geradores", "id": "Gerador"},
                {"label": "EQUIPMENT_TYPE", "pattern": "equipamento", "id": "equipment"},
                {"label": "EQUIPMENT_TYPE", "pattern": "equipamentos", "id": "equipment"},
                {"label": "EQUIPMENT_TYPE", "pattern": "para-raios", "id": "Para-raios"},
                {"label": "EQUIPMENT_TYPE", "pattern": "pararaios", "id": "Para-raios"},
                
                # IDs específicos com padrões (ex: TR-001, DJ-002, SC-003, PR-001)
                {"label": "EQUIPMENT_ID", "pattern": [
                    {"TEXT": {"REGEX": r"^(TR|DJ|SC|PR|BB|BC|AT|CF)-?\d+$"}}
                ]},
                {"label": "EQUIPMENT_ID", "pattern": [ # Ex: "o disjuntor 4k4"
                    {"LOWER": {"IN": ["disjuntor", "transformador", "equipamento", "seccionadora", "para-raios", "motor", "gerador"]}},
                    {"IS_ALPHA": True, "OP": "?"}, # Opcional "o", "a", "os"
                    {"TEXT": {"REGEX": r"^[A-Z0-9_-]+$"}} # Captura "4K4" como ID se não tiver prefixo conhecido
                ], "id": "EQUIPMENT_ID_SUFFIX"}, # Novo ID para identificar se é um sufixo de ID
            ]
            
            # =============================================================================
            # PADRÕES DE MANUTENÇÃO
            # =============================================================================
            maintenance_patterns = [
                {"label": "MAINTENANCE_TYPE", "pattern": "preventiva", "id": "Preventive"},
                {"label": "MAINTENANCE_TYPE", "pattern": "corretiva", "id": "Corrective"},
                {"label": "MAINTENANCE_TYPE", "pattern": "preditiva", "id": "Predictive"},
                {"label": "MAINTENANCE_TYPE", "pattern": "emergencial", "id": "Emergency"},
                {"label": "MAINTENANCE_TYPE", "pattern": "manutenção", "id": "Maintenance"},
                {"label": "MAINTENANCE_TYPE", "pattern": "manutenções", "id": "Maintenance"},
                {"label": "MAINTENANCE_TYPE", "pattern": "reparo", "id": "repair"},
                {"label": "MAINTENANCE_TYPE", "pattern": "reparos", "id": "repair"},
                {"label": "MAINTENANCE_TYPE", "pattern": "inspeção", "id": "inspection"},
                {"label": "MAINTENANCE_TYPE", "pattern": "inspeções", "id": "inspection"},
                {"label": "MAINTENANCE_TYPE", "pattern": "teste operativo", "id": "Operative Test"}, # Adicionado teste operativo
                {"label": "MAINTENANCE_TYPE", "pattern": "teste operatório", "id": "Operative Test"},
                {"label": "MAINTENANCE_TYPE", "pattern": "teste", "id": "Test"}, # General Test
            ]
            
            # =============================================================================
            # NOVOS PADRÕES PARA PMM_2 e SAP_LOCATION
            # =============================================================================
            pmm2_patterns = [
                {"label": "PLAN_CODE", "pattern": [{"TEXT": {"REGEX": r"^(OM|PM|PMM)-\d{4}-?\d+$"}}]}, # Ordem de Manutenção/Plano de Manutenção
                {"label": "PLAN_CODE", "pattern": [{"TEXT": {"REGEX": r"^[A-Z]{2,4}[A-Z0-9]{5,10}[A-Z0-9]{3,}$"}}]}, # Ex: TBDPDTCH001A
                {"label": "WORK_CENTER", "pattern": [{"TEXT": {"REGEX": r"^[A-Z]{2,4}[A-Z0-9]{3,5}[A-Z]$"}}]}, # Ex: TTABDPM
                {"label": "WORK_CENTER", "pattern": "centro de trabalho"},
                {"label": "PLAN_CODE", "pattern": "plano de manutenção"},
                {"label": "PLAN_CODE", "pattern": "planos de manutenção"},
                {"label": "PLAN_CODE", "pattern": "PMM_2"},
                {"label": "PLAN_CODE", "pattern": "PMM2"},
            ]

            sap_location_patterns = [
                {"label": "SAP_LOCATION_CODE", "pattern": [{"TEXT": {"REGEX": r"^[A-Z]{2}-S-\d+$"}}]}, # Ex: MT-S-72183
                {"label": "SAP_LOCATION_DENOMINATION", "pattern": "Baguari_230 KV"}, # Specific example from data
                {"label": "SAP_LOCATION_ABBREVIATION", "pattern": "UEM", "id": "UEM"},
                {"label": "SAP_LOCATION_ABBREVIATION", "pattern": "BDP", "id": "BDP"},
                {"label": "SAP_LOCATION_ABBREVIATION", "pattern": "UJG", "id": "UJG"},
                {"label": "SAP_LOCATION_ABBREVIATION", "pattern": "UNP", "id": "UNP"},
                {"label": "SAP_LOCATION_ABBREVIATION", "pattern": "SGT", "id": "SGT"},
                {"label": "SAP_LOCATION_ABBREVIATION", "pattern": "USS", "id": "USS"},
                {"label": "SAP_LOCATION_ABBREVIATION", "pattern": "UVG", "id": "UVG"},
                # Adicionar mais abreviações SAP conforme necessário
                {"label": "REGION", "pattern": [{"TEXT": {"REGEX": r"^[A-Z]{2}$"}}]}, # Ex: MT, MG
                {"label": "SAP_LOCATION_DENOMINATION", "pattern": "subestação"},
                {"label": "SAP_LOCATION_DENOMINATION", "pattern": "subestacoes"},
                {"label": "SAP_LOCATION_DENOMINATION", "pattern": "localidade"},
                {"label": "SAP_LOCATION_DENOMINATION", "pattern": "localidades"},
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
                {"label": "TIME_PERIOD", "pattern": [{"LOWER": "data"}, {"LOWER": "planejada"}], "id": "planned_date"}, # Para extrair a intenção de data planejada
                {"label": "TIME_PERIOD", "pattern": [{"LOWER": "próxima"}, {"LOWER": "data"}], "id": "next_date"},
            ]
            
            # =============================================================================
            # PADRÕES DE STATUS
            # =============================================================================
            status_patterns = [
                {"label": "STATUS", "pattern": "crítico", "id": "High"}, # Mapeia para High criticality
                {"label": "STATUS", "pattern": "crítica", "id": "High"},
                {"label": "STATUS", "pattern": "ativo", "id": "Active"},
                {"label": "STATUS", "pattern": "ativa", "id": "Active"},
                {"label": "STATUS", "pattern": "inativo", "id": "Inactive"},
                {"label": "STATUS", "pattern": "inativa", "id": "Inactive"},
                {"label": "STATUS", "pattern": "operacional", "id": "Active"},
                {"label": "STATUS", "pattern": "fora de serviço", "id": "Inactive"},
                {"label": "STATUS", "pattern": "em manutenção", "id": "Maintenance"}, # Para equipment status
                {"label": "STATUS", "pattern": "concluída", "id": "Completed"}, # Para maintenance status
                {"label": "STATUS", "pattern": "planejada", "id": "Planned"},
                {"label": "STATUS", "pattern": "em andamento", "id": "InProgress"},
            ]
            
            # Tentar adicionar padrões ao entity ruler
            all_patterns = equipment_patterns + maintenance_patterns + temporal_patterns + status_patterns + pmm2_patterns + sap_location_patterns
            
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
                         {"LOWER": {"IN": ["equipamento", "manutenção", "reparo", "inspeção", "plano"]}}],
                        [{"LOWER": "quando"}, {"LOWER": "foi"}, {"LOWER": {"IN": ["a", "o"]}}, 
                         {"LOWER": {"IN": ["última", "último"]}}],
                    ]
                    
                    # Contagem
                    count_patterns = [
                        [{"LOWER": {"IN": ["quantos", "quantas"]}}, 
                         {"LOWER": {"IN": ["equipamentos", "manutenções", "reparos", "planos", "localidades"]}}],
                        [{"LOWER": "número"}, {"LOWER": "de"}, 
                         {"LOWER": {"IN": ["equipamentos", "manutenções", "planos"]}}],
                    ]
                    
                    # Status/Estado
                    status_patterns_matcher = [
                        [{"LOWER": {"IN": ["status", "estado", "situação"]}}, 
                         {"LOWER": {"IN": ["do", "da", "dos", "das"]}}],
                        [{"LOWER": {"IN": ["como", "qual"]}}, {"LOWER": "está"}, 
                         {"LOWER": {"IN": ["o", "a"]}}],
                    ]

                    # PMM_2 specific
                    pmm2_patterns_matcher = [
                        [{"LOWER": {"IN": ["plano", "planos"]}}, {"LOWER": "de"}, {"LOWER": "manutenção"}],
                        [{"LOWER": "pmm_2"}],
                        [{"LOWER": "pmm2"}],
                        [{"LOWER": "manutenção"}, {"LOWER": "agendada"}, {"LOWER": "no"}, {"LOWER": "centro"}],
                        [{"LOWER": "data"}, {"LOWER": "planejada"}], # Added to help identify planned date queries
                        [{"LOWER": "próximo"}, {"LOWER": "teste"}],
                        [{"LOWER": "próxima"}, {"LOWER": "manutenção"}],
                    ]

                    # SAP Location specific
                    sap_location_patterns_matcher = [
                        [{"LOWER": "localidade"}, {"LOWER": {"IN": ["de", "do"]}}],
                        [{"LOWER": "subestação"}],
                        [{"LOWER": "localidades"}],
                        [{"LOWER": "subestações"}],
                        [{"LOWER": "região"}],
                    ]

                    # Equipment by Location
                    equipment_by_location_patterns_matcher = [
                        [{"LOWER": "equipamentos"}, {"LOWER": "na"}, {"LOWER": {"IN": ["localidade", "subestação", "região"]}}],
                        [{"LOWER": {"IN": ["quais", "quais"]}}, {"LOWER": "equipamentos"}, {"LOWER": "estão"}, {"LOWER": "em"}],
                    ]
                    
                    # Adicionar padrões ao matcher
                    self.matcher.add("LAST_MAINTENANCE", last_patterns)
                    self.matcher.add("COUNT_QUERY", count_patterns)
                    self.matcher.add("STATUS_QUERY", status_patterns_matcher)
                    self.matcher.add("PMM2_PLAN_QUERY", pmm2_patterns_matcher)
                    self.matcher.add("SAP_LOCATION_QUERY", sap_location_patterns_matcher)
                    self.matcher.add("EQUIPMENT_BY_LOCATION_QUERY", equipment_by_location_patterns_matcher)

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
            elif "manutenção" in query_lower:
                intent = QueryIntent.COUNT_MAINTENANCE
            elif "plano" in query_lower:
                intent = QueryIntent.PMM2_PLAN_SEARCH
            elif "localidade" in query_lower:
                intent = QueryIntent.SAP_LOCATION_SEARCH
            else:
                intent = QueryIntent.GENERAL_QUERY
        elif any(word in query_lower for word in ["status", "estado", "situação"]):
            intent = QueryIntent.EQUIPMENT_STATUS
        elif any(word in query_lower for word in ["plano", "pmm2", "pmm_2", "data planejada", "próximo teste"]):
            intent = QueryIntent.UPCOMING_MAINTENANCE # Priorize UPCOMING_MAINTENANCE for planned date/next test
        elif any(word in query_lower for word in ["localidade", "subestação", "região"]):
            intent = QueryIntent.SAP_LOCATION_SEARCH
        else:
            intent = QueryIntent.GENERAL_QUERY
        
        # Entidades simples usando regex
        entities = self._extract_numbers_and_dates(query)
        entities.extend(self._extract_basic_entities_regex(query))
        
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
                logger.debug(f"Error in entity extraction (spaCy): {e}")
        
        # Sempre usar extração básica com regex (fallback)
        entities.extend(self._extract_numbers_and_dates(original_query))
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
            "WORK_CENTER": QueryEntity.WORK_CENTER,
            "PLAN_CODE": QueryEntity.PLAN_CODE,
            "SAP_LOCATION_CODE": QueryEntity.SAP_LOCATION_CODE,
            "SAP_LOCATION_DENOMINATION": QueryEntity.SAP_LOCATION_DENOMINATION,
            "SAP_LOCATION_ABBREVIATION": QueryEntity.SAP_LOCATION_ABBREVIATION,
            "REGION": QueryEntity.REGION,
        }
        return mapping.get(spacy_label)
    
    def _normalize_entity_value(self, text: str, entity_type: QueryEntity, entity_id: Optional[str] = None) -> Any:
        """Normaliza valor da entidade para uso em consultas."""
        if entity_id:
            return entity_id
            
        if entity_type == QueryEntity.EQUIPMENT_TYPE:
            type_mapping = {
                "transformador": "Transformador",
                "transformadores": "Transformador",
                "disjuntor": "Disjuntor",
                "disjuntores": "Disjuntor",
                "seccionadora": "Seccionadora",
                "seccionadoras": "Seccionadora",
                "motor": "Motor",
                "motores": "Motor",
                "gerador": "Gerador",
                "geradores": "Gerador",
                "para-raios": "Para-raios",
                "pararaios": "Para-raios",
                # Removido "equipamento": "equipment" para evitar filtros incorretos
            }
            return type_mapping.get(text.lower(), text.strip()) # Use original case for database if no specific mapping
        
        elif entity_type == QueryEntity.MAINTENANCE_TYPE:
            maintenance_mapping = {
                "preventiva": "Preventive",
                "corretiva": "Corrective",
                "preditiva": "Predictive",
                "emergencial": "Emergency",
                "manutenção": "Maintenance",
                "manutenções": "Maintenance",
                "reparo": "Repair",
                "reparos": "Repair",
                "inspeção": "Inspection",
                "inspeções": "Inspection",
                "teste operativo": "Operative Test",
                "teste operatório": "Operative Test",
                "teste": "Test",
            }
            return maintenance_mapping.get(text.lower(), text.strip())
        
        elif entity_type == QueryEntity.TIME_PERIOD:
            return self._normalize_time_period(text)
        
        elif entity_type == QueryEntity.STATUS:
            status_map = {
                "crítico": "High", "crítica": "High", "alta": "High", # For criticality
                "ativo": "Active", "ativa": "Active", "operacional": "Active", # For equipment status
                "inativo": "Inactive", "inativa": "Inactive", "fora de serviço": "Inactive",
                "em manutenção": "Maintenance",
                "concluída": "Completed", "concluida": "Completed", "planejada": "Planned", # For maintenance/PMM2 status
                "em andamento": "InProgress", "andamento": "InProgress",
                "cancelada": "Cancelled", "cancelado": "Cancelled"
            }
            return status_map.get(text.lower(), text.strip())

        elif entity_type == QueryEntity.WORK_CENTER or entity_type == QueryEntity.PLAN_CODE or \
             entity_type == QueryEntity.SAP_LOCATION_CODE or entity_type == QueryEntity.SAP_LOCATION_ABBREVIATION or \
             entity_type == QueryEntity.REGION:
            return text.strip().upper() # These are typically uppercase codes

        elif entity_type == QueryEntity.SAP_LOCATION_DENOMINATION:
            return text.strip() # Denomination can have mixed case

        return text.strip()
    
    def _normalize_time_period(self, text: str) -> Dict[str, Any]:
        """Normaliza períodos temporais para datas específicas."""
        today = datetime.now()
        
        time_mapping = {
            "hoje": {"start": today.replace(hour=0, minute=0, second=0, microsecond=0),
                    "end": today.replace(hour=23, minute=59, second=59, microsecond=999999)},
            "ontem": {"start": (today - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0),
                     "end": (today - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)},
            "esta semana": {"start": today - timedelta(days=today.weekday()), "end": today + timedelta(days=6 - today.weekday())},
            "semana": {"start": today - timedelta(days=7), "end": today}, # Default to last 7 days
            "este mês": {"start": today.replace(day=1), "end": today},
            "mês": {"start": today - timedelta(days=30), "end": today}, # Default to last 30 days
            "este ano": {"start": today.replace(month=1, day=1), "end": today},
            "ano": {"start": today - timedelta(days=365), "end": today}, # Default to last 365 days
            "último mês": {"start": (today.replace(day=1) - timedelta(days=1)).replace(day=1), "end": today.replace(day=1) - timedelta(days=1)},
            "última semana": {"start": today - timedelta(weeks=2) + timedelta(days=1), "end": today - timedelta(weeks=1)},
            "último ano": {"start": (today.replace(month=1, day=1) - timedelta(days=1)).replace(month=1, day=1), "end": today.replace(month=1, day=1) - timedelta(days=1)},
            "próximo mês": {"start": today.replace(day=1) + timedelta(days=32), "end": today.replace(day=1) + timedelta(days=62)}, # Approximation for next month
            "próxima semana": {"start": today + timedelta(days=1), "end": today + timedelta(days=7)},
            "data planejada": {"start": today, "end": today + timedelta(days=365*2)}, # Future plans for next 2 years
            "próxima data": {"start": today, "end": today + timedelta(days=365*2)}, # Future plans for next 2 years
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
        
        # Detectar datas (formato brasileiro e ISO)
        date_patterns_regex = [
            r'\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})\b',  # DD/MM/YYYY or DD-MM-YYYY
            r'\b(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})\b'    # YYYY-MM-DD
        ]

        for date_pattern in date_patterns_regex:
            for match in re.finditer(date_pattern, query):
                try:
                    parts = [int(p) for p in match.groups()]
                    if len(parts) == 3:
                        if parts[0] > 31: # Assume YYYY-MM-DD if first part is a large number (year)
                            year, month, day = parts
                        else: # Assume DD-MM-YYYY
                            day, month, year = parts
                        
                        if len(str(year)) == 2:
                            year = 2000 + year if year < 50 else 1900 + year # Heuristic for 2-digit year
                        
                        date_obj = datetime(year, month, day)
                        entities.append(ExtractedEntity(
                            type=QueryEntity.DATE_RANGE,
                            value=match.group(0),
                            normalized_value=date_obj,
                            confidence=0.9,
                            start_char=match.start(),
                            end_char=match.end()
                        ))
                except ValueError:
                    # Invalid date, ignore
                    pass
        
        return entities
    
    def _extract_basic_entities_regex(self, query: str) -> List[ExtractedEntity]:
        """Extrai entidades básicas usando regex (fallback quando spaCy não está disponível)."""
        entities = []
        query_lower = query.lower()
        
        # Detectar tipos de equipamentos específicos (não incluir "equipamento" genérico)
        equipment_patterns = {
            r'\btransformador[es]?\b': 'Transformador',
            r'\bdisjuntor[es]?\b': 'Disjuntor', 
            r'\bseccionadora[s]?\b': 'Seccionadora',
            r'\bmotor[es]?\b': 'Motor',
            r'\bgerador[es]?\b': 'Gerador',
            r'\bpara-raios\b': 'Para-raios',
            r'\bpararaios\b': 'Para-raios',
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
        # Pattern atualizado para ser mais genérico e capturar "4k4" se não tiver prefixo
        # Tenta capturar primeiro IDs com prefixo, depois IDs que parecem "sufixos"
        equipment_id_patterns = [
            r'\b(TR|DJ|SC|PR|BB|BC|AT|CF)-?\d+\b', # Example: TR-001, DJ-002
            r'\b([A-Z0-9]+k\d+)\b', # Example: 4K4 (case-insensitive for "k")
            r'\b([A-Z0-9_]{2,10})\b', # Generic short codes/IDs like "UEM", "CH123" but be careful
        ]
        
        for pattern in equipment_id_patterns:
            for match in re.finditer(pattern, query, re.IGNORECASE):
                # Avoid capturing very common words or single letters
                if len(match.group(0)) > 1 and match.group(0).lower() not in ['de', 'da', 'do', 'em', 'um', 'uma']:
                    entities.append(ExtractedEntity(
                        type=QueryEntity.EQUIPMENT_ID,
                        value=match.group(0),
                        normalized_value=match.group(0).upper(), # Normalize to uppercase
                        confidence=0.9,
                        start_char=match.start(),
                        end_char=match.end()
                    ))
        
        # Detectar tipos de manutenção
        maintenance_patterns = {
            r'\bmanutenção\b': 'Maintenance',
            r'\bmanutenções\b': 'Maintenance',
            r'\bpreventiva\b': 'Preventive',
            r'\bcorretiva\b': 'Corrective',
            r'\bpreditiva\b': 'Predictive',
            r'\bemergencial\b': 'Emergency',
            r'\breparo\b': 'Repair',
            r'\breparos\b': 'Repair',
            r'\binspeção\b': 'Inspection',
            r'\binspecao\b': 'Inspection',
            r'\bteste operativo\b': 'Operative Test',
            r'\bteste operatório\b': 'Operative Test',
            r'\bteste\b': 'Test',
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

        # Detectar PMM_2 entities
        pmm2_code_pattern = r'\b(OM|PM|PMM)-\d{4}-?\d+\b' # Ordem de Manutenção/Plano de Manutenção
        for match in re.finditer(pmm2_code_pattern, query, re.IGNORECASE):
            entities.append(ExtractedEntity(
                type=QueryEntity.PLAN_CODE,
                value=match.group(0),
                normalized_value=match.group(0).upper(),
                confidence=0.8,
                start_char=match.start(),
                end_char=match.end()
            ))

        work_center_pattern = r'\b(TTABDPM|TTBGAQM|TTBELOH|TTITAIP)\b' # Example Work Centers from Localidades_SAP.csv
        for match in re.finditer(work_center_pattern, query, re.IGNORECASE):
             entities.append(ExtractedEntity(
                type=QueryEntity.WORK_CENTER,
                value=match.group(0),
                normalized_value=match.group(0).upper(),
                confidence=0.8,
                start_char=match.start(),
                end_char=match.end()
            ))

        # Detectar SAP Location entities
        sap_location_code_pattern = r'\b[A-Z]{2}-S-\d+\b' # MT-S-72183
        for match in re.finditer(sap_location_code_pattern, query, re.IGNORECASE):
            entities.append(ExtractedEntity(
                type=QueryEntity.SAP_LOCATION_CODE,
                value=match.group(0),
                normalized_value=match.group(0).upper(),
                confidence=0.9,
                start_char=match.start(),
                end_char=match.end()
            ))
        
        # Detectar abreviações (e.g., BDP, UEM) - requires careful filtering to avoid common words
        # Aumentar a lista de abreviações com base em Localidades_SAP.csv
        sap_abbreviation_list = ['BDP', 'UEM', 'UJG', 'UNP', 'SGT', 'USS', 'UVG'] # From Localidades_SAP.csv
        sap_abbreviation_pattern = r'\b(' + '|'.join(re.escape(abbr) for abbr in sap_abbreviation_list) + r')\b'
        
        for match in re.finditer(sap_abbreviation_pattern, query, re.IGNORECASE):
            # Ensure it's not a common word being misidentified, and prefer explicit patterns
            # This regex is already quite precise due to \b word boundaries
            entities.append(ExtractedEntity(
                type=QueryEntity.SAP_LOCATION_ABBREVIATION,
                value=match.group(0),
                normalized_value=match.group(0).upper(),
                confidence=0.9, # High confidence for known abbreviations
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
                        # Determinar se é contagem de equipamentos ou manutenções ou planos ou localidades
                        has_equipment = any(e.type == QueryEntity.EQUIPMENT_TYPE for e in entities) or "equipamento" in doc.text
                        has_maintenance = any(e.type == QueryEntity.MAINTENANCE_TYPE for e in entities) or any(word in doc.text for word in ["manutenção", "reparo"])
                        has_plan = any(e.type == QueryEntity.PLAN_CODE for e in entities) or any(word in doc.text for word in ["plano", "pmm_2", "pmm2"])
                        has_location = any(e.type in [QueryEntity.SAP_LOCATION_CODE, QueryEntity.SAP_LOCATION_DENOMINATION] for e in entities) or any(word in doc.text for word in ["localidade", "subestação"])

                        if has_equipment: return QueryIntent.COUNT_EQUIPMENT
                        if has_maintenance: return QueryIntent.COUNT_MAINTENANCE
                        if has_plan: return QueryIntent.PMM2_PLAN_SEARCH # Count plans
                        if has_location: return QueryIntent.SAP_LOCATION_SEARCH # Count locations
                        return QueryIntent.COUNT_EQUIPMENT  # Default count
                    
                    elif label == "STATUS_QUERY":
                        return QueryIntent.EQUIPMENT_STATUS
                    
                    # NOVAS INTENÇÕES DE PMM2 E UPCOMING
                    elif label == "PMM2_PLAN_QUERY":
                        # Se há termos como "data planejada" ou "próximo teste", é UPCOMING_MAINTENANCE
                        if any(e.normalized_value in ["planned_date", "next_date"] for e in entities if e.type == QueryEntity.TIME_PERIOD) or \
                           any(e.normalized_value in ["Operative Test", "Test"] for e in entities if e.type == QueryEntity.MAINTENANCE_TYPE):
                           return QueryIntent.UPCOMING_MAINTENANCE
                        return QueryIntent.PMM2_PLAN_SEARCH # Otherwise, it's just a general PMM2 plan search
                    
                    elif label == "SAP_LOCATION_QUERY":
                        return QueryIntent.SAP_LOCATION_SEARCH
                    elif label == "EQUIPMENT_BY_LOCATION_QUERY":
                        return QueryIntent.EQUIPMENT_BY_LOCATION

            except Exception as e:
                logger.debug(f"Error in matcher processing: {e}")
        
        # Análise baseada em palavras-chave (fallback sempre disponível)
        text = doc.text.lower()
        
        # --- PRIORIZAÇÃO DAS INTENÇÕES ---

        # 1. Manutenção Programada / Próxima Manutenção (Mais específica para "data planejada" e "próximo teste")
        if any(word in text for word in ["data planejada", "próximo teste", "próxima data", "teste operativo", "agenda", "agendado"]):
            # Garante que é sobre equipamento/manutenção e não uma data qualquer
            if any(e.type in [QueryEntity.EQUIPMENT_TYPE, QueryEntity.EQUIPMENT_ID, QueryEntity.MAINTENANCE_TYPE] for e in entities) or \
               any(word in text for word in ["disjuntor", "transformador", "equipamento", "manutenção", "plano"]):
                return QueryIntent.UPCOMING_MAINTENANCE

        # 2. Última Manutenção / Histórico (já existente e importante)
        if any(word in text for word in ["último", "última", "recente", "mais recente"]):
            if any(word in text for word in ["manutenção", "reparo", "inspeção", "plano"]):
                return QueryIntent.LAST_MAINTENANCE
            else:
                return QueryIntent.MAINTENANCE_HISTORY # Generaliza para histórico se não for "última" específica

        # 3. Contagem
        if any(word in text for word in ["quantos", "quantas", "número", "total"]):
            if any(word in text for word in ["equipamento", "equipamentos"]):
                return QueryIntent.COUNT_EQUIPMENT
            elif any(word in text for word in ["manutenção", "manutenções", "reparo", "reparos"]):
                return QueryIntent.COUNT_MAINTENANCE
            elif any(word in text for word in ["plano", "planos", "pmm_2", "pmm2"]):
                return QueryIntent.PMM2_PLAN_SEARCH # Count plans
            elif any(word in text for word in ["localidade", "localidades", "subestação", "subestações"]):
                return QueryIntent.SAP_LOCATION_SEARCH # Count locations
            return QueryIntent.GENERAL_QUERY # Default count if ambiguous

        # 4. Status/Estado de Equipamento
        if any(word in text for word in ["status", "estado", "situação", "como está"]):
            if any(e.type == QueryEntity.EQUIPMENT_TYPE or e.type == QueryEntity.EQUIPMENT_ID for e in entities) or \
               any(word in text for word in ["equipamento", "disjuntor", "transformador"]):
                return QueryIntent.EQUIPMENT_STATUS

        # 5. Análise de Falhas
        if any(word in text for word in ["falha", "problema", "erro", "defeito", "incidente"]):
            return QueryIntent.FAILURE_ANALYSIS

        # 6. Histórico de Manutenção (geral, se não for "última" específica)
        if any(word in text for word in ["histórico", "history", "passado"]):
            return QueryIntent.MAINTENANCE_HISTORY
        
        # 7. Busca por Planos PMM_2 (se menciona PMM_2 ou plano de manutenção)
        if any(word in text for word in ["plano", "planos", "pmm_2", "pmm2", "ordem de manutenção"]):
            return QueryIntent.PMM2_PLAN_SEARCH

        # 8. Equipamento por Localidade (se menciona "equipamento em localidade")
        if (any(e.type == QueryEntity.EQUIPMENT_TYPE or e.type == QueryEntity.EQUIPMENT_ID for e in entities) or \
            any(word in text for word in ["equipamento", "equipamentos"])) and \
           (any(e.type in [QueryEntity.SAP_LOCATION_CODE, QueryEntity.SAP_LOCATION_DENOMINATION, QueryEntity.SAP_LOCATION_ABBREVIATION, QueryEntity.REGION] for e in entities) or \
            any(word in text for word in ["localidade", "subestação", "região"])):
            return QueryIntent.EQUIPMENT_BY_LOCATION
        
        # 9. Busca por Localidade SAP (DEVE SER MAIS BAIXA NA PRIORIDADE)
        # Só aciona se a pergunta é principalmente sobre a localidade e não sobre algo MAIS ESPECÍFICO (como equipamentos dentro dela).
        if any(e.type in [QueryEntity.SAP_LOCATION_CODE, QueryEntity.SAP_LOCATION_DENOMINATION, QueryEntity.SAP_LOCATION_ABBREVIATION, QueryEntity.REGION] for e in entities) or \
           any(word in text for word in ["localidade", "subestacao", "planta", "sitio", "região"]):
            return QueryIntent.SAP_LOCATION_SEARCH

        # 10. Busca por Equipamento (se menciona equipamento mas sem outra intenção clara)
        if any(e.type == QueryEntity.EQUIPMENT_TYPE for e in entities) or \
           any(e.type == QueryEntity.EQUIPMENT_ID for e in entities) or \
           any(word in text for word in ["equipamento", "transformador", "disjuntor", "para-raios"]):
            return QueryIntent.EQUIPMENT_SEARCH

        # Default: Consulta Geral
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
        
        # Coletar filtros das entidades
        equipment_types = [e.normalized_value for e in entities if e.type == QueryEntity.EQUIPMENT_TYPE and e.normalized_value not in ["equipment", "equipamentos"]]
        equipment_ids = [e.normalized_value for e in entities if e.type == QueryEntity.EQUIPMENT_ID]
        maintenance_types = [e.normalized_value for e in entities if e.type == QueryEntity.MAINTENANCE_TYPE]
        
        # New entities for PMM_2 and SAPLocation
        plan_codes = [e.normalized_value for e in entities if e.type == QueryEntity.PLAN_CODE]
        work_centers = [e.normalized_value for e in entities if e.type == QueryEntity.WORK_CENTER]
        sap_location_codes = [e.normalized_value for e in entities if e.type == QueryEntity.SAP_LOCATION_CODE]
        sap_location_denominations = [e.normalized_value for e in entities if e.type == QueryEntity.SAP_LOCATION_DENOMINATION]
        sap_location_abbreviations = [e.normalized_value for e in entities if e.type == QueryEntity.SAP_LOCATION_ABBREVIATION]
        regions = [e.normalized_value for e in entities if e.type == QueryEntity.REGION]
        
        status_filter = [e.normalized_value for e in entities if e.type == QueryEntity.STATUS]
        
        # Debug logging
        logger.info(f"SQL Generation Debug - Intent: {intent.value}")
        logger.info(f"Entities: {[(e.type.value, e.value, e.normalized_value) for e in entities]}")
        logger.info(f"Equipment Types: {equipment_types}, IDs: {equipment_ids}")
        logger.info(f"Maintenance Types: {maintenance_types}")
        logger.info(f"Plan Codes: {plan_codes}, Work Centers: {work_centers}")
        logger.info(f"SAP Locations: Codes: {sap_location_codes}, Denominations: {sap_location_denominations}, Abbreviations: {sap_location_abbreviations}, Regions: {regions}")
        logger.info(f"Status Filter: {status_filter}")

        sql = None # Initialize sql variable

        # --- Geração de SQL para UPCOMING_MAINTENANCE (PMM_2 / Manutenções Futuras) ---
        if intent == QueryIntent.UPCOMING_MAINTENANCE:
            sql = """
            SELECT
                pmm.maintenance_plan_code,
                pmm.maintenance_item_text,
                pmm.planned_date,
                pmm.installation_location,
                pmm.equipment_code,
                e.name AS equipment_name,
                e.equipment_type,
                e.criticality,
                sl.denomination AS location_name,
                sl.abbreviation AS location_abbreviation
            FROM pmm_2 pmm
            LEFT JOIN equipments e ON pmm.equipment_id = e.id
            LEFT JOIN sap_locations sl ON e.sap_location_id = sl.id
            WHERE pmm.status IN ('Active', 'Planned') -- Planos ativos ou planejados
            AND pmm.planned_date IS NOT NULL
            AND pmm.planned_date >= %(current_date)s -- Apenas planos futuros
            """
            parameters['current_date'] = datetime.now().date()

            # Filtrar por tipo de equipamento (Ex: disjuntor)
            if equipment_types:
                sql += " AND e.equipment_type = ANY(%(equipment_types)s)"
                parameters['equipment_types'] = equipment_types
            
            # Filtrar por IDs de equipamento (Ex: 4k4)
            if equipment_ids:
                # Assuming equipment_ids can be partial codes like "4k4"
                # Combine original equipment IDs with potential matches in pmm.equipment_code or installation_location
                id_like_patterns = [f"%{eid}%" for eid in equipment_ids]
                sql += " AND (e.code ILIKE ANY(%(equipment_id_patterns)s) OR pmm.equipment_code ILIKE ANY(%(equipment_id_patterns)s) OR pmm.installation_location ILIKE ANY(%(equipment_id_patterns)s))"
                parameters['equipment_id_patterns'] = id_like_patterns

            # Filtrar por tipo de manutenção (Ex: teste operativo)
            if maintenance_types:
                # Tentativa de mapear 'Operative Test' para maintenance_item_text
                # Isso pode ser ajustado com um campo mais específico no PMM_2 se disponível
                maintenance_type_patterns = [f"%{mt}%" for mt in maintenance_types]
                sql += " AND pmm.maintenance_item_text ILIKE ANY(%(maintenance_type_patterns)s)"
                parameters['maintenance_type_patterns'] = maintenance_type_patterns

            # Filtrar por localidade SAP (Ex: UEM)
            if sap_location_abbreviations:
                sql += " AND (sl.abbreviation = ANY(%(sap_abbreviations)s) OR pmm.installation_location ILIKE ANY(%(sap_abbreviation_patterns)s))"
                parameters['sap_abbreviations'] = sap_location_abbreviations
                parameters['sap_abbreviation_patterns'] = [f"%{abbr}%" for abbr in sap_location_abbreviations]
            elif sap_location_codes:
                sql += " AND (sl.location_code = ANY(%(sap_location_codes)s) OR pmm.installation_location ILIKE ANY(%(sap_location_code_patterns)s))"
                parameters['sap_location_codes'] = sap_location_codes
                parameters['sap_location_code_patterns'] = [f"%{code}%" for code in sap_location_codes]
            elif sap_location_denominations:
                sql += " AND (sl.denomination ILIKE ANY(%(sap_denominations)s) OR pmm.installation_location ILIKE ANY(%(sap_denominations)s))"
                parameters['sap_denominations'] = [f"%{d}%" for d in sap_location_denominations]

            # Filtros temporais adicionais, se houver
            if temporal_context and temporal_context['type'] == 'period':
                period = temporal_context['period']
                if 'start' in period and 'end' in period:
                    sql += " AND pmm.planned_date BETWEEN %(start_date)s AND %(end_date)s"
                    parameters['start_date'] = period['start']
                    parameters['end_date'] = period['end']

            sql += " ORDER BY pmm.planned_date ASC LIMIT 10" # Limita os próximos 10 planos

        elif intent == QueryIntent.LAST_MAINTENANCE:
            sql = """
            SELECT e.name, e.equipment_type, e.criticality, sl.denomination as location_name, sl.location_code,
                   COALESCE(m.completion_date, m.start_date, m.scheduled_date) as maintenance_date,
                   m.maintenance_type, m.status, m.title, m.actual_cost,
                   pmm.maintenance_plan_code, pmm.work_center, pmm.maintenance_item_text
            FROM equipments e
            LEFT JOIN maintenances m ON e.id = m.equipment_id
            LEFT JOIN pmm_2 pmm ON m.id = pmm.maintenance_id -- Link to PMM_2 if maintenance is related to a plan
            LEFT JOIN sap_locations sl ON e.sap_location_id = sl.id
            WHERE m.completion_date IS NOT NULL
            """
            
            if equipment_types:
                sql += " AND e.equipment_type = ANY(%(equipment_types)s)"
                parameters['equipment_types'] = equipment_types
            if equipment_ids:
                sql += " AND e.code = ANY(%(equipment_ids)s)" # Assuming e.code is the ID field
                parameters['equipment_ids'] = equipment_ids
            if maintenance_types:
                sql += " AND m.maintenance_type = ANY(%(maintenance_types)s)"
                parameters['maintenance_types'] = maintenance_types
            if status_filter:
                sql += " AND m.status = ANY(%(status_filter)s)" # Maintenance status
                parameters['status_filter'] = status_filter
            if work_centers:
                sql += " AND pmm.work_center = ANY(%(work_centers)s)"
                parameters['work_centers'] = work_centers
            if plan_codes:
                sql += " AND pmm.maintenance_plan_code = ANY(%(plan_codes)s)"
                parameters['plan_codes'] = plan_codes
            if sap_location_abbreviations:
                sql += " AND sl.abbreviation = ANY(%(sap_abbreviations)s)"
                parameters['sap_abbreviations'] = sap_location_abbreviations
            elif sap_location_codes:
                sql += " AND sl.location_code = ANY(%(sap_location_codes)s)"
                parameters['sap_location_codes'] = sap_location_codes

            sql += " ORDER BY m.completion_date DESC LIMIT 1"
        
        elif intent == QueryIntent.COUNT_EQUIPMENT:
            sql = """
            SELECT COUNT(DISTINCT e.id) as total 
            FROM equipments e
            LEFT JOIN sap_locations sl ON e.sap_location_id = sl.id
            WHERE 1=1
            """
            if equipment_types:
                sql += " AND e.equipment_type = ANY(%(equipment_types)s)"
                parameters['equipment_types'] = equipment_types
            if status_filter:
                sql += " AND e.status = ANY(%(status_filter)s)" # Equipment status
                parameters['status_filter'] = status_filter
            if sap_location_codes:
                sql += " AND sl.location_code = ANY(%(sap_location_codes)s)"
                parameters['sap_location_codes'] = sap_location_codes
            if sap_location_denominations:
                sql += " AND sl.denomination ILIKE ANY(%(sap_location_denominations)s)"
                parameters['sap_location_denominations'] = [f"%{d}%" for d in sap_location_denominations]
            if sap_location_abbreviations:
                sql += " AND sl.abbreviation = ANY(%(sap_location_abbreviations)s)"
                parameters['sap_location_abbreviations'] = sap_location_abbreviations
            if regions:
                sql += " AND sl.region = ANY(%(regions)s)"
                parameters['regions'] = regions
        
        elif intent == QueryIntent.COUNT_MAINTENANCE:
            sql = """
            SELECT COUNT(DISTINCT m.id) as total 
            FROM maintenances m
            LEFT JOIN equipments e ON m.equipment_id = e.id
            LEFT JOIN pmm_2 pmm ON m.id = pmm.maintenance_id
            LEFT JOIN sap_locations sl ON e.sap_location_id = sl.id
            WHERE 1=1
            """
            if maintenance_types:
                sql += " AND m.maintenance_type = ANY(%(maintenance_types)s)"
                parameters['maintenance_types'] = maintenance_types
            if status_filter: # Status for Maintenance
                sql += " AND m.status = ANY(%(status_filter)s)"
                parameters['status_filter'] = status_filter
            if temporal_context and temporal_context['type'] == 'period':
                period = temporal_context['period']
                if 'start' in period and 'end' in period:
                    sql += " AND COALESCE(m.completion_date, m.start_date, m.scheduled_date) BETWEEN %(start_date)s AND %(end_date)s"
                    parameters['start_date'] = period['start']
                    parameters['end_date'] = period['end']
            if work_centers:
                sql += " AND pmm.work_center = ANY(%(work_centers)s)"
                parameters['work_centers'] = work_centers
            if plan_codes:
                sql += " AND pmm.maintenance_plan_code = ANY(%(plan_codes)s)"
                parameters['plan_codes'] = plan_codes
            if equipment_ids:
                sql += " AND e.code = ANY(%(equipment_ids)s)"
                parameters['equipment_ids'] = equipment_ids
            if sap_location_abbreviations:
                sql += " AND sl.abbreviation = ANY(%(sap_abbreviations)s)"
                parameters['sap_abbreviations'] = sap_location_abbreviations

        elif intent == QueryIntent.EQUIPMENT_STATUS:
            sql = """
            SELECT e.name, e.equipment_type, e.status, e.criticality, e.code,
                   sl.denomination as location_name, sl.location_code, sl.abbreviation as location_abbreviation,
                   COALESCE(last_maint.last_maintenance_date, 'Nunca') as last_maintenance_date,
                   last_maint.last_maintenance_type, last_maint.last_maintenance_status
            FROM equipments e
            LEFT JOIN (
                SELECT m.equipment_id, MAX(COALESCE(m.completion_date, m.start_date, m.scheduled_date)) as last_maintenance_date,
                       (ARRAY_AGG(m.maintenance_type ORDER BY COALESCE(m.completion_date, m.start_date, m.scheduled_date) DESC))[1] as last_maintenance_type,
                       (ARRAY_AGG(m.status ORDER BY COALESCE(m.completion_date, m.start_date, m.scheduled_date) DESC))[1] as last_maintenance_status
                FROM maintenances m
                GROUP BY m.equipment_id
            ) last_maint ON e.id = last_maint.equipment_id
            LEFT JOIN sap_locations sl ON e.sap_location_id = sl.id
            WHERE 1=1
            """
            if equipment_types:
                sql += " AND e.equipment_type = ANY(%(equipment_types)s)"
                parameters['equipment_types'] = equipment_types
            if equipment_ids:
                sql += " AND e.code = ANY(%(equipment_ids)s)"
                parameters['equipment_ids'] = equipment_ids
            if status_filter: # Status for Equipment
                sql += " AND e.status = ANY(%(status_filter)s)"
                parameters['status_filter'] = status_filter
            if sap_location_codes:
                sql += " AND sl.location_code = ANY(%(sap_location_codes)s)"
                parameters['sap_location_codes'] = sap_location_codes
            if sap_location_denominations:
                sql += " AND sl.denomination ILIKE ANY(%(sap_location_denominations)s)"
                parameters['sap_location_denominations'] = [f"%{d}%" for d in sap_location_denominations]
            if sap_location_abbreviations:
                sql += " AND sl.abbreviation = ANY(%(sap_location_abbreviations)s)"
                parameters['sap_location_abbreviations'] = sap_location_abbreviations
            if regions:
                sql += " AND sl.region = ANY(%(regions)s)"
                parameters['regions'] = regions
            
        elif intent == QueryIntent.MAINTENANCE_HISTORY:
            sql = """
            SELECT e.name as equipment_name, e.equipment_type, e.code as equipment_code, sl.denomination as location_name,
                   COALESCE(m.completion_date, m.start_date, m.scheduled_date) as maintenance_date,
                   m.maintenance_type, m.description, m.status, m.actual_cost, m.title, m.technician,
                   pmm.maintenance_plan_code, pmm.work_center, pmm.maintenance_item_text
            FROM equipments e
            JOIN maintenances m ON e.id = m.equipment_id
            LEFT JOIN pmm_2 pmm ON m.id = pmm.maintenance_id
            LEFT JOIN sap_locations sl ON e.sap_location_id = sl.id
            WHERE 1=1
            """
            if equipment_types:
                sql += " AND e.equipment_type = ANY(%(equipment_types)s)"
                parameters['equipment_types'] = equipment_types
            if equipment_ids:
                sql += " AND e.code = ANY(%(equipment_ids)s)"
                parameters['equipment_ids'] = equipment_ids
            if maintenance_types:
                sql += " AND m.maintenance_type = ANY(%(maintenance_types)s)"
                parameters['maintenance_types'] = maintenance_types
            if status_filter: # Status for Maintenance
                sql += " AND m.status = ANY(%(status_filter)s)"
                parameters['status_filter'] = status_filter
            if temporal_context and temporal_context['type'] == 'period':
                period = temporal_context['period']
                if 'start' in period and 'end' in period:
                    sql += " AND COALESCE(m.completion_date, m.start_date, m.scheduled_date) BETWEEN %(start_date)s AND %(end_date)s"
                    parameters['start_date'] = period['start']
                    parameters['end_date'] = period['end']
            if work_centers:
                sql += " AND pmm.work_center = ANY(%(work_centers)s)"
                parameters['work_centers'] = work_centers
            if plan_codes:
                sql += " AND pmm.maintenance_plan_code = ANY(%(plan_codes)s)"
                parameters['plan_codes'] = plan_codes
            if sap_location_codes:
                sql += " AND sl.location_code = ANY(%(sap_location_codes)s)"
                parameters['sap_location_codes'] = sap_location_codes
            if sap_location_abbreviations:
                sql += " AND sl.abbreviation = ANY(%(sap_abbreviations)s)"
                parameters['sap_abbreviations'] = sap_location_abbreviations
            
            sql += " ORDER BY COALESCE(m.completion_date, m.start_date, m.scheduled_date) DESC"

        elif intent == QueryIntent.PMM2_PLAN_SEARCH:
            sql = """
            SELECT pmm.maintenance_plan_code, pmm.work_center, pmm.maintenance_item_text,
                   pmm.installation_location, pmm.planned_date, pmm.status,
                   e.name as equipment_name, e.equipment_type, e.code as equipment_code,
                   sl.denomination as location_name, sl.location_code, sl.abbreviation as location_abbreviation
            FROM pmm_2 pmm
            LEFT JOIN equipments e ON pmm.equipment_id = e.id
            LEFT JOIN sap_locations sl ON pmm.sap_location_id = sl.id
            WHERE 1=1
            """
            if plan_codes:
                sql += " AND pmm.maintenance_plan_code = ANY(%(plan_codes)s)"
                parameters['plan_codes'] = plan_codes
            if work_centers:
                sql += " AND pmm.work_center = ANY(%(work_centers)s)"
                parameters['work_centers'] = work_centers
            if equipment_ids:
                sql += " AND (e.code = ANY(%(equipment_ids)s) OR pmm.equipment_code = ANY(%(equipment_ids)s))" # pmm has equipment_code field
                parameters['equipment_ids'] = equipment_ids
            if sap_location_codes:
                sql += " AND (sl.location_code = ANY(%(sap_location_codes)s) OR pmm.installation_location ILIKE ANY(%(sap_location_codes_like)s))" # installation_location can be more specific than sap_location_code
                parameters['sap_location_codes'] = sap_location_codes
                parameters['sap_location_codes_like'] = [f"%{code}%" for code in sap_location_codes]
            if sap_location_abbreviations:
                sql += " AND (sl.abbreviation = ANY(%(sap_abbreviations)s) OR pmm.installation_location ILIKE ANY(%(sap_abbreviation_patterns)s))"
                parameters['sap_abbreviations'] = sap_location_abbreviations
                parameters['sap_abbreviation_patterns'] = [f"%{abbr}%" for abbr in sap_location_abbreviations]
            if sap_location_denominations:
                sql += " AND (sl.denomination ILIKE ANY(%(sap_denominations)s) OR pmm.installation_location ILIKE ANY(%(sap_denominations)s))"
                parameters['sap_denominations'] = [f"%{d}%" for d in sap_location_denominations]

            if temporal_context and temporal_context['type'] == 'period':
                period = temporal_context['period']
                if 'start' in period and 'end' in period:
                    sql += " AND pmm.planned_date BETWEEN %(start_date)s AND %(end_date)s"
                    parameters['start_date'] = period['start']
                    parameters['end_date'] = period['end']
            if status_filter: # Status for PMM_2 plan
                sql += " AND pmm.status = ANY(%(status_filter)s)"
                parameters['status_filter'] = status_filter
            
            sql += " ORDER BY pmm.planned_date DESC"

        elif intent == QueryIntent.SAP_LOCATION_SEARCH:
            sql = """
            SELECT sl.location_code, sl.denomination, sl.abbreviation, sl.region, sl.type_code, sl.status
            FROM sap_locations sl
            WHERE 1=1
            """
            if sap_location_codes:
                sql += " AND sl.location_code = ANY(%(sap_location_codes)s)"
                parameters['sap_location_codes'] = sap_location_codes
            if sap_location_denominations:
                sql += " AND sl.denomination ILIKE ANY(%(sap_location_denominations)s)"
                parameters['sap_location_denominations'] = [f"%{d}%" for d in sap_location_denominations]
            if sap_location_abbreviations:
                sql += " AND sl.abbreviation = ANY(%(sap_location_abbreviations)s)"
                parameters['sap_location_abbreviations'] = sap_location_abbreviations
            if regions:
                sql += " AND sl.region = ANY(%(regions)s)"
                parameters['regions'] = regions
            if status_filter: # Status for SAPLocation
                sql += " AND sl.status = ANY(%(status_filter)s)"
                parameters['status_filter'] = status_filter
            
            sql += " ORDER BY sl.denomination ASC"

        elif intent == QueryIntent.EQUIPMENT_BY_LOCATION:
            sql = """
            SELECT e.name, e.equipment_type, e.code, e.criticality, e.status,
                   sl.denomination as location_name, sl.location_code, sl.abbreviation as location_abbreviation, sl.region
            FROM equipments e
            JOIN sap_locations sl ON e.sap_location_id = sl.id
            WHERE 1=1
            """
            if sap_location_codes:
                sql += " AND sl.location_code = ANY(%(sap_location_codes)s)"
                parameters['sap_location_codes'] = sap_location_codes
            if sap_location_denominations:
                sql += " AND sl.denomination ILIKE ANY(%(sap_location_denominations)s)"
                parameters['sap_location_denominations'] = [f"%{d}%" for d in sap_location_denominations]
            if sap_location_abbreviations:
                sql += " AND sl.abbreviation = ANY(%(sap_location_abbreviations)s)"
                parameters['sap_location_abbreviations'] = sap_location_abbreviations
            if regions:
                sql += " AND sl.region = ANY(%(regions)s)"
                parameters['regions'] = regions
            if equipment_types:
                sql += " AND e.equipment_type = ANY(%(equipment_types)s)"
                parameters['equipment_types'] = equipment_types
            if equipment_ids:
                sql += " AND e.code = ANY(%(equipment_ids)s)"
                parameters['equipment_ids'] = equipment_ids
            if status_filter:
                sql += " AND e.status = ANY(%(status_filter)s)"
                parameters['status_filter'] = status_filter

            sql += " ORDER BY sl.denomination, e.name ASC"

        elif intent == QueryIntent.FAILURE_ANALYSIS:
            sql = """
            SELECT f.failure_type, f.description, f.root_cause, f.severity, f.downtime_hours,
                   e.name as equipment_name, e.code as equipment_code, e.equipment_type,
                   sl.denomination as location_name
            FROM failures f
            LEFT JOIN equipments e ON f.equipment_id = e.id
            LEFT JOIN sap_locations sl ON e.sap_location_id = sl.id
            WHERE 1=1
            """
            if equipment_ids:
                sql += " AND e.code = ANY(%(equipment_ids)s)"
                parameters['equipment_ids'] = equipment_ids
            if equipment_types:
                sql += " AND e.equipment_type = ANY(%(equipment_types)s)"
                parameters['equipment_types'] = equipment_types
            if status_filter: # Status for Failure
                sql += " AND f.status = ANY(%(status_filter)s)"
                parameters['status_filter'] = status_filter
            if temporal_context and temporal_context['type'] == 'period':
                period = temporal_context['period']
                if 'start' in period and 'end' in period:
                    sql += " AND f.failure_date BETWEEN %(start_date)s AND %(end_date)s"
                    parameters['start_date'] = period['start']
                    parameters['end_date'] = period['end']
            if sap_location_abbreviations:
                sql += " AND sl.abbreviation = ANY(%(sap_abbreviations)s)"
                parameters['sap_abbreviations'] = sap_location_abbreviations
            elif sap_location_codes:
                sql += " AND sl.location_code = ANY(%(sap_location_codes)s)"
                parameters['sap_location_codes'] = sap_location_codes

            sql += " ORDER BY f.failure_date DESC"

        elif intent == QueryIntent.EQUIPMENT_SEARCH:
            sql = """
            SELECT e.name, e.equipment_type, e.status, e.criticality, e.code,
                   sl.denomination as location_name, sl.location_code, sl.abbreviation as location_abbreviation
            FROM equipments e
            LEFT JOIN sap_locations sl ON e.sap_location_id = sl.id
            WHERE 1=1
            """
            # Allow searching by name, code, or description (if available)
            if 'query' in parameters: # This would come from a general search if query is not broken down
                 search_pattern = f"%{parameters['query']}%"
                 sql += " AND (e.name ILIKE %(search_pattern)s OR e.code ILIKE %(search_pattern)s OR e.description ILIKE %(search_pattern)s)"
                 parameters['search_pattern'] = search_pattern
                 del parameters['query'] # Remove general query term
            if equipment_types:
                sql += " AND e.equipment_type = ANY(%(equipment_types)s)"
                parameters['equipment_types'] = equipment_types
            if equipment_ids:
                sql += " AND e.code = ANY(%(equipment_ids)s)"
                parameters['equipment_ids'] = equipment_ids
            if status_filter:
                sql += " AND e.status = ANY(%(status_filter)s)"
                parameters['status_filter'] = status_filter
            if sap_location_abbreviations:
                sql += " AND sl.abbreviation = ANY(%(sap_abbreviations)s)"
                parameters['sap_abbreviations'] = sap_location_abbreviations
            elif sap_location_codes:
                sql += " AND sl.location_code = ANY(%(sap_location_codes)s)"
                parameters['sap_location_codes'] = sap_location_codes
            elif sap_location_denominations:
                sql += " AND sl.denomination ILIKE ANY(%(sap_denominations)s)"
                parameters['sap_denominations'] = [f"%{d}%" for d in sap_location_denominations]

            sql += " ORDER BY e.name ASC"

        else:
            # Para outras intenções ou intenção geral, retornar consulta genérica
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
        
        # Penalização se não há entidades relevantes para a intenção
        relevant_entities_for_intent = {
            QueryIntent.EQUIPMENT_SEARCH: [QueryEntity.EQUIPMENT_TYPE, QueryEntity.EQUIPMENT_ID],
            QueryIntent.MAINTENANCE_HISTORY: [QueryEntity.EQUIPMENT_ID, QueryEntity.MAINTENANCE_TYPE],
            QueryIntent.UPCOMING_MAINTENANCE: [QueryEntity.EQUIPMENT_TYPE, QueryEntity.EQUIPMENT_ID, QueryEntity.MAINTENANCE_TYPE, QueryEntity.TIME_PERIOD, QueryEntity.SAP_LOCATION_ABBREVIATION, QueryEntity.SAP_LOCATION_CODE],
            QueryIntent.PMM2_PLAN_SEARCH: [QueryEntity.PLAN_CODE, QueryEntity.WORK_CENTER, QueryEntity.SAP_LOCATION_CODE, QueryEntity.SAP_LOCATION_ABBREVIATION],
            QueryIntent.SAP_LOCATION_SEARCH: [QueryEntity.SAP_LOCATION_CODE, QueryEntity.SAP_LOCATION_DENOMINATION, QueryEntity.SAP_LOCATION_ABBREVIATION, QueryEntity.REGION],
            QueryIntent.EQUIPMENT_BY_LOCATION: [QueryEntity.SAP_LOCATION_CODE, QueryEntity.EQUIPMENT_TYPE, QueryEntity.SAP_LOCATION_ABBREVIATION],
            QueryIntent.FAILURE_ANALYSIS: [QueryEntity.EQUIPMENT_TYPE, QueryEntity.EQUIPMENT_ID, QueryEntity.TIME_PERIOD],
            QueryIntent.EQUIPMENT_STATUS: [QueryEntity.EQUIPMENT_TYPE, QueryEntity.EQUIPMENT_ID, QueryEntity.SAP_LOCATION_CODE, QueryEntity.SAP_LOCATION_ABBREVIATION]
            # Add other specific intents and their relevant entities
        }

        if intent in relevant_entities_for_intent:
            if not any(e.type in relevant_entities_for_intent[intent] for e in entities):
                base_confidence -= 0.1 # Slight penalty if core entities for this intent are missing

        # Penalização se não há entidades relevantes
        relevant_entities = [e for e in entities if e.type in [
            QueryEntity.EQUIPMENT_TYPE, QueryEntity.MAINTENANCE_TYPE, QueryEntity.TIME_PERIOD,
            QueryEntity.PLAN_CODE, QueryEntity.WORK_CENTER, QueryEntity.SAP_LOCATION_CODE,
            QueryEntity.SAP_LOCATION_DENOMINATION, QueryEntity.SAP_LOCATION_ABBREVIATION, QueryEntity.REGION
        ]]
        if not relevant_entities and intent != QueryIntent.GENERAL_QUERY:
            base_confidence -= 0.2
        
        return min(max(base_confidence, 0.0), 1.0)
    
    def _generate_suggestions(self, intent: QueryIntent, entities: List[ExtractedEntity]) -> List[str]:
        """Gera sugestões baseadas na análise."""
        suggestions = []
        
        # Generic suggestions based on entities found
        if any(e.type == QueryEntity.EQUIPMENT_ID for e in entities):
            equipment_id = next((e.value for e in entities if e.type == QueryEntity.EQUIPMENT_ID), 'TR-001')
            suggestions.append(f"Mostre todas as manutenções de {equipment_id}")
            suggestions.append(f"Qual o status atual de {equipment_id}?")
            suggestions.append(f"Última falha em {equipment_id}")
        if any(e.type == QueryEntity.SAP_LOCATION_CODE for e in entities) or \
           any(e.type == QueryEntity.SAP_LOCATION_ABBREVIATION for e in entities):
            location_id = next((e.value for e in entities if e.type in [QueryEntity.SAP_LOCATION_CODE, QueryEntity.SAP_LOCATION_ABBREVIATION]), 'UEM')
            suggestions.append(f"Quais equipamentos estão em {location_id}?")
            suggestions.append(f"Planos de manutenção para {location_id}")
            suggestions.append(f"Endereço de {location_id}") # if SAP_LOCATION_SEARCH
        if any(e.type == QueryEntity.WORK_CENTER for e in entities):
            work_center = next((e.value for e in entities if e.type == QueryEntity.WORK_CENTER), 'TTABDPM')
            suggestions.append(f"Planos de manutenção do centro de trabalho {work_center}")
        if any(e.type == QueryEntity.EQUIPMENT_TYPE for e in entities):
            equipment_type = next((e.value for e in entities if e.type == QueryEntity.EQUIPMENT_TYPE), 'Disjuntor')
            suggestions.append(f"Liste todos os {equipment_type}s")
            suggestions.append(f"Manutenções para {equipment_type}s")


        if intent == QueryIntent.UPCOMING_MAINTENANCE:
            suggestions.extend([
                "Liste todos os próximos testes operativos",
                "Quais manutenções estão agendadas para o próximo mês?",
                "Planos de manutenção para transformadores"
            ])
        elif intent == QueryIntent.LAST_MAINTENANCE:
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
        elif intent == QueryIntent.PMM2_PLAN_SEARCH:
            suggestions.extend([
                "Liste todos os planos de manutenção",
                "Planos de manutenção ativos",
                "Manutenções agendadas para o próximo mês"
            ])
        elif intent == QueryIntent.SAP_LOCATION_SEARCH:
            suggestions.extend([
                "Liste todas as subestações",
                "Localidades por região",
                "Equipamentos em cada localidade"
            ])
        elif intent == QueryIntent.EQUIPMENT_BY_LOCATION:
            suggestions.extend([
                "Quantos equipamentos estão nesta localidade?",
                "Manutenções em andamento nesta localidade",
                "Falhas recentes nesta localidade"
            ])
        elif intent == QueryIntent.FAILURE_ANALYSIS:
            suggestions.extend([
                "Quais são as falhas mais comuns?",
                "Equipamentos com histórico de problemas",
                "Análise de padrões de falhas por período"
            ])
        elif intent == QueryIntent.GENERAL_QUERY:
            suggestions.extend([
                "Status dos equipamentos",
                "Últimas manutenções realizadas",
                "Equipamentos que precisam de atenção",
                "Relatório de falhas recentes"
            ])

        else: # Default suggestions if no specific intent or if generic
            suggestions.extend([
                "Resumo geral do sistema",
                "Equipamentos críticos",
                "Próximas manutenções"
            ])
        
        # Remove duplicates and limit
        unique_suggestions = list(dict.fromkeys(suggestions))
        return unique_suggestions[:5]  # Limit to 5 suggestions