"""
Processador para arquivos CSV usando Pandas.

Responsável por ler, validar e transformar dados de equipamentos e manutenções
a partir de arquivos CSV, preparando-os para inserção no banco de dados.
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


class CSVProcessor:
    """Processador para arquivos CSV com foco em dados de manutenção."""
    
    def __init__(self, validator: Optional[DataValidator] = None):
        """Inicializa o processador CSV.
        
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
        delimiters = [',', ';', '\t', '|']
        
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                first_line = f.readline()
                
            # Conta ocorrências de cada delimitador
            delimiter_counts = {d: first_line.count(d) for d in delimiters}
            
            # Retorna o delimitador com mais ocorrências
            detected = max(delimiter_counts, key=delimiter_counts.get)
            logger.debug(f"Delimitador detectado: '{detected}'")
            return detected
            
        except Exception:
            logger.warning("Não foi possível detectar delimitador, usando vírgula")
            return ','
    
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
            
            logger.info(f"CSV lido com sucesso: {len(df)} linhas, {len(df.columns)} colunas")
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
        # Mapeamento de colunas comuns para nomes padrão
        column_mapping = {
            # Equipamentos
            'equipamento': 'code',
            'codigo': 'code',
            'codigo_equipamento': 'code',
            'equipment_code': 'code',
            'nome': 'name',
            'nome_equipamento': 'name',
            'equipment_name': 'name',
            'descricao': 'description',
            'description': 'description',
            'tipo': 'equipment_type',
            'tipo_equipamento': 'equipment_type',
            'equipment_type': 'equipment_type',
            'criticidade': 'criticality',
            'criticality': 'criticality',
            'localizacao': 'location',
            'location': 'location',
            'subestacao': 'substation',
            'substation': 'substation',
            'fabricante': 'manufacturer',
            'manufacturer': 'manufacturer',
            'modelo': 'model',
            'model': 'model',
            'numero_serie': 'serial_number',
            'serial_number': 'serial_number',
            'ano_fabricacao': 'manufacturing_year',
            'manufacturing_year': 'manufacturing_year',
            'data_instalacao': 'installation_date',
            'installation_date': 'installation_date',
            'tensao_nominal': 'rated_voltage',
            'rated_voltage': 'rated_voltage',
            'potencia_nominal': 'rated_power',
            'rated_power': 'rated_power',
            'corrente_nominal': 'rated_current',
            'rated_current': 'rated_current',
            'status': 'status',
            
            # Manutenções  
            'equipment_id': 'equipment_id',  # CRÍTICO: mantém equipment_id
            'equipamento_id': 'equipment_id',  # Mapeia equipamento_id para equipment_id
            'codigo_equipamento': 'equipment_id',  # Mapeia codigo_equipamento para equipment_id
            'codigo_manutencao': 'maintenance_code',
            'maintenance_code': 'maintenance_code',
            'order_number': 'maintenance_code',  # Mapeia order_number para maintenance_code
            'tipo_manutencao': 'maintenance_type',
            'maintenance_type': 'maintenance_type',
            'type': 'maintenance_type',  # Mapeia type para maintenance_type
            'prioridade': 'priority',
            'priority': 'priority',
            'titulo': 'title',
            'title': 'title',
            'descricao': 'description',  # Adiciona mapeamento para 'description'
            'descricao_manutencao': 'description',
            'description': 'description',  # Mantém description como description
            'trabalho_realizado': 'work_performed',
            'work_performed': 'work_performed',
            'data_programada': 'scheduled_date',
            'scheduled_date': 'scheduled_date',
            'data_inicio': 'start_date',
            'start_date': 'start_date',
            'data_conclusao': 'completion_date',
            'completion_date': 'completion_date',
            'duracao_horas': 'duration_hours',
            'duration_hours': 'duration_hours',
            'resultado': 'result',
            'result': 'result',
            'tecnico': 'technician',
            'technician': 'technician',
            'equipe': 'team',
            'team': 'team',
            'contratada': 'contractor',
            'contractor': 'contractor',
            'custo_estimado': 'estimated_cost',
            'estimated_cost': 'estimated_cost',
            'custo_real': 'actual_cost',
            'actual_cost': 'actual_cost',
            'pecas_substituidas': 'parts_replaced',
            'parts_replaced': 'parts_replaced',
            'materiais_utilizados': 'materials_used',
            'materials_used': 'materials_used',
            'observacoes': 'observations',
            'observations': 'observations',
            
            # Dados históricos
            'fonte_dados': 'data_source',
            'data_source': 'data_source',
            'tipo_dados': 'data_type',
            'data_type': 'data_type',
            'timestamp': 'timestamp',
            'data_hora': 'timestamp',
            'tipo_medicao': 'measurement_type',
            'measurement_type': 'measurement_type',
            'valor_medicao': 'measurement_value',
            'measurement_value': 'measurement_value',
            'unidade_medida': 'measurement_unit',
            'measurement_unit': 'measurement_unit',
            'valor_texto': 'text_value',
            'text_value': 'text_value',
            'status_condicao': 'condition_status',
            'condition_status': 'condition_status',
            'nivel_alerta': 'alert_level',
            'alert_level': 'alert_level',
            'inspetor': 'inspector',
            'inspector': 'inspector',
            'metodo_coleta': 'collection_method',
            'collection_method': 'collection_method',
        }
        
        # Normaliza nomes das colunas (lowercase, remove acentos, underscores)
        normalized_columns = {}
        for col in df.columns:
            normalized = col.lower().strip()
            normalized = re.sub(r'[áàâãä]', 'a', normalized)
            normalized = re.sub(r'[éèêë]', 'e', normalized)
            normalized = re.sub(r'[íìîï]', 'i', normalized)
            normalized = re.sub(r'[óòôõö]', 'o', normalized)
            normalized = re.sub(r'[úùûü]', 'u', normalized)
            normalized = re.sub(r'[ç]', 'c', normalized)
            normalized = re.sub(r'[^\w\s]', '', normalized)
            normalized = re.sub(r'\s+', '_', normalized)
            normalized_columns[col] = normalized
        
        # Renomeia as colunas
        df = df.rename(columns=normalized_columns)
        
        # Aplica mapeamento para nomes padrão
        df = df.rename(columns=column_mapping)
        
        logger.debug(f"Colunas padronizadas: {list(df.columns)}")
        return df
    
    def convert_data_types(self, df: pd.DataFrame, data_type: str) -> pd.DataFrame:
        """Converte tipos de dados baseado no tipo de entidade.
        
        Args:
            df: DataFrame com dados
            data_type: Tipo de dados ('equipment', 'maintenance', 'data_history')
            
        Returns:
            DataFrame com tipos convertidos
        """
        df = df.copy()
        
        # Conversões comuns de data
        date_columns = ['installation_date', 'scheduled_date', 'start_date', 
                       'completion_date', 'followup_date', 'timestamp']
        
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Conversões numéricas
        numeric_columns = ['manufacturing_year', 'rated_voltage', 'rated_power', 
                          'rated_current', 'duration_hours', 'estimated_cost', 
                          'actual_cost', 'measurement_value', 'quality_score']
        
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Conversões booleanas
        boolean_columns = ['is_critical', 'requires_followup', 'is_validated']
        
        for col in boolean_columns:
            if col in df.columns:
                df[col] = df[col].map({
                    'true': True, 'True': True, 'TRUE': True, '1': True, 'sim': True, 'yes': True,
                    'false': False, 'False': False, 'FALSE': False, '0': False, 'nao': False, 'no': False
                })
        
        # Padroniza valores categóricos
        if 'criticality' in df.columns:
            df['criticality'] = df['criticality'].str.strip()
            df['criticality'] = df['criticality'].replace({
                'alta': 'High', 'Alta': 'High', 'HIGH': 'High',
                'média': 'Medium', 'media': 'Medium', 'Média': 'Medium', 'Media': 'Medium', 'MEDIUM': 'Medium',
                'baixa': 'Low', 'Baixa': 'Low', 'LOW': 'Low'
            })
        
        if 'status' in df.columns and data_type == 'equipment':
            df['status'] = df['status'].str.title()
            df['status'] = df['status'].replace({
                'Ativo': 'Active', 'Inativo': 'Inactive', 
                'Manutenção': 'Maintenance', 'Manutencao': 'Maintenance',
                'Aposentado': 'Retired'
            })
        
        if 'maintenance_type' in df.columns:
            df['maintenance_type'] = df['maintenance_type'].str.title()
            df['maintenance_type'] = df['maintenance_type'].replace({
                'Preventiva': 'Preventive', 'Corretiva': 'Corrective',
                'Preditiva': 'Predictive', 'Emergencial': 'Emergency'
            })
        
        logger.debug(f"Tipos de dados convertidos para {data_type}")
        return df
    
    def validate_required_columns(self, df: pd.DataFrame, data_type: str) -> None:
        """Valida se as colunas obrigatórias estão presentes.
        
        Args:
            df: DataFrame para validação
            data_type: Tipo de dados ('equipment', 'maintenance', 'data_history')
            
        Raises:
            ValidationError: Se colunas obrigatórias estão ausentes
        """
        required_columns = {
            'equipment': ['code', 'name', 'equipment_type'],
            'maintenance': ['equipment_id', 'maintenance_type', 'title'],
            'data_history': ['equipment_id', 'data_source', 'data_type', 'timestamp']
        }
        
        if data_type not in required_columns:
            raise ValidationError(f"Tipo de dados não suportado: {data_type}")
        
        missing_columns = []
        for col in required_columns[data_type]:
            if col not in df.columns:
                missing_columns.append(col)
        
        if missing_columns:
            raise ValidationError(f"Colunas obrigatórias ausentes para {data_type}: {missing_columns}")
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpa e valida os dados.
        
        Args:
            df: DataFrame para limpeza
            
        Returns:
            DataFrame limpo
        """
        df = df.copy()
        
        # Remove linhas completamente vazias
        df = df.dropna(how='all')
        
        # Remove linhas duplicadas
        initial_count = len(df)
        df = df.drop_duplicates()
        removed_duplicates = initial_count - len(df)
        
        if removed_duplicates > 0:
            logger.info(f"Removidas {removed_duplicates} linhas duplicadas")
        
        # Limpa códigos de equipamento
        if 'code' in df.columns:
            df['code'] = df['code'].str.upper().str.strip()
            df = df[df['code'].notna() & (df['code'] != '')]
        
        # Limpa valores monetários
        money_columns = ['estimated_cost', 'actual_cost']
        for col in money_columns:
            if col in df.columns:
                # Remove símbolos de moeda e formatação
                df[col] = df[col].astype(str).str.replace(r'[R$\s,.]', '', regex=True)
                df[col] = pd.to_numeric(df[col], errors='coerce') / 100  # Assume centavos
        
        logger.info(f"Dados limpos: {len(df)} linhas restantes")
        return df
    
    def process_equipment_csv(self, file_path: Path) -> List[Dict[str, Any]]:
        """Processa arquivo CSV de equipamentos.
        
        Args:
            file_path: Caminho para o arquivo
            
        Returns:
            Lista de dicionários com dados de equipamentos
        """
        logger.info(f"Processando CSV de equipamentos: {file_path}")
        
        try:
            # Lê o CSV
            df = pd.read_csv(file_path, dtype=str)
            
            # Padroniza nomes das colunas
            column_mapping = {
                'id': 'code', 'equipamento': 'code', 'codigo': 'code', 'codigo_equipamento': 'code',
                'nome': 'name', 'nome_equipamento': 'name', 'equipment_name': 'name',
                'type': 'equipment_type', 'tipo': 'equipment_type', 'tipo_equipamento': 'equipment_type',
                'descricao': 'description',
                'criticidade': 'criticality', 'localizacao': 'location', 'subestacao': 'substation',
                'fabricante': 'manufacturer', 'modelo': 'model', 'numero_serie': 'serial_number',
                'ano_fabricacao': 'manufacturing_year', 'data_instalacao': 'installation_date',
                'tensao_nominal': 'rated_voltage', 'potencia_nominal': 'rated_power',
                'corrente_nominal': 'rated_current', 'status': 'status'
            }
            
            # Normaliza nomes das colunas
            df.columns = df.columns.str.lower().str.strip()
            df = df.rename(columns=column_mapping)
            
            # Conversões de tipo
            date_columns = ['installation_date']
            for col in date_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
            
            numeric_columns = ['manufacturing_year', 'rated_voltage', 'rated_power', 'rated_current']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Limpa dados
            df = df.dropna(how='all')
            if 'code' in df.columns:
                df['code'] = df['code'].str.upper().str.strip()
                df = df[df['code'].notna() & (df['code'] != '')]
            
            # Aplica conversões de tipos e valores categóricos
            df = self.convert_data_types(df, 'equipment')
            
            # Converte para lista de dicionários
            equipment_records = []
            for _, row in df.iterrows():
                record = {}
                for col, value in row.items():
                    if pd.notna(value):
                        if isinstance(value, pd.Timestamp):
                            record[col] = value.to_pydatetime()
                        else:
                            record[col] = value
                
                record['metadata_json'] = {
                    'source_file': file_path.name,
                    'processed_at': datetime.now().isoformat()
                }
                
                equipment_records.append(record)
            
            logger.info(f"Processados {len(equipment_records)} equipamentos")
            return equipment_records
            
        except Exception as e:
            raise DataProcessingError(f"Erro ao processar CSV de equipamentos {file_path}: {str(e)}")
    
    def process_maintenance_csv(self, file_path: Path) -> List[Dict[str, Any]]:
        """Processa arquivo CSV de manutenções.
        
        Args:
            file_path: Caminho para o arquivo
            
        Returns:
            Lista de dicionários com dados de manutenções
        """
        logger.info(f"Processando CSV de manutenções: {file_path}")
        
        try:
            # Lê o CSV
            df = pd.read_csv(file_path, dtype=str)
            
            # Padroniza nomes das colunas
            column_mapping = {
                # ⭐ CRÍTICO: Mapeamentos para equipment_id
                'equipment_id': 'equipment_id', 'equipamento_id': 'equipment_id', 'codigo_equipamento': 'equipment_id',
                
                # ⭐ Mapeamentos para maintenance_code  
                'codigo_manutencao': 'maintenance_code', 'maintenance_code': 'maintenance_code',
                'order_number': 'maintenance_code', 'id': 'maintenance_code',
                
                # ⭐ Mapeamentos para maintenance_type
                'tipo_manutencao': 'maintenance_type', 'maintenance_type': 'maintenance_type',
                'type': 'maintenance_type',
                
                # ⭐ Outros campos essenciais
                'prioridade': 'priority', 'priority': 'priority',
                'titulo': 'title', 'title': 'title',
                'descricao': 'description', 'description': 'description',
                'trabalho_realizado': 'work_performed', 'work_performed': 'work_performed',
                'data_programada': 'scheduled_date', 'scheduled_date': 'scheduled_date',
                'data_inicio': 'start_date', 'start_date': 'start_date',
                'data_conclusao': 'completion_date', 'completion_date': 'completion_date',
                'duracao_horas': 'duration_hours', 'duration_hours': 'duration_hours',
                'resultado': 'result', 'result': 'result',
                'tecnico': 'technician', 'technician': 'technician',
                'equipe': 'team', 'team': 'team',
                'contratada': 'contractor', 'contractor': 'contractor',
                'custo_estimado': 'estimated_cost', 'estimated_cost': 'estimated_cost',
                'custo_real': 'actual_cost', 'actual_cost': 'actual_cost',
                'observacoes': 'observations', 'observations': 'observations'
            }
            
            # Normaliza nomes das colunas
            df.columns = df.columns.str.lower().str.strip()
            df = df.rename(columns=column_mapping)
            
            # 🔍 DEBUG: Verificar se equipment_id está na DataFrame após mapeamento
            if 'equipment_id' not in df.columns:
                print(f"   🚨 ERRO: equipment_id PERDIDO após mapeamento!")
                print(f"   🚨 Colunas finais: {list(df.columns)}")
                print(f"   🚨 Mapeamento para equipment_id: {[(k,v) for k,v in column_mapping.items() if 'equipment' in k.lower()]}")
            else:
                print(f"   ✅ equipment_id preservado: {df['equipment_id'].head().tolist()}")
            
            # Conversões de tipo
            date_columns = ['scheduled_date', 'start_date', 'completion_date']
            for col in date_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
            
            numeric_columns = ['duration_hours', 'estimated_cost', 'actual_cost']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Limpa dados
            df = df.dropna(how='all')
            
            # Converte para lista de dicionários
            maintenance_records = []
            for _, row in df.iterrows():
                record = {}
                for col, value in row.items():
                    if pd.notna(value):
                        if isinstance(value, pd.Timestamp):
                            record[col] = value.to_pydatetime()
                        else:
                            record[col] = value
                
                record['metadata_json'] = {
                    'source_file': file_path.name,
                    'processed_at': datetime.now().isoformat()
                }
                
                maintenance_records.append(record)
            
            logger.info(f"Processadas {len(maintenance_records)} manutenções")
            return maintenance_records
            
        except Exception as e:
            raise DataProcessingError(f"Erro ao processar CSV de manutenções {file_path}: {str(e)}")
    
    def process_data_history_csv(self, file_path: Path) -> List[Dict[str, Any]]:
        """Processa arquivo CSV de histórico de dados.
        
        Args:
            file_path: Caminho para o arquivo
            
        Returns:
            Lista de dicionários com dados históricos
        """
        logger.info(f"Processando CSV de histórico: {file_path}")
        
        df = self.read_csv(file_path)
        df = self.standardize_column_names(df)
        df = self.convert_data_types(df, 'data_history')
        self.validate_required_columns(df, 'data_history')
        df = self.clean_data(df)
        
        # Adiciona fonte de dados se não estiver presente
        if 'data_source' not in df.columns:
            df['data_source'] = 'CSV'
        
        # Converte para lista de dicionários
        history_records = []
        for index, row in df.iterrows():
            record = {}
            for col, value in row.items():
                if pd.notna(value):
                    if isinstance(value, pd.Timestamp):
                        record[col] = value.to_pydatetime()
                    elif isinstance(value, (pd.Int64Dtype, pd.Float64Dtype)):
                        record[col] = float(value) if pd.notna(value) else None
                    else:
                        record[col] = value
            
            # Adiciona informações de origem
            record['source_file'] = file_path.name
            record['source_row'] = index + 2  # +2 por causa do header e índice 0
            record['metadata_json'] = {
                'source_file': file_path.name,
                'source_row': index + 2,
                'processed_at': datetime.now().isoformat()
            }
            
            history_records.append(record)
        
        logger.info(f"Processados {len(history_records)} registros de histórico")
        return history_records
    
    def get_processing_summary(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Gera resumo do processamento.
        
        Args:
            records: Lista de registros processados
            
        Returns:
            Dicionário com estatísticas do processamento
        """
        if not records:
            return {'total_records': 0, 'columns': [], 'data_types': {}}
        
        sample_record = records[0]
        columns = list(sample_record.keys())
        
        # Analisa tipos de dados
        data_types = {}
        for col in columns:
            values = [r.get(col) for r in records[:100]]  # Amostra dos primeiros 100
            non_null_values = [v for v in values if v is not None]
            
            if non_null_values:
                value_type = type(non_null_values[0]).__name__
                data_types[col] = value_type
        
        return {
            'total_records': len(records),
            'columns': columns,
            'data_types': data_types,
            'sample_record': sample_record
        } 