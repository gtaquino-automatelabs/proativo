"""
Endpoint de Health Check para monitoramento da aplicação PROAtivo.

Este módulo fornece endpoints para verificar o status da aplicação,
suas dependências e métricas básicas de funcionamento.
"""

from datetime import datetime
from typing import Dict, Any
import psutil
import os
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ...utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


class HealthResponse(BaseModel):
    """Modelo de resposta para health check."""
    status: str
    timestamp: datetime
    version: str
    environment: str
    uptime_seconds: float
    system: Dict[str, Any]


class DetailedHealthResponse(HealthResponse):
    """Modelo de resposta detalhada para health check."""
    dependencies: Dict[str, str]
    metrics: Dict[str, Any]


# Variável global para armazenar tempo de início
_start_time = datetime.now()


@router.get(
    "/",
    response_model=HealthResponse,
    summary="Health Check Básico",
    description="Endpoint básico para verificar se a aplicação está funcionando."
)
async def health_check() -> HealthResponse:
    """
    Endpoint básico de health check.
    
    Returns:
        HealthResponse: Status básico da aplicação
    """
    try:
        # Calcular uptime
        uptime = (datetime.now() - _start_time).total_seconds()
        
        # Informações do sistema
        system_info = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:').percent
        }
        
        response = HealthResponse(
            status="healthy",
            timestamp=datetime.now(),
            version=os.getenv("APP_VERSION", "0.1.0"),
            environment=os.getenv("ENVIRONMENT", "development"),
            uptime_seconds=uptime,
            system=system_info
        )
        
        logger.info("Health check completed successfully", extra={"uptime": uptime})
        return response
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Health check failed"
        )


@router.get(
    "/detailed",
    response_model=DetailedHealthResponse,
    summary="Health Check Detalhado",
    description="Endpoint detalhado para verificar aplicação e dependências."
)
async def detailed_health_check() -> DetailedHealthResponse:
    """
    Endpoint detalhado de health check incluindo dependências.
    
    Returns:
        DetailedHealthResponse: Status detalhado da aplicação e dependências
    """
    try:
        # Health check básico
        basic_health = await health_check()
        
        # Verificar dependências (simulado por enquanto)
        dependencies = {
            "database": "unknown",  # Será implementado quando tivermos a conexão
            "llm_service": "unknown",  # Será implementado quando tivermos o serviço LLM
            "file_storage": "healthy" if os.path.exists("/app/data") else "unhealthy"
        }
        
        # Métricas adicionais
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/') if os.name != 'nt' else psutil.disk_usage('C:')
        
        metrics = {
            "memory": {
                "total_mb": round(memory.total / 1024 / 1024, 2),
                "available_mb": round(memory.available / 1024 / 1024, 2),
                "used_percent": memory.percent
            },
            "disk": {
                "total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
                "free_gb": round(disk.free / 1024 / 1024 / 1024, 2),
                "used_percent": round((disk.used / disk.total) * 100, 2)
            },
            "process": {
                "pid": os.getpid(),
                "threads": psutil.Process().num_threads()
            }
        }
        
        response = DetailedHealthResponse(
            **basic_health.dict(),
            dependencies=dependencies,
            metrics=metrics
        )
        
        logger.info("Detailed health check completed", extra={"dependencies": dependencies})
        return response
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Detailed health check failed"
        )


@router.get(
    "/ready",
    summary="Readiness Check",
    description="Verifica se a aplicação está pronta para receber tráfego."
)
async def readiness_check() -> Dict[str, str]:
    """
    Endpoint de readiness check para Kubernetes/Docker.
    
    Returns:
        Dict: Status de prontidão da aplicação
    """
    try:
        # Verificações de prontidão (por enquanto sempre pronto)
        # TODO: Adicionar verificações de banco de dados quando implementado
        
        logger.info("Readiness check passed")
        return {"status": "ready", "timestamp": datetime.now().isoformat()}
        
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Application not ready"
        )


@router.get(
    "/live",
    summary="Liveness Check", 
    description="Verifica se a aplicação está viva (para Kubernetes)."
)
async def liveness_check() -> Dict[str, str]:
    """
    Endpoint de liveness check para Kubernetes.
    
    Returns:
        Dict: Status de vida da aplicação
    """
    try:
        # Verificação simples de liveness
        logger.info("Liveness check passed")
        return {"status": "alive", "timestamp": datetime.now().isoformat()}
        
    except Exception as e:
        logger.error(f"Liveness check failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Application not alive"
        ) 