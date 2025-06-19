"""Sistema de Cache básico para testes de integração."""

import time
import hashlib
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CacheMetrics:
    """Métricas básicas do cache."""
    cache_size: int = 0
    max_cache_size: int = 1000
    hit_rate: float = 0.0
    miss_rate: float = 0.0
    expired_entries: int = 0
    stale_entries: int = 0
    memory_usage_mb: float = 0.0
    average_response_size: float = 0.0


class CacheService:
    """Serviço de cache simplificado para testes."""
    
    def __init__(self, max_size: int = 1000):
        """Inicializa cache."""
        self.cache = {}
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
    
    def _generate_key(self, query: str, context: Dict[str, Any] = None) -> str:
        """Gera chave para cache."""
        context_str = json.dumps(context or {}, sort_keys=True)
        combined = f"{query}|{context_str}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    async def get(self, query: str, context: Dict[str, Any] = None, strategy: str = "exact") -> Optional[Dict[str, Any]]:
        """Busca no cache."""
        key = self._generate_key(query, context)
        
        if key in self.cache:
            self.hits += 1
            entry = self.cache[key]
            entry["cache_used"] = True
            entry["cache_strategy"] = strategy
            return entry
        
        self.misses += 1
        return None
    
    async def set(
        self, 
        query: str, 
        response: Dict[str, Any], 
        context: Dict[str, Any] = None,
        ttl: int = 3600,
        tags: set = None
    ) -> str:
        """Armazena no cache."""
        key = self._generate_key(query, context)
        
        # Eviction simples se exceder tamanho
        if len(self.cache) >= self.max_size:
            # Remove primeira entrada (FIFO)
            first_key = next(iter(self.cache))
            del self.cache[first_key]
        
        self.cache[key] = response.copy()
        return key
    
    async def clear(self):
        """Limpa cache."""
        self.cache.clear()
    
    async def get_metrics(self) -> CacheMetrics:
        """Retorna métricas."""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0
        miss_rate = self.misses / total_requests if total_requests > 0 else 0
        
        return CacheMetrics(
            cache_size=len(self.cache),
            max_cache_size=self.max_size,
            hit_rate=hit_rate,
            miss_rate=miss_rate
        )
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Status de saúde."""
        metrics = await self.get_metrics()
        return {
            "status": "healthy",
            "hit_rate": metrics.hit_rate,
            "cache_size": metrics.cache_size
        } 