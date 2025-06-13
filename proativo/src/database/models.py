"""
Modelos SQLAlchemy para o sistema PROAtivo.

Define as entidades do domínio: equipamentos, manutenções e histórico de dados.
Focado em dados de manutenção de ativos elétricos.
"""

import uuid
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

from sqlalchemy import (
    String, Text, Integer, Numeric, DateTime, Boolean, 
    ForeignKey, Index, CheckConstraint, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from .connection import Base


class Equipment(Base):
    """Modelo para equipamentos/ativos elétricos."""
    
    __tablename__ = "equipments"
    
    # Chave primária
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4()),
        comment="Identificador único do equipamento"
    )
    
    # Informações básicas
    code: Mapped[str] = mapped_column(
        String(50), 
        unique=True, 
        nullable=False,
        comment="Código identificador do equipamento (ex: TR-001)"
    )
    name: Mapped[str] = mapped_column(
        String(200), 
        nullable=False,
        comment="Nome do equipamento"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="Descrição detalhada do equipamento"
    )
    
    # Classificação
    equipment_type: Mapped[str] = mapped_column(
        String(50), 
        nullable=False,
        comment="Tipo do equipamento (ex: Transformador, Disjuntor, etc.)"
    )
    category: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="Categoria do equipamento"
    )
    criticality: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        default="Medium",
        comment="Criticidade: High, Medium, Low"
    )
    
    # Localização
    location: Mapped[Optional[str]] = mapped_column(
        String(200),
        comment="Localização do equipamento"
    )
    substation: Mapped[Optional[str]] = mapped_column(
        String(100),
        comment="Subestação onde está instalado"
    )
    
    # Características técnicas
    manufacturer: Mapped[Optional[str]] = mapped_column(
        String(100),
        comment="Fabricante do equipamento"
    )
    model: Mapped[Optional[str]] = mapped_column(
        String(100),
        comment="Modelo do equipamento"
    )
    serial_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        comment="Número de série"
    )
    manufacturing_year: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Ano de fabricação"
    )
    installation_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        comment="Data de instalação"
    )
    
    # Especificações elétricas
    rated_voltage: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        comment="Tensão nominal (kV)"
    )
    rated_power: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        comment="Potência nominal (MVA)"
    )
    rated_current: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        comment="Corrente nominal (A)"
    )
    
    # Status operacional
    status: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        default="Active",
        comment="Status: Active, Inactive, Maintenance, Retired"
    )
    is_critical: Mapped[bool] = mapped_column(
        Boolean, 
        default=False,
        comment="Se é um equipamento crítico"
    )
    
    # Metadados
    metadata_json: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        comment="Dados adicionais em formato JSON"
    )
    
    # Auditoria
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        comment="Data de criação do registro"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        comment="Data da última atualização"
    )
    
    # Relacionamentos
    maintenances: Mapped[List["Maintenance"]] = relationship(
        "Maintenance", 
        back_populates="equipment",
        cascade="all, delete-orphan"
    )
    data_history: Mapped[List["DataHistory"]] = relationship(
        "DataHistory", 
        back_populates="equipment",
        cascade="all, delete-orphan"
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "criticality IN ('High', 'Medium', 'Low')", 
            name="ck_equipment_criticality"
        ),
        CheckConstraint(
            "status IN ('Active', 'Inactive', 'Maintenance', 'Retired')", 
            name="ck_equipment_status"
        ),
        CheckConstraint(
            "manufacturing_year >= 1900 AND manufacturing_year <= EXTRACT(YEAR FROM CURRENT_DATE)", 
            name="ck_equipment_manufacturing_year"
        ),
        Index("idx_equipment_code", "code"),
        Index("idx_equipment_type", "equipment_type"),
        Index("idx_equipment_status", "status"),
        Index("idx_equipment_location", "location"),
        Index("idx_equipment_criticality", "criticality"),
    )
    
    def __repr__(self) -> str:
        return f"<Equipment(code='{self.code}', name='{self.name}', type='{self.equipment_type}')>"


