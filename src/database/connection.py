"""
Configuração de conexão com PostgreSQL usando SQLAlchemy async.

Este módulo configura a engine do SQLAlchemy, sessionmaker e fornece
funções utilitárias para gerenciamento de sessões de banco de dados.
"""

import logging
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession, 
    AsyncEngine,
    async_sessionmaker, 
    create_async_engine
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy import event, text
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class DatabaseSettings(BaseSettings):
    """Configurações do banco de dados."""
    
    database_url: str
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_pool_timeout: int = 30
    database_pool_recycle: int = 3600
    debug: bool = False
    
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


class Base(DeclarativeBase):
    """Classe base para modelos SQLAlchemy."""
    pass


class DatabaseConnection:
    """Gerenciador de conexão com banco de dados PostgreSQL."""
    
    def __init__(self, settings: Optional[DatabaseSettings] = None):
        """Inicializa a conexão com o banco de dados.
        
        Args:
            settings: Configurações do banco de dados. Se None, carrega do .env
        """
        self.settings = settings or DatabaseSettings()
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None
        
    async def initialize(self) -> None:
        """Inicializa a engine e sessionmaker."""
        if self._engine is not None:
            logger.warning("Database connection já foi inicializada")
            return
            
        logger.info("Inicializando conexão com banco de dados PostgreSQL")
        
        # Configurações da engine
        engine_kwargs = {
            "echo": self.settings.debug,
            "future": True,
            "pool_size": self.settings.database_pool_size,
            "max_overflow": self.settings.database_max_overflow,
            "pool_timeout": self.settings.database_pool_timeout,
            "pool_recycle": self.settings.database_pool_recycle,
            "pool_pre_ping": True,  # Verifica conexões antes de usar
        }
        
        # Para testes, usar NullPool
        if "test" in self.settings.database_url or self.settings.debug:
            engine_kwargs["poolclass"] = NullPool
            
        self._engine = create_async_engine(
            self.settings.database_url,
            **engine_kwargs
        )
        
        # Configurar evento para log de conexões
        if self.settings.debug:
            event.listen(self._engine.sync_engine, "connect", self._on_connect)
            event.listen(self._engine.sync_engine, "checkout", self._on_checkout)
        
        # Criar sessionmaker
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
        
        logger.info("Conexão com banco de dados PostgreSQL inicializada com sucesso")
    
    async def close(self) -> None:
        """Fecha a conexão com o banco de dados."""
        if self._engine is None:
            return
            
        logger.info("Fechando conexão com banco de dados")
        await self._engine.dispose()
        self._engine = None
        self._session_factory = None
        logger.info("Conexão com banco de dados fechada")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Context manager para obter uma sessão do banco.
        
        Yields:
            AsyncSession: Sessão do SQLAlchemy
            
        Raises:
            RuntimeError: Se a conexão não foi inicializada
        """
        if self._session_factory is None:
            raise RuntimeError("Database connection não foi inicializada. Chame initialize() primeiro.")
        
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    def get_session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Retorna o sessionmaker para injeção de dependência.
        
        Returns:
            async_sessionmaker: Factory de sessões
            
        Raises:
            RuntimeError: Se a conexão não foi inicializada
        """
        if self._session_factory is None:
            raise RuntimeError("Database connection não foi inicializada. Chame initialize() primeiro.")
        return self._session_factory
    
    @property
    def engine(self) -> AsyncEngine:
        """Retorna a engine do banco.
        
        Returns:
            AsyncEngine: Engine do SQLAlchemy
            
        Raises:
            RuntimeError: Se a conexão não foi inicializada
        """
        if self._engine is None:
            raise RuntimeError("Database connection não foi inicializada. Chame initialize() primeiro.")
        return self._engine
    
    def _on_connect(self, dbapi_connection, connection_record):
        """Callback executado quando uma conexão é estabelecida."""
        logger.debug(f"Nova conexão estabelecida: {connection_record}")
    
    def _on_checkout(self, dbapi_connection, connection_record, connection_proxy):
        """Callback executado quando uma conexão é retirada do pool."""
        logger.debug(f"Conexão retirada do pool: {connection_record}")


# Instância global da conexão
db_connection = DatabaseConnection()


async def init_database() -> None:
    """Inicializa a conexão com o banco de dados."""
    await db_connection.initialize()


async def close_database() -> None:
    """Fecha a conexão com o banco de dados."""
    await db_connection.close()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency para obter sessão do banco (FastAPI).
    
    Yields:
        AsyncSession: Sessão do banco de dados
    """
    async with db_connection.get_session() as session:
        yield session


async def create_tables() -> None:
    """Cria todas as tabelas no banco de dados.
    
    Função utilitária para desenvolvimento e testes.
    Em produção, usar Alembic para migrations.
    """
    logger.info("Criando tabelas no banco de dados")
    async with db_connection.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Tabelas criadas com sucesso")


async def drop_tables() -> None:
    """Remove todas as tabelas do banco de dados.
    
    Função utilitária para desenvolvimento e testes.
    ⚠️ CUIDADO: Remove todos os dados!
    """
    logger.warning("Removendo todas as tabelas do banco de dados")
    async with db_connection.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.warning("Todas as tabelas foram removidas")


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Função para obter sessão assíncrona diretamente (compatibilidade).
    
    Esta função fornece compatibilidade com código existente que espera
    get_async_session() ao invés de get_db_session().
    
    Yields:
        AsyncSession: Sessão do banco de dados
    """
    async with db_connection.get_session() as session:
        yield session


async def check_database_connection() -> bool:
    """Verifica se a conexão com o banco está funcionando.
    
    Returns:
        bool: True se conectou com sucesso, False caso contrário
    """
    try:
        async with db_connection.get_session() as session:
            await session.execute(text("SELECT 1"))
        logger.info("Conexão com banco de dados verificada com sucesso")
        return True
    except Exception as e:
        logger.error(f"Erro ao verificar conexão com banco: {e}")
        return False
