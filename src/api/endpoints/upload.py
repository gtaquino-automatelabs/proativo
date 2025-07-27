"""
Endpoints para upload de arquivos no sistema PROAtivo.

Este módulo implementa endpoints para upload, consulta de status e
histórico de arquivos enviados pelos usuários.
"""

import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import JSONResponse

from ..dependencies import get_current_settings, validate_request_size
from ..config import Settings
from ..models.upload import (
    UploadResponse, 
    UploadStatusResponse, 
    UploadHistoryResponse,
    UploadErrorResponse,
    FileType,
    UploadStatus
)
from ...etl.data_processor import DataProcessor, FileFormat
from ...utils.error_handlers import DataProcessingError

# Configurar logging
logger = logging.getLogger(__name__)

# Criar router para endpoints de upload
router = APIRouter(prefix="/files", tags=["File Upload"])


def detect_file_type_from_name(filename: str) -> FileType:
    """
    Detecta tipo de arquivo baseado no nome.
    
    Args:
        filename: Nome do arquivo
        
    Returns:
        FileType detectado
    """
    filename_lower = filename.lower()
    
    # Palavras-chave para equipamentos
    equipment_keywords = ['equipment', 'equipamento', 'equip', 'asset', 'ativo']
    
    # Palavras-chave para manutenções
    maintenance_keywords = ['maintenance', 'manutencao', 'manutenção', 'maint', 'servico', 'serviço']
    
    # Verifica nome do arquivo
    for keyword in equipment_keywords:
        if keyword in filename_lower:
            return FileType.EQUIPMENT
    
    for keyword in maintenance_keywords:
        if keyword in filename_lower:
            return FileType.MAINTENANCE
    
    # Default
    return FileType.UNKNOWN


def validate_file_extension(filename: str, allowed_extensions: list) -> bool:
    """
    Valida se a extensão do arquivo é permitida.
    
    Args:
        filename: Nome do arquivo
        allowed_extensions: Lista de extensões permitidas
        
    Returns:
        True se válida, False caso contrário
    """
    file_extension = Path(filename).suffix.lower()
    return file_extension in allowed_extensions


