"""
Sistema elaborado de prompts com schema completo para geração SQL.

Este módulo fornece prompts detalhados e contextualizados sobre o domínio
de manutenção de equipamentos elétricos, incluindo schema completo do banco,
exemplos específicos do domínio e melhores práticas SQL.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import json

from ...utils.logger import get_logger

# Configurar logger
logger = get_logger(__name__)


class QueryCategory(Enum):
    """Categorias de queries para prompts especializados."""
    STATUS = "status_equipamentos"
    MAINTENANCE = "manutencao"
    ANALYSIS = "analise_dados"
    COSTS = "custos_financeiro"
    TIMELINE = "linha_tempo"
    RANKING = "ranking_comparacao"
    PREDICTIVE = "analise_preditiva"
    AUDIT = "auditoria_compliance"


@dataclass
class SchemaTable:
    """Representação de uma tabela do schema."""
    name: str
    description: str
    columns: List[Dict[str, str]]
    relationships: List[str]
    business_rules: List[str]
    common_queries: List[str]


class LLMSchemaPrompts:
    """
    Sistema de prompts elaborado com contexto completo do domínio.
    
    Fornece:
    - Schema detalhado do banco de dados
    - Contexto do domínio de manutenção elétrica
    - Exemplos específicos por categoria
    - Regras de negócio importantes
    - Melhores práticas SQL
    """
    
    def __init__(self):
        """Inicializa o sistema de prompts."""
        self.schema_tables = self._build_schema_tables()
        self.domain_context = self._build_domain_context()
        self.category_prompts = self._build_category_prompts()
        self.sql_best_practices = self._build_sql_best_practices()
        
        logger.info("LLMSchemaPrompts inicializado com schema completo")
    
    def _build_schema_tables(self) -> Dict[str, SchemaTable]:
        """Constrói representação detalhada das tabelas."""
        return {
            "equipments": SchemaTable(
                name="equipments",
                description="Tabela principal de equipamentos/ativos elétricos do sistema",
                columns=[
                    {"name": "id", "type": "UUID", "desc": "Identificador único do equipamento"},
                    {"name": "code", "type": "VARCHAR(50)", "desc": "Código do equipamento (ex: TR-001, DJ-042)"},
                    {"name": "name", "type": "VARCHAR(200)", "desc": "Nome descritivo do equipamento"},
                    {"name": "description", "type": "TEXT", "desc": "Descrição detalhada"},
                    {"name": "equipment_type", "type": "VARCHAR(50)", "desc": "Tipo: Transformer, Circuit Breaker, Motor, Generator"},
                    {"name": "category", "type": "VARCHAR(50)", "desc": "Categoria adicional do equipamento"},
                    {"name": "criticality", "type": "VARCHAR(20)", "desc": "Criticidade: High, Medium, Low"},
                    {"name": "location", "type": "VARCHAR(200)", "desc": "Localização física do equipamento"},
                    {"name": "substation", "type": "VARCHAR(100)", "desc": "Subestação onde está instalado"},
                    {"name": "manufacturer", "type": "VARCHAR(100)", "desc": "Fabricante (ex: ABB, Siemens, WEG)"},
                    {"name": "model", "type": "VARCHAR(100)", "desc": "Modelo do equipamento"},
                    {"name": "serial_number", "type": "VARCHAR(100)", "desc": "Número de série único"},
                    {"name": "manufacturing_year", "type": "INTEGER", "desc": "Ano de fabricação (1900-atual)"},
                    {"name": "installation_date", "type": "TIMESTAMP", "desc": "Data de instalação"},
                    {"name": "rated_voltage", "type": "NUMERIC(10,2)", "desc": "Tensão nominal em kV"},
                    {"name": "rated_power", "type": "NUMERIC(10,2)", "desc": "Potência nominal em MVA"},
                    {"name": "rated_current", "type": "NUMERIC(10,2)", "desc": "Corrente nominal em A"},
                    {"name": "status", "type": "VARCHAR(20)", "desc": "Status: Active, Inactive, Maintenance, Retired"},
                    {"name": "is_critical", "type": "BOOLEAN", "desc": "Se é equipamento crítico para operação"},
                    {"name": "metadata_json", "type": "JSONB", "desc": "Dados adicionais em JSON"},
                    {"name": "created_at", "type": "TIMESTAMP", "desc": "Data de criação do registro"},
                    {"name": "updated_at", "type": "TIMESTAMP", "desc": "Data da última atualização"}
                ],
                relationships=[
                    "equipments.id → maintenances.equipment_id (1:N)",
                    "equipments.id → data_history.equipment_id (1:N)"
                ],
                business_rules=[
                    "Código do equipamento é único e segue padrão: TIPO-NÚMERO",
                    "Criticidade afeta prioridade de manutenção",
                    "Status 'Retired' significa fora de operação permanentemente",
                    "Equipamentos críticos (is_critical=true) têm SLA diferenciado"
                ],
                common_queries=[
                    "Equipamentos por tipo e status",
                    "Equipamentos críticos em operação",
                    "Equipamentos por subestação",
                    "Idade dos equipamentos (anos desde instalação)"
                ]
            ),
            
            "maintenances": SchemaTable(
                name="maintenances",
                description="Registros de todas as manutenções realizadas ou planejadas",
                columns=[
                    {"name": "id", "type": "UUID", "desc": "Identificador único da manutenção"},
                    {"name": "equipment_id", "type": "UUID", "desc": "ID do equipamento (FK para equipments)"},
                    {"name": "maintenance_code", "type": "VARCHAR(50)", "desc": "Código da ordem de manutenção"},
                    {"name": "maintenance_type", "type": "VARCHAR(50)", "desc": "Tipo: Preventive, Corrective, Predictive, Emergency"},
                    {"name": "priority", "type": "VARCHAR(20)", "desc": "Prioridade: High, Medium, Low"},
                    {"name": "title", "type": "VARCHAR(200)", "desc": "Título/resumo da manutenção"},
                    {"name": "description", "type": "TEXT", "desc": "Descrição detalhada"},
                    {"name": "work_performed", "type": "TEXT", "desc": "Trabalho realizado"},
                    {"name": "scheduled_date", "type": "TIMESTAMP", "desc": "Data programada"},
                    {"name": "start_date", "type": "TIMESTAMP", "desc": "Data/hora de início"},
                    {"name": "completion_date", "type": "TIMESTAMP", "desc": "Data/hora de conclusão"},
                    {"name": "duration_hours", "type": "NUMERIC(8,2)", "desc": "Duração em horas"},
                    {"name": "status", "type": "VARCHAR(20)", "desc": "Status: Planned, InProgress, Completed, Cancelled"},
                    {"name": "result", "type": "VARCHAR(50)", "desc": "Resultado: Success, Partial, Failed"},
                    {"name": "technician", "type": "VARCHAR(100)", "desc": "Técnico responsável"},
                    {"name": "team", "type": "VARCHAR(200)", "desc": "Equipe responsável"},
                    {"name": "contractor", "type": "VARCHAR(100)", "desc": "Empresa contratada"},
                    {"name": "estimated_cost", "type": "NUMERIC(12,2)", "desc": "Custo estimado em R$"},
                    {"name": "actual_cost", "type": "NUMERIC(12,2)", "desc": "Custo real em R$"},
                    {"name": "parts_replaced", "type": "TEXT", "desc": "Peças substituídas"},
                    {"name": "materials_used", "type": "TEXT", "desc": "Materiais utilizados"},
                    {"name": "observations", "type": "TEXT", "desc": "Observações gerais"},
                    {"name": "requires_followup", "type": "BOOLEAN", "desc": "Se requer acompanhamento"},
                    {"name": "followup_date", "type": "TIMESTAMP", "desc": "Data de acompanhamento"},
                    {"name": "metadata_json", "type": "JSONB", "desc": "Dados adicionais"},
                    {"name": "created_at", "type": "TIMESTAMP", "desc": "Data de criação"},
                    {"name": "updated_at", "type": "TIMESTAMP", "desc": "Data de atualização"}
                ],
                relationships=[
                    "maintenances.equipment_id → equipments.id (N:1)"
                ],
                business_rules=[
                    "Manutenção Preventiva: programada regularmente",
                    "Manutenção Corretiva: após falha ou problema",
                    "Manutenção Preditiva: baseada em condição/dados",
                    "Emergency: urgente, afeta operação",
                    "Custo real pode diferir do estimado",
                    "Duration_hours calculado entre start_date e completion_date"
                ],
                common_queries=[
                    "Manutenções pendentes por prioridade",
                    "Histórico de manutenções por equipamento",
                    "Custos de manutenção por período",
                    "Taxa de sucesso por tipo de manutenção",
                    "Manutenções atrasadas (scheduled < hoje e status != Completed)"
                ]
            ),
            
            "data_history": SchemaTable(
                name="data_history",
                description="Histórico de medições, inspeções e eventos dos equipamentos",
                columns=[
                    {"name": "id", "type": "UUID", "desc": "Identificador único"},
                    {"name": "equipment_id", "type": "UUID", "desc": "ID do equipamento (FK)"},
                    {"name": "data_source", "type": "VARCHAR(50)", "desc": "Fonte: CSV, XML, XLSX, Manual, API"},
                    {"name": "data_type", "type": "VARCHAR(50)", "desc": "Tipo: Measurement, Inspection, Test, Event"},
                    {"name": "timestamp", "type": "TIMESTAMP", "desc": "Momento da medição/evento"},
                    {"name": "measurement_type", "type": "VARCHAR(100)", "desc": "Tipo de medição (Temperatura, Vibração, etc)"},
                    {"name": "measurement_value", "type": "NUMERIC(15,4)", "desc": "Valor numérico medido"},
                    {"name": "measurement_unit", "type": "VARCHAR(20)", "desc": "Unidade (°C, mm/s, etc)"},
                    {"name": "text_value", "type": "TEXT", "desc": "Valor textual ou observação"},
                    {"name": "condition_status", "type": "VARCHAR(50)", "desc": "Condição: Good, Warning, Critical, Unknown"},
                    {"name": "alert_level", "type": "VARCHAR(20)", "desc": "Alerta: Normal, Warning, Critical"},
                    {"name": "inspector", "type": "VARCHAR(100)", "desc": "Responsável pela medição"},
                    {"name": "collection_method", "type": "VARCHAR(50)", "desc": "Método: Automatic, Manual, Remote"},
                    {"name": "is_validated", "type": "BOOLEAN", "desc": "Se dados foram validados"},
                    {"name": "quality_score", "type": "NUMERIC(3,2)", "desc": "Score de qualidade (0.00-1.00)"},
                    {"name": "created_at", "type": "TIMESTAMP", "desc": "Data de inserção"}
                ],
                relationships=[
                    "data_history.equipment_id → equipments.id (N:1)"
                ],
                business_rules=[
                    "Medições críticas geram alertas automáticos",
                    "Quality_score < 0.5 indica dados não confiáveis",
                    "Condition_status deriva de measurement_value e limites",
                    "Dados de inspeção manual requerem validação"
                ],
                common_queries=[
                    "Últimas medições por equipamento",
                    "Tendência de temperatura ao longo do tempo",
                    "Alertas críticos não resolvidos",
                    "Qualidade dos dados por fonte"
                ]
            ),
            
            "user_feedback": SchemaTable(
                name="user_feedback",
                description="Feedback dos usuários sobre respostas do sistema",
                columns=[
                    {"name": "id", "type": "UUID", "desc": "Identificador único"},
                    {"name": "session_id", "type": "UUID", "desc": "ID da sessão do usuário"},
                    {"name": "message_id", "type": "UUID", "desc": "ID da mensagem avaliada"},
                    {"name": "rating", "type": "INTEGER", "desc": "Avaliação 1-5 estrelas"},
                    {"name": "helpful", "type": "BOOLEAN", "desc": "Se foi útil (👍/👎)"},
                    {"name": "comment", "type": "TEXT", "desc": "Comentário do usuário"},
                    {"name": "original_query", "type": "TEXT", "desc": "Pergunta original"},
                    {"name": "feedback_category", "type": "VARCHAR(50)", "desc": "Categoria: accuracy, completeness, clarity, relevance"},
                    {"name": "created_at", "type": "TIMESTAMP", "desc": "Data do feedback"}
                ],
                relationships=[],
                business_rules=[
                    "Feedback negativo prioriza revisão de respostas",
                    "Rating < 3 indica insatisfação",
                    "Comentários são analisados para melhorias"
                ],
                common_queries=[
                    "Taxa de satisfação por período",
                    "Queries problemáticas mais comuns",
                    "Evolução da qualidade das respostas"
                ]
            )
        }
    
    def _build_domain_context(self) -> str:
        """Constrói contexto detalhado do domínio."""
        return """
