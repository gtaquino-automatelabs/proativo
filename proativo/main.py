"""
Ponto de entrada principal para a aplicação PROAtivo.

Este arquivo é usado pelo Docker e uvicorn para inicializar a aplicação FastAPI.
"""

from src.api.main import app

# Expor a aplicação para o uvicorn
__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    from src.api.config import get_settings
    
    settings = get_settings()
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_config=None,
    )
