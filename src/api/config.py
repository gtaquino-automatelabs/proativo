"""
Configuração centralizada para a aplicação PROAtivo.

Este módulo gerencia todas as configurações do sistema usando
Pydantic BaseSettings com suporte a variáveis de ambiente.
"""

from functools import lru_cache
from typing import List, Optional, Union
from pydantic import ConfigDict, field_validator, ValidationInfo, Field
from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    """
    Configurações da aplicação PROAtivo.
    
    Todas as configurações podem ser definidas via variáveis de ambiente
    ou arquivo .env na raiz do projeto.
    """
    
    # =============================================================================
    # CONFIGURAÇÕES DA APLICAÇÃO
    # =============================================================================
    
    app_name: str = "PROAtivo API"
    app_version: str = "1.0.0"
    app_description: str = "Sistema Inteligente de Apoio à Decisão para Manutenção de Ativos Elétricos"
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = True
    
    # =============================================================================
    # CONFIGURAÇÕES DO SERVIDOR
    # =============================================================================
    
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    
    # =============================================================================
    # CONFIGURAÇÕES DE CORS
    # =============================================================================
    
    # CORS como strings simples que serão convertidas em listas por properties
    cors_origins_str: str = Field(
        default="http://localhost:8501,http://localhost:3000,http://127.0.0.1:8501,http://127.0.0.1:3000",
        env="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = True
    cors_allow_methods_str: str = "GET,POST,PUT,DELETE,OPTIONS"
    cors_allow_headers_str: str = "*"
    
    @property
    def cors_origins(self) -> List[str]:
        """Retorna CORS origins como lista."""
        if isinstance(self.cors_origins_str, str):
            return [item.strip() for item in self.cors_origins_str.split(",") if item.strip()]
        return []
    
    @property
    def cors_allow_methods(self) -> List[str]:
        """Retorna CORS methods como lista."""
        if isinstance(self.cors_allow_methods_str, str):
            return [item.strip() for item in self.cors_allow_methods_str.split(",") if item.strip()]
        return ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    
    @property
    def cors_allow_headers(self) -> List[str]:
        """Retorna CORS headers como lista."""
        if self.cors_allow_headers_str == "*":
            return ["*"]
        elif isinstance(self.cors_allow_headers_str, str):
            return [item.strip() for item in self.cors_allow_headers_str.split(",") if item.strip()]
        return ["*"]
    
    # =============================================================================
    # CONFIGURAÇÕES DO BANCO DE DADOS
    # =============================================================================
    
    database_url: str = Field(
        default="postgresql+asyncpg://proativo:proativo123@localhost:5432/proativo",
        env="DATABASE_URL"
    )
    database_echo: bool = False  # Log SQL queries em desenvolvimento
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_pool_timeout: int = 30
    
    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v):
        """Valida se a URL do banco está correta."""
        if not v.startswith(("postgresql://", "postgresql+asyncpg://")):
            raise ValueError("Database URL deve começar com postgresql:// ou postgresql+asyncpg://")
        return v
    
    # =============================================================================
    # CONFIGURAÇÕES DO GOOGLE GEMINI
    # =============================================================================
    
    google_api_key: Optional[str] = Field(default=None)
    gemini_model: str = Field(default="gemini-2.5-flash", env="GEMINI_MODEL")
    gemini_temperature: float = 0.1
    gemini_max_tokens: int = 2048
    gemini_timeout: int = 30
    gemini_max_retries: int = 3
    
    @field_validator("google_api_key")
    @classmethod
    def validate_google_api_key(cls, v):
        """Valida se a chave da API do Gemini está presente e válida."""
        # Se não há valor, emite warning mas permite continuar
        if v is None:
            import warnings
            warnings.warn("GOOGLE_API_KEY não configurada. Funcionalidades de IA não estarão disponíveis.")
            return None
        
        # Se é string vazia, trata como None
        if isinstance(v, str) and v.strip() == "":
            import warnings
            warnings.warn("GOOGLE_API_KEY vazia. Funcionalidades de IA não estarão disponíveis.")
            return None
        
        # Se é string válida, valida o formato
        if isinstance(v, str):
            v_clean = v.strip()
            # Validação básica do formato da chave Google
            if v_clean.startswith("AIza") and len(v_clean) >= 30:
                return v_clean
            else:
                import warnings
                warnings.warn("GOOGLE_API_KEY com formato inválido. Verificar configuração.")
                return None
        
        # Para outros tipos, retorna como está
        return v
    
    # =============================================================================
    # CONFIGURAÇÕES DE LOGGING
    # =============================================================================
    
    log_level: str = "INFO"
    log_format: str = "detailed"  # simple, detailed, json
    log_file: Optional[str] = None
    log_max_size: int = 10 * 1024 * 1024  # 10MB
    log_backup_count: int = 5
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """Valida o nível de log."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level deve ser um de: {valid_levels}")
        return v.upper()
    
    # =============================================================================
    # CONFIGURAÇÕES DE CACHE
    # =============================================================================
    
    cache_enabled: bool = True
    cache_ttl: int = 3600  # 1 hora em segundos
    cache_max_size: int = 1000  # Máximo de itens em cache
    
    # =============================================================================
    # CONFIGURAÇÕES DE UPLOAD
    # =============================================================================
    
    upload_max_size: int = 50 * 1024 * 1024  # 50MB
    upload_allowed_extensions_str: str = ".csv,.xlsx,.xls,.xml"
    
    @property
    def upload_allowed_extensions(self) -> List[str]:
        """Retorna extensões permitidas como lista."""
        if isinstance(self.upload_allowed_extensions_str, str):
            return [ext.strip() for ext in self.upload_allowed_extensions_str.split(",") if ext.strip()]
        return [".csv", ".xlsx", ".xls", ".xml"]
    upload_directory: str = "data/uploads"
    
    # =============================================================================
    # CONFIGURAÇÕES DE SEGURANÇA
    # =============================================================================
    
    secret_key: str = Field(default="dev-proativo-secret-key-2024-super-secure", env="SECRET_KEY")
    access_token_expire_minutes: int = 30
    algorithm: str = "HS256"
    
    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v, info: ValidationInfo):
        """Valida se a chave secreta foi alterada em produção."""
        if info.data.get("environment") == "production" and v == "dev-secret-key-change-in-production":
            raise ValueError("SECRET_KEY deve ser alterada em produção!")
        return v
    
    # =============================================================================
    # CONFIGURAÇÕES DE RATE LIMITING
    # =============================================================================
    
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 3600  # 1 hora
    
    # =============================================================================
    # CONFIGURAÇÕES DE MONITORAMENTO
    # =============================================================================
    
    health_check_timeout: int = 10
    metrics_enabled: bool = True
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # CRUCIAL: Ignora campos extras do .env
        env_ignore_empty=True,  # Ignora valores vazios
        validate_default=True,  # Valida valores padrão
    )
    
    def get_database_url(self, async_fallback: bool = True) -> str:
        """
        Retorna URL do banco de dados com fallback para versão síncrona.
        
        Args:
            async_fallback: Se deve usar driver async como fallback
            
        Returns:
            URL do banco de dados
        """
        if async_fallback and not self.database_url.startswith("postgresql+asyncpg://"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://")
        return self.database_url
    
    def is_development(self) -> bool:
        """Verifica se está em ambiente de desenvolvimento."""
        return self.environment.lower() in ["development", "dev", "local"]
    
    def is_production(self) -> bool:
        """Verifica se está em ambiente de produção."""
        return self.environment.lower() in ["production", "prod"]
    
    def is_testing(self) -> bool:
        """Verifica se está em ambiente de teste."""
        return self.environment.lower() in ["testing", "test"]


# =============================================================================
# INSTÂNCIA GLOBAL DE CONFIGURAÇÃO
# =============================================================================

@lru_cache()
def get_settings() -> Settings:
    """
    Retorna instância singleton das configurações.
    
    Usa cache para evitar recriar as configurações a cada chamada.
    Para limpar o cache (útil em testes), chame: get_settings.cache_clear()
    
    Returns:
        Settings: Instância das configurações
    """
    return Settings()


# Instância global para importação direta
settings = get_settings()


# =============================================================================
# CONFIGURAÇÕES ESPECÍFICAS POR AMBIENTE
# =============================================================================

def get_environment_specific_settings() -> dict:
    """
    Retorna configurações específicas baseadas no ambiente atual.
    
    Returns:
        dict: Configurações específicas do ambiente
    """
    if settings.is_development():
        return {
            "database_echo": True,
            "log_level": "DEBUG",
            "debug": True,
            "reload": True,
        }
    elif settings.is_production():
        return {
            "database_echo": False,
            "log_level": "WARNING",
            "debug": False,
            "reload": False,
        }
    elif settings.is_testing():
        return {
            "database_echo": False,
            "log_level": "ERROR",
            "debug": False,
            "reload": False,
        }
    else:
        return {}


# =============================================================================
# VALIDAÇÕES ADICIONAIS
# =============================================================================

def validate_configuration() -> None:
    """
    Executa validações adicionais da configuração durante a inicialização.
    
    Raises:
        ValueError: Se alguma configuração estiver inválida
    """
    # Verificar se diretório de upload existe
    if not os.path.exists(settings.upload_directory):
        try:
            os.makedirs(settings.upload_directory, exist_ok=True)
        except OSError as e:
            raise ValueError(f"Não foi possível criar diretório de upload: {e}")
    
    # Verificar configurações de produção
    if settings.is_production():
        if settings.secret_key == "dev-secret-key-change-in-production":
            raise ValueError("SECRET_KEY deve ser alterada em produção!")
        
        if settings.google_api_key is None:
            raise ValueError("GOOGLE_API_KEY é obrigatória em produção!")
    
    # Log das configurações principais (sem dados sensíveis)
    try:
        from ..utils.logger import get_logger
        logger = get_logger(__name__)
    except ImportError:
        # Fallback para logging padrão se import relativo falhar
        import logging
        logger = logging.getLogger(__name__)
    
    logger.info("Configuração carregada com sucesso", extra={
        "environment": settings.environment,
        "app_version": settings.app_version,
        "database_configured": bool(settings.database_url),
        "gemini_configured": bool(settings.google_api_key),
        "cache_enabled": settings.cache_enabled,
        "debug": settings.debug,
    })


# Executar validação automaticamente na importação
if __name__ != "__main__":
    validate_configuration() 