CONTEXTO DO DOMÍNIO - MANUTENÇÃO DE EQUIPAMENTOS ELÉTRICOS:

Este sistema gerencia a manutenção de equipamentos elétricos de alta tensão em subestações e usinas.

TIPOS DE EQUIPAMENTOS:
- Transformadores (TR-XXX): Convertem tensão, críticos para distribuição
- Disjuntores (DJ-XXX): Proteção e seccionamento de circuitos
- Motores (MT-XXX): Acionamento de sistemas auxiliares
- Geradores (GR-XXX): Geração de energia elétrica

CRITICIDADE:
- Critical: Falha causa blackout ou parada total
- High: Falha afeta múltiplos sistemas
- Medium: Falha afeta sistema isolado
- Low: Falha tem impacto mínimo

TIPOS DE MANUTENÇÃO:
- Preventiva: Programada regularmente (mensal, trimestral, anual)
- Corretiva: Após falha ou defeito identificado
- Preditiva: Baseada em condição (vibração, temperatura, óleo)
- Emergência: Urgente para evitar falha catastrófica

MÉTRICAS IMPORTANTES:
- MTBF (Mean Time Between Failures): Tempo médio entre falhas
- MTTR (Mean Time To Repair): Tempo médio de reparo
- Disponibilidade: % tempo em operação
- Custo de manutenção por MVA instalado

