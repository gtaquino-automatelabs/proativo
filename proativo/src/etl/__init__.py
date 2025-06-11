"""
Módulo ETL (Extract, Transform, Load) do sistema PROAtivo.

Este módulo é responsável pelo processamento e ingestão de dados
de diferentes formatos (CSV, XML, XLSX) no banco de dados.
"""

from .data_processor import DataProcessor, DataProcessingError
from .data_ingestion import DataIngestionService, IngestionStatus

__all__ = [
    'DataProcessor',
    'DataProcessingError',
    'DataIngestionService',
    'IngestionStatus'
]