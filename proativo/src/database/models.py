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


class UserFeedback(Base):
    """Modelo para armazenar feedback dos usuários sobre as respostas da IA."""
    
    __tablename__ = "user_feedback"
    
    # Chave primária
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4()),
        comment="Identificador único do feedback"
    )
    
    # Identificadores de sessão e mensagem
    session_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        nullable=False,
        comment="ID da sessão do usuário"
    )
    message_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        nullable=False,
        comment="ID da mensagem/resposta avaliada"
    )
    
    # Dados do feedback
    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Avaliação de 1 a 5 estrelas"
    )
    helpful: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        comment="Se a resposta foi útil (👍/👎)"
    )
    comment: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="Comentário adicional do usuário"
    )
    
    # Informações do usuário
    user_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        comment="Identificador do usuário (se disponível)"
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="User agent do navegador"
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        comment="Endereço IP do usuário (IPv4/IPv6)"
    )
    
    # Contexto da resposta
    original_query: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="Query original que gerou a resposta"
    )
    response_snippet: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="Trecho da resposta da IA (primeiros 500 chars)"
    )
    confidence_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(3, 2),
        comment="Score de confiança da resposta original (0.00-1.00)"
    )
    
    # Categorização do feedback
    feedback_category: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="Categoria do problema: accuracy, completeness, clarity, relevance"
    )
    improvement_priority: Mapped[Optional[str]] = mapped_column(
        String(20),
        comment="Prioridade de melhoria: low, medium, high, critical"
    )
    
    # Status e processamento
    is_processed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Se o feedback foi processado/analisado"
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        comment="Data do processamento do feedback"
    )
    
    # Dados estruturados adicionais
    metadata_json: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        comment="Metadados adicionais do feedback"
    )
    
    # Auditoria
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        comment="Data de criação do feedback"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        comment="Data da última atualização"
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "rating >= 1 AND rating <= 5", 
            name="ck_feedback_rating_range"
        ),
        CheckConstraint(
            "feedback_category IN ('accuracy', 'completeness', 'clarity', 'relevance', 'performance', 'other')", 
            name="ck_feedback_category"
        ),
        CheckConstraint(
            "improvement_priority IN ('low', 'medium', 'high', 'critical')", 
            name="ck_feedback_priority"
        ),
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0.00 AND confidence_score <= 1.00)", 
            name="ck_feedback_confidence_range"
        ),
        Index("idx_feedback_session", "session_id"),
        Index("idx_feedback_message", "message_id"),
        Index("idx_feedback_rating", "rating"),
        Index("idx_feedback_helpful", "helpful"),
        Index("idx_feedback_category", "feedback_category"),
        Index("idx_feedback_priority", "improvement_priority"),
        Index("idx_feedback_created", "created_at"),
        Index("idx_feedback_processed", "is_processed"),
        # Index composto para consultas comuns
        Index("idx_feedback_session_helpful", "session_id", "helpful"),
        Index("idx_feedback_rating_category", "rating", "feedback_category"),
    )
    
    def __repr__(self) -> str:
        return f"<UserFeedback(id='{self.id}', rating={self.rating}, helpful={self.helpful}, session='{self.session_id}')>"


class UploadStatus(Base):
    """Modelo para rastrear status de uploads de arquivos."""
    
    __tablename__ = "upload_status"
    
    # Chave primária
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4()),
        comment="Identificador único do upload"
    )
    
    # Identificador único do upload (usado pela aplicação)
    upload_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        comment="ID único do upload gerado pela aplicação"
    )
    
    # Informações do arquivo
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Nome original do arquivo enviado"
    )
    stored_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Nome do arquivo armazenado no sistema"
    )
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Caminho completo do arquivo no sistema"
    )
    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Tamanho do arquivo em bytes"
    )
    
    # Detecção de formato e tipo
    file_format: Mapped[Optional[str]] = mapped_column(
        String(20),
        comment="Formato detectado: CSV, XML, XLSX"
    )
    data_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="Tipo de dados detectado: Equipment, Maintenance, Unknown"
    )
    
    # Status do processamento
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="uploaded",
        comment="Status: uploaded, processing, completed, failed"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        comment="Data do upload"
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        comment="Início do processamento"
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        comment="Conclusão do processamento"
    )
    
    # Resultados do processamento
    records_processed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Total de registros processados"
    )
    records_valid: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Registros válidos processados"
    )
    records_invalid: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Registros inválidos encontrados"
    )
    
    # Informações de erro
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="Mensagem de erro se o processamento falhou"
    )
    error_details: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        comment="Detalhes técnicos do erro em JSON"
    )
    
    # Informações do usuário
    user_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        comment="ID do usuário que fez o upload"
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="User agent do navegador"
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        comment="Endereço IP do upload"
    )
    
    # Configurações do upload
    overwrite_existing: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Se foi configurado para sobrescrever dados existentes"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="Descrição fornecida pelo usuário"
    )
    
    # Localização final dos arquivos
    processed_file_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        comment="Caminho do arquivo após processamento"
    )
    metadata_file_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        comment="Caminho do arquivo de metadados"
    )
    
    # Metadados adicionais
    processing_metadata: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        comment="Metadados do processamento em JSON"
    )
    validation_results: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        comment="Resultados de validação em JSON"
    )
    
    # Auditoria
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        comment="Data da última atualização"
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('uploaded', 'processing', 'completed', 'failed')", 
            name="ck_upload_status_valid"
        ),
        CheckConstraint(
            "file_size > 0", 
            name="ck_upload_file_size_positive"
        ),
        CheckConstraint(
            "records_processed >= 0", 
            name="ck_upload_records_processed_positive"
        ),
        CheckConstraint(
            "records_valid >= 0", 
            name="ck_upload_records_valid_positive"
        ),
        CheckConstraint(
            "records_invalid >= 0", 
            name="ck_upload_records_invalid_positive"
        ),
        Index("idx_upload_status_upload_id", "upload_id"),
        Index("idx_upload_status_status", "status"),
        Index("idx_upload_status_created_at", "created_at"),
        Index("idx_upload_status_user_id", "user_id"),
        Index("idx_upload_status_file_format", "file_format"),
        Index("idx_upload_status_data_type", "data_type"),
    )
    
    def __repr__(self) -> str:
        return f"<UploadStatus(upload_id='{self.upload_id}', filename='{self.original_filename}', status='{self.status}')>"