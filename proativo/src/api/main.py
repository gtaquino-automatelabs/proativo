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
from .endpoints import health

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


# Criar instância da aplicação FastAPI
app = FastAPI(
    title="PROAtivo API",
    description="Sistema Inteligente de Apoio à Decisão para Manutenção de Ativos Elétricos",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Configuração de CORS
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:8501,http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Middleware de hosts confiáveis (segurança)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Em produção, especificar hosts específicos
)


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


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handler para exceções HTTP.
    
    Args:
        request: Requisição HTTP
        exc: Exceção HTTP
        
    Returns:
        JSONResponse: Resposta de erro padronizada
    """
    logger.error(
        f"HTTP Exception: {exc.status_code} - {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": request.url.path
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Exception",
            "message": exc.detail,
            "status_code": exc.status_code,
            "path": request.url.path
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Handler para exceções gerais.
    
    Args:
        request: Requisição HTTP
        exc: Exceção geral
        
    Returns:
        JSONResponse: Resposta de erro padronizada
    """
    logger.error(
        f"Unexpected error: {str(exc)}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "exception_type": type(exc).__name__
        }
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "path": request.url.path
        }
    )


# Incluir routers
app.include_router(health.router)


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
    return {
        "message": "PROAtivo API - Sistema Inteligente de Apoio à Decisão",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
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
    return {
        "name": "PROAtivo",
        "description": "Sistema Inteligente de Apoio à Decisão para Manutenção de Ativos Elétricos",
        "version": "0.1.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "features": [
            "Consultas em linguagem natural",
            "Processamento de dados ETL (CSV, XML, XLSX)",
            "Sistema RAG com Google Gemini",
            "Interface conversacional",
            "Sistema de feedback"
        ],
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }


# Para desenvolvimento local
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 