NORMAS E REGULAMENTOS:
- NBR 5356: Transformadores de potência
- NBR 7118: Disjuntores de alta tensão
- NR-10: Segurança em instalações elétricas
- ONS: Procedimentos de rede

SAZONALIDADE:
- Maior demanda no verão (dezembro-março)
- Manutenções preferencialmente no inverno
- Paradas programadas em feriados prolongados
"""
    
    def _build_category_prompts(self) -> Dict[QueryCategory, str]:
        """Constrói prompts especializados por categoria."""
        return {
            QueryCategory.STATUS: """
Para consultas sobre STATUS DE EQUIPAMENTOS, considere:
- Status operacional atual (Active, Maintenance, etc)
- Criticidade e impacto na operação
- Localização e subestação
- Idade e vida útil esperada
- Próxima manutenção programada

Exemplos úteis:
- "Equipamentos críticos em manutenção"
- "Transformadores ativos por subestação"
- "Equipamentos próximos da aposentadoria (>25 anos)"
""",
            
            QueryCategory.MAINTENANCE: """
Para consultas sobre MANUTENÇÕES, considere:
- Tipo e prioridade da manutenção
- Status atual (Planned, InProgress, Completed)
- Datas programadas vs realizadas
- Equipe responsável e custos
- Resultado e necessidade de follow-up

