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
    PMM_2,
    SAPLocation,
)
from .repositories import (
    BaseRepository,
    EquipmentRepository,
    MaintenanceRepository,
    FailureRepository,
    UserFeedbackRepository,
    UploadStatusRepository,
    PMM_2Repository,
    SAPLocationRepository,
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
    "PMM_2",
    "SAPLocation",
    "BaseRepository",
    "EquipmentRepository",
    "MaintenanceRepository",
    "FailureRepository",
    "UserFeedbackRepository",
    "UploadStatusRepository",
    "PMM_2Repository",
    "SAPLocationRepository",
    "RepositoryManager",
]
