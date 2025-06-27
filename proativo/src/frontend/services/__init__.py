"""
Módulo de serviços do frontend para integração com API backend
"""

from .api_client import APIClient, create_api_client
from .http_service import HTTPService, create_http_service

__all__ = [
    "APIClient",
    "create_api_client",
    "HTTPService", 
    "create_http_service"
] 