"""
Modelos Pydantic para sistema de chat do PROAtivo.

Este módulo define os modelos de dados para:
- Requisições de chat do usuário
- Respostas da IA
- Histórico de conversa
- Sistema de feedback
- Contexto e metadados
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, ConfigDict


class QueryType(str, Enum):
    """Tipos de consulta suportados pelo sistema."""
    
    EQUIPMENT_INFO = "equipment_info"
    MAINTENANCE_HISTORY = "maintenance_history"
    FAILURE_ANALYSIS = "failure_analysis"
    PERFORMANCE_METRICS = "performance_metrics"
    RECOMMENDATIONS = "recommendations"
    GENERAL_QUERY = "general_query"


class ResponseType(str, Enum):
    """Tipos de resposta do sistema."""
    
    SUCCESS = "success"
    PARTIAL = "partial"
    NO_DATA = "no_data"
    ERROR = "error"
    CLARIFICATION_NEEDED = "clarification_needed"


class ChatMessage(BaseModel):
    """Modelo para uma mensagem individual no chat."""
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }
    )
    
    id: UUID = Field(default_factory=uuid4, description="ID único da mensagem")
    content: str = Field(..., min_length=1, max_length=2000, description="Conteúdo da mensagem")
    role: str = Field(..., description="Papel (user/assistant)")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp da mensagem")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Metadados adicionais")
    
    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Valida se o role é válido."""
        valid_roles = ["user", "assistant", "system"]
        if v not in valid_roles:
            raise ValueError(f"Role deve ser um de: {valid_roles}")
        return v
    
    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Valida e limpa o conteúdo da mensagem."""
        content = v.strip()
        if not content:
            raise ValueError("Conteúdo da mensagem não pode estar vazio")
        return content


class ChatContext(BaseModel):
    """Contexto da conversa para sistema RAG."""
    
    session_id: UUID = Field(default_factory=uuid4, description="ID da sessão")
    user_id: Optional[str] = Field(default=None, description="ID do usuário (opcional)")
    conversation_history: List[ChatMessage] = Field(default=[], description="Histórico da conversa")
    relevant_equipment: List[str] = Field(default=[], description="Equipamentos relevantes identificados")
    query_context: Optional[Dict[str, Any]] = Field(default=None, description="Contexto específico da query")
    last_query_type: Optional[QueryType] = Field(default=None, description="Tipo da última consulta")
    
    @field_validator("conversation_history")
    @classmethod
    def validate_history_limit(cls, v: List[ChatMessage]) -> List[ChatMessage]:
        """Limita o histórico a últimas 50 mensagens para performance."""
        if len(v) > 50:
            return v[-50:]  # Mantém apenas as últimas 50 mensagens
        return v


class ChatRequest(BaseModel):
    """Modelo para requisição de chat do usuário."""
    
    message: str = Field(
        ..., 
        min_length=1, 
        max_length=2000, 
        description="Mensagem do usuário em linguagem natural"
    )
    session_id: Optional[UUID] = Field(
        default=None, 
        description="ID da sessão para manter contexto da conversa"
    )
    context: Optional[ChatContext] = Field(
        default=None, 
        description="Contexto adicional da conversa"
    )
    include_debug: bool = Field(
        default=False, 
        description="Incluir informações de debug na resposta"
    )
    max_results: int = Field(
        default=10, 
        ge=1, 
        le=50, 
        description="Número máximo de resultados a retornar"
    )
    
    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        """Valida e sanitiza a mensagem do usuário."""
        message = v.strip()
        if not message:
            raise ValueError("Mensagem não pode estar vazia")
        
        # Lista de caracteres potencialmente perigosos para SQL
        dangerous_chars = ["'", '"', ";", "--", "/*", "*/", "xp_", "sp_"]
        message_lower = message.lower()
        
        for char in dangerous_chars:
            if char in message_lower:
                # Log de segurança seria ideal aqui
                pass  # Por enquanto apenas registramos, não bloqueamos
        
        return message


class ChatResponse(BaseModel):
    """Modelo para resposta do sistema de chat."""
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }
    )
    
    message_id: UUID = Field(default_factory=uuid4, description="ID único da resposta")
    session_id: UUID = Field(..., description="ID da sessão")
    response: str = Field(..., description="Resposta da IA em linguagem natural")
    response_type: ResponseType = Field(..., description="Tipo da resposta")
    query_type: Optional[QueryType] = Field(None, description="Tipo de consulta identificado")
    
    # Dados estruturados (quando aplicável)
    data_found: int = Field(default=0, ge=0, description="Número de registros encontrados")
    equipment_ids: List[str] = Field(default=[], description="IDs dos equipamentos relacionados")
    maintenance_records: List[Dict[str, Any]] = Field(default=[], description="Registros de manutenção relevantes")
    
    # Métricas e metadados
    processing_time_ms: int = Field(default=0, ge=0, description="Tempo de processamento em millisegundos")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Nível de confiança da resposta")
    sources_used: List[str] = Field(default=[], description="Fontes de dados utilizadas")
    
    # Contexto para próximas consultas
    suggested_followup: List[str] = Field(default=[], description="Sugestões de perguntas relacionadas")
    context_updated: bool = Field(default=False, description="Se o contexto foi atualizado")
    
    # Debug e logging
    debug_info: Optional[Dict[str, Any]] = Field(default=None, description="Informações de debug (apenas em dev)")
    generated_sql: Optional[str] = Field(default=None, description="SQL gerado (apenas em debug)")
    
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp da resposta")
    
    @field_validator("response")
    @classmethod
    def validate_response(cls, v: str) -> str:
        """Valida a resposta da IA."""
        if not v or not v.strip():
            raise ValueError("Resposta não pode estar vazia")
        return v.strip()
    
    @field_validator("confidence_score")
    @classmethod
    def validate_confidence(cls, v: Optional[float]) -> Optional[float]:
        """Valida o score de confiança."""
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError("Confidence score deve estar entre 0.0 e 1.0")
        return v


class FeedbackRequest(BaseModel):
    """Modelo para feedback do usuário sobre uma resposta."""
    
    message_id: UUID = Field(..., description="ID da mensagem avaliada")
    session_id: UUID = Field(..., description="ID da sessão")
    rating: int = Field(..., ge=1, le=5, description="Avaliação de 1 a 5 estrelas")
    helpful: bool = Field(..., description="Se a resposta foi útil (👍/👎)")
    comment: Optional[str] = Field(
        default=None, 
        max_length=500, 
        description="Comentário adicional do usuário"
    )
    
    @field_validator("comment")
    @classmethod
    def validate_comment(cls, v: Optional[str]) -> Optional[str]:
        """Valida e limpa o comentário."""
        if v:
            comment = v.strip()
            return comment if comment else None
        return v


class FeedbackResponse(BaseModel):
    """Modelo para resposta após submissão de feedback."""
    
    feedback_id: UUID = Field(default_factory=uuid4, description="ID único do feedback")
    message: str = Field(default="Obrigado pelo seu feedback!", description="Mensagem de confirmação")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp do feedback")
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }
    )


# Modelos auxiliares para casos específicos

class EquipmentSummary(BaseModel):
    """Resumo de equipamento para respostas de chat."""
    
    id: str = Field(..., description="ID do equipamento")
    name: str = Field(..., description="Nome do equipamento")
    type: str = Field(..., description="Tipo do equipamento")
    status: str = Field(..., description="Status atual")
    last_maintenance: Optional[datetime] = Field(None, description="Data da última manutenção")
    next_maintenance: Optional[datetime] = Field(None, description="Data da próxima manutenção")
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class MaintenanceRecord(BaseModel):
    """Registro de manutenção simplificado para chat."""
    
    id: str = Field(..., description="ID do registro")
    equipment_id: str = Field(..., description="ID do equipamento")
    type: str = Field(..., description="Tipo de manutenção")
    date: datetime = Field(..., description="Data da manutenção")
    description: str = Field(..., description="Descrição da manutenção")
    cost: Optional[float] = Field(None, ge=0, description="Custo da manutenção")
    status: str = Field(..., description="Status da manutenção")
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    ) 