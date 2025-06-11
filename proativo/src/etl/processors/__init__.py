"""
Processadores específicos para diferentes formatos de arquivo.

Este módulo contém implementações de processadores para:
- CSV: Processamento de arquivos separados por vírgula
- XML: Processamento de arquivos XML estruturados
- XLSX: Processamento de planilhas Excel
"""

from .base_processor import BaseProcessor
from .csv_processor import CSVProcessor
from .xml_processor import XMLProcessor
from .xlsx_processor import XLSXProcessor

__all__ = [
    'BaseProcessor',
    'CSVProcessor',
    'XMLProcessor',
    'XLSXProcessor'
]