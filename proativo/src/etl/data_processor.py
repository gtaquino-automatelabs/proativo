"""
Pipeline ETL principal para processamento de dados do PROAtivo.

Este módulo implementa a classe principal que orquestra o processamento
de diferentes tipos de arquivos (CSV, XML, XLSX) e sua ingestão no banco.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Type, Union
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from ..database.repositories import EquipmentRepository, MaintenanceRepository
from ..utils.validators import DataValidator
from ..utils.logger import get_logger
from .processors.base_processor import BaseProcessor
from .processors.csv_processor import CSVProcessor
from .processors.xml_processor import XMLProcessor
from .processors.xlsx_processor import XLSXProcessor

logger = get_logger(__name__)


class DataProcessingError(Exception):
    """Exceção para erros durante processamento de dados."""
    pass


class DataProcessor:
    """
    Classe principal do pipeline ETL para processamento de dados.
    
    Responsável por:
    - Identificar o tipo de arquivo
    - Selecionar o processador apropriado
    - Orquestrar o processamento
    - Validar dados processados
    - Inserir dados no banco
    """
    
    # Mapeamento de extensões para processadores
    PROCESSOR_MAPPING: Dict[str, Type[BaseProcessor]] = {
        '.csv': CSVProcessor,
        '.xml': XMLProcessor,
        '.xlsx': XLSXProcessor,
        '.xls': XLSXProcessor,  # Suporte para formato antigo do Excel
    }
    
    def __init__(
        self,
        db_session: AsyncSession,
        equipment_repo: Optional[EquipmentRepository] = None,
        maintenance_repo: Optional[MaintenanceRepository] = None,
        validator: Optional[DataValidator] = None
    ):
        """
        Inicializa o processador de dados.
        
        Args:
            db_session: Sessão assíncrona do SQLAlchemy
            equipment_repo: Repositório de equipamentos (opcional)
            maintenance_repo: Repositório de manutenções (opcional)
            validator: Validador de dados (opcional)
        """
        self.db_session = db_session
        self.equipment_repo = equipment_repo or EquipmentRepository(db_session)
        self.maintenance_repo = maintenance_repo or MaintenanceRepository(db_session)
        self.validator = validator or DataValidator()
        self._processed_files: List[str] = []
        self._errors: List[Dict[str, str]] = []
    
    async def process_file(
        self,
        file_path: Union[str, Path],
        batch_size: int = 100
    ) -> Dict[str, any]:
        """
        Processa um arquivo de dados.
        
        Args:
            file_path: Caminho do arquivo a processar
            batch_size: Tamanho do lote para processamento em batch
            
        Returns:
            Dicionário com estatísticas do processamento
            
        Raises:
            DataProcessingError: Se houver erro no processamento
        """
        file_path = Path(file_path)
        
        # Validar arquivo
        if not file_path.exists():
            raise DataProcessingError(f"Arquivo não encontrado: {file_path}")
        
        if not file_path.is_file():
            raise DataProcessingError(f"Caminho não é um arquivo: {file_path}")
        
        # Identificar processador apropriado
        processor_class = self._get_processor(file_path)
        if not processor_class:
            raise DataProcessingError(
                f"Tipo de arquivo não suportado: {file_path.suffix}"
            )
        
        logger.info(f"Iniciando processamento de {file_path.name}")
        start_time = datetime.now()
        
        try:
            # Instanciar processador
            processor = processor_class()
            
            # Processar arquivo
            data = await processor.process(file_path)
            
            # Validar dados
            validation_results = await self._validate_data(data)
            
            # Inserir dados válidos no banco
            insert_results = await self._insert_data(
                validation_results['valid_data'],
                batch_size
            )
            
            # Calcular estatísticas
            processing_time = (datetime.now() - start_time).total_seconds()
            stats = {
                'file_name': file_path.name,
                'file_type': file_path.suffix,
                'processing_time': processing_time,
                'total_records': len(data),
                'valid_records': len(validation_results['valid_data']),
                'invalid_records': len(validation_results['invalid_data']),
                'inserted_records': insert_results['total_inserted'],
                'errors': validation_results['errors'] + insert_results['errors']
            }
            
            self._processed_files.append(str(file_path))
            logger.info(
                f"Processamento concluído: {stats['inserted_records']} "
                f"registros inseridos em {processing_time:.2f}s"
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Erro ao processar arquivo {file_path}: {e}")
            self._errors.append({
                'file': str(file_path),
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            raise DataProcessingError(f"Falha no processamento: {e}") from e
    
    async def process_directory(
        self,
        directory_path: Union[str, Path],
        recursive: bool = True,
        batch_size: int = 100
    ) -> Dict[str, any]:
        """
        Processa todos os arquivos suportados em um diretório.
        
        Args:
            directory_path: Caminho do diretório
            recursive: Se deve processar subdiretórios
            batch_size: Tamanho do lote para processamento
            
        Returns:
            Dicionário com estatísticas consolidadas
        """
        directory_path = Path(directory_path)
        
        if not directory_path.exists():
            raise DataProcessingError(f"Diretório não encontrado: {directory_path}")
        
        if not directory_path.is_dir():
            raise DataProcessingError(f"Caminho não é um diretório: {directory_path}")
        
        # Coletar arquivos para processar
        files_to_process = []
        pattern = "**/*" if recursive else "*"
        
        for suffix in self.PROCESSOR_MAPPING:
            files_to_process.extend(
                directory_path.glob(f"{pattern}{suffix}")
            )
        
        logger.info(
            f"Encontrados {len(files_to_process)} arquivos para processar "
            f"em {directory_path}"
        )
        
        # Processar arquivos
        results = []
        for file_path in files_to_process:
            try:
                result = await self.process_file(file_path, batch_size)
                results.append(result)
            except DataProcessingError as e:
                logger.error(f"Erro ao processar {file_path}: {e}")
                continue
        
        # Consolidar estatísticas
        total_stats = {
            'directory': str(directory_path),
            'files_processed': len(results),
            'files_failed': len(files_to_process) - len(results),
            'total_records': sum(r['total_records'] for r in results),
            'total_inserted': sum(r['inserted_records'] for r in results),
            'total_errors': sum(len(r['errors']) for r in results),
            'processing_time': sum(r['processing_time'] for r in results),
            'details': results
        }
        
        return total_stats
    
    def _get_processor(self, file_path: Path) -> Optional[Type[BaseProcessor]]:
        """
        Retorna o processador apropriado para o tipo de arquivo.
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            Classe do processador ou None se não suportado
        """
        suffix = file_path.suffix.lower()
        return self.PROCESSOR_MAPPING.get(suffix)
    
    async def _validate_data(
        self,
        data: List[Dict[str, any]]
    ) -> Dict[str, any]:
        """
        Valida os dados processados.
        
        Args:
            data: Lista de registros a validar
            
        Returns:
            Dicionário com dados válidos, inválidos e erros
        """
        valid_data = []
        invalid_data = []
        errors = []
        
        for idx, record in enumerate(data):
            try:
                # Validar registro
                validation_result = await self.validator.validate_record(record)
                
                if validation_result.is_valid:
                    valid_data.append(record)
                else:
                    invalid_data.append(record)
                    errors.append({
                        'record_index': idx,
                        'errors': validation_result.errors
                    })
                    
            except Exception as e:
                logger.error(f"Erro ao validar registro {idx}: {e}")
                invalid_data.append(record)
                errors.append({
                    'record_index': idx,
                    'errors': [str(e)]
                })
        
        logger.info(
            f"Validação concluída: {len(valid_data)} válidos, "
            f"{len(invalid_data)} inválidos"
        )
        
        return {
            'valid_data': valid_data,
            'invalid_data': invalid_data,
            'errors': errors
        }
    
    async def _insert_data(
        self,
        data: List[Dict[str, any]],
        batch_size: int
    ) -> Dict[str, any]:
        """
        Insere dados no banco em lotes.
        
        Args:
            data: Lista de registros a inserir
            batch_size: Tamanho do lote
            
        Returns:
            Dicionário com estatísticas de inserção
        """
        total_inserted = 0
        errors = []
        
        # Processar em lotes
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            
            try:
                # Separar por tipo de registro
                equipment_records = [
                    r for r in batch if r.get('record_type') == 'equipment'
                ]
                maintenance_records = [
                    r for r in batch if r.get('record_type') == 'maintenance'
                ]
                
                # Inserir equipamentos
                if equipment_records:
                    await self.equipment_repo.bulk_create(equipment_records)
                    total_inserted += len(equipment_records)
                
                # Inserir manutenções
                if maintenance_records:
                    await self.maintenance_repo.bulk_create(maintenance_records)
                    total_inserted += len(maintenance_records)
                
                # Commit do lote
                await self.db_session.commit()
                
            except Exception as e:
                logger.error(f"Erro ao inserir lote {i//batch_size}: {e}")
                await self.db_session.rollback()
                errors.append({
                    'batch': i // batch_size,
                    'error': str(e)
                })
        
        return {
            'total_inserted': total_inserted,
            'errors': errors
        }
    
    def get_processing_summary(self) -> Dict[str, any]:
        """
        Retorna um resumo do processamento.
        
        Returns:
            Dicionário com resumo de arquivos processados e erros
        """
        return {
            'processed_files': self._processed_files,
            'total_files': len(self._processed_files),
            'errors': self._errors,
            'total_errors': len(self._errors)
        }
    
    async def cleanup(self):
        """Limpa recursos e fecha conexões."""
        try:
            await self.db_session.close()
        except Exception as e:
            logger.error(f"Erro ao limpar recursos: {e}")