#!/usr/bin/env python3
"""
Script para criar a tabela upload_status no banco de dados.

Este script cria a tabela para rastrear o status de uploads de arquivos,
incluindo informações de processamento, erro e metadados.
"""

import sys
import os
import logging
from pathlib import Path
from sqlalchemy import text
from datetime import datetime

# Adiciona o diretório src ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from database.connection import get_database_connection, Base
from database.models import UploadStatus

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_upload_status_table():
    """Cria a tabela upload_status no banco de dados."""
    try:
        logger.info("Conectando ao banco de dados...")
        
        # Obtém conexão com o banco
        engine = get_database_connection()
        
        logger.info("Criando tabela upload_status...")
        
        # Cria apenas a tabela UploadStatus
        UploadStatus.__table__.create(engine, checkfirst=True)
        
        logger.info("✅ Tabela upload_status criada com sucesso!")
        
        # Verifica se a tabela foi criada
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'upload_status' 
                ORDER BY ordinal_position
            """))
            
            columns = result.fetchall()
            
            if columns:
                logger.info(f"Tabela criada com {len(columns)} colunas:")
                for col in columns:
                    nullable = "NULL" if col.is_nullable == "YES" else "NOT NULL"
                    logger.info(f"  - {col.column_name}: {col.data_type} {nullable}")
            else:
                logger.warning("Não foi possível verificar as colunas da tabela")
        
        # Verifica índices
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT indexname, indexdef 
                FROM pg_indexes 
                WHERE tablename = 'upload_status'
                ORDER BY indexname
            """))
            
            indexes = result.fetchall()
            
            if indexes:
                logger.info(f"Índices criados ({len(indexes)}):")
                for idx in indexes:
                    logger.info(f"  - {idx.indexname}")
            
        logger.info("✅ Setup da tabela upload_status concluído!")
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar tabela upload_status: {e}")
        return False
    
    return True


def test_upload_status_operations():
    """Testa operações básicas na tabela upload_status."""
    try:
        logger.info("Testando operações na tabela upload_status...")
        
        from database.repositories import RepositoryManager
        
        # Inicializa repositório
        repo_manager = RepositoryManager()
        
        # Teste de inserção
        test_upload = UploadStatus(
            upload_id="test_upload_001",
            original_filename="test_file.csv",
            stored_filename="test_file_20240101_123456.csv",
            file_path="/data/uploads/test_file_20240101_123456.csv",
            file_size=1024,
            status="uploaded"
        )
        
        with repo_manager.get_session() as session:
            session.add(test_upload)
            session.commit()
            
            logger.info(f"✅ Registro de teste inserido: {test_upload.upload_id}")
            
            # Teste de consulta
            found_upload = session.query(UploadStatus).filter_by(
                upload_id="test_upload_001"
            ).first()
            
            if found_upload:
                logger.info(f"✅ Registro encontrado: {found_upload.original_filename}")
                
                # Teste de atualização
                found_upload.status = "processing"
                found_upload.started_at = datetime.now()
                session.commit()
                
                logger.info("✅ Status atualizado para 'processing'")
                
                # Teste de remoção
                session.delete(found_upload)
                session.commit()
                
                logger.info("✅ Registro de teste removido")
            else:
                logger.warning("⚠️ Registro não encontrado após inserção")
        
        logger.info("✅ Todos os testes de operação passaram!")
        
    except Exception as e:
        logger.error(f"❌ Erro nos testes: {e}")
        return False
    
    return True


def main():
    """Função principal."""
    logger.info("=== Setup da Tabela Upload Status ===")
    
    # Cria a tabela
    if not create_upload_status_table():
        sys.exit(1)
    
    # Executa testes se solicitado
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logger.info("\n=== Executando Testes ===")
        if not test_upload_status_operations():
            sys.exit(1)
    
    logger.info("\n🎉 Setup concluído com sucesso!")


if __name__ == "__main__":
    main() 