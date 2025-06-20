"""
Sistema de Injeção de Dependências para o PROAtivo.

Este módulo fornece funções de dependência que o FastAPI usa para
automaticamente criar e injetar services e repositories nos endpoints.

Funciona como um "gerente de recursos" que:
- Cria cada serviço apenas quando necessário
- Reutiliza conexões quando possível
- Gerencia o ciclo de vida dos recursos
- Facilita testes com mock objects
"""

from functools import lru_cache
from typing import AsyncGenerator, Generator
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.exc import SQLAlchemyError
import asyncio

from .config import get_settings, Settings
from ..database.repositories import EquipmentRepository, MaintenanceRepository, RepositoryManager
from ..utils.logger import get_logger
from ..utils.error_handlers import DatabaseError, LLMServiceError
# Services imports movidos para lazy loading para evitar import circular

logger = get_logger(__name__)

# =============================================================================
# DEPENDÊNCIAS DE CONFIGURAÇÃO
# =============================================================================

def get_current_settings() -> Settings:
    """
    Dependência para obter as configurações atuais.
    
    Returns:
        Settings: Instância das configurações
    """
    return get_settings()


# =============================================================================
# DEPENDÊNCIAS DE BANCO DE DADOS
# =============================================================================

@lru_cache()
def get_database_engine():
    """
    Cria e retorna engine do banco de dados (singleton).
    
    Usa cache para garantir que apenas uma instância do engine seja criada.
    
    Returns:
        AsyncEngine: Engine do SQLAlchemy para conexões assíncronas
    """
    settings = get_settings()
    
    try:
        engine = create_async_engine(
            settings.get_database_url(),
            echo=settings.database_echo,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout,
            future=True,
        )
        
        logger.info("Database engine created successfully", extra={
            "database_url": settings.database_url.split("@")[0] + "@***",  # Mascarar senha
            "pool_size": settings.database_pool_size,
        })
        
        return engine
        
    except Exception as e:
        logger.error(f"Failed to create database engine: {str(e)}", exc_info=True)
        raise DatabaseError(
            message="Failed to initialize database connection",
            operation="create_engine",
            details={"error": str(e)}
        )


