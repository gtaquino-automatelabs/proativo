"""
Sistema de templates de prompt para diferentes tipos de consulta.

Este módulo implementa templates especializados para cada tipo de consulta,
otimizados para o domínio de manutenção de equipamentos elétricos.
"""

from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass
import logging

from ...utils.logger import get_logger

# Configurar logger
logger = get_logger(__name__)


class PromptType(Enum):
    """Tipos de prompt disponíveis."""
    EQUIPMENT_STATUS = "equipment_status"
    MAINTENANCE_SCHEDULE = "maintenance_schedule" 
    FAILURE_ANALYSIS = "failure_analysis"
    COST_ANALYSIS = "cost_analysis"
    HISTORICAL_DATA = "historical_data"
    GENERAL_SEARCH = "general_search"
    SYSTEM_HEALTH = "system_health"


@dataclass
class PromptTemplate:
    """Template de prompt com metadados."""
    name: str
    system_prompt: str
    user_template: str
    context_template: str
    examples: List[str]
    parameters: Dict[str, Any]


class PromptTemplateService:
    """
    Serviço de templates de prompt especializado.
    
    Responsabilidades:
    - Geração de prompts baseados no tipo de consulta
    - Integração com contexto RAG
    - Formatação de exemplos e instruções
    - Otimização para domínio específico
    """
    
    def __init__(self):
        """Inicializa o serviço de templates."""
        self.templates: Dict[PromptType, PromptTemplate] = {}
        self._load_templates()
        
        logger.info("PromptTemplateService inicializado com sucesso")
    
    def _load_templates(self) -> None:
        """Carrega todos os templates de prompt."""
        
        # Template para status de equipamentos
        self.templates[PromptType.EQUIPMENT_STATUS] = PromptTemplate(
            name="Status de Equipamentos",
            system_prompt="""Você é um especialista em manutenção de equipamentos elétricos industriais.
Sua função é analisar e reportar o status atual de equipamentos baseado nos dados fornecidos.

INSTRUÇÕES:
- Analise os dados de equipamentos fornecidos no contexto
- Forneça informações precisas sobre status operacional
- Identifique equipamentos que precisam de atenção
- Use linguagem técnica mas acessível
- Sempre cite os IDs dos equipamentos mencionados
- Se não houver dados suficientes, seja transparente sobre as limitações

FORMATO DE RESPOSTA:
- Status atual do(s) equipamento(s)
- Observações técnicas relevantes
- Recomendações se aplicável
- Próximas ações sugeridas""",
            
            user_template="""Com base no contexto fornecido, responda à seguinte consulta sobre status de equipamentos:

CONSULTA: {query}

{context}

Forneça uma análise detalhada do status dos equipamentos mencionados.""",
            
            context_template="""DADOS DE EQUIPAMENTOS:
{rag_context}""",
            
            examples=[
                "Qual o status do transformador T001?",
                "Liste equipamentos operacionais na subestação norte",
                "Mostre equipamentos que precisam de manutenção urgente"
            ],
            
            parameters={
                "temperature": 0.3,
                "max_tokens": 800,
                "focus": "precision"
            }
        )
        
        # Template para programação de manutenção
        self.templates[PromptType.MAINTENANCE_SCHEDULE] = PromptTemplate(
            name="Programação de Manutenção",
            system_prompt="""Você é um especialista em planejamento de manutenção preventiva e corretiva.
Sua função é analisar cronogramas, prioridades e recursos para manutenção de equipamentos.

INSTRUÇÕES:
- Analise dados de manutenção programada e histórica
- Considere prioridades baseadas em criticidade e idade do equipamento
- Identifique conflitos de agenda e recursos
- Sugira otimizações no cronograma quando apropriado
- Sempre inclua datas, custos estimados e recursos necessários
- Considere impacto operacional das manutenções

FORMATO DE RESPOSTA:
- Cronograma de manutenções
- Priorização por criticidade
- Recursos necessários (técnicos, peças, tempo)
- Custos estimados
- Observações sobre otimização""",
            
            user_template="""Com base no contexto de manutenções, responda à consulta:

CONSULTA: {query}

{context}

Forneça um plano detalhado considerando cronograma, recursos e prioridades.""",
            
            context_template="""DADOS DE MANUTENÇÃO:
{rag_context}""",
            
            examples=[
                "Quais manutenções estão agendadas para esta semana?",
                "Cronograma de manutenção preventiva do transformador T001",
                "Otimize o cronograma de manutenções do próximo mês"
            ],
            
            parameters={
                "temperature": 0.4,
                "max_tokens": 1000,
                "focus": "planning"
            }
        )
        
        # Template para análise de falhas
        self.templates[PromptType.FAILURE_ANALYSIS] = PromptTemplate(
            name="Análise de Falhas",
            system_prompt="""Você é um especialista em análise de falhas de equipamentos elétricos industriais.
Sua função é investigar, diagnosticar e recomendar soluções para falhas e problemas.

INSTRUÇÕES:
- Analise padrões de falha e histórico de problemas
- Identifique causas raiz quando possível
- Correlacione falhas similares ou recorrentes
- Avalie impacto e severidade dos problemas
- Sugira ações corretivas e preventivas específicas
- Considere aspectos de segurança

FORMATO DE RESPOSTA:
- Descrição da(s) falha(s)
- Análise de causa raiz
- Padrões identificados
- Impacto operacional
- Recomendações de reparo
- Medidas preventivas futuras""",
            
            user_template="""Analise as falhas reportadas e responda à consulta:

CONSULTA: {query}

{context}

Forneça uma análise técnica completa com diagnóstico e recomendações.""",
            
            context_template="""DADOS DE FALHAS:
{rag_context}""",
            
            examples=[
                "Analise as falhas recorrentes no gerador GER-123",
                "Qual foi a causa da falha crítica na subestação ontem?",
                "Identifique padrões de falha nos transformadores"
            ],
            
            parameters={
                "temperature": 0.2,
                "max_tokens": 1200,
                "focus": "analysis"
            }
        )
        
        # Template para análise de custos
        self.templates[PromptType.COST_ANALYSIS] = PromptTemplate(
            name="Análise de Custos",
            system_prompt="""Você é um especialista em análise financeira de operações de manutenção.
Sua função é analisar custos, otimizar orçamentos e fornecer insights econômicos.

INSTRUÇÕES:
- Analise custos de manutenção, reparos e operação
- Compare custos históricos e identifique tendências
- Calcule ROI de investimentos em manutenção preventiva
- Identifique oportunidades de economia
- Considere custos de parada não programada
- Forneça análises baseadas em dados quantitativos

FORMATO DE RESPOSTA:
- Resumo financeiro dos custos
- Análise de tendências e variações
- Comparações e benchmarks
- Oportunidades de otimização
- Recomendações econômicas
- Projeções e estimativas""",
            
            user_template="""Analise os dados financeiros e responda à consulta sobre custos:

CONSULTA: {query}

{context}

Forneça uma análise financeira detalhada com números específicos e tendências.""",
            
            context_template="""DADOS FINANCEIROS:
{rag_context}""",
            
            examples=[
                "Qual foi o custo total de manutenção no último trimestre?",
                "Analise a evolução dos custos de reparo dos transformadores",
                "Compare custos de manutenção preventiva vs corretiva"
            ],
            
            parameters={
                "temperature": 0.1,
                "max_tokens": 900,
                "focus": "financial"
            }
        )
        
        # Template para dados históricos
        self.templates[PromptType.HISTORICAL_DATA] = PromptTemplate(
            name="Análise Histórica",
            system_prompt="""Você é um especialista em análise de dados históricos de equipamentos industriais.
Sua função é identificar tendências, padrões e insights baseados em dados temporais.

INSTRUÇÕES:
- Analise séries temporais de dados operacionais
- Identifique tendências de longo prazo
- Correlacione eventos e padrões sazonais
- Compare períodos diferentes
- Identifique melhorias ou degradações
- Base recomendações em evidências históricas

FORMATO DE RESPOSTA:
- Tendências identificadas
- Comparações temporais
- Padrões sazonais ou cíclicos
- Pontos de inflexão importantes
- Lições aprendidas
- Projeções baseadas em histórico""",
            
            user_template="""Analise os dados históricos e responda à consulta:

CONSULTA: {query}

{context}

Forneça uma análise temporal com identificação de tendências e padrões.""",
            
            context_template="""DADOS HISTÓRICOS:
{rag_context}""",
            
            examples=[
                "Como evoluiu a confiabilidade dos equipamentos nos últimos 2 anos?",
                "Identifique tendências de falha por tipo de equipamento",
                "Compare performance operacional entre trimestres"
            ],
            
            parameters={
                "temperature": 0.3,
                "max_tokens": 1000,
                "focus": "trends"
            }
        )
        
        # Template para busca geral
        self.templates[PromptType.GENERAL_SEARCH] = PromptTemplate(
            name="Busca Geral",
            system_prompt="""Você é um assistente especializado em sistemas de equipamentos elétricos industriais.
Sua função é responder consultas gerais fornecendo informações precisas e úteis.

INSTRUÇÕES:
- Responda de forma clara e objetiva
- Use os dados fornecidos no contexto
- Se não houver informações suficientes, seja transparente
- Sugira como obter informações adicionais se necessário
- Mantenha foco no domínio de equipamentos elétricos
- Forneça respostas práticas e acionáveis

FORMATO DE RESPOSTA:
- Resposta direta à consulta
- Informações de suporte relevantes
- Sugestões de próximos passos se aplicável
- Referências aos dados utilizados""",
            
            user_template="""Responda à seguinte consulta baseando-se no contexto disponível:

CONSULTA: {query}

{context}

Forneça uma resposta completa e útil.""",
            
            context_template="""INFORMAÇÕES DISPONÍVEIS:
{rag_context}""",
            
            examples=[
                "Como está funcionando o sistema elétrico geral?",
                "Preciso de informações sobre equipamentos na região X",
                "Qual o status geral das operações?"
            ],
            
            parameters={
                "temperature": 0.5,
                "max_tokens": 700,
                "focus": "general"
            }
        )
        
        # Template para saúde do sistema
        self.templates[PromptType.SYSTEM_HEALTH] = PromptTemplate(
            name="Saúde do Sistema",
            system_prompt="""Você é um especialista em monitoramento de saúde de sistemas elétricos industriais.
Sua função é avaliar o estado geral do sistema e identificar riscos ou oportunidades.

INSTRUÇÕES:
- Avalie a saúde geral do sistema de equipamentos
- Identifique indicadores de performance (KPIs)
- Sinalize alertas ou riscos potenciais
- Recomende ações proativas
- Considere aspectos de confiabilidade e disponibilidade
- Forneça visão sistêmica e holística

FORMATO DE RESPOSTA:
- Status geral do sistema
- Indicadores de performance chave
- Alertas e riscos identificados
- Recomendações preventivas
- Prioridades de ação""",
            
            user_template="""Avalie a saúde do sistema baseando-se nos dados disponíveis:

CONSULTA: {query}

{context}

Forneça uma avaliação abrangente da saúde do sistema.""",
            
            context_template="""DADOS DO SISTEMA:
{rag_context}""",
            
            examples=[
                "Como está a saúde geral do sistema elétrico?",
                "Identifique riscos no sistema de equipamentos",
                "Avalie a confiabilidade operacional atual"
            ],
            
            parameters={
                "temperature": 0.2,
                "max_tokens": 800,
                "focus": "health"
            }
        )
    
    def get_template(self, prompt_type: PromptType) -> PromptTemplate:
        """
        Obtém template para um tipo específico.
        
        Args:
            prompt_type: Tipo de prompt desejado
            
        Returns:
            PromptTemplate: Template correspondente
        """
        if prompt_type not in self.templates:
            logger.warning(f"Template não encontrado: {prompt_type}")
            return self.templates[PromptType.GENERAL_SEARCH]
        
        return self.templates[prompt_type]
    
    def generate_prompt(
        self,
        prompt_type: PromptType,
        query: str,
        rag_context: str = "",
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Gera prompt completo baseado no tipo e contexto.
        
        Args:
            prompt_type: Tipo de prompt
            query: Consulta do usuário
            rag_context: Contexto recuperado pelo RAG
            additional_context: Contexto adicional opcional
            
        Returns:
            Dict com system_prompt e user_prompt formatados
        """
        template = self.get_template(prompt_type)
        
        # Formatar contexto RAG
        formatted_context = ""
        if rag_context:
            formatted_context = template.context_template.format(
                rag_context=rag_context
            )
        
        # Formatar prompt do usuário
        user_prompt = template.user_template.format(
            query=query,
            context=formatted_context,
            **(additional_context or {})
        )
        
        logger.info("Prompt gerado", extra={
            "prompt_type": prompt_type.value,
            "query_length": len(query),
            "context_length": len(rag_context)
        })
        
        return {
            "system_prompt": template.system_prompt,
            "user_prompt": user_prompt,
            "parameters": template.parameters
        }
    
    def get_examples(self, prompt_type: PromptType) -> List[str]:
        """
        Obtém exemplos de consultas para um tipo.
        
        Args:
            prompt_type: Tipo de prompt
            
        Returns:
            Lista de exemplos de consulta
        """
        template = self.get_template(prompt_type)
        return template.examples.copy()
    
    def get_all_examples(self) -> Dict[str, List[str]]:
        """
        Obtém todos os exemplos organizados por tipo.
        
        Returns:
            Dict com exemplos por tipo de prompt
        """
        return {
            prompt_type.value: template.examples
            for prompt_type, template in self.templates.items()
        }
    
    def optimize_for_model(
        self,
        prompt_type: PromptType,
        model_name: str = "gemini-2.5-flash"
    ) -> Dict[str, Any]:
        """
        Otimiza parâmetros para modelo específico.
        
        Args:
            prompt_type: Tipo de prompt
            model_name: Nome do modelo LLM
            
        Returns:
            Parâmetros otimizados para o modelo
        """
        template = self.get_template(prompt_type)
        base_params = template.parameters.copy()
        
        # Otimizações específicas para Gemini
        if "gemini" in model_name.lower():
            # Gemini funciona bem com temperaturas ligeiramente mais altas
            if base_params.get("temperature", 0.3) < 0.2:
                base_params["temperature"] = 0.2
            
            # Ajustar max_tokens para limites do Gemini
            if base_params.get("max_tokens", 800) > 2048:
                base_params["max_tokens"] = 2048
        
        return base_params
    
    def validate_prompt_length(
        self,
        system_prompt: str,
        user_prompt: str,
        max_length: int = 4000
    ) -> bool:
        """
        Valida se o prompt está dentro dos limites.
        
        Args:
            system_prompt: Prompt do sistema
            user_prompt: Prompt do usuário
            max_length: Comprimento máximo permitido
            
        Returns:
            True se válido, False caso contrário
        """
        total_length = len(system_prompt) + len(user_prompt)
        
        if total_length > max_length:
            logger.warning(f"Prompt muito longo: {total_length} > {max_length}")
            return False
        
        return True
    
    def get_template_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Obtém informações sobre todos os templates.
        
        Returns:
            Dict com informações de cada template
        """
        return {
            prompt_type.value: {
                "name": template.name,
                "examples_count": len(template.examples),
                "parameters": template.parameters,
                "system_prompt_length": len(template.system_prompt),
                "user_template_length": len(template.user_template)
            }
            for prompt_type, template in self.templates.items()
        } 