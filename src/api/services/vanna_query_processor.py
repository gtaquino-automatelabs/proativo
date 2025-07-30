"""
Processador híbrido que combina Vanna.ai com o sistema de queries estático.

Este módulo implementa uma abordagem híbrida:
1. Tenta gerar SQL usando Vanna.ai (inteligente)
2. Se falhar ou confiança baixa, usa QueryProcessor original (fallback)
3. Aprende com feedback do usuário
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

from .vanna_service import get_vanna_service, VannaResponse
from .query_processor import QueryProcessor, QueryAnalysis, QueryIntent
from ..config import get_settings

logger = logging.getLogger(__name__)

@dataclass
class HybridQueryResult:
    """Resultado do processamento híbrido de query."""
    sql_query: Optional[str]
    parameters: Dict[str, Any]
    confidence_score: float
    processing_method: str  # "vanna", "fallback", "hybrid"
    vanna_response: Optional[VannaResponse]
    fallback_analysis: Optional[QueryAnalysis]
    explanation: Optional[str]
    suggestions: List[str]
    processing_time: float

class VannaQueryProcessor:
    """
    Processador híbrido que combina Vanna.ai com QueryProcessor tradicional.
    
    Estratégia:
    1. Primeiro tenta Vanna.ai para gerar SQL inteligente
    2. Se confiança < threshold, usa sistema tradicional como fallback
    3. Coleta feedback para melhoria contínua
    """
    
    def __init__(self, confidence_threshold: float = None):
        """
        Inicializa o processador híbrido.
        
        Args:
            confidence_threshold: Limite mínimo de confiança para usar Vanna (0.0-1.0)
        """
        self.settings = get_settings()
        self.confidence_threshold = confidence_threshold or self.settings.vanna_confidence_threshold
        self.vanna_service = get_vanna_service()
        self.fallback_processor = QueryProcessor()
        
        # Métricas de uso
        self.usage_stats = {
            'vanna_success': 0,
            'fallback_used': 0,
            'hybrid_used': 0,
            'total_queries': 0
        }
    
    async def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> QueryAnalysis:
        """
        Processa uma consulta usando abordagem híbrida.
        
        Args:
            query: Consulta do usuário em português
            context: Contexto adicional (filtros, localização, etc.)
            
        Returns:
            QueryAnalysis com SQL e metadata do processamento
        """
        start_time = datetime.now()
        self.usage_stats['total_queries'] += 1
        
        logger.info(f"Processing hybrid query: {query[:100]}...")
        
        # Fase 1: Tentar Vanna.ai primeiro
        # Usar método completo se confiança for alta o suficiente para workflow completo
        # Threshold temporariamente baixo para testar fluxo completo
        use_complete_workflow = self.confidence_threshold >= 0.6
        
        if use_complete_workflow and hasattr(self.vanna_service, 'ask_complete'):
            try:
                logger.info("Attempting Vanna.ai complete workflow")
                complete_response = await self.vanna_service.ask_complete(query, context)
                
                if complete_response.confidence >= self.confidence_threshold and not complete_response.error:
                    # Vanna complete workflow teve sucesso
                    result = await self._create_complete_vanna_result(
                        query, complete_response, start_time
                    )
                    self.usage_stats['vanna_success'] += 1
                    logger.info(f"Query processed with Vanna.ai complete workflow (confidence: {complete_response.confidence:.2f})")
                    
                    # Converter e retornar
                    return self._convert_to_query_analysis(result, query)
                    
            except Exception as complete_error:
                logger.warning(f"Vanna complete workflow failed, falling back to SQL-only: {complete_error}")
        
        # Fallback: usar apenas geração de SQL (método atual)
        vanna_response = await self.vanna_service.generate_sql(query, context)
        
        # Fase 2: Avaliar confiança e decidir estratégia
        if (vanna_response.confidence >= self.confidence_threshold and 
            vanna_response.sql and 
            not vanna_response.error):
            
            # Vanna teve sucesso - usar resultado
            result = await self._create_vanna_result(
                query, vanna_response, start_time
            )
            self.usage_stats['vanna_success'] += 1
            logger.info(f"Query processed with Vanna.ai (confidence: {vanna_response.confidence:.2f})")
            
        else:
            # Vanna falhou ou confiança baixa - usar fallback
            fallback_analysis = await self.fallback_processor.process_query(query)
            
            if fallback_analysis.sql_query:
                # Fallback funcionou
                result = await self._create_fallback_result(
                    query, fallback_analysis, vanna_response, start_time
                )
                self.usage_stats['fallback_used'] += 1
                logger.info(f"Query processed with fallback (Vanna confidence: {vanna_response.confidence:.2f})")
                
            else:
                # Ambos falharam - resultado híbrido com explicação
                result = await self._create_failed_result(
                    query, vanna_response, fallback_analysis, start_time
                )
                logger.warning(f"Both Vanna and fallback failed for query: {query[:50]}...")
        
        # Converter HybridQueryResult para QueryAnalysis (compatibilidade com chat.py)
        return self._convert_to_query_analysis(result, query)
    
    def _convert_to_query_analysis(self, hybrid_result: HybridQueryResult, original_query: str = "") -> QueryAnalysis:
        """
        Converte HybridQueryResult para QueryAnalysis para compatibilidade com chat.py.
        
        Args:
            hybrid_result: Resultado do processamento híbrido
            original_query: Query original do usuário
            
        Returns:
            QueryAnalysis: Análise de consulta no formato esperado pelo chat
        """
        # Determinar intent baseado no processamento usado
        if hybrid_result.fallback_analysis:
            # Se usou fallback, usar o intent do fallback
            intent = hybrid_result.fallback_analysis.intent
            entities = hybrid_result.fallback_analysis.entities
            temporal_context = hybrid_result.fallback_analysis.temporal_context
            query_source = hybrid_result.fallback_analysis.original_query
        else:
            # Se usou Vanna, inferir intent ou usar GENERAL_QUERY
            intent = QueryIntent.GENERAL_QUERY  # Default - pode ser melhorado
            entities = []  # Vanna não retorna entidades estruturadas
            temporal_context = None
            query_source = original_query  # Usar a query original passada
            
            logger.info(f"Query source: {query_source}, sql: {hybrid_result.sql_query}")
        
        return QueryAnalysis(
            original_query=query_source or original_query,
            intent=intent,
            entities=entities,
            temporal_context=temporal_context,
            sql_query=hybrid_result.sql_query,
            parameters=hybrid_result.parameters,
            confidence_score=hybrid_result.confidence_score,
            suggestions=hybrid_result.suggestions,
            processing_method=hybrid_result.processing_method,
            explanation=hybrid_result.explanation
        )
    
    async def _create_vanna_result(
        self, 
        query: str, 
        vanna_response: VannaResponse, 
        start_time: datetime
    ) -> HybridQueryResult:
        """Cria resultado baseado na resposta do Vanna."""
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return HybridQueryResult(
            sql_query=vanna_response.sql,
            parameters={},  # Vanna já inclui parâmetros no SQL
            confidence_score=vanna_response.confidence,
            processing_method="vanna",
            vanna_response=vanna_response,
            fallback_analysis=None,
            explanation=vanna_response.explanation,
            suggestions=self._generate_vanna_suggestions(query, vanna_response),
            processing_time=processing_time
        )
    
    async def _create_complete_vanna_result(
        self, 
        query: str, 
        complete_response, # VannaCompleteResponse
        start_time: datetime
    ) -> HybridQueryResult:
        """Cria resultado baseado na resposta completa do Vanna (método ask)."""
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return HybridQueryResult(
            sql_query=complete_response.sql,
            parameters={},  # Vanna já processou tudo internamente
            confidence_score=complete_response.confidence,
            processing_method="vanna_complete",
            vanna_response=None,  # Não precisamos do VannaResponse parcial
            fallback_analysis=None,
            explanation=complete_response.natural_language_response,
            suggestions=complete_response.followup_questions or [],
            processing_time=processing_time
        )
    
    async def _create_fallback_result(
        self, 
        query: str, 
        fallback_analysis: QueryAnalysis,
        vanna_response: VannaResponse,
        start_time: datetime
    ) -> HybridQueryResult:
        """Cria resultado baseado no fallback."""
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return HybridQueryResult(
            sql_query=fallback_analysis.sql_query,
            parameters=fallback_analysis.parameters,
            confidence_score=fallback_analysis.confidence_score,
            processing_method="fallback",
            vanna_response=vanna_response,
            fallback_analysis=fallback_analysis,
            explanation=f"Usando sistema de análise tradicional: {fallback_analysis.intent.value}",
            suggestions=fallback_analysis.suggestions,
            processing_time=processing_time
        )
    
    async def _create_failed_result(
        self,
        query: str,
        vanna_response: VannaResponse,
        fallback_analysis: QueryAnalysis,
        start_time: datetime
    ) -> HybridQueryResult:
        """Cria resultado quando ambos os métodos falham."""
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return HybridQueryResult(
            sql_query=None,
            parameters={},
            confidence_score=0.0,
            processing_method="failed",
            vanna_response=vanna_response,
            fallback_analysis=fallback_analysis,
            explanation="Não foi possível processar a consulta. Tente reformular a pergunta.",
            suggestions=[
                "Tente ser mais específico sobre o que deseja consultar",
                "Use termos como 'equipamentos', 'manutenções', 'falhas'",
                "Mencione tipos específicos: transformador, disjuntor, etc.",
                "Inclua informações de tempo: 'último mês', 'este ano', etc."
            ],
            processing_time=processing_time
        )
    
    def _generate_vanna_suggestions(
        self, 
        query: str, 
        vanna_response: VannaResponse
    ) -> List[str]:
        """Gera sugestões baseadas na resposta do Vanna."""
        suggestions = []
        
        if vanna_response.related_data:
            suggestions.append("Consulta relacionada encontrada no histórico")
        
        if vanna_response.confidence < 0.9:
            suggestions.extend([
                "Tente ser mais específico na sua pergunta",
                "Adicione contexto sobre período de tempo",
                "Especifique tipo de equipamento se relevante"
            ])
        
        return suggestions
    
    async def learn_from_feedback(
        self, 
        original_query: str,
        generated_sql: str,
        user_feedback: Dict[str, Any]
    ) -> bool:
        """
        Aprende com feedback do usuário para melhorar futuras respostas.
        
        Args:
            original_query: Pergunta original do usuário
            generated_sql: SQL que foi gerado
            user_feedback: Feedback do usuário (útil: bool, comentários: str, etc.)
            
        Returns:
            True se feedback foi processado com sucesso
        """
        try:
            is_helpful = user_feedback.get('helpful', False)
            
            if is_helpful and self.vanna_service.is_initialized:
                # Feedback positivo - treinar Vanna com este exemplo
                self.vanna_service.vanna.train(
                    question=original_query,
                    sql=generated_sql
                )
                logger.info(f"Trained Vanna with positive feedback: {original_query[:50]}...")
                
            elif not is_helpful:
                # Feedback negativo - marcar para revisão
                logger.warning(f"Negative feedback received for query: {original_query[:50]}...")
                # Aqui poderia implementar um sistema de revisão manual
                
            return True
            
        except Exception as e:
            logger.error(f"Error processing feedback: {e}")
            return False
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas de uso do processador híbrido."""
        total = self.usage_stats['total_queries']
        if total == 0:
            return self.usage_stats
        
        return {
            **self.usage_stats,
            'vanna_success_rate': self.usage_stats['vanna_success'] / total,
            'fallback_usage_rate': self.usage_stats['fallback_used'] / total,
            'success_rate': (self.usage_stats['vanna_success'] + self.usage_stats['fallback_used']) / total
        }
    
    def update_confidence_threshold(self, new_threshold: float):
        """Atualiza o limite de confiança para usar Vanna."""
        if 0.0 <= new_threshold <= 1.0:
            self.confidence_threshold = new_threshold
            logger.info(f"Updated confidence threshold to {new_threshold}")
        else:
            raise ValueError("Confidence threshold must be between 0.0 and 1.0")

# Instância global do processador híbrido
_hybrid_processor = None

def get_vanna_query_processor() -> VannaQueryProcessor:
    """Retorna instância singleton do VannaQueryProcessor."""
    global _hybrid_processor
    if _hybrid_processor is None:
        _hybrid_processor = VannaQueryProcessor()
    return _hybrid_processor 