"""
Modelos Pydantic para funcionalidade de upload de arquivos.

Este módulo define os modelos de request e response para endpoints
de upload, incluindo validações e tipos de dados apropriados.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4
from enum import Enum

from pydantic import BaseModel, Field, validator


class UploadStatus(str, Enum):
    """Status possíveis de um upload."""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileType(str, Enum):
    """Tipos de arquivo detectados."""
    EQUIPMENT = "equipment"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"


class UploadRequest(BaseModel):
    """Request model para upload de arquivo."""
    
    file_type: Optional[FileType] = Field(
        default=None,
        description="Tipo de dados do arquivo (auto-detectado se não informado)"
    )
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Descrição opcional do arquivo"
    )
    overwrite_existing: bool = Field(
        default=False,
        description="Se deve sobrescrever dados existentes"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "file_type": "equipment",
                "description": "Arquivo de equipamentos da planta industrial",
                "overwrite_existing": False
            }
        }


class UploadResponse(BaseModel):
    """Response model para upload de arquivo."""
    
    upload_id: UUID = Field(
        default_factory=uuid4,
        description="ID único do upload"
    )
    filename: str = Field(
        description="Nome do arquivo enviado"
    )
    file_size: int = Field(
        description="Tamanho do arquivo em bytes"
    )
    file_type: FileType = Field(
        description="Tipo de dados detectado"
    )
    status: UploadStatus = Field(
        default=UploadStatus.UPLOADED,
        description="Status atual do upload"
    )
    message: str = Field(
        description="Mensagem de status"
    )
    uploaded_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp do upload"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "upload_id": "123e4567-e89b-12d3-a456-426614174000",
                "filename": "equipamentos.csv",
                "file_size": 2048576,
                "file_type": "equipment",
                "status": "uploaded",
                "message": "Arquivo enviado com sucesso e aguardando processamento",
                "uploaded_at": "2024-01-15T10:30:00Z"
            }
        }


class UploadStatusResponse(BaseModel):
    """Response model para consulta de status de upload."""
    
    upload_id: UUID = Field(
        description="ID do upload"
    )
    filename: str = Field(
        description="Nome do arquivo"
    )
    status: UploadStatus = Field(
        description="Status atual do processamento"
    )
    progress_percentage: Optional[int] = Field(
        default=None,
        ge=0,
        le=100,
        description="Percentual de progresso (se disponível)"
    )
    records_processed: Optional[int] = Field(
        default=None,
        ge=0,
        description="Número de registros processados"
    )
    records_valid: Optional[int] = Field(
        default=None,
        ge=0,
        description="Número de registros válidos"
    )
    records_invalid: Optional[int] = Field(
        default=None,
        ge=0,
        description="Número de registros inválidos"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Mensagem de erro (se status = failed)"
    )
    started_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp de início do processamento"
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp de conclusão"
    )
    processing_time_seconds: Optional[float] = Field(
        default=None,
        ge=0,
        description="Tempo total de processamento em segundos"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "upload_id": "123e4567-e89b-12d3-a456-426614174000",
                "filename": "equipamentos.csv",
                "status": "completed",
                "progress_percentage": 100,
                "records_processed": 1250,
                "records_valid": 1200,
                "records_invalid": 50,
                "error_message": None,
                "started_at": "2024-01-15T10:31:00Z",
                "completed_at": "2024-01-15T10:33:45Z",
                "processing_time_seconds": 165.3
            }
        }


class UploadHistoryResponse(BaseModel):
    """Response model para histórico de uploads."""
    
    uploads: List[UploadStatusResponse] = Field(
        description="Lista de uploads do usuário"
    )
    total_count: int = Field(
        ge=0,
        description="Número total de uploads"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "uploads": [
                    {
                        "upload_id": "123e4567-e89b-12d3-a456-426614174000",
                        "filename": "equipamentos.csv",
                        "status": "completed",
                        "progress_percentage": 100,
                        "records_processed": 1250,
                        "records_valid": 1200,
                        "records_invalid": 50,
                        "completed_at": "2024-01-15T10:33:45Z"
                    }
                ],
                "total_count": 1
            }
        }


class UploadErrorResponse(BaseModel):
    """Response model para erros de upload."""
    
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
    details: Optional[dict] = Field(
        default=None,
        description="Detalhes adicionais do erro"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": True,
                "error_code": "FILE_TOO_LARGE",
                "message": "Arquivo excede o tamanho máximo permitido de 50MB",
                "details": {
                    "file_size": 52428800,
                    "max_size": 50331648
                }
            }
        } 