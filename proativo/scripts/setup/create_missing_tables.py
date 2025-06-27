#!/usr/bin/env python3

"""
Script para criar tabelas que podem estar faltando no banco de dados PROAtivo.

Este script verifica e cria tabelas que são referenciadas pelo sistema mas
podem não ter sido criadas durante a inicialização.
"""

import asyncio
import sys
from pathlib import Path

# Adiciona o diretório raiz ao Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.database.connection import init_database, close_database, get_db_session
from src.utils.logger import get_logger
from sqlalchemy import text

logger = get_logger(__name__)


async def create_failures_table():
    """Cria a tabela failures se ela não existir."""
    create_failures_sql = """
    CREATE TABLE IF NOT EXISTS failures (
        id SERIAL PRIMARY KEY,
        equipment_id VARCHAR(50) NOT NULL,
        failure_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        description TEXT,
        severity VARCHAR(20) DEFAULT 'medium',
        resolution_time INTEGER, -- em minutos
        cost DECIMAL(10,2),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    create_index_sql = """
    CREATE INDEX IF NOT EXISTS idx_failures_equipment_id ON failures(equipment_id);
    CREATE INDEX IF NOT EXISTS idx_failures_date ON failures(failure_date);
    CREATE INDEX IF NOT EXISTS idx_failures_severity ON failures(severity);
    """
    
    async with get_db_session() as session:
        try:
            # Criar tabela
            await session.execute(text(create_failures_sql))
            logger.info("✅ Tabela 'failures' criada/verificada com sucesso")
            
            # Criar índices
            await session.execute(text(create_index_sql))
            logger.info("✅ Índices da tabela 'failures' criados com sucesso")
            
            await session.commit()
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar tabela 'failures': {e}")
            await session.rollback()
            raise


async def create_user_feedback_table():
    """Cria a tabela user_feedback se ela não existir."""
    create_feedback_sql = """
    CREATE TABLE IF NOT EXISTS user_feedback (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        session_id UUID NOT NULL,
        message_id UUID NOT NULL UNIQUE,
        rating INTEGER CHECK (rating >= 1 AND rating <= 5),
        helpful BOOLEAN NOT NULL,
        comment TEXT,
        feedback_category VARCHAR(50),
        improvement_priority VARCHAR(20) DEFAULT 'medium',
        is_processed BOOLEAN DEFAULT false,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    create_feedback_indexes = """
    CREATE INDEX IF NOT EXISTS idx_user_feedback_session_id ON user_feedback(session_id);
    CREATE INDEX IF NOT EXISTS idx_user_feedback_message_id ON user_feedback(message_id);
    CREATE INDEX IF NOT EXISTS idx_user_feedback_helpful ON user_feedback(helpful);
    CREATE INDEX IF NOT EXISTS idx_user_feedback_created_at ON user_feedback(created_at);
    """
    
    async with get_db_session() as session:
        try:
            # Criar tabela
            await session.execute(text(create_feedback_sql))
            logger.info("✅ Tabela 'user_feedback' criada/verificada com sucesso")
            
            # Criar índices
            await session.execute(text(create_feedback_indexes))
            logger.info("✅ Índices da tabela 'user_feedback' criados com sucesso")
            
            await session.commit()
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar tabela 'user_feedback': {e}")
            await session.rollback()
            raise


async def insert_sample_failures():
    """Insere alguns dados de exemplo na tabela failures."""
    sample_failures = """
    INSERT INTO failures (equipment_id, failure_date, description, severity, resolution_time, cost)
    VALUES 
        ('TR-001', '2024-01-15 10:30:00', 'Falha no transformador principal', 'high', 240, 15000.00),
        ('TR-002', '2024-02-20 14:15:00', 'Superaquecimento detectado', 'medium', 120, 5000.00),
        ('TR-003', '2024-03-10 08:45:00', 'Vazamento de óleo isolante', 'high', 360, 25000.00)
    ON CONFLICT DO NOTHING;
    """
    
    async with get_db_session() as session:
        try:
            result = await session.execute(text(sample_failures))
            await session.commit()
            logger.info(f"✅ {result.rowcount} registros de falhas inseridos como exemplo")
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao inserir dados de exemplo: {e}")
            await session.rollback()


async def verify_tables():
    """Verifica se todas as tabelas foram criadas corretamente."""
    check_tables_sql = """
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name IN ('failures', 'user_feedback', 'equipments', 'maintenances');
    """
    
    async with get_db_session() as session:
        try:
            result = await session.execute(text(check_tables_sql))
            tables = [row[0] for row in result.fetchall()]
            
            print("\n📊 Status das tabelas:")
            expected_tables = ['failures', 'user_feedback', 'equipments', 'maintenances']
            
            for table in expected_tables:
                if table in tables:
                    print(f"  ✅ {table}")
                else:
                    print(f"  ❌ {table} (ausente)")
            
            return len(tables) == len(expected_tables)
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar tabelas: {e}")
            return False


async def main():
    """Função principal do script."""
    try:
        print("🔄 Inicializando conexão com banco de dados...")
        await init_database()
        
        print("🔄 Criando tabelas necessárias...")
        
        # Criar tabela failures
        await create_failures_table()
        
        # Criar tabela user_feedback
        await create_user_feedback_table()
        
        # Inserir dados de exemplo
        await insert_sample_failures()
        
        # Verificar se tudo foi criado
        success = await verify_tables()
        
        if success:
            print("\n✅ Todas as tabelas foram criadas com sucesso!")
        else:
            print("\n⚠️ Algumas tabelas ainda estão ausentes.")
        
    except Exception as e:
        logger.error(f"❌ Erro na execução: {e}")
        sys.exit(1)
        
    finally:
        await close_database()
        print("🔄 Conexão com banco encerrada.")


if __name__ == "__main__":
    asyncio.run(main()) 