Exemplos úteis:
- "Manutenções preventivas atrasadas"
- "Histórico de manutenções do transformador TR-001"
- "Taxa de sucesso das manutenções preditivas"
""",
            
            QueryCategory.ANALYSIS: """
Para ANÁLISES DE DADOS E TENDÊNCIAS, considere:
- Medições históricas (temperatura, vibração)
- Evolução de condições ao longo do tempo
- Correlações entre medições e falhas
- Qualidade dos dados coletados
- Alertas e anomalias

Exemplos úteis:
- "Tendência de temperatura dos transformadores"
- "Equipamentos com mais alertas críticos"
- "Correlação entre vibração e falhas"
""",
            
            QueryCategory.COSTS: """
Para análises de CUSTOS E FINANÇAS, considere:
- Custo estimado vs realizado
- Custos por tipo de manutenção
- Custos por tipo de equipamento
- ROI de manutenção preventiva vs corretiva
- Custos de peças e mão de obra

Exemplos úteis:
- "Custo total de manutenção este ano"
- "Equipamentos mais caros para manter"
- "Economia da manutenção preditiva"
""",
            
            QueryCategory.TIMELINE: """
Para consultas de LINHA DO TEMPO, considere:
- Histórico completo por equipamento
- Cronograma de manutenções futuras
- Tempo entre falhas (MTBF)
- Tempo de reparo (MTTR)
- Vida útil e obsolescência

