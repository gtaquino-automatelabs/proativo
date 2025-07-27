"""
Endpoints de administração do sistema de cache inteligente.

Este módulo fornece endpoints para:
- Visualizar métricas detalhadas do cache
- Administrar cache (limpeza, invalidação)
- Configurar parâmetros dinamicamente
- Obter informações específicas de queries
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
import logging

from ..dependencies import get_cache_service
from ..services.cache_service import CacheService
from ...utils.logger import get_logger

# Configurar logger
logger = get_logger(__name__)

router = APIRouter(prefix="/cache", tags=["Cache Management"])


# Modelos de request/response


class CacheInfoResponse(BaseModel):
    """Response com informações sobre cache de uma query."""
    cache_key: str
    normalized_query: str
    exists_in_cache: bool
    similar_entries: List[Dict[str, Any]]
    recommendations: List[str]


class CacheInvalidationRequest(BaseModel):
    """Request para invalidação de cache."""
    pattern: Optional[str] = Field(default=None, description="Padrão regex para invalidar")
    tags: Optional[List[str]] = Field(default=None, description="Tags para invalidar")
    older_than_hours: Optional[int] = Field(default=None, description="Invalidar entradas mais antigas que X horas")





@router.get("/metrics", response_model=Dict[str, Any])
async def get_cache_metrics(
    cache_service: CacheService = Depends(get_cache_service)
) -> Dict[str, Any]:
    """
    Retorna métricas detalhadas do sistema de cache.
    
    Returns:
        Dict: Métricas completas do cache
    """
    try:
        metrics = await cache_service.get_metrics()
        health = await cache_service.get_health_status()
        
        return {
            "metrics": {
                "total_requests": metrics.total_requests,
                "cache_hits": metrics.cache_hits,
                "cache_misses": metrics.cache_misses,
                "hit_rate": metrics.hit_rate,
                "miss_rate": metrics.miss_rate,
                "cache_size": metrics.cache_size,
                "max_cache_size": metrics.max_cache_size,
                "expired_entries": metrics.expired_entries,
                "stale_entries": metrics.stale_entries,
                "memory_usage_mb": metrics.memory_usage_mb,
                "average_response_size": metrics.average_response_size
            },
            "health": health,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter métricas do cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao obter métricas: {str(e)}")


@router.get("/info/{query}", response_model=CacheInfoResponse)
async def get_cache_info(
    query: str,
    cache_service: CacheService = Depends(get_cache_service)
) -> CacheInfoResponse:
    """
    Retorna informações sobre o cache para uma query específica.
    
    Args:
        query: Query para verificar no cache
        cache_service: Serviço de cache
        
    Returns:
        CacheInfoResponse: Informações detalhadas sobre o cache
    """
    try:
        cache_info = await cache_service.get_cache_info(query)
        
        # Gerar recomendações baseadas no estado do cache
        recommendations = []
        
        if cache_info["exists_in_cache"]:
            recommendations.append("Query está no cache - resposta será rápida")
            
            # Verificar status da entrada
            if "status" in cache_info:
                if cache_info["status"] == "stale":
                    recommendations.append("Entrada está obsoleta - considere invalidar")
                elif cache_info["status"] == "expired":
                    recommendations.append("Entrada expirada - será removida automaticamente")
        else:
            recommendations.append("Query não está no cache - será mais lenta na primeira vez")
            
            if cache_info["similar_entries"]:
                recommendations.append("Existem queries similares no cache")
            else:
                recommendations.append("Nenhuma query similar no cache")
        
        return CacheInfoResponse(
            cache_key=cache_info["cache_key"],
            normalized_query=cache_info["normalized_query"],
            exists_in_cache=cache_info["exists_in_cache"],
            similar_entries=cache_info["similar_entries"],
            recommendations=recommendations
        )
        
    except Exception as e:
        logger.error(f"Erro ao obter informações do cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao obter informações: {str(e)}")


@router.post("/invalidate", response_model=Dict[str, Any])
async def invalidate_cache(
    request: CacheInvalidationRequest,
    cache_service: CacheService = Depends(get_cache_service)
) -> Dict[str, Any]:
    """
    Invalida entradas do cache baseado em critérios.
    
    Args:
        request: Critérios para invalidação
        cache_service: Serviço de cache
        
    Returns:
        Dict: Resultado da invalidação
    """
    try:
        older_than = None
        if request.older_than_hours:
            older_than = datetime.now() - timedelta(hours=request.older_than_hours)
        
        tags_set = set(request.tags) if request.tags else None
        
        invalidated_count = await cache_service.invalidate(
            pattern=request.pattern,
            tags=tags_set,
            older_than=older_than
        )
        
        logger.info(f"Cache invalidado: {invalidated_count} entradas removidas", extra={
            "pattern": request.pattern,
            "tags": request.tags,
            "older_than_hours": request.older_than_hours
        })
        
        return {
            "invalidated_entries": invalidated_count,
            "criteria": {
                "pattern": request.pattern,
                "tags": request.tags,
                "older_than_hours": request.older_than_hours
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao invalidar cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro na invalidação: {str(e)}")


@router.delete("/clear", response_model=Dict[str, Any])
async def clear_cache(
    cache_service: CacheService = Depends(get_cache_service)
) -> Dict[str, Any]:
    """
    Limpa completamente o cache.
    
    Returns:
        Dict: Resultado da limpeza
    """
    try:
        # Obter tamanho antes da limpeza
        metrics_before = await cache_service.get_metrics()
        size_before = metrics_before.cache_size
        
        await cache_service.clear()
        
        logger.info(f"Cache completamente limpo: {size_before} entradas removidas")
        
        return {
            "cleared": True,
            "entries_removed": size_before,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao limpar cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro na limpeza: {str(e)}")








# Endpoints administrativos
@router.post("/admin/configure", response_model=Dict[str, Any])
async def configure_cache(
    max_size: Optional[int] = Query(default=None, description="Tamanho máximo do cache"),
    default_ttl: Optional[int] = Query(default=None, description="TTL padrão em segundos"),
    similarity_threshold: Optional[float] = Query(default=None, description="Threshold de similaridade"),
    cache_service: CacheService = Depends(get_cache_service)
) -> Dict[str, Any]:
    """
    Configura parâmetros do cache dinamicamente.
    
    Args:
        max_size: Novo tamanho máximo
        default_ttl: Novo TTL padrão
        similarity_threshold: Novo threshold de similaridade
        cache_service: Serviço de cache
        
    Returns:
        Dict: Configuração atualizada
    """
    try:
        old_config = {
            "max_cache_size": cache_service.max_cache_size,
            "default_ttl": cache_service.default_ttl,
            "similarity_threshold": cache_service.similarity_threshold
        }
        
        # Atualizar configurações se fornecidas
        if max_size is not None:
            cache_service.max_cache_size = max_size
        
        if default_ttl is not None:
            cache_service.default_ttl = default_ttl
        
        if similarity_threshold is not None:
            if 0.0 <= similarity_threshold <= 1.0:
                cache_service.similarity_threshold = similarity_threshold
            else:
                raise ValueError("Threshold deve estar entre 0.0 e 1.0")
        
        new_config = {
            "max_cache_size": cache_service.max_cache_size,
            "default_ttl": cache_service.default_ttl,
            "similarity_threshold": cache_service.similarity_threshold
        }
        
        logger.info("Configuração do cache atualizada", extra={
            "old_config": old_config,
            "new_config": new_config
        })
        
        return {
            "updated": True,
            "old_configuration": old_config,
            "new_configuration": new_config,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao configurar cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro na configuração: {str(e)}") 