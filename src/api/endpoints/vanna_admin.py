"""
Endpoint administrativo para gerenciamento do Vanna.ai.

Este módulo fornece endpoints para:
- Monitorar status do Vanna
- Executar treinamento manual
- Configurar auto-treinamento
- Visualizar métricas de uso
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel

from ..dependencies import get_current_settings
from ..config import Settings
from ..services.vanna_service import get_vanna_service
from ..services.vanna_query_processor import get_vanna_query_processor
from ..services.vanna_auto_trainer import get_vanna_auto_trainer

logger = logging.getLogger(__name__)

# Criar router para endpoints administrativos do Vanna
router = APIRouter(prefix="/admin/vanna", tags=["Vanna Admin"])

class TrainingRequest(BaseModel):
    """Request para treinamento manual."""
    force: bool = False
    add_examples: bool = True

class ConfigUpdateRequest(BaseModel):
    """Request para atualizar configurações."""
    confidence_threshold: float = None
    check_interval_minutes: int = None
    enable_auto_training: bool = None

class VannaStatusResponse(BaseModel):
    """Resposta com status completo do Vanna."""
    service_status: Dict[str, Any]
    processor_status: Dict[str, Any]
    auto_trainer_status: Dict[str, Any]
    usage_statistics: Dict[str, Any]
    compatibility_check: Dict[str, Any]

@router.get("/status", response_model=VannaStatusResponse)
async def get_vanna_status(
    settings: Settings = Depends(get_current_settings)
) -> VannaStatusResponse:
    """
    Retorna status completo do sistema Vanna.ai.
    
    Inclui:
    - Status do serviço principal
    - Status do processador híbrido
    - Status do auto-trainer
    - Estatísticas de uso
    """
    try:
        vanna_service = get_vanna_service()
        vanna_processor = get_vanna_query_processor()
        auto_trainer = get_vanna_auto_trainer()
        
        service_status = {
            "initialized": vanna_service.is_initialized,
            "model_name": vanna_service.model_name,
            "llm_provider": settings.vanna_llm_provider,
            "confidence_threshold": settings.vanna_confidence_threshold,
            "training_enabled": settings.vanna_enable_training
        }
        
        processor_status = {
            "confidence_threshold": vanna_processor.confidence_threshold,
            "vanna_service_available": vanna_processor.vanna_service.is_initialized,
            "fallback_processor_available": True  # Sempre disponível
        }
        
        auto_trainer_status = auto_trainer.get_status()
        usage_stats = vanna_processor.get_usage_statistics()
        
        # Diagnóstico de compatibilidade
        compatibility_issues = []
        dependency_versions = {}
        
        # Verificar Vanna.ai
        try:
            import importlib.metadata
            dependency_versions["vanna"] = importlib.metadata.version("vanna")
        except ImportError:
            dependency_versions["vanna"] = "Not installed"
            compatibility_issues.append("Vanna.ai not installed")
        except Exception as e:
            dependency_versions["vanna"] = f"Error: {e}"
            compatibility_issues.append(f"Vanna.ai import error: {e}")
        
        # Verificar ChromaDB
        try:
            import chromadb
            dependency_versions["chromadb"] = chromadb.__version__
        except ImportError:
            dependency_versions["chromadb"] = "Not installed"
            compatibility_issues.append("ChromaDB not installed")
        except Exception as e:
            dependency_versions["chromadb"] = f"Error: {e}"
            compatibility_issues.append(f"ChromaDB import error: {e}")
        
        # Verificar NumPy
        try:
            import numpy as np
            dependency_versions["numpy"] = np.__version__
            if int(np.__version__.split('.')[0]) >= 2:
                compatibility_issues.append(f"NumPy {np.__version__} may be incompatible with ChromaDB (use <2.0.0)")
        except ImportError:
            dependency_versions["numpy"] = "Not installed"
            compatibility_issues.append("NumPy not installed")
        except Exception as e:
            dependency_versions["numpy"] = f"Error: {e}"
            compatibility_issues.append(f"NumPy import error: {e}")
        
        compatibility_check = {
            "dependency_versions": dependency_versions,
            "compatibility_issues": compatibility_issues,
            "system_ready": vanna_service.is_initialized and len(compatibility_issues) == 0,
            "recommendations": []
        }
        
        # Adicionar recomendações baseadas nos problemas encontrados
        if any("NumPy" in issue and "2.0" in issue for issue in compatibility_issues):
            compatibility_check["recommendations"].append(
                "Execute: pip install 'numpy>=1.21.0,<2.0.0' para resolver compatibilidade"
            )
        
        if any("ChromaDB" in issue for issue in compatibility_issues):
            compatibility_check["recommendations"].append(
                "Execute: pip install 'chromadb>=0.4.0,<0.5.0' para instalar ChromaDB"
            )
        
        if any("Vanna" in issue for issue in compatibility_issues):
            compatibility_check["recommendations"].append(
                "Execute: pip install 'vanna>=0.7.9' para instalar Vanna.ai"
            )
        
        return VannaStatusResponse(
            service_status=service_status,
            processor_status=processor_status,
            auto_trainer_status=auto_trainer_status,
            usage_statistics=usage_stats,
            compatibility_check=compatibility_check
        )
        
    except Exception as e:
        logger.error(f"Error getting Vanna status: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao obter status: {str(e)}")

@router.post("/train")
async def trigger_training(
    request: TrainingRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_current_settings)
):
    """
    Executa treinamento manual do modelo Vanna.
    
    Args:
        request: Parâmetros do treinamento
        background_tasks: Para execução em background
        
    Returns:
        Status da operação de treinamento
    """
    if not settings.vanna_enable_training:
        raise HTTPException(
            status_code=403, 
            detail="Treinamento automático está desabilitado nas configurações"
        )
    
    try:
        auto_trainer = get_vanna_auto_trainer()
        
        if auto_trainer.training_in_progress and not request.force:
            raise HTTPException(
                status_code=409,
                detail="Treinamento já em andamento. Use force=true para forçar novo treinamento."
            )
        
        # Executar treinamento em background
        if request.force:
            background_tasks.add_task(auto_trainer.force_retrain)
            message = "Treinamento forçado iniciado em background"
        else:
            background_tasks.add_task(auto_trainer._execute_training)
            message = "Treinamento iniciado em background"
        
        logger.info(f"Manual training triggered: force={request.force}")
        
        return {
            "status": "started",
            "message": message,
            "force": request.force,
            "timestamp": auto_trainer.last_training_time.isoformat() if auto_trainer.last_training_time else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering training: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao iniciar treinamento: {str(e)}")

@router.put("/config")
async def update_config(
    request: ConfigUpdateRequest,
    settings: Settings = Depends(get_current_settings)
):
    """
    Atualiza configurações do Vanna em runtime.
    
    Args:
        request: Novas configurações
        
    Returns:
        Configurações atualizadas
    """
    try:
        vanna_processor = get_vanna_query_processor()
        auto_trainer = get_vanna_auto_trainer()
        
        updated_fields = []
        
        # Atualizar threshold de confiança
        if request.confidence_threshold is not None:
            if not 0.0 <= request.confidence_threshold <= 1.0:
                raise HTTPException(
                    status_code=400,
                    detail="Confidence threshold deve estar entre 0.0 e 1.0"
                )
            
            vanna_processor.update_confidence_threshold(request.confidence_threshold)
            updated_fields.append(f"confidence_threshold={request.confidence_threshold}")
        
        # Atualizar intervalo de verificação do auto-trainer
        if request.check_interval_minutes is not None:
            if request.check_interval_minutes < 5:
                raise HTTPException(
                    status_code=400,
                    detail="Check interval deve ser pelo menos 5 minutos"
                )
            
            auto_trainer.check_interval_minutes = request.check_interval_minutes
            updated_fields.append(f"check_interval_minutes={request.check_interval_minutes}")
        
        logger.info(f"Vanna config updated: {', '.join(updated_fields)}")
        
        return {
            "status": "updated",
            "updated_fields": updated_fields,
            "current_config": {
                "confidence_threshold": vanna_processor.confidence_threshold,
                "check_interval_minutes": auto_trainer.check_interval_minutes,
                "training_enabled": settings.vanna_enable_training
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar configurações: {str(e)}")

@router.post("/test")
async def test_vanna(
    question: str = "Quantos equipamentos temos no total?"
):
    """
    Testa o funcionamento do Vanna com uma pergunta.
    
    Args:
        question: Pergunta para testar
        
    Returns:
        Resultado do teste incluindo SQL gerado e métricas
    """
    try:
        vanna_processor = get_vanna_query_processor()
        
        # Processar query de teste
        result = await vanna_processor.process_query(question)
        
        return {
            "status": "success",
            "test_question": question,
            "result": {
                "sql_generated": bool(result.sql_query),
                "sql_query": result.sql_query,
                "processing_method": result.processing_method,
                "confidence_score": result.confidence_score,
                "processing_time": result.processing_time,
                "explanation": result.explanation,
                "suggestions": result.suggestions
            },
            "vanna_response": {
                "available": result.vanna_response is not None,
                "confidence": result.vanna_response.confidence if result.vanna_response else None,
                "error": result.vanna_response.error if result.vanna_response else None
            } if result.vanna_response else None
        }
        
    except Exception as e:
        logger.error(f"Error testing Vanna: {e}")
        raise HTTPException(status_code=500, detail=f"Erro no teste: {str(e)}")

@router.get("/metrics")
async def get_metrics():
    """
    Retorna métricas detalhadas de uso do Vanna.
    
    Returns:
        Métricas de performance e uso
    """
    try:
        vanna_processor = get_vanna_query_processor()
        auto_trainer = get_vanna_auto_trainer()
        vanna_service = get_vanna_service()
        
        usage_stats = vanna_processor.get_usage_statistics()
        trainer_status = auto_trainer.get_status()
        
        return {
            "usage_statistics": usage_stats,
            "auto_trainer": {
                "training_enabled": trainer_status["training_enabled"],
                "last_training": trainer_status["last_training_time"],
                "schema_monitoring": {
                    "tables_monitored": trainer_status["tables_monitored"],
                    "columns_monitored": trainer_status["columns_monitored"],
                    "last_check": trainer_status["last_schema_check"],
                    "checksum": trainer_status["schema_checksum"]
                }
            },
            "service_health": {
                "vanna_initialized": vanna_service.is_initialized,
                "model_name": vanna_service.model_name
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao obter métricas: {str(e)}")

@router.post("/reset-stats")
async def reset_statistics():
    """
    Reseta as estatísticas de uso do processador híbrido.
    
    Returns:
        Confirmação do reset
    """
    try:
        vanna_processor = get_vanna_query_processor()
        
        # Reset das estatísticas
        vanna_processor.usage_stats = {
            'vanna_success': 0,
            'fallback_used': 0,
            'hybrid_used': 0,
            'total_queries': 0
        }
        
        logger.info("Vanna usage statistics reset")
        
        return {
            "status": "reset",
            "message": "Estatísticas de uso resetadas com sucesso",
            "new_stats": vanna_processor.get_usage_statistics()
        }
        
    except Exception as e:
        logger.error(f"Error resetting stats: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao resetar estatísticas: {str(e)}") 