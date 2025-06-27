"""
Configurações compartilhadas para testes do PROAtivo.

Este módulo contém fixtures e configurações compartilhadas
entre os testes unitários e de integração.
"""

import pytest
import sys
import os
from unittest.mock import Mock

# Adicionar src ao path para imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

@pytest.fixture
def mock_settings():
    """Mock das configurações do sistema."""
    settings = Mock()
    settings.gemini_api_key = "test_api_key"
    settings.gemini_model = "gemini-2.5-flash"
    settings.gemini_temperature = 0.1
    settings.gemini_max_tokens = 2048
    settings.gemini_timeout = 30
    settings.gemini_max_retries = 3
    settings.database_url = "postgresql://test:test@localhost:5432/test"
    return settings

@pytest.fixture
def sample_equipment_data():
    """Dados de exemplo para equipamentos."""
    return [
        {
            "id": "T001",
            "name": "Transformador Principal",
            "type": "transformador",
            "status": "operacional",
            "location": "São Paulo",
            "manufacturer": "Fabricante A",
            "model": "Modelo X"
        },
        {
            "id": "GER-123",
            "name": "Gerador de Emergência",
            "type": "gerador",
            "status": "manutenção",
            "location": "Rio de Janeiro",
            "manufacturer": "Fabricante B",
            "model": "Modelo Y"
        }
    ]

@pytest.fixture
def sample_maintenance_data():
    """Dados de exemplo para manutenções."""
    return [
        {
            "id": "M001",
            "equipment_id": "T001",
            "type": "preventiva",
            "status": "agendada",
            "scheduled_date": "2024-01-15",
            "cost": 1500.00
        },
        {
            "id": "M002",
            "equipment_id": "GER-123",
            "type": "corretiva",
            "status": "concluída",
            "scheduled_date": "2024-01-10",
            "completion_date": "2024-01-12",
            "cost": 3200.00
        }
    ]

@pytest.fixture
def sample_queries():
    """Consultas de exemplo para testes."""
    return [
        "Status dos transformadores",
        "Manutenções programadas para esta semana",
        "Equipamentos com falhas críticas",
        "Custo total de manutenções este mês",
        "Liste todos os geradores operacionais"
    ]

@pytest.fixture(autouse=True)
def setup_test_environment():
    """Configuração automática do ambiente de teste."""
    # Configurar variáveis de ambiente para testes
    os.environ["TESTING"] = "true"
    os.environ["LOG_LEVEL"] = "DEBUG"
    
    yield
    
    # Limpeza após teste
    if "TESTING" in os.environ:
        del os.environ["TESTING"]
    if "LOG_LEVEL" in os.environ:
        del os.environ["LOG_LEVEL"] 