Exemplos úteis:
- "Timeline de eventos do disjuntor DJ-042"
- "Manutenções programadas próximo trimestre"
- "Equipamentos sem manutenção há mais de 1 ano"
""",
            
            QueryCategory.RANKING: """
Para RANKINGS E COMPARAÇÕES, considere:
- Ordenação por criticidade, custo, falhas
- Comparações entre tipos de equipamento
- Benchmarking entre subestações
- Top N melhores/piores performers

Exemplos úteis:
- "Top 10 equipamentos com mais falhas"
- "Ranking de subestações por disponibilidade"
- "Técnicos com melhor taxa de sucesso"
""",
            
            QueryCategory.PREDICTIVE: """
Para ANÁLISES PREDITIVAS, considere:
- Previsão de falhas baseada em histórico
- Estimativa de vida útil remanescente
- Otimização de intervalos de manutenção
- Identificação de padrões de degradação

Exemplos úteis:
- "Equipamentos com risco de falha próximo mês"
- "Previsão de custos de manutenção 2025"
- "Otimização do calendário de preventivas"
""",
            
            QueryCategory.AUDIT: """
Para AUDITORIA E COMPLIANCE, considere:
- Conformidade com planos de manutenção
- Aderência a normas técnicas
- Rastreabilidade de intervenções
- Documentação e registros

Exemplos úteis:
- "Equipamentos sem inspeção obrigatória"
- "Manutenções realizadas sem ordem de serviço"
- "Compliance com NR-10 por subestação"
"""
        }
    
    def _build_sql_best_practices(self) -> str:
        """Define melhores práticas SQL para o domínio."""
        return """
MELHORES PRÁTICAS SQL PARA CONSULTAS:

1. JOINS EFICIENTES:
   - Use aliases curtos e significativos (e = equipments, m = maintenances)
   - Prefira LEFT JOIN quando nem todos equipamentos têm manutenções
   - Use INNER JOIN apenas quando a relação é obrigatória

2. FILTROS TEMPORAIS:
   - Use CURRENT_DATE para comparações com hoje
   - EXTRACT(YEAR FROM date) para filtrar por ano
   - date_field BETWEEN '2024-01-01' AND '2024-12-31' para períodos
   - AGE(CURRENT_DATE, date_field) para calcular idade

3. AGREGAÇÕES ÚTEIS:
   - COUNT(*) para total de registros
   - COUNT(DISTINCT field) para valores únicos
   - AVG(CASE WHEN condition THEN 1 ELSE 0 END) para percentuais
   - STRING_AGG(field, ', ') para concatenar textos

4. ORDENAÇÃO INTELIGENTE:
   - ORDER BY criticality_order (Critical=1, High=2, Medium=3, Low=4)
   - ORDER BY scheduled_date NULLS LAST
   - ORDER BY cost DESC para maiores valores primeiro

5. LIMITES PRÁTICOS:
   - Use LIMIT 10 para Top N queries
   - LIMIT 100 para listagens grandes
   - Sem LIMIT para contagens e somas

6. FORMATAÇÃO DE RESULTADOS:
   - TO_CHAR(date, 'DD/MM/YYYY') para datas brasileiras
   - ROUND(numeric, 2) para valores monetários
   - COALESCE(field, 'N/A') para tratar nulos
   - || para concatenar strings no PostgreSQL

7. PERFORMANCE:
   - Use índices existentes (equipment_type, status, scheduled_date)
   - Evite funções em colunas do WHERE quando possível
   - Prefira = sobre LIKE quando exato
   - Use EXISTS ao invés de IN para subqueries grandes
"""
    
    def get_base_prompt(self) -> str:
        """Retorna o prompt base com schema completo."""
        schema_text = self._format_schema_for_prompt()
        
        return f"""You are a PostgreSQL expert specialized in electrical equipment maintenance databases.

{self.domain_context}

DATABASE SCHEMA:
{schema_text}

{self.sql_best_practices}

