"""
Processador para arquivos CSV de localidades SAP.

Responsável por ler, validar e transformar dados de localidades SAP
a partir de arquivos CSV, preparando-os para inserção no banco de dados.
"""

import logging
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
import re
import uuid
import json

from ..exceptions import DataProcessingError, ValidationError
from ...utils.validators import DataValidator

logger = logging.getLogger(__name__)


def convert_timestamps_to_iso(data: Any) -> Any:
    """Converte objetos Timestamp para string ISO para serialização JSON.
    
    Args:
        data: Dados que podem conter Timestamps
        
    Returns:
        Dados com Timestamps convertidos para string ISO
    """
    if isinstance(data, pd.Timestamp):
        return data.isoformat()
    elif isinstance(data, datetime):
        return data.isoformat()
    elif isinstance(data, dict):
        return {key: convert_timestamps_to_iso(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_timestamps_to_iso(item) for item in data]
    else:
        return data


class LocalidadesProcessor:
    """Processador para arquivos CSV de localidades SAP."""
    
    def __init__(self, validator: Optional[DataValidator] = None):
        """Inicializa o processador de localidades.
        
        Args:
            validator: Instância do validador de dados
        """
        self.validator = validator or DataValidator()
        self.supported_encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
    def detect_encoding(self, file_path: Path) -> str:
        """Detecta a codificação do arquivo CSV.
        
        Args:
            file_path: Caminho para o arquivo
            
        Returns:
            Codificação detectada
            
        Raises:
            DataProcessingError: Se não conseguir detectar a codificação
        """
        for encoding in self.supported_encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    f.read()
                logger.debug(f"Codificação detectada: {encoding}")
                return encoding
            except UnicodeDecodeError:
                continue
        
        raise DataProcessingError(f"Não foi possível detectar a codificação do arquivo: {file_path}")
    
    def detect_delimiter(self, file_path: Path, encoding: str) -> str:
        """Detecta o delimitador do arquivo CSV.
        
        Args:
            file_path: Caminho para o arquivo
            encoding: Codificação do arquivo
            
        Returns:
            Delimitador detectado
        """
        delimiters = [';', ',', '\t', '|']
        
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                first_line = f.readline()
                
            # Conta ocorrências de cada delimitador
            delimiter_counts = {d: first_line.count(d) for d in delimiters}
            
            # Retorna o delimitador com mais ocorrências
            detected = max(delimiter_counts.items(), key=lambda x: x[1])[0]
            logger.debug(f"Delimitador detectado: '{detected}'")
            return detected
            
        except Exception:
            logger.warning("Não foi possível detectar delimitador, usando ponto e vírgula")
            return ';'
    
    def read_csv(self, file_path: Path) -> pd.DataFrame:
        """Lê arquivo CSV com detecção automática de parâmetros.
        
        Args:
            file_path: Caminho para o arquivo CSV
            
        Returns:
            DataFrame com os dados
            
        Raises:
            DataProcessingError: Se houver erro na leitura
        """
        try:
            encoding = self.detect_encoding(file_path)
            delimiter = self.detect_delimiter(file_path, encoding)
            
            df = pd.read_csv(
                file_path,
                encoding=encoding,
                delimiter=delimiter,
                dtype=str,  # Ler tudo como string inicialmente
                na_values=['', 'NULL', 'null', 'N/A', 'n/a', '-'],
                keep_default_na=True
            )
            
            # Remove espaços em branco das colunas
            df.columns = df.columns.str.strip()
            
            # Remove espaços em branco dos valores string
            string_columns = df.select_dtypes(include=['object']).columns
            df[string_columns] = df[string_columns].apply(lambda x: x.str.strip() if x.dtype == "object" else x)
            
            logger.info(f"CSV de localidades lido com sucesso: {len(df)} linhas, {len(df.columns)} colunas")
            return df
            
        except Exception as e:
            raise DataProcessingError(f"Erro ao ler arquivo CSV {file_path}: {str(e)}")
    
    def standardize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Padroniza nomes de colunas para o schema do banco.
        
        Args:
            df: DataFrame original
            
        Returns:
            DataFrame com colunas padronizadas
        """
        # Mapeamento específico para localidades SAP
        column_mapping = {
            'loc.instalação': 'location_code',
            'loc.instalacao': 'location_code',
            'loc_instalacao': 'location_code',
            'localizacao': 'location_code',
            'codigo': 'location_code',
            'code': 'location_code',
            'denominação': 'denomination',
            'denominacao': 'denomination',
            'nome': 'denomination',
            'name': 'denomination',
            'descricao': 'denomination',
            'loc.abreviada': 'abbreviation',
            'loc_abreviada': 'abbreviation',
            'abreviacao': 'abbreviation',
            'abrev': 'abbreviation',
            'sigla': 'abbreviation',
        }
        
        # Normalizar nomes de colunas (minúsculas, sem espaços)
        normalized_columns = {}
        for col in df.columns:
            normalized_col = col.lower().strip().replace(' ', '_')
            normalized_columns[col] = normalized_col
        
        df = df.rename(columns=normalized_columns)
        
        # Aplicar mapeamento
        df = df.rename(columns=column_mapping)
        
        logger.debug(f"Colunas padronizadas: {list(df.columns)}")
        return df
    
    def extract_location_components(self, location_code: str) -> Dict[str, Optional[str]]:
        """Extrai componentes do código de localização.
        
        Args:
            location_code: Código da localização (ex: MT-S-72183)
            
        Returns:
            Dicionário com componentes extraídos
        """
        if not location_code:
            return {'region': None, 'type_code': None}
        
        # Padrão: MT-S-72183 (Região-Tipo-Código)
        pattern = r'^([A-Z]{2})-([A-Z])-(.+)$'
        match = re.match(pattern, location_code.upper())
        
        if match:
            return {
                'region': match.group(1),
                'type_code': match.group(2)
            }
        
        # Tentar extrair só região se não seguir padrão completo
        region_pattern = r'^([A-Z]{2})-'
        region_match = re.match(region_pattern, location_code.upper())
        
        if region_match:
            return {
                'region': region_match.group(1),
                'type_code': None
            }
        
        return {'region': None, 'type_code': None}
    
    def validate_location_data(self, location_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Valida dados de uma localidade.
        
        Args:
            location_data: Dados da localidade
            
        Returns:
            Tupla (é_válido, lista_de_erros)
        """
        errors = []
        
        # Validar código da localização (obrigatório)
        if not location_data.get('location_code'):
            errors.append("Código da localização é obrigatório")
        else:
            code = location_data['location_code']
            if len(code) < 3:
                errors.append("Código da localização deve ter pelo menos 3 caracteres")
        
        # Validar denominação (obrigatório)
        if not location_data.get('denomination'):
            errors.append("Denominação é obrigatória")
        
        # Validar abreviação (opcional, mas se presente deve ser válida)
        abbreviation = location_data.get('abbreviation')
        if abbreviation and len(abbreviation) > 20:
            errors.append("Abreviação deve ter no máximo 20 caracteres")
        
        return len(errors) == 0, errors
    
    def normalize_location_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normaliza dados de localidades.
        
        Args:
            df: DataFrame com dados brutos
            
        Returns:
            DataFrame com dados normalizados
        """
        df = df.copy()
        
        # Garantir que colunas obrigatórias existam
        required_columns = ['location_code', 'denomination']
        for col in required_columns:
            if col not in df.columns:
                raise DataProcessingError(f"Coluna obrigatória '{col}' não encontrada")
        
        # Normalizar código da localização
        df['location_code'] = df['location_code'].astype(str).str.upper().str.strip()
        
        # Normalizar denominação
        df['denomination'] = df['denomination'].astype(str).str.strip()
        
        # Normalizar abreviação (se presente)
        if 'abbreviation' in df.columns:
            df['abbreviation'] = df['abbreviation'].astype(str).str.upper().str.strip()
            df['abbreviation'] = df['abbreviation'].replace('NAN', None)
        else:
            df['abbreviation'] = None
        
        # Extrair componentes do código
        location_components = df['location_code'].apply(self.extract_location_components)
        df['region'] = location_components.apply(lambda x: x['region'])
        df['type_code'] = location_components.apply(lambda x: x['type_code'])
        
        # Adicionar metadados
        df['status'] = 'Active'
        df['data_source'] = 'CSV'
        df['import_date'] = datetime.now()
        
        logger.info(f"Dados de localidades normalizados: {len(df)} registros")
        return df
    
    def process_file(self, file_path: Path, import_batch_id: Optional[str] = None) -> Dict[str, Any]:
        """Processa arquivo CSV de localidades.
        
        Args:
            file_path: Caminho para o arquivo
            import_batch_id: ID do lote de importação
            
        Returns:
            Dicionário com resultado do processamento
        """
        try:
            # Gerar ID do lote se não fornecido
            if not import_batch_id:
                import_batch_id = str(uuid.uuid4())
            
            # Ler arquivo CSV
            df = self.read_csv(file_path)
            
            if df.empty:
                raise DataProcessingError("Arquivo CSV está vazio")
            
            # Padronizar nomes de colunas
            df = self.standardize_column_names(df)
            
            # Normalizar dados
            df = self.normalize_location_data(df)
            
            # Adicionar ID do lote
            df['import_batch_id'] = import_batch_id
            
            # Validar dados
            valid_records = []
            invalid_records = []
            
            for index, row in df.iterrows():
                location_data = row.to_dict()
                # Converter Timestamps para garantir serialização JSON
                location_data = convert_timestamps_to_iso(location_data)
                
                is_valid, errors = self.validate_location_data(location_data)
                
                if is_valid:
                    valid_records.append(location_data)
                else:
                    invalid_records.append({
                        'row': index + 1,
                        'data': location_data,
                        'errors': errors
                    })
            
            # Resultado do processamento
            result = {
                'file_path': str(file_path),
                'import_batch_id': import_batch_id,
                'total_records': len(df),
                'valid_records': len(valid_records),
                'invalid_records': len(invalid_records),
                'data': valid_records,
                'errors': invalid_records,
                'columns_found': list(df.columns),
                'processing_timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Processamento concluído: {len(valid_records)} válidos, {len(invalid_records)} inválidos")
            return result
            
        except Exception as e:
            logger.error(f"Erro no processamento do arquivo {file_path}: {str(e)}")
            raise DataProcessingError(f"Erro no processamento: {str(e)}")
    
    def create_location_records(self, processed_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Cria registros de localidades prontos para inserção no banco.
        
        Args:
            processed_data: Dados processados
            
        Returns:
            Lista de registros prontos para inserção
        """
        records = []
        
        for data in processed_data:
            # Converter dados para garantir serialização JSON
            converted_data = convert_timestamps_to_iso(data)
            
            record = {
                'location_code': data['location_code'],
                'denomination': data['denomination'],
                'abbreviation': data.get('abbreviation'),
                'region': data.get('region'),
                'type_code': data.get('type_code'),
                'status': data.get('status', 'Active'),
                'data_source': data.get('data_source', 'CSV'),
                'import_batch_id': data.get('import_batch_id'),
                'metadata_json': {
                    'original_data': converted_data,
                    'processing_timestamp': datetime.now().isoformat()
                }
            }
            records.append(record)
        
        return records 