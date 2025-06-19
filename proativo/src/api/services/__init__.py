"""
Serviços de IA e integração do PROAtivo.

Este módulo contém os serviços responsáveis por:
- Integração com Google Gemini LLM
- Sistema RAG (Retrieval Augmented Generation)
- Processamento de queries em linguagem natural
- Templates de prompts e context management
"""

from .llm_service import LLMService

__all__ = [
    "LLMService",
] 