"""
Aplicação FastAPI principal do sistema PROAtivo.

Este módulo configura a aplicação FastAPI com:
- Middleware de CORS
- Roteamento de endpoints
- Tratamento de erros
- Configuração de logging
- Documentação automática
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import time
from typing import AsyncGenerator

from ..utils.logger import get_logger, LogContext
from ..utils.error_handlers import setup_error_handlers
from .config import get_settings
from .endpoints import health, chat, feedback, fallback_demo, cache_demo, metrics_export

# Configurar logger
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Gerenciar ciclo de vida da aplicação.
    
    Args:
        app: Instância da aplicação FastAPI
    """
    # Startup
    logger.info("Starting PROAtivo application")
    
    # TODO: Inicializar conexões com banco de dados
    # TODO: Verificar conectividade com serviços externos
    # TODO: Carregar modelos ou cache inicial
    
    logger.info("PROAtivo application started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down PROAtivo application")
    
    # TODO: Fechar conexões com banco de dados
    # TODO: Limpar recursos
    
    logger.info("PROAtivo application shutdown complete")


def create_app() -> FastAPI:
    """
    Factory function para criar e configurar a aplicação FastAPI.
    
    Returns:
        FastAPI: Aplicação configurada
    """
    settings = get_settings()
    
    # Criar aplicação FastAPI
    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
        debug=settings.debug,
        docs_url="/docs" if settings.is_development() else None,
        redoc_url="/redoc" if settings.is_development() else None,
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    
    # Configurar CORS usando configurações centralizadas
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )
    
    # Middleware de hosts confiáveis (segurança)
    if not settings.is_development():
        # Em produção, usar hosts específicos
        allowed_hosts = ["api.proativo.com", "localhost"]  # Configurar hosts reais
    else:
        allowed_hosts = ["*"]
    
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=allowed_hosts
    )
    
    # Middleware de logging
    setup_logging_middleware(app)
    
    # Configurar tratamento centralizado de erros
    setup_error_handlers(app)
    
    # Incluir routers
    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])
    app.include_router(feedback.router, prefix="/api/v1", tags=["Feedback"])
    app.include_router(fallback_demo.router, prefix="/api/v1", tags=["Fallback Demo"])
    app.include_router(cache_demo.router, prefix="/api/v1", tags=["Cache Demo"])
    app.include_router(metrics_export.router, prefix="/api/v1", tags=["Metrics Export"])
    
    return app


def setup_logging_middleware(app: FastAPI) -> None:
    """
    Configura middleware de logging para a aplicação.
    
    Args:
        app: Instância da aplicação FastAPI
    """


    @app.middleware("http")
    async def logging_middleware(request: Request, call_next):
        """
        Middleware para logging de requisições com tempo de resposta.
        
        Args:
            request: Requisição HTTP
            call_next: Próximo middleware/endpoint
            
        Returns:
            Response: Resposta HTTP
        """
        start_time = time.time()
        
        # Gerar ID único para a requisição
        request_id = f"{int(time.time() * 1000)}-{id(request)}"
        
        # Adicionar request_id ao state para uso em error handlers
        request.state.request_id = request_id
        
        with LogContext(request_id=request_id):
            logger.info(
                f"Request started: {request.method} {request.url.path}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": str(request.query_params),
                    "client_ip": request.client.host if request.client else "unknown"
                }
            )
            
            # Processar requisição
            response = await call_next(request)
            
            # Calcular tempo de resposta
            duration = (time.time() - start_time) * 1000  # em milissegundos
            
            logger.info(
                f"Request completed: {request.method} {request.url.path}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration": round(duration, 2)
                }
            )
            
            # Adicionar header com tempo de resposta
            response.headers["X-Response-Time"] = f"{duration:.2f}ms"
            response.headers["X-Request-ID"] = request_id
            
        return response


# Criar instância da aplicação
app = create_app()


@app.get(
    "/",
    summary="Root Endpoint",
    description="Endpoint raiz da API PROAtivo"
)
async def root():
    """
    Endpoint raiz da API.
    
    Returns:
        Dict: Informações básicas da API
    """
    settings = get_settings()
    return {
        "message": f"{settings.app_name}",
        "version": settings.app_version,
        "environment": settings.environment,
        "docs": "/docs" if settings.is_development() else "disabled",
        "health": "/api/v1/health",
        "status": "running"
    }


@app.get(
    "/info",
    summary="Application Info",
    description="Informações detalhadas sobre a aplicação"
)
async def app_info():
    """
    Informações detalhadas sobre a aplicação.
    
    Returns:
        Dict: Informações da aplicação
    """
    settings = get_settings()
    return {
        "name": settings.app_name,
        "description": settings.app_description,
        "version": settings.app_version,
        "environment": settings.environment,
        "debug": settings.debug,
        "features": [
            "Consultas em linguagem natural",
            "Processamento de dados ETL (CSV, XML, XLSX)",
            "Sistema RAG com Google Gemini",
            "Interface conversacional",
            "Sistema de feedback",
            "Injeção de dependências",
            "Tratamento centralizado de erros"
        ],
        "endpoints": {
            "health": "/api/v1/health",
            "docs": "/docs" if settings.is_development() else "disabled",
            "redoc": "/redoc" if settings.is_development() else "disabled"
        },
        "configuration": {
            "cors_enabled": bool(settings.cors_origins),
            "database_configured": bool(settings.database_url),
            "gemini_configured": bool(settings.gemini_api_key),
            "cache_enabled": settings.cache_enabled,
        }
    }


# Para desenvolvimento local
if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    
    logger.info("Iniciando servidor de desenvolvimento...")
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_config=None,  # Usar nosso próprio logger
    ) 