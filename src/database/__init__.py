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
    Failure,
)
from .repositories import (
    BaseRepository,
    EquipmentRepository,
    MaintenanceRepository,
    FailureRepository,
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
    "Failure",
    "BaseRepository",
    "EquipmentRepository",
    "MaintenanceRepository",
    "FailureRepository",
    "UserFeedbackRepository",
    "RepositoryManager",
]
