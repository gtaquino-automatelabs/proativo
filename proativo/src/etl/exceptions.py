"""
Exceções customizadas para o módulo ETL.
"""


class ETLException(Exception):
    """Exceção base para erros do módulo ETL."""
    pass


class DataProcessingError(ETLException):
    """Erro durante o processamento de dados."""
    pass


class ValidationError(ETLException):
    """Erro de validação de dados."""
    pass


class FileFormatError(ETLException):
    """Erro de formato de arquivo."""
    pass


class ConfigurationError(ETLException):
    """Erro de configuração do processamento."""
    pass 