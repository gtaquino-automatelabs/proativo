"""
Sistema de Cache Inteligente para Respostas do LLM.

Este módulo implementa um sistema avançado de cache que:
- Identifica consultas similares mesmo com variações na redação
- Normaliza queries para melhor correspondência
- Gerencia TTL e invalidação automática
- Coleta métricas detalhadas de performance
- Suporta diferentes estratégias de cache
"""

import hashlib
import json
import re
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Set
from enum import Enum
from dataclasses import dataclass, asdict
import asyncio
from collections import defaultdict
import logging

from ..config import get_settings
from ...utils.logger import get_logger

# Configurar logger
logger = get_logger(__name__)


class CacheStrategy(Enum):
    """Estratégias de cache disponíveis."""
    EXACT_MATCH = "exact_match"
    NORMALIZED_MATCH = "normalized_match"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    FUZZY_MATCH = "fuzzy_match"


class CacheStatus(Enum):
    """Status do item no cache."""
    FRESH = "fresh"
    STALE = "stale"
    EXPIRED = "expired"


@dataclass
class CacheEntry:
    """Entrada do cache com metadados."""
    key: str
    original_query: str
    normalized_query: str
    response: Dict[str, Any]
    created_at: datetime
    last_accessed: datetime
    access_count: int
    ttl_seconds: int
    tags: Set[str]
    confidence_score: float
    
    @property
    def expires_at(self) -> datetime:
        """Retorna quando a entrada expira."""
        return self.created_at + timedelta(seconds=self.ttl_seconds)
    
    @property
    def is_expired(self) -> bool:
        """Verifica se a entrada está expirada."""
        return datetime.now() > self.expires_at
    
    @property
    def is_stale(self) -> bool:
        """Verifica se a entrada está obsoleta (75% do TTL)."""
        stale_threshold = self.created_at + timedelta(seconds=int(self.ttl_seconds * 0.75))
        return datetime.now() > stale_threshold
    
    @property
    def status(self) -> CacheStatus:
        """Retorna status atual da entrada."""
        if self.is_expired:
            return CacheStatus.EXPIRED
        elif self.is_stale:
            return CacheStatus.STALE
        else:
            return CacheStatus.FRESH
    
    def update_access(self) -> None:
        """Atualiza metadados de acesso."""
        self.last_accessed = datetime.now()
        self.access_count += 1


@dataclass
class CacheMetrics:
    """Métricas do sistema de cache."""
    total_requests: int
    cache_hits: int
    cache_misses: int
    cache_size: int
    max_cache_size: int
    expired_entries: int
    stale_entries: int
    average_response_size: float
    hit_rate: float
    miss_rate: float
    memory_usage_mb: float


