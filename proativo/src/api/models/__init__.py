"""
Modelos Pydantic para API do PROAtivo.

Este módulo contém todos os modelos de dados utilizados na API FastAPI,
incluindo modelos para chat, feedback, equipamentos e respostas.
"""

from .chat import (
    ChatRequest,
    ChatResponse,
    ChatMessage,
    ChatContext,
    QueryType,
    ResponseType,
    FeedbackRequest,
    FeedbackResponse,
)

__all__ = [
    "ChatRequest",
    "ChatResponse", 
    "ChatMessage",
    "ChatContext",
    "QueryType",
    "ResponseType",
    "FeedbackRequest",
    "FeedbackResponse",
] 