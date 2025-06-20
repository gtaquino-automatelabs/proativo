"""
Sistema RAG (Retrieval Augmented Generation) para o PROAtivo.

Este módulo implementa a recuperação de contexto relevante baseado em
embeddings e similaridade semântica para enriquecer consultas ao LLM.
"""

import json
import hashlib
import asyncio
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ..config import get_settings
from ...database.repositories import EquipmentRepository, MaintenanceRepository
from ...utils.error_handlers import DataProcessingError, ValidationError
from ...utils.logger import get_logger

# Configurar logger
logger = get_logger(__name__)


@dataclass
class DocumentChunk:
    """Representa um chunk de documento com embedding."""
    id: str
    content: str
    source: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    relevance_score: float = 0.0


@dataclass
class RAGContext:
    """Contexto recuperado pelo sistema RAG."""
    query: str
    chunks: List[DocumentChunk]
    total_chunks: int
    retrieval_time: float
    context_summary: str
    relevance_threshold: float


class RAGService:
    """
    Sistema RAG para recuperação de contexto relevante.
    
    Implementa:
    - Indexação de documentos e dados
    - Geração de embeddings simples (TF-IDF simulado)
    - Busca por similaridade
    - Ranking e filtragem de resultados
    - Contextualização para LLM
    """
    
    def __init__(self):
        """Inicializa o serviço RAG."""
        self.settings = get_settings()
        
        # Cache de documentos e embeddings
        self.document_cache: Dict[str, DocumentChunk] = {}
        self.index_cache: Dict[str, List[float]] = {}
        
        # Configurações
        self.max_chunks_per_query = 5
        self.relevance_threshold = 0.3
        self.cache_ttl = 3600  # 1 hora
        
        # Métricas
        self.queries_processed = 0
        self.cache_hits = 0
        self.total_retrieval_time = 0.0
        
        # Índice de termos para busca
        self.term_index: Dict[str, List[str]] = {}
        
        logger.info("RAGService inicializado com sucesso")
    
    async def retrieve_context(
        self, 
        query: str, 
        query_type: Optional[str] = None,
        max_chunks: Optional[int] = None
    ) -> RAGContext:
        """
        Recupera contexto relevante para uma query.
        
        Args:
            query: Consulta do usuário
            query_type: Tipo da consulta (equipment, maintenance, etc.)
            max_chunks: Máximo de chunks a retornar
            
        Returns:
            RAGContext: Contexto recuperado com chunks relevantes
        """
        start_time = datetime.now()
        
        try:
            self.queries_processed += 1
            max_chunks = max_chunks or self.max_chunks_per_query
            
            # 1. Pré-processar query
            processed_query = self._preprocess_query(query)
            
            # 2. Buscar documentos relevantes
            relevant_chunks = await self._search_relevant_chunks(
                processed_query, query_type, max_chunks
            )
            
            # 3. Calcular scores de relevância
            scored_chunks = self._calculate_relevance_scores(
                processed_query, relevant_chunks
            )
            
            # 4. Filtrar por threshold
            filtered_chunks = [
                chunk for chunk in scored_chunks 
                if chunk.relevance_score >= self.relevance_threshold
            ]
            
            # 5. Gerar resumo do contexto
            context_summary = self._generate_context_summary(filtered_chunks)
            
            retrieval_time = (datetime.now() - start_time).total_seconds()
            self.total_retrieval_time += retrieval_time
            
            logger.info("Contexto recuperado com sucesso", extra={
                "query": query[:50],
                "chunks_found": len(filtered_chunks),
                "retrieval_time": retrieval_time
            })
            
            return RAGContext(
                query=query,
                chunks=filtered_chunks[:max_chunks],
                total_chunks=len(filtered_chunks),
                retrieval_time=retrieval_time,
                context_summary=context_summary,
                relevance_threshold=self.relevance_threshold
            )
            
        except Exception as e:
            logger.error(f"Erro ao recuperar contexto: {str(e)}", extra={
                "query": query[:50] if query else "empty"
            })
            raise DataProcessingError(f"Falha na recuperação de contexto: {str(e)}")
    
    async def index_data_sources(self) -> None:
        """Indexa fontes de dados para busca RAG."""
        try:
            logger.info("Iniciando indexação de fontes de dados...")
            
            # Import lazy para evitar circular import
            from ..dependencies import get_database_engine
            from sqlalchemy.ext.asyncio import async_sessionmaker
            
            # Obter sessão do banco
            engine = get_database_engine()
            async_session = async_sessionmaker(engine, expire_on_commit=False)
            
            async with async_session() as session:
                # Indexar equipamentos
                await self._index_equipment_data(session)
                
                # Indexar manutenções
                await self._index_maintenance_data(session)
                
                # Indexar dados históricos
                await self._index_historical_data(session)
            
            # Construir índice de termos
            self._build_term_index()
            
            logger.info(f"Indexação concluída. {len(self.document_cache)} documentos indexados")
            
        except Exception as e:
            logger.error(f"Erro na indexação: {str(e)}")
            raise DataProcessingError(f"Falha na indexação de dados: {str(e)}")
    
    async def _index_equipment_data(self, session: AsyncSession) -> None:
        """Indexa dados de equipamentos."""
        try:
            # Query para buscar equipamentos
            query = text("""
                SELECT id, name, type, status, location, manufacturer, 
                       model, installation_date, last_maintenance
                FROM equipment
                ORDER BY id
            """)
            
            result = await session.execute(query)
            equipments = result.fetchall()
            
            for equipment in equipments:
                # Criar documento chunk
                content = f"""
                Equipamento: {equipment.name} (ID: {equipment.id})
                Tipo: {equipment.type}
                Status: {equipment.status}
                Localização: {equipment.location}
                Fabricante: {equipment.manufacturer}
                Modelo: {equipment.model}
                Data de Instalação: {equipment.installation_date}
                Última Manutenção: {equipment.last_maintenance}
                """.strip()
                
                chunk = DocumentChunk(
                    id=f"equipment_{equipment.id}",
                    content=content,
                    source="equipment",
                    metadata={
                        "equipment_id": equipment.id,
                        "name": equipment.name,
                        "type": equipment.type,
                        "status": equipment.status,
                        "location": equipment.location
                    }
                )
                
                # Gerar embedding simples
                chunk.embedding = self._generate_simple_embedding(content)
                
                self.document_cache[chunk.id] = chunk
                
        except Exception as e:
            logger.error(f"Erro ao indexar equipamentos: {str(e)}")
            raise
    
    async def _index_maintenance_data(self, session: AsyncSession) -> None:
        """Indexa dados de manutenções."""
        try:
            # Query para buscar manutenções
            query = text("""
                SELECT m.id, m.equipment_id, m.type, m.status, 
                       m.scheduled_date, m.completion_date, m.cost,
                       m.description, m.technician, e.name as equipment_name
                FROM maintenance_orders m
                LEFT JOIN equipment e ON m.equipment_id = e.id
                ORDER BY m.scheduled_date DESC
                LIMIT 1000
            """)
            
            result = await session.execute(query)
            maintenances = result.fetchall()
            
            for maintenance in maintenances:
                # Criar documento chunk
                content = f"""
                Manutenção: {maintenance.type} (ID: {maintenance.id})
                Equipamento: {maintenance.equipment_name} (ID: {maintenance.equipment_id})
                Status: {maintenance.status}
                Data Programada: {maintenance.scheduled_date}
                Data Conclusão: {maintenance.completion_date}
                Custo: R$ {maintenance.cost if maintenance.cost else 'N/A'}
                Descrição: {maintenance.description or 'Sem descrição'}
                Técnico: {maintenance.technician or 'Não informado'}
                """.strip()
                
                chunk = DocumentChunk(
                    id=f"maintenance_{maintenance.id}",
                    content=content,
                    source="maintenance",
                    metadata={
                        "maintenance_id": maintenance.id,
                        "equipment_id": maintenance.equipment_id,
                        "type": maintenance.type,
                        "status": maintenance.status,
                        "cost": maintenance.cost,
                        "scheduled_date": str(maintenance.scheduled_date)
                    }
                )
                
                # Gerar embedding simples
                chunk.embedding = self._generate_simple_embedding(content)
                
                self.document_cache[chunk.id] = chunk
                
        except Exception as e:
            logger.error(f"Erro ao indexar manutenções: {str(e)}")
            raise
    
    async def _index_historical_data(self, session: AsyncSession) -> None:
        """Indexa dados históricos."""
        try:
            # Query para buscar falhas
            query = text("""
                SELECT f.id, f.equipment_id, f.failure_date, f.description,
                       f.severity, f.resolution_time, f.cost, e.name as equipment_name
                FROM failures f
                LEFT JOIN equipment e ON f.equipment_id = e.id
                ORDER BY f.failure_date DESC
                LIMIT 1000
            """)
            
            result = await session.execute(query)
            failures = result.fetchall()
            
            for failure in failures:
                # Criar documento chunk
                content = f"""
                Falha: {failure.description} (ID: {failure.id})
                Equipamento: {failure.equipment_name} (ID: {failure.equipment_id})
                Data da Falha: {failure.failure_date}
                Severidade: {failure.severity}
                Tempo de Resolução: {failure.resolution_time}
                Custo de Reparo: R$ {failure.cost if failure.cost else 'N/A'}
                """.strip()
                
                chunk = DocumentChunk(
                    id=f"failure_{failure.id}",
                    content=content,
                    source="failure",
                    metadata={
                        "failure_id": failure.id,
                        "equipment_id": failure.equipment_id,
                        "severity": failure.severity,
                        "failure_date": str(failure.failure_date),
                        "cost": failure.cost
                    }
                )
                
                # Gerar embedding simples
                chunk.embedding = self._generate_simple_embedding(content)
                
                self.document_cache[chunk.id] = chunk
                
        except Exception as e:
            logger.error(f"Erro ao indexar dados históricos: {str(e)}")
            raise
    
    def _preprocess_query(self, query: str) -> str:
        """Pré-processa a query para busca."""
        # Converter para minúsculo
        query = query.lower().strip()
        
        # Normalizar termos comuns
        normalizations = {
            "trafo": "transformador",
            "preventiva": "manutenção preventiva",
            "corretiva": "manutenção corretiva",
            "falhou": "falha",
            "quebrou": "falha",
            "custo": "cost",
            "gasto": "cost",
            "valor": "cost"
        }
        
        for old_term, new_term in normalizations.items():
            query = query.replace(old_term, new_term)
        
        return query
    
    async def _search_relevant_chunks(
        self, 
        query: str, 
        query_type: Optional[str], 
        max_chunks: int
    ) -> List[DocumentChunk]:
        """Busca chunks relevantes baseado na query."""
        
        relevant_chunks = []
        
        # Buscar por termos da query
        query_terms = self._extract_query_terms(query)
        
        for chunk in self.document_cache.values():
            # Filtrar por tipo se especificado
            if query_type and chunk.source != query_type:
                continue
            
            # Calcular similaridade baseada em termos
            similarity = self._calculate_term_similarity(query_terms, chunk.content)
            
            if similarity > 0:
                chunk.relevance_score = similarity
                relevant_chunks.append(chunk)
        
        # Ordenar por relevância
        relevant_chunks.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return relevant_chunks[:max_chunks * 2]  # Buscar mais para depois filtrar
    
    def _extract_query_terms(self, query: str) -> List[str]:
        """Extrai termos relevantes da query."""
        # Remover stop words comuns
        stop_words = {
            "o", "a", "os", "as", "de", "do", "da", "dos", "das",
            "em", "no", "na", "nos", "nas", "para", "por", "com",
            "que", "qual", "quais", "como", "quando", "onde", "e",
            "ou", "mas", "se", "é", "são", "foi", "foram", "tem",
            "têm", "ter", "the", "and", "or", "but", "if", "is",
            "are", "was", "were", "have", "has", "had"
        }
        
        # Dividir em palavras e filtrar
        terms = []
        for word in query.split():
            word = word.strip(".,!?;:")
            if len(word) > 2 and word not in stop_words:
                terms.append(word)
        
        return terms
    
    def _calculate_term_similarity(self, query_terms: List[str], content: str) -> float:
        """Calcula similaridade baseada em termos."""
        content_lower = content.lower()
        
        matches = 0
        total_terms = len(query_terms)
        
        for term in query_terms:
            if term in content_lower:
                matches += 1
        
        # Bonus para correspondências exatas
        exact_matches = sum(1 for term in query_terms if f" {term} " in f" {content_lower} ")
        
        base_score = matches / total_terms if total_terms > 0 else 0
        bonus = exact_matches * 0.2
        
        return min(1.0, base_score + bonus)
    
    def _calculate_relevance_scores(
        self, 
        query: str, 
        chunks: List[DocumentChunk]
    ) -> List[DocumentChunk]:
        """Calcula scores de relevância refinados."""
        
        for chunk in chunks:
            # Score base já calculado
            base_score = chunk.relevance_score
            
            # Bonus por tipo de fonte
            source_bonus = {
                "equipment": 0.1,
                "maintenance": 0.15,
                "failure": 0.05
            }.get(chunk.source, 0)
            
            # Bonus por metadados relevantes
            metadata_bonus = 0
            if chunk.metadata:
                # Bonus se a query menciona IDs específicos
                if any(term.upper() in chunk.content.upper() for term in query.split() if term.isupper()):
                    metadata_bonus += 0.2
                
                # Bonus por status crítico
                if chunk.metadata.get("status") in ["falha", "critical", "urgent"]:
                    metadata_bonus += 0.1
            
            # Score final
            chunk.relevance_score = min(1.0, base_score + source_bonus + metadata_bonus)
        
        return chunks
    
    def _generate_simple_embedding(self, text: str) -> List[float]:
        """Gera embedding simples baseado em TF-IDF simulado."""
        # Vocabulário básico para o domínio
        vocab = [
            "transformador", "gerador", "disjuntor", "cabo", "subestacao", "linha",
            "manutenção", "preventiva", "corretiva", "falha", "defeito", "problema",
            "operacional", "ativo", "inativo", "parado", "funcionando",
            "custo", "valor", "preço", "gasto", "orçamento",
            "hoje", "ontem", "semana", "mes", "ano", "ultimo",
            "urgente", "critico", "normal", "baixo", "alto",
            "instalação", "reparar", "trocar", "verificar", "inspecionar"
        ]
        
        text_lower = text.lower()
        embedding = []
        
        for word in vocab:
            # TF simples - contagem de termo
            count = text_lower.count(word)
            # Normalizar por comprimento do texto
            tf = count / max(1, len(text_lower.split()))
            embedding.append(tf)
        
        return embedding
    
    def _build_term_index(self) -> None:
        """Constrói índice de termos para busca rápida."""
        self.term_index.clear()
        
        for chunk_id, chunk in self.document_cache.items():
            terms = self._extract_query_terms(chunk.content)
            
            for term in terms:
                if term not in self.term_index:
                    self.term_index[term] = []
                self.term_index[term].append(chunk_id)
    
    def _generate_context_summary(self, chunks: List[DocumentChunk]) -> str:
        """Gera resumo do contexto recuperado."""
        if not chunks:
            return "Nenhum contexto relevante encontrado."
        
        # Contar por tipo de fonte
        source_counts = {}
        for chunk in chunks:
            source = chunk.source
            source_counts[source] = source_counts.get(source, 0) + 1
        
        # Criar resumo
        summary_parts = []
        
        for source, count in source_counts.items():
            source_names = {
                "equipment": "equipamentos",
                "maintenance": "manutenções", 
                "failure": "falhas"
            }
            summary_parts.append(f"{count} {source_names.get(source, source)}")
        
        summary = f"Contexto encontrado: {', '.join(summary_parts)}"
        
        # Adicionar informações específicas
        if chunks:
            top_chunk = chunks[0]
            if top_chunk.metadata:
                if "equipment_id" in top_chunk.metadata:
                    summary += f". Foco no equipamento {top_chunk.metadata['equipment_id']}"
        
        return summary
    
    def format_context_for_llm(self, context: RAGContext) -> str:
        """Formata o contexto para ser usado pelo LLM."""
        if not context.chunks:
            return "Sem contexto adicional disponível."
        
        formatted_parts = [
            "=== CONTEXTO RELEVANTE ===",
            f"Query: {context.query}",
            f"Chunks encontrados: {context.total_chunks}",
            f"Tempo de recuperação: {context.retrieval_time:.3f}s",
            "",
            "=== DADOS RELEVANTES ==="
        ]
        
        for i, chunk in enumerate(context.chunks, 1):
            formatted_parts.extend([
                f"[{i}] {chunk.source.upper()} (Relevância: {chunk.relevance_score:.2f})",
                chunk.content,
                ""
            ])
        
        formatted_parts.extend([
            "=== RESUMO ===",
            context.context_summary,
            "",
            "Use essas informações para fornecer uma resposta precisa e contextualizada."
        ])
        
        return "\n".join(formatted_parts)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retorna métricas do serviço RAG."""
        avg_retrieval_time = (
            self.total_retrieval_time / self.queries_processed 
            if self.queries_processed > 0 else 0
        )
        
        cache_hit_rate = (
            self.cache_hits / self.queries_processed 
            if self.queries_processed > 0 else 0
        )
        
        return {
            "queries_processed": self.queries_processed,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": round(cache_hit_rate, 3),
            "avg_retrieval_time": round(avg_retrieval_time, 3),
            "total_documents": len(self.document_cache),
            "indexed_terms": len(self.term_index),
            "relevance_threshold": self.relevance_threshold,
            "max_chunks_per_query": self.max_chunks_per_query
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Verifica saúde do serviço RAG."""
        try:
            # Testar busca simples
            test_context = await self.retrieve_context("teste", max_chunks=1)
            
            return {
                "status": "healthy",
                "documents_indexed": len(self.document_cache),
                "test_retrieval_time": test_context.retrieval_time,
                "memory_usage_mb": len(str(self.document_cache)) / 1024 / 1024
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "documents_indexed": len(self.document_cache)
            } 