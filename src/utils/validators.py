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
            # Campo CRÍTICO - equipment_id (deve ser preservado sempre)
            if 'equipment_id' in record:
                validated['equipment_id'] = record['equipment_id']  # Preserva exatamente como está
            
            # Campos obrigatórios com conversão
            if record.get('maintenance_type'):
                raw_type = record['maintenance_type'].strip().lower()
                # Converter português para inglês conforme constraint do banco
                type_mapping = {
                    'preventiva': 'Preventive',
                    'corretiva': 'Corrective', 
                    'preditiva': 'Predictive',
                    'emergencia': 'Emergency',
                    'emergência': 'Emergency',
                    # Tipos específicos que mapeiam para categorias principais
                    'inspeção': 'Preventive',
                    'inspecao': 'Preventive',
                    'análise_óleo': 'Predictive',
                    'analise_oleo': 'Predictive',
                    'calibração': 'Preventive',
                    'calibracao': 'Preventive',
                    'monitoramento': 'Predictive',
                    'termografia': 'Predictive',
                    'limpeza': 'Preventive',
                    'lubrificação': 'Preventive',
                    'lubrificacao': 'Preventive'
                }
                validated['maintenance_type'] = type_mapping.get(raw_type, 'Preventive')
            
            # Title é obrigatório - gerar se não existir
            if record.get('title'):
                validated['title'] = record['title'].strip()
            else:
                # Gerar title baseado no maintenance_type original (português)
                maintenance_type = record.get('maintenance_type', 'Manutenção')
                validated['title'] = f"Manutenção {maintenance_type.title()}"
            
        except Exception as e:
            errors.append(str(e))
        
        # Campos opcionais com conversão específica
        for field in ['maintenance_code', 'description', 'work_performed', 
                     'result', 'technician', 'team', 'contractor', 'observations',
                     'status']:  # Adicionado status também
            if record.get(field):
                validated[field] = str(record[field]).strip()
        
        # Campo priority com conversão português -> inglês
        if record.get('priority'):
            raw_priority = record['priority'].strip().lower()
            priority_mapping = {
                'alta': 'High',
                'high': 'High',
                'média': 'Medium',
                'media': 'Medium',
                'medium': 'Medium',
                'baixa': 'Low',
                'low': 'Low',
                'crítica': 'Critical',
                'critica': 'Critical',
                'critical': 'Critical'
            }
            validated['priority'] = priority_mapping.get(raw_priority, 'Medium')
        
        # Campo status com conversão português -> inglês (conforme constraint do banco)
        if record.get('status'):
            raw_status = record['status'].strip().lower()
            status_mapping = {
                'aberta': 'Planned',
                'open': 'Planned',
                'planned': 'Planned',
                'planejada': 'Planned',
                'em andamento': 'InProgress',
                'em_andamento': 'InProgress',
                'in progress': 'InProgress',
                'in_progress': 'InProgress',
                'inprogress': 'InProgress',
                'andamento': 'InProgress',
                'concluída': 'Completed',
                'concluida': 'Completed',
                'completed': 'Completed',
                'finalizada': 'Completed',
                'cancelada': 'Cancelled',
                'cancelled': 'Cancelled',
                'cancelado': 'Cancelled'
            }
            validated['status'] = status_mapping.get(raw_status, 'Planned')
        
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
    
    def validate_pmm_2_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Valida registro completo de PMM_2."""
        validated = {}
        errors = []
        
        try:
            # Campos obrigatórios
            self.validate_required_field(record.get('maintenance_plan_code'), 'maintenance_plan_code')
            validated['maintenance_plan_code'] = record['maintenance_plan_code'].strip().upper()
            
            self.validate_required_field(record.get('work_center'), 'work_center')
            validated['work_center'] = record['work_center'].strip().upper()
            
            self.validate_required_field(record.get('maintenance_item_text'), 'maintenance_item_text')
            validated['maintenance_item_text'] = record['maintenance_item_text'].strip()
            
            # Campo opcional - installation_location pode não existir
            if record.get('installation_location'):
                validated['installation_location'] = record['installation_location'].strip()
            
        except ValidationError as e:
            errors.append(str(e))
        
        # Campos opcionais
        for field in ['equipment_code', 'abbreviation', 'status', 'data_source']:
            if record.get(field):
                validated[field] = str(record[field]).strip()
        
        # Datas
        for field in ['planned_date', 'scheduled_start_date', 'completion_date']:
            if record.get(field):
                validated[field] = record[field]
        
        # Campos de ordem
        for field in ['last_order', 'current_order']:
            if record.get(field):
                validated[field] = str(record[field]).strip()
        
        if errors:
            raise ValidationError(f"Erros de validação: {'; '.join(errors)}")
        
        # Mantém metadados
        if 'metadata_json' in record:
            validated['metadata_json'] = record['metadata_json']
        
        return validated
    
    def validate_failure_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Valida registro completo de falha."""
        validated = {}
        errors = []
        
        try:
            # Campos obrigatórios
            self.validate_required_field(record.get('equipment_id'), 'equipment_id')
            validated['equipment_id'] = record['equipment_id']
            
            self.validate_required_field(record.get('failure_date'), 'failure_date')
            validated['failure_date'] = record['failure_date']
            
            self.validate_required_field(record.get('description'), 'description')
            validated['description'] = record['description'].strip()
            
        except ValidationError as e:
            errors.append(str(e))
        
        # Campos opcionais
        for field in ['failure_type', 'severity', 'resolution_time', 'cost', 'equipment_name']:
            if record.get(field):
                validated[field] = str(record[field]).strip()
        
        # Campo severity com conversão português -> inglês
        if record.get('severity'):
            raw_severity = record['severity'].strip().lower()
            severity_mapping = {
                'crítica': 'Critical',
                'critica': 'Critical',
                'critical': 'Critical',
                'alta': 'High',
                'high': 'High',
                'média': 'Medium',
                'media': 'Medium',
                'medium': 'Medium',
                'baixa': 'Low',
                'low': 'Low'
            }
            validated['severity'] = severity_mapping.get(raw_severity, 'Medium')
        
        # Campos numéricos
        for field in ['resolution_time', 'cost']:
            if record.get(field) is not None:
                try:
                    validated[field] = float(record[field])
                except (ValueError, TypeError):
                    errors.append(f"Valor numérico inválido para {field}: {record[field]}")
        
        if errors:
            raise ValidationError(f"Erros de validação: {'; '.join(errors)}")
        
        # Mantém metadados
        if 'metadata_json' in record:
            validated['metadata_json'] = record['metadata_json']
        
        return validated
    
    def validate_localidades_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Valida registro completo de localidade."""
        validated = {}
        errors = []
        
        try:
            # Campos obrigatórios
            self.validate_required_field(record.get('location_code'), 'location_code')
            validated['location_code'] = record['location_code'].strip().upper()
            
            self.validate_required_field(record.get('denomination'), 'denomination')
            validated['denomination'] = record['denomination'].strip()
            
        except ValidationError as e:
            errors.append(str(e))
        
        # Campos opcionais
        for field in ['abbreviation', 'region', 'type_code', 'status', 'data_source']:
            if record.get(field):
                validated[field] = str(record[field]).strip()
        
        # Campo status com conversão português -> inglês
        if record.get('status'):
            raw_status = record['status'].strip().lower()
            status_mapping = {
                'ativo': 'Active',
                'active': 'Active',
                'inativo': 'Inactive',
                'inactive': 'Inactive'
            }
            validated['status'] = status_mapping.get(raw_status, 'Active')
        
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
            'maintenance': self.validate_maintenance_record,
            'pmm_2': self.validate_pmm_2_record,
            'failure': self.validate_failure_record,
            'localidades': self.validate_localidades_record
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