def generate_unique_filename(original_filename: str, upload_dir: Path) -> str:
    """
    Gera nome único para arquivo evitando conflitos.
    
    Args:
        original_filename: Nome original do arquivo
        upload_dir: Diretório de upload
        
    Returns:
        Nome único para o arquivo
    """
    # Separar nome e extensão
    file_path = Path(original_filename)
    stem = file_path.stem
    suffix = file_path.suffix
    
    # Gerar nome único usando UUID
    unique_id = str(uuid4())[:8]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    unique_filename = f"{stem}_{timestamp}_{unique_id}{suffix}"
    
    # Verificar se ainda não existe (muito improvável, mas por segurança)
    counter = 1
    while (upload_dir / unique_filename).exists():
        unique_filename = f"{stem}_{timestamp}_{unique_id}_{counter}{suffix}"
        counter += 1
    
    return unique_filename


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(..., description="Arquivo para upload"),
    file_type: Optional[FileType] = Form(None, description="Tipo de dados do arquivo"),
    description: Optional[str] = Form(None, description="Descrição opcional do arquivo"),
    overwrite_existing: bool = Form(False, description="Sobrescrever dados existentes"),
    settings: Settings = Depends(get_current_settings),
    _: None = Depends(validate_request_size),
) -> UploadResponse:
    """
    Endpoint para upload de arquivos de dados.
    
    Aceita arquivos CSV, XML e XLSX para processamento posterior.
    O arquivo é validado quanto ao tamanho e extensão antes de ser salvo.
    
    Args:
        file: Arquivo enviado
        file_type: Tipo de dados (opcional, será auto-detectado)
        description: Descrição opcional
        overwrite_existing: Se deve sobrescrever dados existentes
        settings: Configurações da aplicação
        
    Returns:
        UploadResponse com detalhes do upload
        
    Raises:
        HTTPException: Erro de validação ou processamento
    """
    upload_id = uuid4()
    
    try:
        logger.info(f"Iniciando upload - ID: {upload_id}, Arquivo: {file.filename}")
        
        # Validar se arquivo foi enviado
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nome do arquivo não pode estar vazio"
            )
        
        # Validar extensão do arquivo
        if not validate_file_extension(file.filename, settings.upload_allowed_extensions):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Extensão de arquivo não permitida. Extensões aceitas: {', '.join(settings.upload_allowed_extensions)}"
            )
        
        # Ler conteúdo do arquivo para validar tamanho
        file_content = await file.read()
        file_size = len(file_content)
        
        # Validar tamanho do arquivo
        if file_size > settings.upload_max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Arquivo muito grande ({file_size} bytes). Tamanho máximo: {settings.upload_max_size} bytes"
            )
        
        # Garantir que diretório de upload existe
        upload_dir = Path(settings.upload_directory)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Gerar nome único para o arquivo
        unique_filename = generate_unique_filename(file.filename, upload_dir)
        file_path = upload_dir / unique_filename
        
        # Salvar arquivo
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        
        # Detectar tipo de arquivo se não fornecido
        detected_file_type = file_type or detect_file_type_from_name(file.filename)
        
        # Validação prévia usando DataProcessor
        try:
            data_processor = DataProcessor()
            
            # Detecta formato do arquivo
            file_format = data_processor.detect_file_format(file_path)
            
            # Detecta tipo de dados
            data_type = data_processor.detect_data_type(file_path, file_format)
            
            logger.info(f"Arquivo validado - Formato: {file_format.value}, Tipo: {data_type.value}")
            
        except Exception as validation_error:
            # Se houver erro na validação, remove o arquivo e retorna erro
            if file_path.exists():
                file_path.unlink()
            
            logger.warning(f"Erro na validação do arquivo: {validation_error}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Arquivo inválido ou corrompido: {str(validation_error)}"
            )
        
        # Registra upload no banco de dados
        try:
            from ...database.connection import get_async_session
            from ...database.repositories import RepositoryManager
            
            async with get_async_session() as session:
                repo_manager = RepositoryManager(session)
                
                # Dados do upload para o banco
                upload_data = {
                    'upload_id': str(upload_id),
                    'original_filename': file.filename,
                    'stored_filename': unique_filename,
                    'file_path': str(file_path),
                    'file_size': file_size,
                    'file_format': file_format.value if file_format else None,
                    'data_type': data_type.value if data_type else None,
                    'status': 'uploaded',
                    'description': description,
                    'overwrite_existing': overwrite_existing
                }
                
                # Cria registro no banco
                upload_record = await repo_manager.upload_status.create(**upload_data)
                await repo_manager.commit()
                
                logger.debug(f"Upload registrado no banco: {upload_record.id}")
                
        except Exception as db_error:
            logger.warning(f"Erro ao registrar upload no banco: {db_error}")
            # Continua mesmo com erro no banco, pois o arquivo foi salvo
        
        # Criar resposta
        response = UploadResponse(
            upload_id=upload_id,
            filename=file.filename,
            file_size=file_size,
            file_type=detected_file_type,
            status=UploadStatus.UPLOADED,
            message="Arquivo enviado com sucesso e aguardando processamento",
            uploaded_at=datetime.now()
        )
        
        logger.info(f"Upload concluído - ID: {upload_id}, Arquivo: {unique_filename}, Tamanho: {file_size} bytes")
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except Exception as e:
        logger.error(f"Erro inesperado no upload - ID: {upload_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno durante upload do arquivo"
        )


@router.get("/status/{upload_id}", response_model=UploadStatusResponse)
async def get_upload_status(
    upload_id: str,
    settings: Settings = Depends(get_current_settings),
) -> UploadStatusResponse:
    """
    Consulta o status de um upload específico.
    
    Args:
        upload_id: ID do upload para consultar
        settings: Configurações da aplicação
        
    Returns:
        UploadStatusResponse com status atual
        
    Raises:
        HTTPException: Se upload não for encontrado
    """
    try:
        logger.info(f"Consultando status do upload: {upload_id}")
        
        # Importa repositório dentro da função para evitar circular imports
        from ...database.connection import get_async_session
        from ...database.repositories import RepositoryManager
        
        # Busca upload no banco de dados
        async with get_async_session() as session:
            repo_manager = RepositoryManager(session)
            upload_record = await repo_manager.upload_status.get_by_upload_id(upload_id)
            
            if not upload_record:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Upload {upload_id} não encontrado"
                )
            
            # Calcula progresso e tempo de processamento
            progress_percentage = 0
            processing_time_seconds = None
            
            if upload_record.status == "completed":
                progress_percentage = 100
            elif upload_record.status == "processing":
                progress_percentage = 50  # Estimativa para processamento em andamento
            elif upload_record.status == "failed":
                progress_percentage = 0
            
            # Calcula tempo de processamento se disponível
            if upload_record.started_at and upload_record.completed_at:
                processing_time_seconds = (upload_record.completed_at - upload_record.started_at).total_seconds()
            
            # Mapeia status do banco para enum da API
            api_status_map = {
                "uploaded": UploadStatus.UPLOADED,
                "processing": UploadStatus.PROCESSING,
                "completed": UploadStatus.COMPLETED,
                "failed": UploadStatus.FAILED
            }
            
            api_status = api_status_map.get(upload_record.status, UploadStatus.UPLOADED)
            
            # Cria resposta
            response = UploadStatusResponse(
                upload_id=upload_record.upload_id,
                filename=upload_record.original_filename,
                status=api_status,
                progress_percentage=progress_percentage,
                records_processed=upload_record.records_processed if upload_record.records_processed > 0 else None,
                records_valid=upload_record.records_valid if upload_record.records_valid > 0 else None,
                records_invalid=upload_record.records_invalid if upload_record.records_invalid > 0 else None,
                error_message=upload_record.error_message,
                started_at=upload_record.started_at,
                completed_at=upload_record.completed_at,
                processing_time_seconds=processing_time_seconds
            )
            
            logger.info(f"Status encontrado: {upload_record.status} - {upload_record.original_filename}")
            return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except Exception as e:
        logger.error(f"Erro ao consultar status do upload {upload_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao consultar status do upload"
        )


