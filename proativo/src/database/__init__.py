"""
Módulo de banco de dados do PROAtivo.

Contém configurações de conexão, modelos e repositories.
"""

from .connection import (
    Base,
    DatabaseConnection,
    DatabaseSettings,
    db_connection,
    init_database,
    close_database,
    get_db_session,
    create_tables,
    drop_tables,
    check_database_connection,
)
from .models import (
    Equipment,
    Maintenance,
    DataHistory,
)
from .repositories import (
    BaseRepository,
    EquipmentRepository,
    MaintenanceRepository,
    DataHistoryRepository,
    RepositoryManager,
)

__all__ = [
    "Base",
    "DatabaseConnection", 
    "DatabaseSettings",
    "db_connection",
    "init_database",
    "close_database",
    "get_db_session",
    "create_tables",
    "drop_tables",
    "check_database_connection",
    "Equipment",
    "Maintenance",
    "DataHistory",
    "BaseRepository",
    "EquipmentRepository",
    "MaintenanceRepository",
    "DataHistoryRepository",
    "UserFeedbackRepository",
    "RepositoryManager",
]
