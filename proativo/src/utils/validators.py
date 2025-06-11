"""
Validações de integridade de dados para o sistema PROAtivo.

Este módulo implementa validações para dados de entrada, queries SQL
e registros de equipamentos/manutenções.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import json

import sqlparse
from pydantic import BaseModel, Field, validator


@dataclass
class ValidationResult:
    """Resultado de uma validação."""
    is_valid: bool
    errors: List[str]
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class DataValidator:
    """
    Validador principal para dados do sistema.
    
    Responsável por:
    - Validar registros de equipamentos
    - Validar registros de manutenção
    - Validar integridade de dados
    - Sanitizar entradas
    """
    
    # Padrões regex para validações
    EQUIPMENT_ID_PATTERN = re.compile(r'^[A-Z]{2,4}-\d{4,8}$')
    DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    TIME_PATTERN = re.compile(r'^\d{2}:\d{2}(:\d{2})?$')
    EMAIL_PATTERN = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w+$')
    
    # Tipos de equipamento válidos
    VALID_EQUIPMENT_TYPES = {
        'TRANSFORMADOR',
        'DISJUNTOR',
        'CHAVE',
        'PARA-RAIOS',
        'CAPACITOR',
        'REATOR',
        'REGULADOR',
        'MEDIDOR',
        'OUTROS'
    }
    
    # Status de manutenção válidos
    VALID_MAINTENANCE_STATUS = {
        'PLANEJADA',
        'EM_ANDAMENTO',
        'CONCLUIDA',
        'CANCELADA',
        'ADIADA'
    }
    
    # Campos obrigatórios por tipo
    REQUIRED_FIELDS = {
        'equipment': ['id', 'tipo', 'nome', 'fabricante', 'data_instalacao'],
        'maintenance': ['id', 'equipment_id', 'tipo', 'data_programada', 'status']
    }
    
    async def validate_record(
        self,
        record: Dict[str, Any],
        record_type: Optional[str] = None
    ) -> ValidationResult:
        """
        Valida um registro de dados.
        
        Args:
            record: Registro a validar
            record_type: Tipo do registro (equipment/maintenance)
            
        Returns:
            Resultado da validação
        """
        errors = []
        warnings = []
        
        # Detectar tipo se não fornecido
        if not record_type:
            record_type = record.get('record_type', '')
            if not record_type:
                if 'equipment_id' in record:
                    record_type = 'maintenance'
                elif 'tipo' in record and record.get('tipo', '').upper() in self.VALID_EQUIPMENT_TYPES:
                    record_type = 'equipment'
                else:
                    errors.append("Tipo de registro não identificado")
                    return ValidationResult(False, errors)
        
        # Validar campos obrigatórios
        required_fields = self.REQUIRED_FIELDS.get(record_type, [])
        for field in required_fields:
            if field not in record or record[field] is None or str(record[field]).strip() == '':
                errors.append(f"Campo obrigatório ausente: {field}")
        
        # Validações específicas por tipo
        if record_type == 'equipment':
            self._validate_equipment(record, errors, warnings)
        elif record_type == 'maintenance':
            self._validate_maintenance(record, errors, warnings)
        else:
            errors.append(f"Tipo de registro inválido: {record_type}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _validate_equipment(
        self,
        record: Dict[str, Any],
        errors: List[str],
        warnings: List[str]
    ):
        """Valida registro de equipamento."""
        # Validar ID do equipamento
        equipment_id = record.get('id', '')
        if equipment_id and not self.EQUIPMENT_ID_PATTERN.match(str(equipment_id)):
            errors.append(f"ID de equipamento inválido: {equipment_id}")
        
        # Validar tipo
        equipment_type = str(record.get('tipo', '')).upper()
        if equipment_type and equipment_type not in self.VALID_EQUIPMENT_TYPES:
            errors.append(f"Tipo de equipamento inválido: {equipment_type}")
        
        # Validar data de instalação
        install_date = record.get('data_instalacao')
        if install_date:
            if not self._validate_date(install_date):
                errors.append(f"Data de instalação inválida: {install_date}")
            else:
                # Verificar se data não é futura
                try:
                    date_obj = datetime.strptime(str(install_date), '%Y-%m-%d')
                    if date_obj > datetime.now():
                        warnings.append("Data de instalação no futuro")
                except:
                    pass
        
        # Validar valores numéricos
        numeric_fields = ['tensao_nominal', 'potencia_nominal', 'corrente_nominal']
        for field in numeric_fields:
            if field in record:
                value = record[field]
                if value is not None:
                    try:
                        float_val = float(value)
                        if float_val < 0:
                            errors.append(f"{field} não pode ser negativo")
                    except (ValueError, TypeError):
                        errors.append(f"{field} deve ser numérico")
        
        # Validar localização
        if 'latitude' in record or 'longitude' in record:
            lat = record.get('latitude')
            lon = record.get('longitude')
            if lat is not None:
                try:
                    lat_val = float(lat)
                    if not -90 <= lat_val <= 90:
                        errors.append("Latitude deve estar entre -90 e 90")
                except:
                    errors.append("Latitude deve ser numérica")
            
            if lon is not None:
                try:
                    lon_val = float(lon)
                    if not -180 <= lon_val <= 180:
                        errors.append("Longitude deve estar entre -180 e 180")
                except:
                    errors.append("Longitude deve ser numérica")
    
    def _validate_maintenance(
        self,
        record: Dict[str, Any],
        errors: List[str],
        warnings: List[str]
    ):
        """Valida registro de manutenção."""
        # Validar ID do equipamento
        equipment_id = record.get('equipment_id', '')
        if equipment_id and not self.EQUIPMENT_ID_PATTERN.match(str(equipment_id)):
            errors.append(f"ID de equipamento inválido: {equipment_id}")
        
        # Validar status
        status = str(record.get('status', '')).upper()
        if status and status not in self.VALID_MAINTENANCE_STATUS:
            errors.append(f"Status de manutenção inválido: {status}")
        
        # Validar datas
        date_fields = ['data_programada', 'data_inicio', 'data_fim']
        for field in date_fields:
            if field in record and record[field]:
                if not self._validate_date(record[field]):
                    errors.append(f"{field} inválida: {record[field]}")
        
        # Validar coerência de datas
        if all(field in record and record[field] for field in ['data_inicio', 'data_fim']):
            try:
                start = datetime.strptime(str(record['data_inicio']), '%Y-%m-%d')
                end = datetime.strptime(str(record['data_fim']), '%Y-%m-%d')
                if end < start:
                    errors.append("Data de fim anterior à data de início")
            except:
                pass
        
        # Validar custo
        if 'custo' in record and record['custo'] is not None:
            try:
                custo = Decimal(str(record['custo']))
                if custo < 0:
                    errors.append("Custo não pode ser negativo")
            except (InvalidOperation, ValueError):
                errors.append("Custo deve ser um valor decimal válido")
        
        # Validar responsável
        if 'responsavel_email' in record and record['responsavel_email']:
            if not self.EMAIL_PATTERN.match(str(record['responsavel_email'])):
                warnings.append(f"Email inválido: {record['responsavel_email']}")
    
    def _validate_date(self, date_value: Any) -> bool:
        """Valida se valor é uma data válida."""
        if isinstance(date_value, datetime):
            return True
        
        date_str = str(date_value)
        if not self.DATE_PATTERN.match(date_str):
            return False
        
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    def sanitize_string(self, value: str, max_length: int = 255) -> str:
        """
        Sanitiza string removendo caracteres perigosos.
        
        Args:
            value: String a sanitizar
            max_length: Comprimento máximo permitido
            
        Returns:
            String sanitizada
        """
        if not value:
            return ''
        
        # Remover caracteres de controle
        value = ''.join(char for char in value if ord(char) >= 32 or char == '\n')
        
        # Remover espaços extras
        value = ' '.join(value.split())
        
        # Truncar se necessário
        if len(value) > max_length:
            value = value[:max_length]
        
        return value
    
    def validate_sql_query(self, query: str) -> ValidationResult:
        """
        Valida e sanitiza query SQL.
        
        Args:
            query: Query SQL a validar
            
        Returns:
            Resultado da validação
        """
        errors = []
        warnings = []
        
        if not query or not query.strip():
            errors.append("Query vazia")
            return ValidationResult(False, errors)
        
        # Parse da query
        try:
            parsed = sqlparse.parse(query)
            if not parsed:
                errors.append("Query SQL inválida")
                return ValidationResult(False, errors)
        except Exception as e:
            errors.append(f"Erro ao analisar query: {e}")
            return ValidationResult(False, errors)
        
        # Verificar comandos perigosos
        dangerous_keywords = [
            'DROP', 'DELETE', 'TRUNCATE', 'UPDATE', 'INSERT',
            'CREATE', 'ALTER', 'GRANT', 'REVOKE', 'EXEC', 'EXECUTE'
        ]
        
        query_upper = query.upper()
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                errors.append(f"Comando SQL não permitido: {keyword}")
        
        # Verificar comentários SQL
        if '--' in query or '/*' in query:
            warnings.append("Query contém comentários SQL")
        
        # Verificar múltiplas queries
        if ';' in query.strip()[:-1]:  # Ignora ; no final
            errors.append("Múltiplas queries não permitidas")
        
        # Limitar tamanho
        if len(query) > 5000:
            errors.append("Query muito longa (máximo 5000 caracteres)")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def validate_file_upload(
        self,
        filename: str,
        file_size: int,
        content_type: Optional[str] = None
    ) -> ValidationResult:
        """
        Valida upload de arquivo.
        
        Args:
            filename: Nome do arquivo
            file_size: Tamanho em bytes
            content_type: Tipo MIME do arquivo
            
        Returns:
            Resultado da validação
        """
        errors = []
        warnings = []
        
        # Validar extensão
        allowed_extensions = {'.csv', '.xml', '.xlsx', '.xls'}
        file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
        if f'.{file_ext}' not in allowed_extensions:
            errors.append(f"Tipo de arquivo não permitido: {file_ext}")
        
        # Validar tamanho
        max_size = 50 * 1024 * 1024  # 50MB
        if file_size > max_size:
            errors.append(f"Arquivo muito grande (máximo 50MB)")
        elif file_size == 0:
            errors.append("Arquivo vazio")
        
        # Validar nome do arquivo
        if len(filename) > 255:
            errors.append("Nome do arquivo muito longo")
        
        # Caracteres perigosos no nome
        dangerous_chars = ['..', '/', '\\', '\x00']
        for char in dangerous_chars:
            if char in filename:
                errors.append(f"Nome do arquivo contém caractere não permitido: {char}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )


class QueryInputValidator(BaseModel):
    """Validador Pydantic para entrada de queries."""
    
    query: str = Field(..., min_length=1, max_length=1000)
    context: Optional[List[str]] = Field(default=None, max_items=10)
    
    @validator('query')
    def validate_query(cls, v):
        """Valida query de entrada."""
        # Remover espaços extras
        v = ' '.join(v.split())
        
        # Verificar caracteres suspeitos
        if any(char in v for char in ['<', '>', '{', '}', 'script', 'javascript']):
            raise ValueError("Query contém caracteres não permitidos")
        
        return v
    
    @validator('context')
    def validate_context(cls, v):
        """Valida lista de contexto."""
        if v:
            # Limitar tamanho de cada item de contexto
            validated = []
            for item in v:
                if len(item) > 500:
                    item = item[:500]
                validated.append(item)
            return validated
        return v


class MaintenanceInputValidator(BaseModel):
    """Validador Pydantic para entrada de manutenção."""
    
    equipment_id: str = Field(..., regex=r'^[A-Z]{2,4}-\d{4,8}$')
    tipo: str = Field(..., min_length=3, max_length=50)
    data_programada: datetime
    status: str = Field(..., min_length=3, max_length=20)
    descricao: Optional[str] = Field(None, max_length=1000)
    custo: Optional[Decimal] = Field(None, ge=0)
    responsavel: Optional[str] = Field(None, max_length=100)
    responsavel_email: Optional[str] = Field(None, regex=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    
    @validator('status')
    def validate_status(cls, v):
        """Valida status da manutenção."""
        v_upper = v.upper()
        if v_upper not in DataValidator.VALID_MAINTENANCE_STATUS:
            raise ValueError(f"Status inválido: {v}")
        return v_upper
    
    @validator('data_programada')
    def validate_data(cls, v):
        """Valida data programada."""
        # Não permitir datas muito no passado
        min_date = datetime.now() - timedelta(days=365 * 10)  # 10 anos
        if v < min_date:
            raise ValueError("Data muito antiga")
        return v