Generate SQL queries that are:
- Accurate and efficient
- Use appropriate JOINs and relationships
- Include meaningful column aliases
- Follow PostgreSQL syntax strictly
- Optimized for the business context
"""
    
    def get_enhanced_prompt(self, query: str, category: Optional[QueryCategory] = None) -> str:
        """
        Retorna prompt enhanced com contexto específico.
        
        Args:
            query: Query do usuário
            category: Categoria da query (opcional)
            
        Returns:
            Prompt completo e contextualizado
        """
        base_prompt = self.get_base_prompt()
        
        # Detectar categoria se não fornecida
        if category is None:
            category = self._detect_category(query)
        
        # Adicionar contexto da categoria
        category_context = ""
        if category and category in self.category_prompts:
            category_context = f"\nCONTEXT FOR THIS QUERY TYPE:\n{self.category_prompts[category]}"
        
        # Adicionar exemplos relevantes
        examples = self._get_relevant_examples(query, category)
        examples_text = "\nRELEVANT EXAMPLES:\n" + "\n".join([
            f"Q: {ex['question']}\nSQL: {ex['sql']}" 
            for ex in examples
        ]) if examples else ""
        
        return f"""{base_prompt}
{category_context}
{examples_text}

IMPORTANT NOTES FOR THIS QUERY:
- Consider the business context and domain rules
- Use appropriate date ranges and filters
- Include helpful column aliases in Portuguese
- Sort results in the most useful order
- Consider NULL values appropriately

USER QUERY: {query}

Generate the SQL query:"""
    
    def _format_schema_for_prompt(self) -> str:
        """Formata o schema para inclusão no prompt."""
        schema_parts = []
        
        for table_name, table in self.schema_tables.items():
            # Cabeçalho da tabela
            schema_parts.append(f"\nTABLE: {table.name}")
            schema_parts.append(f"Description: {table.description}")
            
            # Colunas principais (não todas para não poluir)
            schema_parts.append("Key columns:")
            important_columns = [col for col in table.columns if 
                               col["name"] in ["id", "code", "name", "equipment_type", "status", 
                                             "criticality", "maintenance_type", "priority", "scheduled_date",
                                             "timestamp", "measurement_value", "condition_status"]]
            
            for col in important_columns:
                schema_parts.append(f"  - {col['name']} ({col['type']}): {col['desc']}")
            
            # Relacionamentos
            if table.relationships:
                schema_parts.append("Relationships:")
                for rel in table.relationships:
                    schema_parts.append(f"  - {rel}")
            
            # Regras de negócio (top 2)
            if table.business_rules:
                schema_parts.append("Key business rules:")
                for rule in table.business_rules[:2]:
                    schema_parts.append(f"  - {rule}")
        
        return "\n".join(schema_parts)
    
    def _detect_category(self, query: str) -> Optional[QueryCategory]:
        """Detecta a categoria da query baseado em palavras-chave."""
        query_lower = query.lower()
        
        # Mapeamento de palavras-chave para categorias
        category_keywords = {
            QueryCategory.STATUS: ["status", "situação", "estado", "operacional", "ativo", "inativo"],
            QueryCategory.MAINTENANCE: ["manutenção", "preventiva", "corretiva", "preditiva", "ordem"],
            QueryCategory.ANALYSIS: ["análise", "tendência", "evolução", "medição", "temperatura", "vibração"],
            QueryCategory.COSTS: ["custo", "valor", "gasto", "economia", "orçamento", "financeiro", "gastamos", "pagamos"],
            QueryCategory.TIMELINE: ["histórico", "timeline", "cronograma", "agenda", "calendário"],
            QueryCategory.RANKING: ["ranking", "top", "maiores", "menores", "comparar", "versus"],
            QueryCategory.PREDICTIVE: ["previsão", "prever", "futuro", "risco", "probabilidade"],
            QueryCategory.AUDIT: ["auditoria", "compliance", "conformidade", "norma", "inspeção"]
        }
        
        # Contar matches por categoria
        category_scores = {}
        for category, keywords in category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in query_lower)
            if score > 0:
                category_scores[category] = score
        
        # Regras especiais de priorização
        # Se tem palavras financeiras, priorizar COSTS mesmo que tenha "manutenção"
        if any(word in query_lower for word in ["custo", "gasto", "valor", "gastamos", "pagamos", "economia"]):
            if QueryCategory.COSTS in category_scores:
                category_scores[QueryCategory.COSTS] += 2  # Boost para termos financeiros
        
        # Retornar categoria com maior score
        if category_scores:
            return max(category_scores, key=category_scores.get)
        
        return None
    
    def _get_relevant_examples(self, query: str, category: Optional[QueryCategory]) -> List[Dict[str, str]]:
        """Retorna exemplos relevantes baseados na query e categoria."""
        examples = []
        
        # Exemplos gerais sempre úteis
        general_examples = [
            {
                "question": "Quantos equipamentos críticos estão em manutenção?",
                "sql": """SELECT COUNT(*) as total 
