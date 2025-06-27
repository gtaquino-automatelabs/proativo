"""
Sistema de logging estruturado para o projeto PROAtivo.

Este módulo fornece configuração centralizada de logging com:
- Formatação estruturada (JSON quando possível)
- Múltiplos handlers (console, arquivo)
- Diferentes níveis por ambiente
- Contextualização de logs com request IDs
- Sanitização de dados sensíveis
"""

import logging
import logging.config
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional
import json
from datetime import datetime


class CustomFormatter(logging.Formatter):
    """Formatter customizado para logs estruturados."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Formatar log record como JSON estruturado."""
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Adicionar informações extras se disponíveis
        if hasattr(record, 'request_id'):
            log_entry["request_id"] = record.request_id
            
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id
            
        if hasattr(record, 'duration'):
            log_entry["duration_ms"] = record.duration
            
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
            
        # Adicionar campos extras do record
        extra_fields = {
            k: v for k, v in record.__dict__.items() 
            if k not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                'thread', 'threadName', 'processName', 'process', 'getMessage',
                'request_id', 'user_id', 'duration'
            }
        }
        
        if extra_fields:
            log_entry["extra"] = extra_fields
            
        return json.dumps(log_entry, ensure_ascii=False, default=str)


class SanitizingFormatter(logging.Formatter):
    """Formatter que sanitiza dados sensíveis nos logs."""
    
    SENSITIVE_FIELDS = {
        'password', 'token', 'api_key', 'secret', 'authorization',
        'cookie', 'session', 'csrf', 'jwt', 'bearer'
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Sanitizar dados sensíveis antes de formatar."""
        # Sanitizar a mensagem
        message = record.getMessage()
        for field in self.SENSITIVE_FIELDS:
            if field.lower() in message.lower():
                # Mascarar valores sensíveis
                import re
                pattern = f'({field}["\']?\\s*[:=]\\s*["\']?)([^\\s,"\'\\]}}]+)'
                message = re.sub(pattern, r'\1***', message, flags=re.IGNORECASE)
        
        # Atualizar o record
        record.msg = message
        record.args = ()
        
        return super().format(record)


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    enable_json: bool = True,
    enable_console: bool = True
) -> None:
    """
    Configurar sistema de logging para a aplicação.
    
    Args:
        level: Nível de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Caminho para arquivo de log (opcional)
        enable_json: Se deve usar formatação JSON estruturada
        enable_console: Se deve habilitar logging no console
    """
    # Criar diretório de logs se necessário
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configuração base
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structured": {
                "()": CustomFormatter,
            },
            "simple": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "sanitizing": {
                "()": SanitizingFormatter,
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {},
        "root": {
            "level": level,
            "handlers": []
        },
        "loggers": {
            "proativo": {
                "level": level,
                "handlers": [],
                "propagate": False
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": [],
                "propagate": False
            },
            "sqlalchemy": {
                "level": "WARNING",
                "handlers": [],
                "propagate": False
            }
        }
    }
    
    # Handler para console
    if enable_console:
        config["handlers"]["console"] = {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "structured" if enable_json else "sanitizing",
            "level": level
        }
        config["root"]["handlers"].append("console")
        config["loggers"]["proativo"]["handlers"].append("console")
        config["loggers"]["uvicorn"]["handlers"].append("console")
        config["loggers"]["sqlalchemy"]["handlers"].append("console")
    
    # Handler para arquivo
    if log_file:
        config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": log_file,
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 5,
            "formatter": "structured" if enable_json else "sanitizing",
            "level": level,
            "encoding": "utf-8"
        }
        config["root"]["handlers"].append("file")
        config["loggers"]["proativo"]["handlers"].append("file")
        config["loggers"]["uvicorn"]["handlers"].append("file")
        config["loggers"]["sqlalchemy"]["handlers"].append("file")
    
    # Aplicar configuração
    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    """
    Obter logger configurado para um módulo específico.
    
    Args:
        name: Nome do logger (geralmente __name__)
        
    Returns:
        Logger configurado
    """
    return logging.getLogger(f"proativo.{name}")


class LogContext:
    """Context manager para adicionar contexto aos logs."""
    
    def __init__(self, **context: Any):
        self.context = context
        self.old_factory = logging.getLogRecordFactory()
    
    def __enter__(self):
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self.old_factory)


def log_performance(func_name: str, duration_ms: float, **kwargs: Any) -> None:
    """
    Log de performance para monitoramento.
    
    Args:
        func_name: Nome da função/operação
        duration_ms: Duração em milissegundos
        **kwargs: Contexto adicional
    """
    logger = get_logger("performance")
    logger.info(
        f"Performance: {func_name}",
        extra={
            "duration": duration_ms,
            "operation": func_name,
            **kwargs
        }
    )


def log_llm_interaction(
    query: str,
    response: str,
    model: str,
    duration_ms: float,
    tokens_used: Optional[int] = None,
    **kwargs: Any
) -> None:
    """
    Log específico para interações com LLM.
    
    Args:
        query: Query do usuário (sanitizada)
        response: Resposta do LLM (resumida se muito longa)
        model: Modelo utilizado
        duration_ms: Duração da chamada
        tokens_used: Tokens utilizados (se disponível)
        **kwargs: Contexto adicional
    """
    logger = get_logger("llm")
    
    # Truncar resposta se muito longa
    response_summary = response[:200] + "..." if len(response) > 200 else response
    
    logger.info(
        "LLM interaction completed",
        extra={
            "query_length": len(query),
            "response_length": len(response),
            "response_summary": response_summary,
            "model": model,
            "duration": duration_ms,
            "tokens_used": tokens_used,
            **kwargs
        }
    )


def log_data_processing(
    operation: str,
    file_type: str,
    records_processed: int,
    duration_ms: float,
    **kwargs: Any
) -> None:
    """
    Log específico para processamento de dados ETL.
    
    Args:
        operation: Tipo de operação (ingest, transform, load)
        file_type: Tipo de arquivo processado
        records_processed: Número de registros processados
        duration_ms: Duração do processamento
        **kwargs: Contexto adicional
    """
    logger = get_logger("etl")
    logger.info(
        f"Data processing: {operation}",
        extra={
            "operation": operation,
            "file_type": file_type,
            "records_processed": records_processed,
            "duration": duration_ms,
            **kwargs
        }
    )


# Configuração inicial baseada em variáveis de ambiente
def init_logging() -> None:
    """Inicializar logging com configurações do ambiente."""
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_file = os.getenv("LOG_FILE")
    environment = os.getenv("ENVIRONMENT", "development")
    
    # JSON logging apenas em produção
    enable_json = environment.lower() == "production"
    
    setup_logging(
        level=level,
        log_file=log_file,
        enable_json=enable_json,
        enable_console=True
    )
    
    # Log inicial
    logger = get_logger("system")
    logger.info(
        "Logging system initialized",
        extra={
            "level": level,
            "log_file": log_file,
            "environment": environment,
            "json_format": enable_json
        }
    )


# Inicializar automaticamente quando importado
if __name__ != "__main__":
    init_logging() 