async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependência para obter sessão do banco de dados.
    
    Cria uma nova sessão para cada request e garante que seja fechada
    ao final, mesmo em caso de erro.
    
    Yields:
        AsyncSession: Sessão do banco de dados
        
    Raises:
        DatabaseError: Se houver erro na conexão com o banco
    """
    engine = get_database_engine()
    
    # Criar session maker
    async_session = async_sessionmaker(
        engine, 
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    session = None
    try:
        # Criar nova sessão
        session = async_session()
        
        logger.debug("Database session created")
        yield session
        
    except SQLAlchemyError as e:
        logger.error(f"Database session error: {str(e)}", exc_info=True)
        if session:
            await session.rollback()
        raise DatabaseError(
            message="Database operation failed",
            operation="session_management",
            details={"error": str(e)}
        )
        
    except Exception as e:
        logger.error(f"Unexpected error in database session: {str(e)}", exc_info=True)
        if session:
            await session.rollback()
        raise DatabaseError(
            message="Unexpected database error",
            operation="session_management",
            details={"error": str(e)}
        )
        
    finally:
        if session:
            await session.close()
            logger.debug("Database session closed")


# =============================================================================
# DEPENDÊNCIAS DE REPOSITORIES
# =============================================================================

async def get_equipment_repository(
    session: AsyncSession = Depends(get_database_session)
) -> EquipmentRepository:
    """
    Dependência para obter repository de equipamentos.
    
    Args:
        session: Sessão do banco de dados (injetada automaticamente)
        
    Returns:
        EquipmentRepository: Repository para operações com equipamentos
    """
    try:
        repository = EquipmentRepository(session)
        logger.debug("Equipment repository created")
        return repository
        
    except Exception as e:
        logger.error(f"Failed to create equipment repository: {str(e)}", exc_info=True)
        raise DatabaseError(
            message="Failed to initialize equipment repository",
            operation="create_repository",
            details={"repository_type": "equipment", "error": str(e)}
        )


async def get_maintenance_repository(
    session: AsyncSession = Depends(get_database_session)
) -> MaintenanceRepository:
    """
    Dependência para obter repository de manutenções.
    
    Args:
        session: Sessão do banco de dados (injetada automaticamente)
        
    Returns:
        MaintenanceRepository: Repository para operações com manutenções
    """
    try:
        repository = MaintenanceRepository(session)
        logger.debug("Maintenance repository created")
        return repository
        
    except Exception as e:
        logger.error(f"Failed to create maintenance repository: {str(e)}", exc_info=True)
        raise DatabaseError(
            message="Failed to initialize maintenance repository",
            operation="create_repository",
            details={"repository_type": "maintenance", "error": str(e)}
        )


async def get_repository_manager(
    session: AsyncSession = Depends(get_database_session)
) -> RepositoryManager:
    """
    Dependência para obter gerenciador de repositories.
    
    Args:
        session: Sessão do banco de dados (injetada automaticamente)
        
    Returns:
        RepositoryManager: Gerenciador centralizado de repositories
    """
    try:
        manager = RepositoryManager(session)
        logger.debug("Repository manager created")
        return manager
        
    except Exception as e:
        logger.error(f"Failed to create repository manager: {str(e)}", exc_info=True)
        raise DatabaseError(
            message="Failed to initialize repository manager",
            operation="create_repository_manager",
            details={"error": str(e)}
        )


# =============================================================================
# DEPENDÊNCIAS DE SERVICES (PREPARAÇÃO PARA PRÓXIMAS TAREFAS)
# =============================================================================

@lru_cache()
def get_llm_service():
    """
    Dependência para obter serviço de LLM (singleton).
    
    Cria uma única instância do serviço LLM que é reutilizada.
    Será implementado completamente na tarefa 4.0.
    
    Returns:
        LLMService: Serviço de integração com LLM
        
    Raises:
        LLMServiceError: Se não conseguir inicializar o serviço
    """
    settings = get_settings()
    
    if not settings.google_api_key:
        logger.warning("LLM service not available - API key not configured")
        raise LLMServiceError(
            message="LLM service not configured",
            service_name="Google Gemini",
            details={"reason": "API key not provided"}
        )
    
    try:
        # Placeholder para quando implementarmos o LLMService
        # from ..api.services.llm_service import LLMService
        # return LLMService(
        #     api_key=settings.google_api_key,
        #     model=settings.gemini_model,
        #     temperature=settings.gemini_temperature,
        #     max_tokens=settings.gemini_max_tokens,
        #     timeout=settings.gemini_timeout,
        #     max_retries=settings.gemini_max_retries
        # )
        
        # Por enquanto, retorna um mock placeholder
        class MockLLMService:
            def __init__(self):
                self.configured = True
                
            async def process_query(self, query: str, context: list = None):
                return "LLM service will be implemented in task 4.0"
        
        service = MockLLMService()
        logger.info("LLM service placeholder created")
        return service
        
    except Exception as e:
        logger.error(f"Failed to create LLM service: {str(e)}", exc_info=True)
        raise LLMServiceError(
            message="Failed to initialize LLM service",
            service_name="Google Gemini",
            details={"error": str(e)}
        )


@lru_cache()
def get_rag_service():
    """
    Dependência para obter serviço de RAG (singleton).
    
    Será implementado completamente na tarefa 4.0.
    
    Returns:
        RAGService: Serviço de Retrieval-Augmented Generation
    """
    try:
        # Placeholder para quando implementarmos o RAGService
        class MockRAGService:
            def __init__(self):
                self.configured = True
                
            async def retrieve_context(self, query: str):
                return ["Context will be implemented in task 4.0"]
        
        service = MockRAGService()
        logger.info("RAG service placeholder created")
        return service
        
    except Exception as e:
        logger.error(f"Failed to create RAG service: {str(e)}", exc_info=True)
        raise LLMServiceError(
            message="Failed to initialize RAG service",
            service_name="RAG",
            details={"error": str(e)}
        )


@lru_cache()
def get_query_processor():
    """
    Dependência para obter processador de queries (singleton).
    
    Será implementado completamente na tarefa 4.0.
    
    Returns:
        QueryProcessor: Processador de consultas em linguagem natural
    """
    try:
        # Placeholder para quando implementarmos o QueryProcessor
        class MockQueryProcessor:
            def __init__(self):
                self.configured = True
                
            async def process_natural_language_query(self, query: str):
                return "Query processing will be implemented in task 4.0"
        
        service = MockQueryProcessor()
        logger.info("Query processor placeholder created")
        return service
        
    except Exception as e:
        logger.error(f"Failed to create query processor: {str(e)}", exc_info=True)
        raise LLMServiceError(
            message="Failed to initialize query processor",
            service_name="QueryProcessor",
            details={"error": str(e)}
        )


@lru_cache()
def get_fallback_service():
    """
    Dependência para obter serviço de fallback (singleton).
    
    O sistema de fallback é usado quando o LLM não consegue responder
    adequadamente, fornecendo respostas alternativas baseadas em regras.
    
    Returns:
        FallbackService: Serviço de fallback para respostas inadequadas do LLM
        
    Raises:
        LLMServiceError: Se não conseguir inicializar o serviço
    """
    try:
        from .services.fallback_service import FallbackService
        
        service = FallbackService()
        logger.info("Fallback service created successfully")
        return service
        
    except Exception as e:
        logger.error(f"Failed to create fallback service: {str(e)}", exc_info=True)
        raise LLMServiceError(
            message="Failed to initialize fallback service",
            service_name="FallbackService",
            details={"error": str(e)}
        )


# =============================================================================
# DEPENDÊNCIAS DE VALIDAÇÃO E SEGURANÇA
# =============================================================================

async def validate_request_size(content_length: int = 0) -> None:
    """
    Dependência para validar tamanho do request.
    
    Args:
        content_length: Tamanho do conteúdo em bytes
        
    Raises:
        HTTPException: Se o request exceder o tamanho máximo
    """
    settings = get_settings()
    
    if content_length > settings.upload_max_size:
        logger.warning(f"Request too large: {content_length} bytes", extra={
            "max_size": settings.upload_max_size,
            "request_size": content_length
        })
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Request size ({content_length} bytes) exceeds maximum allowed "
                   f"({settings.upload_max_size} bytes)"
        )


# =============================================================================
# DEPENDÊNCIAS DE MONITORAMENTO
# =============================================================================

class RequestMetrics:
    """Classe para coletar métricas de request."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.request_count = 0
    
    def start(self):
        """Inicia medição de tempo."""
        import time
        self.start_time = time.time()
        self.request_count += 1
    
    def end(self):
        """Finaliza medição de tempo."""
        import time
        self.end_time = time.time()
    
    @property
    def duration(self) -> float:
        """Retorna duração em segundos."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0


async def get_request_metrics() -> RequestMetrics:
    """
    Dependência para obter métricas de request.
    
    Returns:
        RequestMetrics: Objeto para coletar métricas
    """
    metrics = RequestMetrics()
    metrics.start()
    return metrics


# =============================================================================
# DEPENDÊNCIAS COMBINADAS (CONVENIENCE FUNCTIONS)
# =============================================================================

async def get_database_dependencies(
    session: AsyncSession = Depends(get_database_session),
    equipment_repo: EquipmentRepository = Depends(get_equipment_repository),
    maintenance_repo: MaintenanceRepository = Depends(get_maintenance_repository)
) -> tuple[AsyncSession, EquipmentRepository, MaintenanceRepository]:
    """
    Dependência combinada para obter todos os recursos de banco de dados.
    
    Útil para endpoints que precisam de múltiplos repositories.
    
    Returns:
        tuple: (sessão, repository_equipamentos, repository_manutenções)
    """
    return session, equipment_repo, maintenance_repo


async def get_ai_services(
    llm_service = Depends(get_llm_service),
    rag_service = Depends(get_rag_service),
    query_processor = Depends(get_query_processor),
    fallback_service = Depends(get_fallback_service)
) -> tuple:
    """
    Dependência combinada para obter todos os serviços de IA.
    
    Útil para endpoints que precisam de múltiplos serviços de IA.
    
    Returns:
        tuple: (llm_service, rag_service, query_processor, fallback_service)
    """
    return llm_service, rag_service, query_processor, fallback_service


# =============================================================================
# UTILITÁRIOS PARA TESTES
# =============================================================================

def override_dependency(app, original_dependency, mock_dependency):
    """
    Utilitário para substituir dependências em testes.
    
    Args:
        app: Instância da aplicação FastAPI
        original_dependency: Função de dependência original
        mock_dependency: Função de dependência mock para testes
    """
    app.dependency_overrides[original_dependency] = mock_dependency


def clear_dependency_overrides(app):
    """
    Limpa todas as substituições de dependências.
    
    Args:
        app: Instância da aplicação FastAPI
    """
    app.dependency_overrides.clear()


# =============================================================================
# LIMPEZA DE CACHE
# =============================================================================

def clear_all_caches():
    """
    Limpa todos os caches de dependências.
    
    Útil para testes ou quando necessário recriar todas as dependências.
    """
    get_database_engine.cache_clear()
    get_llm_service.cache_clear()
    get_rag_service.cache_clear()
    get_query_processor.cache_clear()
    get_fallback_service.cache_clear()
    get_settings.cache_clear()
    
    logger.info("All dependency caches cleared")


async def get_cache_service():
    """
    Retorna instância do CacheService.
    
    Returns:
        CacheService: Instância do serviço de cache
    """
    from .services.cache_service import CacheService
    return CacheService() 