@router.get("/history", response_model=UploadHistoryResponse)
async def get_upload_history(
    limit: int = 10,
    status_filter: Optional[str] = None,
    settings: Settings = Depends(get_current_settings),
) -> UploadHistoryResponse:
    """
    Retorna histórico de uploads do usuário com métricas completas.
    
    Args:
        limit: Número máximo de uploads para retornar (padrão: 10)
        status_filter: Filtrar por status específico (opcional)
        settings: Configurações da aplicação
        
    Returns:
        UploadHistoryResponse com lista de uploads e métricas
    """
    try:
        logger.info(f"Consultando histórico de uploads - Limite: {limit}, Filtro: {status_filter}")
        
        # Importa repositório dentro da função para evitar circular imports
        from ...database.connection import get_async_session
        from ...database.repositories import RepositoryManager
        
        # Busca uploads no banco de dados
        async with get_async_session() as session:
            repo_manager = RepositoryManager(session)
            
            # Busca uploads com filtro de status se especificado
            if status_filter:
                upload_records = await repo_manager.upload_status.list_by_status(status_filter, limit)
                total_count = len(upload_records)  # Aproximação para consulta filtrada
            else:
                # Busca uploads recentes (todos os status)
                all_uploads = []
                for status in ["uploaded", "processing", "completed", "failed"]:
                    status_uploads = await repo_manager.upload_status.list_by_status(status, limit//4 + 1)
                    all_uploads.extend(status_uploads)
                
                # Ordena por data de criação e limita
                upload_records = sorted(all_uploads, key=lambda x: x.created_at, reverse=True)[:limit]
                total_count = len(upload_records)
            
            # Converte registros do banco para formato da API
            upload_responses = []
            
            for upload_record in upload_records:
                # Calcula progresso e tempo de processamento
                progress_percentage = 0
                processing_time_seconds = None
                
                if upload_record.status == "completed":
                    progress_percentage = 100
                elif upload_record.status == "processing":
                    progress_percentage = 50  # Estimativa para processamento em andamento
                elif upload_record.status == "failed":
                    progress_percentage = 0
                
                # Calcula tempo de processamento se disponível
                if upload_record.started_at and upload_record.completed_at:
                    processing_time_seconds = (upload_record.completed_at - upload_record.started_at).total_seconds()
                
                # Mapeia status do banco para enum da API
                api_status_map = {
                    "uploaded": UploadStatus.UPLOADED,
                    "processing": UploadStatus.PROCESSING,
                    "completed": UploadStatus.COMPLETED,
                    "failed": UploadStatus.FAILED
                }
                
                api_status = api_status_map.get(upload_record.status, UploadStatus.UPLOADED)
                
                # Cria resposta para cada upload
                upload_response = UploadStatusResponse(
                    upload_id=upload_record.upload_id,
                    filename=upload_record.original_filename,
                    status=api_status,
                    progress_percentage=progress_percentage,
                    records_processed=upload_record.records_processed if upload_record.records_processed > 0 else None,
                    records_valid=upload_record.records_valid if upload_record.records_valid > 0 else None,
                    records_invalid=upload_record.records_invalid if upload_record.records_invalid > 0 else None,
                    error_message=upload_record.error_message,
                    started_at=upload_record.started_at,
                    completed_at=upload_record.completed_at,
                    processing_time_seconds=processing_time_seconds
                )
                
                upload_responses.append(upload_response)
            
            # Cria resposta final
            response = UploadHistoryResponse(
                uploads=upload_responses,
                total_count=total_count
            )
            
            logger.info(f"Histórico encontrado: {len(upload_responses)} uploads de {total_count} total")
            return response
        
    except Exception as e:
        logger.error(f"Erro ao consultar histórico de uploads: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao consultar histórico"
        )





@router.post("/process-pending")
async def process_pending_uploads(
    settings: Settings = Depends(get_current_settings),
) -> dict:
    """
    Processa uploads que estão com status 'uploaded' e aguardando processamento.
    
    Returns:
        Dict com resultado do processamento
    """
    try:
        logger.info("Iniciando processamento de uploads pendentes")
        
        from ...database.connection import get_async_session
        from ...database.repositories import RepositoryManager
        from ...etl.data_processor import DataProcessor
        from ...etl.data_ingestion import DataIngestionOrchestrator
        
        processed_count = 0
        error_count = 0
        results = []
        
        # Buscar uploads pendentes
        async with get_async_session() as session:
            repo_manager = RepositoryManager(session)
            
            # Buscar uploads com status 'uploaded'
            pending_uploads = await repo_manager.upload_status.list_by_status("uploaded", 100)
            
            logger.info(f"Encontrados {len(pending_uploads)} uploads pendentes")
            
            data_processor = DataProcessor(repository_manager=repo_manager)
            
            for upload in pending_uploads:
                try:
                    # Atualizar status para 'processing'
                    await repo_manager.upload_status.update_status(
                        upload.upload_id, 
                        "processing",
                        progress_percentage=10
                    )
                    await repo_manager.commit()
                    
                    logger.info(f"Processando upload {upload.upload_id}: {upload.original_filename}")
                    
                    # Verificar se arquivo existe
                    file_path = Path(upload.file_path)
                    if not file_path.exists():
                        await repo_manager.upload_status.update_status(
                            upload.upload_id,
                            "failed",
                            error_message="Arquivo não encontrado no sistema"
                        )
                        await repo_manager.commit()
                        error_count += 1
                        continue
                    
                    # Converter strings para enums se necessário
                    from ...etl.data_processor import FileFormat, DataType
                    
                    file_format = None
                    if upload.file_format:
                        try:
                            file_format = FileFormat(upload.file_format)
                        except ValueError:
                            file_format = None
                    
                    data_type = None
                    if upload.data_type:
                        try:
                            data_type = DataType(upload.data_type)
                        except ValueError:
                            data_type = None
                    
                    # Processar arquivo
                    process_result = await data_processor.process_and_save(
                        file_path,
                        data_type,
                        file_format
                    )
                    
                    # Atualizar progresso
                    await repo_manager.upload_status.update_status(
                        upload.upload_id,
                        "processing", 
                        progress_percentage=75,
                        records_processed=process_result.get("total_records", 0)
                    )
                    await repo_manager.commit()
                    
                    # Finalizar com sucesso
                    await repo_manager.upload_status.update_status(
                        upload.upload_id,
                        "completed",
                        progress_percentage=100,
                        records_processed=process_result.get("total_records", 0),
                        records_valid=process_result.get("valid_records", 0),
                        records_invalid=process_result.get("invalid_records", 0),
                        completed_at=datetime.now()
                    )
                    await repo_manager.commit()
                    
                    processed_count += 1
                    results.append({
                        "upload_id": upload.upload_id,
                        "filename": upload.original_filename,
                        "status": "completed",
                        "records_processed": process_result.get("total_records", 0)
                    })
                    
                    logger.info(f"Upload {upload.upload_id} processado com sucesso")
                    
                except Exception as process_error:
                    logger.error(f"Erro ao processar upload {upload.upload_id}: {process_error}")
                    
                    # Marcar como falho
                    await repo_manager.upload_status.update_status(
                        upload.upload_id,
                        "failed", 
                        error_message=str(process_error)[:500]
                    )
                    await repo_manager.commit()
                    
                    error_count += 1
                    results.append({
                        "upload_id": upload.upload_id,
                        "filename": upload.original_filename,
                        "status": "failed",
                        "error": str(process_error)
                    })
        
        response = {
            "processed_count": processed_count,
            "error_count": error_count,
            "total_pending": len(pending_uploads),
            "results": results
        }
        
        logger.info(f"Processamento concluído: {processed_count} sucessos, {error_count} erros")
        return response
        
    except Exception as e:
        logger.error(f"Erro no processamento de uploads pendentes: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erro interno no processamento de uploads"
        )





 