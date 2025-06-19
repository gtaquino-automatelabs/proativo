"""
Sistema de tratamento centralizado de erros para o sistema PROAtivo.

Este módulo fornece:
- Hierarquia de exceções customizadas
- Handlers de erro para FastAPI
- Formatação padronizada de respostas de erro
- Logging estruturado de erros
"""

from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import traceback
from datetime import datetime

from .logger import get_logger

logger = get_logger(__name__)


# =============================================================================
# EXCEÇÕES CUSTOMIZADAS
# =============================================================================

class PROAtivoException(Exception):
    """Exceção base para o sistema PROAtivo."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.status_code = status_code
        super().__init__(self.message)


class DataProcessingError(PROAtivoException):
    """Erros durante ingestão/processamento de dados."""
    
    def __init__(self, message: str, file_path: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        if file_path:
            details['file_path'] = file_path
        
        super().__init__(
            message=message,
            error_code="DATA_PROCESSING_ERROR",
            details=details,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


class LLMServiceError(PROAtivoException):
    """Erros da integração com serviço LLM."""
    
    def __init__(self, message: str, service_name: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        if service_name:
            details['service_name'] = service_name
        
        super().__init__(
            message=message,
            error_code="LLM_SERVICE_ERROR",
            details=details,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


class DatabaseError(PROAtivoException):
    """Erros de banco de dados."""
    
    def __init__(self, message: str, operation: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        if operation:
            details['operation'] = operation
        
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            details=details,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


class ValidationError(PROAtivoException):
    """Erros de validação de dados."""
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        if field:
            details['field'] = field
        
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details=details,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class AuthenticationError(PROAtivoException):
    """Erros de autenticação."""
    
    def __init__(self, message: str = "Authentication required", **kwargs):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            details=kwargs.get('details', {}),
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class AuthorizationError(PROAtivoException):
    """Erros de autorização."""
    
    def __init__(self, message: str = "Access denied", **kwargs):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            details=kwargs.get('details', {}),
            status_code=status.HTTP_403_FORBIDDEN
        )


class ResourceNotFoundError(PROAtivoException):
    """Erros de recurso não encontrado."""
    
    def __init__(self, message: str, resource_type: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        if resource_type:
            details['resource_type'] = resource_type
        
        super().__init__(
            message=message,
            error_code="RESOURCE_NOT_FOUND",
            details=details,
            status_code=status.HTTP_404_NOT_FOUND
        )


# =============================================================================
# FORMATADORES DE RESPOSTA DE ERRO
# =============================================================================

def create_error_response(
    error: Exception,
    request: Request,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    include_traceback: bool = False
) -> Dict[str, Any]:
    """
    Cria uma resposta de erro padronizada.
    
    Args:
        error: Exceção ocorrida
        request: Request HTTP
        status_code: Código de status HTTP
        include_traceback: Se deve incluir traceback no response
        
    Returns:
        Dict com os dados do erro formatados
    """
    error_data = {
        "error": True,
        "timestamp": datetime.now().isoformat(),
        "path": str(request.url.path),
        "method": request.method,
        "status_code": status_code,
        "message": str(error),
        "error_code": getattr(error, 'error_code', error.__class__.__name__),
        "details": getattr(error, 'details', {})
    }
    
    # Adicionar traceback em desenvolvimento
    if include_traceback:
        error_data["traceback"] = traceback.format_exc()
    
    # Adicionar request_id se disponível
    if hasattr(request.state, 'request_id'):
        error_data["request_id"] = request.state.request_id
    
    return error_data


# =============================================================================
# HANDLERS DE ERRO PARA FASTAPI
# =============================================================================

async def proativo_exception_handler(request: Request, exc: PROAtivoException) -> JSONResponse:
    """
    Handler para exceções customizadas do PROAtivo.
    
    Args:
        request: Request HTTP
        exc: Exceção customizada do PROAtivo
        
    Returns:
        JSONResponse com erro formatado
    """
    logger.error(
        f"PROAtivo Exception: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
            "details": exc.details
        },
        exc_info=True
    )
    
    error_response = create_error_response(exc, request, exc.status_code)
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handler para exceções HTTP do FastAPI.
    
    Args:
        request: Request HTTP
        exc: Exceção HTTP
        
    Returns:
        JSONResponse com erro formatado
    """
    logger.warning(
        f"HTTP Exception: {exc.status_code} - {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
            "detail": exc.detail
        }
    )
    
    error_response = create_error_response(exc, request, exc.status_code)
    error_response["message"] = exc.detail
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handler para erros de validação do Pydantic.
    
    Args:
        request: Request HTTP
        exc: Erro de validação
        
    Returns:
        JSONResponse com erro formatado
    """
    logger.warning(
        f"Validation Error: {len(exc.errors())} errors",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": exc.errors()
        }
    )
    
    # Formatar erros de validação
    validation_errors = []
    for error in exc.errors():
        validation_errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
            "input": error.get("input")
        })
    
    error_response = create_error_response(exc, request, status.HTTP_422_UNPROCESSABLE_ENTITY)
    error_response["message"] = "Validation error"
    error_response["validation_errors"] = validation_errors
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handler para exceções gerais não tratadas.
    
    Args:
        request: Request HTTP
        exc: Exceção geral
        
    Returns:
        JSONResponse com erro formatado
    """
    logger.error(
        f"Unexpected error: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__
        },
        exc_info=True
    )
    
    # Em produção, não expor detalhes internos
    error_message = "An unexpected error occurred"
    error_response = create_error_response(
        exc, 
        request, 
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        include_traceback=False  # Nunca expor traceback em produção
    )
    error_response["message"] = error_message
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response
    )


