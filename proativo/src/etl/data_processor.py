"""
Classe principal do pipeline ETL.

Orquestra o processamento de dados de diferentes formatos (CSV, XML, XLSX)
e coordena validação, transformação e carregamento no banco de dados.
"""

import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
from enum import Enum

from .processors.csv_processor import CSVProcessor
from .processors.xml_processor import XMLProcessor
from .processors.xlsx_processor import XLSXProcessor
from .exceptions import DataProcessingError, ValidationError, FileFormatError
from ..utils.validators import DataValidator
try:
    from ..database.repositories import RepositoryManager
except ImportError:
    RepositoryManager = None

logger = logging.getLogger(__name__)


class FileFormat(Enum):
    """Formatos de arquivo suportados."""
    CSV = "csv"
    XML = "xml"
    XLSX = "xlsx"


class DataType(Enum):
    """Tipos de dados suportados."""
    EQUIPMENT = "equipment"
    MAINTENANCE = "maintenance"
    DATA_HISTORY = "data_history"


class DataProcessor:
    """Processador principal de dados ETL."""
    
    def __init__(self, repository_manager: RepositoryManager = None):
        """Inicializa o processador ETL.
        
        Args:
            repository_manager: Gerenciador de repositórios para acesso ao banco
        """
        self.repository_manager = repository_manager
        self.validator = DataValidator()
        
        # Inicializa processadores específicos
        self.csv_processor = CSVProcessor()
        self.xml_processor = XMLProcessor()
        self.xlsx_processor = XLSXProcessor()
        
        # Estatísticas de processamento
        self.stats = {
            'files_processed': 0,
            'records_processed': 0,
            'records_valid': 0,
            'records_invalid': 0,
            'errors': []
        }
    
    def detect_file_format(self, file_path: Union[str, Path]) -> FileFormat:
        """Detecta o formato do arquivo baseado na extensão.
        
        Args:
            file_path: Caminho para o arquivo (string ou Path)
            
        Returns:
            Formato detectado
            
        Raises:
            FileFormatError: Se o formato não for suportado
        """
        # Converte para Path se for string
        if isinstance(file_path, str):
            file_path = Path(file_path)
            
        extension = file_path.suffix.lower()
        
        format_map = {
            '.csv': FileFormat.CSV,
            '.xml': FileFormat.XML,
            '.xlsx': FileFormat.XLSX,
            '.xls': FileFormat.XLSX  # Trata XLS como XLSX
        }
        
        if extension not in format_map:
            raise FileFormatError(f"Formato de arquivo não suportado: {extension}")
        
        return format_map[extension]
    
    def detect_data_type(self, file_path: Union[str, Path], file_format: FileFormat) -> DataType:
        """Detecta o tipo de dados baseado no nome do arquivo e conteúdo.
        
        Args:
            file_path: Caminho para o arquivo (string ou Path)
            file_format: Formato do arquivo
            
        Returns:
            Tipo de dados detectado
        """
        # Converte para Path se for string
        if isinstance(file_path, str):
            file_path = Path(file_path)
            
        filename_lower = file_path.name.lower()
        
        # Palavras-chave para equipamentos
        equipment_keywords = ['equipment', 'equipamento', 'equip', 'asset', 'ativo']
        
        # Palavras-chave para manutenções
        maintenance_keywords = ['maintenance', 'manutencao', 'manutenção', 'maint', 'servico', 'serviço']
        
        # Verifica nome do arquivo
        for keyword in equipment_keywords:
            if keyword in filename_lower:
                return DataType.EQUIPMENT
        
        for keyword in maintenance_keywords:
            if keyword in filename_lower:
                return DataType.MAINTENANCE
        
        # Se não conseguiu detectar pelo nome, tenta pelo conteúdo (para XML)
        if file_format == FileFormat.XML:
            try:
                detected_type = self.xml_processor.detect_xml_type(file_path)
                if detected_type == 'equipment':
                    return DataType.EQUIPMENT
                elif detected_type == 'maintenance':
                    return DataType.MAINTENANCE
            except Exception as e:
                logger.warning(f"Erro ao detectar tipo de dados do XML: {e}")
        
        # Default para equipamentos
        logger.info(f"Tipo de dados não detectado para {file_path}, assumindo equipamentos")
        return DataType.EQUIPMENT
    
    def process_file(self, file_path: Union[str, Path], data_type: DataType = None, 
                     file_format: FileFormat = None) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Processa um arquivo de dados.
        
        Args:
            file_path: Caminho para o arquivo (string ou Path)
            data_type: Tipo de dados (auto-detectado se None)
            file_format: Formato do arquivo (auto-detectado se None)
            
        Returns:
            Tupla com (registros_processados, lista_de_erros)
        """
        # Converte para Path se for string
        if isinstance(file_path, str):
            file_path = Path(file_path)
            
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        
        # Detecta formato se não fornecido
        if file_format is None:
            file_format = self.detect_file_format(file_path)
        
        # Detecta tipo de dados se não fornecido
        if data_type is None:
            data_type = self.detect_data_type(file_path, file_format)
        
        logger.info(f"Processando arquivo {file_path} - Formato: {file_format.value}, Tipo: {data_type.value}")
        
        try:
            # Processa baseado no formato
            raw_records = self._process_by_format(file_path, file_format, data_type)
            
            # Valida registros
            valid_records, validation_errors = self.validator.validate_batch(
                raw_records, data_type.value
            )
            
            # Atualiza estatísticas
            self.stats['files_processed'] += 1
            self.stats['records_processed'] += len(raw_records)
            self.stats['records_valid'] += len(valid_records)
            self.stats['records_invalid'] += len(validation_errors)
            self.stats['errors'].extend(validation_errors)
            
            logger.info(f"Arquivo processado: {len(valid_records)} registros válidos, {len(validation_errors)} inválidos")
            
            return valid_records, validation_errors
            
        except Exception as e:
            error_msg = f"Erro ao processar arquivo {file_path}: {str(e)}"
            logger.error(error_msg)
            self.stats['errors'].append(error_msg)
            raise DataProcessingError(error_msg)
    
    def _process_by_format(self, file_path: Path, file_format: FileFormat, 
                          data_type: DataType) -> List[Dict[str, Any]]:
        """Processa arquivo baseado no formato específico.
        
        Args:
            file_path: Caminho para o arquivo
            file_format: Formato do arquivo
            data_type: Tipo de dados
            
        Returns:
            Lista de registros processados
        """
        if file_format == FileFormat.CSV:
            if data_type == DataType.EQUIPMENT:
                return self.csv_processor.process_equipment_csv(file_path)
            elif data_type == DataType.MAINTENANCE:
                return self.csv_processor.process_maintenance_csv(file_path)
            
        elif file_format == FileFormat.XML:
            if data_type == DataType.EQUIPMENT:
                return self.xml_processor.process_equipment_xml(file_path)
            elif data_type == DataType.MAINTENANCE:
                return self.xml_processor.process_maintenance_xml(file_path)
            
        elif file_format == FileFormat.XLSX:
            if data_type == DataType.EQUIPMENT:
                return self.xlsx_processor.process_equipment_xlsx(file_path)
            elif data_type == DataType.MAINTENANCE:
                return self.xlsx_processor.process_maintenance_xlsx(file_path)
        
        raise DataProcessingError(f"Combinação não suportada: {file_format.value} + {data_type.value}")
    
    async def save_to_database(self, records: List[Dict[str, Any]], 
                              data_type: DataType) -> int:
        """Salva registros no banco de dados.
        
        Args:
            records: Lista de registros para salvar
            data_type: Tipo de dados
            
        Returns:
            Número de registros salvos
        """
        if not self.repository_manager:
            raise ValueError("Repository manager não configurado")
        
        if not records:
            return 0
        
        try:
            if data_type == DataType.EQUIPMENT:
                # Converte para objetos Equipment
                equipment_objects = []
                for record in records:
                    # Remove metadados antes de criar o objeto
                    clean_record = {k: v for k, v in record.items() if k != 'metadata_json'}
                    equipment_objects.append(clean_record)
                
                # Salva usando repository
                saved_count = 0
                for eq_data in equipment_objects:
                    try:
                        await self.repository_manager.equipment.create(**eq_data)
                        saved_count += 1
                    except Exception as e:
                        logger.error(f"Erro ao salvar equipamento: {e}")
                
                return saved_count
                
            elif data_type == DataType.MAINTENANCE:
                # Converte para objetos Maintenance
                maintenance_objects = []
                for record in records:
                    # Remove metadados antes de criar o objeto
                    clean_record = {k: v for k, v in record.items() if k != 'metadata_json'}
                    maintenance_objects.append(clean_record)
                
                # Salva usando repository
                saved_count = 0
                for maint_data in maintenance_objects:
                    try:
                        await self.repository_manager.maintenance.create(**maint_data)
                        saved_count += 1
                    except Exception as e:
                        logger.error(f"Erro ao salvar manutenção: {e}")
                
                return saved_count
            
        except Exception as e:
            error_msg = f"Erro ao salvar no banco de dados: {str(e)}"
            logger.error(error_msg)
            raise DataProcessingError(error_msg)
    
    async def process_and_save(self, file_path: Path, data_type: DataType = None,
                              file_format: FileFormat = None) -> Dict[str, Any]:
        """Processa arquivo e salva no banco de dados.
        
        Args:
            file_path: Caminho para o arquivo
            data_type: Tipo de dados (auto-detectado se None)
            file_format: Formato do arquivo (auto-detectado se None)
            
        Returns:
            Dicionário com estatísticas do processamento
        """
        start_time = datetime.now()
        
        try:
            # Processa arquivo
            valid_records, validation_errors = self.process_file(
                file_path, data_type, file_format
            )
            
            # Salva no banco se há registros válidos
            saved_count = 0
            if valid_records and self.repository_manager:
                saved_count = await self.save_to_database(valid_records, data_type or self.detect_data_type(file_path, file_format or self.detect_file_format(file_path)))
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                'file_path': str(file_path),
                'processing_time_seconds': processing_time,
                'total_records': len(valid_records) + len(validation_errors),
                'valid_records': len(valid_records),
                'invalid_records': len(validation_errors),
                'saved_records': saved_count,
                'validation_errors': validation_errors,
                'success': True
            }
            
            logger.info(f"Processamento concluído: {result}")
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                'file_path': str(file_path),
                'processing_time_seconds': processing_time,
                'total_records': 0,
                'valid_records': 0,
                'invalid_records': 0,
                'saved_records': 0,
                'error': str(e),
                'success': False
            }
            
            logger.error(f"Erro no processamento: {result}")
            return result
    
    def process_directory(self, directory_path: Path, recursive: bool = True) -> List[Dict[str, Any]]:
        """Processa todos os arquivos suportados em um diretório.
        
        Args:
            directory_path: Caminho para o diretório
            recursive: Se deve processar subdiretórios
            
        Returns:
            Lista com resultados de cada arquivo processado
        """
        if not directory_path.is_dir():
            raise ValueError(f"Caminho não é um diretório: {directory_path}")
        
        # Extensões suportadas
        supported_extensions = {'.csv', '.xml', '.xlsx', '.xls'}
        
        # Encontra arquivos
        files_to_process = []
        if recursive:
            for extension in supported_extensions:
                files_to_process.extend(directory_path.rglob(f'*{extension}'))
        else:
            for extension in supported_extensions:
                files_to_process.extend(directory_path.glob(f'*{extension}'))
        
        logger.info(f"Encontrados {len(files_to_process)} arquivos para processar")
        
        # Processa cada arquivo
        results = []
        for file_path in files_to_process:
            try:
                result = asyncio.run(self.process_and_save(file_path))
                results.append(result)
            except Exception as e:
                error_result = {
                    'file_path': str(file_path),
                    'error': str(e),
                    'success': False
                }
                results.append(error_result)
                logger.error(f"Erro ao processar {file_path}: {e}")
        
        return results
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas de processamento.
        
        Returns:
            Dicionário com estatísticas
        """
        total_records = self.stats['records_processed']
        success_rate = (self.stats['records_valid'] / total_records * 100) if total_records > 0 else 0
        
        return {
            'files_processed': self.stats['files_processed'],
            'total_records_processed': self.stats['records_processed'],
            'valid_records': self.stats['records_valid'],
            'invalid_records': self.stats['records_invalid'],
            'success_rate_percent': round(success_rate, 2),
            'total_errors': len(self.stats['errors']),
            'error_summary': self.stats['errors'][-10]  # Últimos 10 erros
        }
    
    def reset_statistics(self):
        """Reseta estatísticas de processamento."""
        self.stats = {
            'files_processed': 0,
            'records_processed': 0,
            'records_valid': 0,
            'records_invalid': 0,
            'errors': []
        } 