class QueryNormalizer:
    """Normalizador de consultas para melhor correspondência de cache."""
    
    def __init__(self):
        """Inicializa o normalizador."""
        # Palavras irrelevantes que podem ser removidas
        self.stop_words = {
            "o", "a", "os", "as", "um", "uma", "uns", "umas",
            "de", "da", "do", "das", "dos", "em", "na", "no", "nas", "nos",
            "por", "para", "com", "sem", "sobre", "entre", "até", "desde",
            "e", "ou", "mas", "que", "se", "como", "quando", "onde",
            "qual", "quais", "quanto", "quantos", "quantas",
            "me", "te", "se", "nos", "vos", "lhe", "lhes",
            "por favor", "obrigado", "obrigada", "pode", "poderia",
            "gostaria", "quero", "preciso", "queria"
        }
        
        # Sinônimos para normalização
        self.synonyms = {
            "transformador": ["trafo", "transformer", "transformadores"],
            "gerador": ["generator", "geradores"],
            "disjuntor": ["breaker", "disjuntores"],
            "manutenção": ["manutencao", "maintenance", "manutenções"],
            "equipamento": ["equipment", "equipamentos"],
            "status": ["situação", "condição", "estado"],
            "falha": ["defeito", "problema", "fault", "failure", "falhas"],
            "custo": ["valor", "preço", "price", "cost", "custos"]
        }
        
        # Padrões de normalização
        self.normalization_patterns = [
            (r'\s+', ' '),  # Múltiplos espaços para um espaço
            (r'[^\w\s-]', ''),  # Remover pontuação exceto hífen
            (r'\b\d{4}-\d{2}-\d{2}\b', 'DATA'),  # Normalizar datas
            (r'\b[A-Z]+\d+\b', 'ID_EQUIPAMENTO'),  # Normalizar IDs de equipamento
            (r'\b\d+\b', 'NUMERO'),  # Normalizar números
        ]
    
    def normalize(self, query: str) -> str:
        """
        Normaliza uma consulta para correspondência de cache.
        
        Args:
            query: Consulta original
            
        Returns:
            str: Consulta normalizada
        """
        if not query:
            return ""
        
        # Converter para lowercase
        normalized = query.lower().strip()
        
        # Aplicar padrões de normalização
        for pattern, replacement in self.normalization_patterns:
            normalized = re.sub(pattern, replacement, normalized)
        
        # Expandir sinônimos
        words = normalized.split()
        normalized_words = []
        
        for word in words:
            # Verificar se é sinônimo
            canonical_word = word
            for canonical, synonyms in self.synonyms.items():
                if word in synonyms:
                    canonical_word = canonical
                    break
            
            # Adicionar se não for stop word
            if canonical_word not in self.stop_words:
                normalized_words.append(canonical_word)
        
        # Ordenar palavras para consistência
        normalized_words.sort()
        
        return " ".join(normalized_words)
    
    def calculate_similarity(self, query1: str, query2: str) -> float:
        """
        Calcula similaridade entre duas consultas normalizadas.
        
        Args:
            query1: Primeira consulta
            query2: Segunda consulta
            
        Returns:
            float: Score de similaridade (0.0 - 1.0)
        """
        norm1 = self.normalize(query1)
        norm2 = self.normalize(query2)
        
        if not norm1 or not norm2:
            return 0.0
        
        if norm1 == norm2:
            return 1.0
        
        # Similaridade baseada em palavras comuns
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        jaccard_similarity = len(intersection) / len(union)
        
        # Bonus por ordem similar das palavras
        if len(words1) == len(words2):
            word_order_bonus = 0.1 if norm1.split()[:3] == norm2.split()[:3] else 0.0
        else:
            word_order_bonus = 0.0
        
        return min(1.0, jaccard_similarity + word_order_bonus)