# =============================================================================
# CONFIGURAÇÃO DOS HANDLERS
# =============================================================================

def setup_error_handlers(app: FastAPI) -> None:
    """
    Configura todos os handlers de erro para a aplicação FastAPI.
    
    Args:
        app: Instância da aplicação FastAPI
    """
    # Exceções customizadas do PROAtivo
    app.add_exception_handler(PROAtivoException, proativo_exception_handler)
    
    # Exceções específicas
    app.add_exception_handler(DataProcessingError, proativo_exception_handler)
    app.add_exception_handler(LLMServiceError, proativo_exception_handler)
    app.add_exception_handler(DatabaseError, proativo_exception_handler)
    app.add_exception_handler(ValidationError, proativo_exception_handler)
    app.add_exception_handler(AuthenticationError, proativo_exception_handler)
    app.add_exception_handler(AuthorizationError, proativo_exception_handler)
    app.add_exception_handler(ResourceNotFoundError, proativo_exception_handler)
    
    # Exceções do FastAPI
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    
    # Exceções gerais (fallback)
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("Error handlers configured successfully")


# =============================================================================
# UTILITÁRIOS PARA LOGGING DE ERROS
# =============================================================================

def log_error_context(
    error: Exception,
    context: Dict[str, Any],
    level: str = "error"
) -> None:
    """
    Registra erro com contexto adicional.
    
    Args:
        error: Exceção ocorrida
        context: Contexto adicional para logging
        level: Nível de log (error, warning, info)
    """
    log_func = getattr(logger, level, logger.error)
    
    log_func(
        f"Error in context: {str(error)}",
        extra={
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context
        },
        exc_info=True
    )


def create_user_friendly_message(error: Exception) -> str:
    """
    Cria mensagem amigável para o usuário baseada no tipo de erro.
    
    Args:
        error: Exceção ocorrida
        
    Returns:
        Mensagem amigável para o usuário
    """
    if isinstance(error, DataProcessingError):
        return "Erro ao processar os dados. Verifique o formato do arquivo."
    
    elif isinstance(error, LLMServiceError):
        return "Serviço de IA temporariamente indisponível. Tente novamente em alguns instantes."
    
    elif isinstance(error, DatabaseError):
        return "Erro interno do sistema. Nossa equipe foi notificada."
    
    elif isinstance(error, ValidationError):
        return f"Dados inválidos: {error.message}"
    
    elif isinstance(error, ResourceNotFoundError):
        return "Recurso solicitado não foi encontrado."
    
    elif isinstance(error, (AuthenticationError, AuthorizationError)):
        return "Acesso não autorizado."
    
    else:
        return "Ocorreu um erro inesperado. Nossa equipe foi notificada." 