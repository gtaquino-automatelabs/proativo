"""
Processador para arquivos PMM_2 (Plano de Manutenção Maestro) do SAP.

Responsável por ler, validar e transformar dados de planos de manutenção
do SAP a partir de arquivos CSV, preparando-os para inserção no banco de dados.
"""

import logging
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
from pathlib import Path
from decimal import Decimal
import re

from ..exceptions import DataProcessingError, ValidationError
from ...utils.validators import DataValidator

logger = logging.getLogger(__name__)


class PMM_2Processor:
    """Processador para arquivos PMM_2 do SAP."""
    
    def __init__(self, validator: Optional[DataValidator] = None):
        """Inicializa o processador PMM_2.
        
        Args:
            validator: Instância do validador de dados
        """
        self.validator = validator or DataValidator()
        self.supported_encodings = ['latin-1', 'cp1252', 'utf-8', 'iso-8859-1']
        
        # Mapeamento de colunas específico para PMM_2
        self.column_mapping = {
            'plano manut.': 'maintenance_plan_code',
            'plano_manut': 'maintenance_plan_code',
            'centrab respon.': 'work_center',
            'centrab_respon': 'work_center',
            'centro_trabalho': 'work_center',
            'texto item man.': 'maintenance_item_text',
            'texto_item_man': 'maintenance_item_text',
            'descricao': 'maintenance_item_text',
            'loc.instalação': 'installation_location',
            'loc_instalacao': 'installation_location',
            'localizacao': 'installation_location',
            'data planejada': 'planned_date',
            'data_planejada': 'planned_date',
            'dta.início.progr.': 'scheduled_start_date',
            'dta_inicio_progr': 'scheduled_start_date',
            'data_inicio': 'scheduled_start_date',
            'data encermto.': 'completion_date',
            'data_encermto': 'completion_date',
            'data_fim': 'completion_date',
            'última ordem': 'last_order',
            'ultima_ordem': 'last_order',
            'ordem_anterior': 'last_order',
            'ordem': 'current_order',
            'ordem_atual': 'current_order'
        }
        
    def detect_encoding(self, file_path: Path) -> str:
        """Detecta a codificação do arquivo PMM_2.
        
        Args:
            file_path: Caminho para o arquivo
            
        Returns:
            Codificação detectada
            
        Raises:
            DataProcessingError: Se não conseguir detectar a codificação
        """
        # PMM_2 do SAP geralmente usa latin-1 ou cp1252
        for encoding in self.supported_encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    # Verifica se há caracteres típicos do PMM_2
                    if any(keyword in content.lower() for keyword in ['plano manut', 'centrab', 'loc.instalação']):
                        logger.debug(f"Codificação detectada para PMM_2: {encoding}")
                        return encoding
            except UnicodeDecodeError:
                continue
        
        # Default para latin-1 se não conseguir detectar
        logger.warning(f"Não foi possível detectar codificação do PMM_2 {file_path}, usando latin-1")
        return 'latin-1'
    
    def detect_delimiter(self, file_path: Path, encoding: str) -> str:
        """Detecta o delimitador do arquivo PMM_2.
        
        Args:
            file_path: Caminho para o arquivo
            encoding: Codificação do arquivo
            
        Returns:
            Delimitador detectado
        """
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                first_line = f.readline()
                
            # PMM_2 do SAP usa ponto e vírgula como separador
            if ';' in first_line:
                logger.debug("Delimitador detectado para PMM_2: ';'")
                return ';'
            elif ',' in first_line:
                logger.debug("Delimitador detectado para PMM_2: ','")
                return ','
            else:
                logger.warning("Delimitador não detectado, usando ';' como padrão")
                return ';'
                
        except Exception as e:
            logger.warning(f"Erro ao detectar delimitador: {e}, usando ';' como padrão")
            return ';'
    
    def read_pmm_2_csv(self, file_path: Path) -> pd.DataFrame:
        """Lê arquivo PMM_2 CSV com configurações específicas.
        
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
            
            # Lê o arquivo com configurações específicas para PMM_2
            df = pd.read_csv(
                file_path,
                encoding=encoding,
                delimiter=delimiter,
                dtype=str,  # Ler tudo como string inicialmente
                na_values=['', 'NULL', 'null', 'N/A', 'n/a', '-', 'nan', 'NaN'],
                keep_default_na=True,
                skipinitialspace=True,  # Remove espaços após delimitador
                quoting=1,  # QUOTE_ALL para lidar com campos com aspas
                na_filter=False  # Evita interpretação automática de NA como boolean
            )
            
            # Remove espaços em branco das colunas
            df.columns = df.columns.str.strip()
            
            # Remove espaços em branco dos valores string e trata valores nulos
            for col in df.columns:
                if df[col].dtype == 'object':
                    df[col] = df[col].astype(str).str.strip()
                    # Substitui valores nulos por None
                    df[col] = df[col].replace(['nan', 'NaN', 'NULL', 'null', 'N/A', 'n/a', '-', ''], None)
            
            logger.info(f"PMM_2 CSV lido com sucesso: {len(df)} linhas, {len(df.columns)} colunas")
            return df
            
        except Exception as e:
            raise DataProcessingError(f"Erro ao ler arquivo PMM_2 CSV {file_path}: {str(e)}")
    
    def standardize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Padroniza nomes de colunas PMM_2 para o schema do banco.
        
        Args:
            df: DataFrame original
            
        Returns:
            DataFrame com colunas padronizadas
        """
        # Cria um dicionário para normalizar os nomes das colunas de entrada
        # (minúsculas, sem acentos, etc.) para correspondência.
        def normalize_header(header):
            normalized = str(header).lower().strip()
            normalized = re.sub(r'[áàâãä]', 'a', normalized)
            normalized = re.sub(r'[éèêë]', 'e', normalized)
            normalized = re.sub(r'[íìîï]', 'i', normalized)
            normalized = re.sub(r'[óòôõö]', 'o', normalized)
            normalized = re.sub(r'[úùûü]', 'u', normalized)
            normalized = re.sub(r'[ç]', 'c', normalized)
            # Mantém o ponto para correspondência com chaves como 'plano manut.'
            # mas remove outros caracteres especiais que não sejam '_'
            normalized = re.sub(r'[^\w\s.]', '_', normalized) 
            normalized = re.sub(r'\s+', '_', normalized)
            normalized = re.sub(r'_+', '_', normalized)
            return normalized.strip('_')

        # Inverte o mapeamento para facilitar a busca: {schema_final: [apelidos]}
        reversed_mapping = {}
        for alias, standard_name in self.column_mapping.items():
            if standard_name not in reversed_mapping:
                reversed_mapping[standard_name] = []
            reversed_mapping[standard_name].append(normalize_header(alias))

        # Dicionário final para renomear as colunas do DataFrame
        final_rename_map = {}
        
        for col_original in df.columns:
            normalized_col = normalize_header(col_original)
            
            # Procura o nome normalizado nos apelidos do mapeamento
            for standard_name, aliases in reversed_mapping.items():
                if normalized_col in aliases:
                    final_rename_map[col_original] = standard_name
                    break
        
        df = df.rename(columns=final_rename_map)
        
        logger.debug(f"Colunas PMM_2 padronizadas. Mapeamento aplicado: {final_rename_map}")
        logger.debug(f"Colunas resultantes: {list(df.columns)}")
        
        return df
    
    def extract_equipment_code(self, installation_location: str) -> Optional[str]:
        """Extrai o código do equipamento da localização de instalação.
        
        Args:
            installation_location: String da localização (ex: MT-S-70113-FE01-CH-301F7T)
            
        Returns:
            Código do equipamento extraído ou None
        """
        if not installation_location or pd.isna(installation_location):
            return None
        
        try:
            # Padrão para extrair código do equipamento
            # Exemplo: MT-S-70113-FE01-CH-301F7T -> CH-301F7T
            
            # Busca por padrões comuns de equipamentos
            patterns = [
                r'(CH-[A-Z0-9_]+)',  # Chaves
                r'(DJ-[A-Z0-9_]+)',  # Disjuntores
                r'(TR-[A-Z0-9_]+)',  # Transformadores
                r'(BC-[A-Z0-9_]+)',  # Banco de capacitores
                r'(FH-[A-Z0-9_]+)',  # Fusíveis
                r'(BB-[A-Z0-9_]+)',  # Barramento
                r'(TC-[A-Z0-9_]+)',  # Transformadores de corrente
                r'(PR-[A-Z0-9_]+)',  # Para-raios
                r'(GM-[A-Z0-9_]+)',  # Geradores
            ]
            
            for pattern in patterns:
                match = re.search(pattern, installation_location)
                if match:
                    return match.group(1)
            
            # Se não encontrou padrão específico, tenta pegar a última parte
            parts = installation_location.split('-')
            if len(parts) >= 2:
                # Pega os dois últimos componentes
                return '-'.join(parts[-2:])
            
            return None
            
        except Exception as e:
            logger.warning(f"Erro ao extrair código do equipamento de '{installation_location}': {e}")
            return None
    
    def convert_sap_date(self, date_str: str) -> Optional[datetime]:
        """Converte datas do formato SAP para datetime.
        
        Args:
            date_str: String da data no formato SAP
            
        Returns:
            Objeto datetime ou None se não conseguir converter
        """
        if not date_str or pd.isna(date_str) or str(date_str).strip() == '':
            return None
        
        try:
            # Formatos de data comuns do SAP
            date_formats = [
                '%d/%m/%Y',      # 15/01/2025
                '%d.%m.%Y',      # 15.01.2025
                '%Y-%m-%d',      # 2025-01-15
                '%d-%m-%Y',      # 15-01-2025
                '%d/%m/%y',      # 15/01/25
                '%d.%m.%y',      # 15.01.25
            ]
            
            for fmt in date_formats:
                try:
                    return datetime.strptime(str(date_str).strip(), fmt)
                except ValueError:
                    continue
            
            # Se não conseguiu converter, tenta pandas
            return pd.to_datetime(date_str, errors='coerce')
            
        except Exception as e:
            logger.warning(f"Erro ao converter data SAP '{date_str}': {e}")
            return None
    
    def clean_pmm_2_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpa e valida dados específicos do PMM_2.
        
        Args:
            df: DataFrame com dados
            
        Returns:
            DataFrame com dados limpos
        """
        df = df.copy()
        initial_count = len(df)
        
        # Remove linhas completamente vazias
        df = df.dropna(how='all')
        
        # Remove linhas sem código de plano de manutenção
        if 'maintenance_plan_code' in df.columns:
            df = df[df['maintenance_plan_code'].notna()]
            df = df[df['maintenance_plan_code'].str.strip() != '']
            df['maintenance_plan_code'] = df['maintenance_plan_code'].str.upper().str.strip()
        
        # Remove linhas sem centro de trabalho
        if 'work_center' in df.columns:
            df = df[df['work_center'].notna()]
            df = df[df['work_center'].str.strip() != '']
            df['work_center'] = df['work_center'].str.upper().str.strip()
        
        # Remove linhas sem texto de item de manutenção
        if 'maintenance_item_text' in df.columns:
            df = df[df['maintenance_item_text'].notna()]
            df = df[df['maintenance_item_text'].str.strip() != '']
            df['maintenance_item_text'] = df['maintenance_item_text'].str.strip()
        
        # Remove linhas sem localização de instalação
        if 'installation_location' in df.columns:
            df = df[df['installation_location'].notna()]
            df = df[df['installation_location'].str.strip() != '']
            df['installation_location'] = df['installation_location'].str.strip()
        
        # Remove duplicatas baseado na chave de negócio
        duplicate_columns = ['maintenance_plan_code', 'installation_location']
        available_columns = [col for col in duplicate_columns if col in df.columns]
        if available_columns:
            df = df.drop_duplicates(subset=available_columns, keep='first')
        
        removed_count = initial_count - len(df)
        if removed_count > 0:
            logger.info(f"Removidas {removed_count} linhas inválidas/duplicadas do PMM_2")
        
        logger.info(f"Dados PMM_2 limpos: {len(df)} linhas restantes")
        return df
    
    def process_pmm_2_csv(self, file_path: Path) -> List[Dict[str, Any]]:
        """Processa arquivo CSV PMM_2 do SAP.
        
        Args:
            file_path: Caminho para o arquivo
            
        Returns:
            Lista de dicionários com dados PMM_2
        """
        logger.info(f"Processando CSV PMM_2: {file_path}")
        
        try:
            # Lê o CSV
            df = self.read_pmm_2_csv(file_path)
            
            # Padroniza nomes das colunas
            df = self.standardize_column_names(df)
            
            # Extrai código do equipamento da localização
            if 'installation_location' in df.columns:
                df['equipment_code'] = df['installation_location'].apply(self.extract_equipment_code)
            
            # Converte datas
            date_columns = ['planned_date', 'scheduled_start_date', 'completion_date']
            for col in date_columns:
                if col in df.columns:
                    df[col] = df[col].apply(self.convert_sap_date)
            
            # Limpa dados
            df = self.clean_pmm_2_data(df)
            
                         # Converte para lista de dicionários
            pmm_2_records = []
            for _, row in df.iterrows():
                record: Dict[str, Any] = {
                    'data_source': 'SAP',
                    'import_batch_id': f"PMM_2_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    'status': 'Active'
                }
                
                # Adiciona campos do PMM_2
                for col, value in row.items():
                    if pd.notna(value) and value != '':
                        if isinstance(value, pd.Timestamp):
                            record[col] = value.to_pydatetime()
                        elif isinstance(value, datetime):
                            record[col] = value
                        else:
                            record[col] = value
                
                # Metadados
                record['metadata_json'] = {
                    'source_file': file_path.name,
                    'processed_at': datetime.now().isoformat(),
                    'original_location': row.get('installation_location', ''),
                    'extracted_equipment_code': row.get('equipment_code', '')
                }
                
                pmm_2_records.append(record)
            
            logger.info(f"Processados {len(pmm_2_records)} registros PMM_2")
            return pmm_2_records
            
        except Exception as e:
            raise DataProcessingError(f"Erro ao processar CSV PMM_2 {file_path}: {str(e)}")
    
    def validate_pmm_2_record(self, record: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Valida um registro PMM_2.
        
        Args:
            record: Dicionário com dados do registro
            
        Returns:
            Tupla (is_valid, list_of_errors)
        """
        errors = []
        
        # Campos obrigatórios
        required_fields = [
            'maintenance_plan_code',
            'work_center',
            'maintenance_item_text',
            'installation_location'
        ]
        
        for field in required_fields:
            if field not in record or not record[field]:
                errors.append(f"Campo obrigatório ausente: {field}")
        
        # Validações específicas
        if 'maintenance_plan_code' in record:
            code = record['maintenance_plan_code']
            if not isinstance(code, str) or len(code) > 20:
                errors.append(f"Código de plano inválido: {code}")
        
        if 'work_center' in record:
            center = record['work_center']
            if not isinstance(center, str) or len(center) > 20:
                errors.append(f"Centro de trabalho inválido: {center}")
        
        if 'maintenance_item_text' in record:
            text = record['maintenance_item_text']
            if not isinstance(text, str) or len(text) > 500:
                errors.append(f"Texto de item muito longo: {len(text)} caracteres")
        
        if 'installation_location' in record:
            location = record['installation_location']
            if not isinstance(location, str) or len(location) > 100:
                errors.append(f"Localização inválida: {location}")
        
        # Validação de datas
        date_fields = ['planned_date', 'scheduled_start_date', 'completion_date']
        for field in date_fields:
            if field in record and record[field] is not None:
                if not isinstance(record[field], datetime):
                    errors.append(f"Data inválida em {field}: {record[field]}")
        
        return len(errors) == 0, errors
    
    def get_processing_summary(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Gera resumo do processamento PMM_2.
        
        Args:
            records: Lista de registros processados
            
        Returns:
            Dicionário com estatísticas do processamento
        """
        if not records:
            return {
                'total_records': 0,
                'work_centers': [],
                'equipment_types': [],
                'date_range': None
            }
        
        # Estatísticas básicas
        total_records = len(records)
        
        # Centros de trabalho únicos
        work_centers = set()
        equipment_codes = set()
        dates = []
        
        for record in records:
            if 'work_center' in record and record['work_center']:
                work_centers.add(record['work_center'])
            
            if 'equipment_code' in record and record['equipment_code']:
                equipment_codes.add(record['equipment_code'])
            
            if 'planned_date' in record and record['planned_date']:
                dates.append(record['planned_date'])
        
        # Faixa de datas
        date_range = None
        if dates:
            min_date = min(dates)
            max_date = max(dates)
            date_range = {
                'min_date': min_date.isoformat() if isinstance(min_date, datetime) else str(min_date),
                'max_date': max_date.isoformat() if isinstance(max_date, datetime) else str(max_date)
            }
        
        return {
            'total_records': total_records,
            'work_centers': sorted(list(work_centers)),
            'equipment_codes': sorted(list(equipment_codes)),
            'unique_work_centers': len(work_centers),
            'unique_equipment_codes': len(equipment_codes),
            'date_range': date_range,
            'sample_record': records[0] if records else None
        } 