class Maintenance(Base):
    """Modelo para registros de manutenção."""
    
    __tablename__ = "maintenances"
    
    # Chave primária
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4()),
        comment="Identificador único da manutenção"
    )
    
    # Relacionamento com equipamento
    equipment_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), 
        ForeignKey("equipments.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID do equipamento"
    )
    
    # Informações da manutenção
    maintenance_code: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="Código da ordem de manutenção"
    )
    maintenance_type: Mapped[str] = mapped_column(
        String(50), 
        nullable=False,
        comment="Tipo: Preventive, Corrective, Predictive, Emergency"
    )
    priority: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        default="Medium",
        comment="Prioridade: High, Medium, Low"
    )
    
    # Descrição e detalhes
    title: Mapped[str] = mapped_column(
        String(200), 
        nullable=False,
        comment="Título da manutenção"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="Descrição detalhada da manutenção"
    )
    work_performed: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="Trabalho realizado"
    )
    
    # Datas e tempo
    scheduled_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        comment="Data programada"
    )
    start_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        comment="Data de início"
    )
    completion_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        comment="Data de conclusão"
    )
    duration_hours: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 2),
        comment="Duração em horas"
    )
    
    # Status e resultado
    status: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        default="Planned",
        comment="Status: Planned, InProgress, Completed, Cancelled"
    )
    result: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="Resultado: Success, Partial, Failed"
    )
    
    # Recursos
    technician: Mapped[Optional[str]] = mapped_column(
        String(100),
        comment="Técnico responsável"
    )
    team: Mapped[Optional[str]] = mapped_column(
        String(200),
        comment="Equipe responsável"
    )
    contractor: Mapped[Optional[str]] = mapped_column(
        String(100),
        comment="Empresa contratada"
    )
    
    # Custos
    estimated_cost: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        comment="Custo estimado (R$)"
    )
    actual_cost: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        comment="Custo real (R$)"
    )
    
    # Materiais e peças
    parts_replaced: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="Peças substituídas"
    )
    materials_used: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="Materiais utilizados"
    )
    
    # Observações e follow-up
    observations: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="Observações gerais"
    )
    requires_followup: Mapped[bool] = mapped_column(
        Boolean, 
        default=False,
        comment="Se requer acompanhamento"
    )
    followup_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        comment="Data de acompanhamento"
    )
    
    # Metadados
    metadata_json: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        comment="Dados adicionais em formato JSON"
    )
    
    # Auditoria
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        comment="Data de criação do registro"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        comment="Data da última atualização"
    )
    
    # Relacionamentos
    equipment: Mapped["Equipment"] = relationship(
        "Equipment", 
        back_populates="maintenances"
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "maintenance_type IN ('Preventive', 'Corrective', 'Predictive', 'Emergency')", 
            name="ck_maintenance_type"
        ),
        CheckConstraint(
            "priority IN ('High', 'Medium', 'Low')", 
            name="ck_maintenance_priority"
        ),
        CheckConstraint(
            "status IN ('Planned', 'InProgress', 'Completed', 'Cancelled')", 
            name="ck_maintenance_status"
        ),
        CheckConstraint(
            "result IS NULL OR result IN ('Success', 'Partial', 'Failed')", 
            name="ck_maintenance_result"
        ),
        CheckConstraint(
            "completion_date IS NULL OR start_date IS NULL OR completion_date >= start_date", 
            name="ck_maintenance_dates"
        ),
        Index("idx_maintenance_equipment", "equipment_id"),
        Index("idx_maintenance_type", "maintenance_type"),
        Index("idx_maintenance_status", "status"),
        Index("idx_maintenance_scheduled_date", "scheduled_date"),
        Index("idx_maintenance_priority", "priority"),
    )
    
    def __repr__(self) -> str:
        return f"<Maintenance(id='{self.id}', type='{self.maintenance_type}', status='{self.status}')>"


