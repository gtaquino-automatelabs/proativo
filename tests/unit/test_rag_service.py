"""
Testes unitários para o RAGService.

Testa indexação, recuperação de contexto, embeddings e ranking.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.api.services.rag_service import (
    RAGService, DocumentChunk, RAGContext
)
from src.utils.error_handlers import ValidationError, DataProcessingError


class TestRAGService:
    """Testes para o serviço RAG."""
    
    @pytest.fixture
    def rag_service(self):
        """Fixture para instância do RAGService."""
        with patch('src.api.services.rag_service.get_settings') as mock_settings, \
             patch('src.api.services.rag_service.get_database_session'):
            
            settings = Mock()
            mock_settings.return_value = settings
            
            service = RAGService()
            return service
    
    @pytest.fixture
    def sample_chunks(self):
        """Fixture com chunks de exemplo."""
        return [
            DocumentChunk(
                id="equipment_T001",
                content="Transformador T001 operacional localizado em São Paulo",
                source="equipment",
                metadata={"equipment_id": "T001", "type": "transformador", "status": "operacional"}
            ),
            DocumentChunk(
                id="maintenance_M001", 
                content="Manutenção preventiva do transformador T001 agendada",
                source="maintenance",
                metadata={"maintenance_id": "M001", "equipment_id": "T001", "type": "preventiva"}
            ),
            DocumentChunk(
                id="failure_F001",
                content="Falha crítica no gerador GER-123 resolvida em 4 horas",
                source="failure", 
                metadata={"failure_id": "F001", "equipment_id": "GER-123", "severity": "critical"}
            )
        ]
    
    def test_initialization(self, rag_service):
        """Testa inicialização do serviço RAG."""
        assert rag_service.max_chunks_per_query == 5
        assert rag_service.relevance_threshold == 0.3
        assert rag_service.queries_processed == 0
        assert isinstance(rag_service.document_cache, dict)
        assert isinstance(rag_service.term_index, dict)
    
    def test_preprocess_query(self, rag_service):
        """Testa pré-processamento de queries."""
        # Normalização de termos
        result = rag_service._preprocess_query("Trafo com problemas")
        assert "transformador" in result
        assert "trafo" not in result
        
        # Conversão para minúsculo
        result = rag_service._preprocess_query("MANUTENÇÃO PREVENTIVA")
        assert result == "manutenção preventiva"
        
        # Normalização de sinônimos
        result = rag_service._preprocess_query("equipamento falhou")
        assert "falha" in result
    
    def test_extract_query_terms(self, rag_service):
        """Testa extração de termos relevantes."""
        terms = rag_service._extract_query_terms("transformador em manutenção")
        
        # Deve incluir termos relevantes
        assert "transformador" in terms
        assert "manutenção" in terms
        
        # Deve excluir stop words
        assert "em" not in terms
        
        # Deve filtrar termos muito curtos
        terms = rag_service._extract_query_terms("o a de")
        assert len(terms) == 0
    
    def test_calculate_term_similarity(self, rag_service):
        """Testa cálculo de similaridade por termos."""
        query_terms = ["transformador", "operacional"]
        content = "Transformador T001 está operacional e funcionando normalmente"
        
        similarity = rag_service._calculate_term_similarity(query_terms, content)
        
        assert similarity > 0.5  # Deve ter alta similaridade
        assert similarity <= 1.0  # Não deve exceder 1
    
    def test_calculate_term_similarity_no_match(self, rag_service):
        """Testa similaridade sem correspondências."""
        query_terms = ["gerador", "falha"]
        content = "Transformador operacional sem problemas"
        
        similarity = rag_service._calculate_term_similarity(query_terms, content)
        
        assert similarity == 0.0  # Sem correspondências
    
    def test_generate_simple_embedding(self, rag_service):
        """Testa geração de embeddings simples."""
        text = "Transformador em manutenção preventiva"
        embedding = rag_service._generate_simple_embedding(text)
        
        # Deve retornar lista de floats
        assert isinstance(embedding, list)
        assert all(isinstance(x, float) for x in embedding)
        assert len(embedding) > 0
        
        # Deve ter valores para termos encontrados
        vocab = ["transformador", "manutenção", "preventiva"]
        # Pelo menos alguns valores devem ser > 0 para termos presentes
        assert any(x > 0 for x in embedding)
    
    def test_calculate_relevance_scores(self, rag_service, sample_chunks):
        """Testa cálculo de scores de relevância."""
        # Configurar scores base
        for chunk in sample_chunks:
            chunk.relevance_score = 0.5
        
        scored_chunks = rag_service._calculate_relevance_scores(
            "transformador T001", sample_chunks
        )
        
        # Deve manter ou aumentar scores
        for chunk in scored_chunks:
            assert chunk.relevance_score >= 0.5
        
        # Chunk de manutenção deve ter bonus
        maintenance_chunk = next(c for c in scored_chunks if c.source == "maintenance")
        assert maintenance_chunk.relevance_score > 0.5
    
    def test_generate_context_summary_empty(self, rag_service):
        """Testa resumo com lista vazia."""
        summary = rag_service._generate_context_summary([])
        assert "Nenhum contexto relevante encontrado" in summary
    
    def test_generate_context_summary_multiple_sources(self, rag_service, sample_chunks):
        """Testa resumo com múltiplas fontes."""
        summary = rag_service._generate_context_summary(sample_chunks)
        
        assert "equipamentos" in summary
        assert "manutenções" in summary
        assert "falhas" in summary
        assert "T001" in summary  # Deve mencionar equipamento específico
    
    def test_build_term_index(self, rag_service, sample_chunks):
        """Testa construção do índice de termos."""
        # Adicionar chunks ao cache
        for chunk in sample_chunks:
            rag_service.document_cache[chunk.id] = chunk
        
        # Construir índice
        rag_service._build_term_index()
        
        # Verificar se termos foram indexados
        assert len(rag_service.term_index) > 0
        assert "transformador" in rag_service.term_index
        assert "operacional" in rag_service.term_index
    
    @pytest.mark.asyncio
    async def test_search_relevant_chunks(self, rag_service, sample_chunks):
        """Testa busca de chunks relevantes."""
        # Adicionar chunks ao cache
        for chunk in sample_chunks:
            rag_service.document_cache[chunk.id] = chunk
        
        # Buscar chunks
        relevant_chunks = await rag_service._search_relevant_chunks(
            "transformador operacional", None, 5
        )
        
        # Deve encontrar chunks relevantes
        assert len(relevant_chunks) > 0
        
        # Deve estar ordenado por relevância
        if len(relevant_chunks) > 1:
            assert relevant_chunks[0].relevance_score >= relevant_chunks[1].relevance_score
    
    @pytest.mark.asyncio
    async def test_search_relevant_chunks_filtered_by_type(self, rag_service, sample_chunks):
        """Testa busca filtrada por tipo."""
        # Adicionar chunks ao cache
        for chunk in sample_chunks:
            rag_service.document_cache[chunk.id] = chunk
        
        # Buscar apenas equipamentos
        relevant_chunks = await rag_service._search_relevant_chunks(
            "transformador", "equipment", 5
        )
        
        # Deve retornar apenas chunks de equipamento
        for chunk in relevant_chunks:
            assert chunk.source == "equipment"
    
    @pytest.mark.asyncio
    async def test_retrieve_context_success(self, rag_service, sample_chunks):
        """Testa recuperação de contexto bem-sucedida."""
        # Adicionar chunks ao cache
        for chunk in sample_chunks:
            rag_service.document_cache[chunk.id] = chunk
        
        # Configurar scores para passar o threshold
        for chunk in sample_chunks:
            chunk.relevance_score = 0.5
        
        context = await rag_service.retrieve_context("transformador operacional")
        
        assert isinstance(context, RAGContext)
        assert context.query == "transformador operacional"
        assert len(context.chunks) >= 0
        assert context.retrieval_time > 0
        assert isinstance(context.context_summary, str)
    
    @pytest.mark.asyncio
    async def test_retrieve_context_with_max_chunks(self, rag_service, sample_chunks):
        """Testa limitação de chunks retornados."""
        # Adicionar chunks ao cache
        for chunk in sample_chunks:
            chunk.relevance_score = 0.5  # Acima do threshold
            rag_service.document_cache[chunk.id] = chunk
        
        context = await rag_service.retrieve_context("teste", max_chunks=2)
        
        # Não deve retornar mais que o máximo especificado
        assert len(context.chunks) <= 2
    
    def test_format_context_for_llm_empty(self, rag_service):
        """Testa formatação com contexto vazio."""
        context = RAGContext(
            query="teste",
            chunks=[],
            total_chunks=0,
            retrieval_time=0.1,
            context_summary="Nenhum contexto",
            relevance_threshold=0.3
        )
        
        formatted = rag_service.format_context_for_llm(context)
        assert "Sem contexto adicional disponível" in formatted
    
    def test_format_context_for_llm_with_chunks(self, rag_service, sample_chunks):
        """Testa formatação com chunks."""
        context = RAGContext(
            query="transformador",
            chunks=sample_chunks[:2],
            total_chunks=2,
            retrieval_time=0.1,
            context_summary="Contexto encontrado",
            relevance_threshold=0.3
        )
        
        formatted = rag_service.format_context_for_llm(context)
        
        assert "=== CONTEXTO RELEVANTE ===" in formatted
        assert "Query: transformador" in formatted
        assert "Chunks encontrados: 2" in formatted
        assert "=== DADOS RELEVANTES ===" in formatted
        assert "EQUIPMENT" in formatted  # Tipo do primeiro chunk
    
    def test_get_metrics(self, rag_service):
        """Testa obtenção de métricas."""
        # Simular algumas operações
        rag_service.queries_processed = 10
        rag_service.cache_hits = 3
        rag_service.total_retrieval_time = 1.5
        rag_service.document_cache = {"doc1": Mock(), "doc2": Mock()}
        rag_service.term_index = {"termo1": [], "termo2": []}
        
        metrics = rag_service.get_metrics()
        
        assert metrics["queries_processed"] == 10
        assert metrics["cache_hits"] == 3
        assert metrics["cache_hit_rate"] == 0.3
        assert metrics["avg_retrieval_time"] == 0.15
        assert metrics["total_documents"] == 2
        assert metrics["indexed_terms"] == 2
        assert "relevance_threshold" in metrics
        assert "max_chunks_per_query" in metrics
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, rag_service):
        """Testa health check saudável."""
        # Mock do retrieve_context para não falhar
        with patch.object(rag_service, 'retrieve_context') as mock_retrieve:
            mock_context = RAGContext(
                query="teste",
                chunks=[],
                total_chunks=0,
                retrieval_time=0.1,
                context_summary="",
                relevance_threshold=0.3
            )
            mock_retrieve.return_value = mock_context
            
            health = await rag_service.health_check()
            
            assert health["status"] == "healthy"
            assert "documents_indexed" in health
            assert "test_retrieval_time" in health
            assert "memory_usage_mb" in health
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, rag_service):
        """Testa health check com erro."""
        # Mock para simular erro
        with patch.object(rag_service, 'retrieve_context', side_effect=Exception("Erro de teste")):
            health = await rag_service.health_check()
            
            assert health["status"] == "unhealthy"
            assert "error" in health
            assert "Erro de teste" in health["error"]
    
    @pytest.mark.asyncio
    async def test_index_equipment_data(self, rag_service):
        """Testa indexação de dados de equipamentos."""
        # Mock da sessão e resultados
        mock_session = AsyncMock()
        mock_result = Mock()
        
        # Mock equipment data
        mock_equipment = Mock()
        mock_equipment.id = "T001"
        mock_equipment.name = "Transformador Principal"
        mock_equipment.type = "transformador"
        mock_equipment.status = "operacional"
        mock_equipment.location = "São Paulo"
        mock_equipment.manufacturer = "Fabricante A"
        mock_equipment.model = "Modelo X"
        mock_equipment.installation_date = "2020-01-01"
        mock_equipment.last_maintenance = "2023-12-01"
        
        mock_result.fetchall.return_value = [mock_equipment]
        mock_session.execute.return_value = mock_result
        
        # Executar indexação
        await rag_service._index_equipment_data(mock_session)
        
        # Verificar se chunk foi criado
        assert len(rag_service.document_cache) == 1
        chunk_id = "equipment_T001"
        assert chunk_id in rag_service.document_cache
        
        chunk = rag_service.document_cache[chunk_id]
        assert chunk.source == "equipment"
        assert "T001" in chunk.content
        assert "transformador" in chunk.content.lower()
        assert chunk.metadata["equipment_id"] == "T001"
    
    @pytest.mark.asyncio
    async def test_index_maintenance_data(self, rag_service):
        """Testa indexação de dados de manutenção."""
        # Mock da sessão e resultados
        mock_session = AsyncMock()
        mock_result = Mock()
        
        # Mock maintenance data
        mock_maintenance = Mock()
        mock_maintenance.id = "M001"
        mock_maintenance.equipment_id = "T001"
        mock_maintenance.type = "preventiva"
        mock_maintenance.status = "agendada"
        mock_maintenance.scheduled_date = "2024-01-15"
        mock_maintenance.completion_date = None
        mock_maintenance.cost = 1500.00
        mock_maintenance.description = "Manutenção preventiva trimestral"
        mock_maintenance.technician = "João Silva"
        mock_maintenance.equipment_name = "Transformador Principal"
        
        mock_result.fetchall.return_value = [mock_maintenance]
        mock_session.execute.return_value = mock_result
        
        # Executar indexação
        await rag_service._index_maintenance_data(mock_session)
        
        # Verificar se chunk foi criado
        assert len(rag_service.document_cache) == 1
        chunk_id = "maintenance_M001"
        assert chunk_id in rag_service.document_cache
        
        chunk = rag_service.document_cache[chunk_id]
        assert chunk.source == "maintenance"
        assert "M001" in chunk.content
        assert "preventiva" in chunk.content
        assert chunk.metadata["maintenance_id"] == "M001"
    
    @pytest.mark.asyncio 
    async def test_index_historical_data(self, rag_service):
        """Testa indexação de dados históricos."""
        # Mock da sessão e resultados
        mock_session = AsyncMock()
        mock_result = Mock()
        
        # Mock failure data
        mock_failure = Mock()
        mock_failure.id = "F001"
        mock_failure.equipment_id = "GER-123"
        mock_failure.failure_date = "2023-12-01"
        mock_failure.description = "Falha no sistema de refrigeração"
        mock_failure.severity = "critical"
        mock_failure.resolution_time = 240  # minutos
        mock_failure.cost = 5000.00
        mock_failure.equipment_name = "Gerador Principal"
        
        mock_result.fetchall.return_value = [mock_failure]
        mock_session.execute.return_value = mock_result
        
        # Executar indexação
        await rag_service._index_historical_data(mock_session)
        
        # Verificar se chunk foi criado
        assert len(rag_service.document_cache) == 1
        chunk_id = "failure_F001"
        assert chunk_id in rag_service.document_cache
        
        chunk = rag_service.document_cache[chunk_id]
        assert chunk.source == "failure"
        assert "F001" in chunk.content
        assert "critical" in chunk.content
        assert chunk.metadata["failure_id"] == "F001"
    
    def test_relevance_threshold_filtering(self, rag_service, sample_chunks):
        """Testa filtragem por threshold de relevância."""
        # Configurar scores diferentes
        sample_chunks[0].relevance_score = 0.5  # Acima do threshold (0.3)
        sample_chunks[1].relevance_score = 0.2  # Abaixo do threshold
        sample_chunks[2].relevance_score = 0.4  # Acima do threshold
        
        # Simular filtragem
        filtered_chunks = [
            chunk for chunk in sample_chunks 
            if chunk.relevance_score >= rag_service.relevance_threshold
        ]
        
        # Deve filtrar apenas chunks acima do threshold
        assert len(filtered_chunks) == 2
        assert all(chunk.relevance_score >= 0.3 for chunk in filtered_chunks)
    
    def test_metadata_bonus_scoring(self, rag_service):
        """Testa bonus por metadados específicos."""
        chunk = DocumentChunk(
            id="test_chunk",
            content="Equipamento T001 com status crítico",
            source="equipment",
            metadata={"status": "critical", "equipment_id": "T001"},
            relevance_score=0.5
        )
        
        scored_chunks = rag_service._calculate_relevance_scores("T001", [chunk])
        
        # Deve ter recebido bonus por ID específico e status crítico
        assert scored_chunks[0].relevance_score > 0.5


if __name__ == "__main__":
    pytest.main([__file__]) 