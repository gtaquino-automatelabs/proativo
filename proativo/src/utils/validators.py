"""
Validadores de integridade de dados.

Conjunto de validadores para garantir a qualidade e integridade dos dados
de equipamentos, manutenções e histórico antes da inserção no banco de dados.
"""

import logging
import re
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple, Union
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Exceção para erros de validação."""
    pass


class DataValidator:
    """Validador principal para dados do sistema."""
    
    def __init__(self):
        """Inicializa o validador."""
        self.equipment_types = {
            'Transformer', 'Circuit Breaker', 'Disconnect Switch', 'Relay', 
            'Meter', 'Capacitor', 'Reactor', 'Cable', 'Conductor', 'Busbar',
            'Lightning Arrester', 'Insulator', 'Support Structure', 'Other'
        }
        
        self.maintenance_types = {
            'Preventive', 'Corrective', 'Predictive', 'Emergency', 'Inspection'
        }
        
        self.criticality_levels = {'High', 'Medium', 'Low'}
        self.priority_levels = {'Critical', 'High', 'Medium', 'Low'}
        self.equipment_status = {'Active', 'Inactive', 'Maintenance', 'Retired'}
    
    def validate_required_field(self, value: Any, field_name: str) -> None:
        """Valida se um campo obrigatório está presente e não vazio."""
        if value is None or (isinstance(value, str) and value.strip() == ''):
            raise ValidationError(f"Campo obrigatório ausente ou vazio: {field_name}")
    
    def validate_equipment_code(self, code: str) -> str:
        """Valida e normaliza código de equipamento."""
        if not code or not isinstance(code, str):
            raise ValidationError("Código de equipamento deve ser uma string não vazia")
        
        normalized_code = code.strip().upper()
        
        if not re.match(r'^[A-Z0-9_-]+$', normalized_code):
            raise ValidationError(f"Código de equipamento inválido: {code}")
        
        if len(normalized_code) < 2 or len(normalized_code) > 50:
            raise ValidationError(f"Código de equipamento deve ter entre 2 e 50 caracteres: {code}")
        
        return normalized_code
    
    def validate_equipment_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Valida registro completo de equipamento."""
        validated = {}
        errors = []
        
        try:
            # Campos obrigatórios
            self.validate_required_field(record.get('code'), 'code')
            validated['code'] = self.validate_equipment_code(record['code'])
            
            self.validate_required_field(record.get('name'), 'name')
            validated['name'] = record['name'].strip()
            
            if record.get('equipment_type'):
                validated['equipment_type'] = record['equipment_type'].strip()
            
        except ValidationError as e:
            errors.append(str(e))
        
        # Campos opcionais
        for field in ['description', 'criticality', 'location', 'substation', 
                     'manufacturer', 'model', 'serial_number', 'status']:
            if record.get(field):
                validated[field] = str(record[field]).strip()
        
        # Campos numéricos
        for field in ['manufacturing_year', 'rated_voltage', 'rated_power', 'rated_current']:
            if record.get(field) is not None:
                try:
                    validated[field] = float(record[field])
                except (ValueError, TypeError):
                    errors.append(f"Valor numérico inválido para {field}: {record[field]}")
        
        # Data de instalação
        if record.get('installation_date'):
            validated['installation_date'] = record['installation_date']
        
        if errors:
            raise ValidationError(f"Erros de validação: {'; '.join(errors)}")
        
        # Mantém metadados
        if 'metadata_json' in record:
            validated['metadata_json'] = record['metadata_json']
        
        return validated
    
    def validate_maintenance_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Valida registro completo de manutenção."""
        validated = {}
        errors = []
        
        try:
            # 🔧 CRÍTICO: Preservar equipment_id
            if record.get('equipment_id'):
                validated['equipment_id'] = record['equipment_id']
            
            # Campos obrigatórios
            if record.get('maintenance_type'):
                validated['maintenance_type'] = record['maintenance_type'].strip()
            
            # 🔧 CRÍTICO: Garantir que title seja preenchido (obrigatório no banco)
            if record.get('title'):
                validated['title'] = record['title'].strip()
            elif record.get('description'):
                # Usa description como title se title estiver vazio
                validated['title'] = record['description'].strip()
            elif record.get('maintenance_code'):
                # Usa maintenance_code como fallback
                validated['title'] = f"Manutenção {record['maintenance_code']}"
            else:
                # Fallback final
                validated['title'] = f"Manutenção {record.get('maintenance_type', 'Geral')}"
            
        except Exception as e:
            errors.append(str(e))
        
        # Campos opcionais
        for field in ['maintenance_code', 'description', 'work_performed', 
                     'priority', 'result', 'technician', 'team', 'contractor', 'observations']:
            if record.get(field):
                validated[field] = str(record[field]).strip()
        
        # Campos numéricos
        for field in ['duration_hours', 'estimated_cost', 'actual_cost']:
            if record.get(field) is not None:
                try:
                    validated[field] = float(record[field])
                except (ValueError, TypeError):
                    errors.append(f"Valor numérico inválido para {field}: {record[field]}")
        
        # Datas
        for field in ['scheduled_date', 'start_date', 'completion_date']:
            if record.get(field):
                validated[field] = record[field]
        
        if errors:
            raise ValidationError(f"Erros de validação: {'; '.join(errors)}")
        
        # Mantém metadados
        if 'metadata_json' in record:
            validated['metadata_json'] = record['metadata_json']
        
        return validated
    
    def validate_batch(self, records: List[Dict[str, Any]], record_type: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Valida lote de registros."""
        valid_records = []
        errors = []
        
        validator_map = {
            'equipment': self.validate_equipment_record,
            'maintenance': self.validate_maintenance_record
        }
        
        if record_type not in validator_map:
            raise ValueError(f"Tipo de registro não suportado: {record_type}")
        
        validator = validator_map[record_type]
        
        for i, record in enumerate(records):
            try:
                validated_record = validator(record)
                valid_records.append(validated_record)
            except ValidationError as e:
                error_msg = f"Registro {i+1}: {str(e)}"
                errors.append(error_msg)
                logger.warning(error_msg)
        
        logger.info(f"Validação do lote {record_type}: {len(valid_records)} válidos, {len(errors)} com erro")
        
        return valid_records, errors 