class DataHistory(Base):
    """Modelo para histórico de dados dos equipamentos."""
    
    __tablename__ = "data_history"
    
    # Chave primária
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4()),
        comment="Identificador único do registro"
    )
    
    # Relacionamento com equipamento
    equipment_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), 
        ForeignKey("equipments.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID do equipamento"
    )
    
    # Origem e tipo dos dados
    data_source: Mapped[str] = mapped_column(
        String(50), 
        nullable=False,
        comment="Fonte dos dados: CSV, XML, XLSX, Manual, API"
    )
    data_type: Mapped[str] = mapped_column(
        String(50), 
        nullable=False,
        comment="Tipo de dados: Measurement, Inspection, Test, Event"
    )
    
    # Timestamp dos dados
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False,
        comment="Timestamp dos dados originais"
    )
    
    # Valores medidos/observados
    measurement_type: Mapped[Optional[str]] = mapped_column(
        String(100),
        comment="Tipo de medição (ex: Temperatura, Vibração, etc.)"
    )
    measurement_value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 4),
        comment="Valor numérico medido"
    )
    measurement_unit: Mapped[Optional[str]] = mapped_column(
        String(20),
        comment="Unidade de medida"
    )
    
    # Dados textuais
    text_value: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="Valor textual ou observação"
    )
    
    # Status e condição
    condition_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="Status da condição: Good, Warning, Critical, Unknown"
    )
    alert_level: Mapped[Optional[str]] = mapped_column(
        String(20),
        comment="Nível de alerta: Normal, Warning, Critical"
    )
    
    # Contexto da coleta
    inspector: Mapped[Optional[str]] = mapped_column(
        String(100),
        comment="Responsável pela coleta/inspeção"
    )
    collection_method: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="Método de coleta: Automatic, Manual, Remote"
    )
    
    # Arquivo fonte
    source_file: Mapped[Optional[str]] = mapped_column(
        String(255),
        comment="Nome do arquivo fonte dos dados"
    )
    source_row: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Linha do arquivo fonte"
    )
    
    # Validação e qualidade
    is_validated: Mapped[bool] = mapped_column(
        Boolean, 
        default=False,
        comment="Se os dados foram validados"
    )
    validation_status: Mapped[Optional[str]] = mapped_column(
        String(20),
        comment="Status da validação: Valid, Invalid, Pending"
    )
    quality_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(3, 2),
        comment="Score de qualidade dos dados (0.00-1.00)"
    )
    
    # Dados estruturados adicionais
    raw_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        comment="Dados brutos em formato JSON"
    )
    processed_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        comment="Dados processados em formato JSON"
    )
    
    # Metadados
    metadata_json: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        comment="Metadados adicionais"
    )
    
    # Auditoria
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        comment="Data de criação do registro"
    )
    
    # Relacionamentos
    equipment: Mapped["Equipment"] = relationship(
        "Equipment", 
        back_populates="data_history"
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "data_source IN ('CSV', 'XML', 'XLSX', 'Manual', 'API')", 
            name="ck_data_history_source"
        ),
        CheckConstraint(
            "data_type IN ('Measurement', 'Inspection', 'Test', 'Event')", 
            name="ck_data_history_type"
        ),
        CheckConstraint(
            "condition_status IS NULL OR condition_status IN ('Good', 'Warning', 'Critical', 'Unknown')", 
            name="ck_data_history_condition"
        ),
        CheckConstraint(
            "alert_level IS NULL OR alert_level IN ('Normal', 'Warning', 'Critical')", 
            name="ck_data_history_alert"
        ),
        CheckConstraint(
            "validation_status IS NULL OR validation_status IN ('Valid', 'Invalid', 'Pending')", 
            name="ck_data_history_validation"
        ),
        CheckConstraint(
            "quality_score IS NULL OR (quality_score >= 0.00 AND quality_score <= 1.00)", 
            name="ck_data_history_quality"
        ),
        Index("idx_data_history_equipment", "equipment_id"),
        Index("idx_data_history_timestamp", "timestamp"),
        Index("idx_data_history_source", "data_source"),
        Index("idx_data_history_type", "data_type"),
        Index("idx_data_history_measurement", "measurement_type"),
        Index("idx_data_history_condition", "condition_status"),
        Index("idx_data_history_alert", "alert_level"),
        # Índice composto para queries comuns
        Index("idx_data_history_equipment_timestamp", "equipment_id", "timestamp"),
        Index("idx_data_history_equipment_type", "equipment_id", "data_type"),
    )
    
    def __repr__(self) -> str:
        return f"<DataHistory(id='{self.id}', equipment_id='{self.equipment_id}', type='{self.data_type}')>" 