"""
Modelos Pydantic para funcionalidade de chat com IA.

Este módulo define os modelos de request e response para endpoints
de chat, incluindo contexto de conversa, tipos de consulta e validações.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from enum import Enum

from pydantic import BaseModel, Field, validator


class QueryType(str, Enum):
    """Tipos de consulta suportados pelo sistema."""
    EQUIPMENT_INFO = "equipment_info"
    MAINTENANCE_HISTORY = "maintenance_history"
    FAILURE_ANALYSIS = "failure_analysis"
    PERFORMANCE_METRICS = "performance_metrics"
    RECOMMENDATIONS = "recommendations"
    GENERAL_QUERY = "general_query"
    EQUIPMENT_STATUS = "equipment_status"
    MAINTENANCE_SCHEDULE = "maintenance_schedule"
    COST_ANALYSIS = "cost_analysis"
    HISTORICAL_DATA = "historical_data"
    UNKNOWN = "unknown"


class ResponseType(str, Enum):
    """Tipos de resposta do sistema."""
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"
    NO_DATA = "no_data"


class ChatMessage(BaseModel):
    """Modelo para mensagem individual do chat."""
    
    content: str = Field(
        description="Conteúdo da mensagem"
    )
    role: str = Field(
        description="Papel do remetente (user, assistant, system)",
        pattern="^(user|assistant|system)$"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp da mensagem"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Metadados adicionais da mensagem"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "Qual é o status do transformador T001?",
                "role": "user",
                "timestamp": "2024-01-15T10:30:00Z",
                "metadata": None
            }
        }


class ChatContext(BaseModel):
    """Contexto da conversa de chat."""
    
    session_id: UUID = Field(
        default_factory=uuid4,
        description="ID único da sessão de chat"
    )
    conversation_history: List[ChatMessage] = Field(
        default_factory=list,
        description="Histórico de mensagens da conversa",
        max_items=100
    )
    last_query_type: Optional[QueryType] = Field(
        default=None,
        description="Tipo da última consulta realizada"
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp de criação do contexto"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp da última atualização"
    )
    
    @validator('conversation_history')
    def validate_conversation_history(cls, v):
        """Valida que o histórico não excede o limite."""
        if len(v) > 100:
            return v[-100:]  # Manter apenas as últimas 100 mensagens
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "conversation_history": [
                    {
                        "content": "Qual é o status do transformador T001?",
                        "role": "user",
                        "timestamp": "2024-01-15T10:30:00Z"
                    }
                ],
                "last_query_type": "equipment_info",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }


class ChatRequest(BaseModel):
    """Request model para chat com IA."""
    
    message: str = Field(
        min_length=1,
        max_length=2000,
        description="Mensagem do usuário para a IA"
    )
    session_id: Optional[UUID] = Field(
        default=None,
        description="ID da sessão (será gerado automaticamente se não fornecido)"
    )
    context: Optional[ChatContext] = Field(
        default=None,
        description="Contexto atual da conversa"
    )
    include_debug: bool = Field(
        default=False,
        description="Se deve incluir informações de debug na resposta"
    )
    max_results: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Número máximo de resultados a retornar"
    )
    
    @validator('message')
    def validate_message(cls, v):
        """Valida que a mensagem não está vazia após strip."""
        if not v.strip():
            raise ValueError('Mensagem não pode estar vazia')
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Qual é o status atual dos transformadores da planta?",
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "context": None,
                "include_debug": False,
                "max_results": 10
            }
        }


class ChatResponse(BaseModel):
    """Response model para chat com IA."""
    
    session_id: UUID = Field(
        description="ID da sessão de chat"
    )
    response: str = Field(
        description="Resposta da IA para o usuário"
    )
    query_type: QueryType = Field(
        description="Tipo de consulta identificado"
    )
    response_type: ResponseType = Field(
        description="Tipo de resposta fornecida"
    )
    data_found: int = Field(
        ge=0,
        description="Quantidade de dados encontrados"
    )
    equipment_ids: List[str] = Field(
        default_factory=list,
        description="Lista de IDs de equipamentos relacionados"
    )
    processing_time_ms: int = Field(
        ge=0,
        description="Tempo de processamento em milissegundos"
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Pontuação de confiança da resposta (0.0 a 1.0)"
    )
    sources_used: List[str] = Field(
        default_factory=list,
        description="Fontes de dados utilizadas na resposta"
    )
    suggested_followup: List[str] = Field(
        default_factory=list,
        max_items=5,
        description="Sugestões de perguntas relacionadas"
    )
    context_updated: bool = Field(
        default=False,
        description="Se o contexto da conversa foi atualizado"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp da resposta"
    )
    debug_info: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Informações de debug (apenas se solicitado)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "response": "Encontrei 3 transformadores ativos na planta. O T001 está operando normalmente, o T002 precisa de manutenção preventiva em 15 dias, e o T003 foi reparado recentemente.",
                "query_type": "equipment_info",
                "response_type": "success",
                "data_found": 3,
                "equipment_ids": ["T001", "T002", "T003"],
                "processing_time_ms": 1250,
                "confidence_score": 0.92,
                "sources_used": ["database", "llm"],
                "suggested_followup": [
                    "Quando foi a última manutenção do T002?",
                    "Qual é o histórico de reparos do T003?",
                    "Mostre-me todos os equipamentos que precisam de manutenção"
                ],
                "context_updated": True,
                "timestamp": "2024-01-15T10:30:45Z",
                "debug_info": None
            }
        }


class ChatErrorResponse(BaseModel):
    """Response model para erros de chat."""
    
    error: bool = Field(
        default=True,
        description="Indica que houve erro"
    )
    error_code: str = Field(
        description="Código do erro"
    )
    message: str = Field(
        description="Mensagem de erro legível"
    )
    session_id: Optional[UUID] = Field(
        default=None,
        description="ID da sessão (se disponível)"
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Detalhes adicionais do erro"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp do erro"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": True,
                "error_code": "LLM_SERVICE_ERROR",
                "message": "Erro no serviço de IA. Tente novamente em alguns instantes.",
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "details": {
                    "internal_error": "Connection timeout to LLM service"
                },
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class ChatHistoryResponse(BaseModel):
    """Response model para histórico de chat."""
    
    session_id: UUID = Field(
        description="ID da sessão"
    )
    messages: List[ChatMessage] = Field(
        description="Lista de mensagens da sessão"
    )
    message_count: int = Field(
        ge=0,
        description="Número total de mensagens"
    )
    session_created_at: datetime = Field(
        description="Timestamp de criação da sessão"
    )
    last_activity: datetime = Field(
        description="Timestamp da última atividade"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "messages": [
                    {
                        "content": "Qual é o status do transformador T001?",
                        "role": "user",
                        "timestamp": "2024-01-15T10:30:00Z"
                    },
                    {
                        "content": "O transformador T001 está operando normalmente...",
                        "role": "assistant",
                        "timestamp": "2024-01-15T10:30:45Z"
                    }
                ],
                "message_count": 2,
                "session_created_at": "2024-01-15T10:30:00Z",
                "last_activity": "2024-01-15T10:30:45Z"
            }
        }


class FeedbackRequest(BaseModel):
    """Request model para feedback do usuário sobre respostas da IA."""
    
    message_id: UUID = Field(
        description="ID da mensagem sendo avaliada"
    )
    session_id: UUID = Field(
        description="ID da sessão de chat"
    )
    helpful: bool = Field(
        description="Se a resposta foi útil (True) ou não (False)"
    )
    rating: Optional[int] = Field(
        default=None,
        ge=1,
        le=5,
        description="Avaliação de 1-5 estrelas (opcional)"
    )
    comment: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Comentário adicional do usuário (opcional)"
    )
    category: Optional[str] = Field(
        default=None,
        description="Categoria do feedback (opcional)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "123e4567-e89b-12d3-a456-426614174000",
                "session_id": "987fcdeb-51d3-12a4-b567-123456789abc",
                "helpful": True,
                "rating": 4,
                "comment": "A resposta foi clara e precisa, me ajudou muito!",
                "category": "quality"
            }
        }


class FeedbackResponse(BaseModel):
    """Response model para confirmação de feedback recebido."""
    
    message: str = Field(
        description="Mensagem de confirmação do feedback"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp do processamento do feedback"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Obrigado pelo feedback positivo! Continuaremos melhorando para atendê-lo melhor.",
                "timestamp": "2024-01-15T10:35:00Z"
            }
        } 