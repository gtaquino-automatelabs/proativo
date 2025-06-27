"""
Mapeadores de dados para compatibilidade entre formatos de arquivo e banco de dados.

Este módulo contém mapeamentos para converter valores dos arquivos (CSV, XML, XLSX)
para os valores esperados pelo banco de dados.
"""

from typing import Optional, Dict, Any
from datetime import datetime
import re


class DataMapper:
    """Classe para mapear valores entre formatos de arquivo e banco de dados."""
    
    # Mapeamento de criticidade
    CRITICALITY_MAPPING = {
        'alta': 'High',
        'high': 'High',
        'crítica': 'High',
        'critica': 'High',
        'crítico': 'High',
        'critico': 'High',
        'h': 'High',
        
        'média': 'Medium',
        'media': 'Medium',
        'médio': 'Medium',
        'medio': 'Medium',
        'normal': 'Medium',
        'medium': 'Medium',
        'm': 'Medium',
        
        'baixa': 'Low',
        'baixo': 'Low',
        'low': 'Low',
        'l': 'Low',
    }
    
    # Mapeamento de status de equipamento
    EQUIPMENT_STATUS_MAPPING = {
        'ativo': 'Active',
        'active': 'Active',
        'operacional': 'Active',
        'funcionando': 'Active',
        'em_operacao': 'Active',
        'operando': 'Active',
        
        'inativo': 'Inactive',
        'inactive': 'Inactive',
        'parado': 'Inactive',
        'desligado': 'Inactive',
        'fora_operacao': 'Inactive',
        
        'manutencao': 'Maintenance',
        'manutenção': 'Maintenance',
        'maintenance': 'Maintenance',
        'em_manutencao': 'Maintenance',
        'em_manutenção': 'Maintenance',
        
        'aposentado': 'Retired',
        'retired': 'Retired',
        'descomissionado': 'Retired',
        'fora_linha': 'Retired',
        'descartado': 'Retired',
    }
    
    # Mapeamento de tipos de manutenção
    MAINTENANCE_TYPE_MAPPING = {
        'preventiva': 'Preventive',
        'preventive': 'Preventive',
        'programada': 'Preventive',
        'planejada': 'Preventive',
        
        'corretiva': 'Corrective',
        'corrective': 'Corrective',
        'emergencial': 'Emergency',
        'emergency': 'Emergency',
        'urgente': 'Emergency',
        
        'preditiva': 'Predictive',
        'predictive': 'Predictive',
        'condicional': 'Predictive',
    }
    
    # Mapeamento de prioridade
    PRIORITY_MAPPING = {
        'alta': 'High',
        'high': 'High',
        'urgente': 'High',
        'crítica': 'High',
        'critica': 'High',
        
        'média': 'Medium',
        'media': 'Medium',
        'normal': 'Medium',
        'medium': 'Medium',
        
        'baixa': 'Low',
        'low': 'Low',
    }
    
    # Mapeamento de status de manutenção
    MAINTENANCE_STATUS_MAPPING = {
        'planejada': 'Planned',
        'planned': 'Planned',
        'programada': 'Planned',
        'agendada': 'Planned',
        'nova': 'Planned',
        
        'em_andamento': 'InProgress',
        'inprogress': 'InProgress',
        'executando': 'InProgress',
        'em_execucao': 'InProgress',
        'em_execução': 'InProgress',
        
        'concluida': 'Completed',
        'concluída': 'Completed',
        'completed': 'Completed',
        'finalizada': 'Completed',
        'terminada': 'Completed',
        'ok': 'Completed',
        
        'cancelada': 'Cancelled',
        'cancelled': 'Cancelled',
        'cancelado': 'Cancelled',
        'suspenso': 'Cancelled',
        'abortado': 'Cancelled',
    }

    @classmethod
    def map_criticality(cls, value: Optional[str]) -> str:
        """Mapeia criticidade para valor do banco.
        
        Args:
            value: Valor original
            
        Returns:
            Valor mapeado para o banco (High, Medium, Low)
        """
        if not value:
            return 'Medium'  # Valor padrão
            
        # Normalizar: lowercase e remover espaços/acentos
        normalized = str(value).lower().strip()
        
        # Buscar no mapeamento
        mapped = cls.CRITICALITY_MAPPING.get(normalized, 'Medium')
        return mapped

    @classmethod
    def map_equipment_status(cls, value: Optional[str]) -> str:
        """Mapeia status de equipamento para valor do banco.
        
        Args:
            value: Valor original
            
        Returns:
            Valor mapeado para o banco (Active, Inactive, Maintenance, Retired)
        """
        if not value:
            return 'Active'  # Valor padrão
            
        # Normalizar: lowercase e remover espaços
        normalized = str(value).lower().strip()
        
        # Buscar no mapeamento
        mapped = cls.EQUIPMENT_STATUS_MAPPING.get(normalized, 'Active')
        return mapped

    @classmethod
    def map_maintenance_type(cls, value: Optional[str]) -> str:
        """Mapeia tipo de manutenção para valor do banco.
        
        Args:
            value: Valor original
            
        Returns:
            Valor mapeado para o banco (Preventive, Corrective, Predictive, Emergency)
        """
        if not value:
            return 'Preventive'  # Valor padrão
            
        # Normalizar: lowercase e remover espaços
        normalized = str(value).lower().strip()
        
        # Buscar no mapeamento
        mapped = cls.MAINTENANCE_TYPE_MAPPING.get(normalized, 'Preventive')
        return mapped

    @classmethod
    def map_priority(cls, value: Optional[str]) -> str:
        """Mapeia prioridade para valor do banco.
        
        Args:
            value: Valor original
            
        Returns:
            Valor mapeado para o banco (High, Medium, Low)
        """
        if not value:
            return 'Medium'  # Valor padrão
            
        # Normalizar: lowercase e remover espaços
        normalized = str(value).lower().strip()
        
        # Buscar no mapeamento
        mapped = cls.PRIORITY_MAPPING.get(normalized, 'Medium')
        return mapped

    @classmethod
    def map_maintenance_status(cls, value: Optional[str]) -> str:
        """Mapeia status de manutenção para valor do banco.
        
        Args:
            value: Valor original
            
        Returns:
            Valor mapeado para o banco (Planned, InProgress, Completed, Cancelled)
        """
        if not value:
            return 'Planned'  # Valor padrão
            
        # Normalizar: lowercase e remover espaços
        normalized = str(value).lower().strip()
        
        # Buscar no mapeamento
        mapped = cls.MAINTENANCE_STATUS_MAPPING.get(normalized, 'Planned')
        return mapped

    @classmethod
    def parse_date(cls, value: Optional[str]) -> Optional[datetime]:
        """Converte string de data para datetime.
        
        Args:
            value: String de data em vários formatos
            
        Returns:
            Objeto datetime ou None se não conseguir converter
        """
        if not value or value in ['', 'null', 'None', 'NULL']:
            return None
            
        # Se já é datetime, retorna
        if isinstance(value, datetime):
            return value
            
        # Converter para string
        date_str = str(value).strip()
        
        # Padrões de data mais comuns
        date_patterns = [
            '%Y-%m-%d',           # 2018-03-15
            '%d/%m/%Y',           # 15/03/2018
            '%d-%m-%Y',           # 15-03-2018
            '%Y/%m/%d',           # 2018/03/15
            '%Y-%m-%d %H:%M:%S',  # 2018-03-15 10:30:00
            '%d/%m/%Y %H:%M:%S',  # 15/03/2018 10:30:00
            '%Y-%m-%dT%H:%M:%S',  # ISO format
        ]
        
        for pattern in date_patterns:
            try:
                return datetime.strptime(date_str, pattern)
            except ValueError:
                continue
        
        # Se nada funcionar, tenta regex para extrair ano-mês-dia
        date_match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', date_str)
        if date_match:
            year, month, day = date_match.groups()
            try:
                return datetime(int(year), int(month), int(day))
            except ValueError:
                pass
        
        # Último recurso: retorna None se não conseguir converter
        return None

    @classmethod
    def map_equipment_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mapeia todos os campos de um equipamento.
        
        Args:
            data: Dicionário com dados do equipamento
            
        Returns:
            Dicionário com dados mapeados
        """
        mapped = data.copy()
        
        # Mapear criticidade
        if 'criticality' in mapped:
            mapped['criticality'] = cls.map_criticality(mapped['criticality'])
        
        # Mapear status
        if 'status' in mapped:
            mapped['status'] = cls.map_equipment_status(mapped['status'])
        
        # Mapear data de instalação
        if 'installation_date' in mapped:
            mapped['installation_date'] = cls.parse_date(mapped['installation_date'])
        
        return mapped

    @classmethod
    def map_maintenance_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mapeia todos os campos de uma manutenção.
        
        Args:
            data: Dicionário com dados da manutenção
            
        Returns:
            Dicionário com dados mapeados
        """
        mapped = data.copy()
        
        # Mapear tipo de manutenção
        if 'maintenance_type' in mapped:
            mapped['maintenance_type'] = cls.map_maintenance_type(mapped['maintenance_type'])
        
        # Mapear prioridade
        if 'priority' in mapped:
            mapped['priority'] = cls.map_priority(mapped['priority'])
        
        # Mapear status
        if 'status' in mapped:
            mapped['status'] = cls.map_maintenance_status(mapped['status'])
        
        # Mapear datas
        date_fields = ['scheduled_date', 'start_date', 'completion_date', 'followup_date']
        for field in date_fields:
            if field in mapped:
                mapped[field] = cls.parse_date(mapped[field])
        
        return mapped 