class CacheService:
    """
    Serviço principal de cache para respostas do LLM.
    
    Responsabilidades:
    - Gerenciar cache em memória com TTL
    - Normalizar consultas para melhor correspondência
    - Identificar consultas similares
    - Coletar métricas de performance
    - Limpeza automática de entradas expiradas
    """
    
    def __init__(self):
        """Inicializa o serviço de cache."""
        self.settings = get_settings()
        self.normalizer = QueryNormalizer()
        
        # Armazenamento do cache
        self.cache: Dict[str, CacheEntry] = {}
        self.query_index: Dict[str, Set[str]] = defaultdict(set)  # normalized_query -> cache_keys
        
        # Configurações
        self.max_cache_size = 1000
        self.default_ttl = 3600  # 1 hora
        self.similarity_threshold = 0.8
        self.cleanup_interval = 300  # 5 minutos
        
        # Métricas
        self.total_requests = 0
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Iniciar limpeza automática
        self._start_cleanup_task()
        
        logger.info("CacheService inicializado", extra={
            "max_size": self.max_cache_size,
            "default_ttl": self.default_ttl,
            "similarity_threshold": self.similarity_threshold
        })
    
    def _start_cleanup_task(self) -> None:
        """Inicia task de limpeza automática."""
        asyncio.create_task(self._cleanup_loop())
    
    async def _cleanup_loop(self) -> None:
        """Loop de limpeza automática."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro na limpeza do cache: {str(e)}")
    
    async def _cleanup_expired(self) -> None:
        """Remove entradas expiradas do cache."""
        expired_keys = []
        
        for key, entry in self.cache.items():
            if entry.is_expired:
                expired_keys.append(key)
        
        for key in expired_keys:
            await self._remove_entry(key)
        
        if expired_keys:
            logger.info(f"Limpeza do cache: {len(expired_keys)} entradas removidas")
    
    async def _remove_entry(self, key: str) -> None:
        """Remove uma entrada do cache e índices."""
        if key in self.cache:
            entry = self.cache[key]
            
            # Remover do índice de consultas
            self.query_index[entry.normalized_query].discard(key)
            if not self.query_index[entry.normalized_query]:
                del self.query_index[entry.normalized_query]
            
            # Remover do cache principal
            del self.cache[key]
    
    def _generate_cache_key(self, query: str, context: Dict[str, Any] = None) -> str:
        """
        Gera chave única para cache.
        
        Args:
            query: Consulta original
            context: Contexto adicional
            
        Returns:
            str: Chave de cache
        """
        # Normalizar query
        normalized_query = self.normalizer.normalize(query)
        
        # Incluir contexto relevante
        context_data = {
            "query": normalized_query,
            "model": self.settings.gemini_model,
            "temperature": self.settings.gemini_temperature
        }
        
        if context:
            # Incluir apenas partes relevantes do contexto
            relevant_context = {
                k: v for k, v in context.items() 
                if k in ["query_type", "user_type", "filters"]
            }
            context_data.update(relevant_context)
        
        # Gerar hash
        cache_string = json.dumps(context_data, sort_keys=True)
        return hashlib.sha256(cache_string.encode()).hexdigest()[:16]
    
    async def get(
        self, 
        query: str, 
        context: Dict[str, Any] = None,
        strategy: CacheStrategy = CacheStrategy.NORMALIZED_MATCH
    ) -> Optional[Dict[str, Any]]:
        """
        Busca resposta no cache.
        
        Args:
            query: Consulta do usuário
            context: Contexto adicional
            strategy: Estratégia de busca no cache
            
        Returns:
            Dict com resposta ou None se não encontrada
        """
        self.total_requests += 1
        
        # Tentar busca exata primeiro
        cache_key = self._generate_cache_key(query, context)
        
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            
            if not entry.is_expired:
                entry.update_access()
                self.cache_hits += 1
                
                logger.debug("Cache hit exato", extra={
                    "cache_key": cache_key[:8],
                    "query": query[:50],
                    "status": entry.status.value
                })
                
                response = entry.response.copy()
                response["cache_used"] = True
                response["cache_status"] = entry.status.value
                response["cache_age_seconds"] = int((datetime.now() - entry.created_at).total_seconds())
                
                return response
        
        # Tentar busca por similaridade se configurada
        if strategy in [CacheStrategy.NORMALIZED_MATCH, CacheStrategy.SEMANTIC_SIMILARITY]:
            similar_entry = await self._find_similar_entry(query, context)
            
            if similar_entry:
                similar_entry.update_access()
                self.cache_hits += 1
                
                logger.debug("Cache hit por similaridade", extra={
                    "original_query": query[:50],
                    "similar_query": similar_entry.original_query[:50],
                    "similarity_strategy": strategy.value
                })
                
                response = similar_entry.response.copy()
                response["cache_used"] = True
                response["cache_status"] = "similar_match"
                response["cache_similarity"] = True
                
                return response
        
        # Cache miss
        self.cache_misses += 1
        logger.debug("Cache miss", extra={
            "query": query[:50],
            "strategy": strategy.value
        })
        
        return None
    
    async def _find_similar_entry(
        self, 
        query: str, 
        context: Dict[str, Any] = None
    ) -> Optional[CacheEntry]:
        """
        Busca entrada similar no cache.
        
        Args:
            query: Consulta do usuário
            context: Contexto adicional
            
        Returns:
            CacheEntry similar ou None
        """
        normalized_query = self.normalizer.normalize(query)
        
        # Buscar por consultas normalizadas similares
        best_entry = None
        best_similarity = 0.0
        
        for norm_query, cache_keys in self.query_index.items():
            similarity = self.normalizer.calculate_similarity(normalized_query, norm_query)
            
            if similarity >= self.similarity_threshold and similarity > best_similarity:
                # Encontrar a entrada mais recente e não expirada
                for key in cache_keys:
                    if key in self.cache:
                        entry = self.cache[key]
                        if not entry.is_expired:
                            best_entry = entry
                            best_similarity = similarity
                            break
        
        return best_entry
    
    async def set(
        self, 
        query: str, 
        response: Dict[str, Any],
        context: Dict[str, Any] = None,
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None
    ) -> str:
        """
        Armazena resposta no cache.
        
        Args:
            query: Consulta original
            response: Resposta para armazenar
            context: Contexto adicional
            ttl: Time-to-live em segundos
            tags: Tags para categorização
            
        Returns:
            str: Chave do cache gerada
        """
        cache_key = self._generate_cache_key(query, context)
        normalized_query = self.normalizer.normalize(query)
        
        # Verificar se precisa fazer limpeza por tamanho
        if len(self.cache) >= self.max_cache_size:
            await self._evict_entries()
        
        # Criar entrada do cache
        entry = CacheEntry(
            key=cache_key,
            original_query=query,
            normalized_query=normalized_query,
            response=response.copy(),
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            access_count=1,
            ttl_seconds=ttl or self.default_ttl,
            tags=tags or set(),
            confidence_score=response.get("confidence_score", 0.0)
        )
        
        # Armazenar no cache
        self.cache[cache_key] = entry
        self.query_index[normalized_query].add(cache_key)
        
        logger.debug("Entrada adicionada ao cache", extra={
            "cache_key": cache_key[:8],
            "query": query[:50],
            "ttl": entry.ttl_seconds,
            "cache_size": len(self.cache)
        })
        
        return cache_key
    
    async def _evict_entries(self) -> None:
        """Remove entradas do cache para liberar espaço."""
        # Estratégia: remover 20% das entradas menos acessadas ou mais antigas
        entries_to_remove = int(self.max_cache_size * 0.2)
        
        # Ordenar por critério de remoção (menos acessadas, mais antigas)
        sorted_entries = sorted(
            self.cache.items(),
            key=lambda x: (x[1].access_count, x[1].last_accessed)
        )
        
        for i in range(min(entries_to_remove, len(sorted_entries))):
            key = sorted_entries[i][0]
            await self._remove_entry(key)
        
        logger.info(f"Cache eviction: {entries_to_remove} entradas removidas")
    
    async def invalidate(
        self, 
        pattern: Optional[str] = None,
        tags: Optional[Set[str]] = None,
        older_than: Optional[datetime] = None
    ) -> int:
        """
        Invalida entradas do cache baseado em critérios.
        
        Args:
            pattern: Padrão regex para corresponder com queries
            tags: Tags para invalidar
            older_than: Invalidar entradas mais antigas que esta data
            
        Returns:
            int: Número de entradas invalidadas
        """
        keys_to_remove = []
        
        for key, entry in self.cache.items():
            should_remove = False
            
            # Verificar padrão
            if pattern and re.search(pattern, entry.original_query, re.IGNORECASE):
                should_remove = True
            
            # Verificar tags
            if tags and entry.tags.intersection(tags):
                should_remove = True
            
            # Verificar idade
            if older_than and entry.created_at < older_than:
                should_remove = True
            
            if should_remove:
                keys_to_remove.append(key)
        
        # Remover entradas
        for key in keys_to_remove:
            await self._remove_entry(key)
        
        logger.info(f"Cache invalidation: {len(keys_to_remove)} entradas removidas")
        return len(keys_to_remove)
    
    async def clear(self) -> None:
        """Limpa todo o cache."""
        cache_size = len(self.cache)
        self.cache.clear()
        self.query_index.clear()
        
        logger.info(f"Cache completamente limpo: {cache_size} entradas removidas")
    
    async def get_metrics(self) -> CacheMetrics:
        """
        Retorna métricas detalhadas do cache.
        
        Returns:
            CacheMetrics: Métricas do sistema de cache
        """
        # Calcular estatísticas
        hit_rate = (self.cache_hits / self.total_requests) if self.total_requests > 0 else 0.0
        miss_rate = (self.cache_misses / self.total_requests) if self.total_requests > 0 else 0.0
        
        # Contar entradas por status
        expired_count = sum(1 for entry in self.cache.values() if entry.is_expired)
        stale_count = sum(1 for entry in self.cache.values() if entry.is_stale and not entry.is_expired)
        
        # Calcular tamanho médio das respostas
        total_size = sum(len(str(entry.response)) for entry in self.cache.values())
        avg_response_size = total_size / len(self.cache) if self.cache else 0.0
        
        # Estimativa de uso de memória (simplificada)
        memory_usage = total_size / (1024 * 1024)  # MB
        
        return CacheMetrics(
            total_requests=self.total_requests,
            cache_hits=self.cache_hits,
            cache_misses=self.cache_misses,
            cache_size=len(self.cache),
            max_cache_size=self.max_cache_size,
            expired_entries=expired_count,
            stale_entries=stale_count,
            average_response_size=avg_response_size,
            hit_rate=round(hit_rate, 3),
            miss_rate=round(miss_rate, 3),
            memory_usage_mb=round(memory_usage, 2)
        )
    
    async def get_cache_info(self, query: str) -> Dict[str, Any]:
        """
        Retorna informações sobre cache para uma query específica.
        
        Args:
            query: Consulta para verificar
            
        Returns:
            Dict: Informações sobre o estado no cache
        """
        cache_key = self._generate_cache_key(query)
        normalized_query = self.normalizer.normalize(query)
        
        info = {
            "cache_key": cache_key,
            "normalized_query": normalized_query,
            "exists_in_cache": cache_key in self.cache,
            "similar_entries": []
        }
        
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            info.update({
                "status": entry.status.value,
                "created_at": entry.created_at.isoformat(),
                "expires_at": entry.expires_at.isoformat(),
                "access_count": entry.access_count,
                "last_accessed": entry.last_accessed.isoformat()
            })
        
        # Buscar entradas similares
        similar_entry = await self._find_similar_entry(query)
        if similar_entry:
            similarity = self.normalizer.calculate_similarity(
                normalized_query, 
                similar_entry.normalized_query
            )
            info["similar_entries"].append({
                "query": similar_entry.original_query,
                "similarity": round(similarity, 3),
                "status": similar_entry.status.value
            })
        
        return info
    
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Retorna status de saúde do sistema de cache.
        
        Returns:
            Dict: Status de saúde
        """
        metrics = await self.get_metrics()
        
        # Determinar status geral
        if metrics.hit_rate >= 0.6 and metrics.cache_size < metrics.max_cache_size * 0.9:
            status = "healthy"
        elif metrics.hit_rate >= 0.3:
            status = "warning"
        else:
            status = "critical"
        
        return {
            "status": status,
            "hit_rate": metrics.hit_rate,
            "cache_utilization": round(metrics.cache_size / metrics.max_cache_size, 3),
            "memory_usage_mb": metrics.memory_usage_mb,
            "expired_entries": metrics.expired_entries,
            "stale_entries": metrics.stale_entries,
            "recommendations": self._generate_recommendations(metrics)
        }
    
    def _generate_recommendations(self, metrics: CacheMetrics) -> List[str]:
        """Gera recomendações baseadas nas métricas."""
        recommendations = []
        
        if metrics.hit_rate < 0.3:
            recommendations.append("Taxa de acerto baixa - considere ajustar threshold de similaridade")
        
        if metrics.cache_size > metrics.max_cache_size * 0.9:
            recommendations.append("Cache quase cheio - considere aumentar tamanho máximo")
        
        if metrics.expired_entries > metrics.cache_size * 0.2:
            recommendations.append("Muitas entradas expiradas - considere reduzir TTL")
        
        if metrics.memory_usage_mb > 100:
            recommendations.append("Alto uso de memória - considere limpeza mais frequente")
        
        return recommendations 