FROM equipments e 
WHERE e.criticality = 'Critical' 
AND e.status = 'Maintenance';"""
            },
            {
                "question": "Liste as próximas manutenções programadas",
                "sql": """SELECT e.name as equipamento, e.location, 
       m.maintenance_type as tipo, 
       m.scheduled_date as data_programada,
       m.priority as prioridade
FROM maintenances m
JOIN equipments e ON m.equipment_id = e.id
WHERE m.status = 'Planned' 
AND m.scheduled_date >= CURRENT_DATE
ORDER BY m.scheduled_date, m.priority;"""
            }
        ]
        
        # Exemplos específicos por categoria
        category_examples = {
            QueryCategory.STATUS: [
                {
                    "question": "Status dos transformadores por subestação",
                    "sql": """SELECT e.substation, e.status, COUNT(*) as quantidade
FROM equipments e
WHERE e.equipment_type = 'Transformer'
GROUP BY e.substation, e.status
ORDER BY e.substation, e.status;"""
                }
            ],
            QueryCategory.COSTS: [
                {
                    "question": "Custo total de manutenção por tipo este ano",
                    "sql": """SELECT m.maintenance_type as tipo_manutencao,
       COUNT(*) as quantidade,
       SUM(m.actual_cost) as custo_total,
       AVG(m.actual_cost) as custo_medio
FROM maintenances m
WHERE EXTRACT(YEAR FROM m.completion_date) = EXTRACT(YEAR FROM CURRENT_DATE)
AND m.actual_cost IS NOT NULL
GROUP BY m.maintenance_type
ORDER BY custo_total DESC;"""
                }
            ],
            QueryCategory.ANALYSIS: [
                {
                    "question": "Evolução da temperatura dos transformadores",
                    "sql": """SELECT e.name as transformador,
       DATE_TRUNC('month', d.timestamp) as mes,
       AVG(d.measurement_value) as temp_media,
       MAX(d.measurement_value) as temp_maxima
FROM data_history d
JOIN equipments e ON d.equipment_id = e.id
WHERE e.equipment_type = 'Transformer'
AND d.measurement_type = 'Temperature'
AND d.timestamp >= CURRENT_DATE - INTERVAL '6 months'
GROUP BY e.name, DATE_TRUNC('month', d.timestamp)
ORDER BY e.name, mes;"""
                }
            ]
        }
        
        # Adicionar exemplos relevantes
        if category and category in category_examples:
            examples.extend(category_examples[category])
        else:
            examples.extend(general_examples[:2])
        
        return examples
    
    def get_schema_summary(self) -> Dict[str, Any]:
        """Retorna resumo do schema para referência rápida."""
        return {
            "tables": list(self.schema_tables.keys()),
            "total_tables": len(self.schema_tables),
            "key_relationships": [
                "equipments ← maintenances (1:N)",
                "equipments ← data_history (1:N)"
            ],
            "main_entities": ["Equipamentos", "Manutenções", "Histórico de Dados", "Feedback"],
            "domain": "Manutenção de Equipamentos Elétricos"
        }
    
    def get_validation_rules(self) -> List[str]:
        """Retorna regras de validação importantes para SQL gerado."""
        return [
            "equipment_type deve ser um dos valores: Transformer, Circuit Breaker, Motor, Generator",
            "status de equipment: Active, Inactive, Maintenance, Retired",
            "criticality: Critical, High, Medium, Low",
            "maintenance_type: Preventive, Corrective, Predictive, Emergency",
            "maintenance status: Planned, InProgress, Completed, Cancelled",
            "Datas devem estar no formato ISO: YYYY-MM-DD",
            "Custos são armazenados em NUMERIC(12,2) para valores em R$",
            "IDs são UUIDs, não integers"
        ] 