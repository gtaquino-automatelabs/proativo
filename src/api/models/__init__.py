"""
Modelos Pydantic para API do PROAtivo.

Este módulo contém todos os modelos de dados utilizados
pela API REST do sistema PROAtivo.
"""

from .chat import (
    QueryType,
    ResponseType,
    ChatMessage,
    ChatContext,
    ChatRequest,
    ChatResponse,
    ChatErrorResponse,
    ChatHistoryResponse,
    FeedbackRequest,
    FeedbackResponse,
)

from .upload import (
    UploadStatus,
    FileType,
    UploadRequest,
    UploadResponse,
    UploadStatusResponse,
    UploadHistoryResponse,
    UploadErrorResponse,
)

__all__ = [
    # Chat models
    "QueryType",
    "ResponseType",
    "ChatMessage",
    "ChatContext",
    "ChatRequest",
    "ChatResponse",
    "ChatErrorResponse",
    "ChatHistoryResponse",
    "FeedbackRequest",
    "FeedbackResponse",
    # Upload models
    "UploadStatus",
    "FileType",
    "UploadRequest",
    "UploadResponse",
    "UploadStatusResponse",
    "UploadHistoryResponse",
    "UploadErrorResponse",
] 