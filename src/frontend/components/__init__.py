"""
Componentes reutilizáveis do frontend Streamlit do PROAtivo
"""

from .chat_interface import ChatInterface, create_chat_interface
from .feedback import FeedbackSystem, create_feedback_system, quick_feedback_buttons
from .loading import LoadingIndicator, create_loading_indicator, show_api_status, processing_spinner
from .theme import ThemeManager, create_theme_manager, apply_professional_theme, COLOR_SCHEMES
from .validation import InputValidator, create_input_validator, validate_chat_input, safe_chat_input
from .error_handler import ErrorHandler, create_error_handler, safe_api_call, show_error_dashboard, handle_errors

# Importa serviços se disponíveis
try:
    import sys
    import os
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent_dir)
    from services.api_client import APIClient, create_api_client
    from services.http_service import HTTPService, create_http_service
    SERVICES_AVAILABLE = True
except ImportError:
    SERVICES_AVAILABLE = False

# Define exports baseado na disponibilidade dos serviços
base_exports = [
    "ChatInterface", 
    "create_chat_interface",
    "FeedbackSystem",
    "create_feedback_system", 
    "quick_feedback_buttons",
    "LoadingIndicator",
    "create_loading_indicator",
    "show_api_status",
    "processing_spinner",
    "ThemeManager",
    "create_theme_manager",
    "apply_professional_theme",
    "COLOR_SCHEMES",
    "InputValidator",
    "create_input_validator",
    "validate_chat_input",
    "safe_chat_input",
    "ErrorHandler",
    "create_error_handler",
    "safe_api_call",
    "show_error_dashboard",
    "handle_errors"
]

if SERVICES_AVAILABLE:
    __all__ = base_exports + [
        "APIClient",
        "create_api_client",
        "HTTPService",
        "create_http_service"
    ]
else:
    __all__ = base_exports 