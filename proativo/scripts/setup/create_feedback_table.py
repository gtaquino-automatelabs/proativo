#!/usr/bin/env python3
"""
Script para criar tabela user_feedback no banco de dados PROAtivo.

Este script cria especificamente a tabela de feedback que pode ter sido
perdida durante migrações anteriores.
"""

import asyncio
import sys
from pathlib import Path

# Adiciona o diretório raiz ao Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.database.connection import init_database, close_database
from src.database.models import Base, UserFeedback
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def create_feedback_table():
    """Cria apenas a tabela user_feedback."""
    try:
        print("🔄 Inicializando conexão com banco de dados...")
        await init_database()
        
        print("🔄 Criando tabela user_feedback...")
        
        # Importa o engine da conexão
        from src.database.connection import db_connection
        
        async with db_connection.engine.begin() as conn:
            # Cria apenas a tabela UserFeedback
            await conn.run_sync(UserFeedback.metadata.create_all, checkfirst=True)
        
        print("✅ Tabela user_feedback criada com sucesso!")
        
        # Verifica se a tabela foi criada
        async with db_connection.engine.begin() as conn:
            result = await conn.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'user_feedback'"
            )
            count = result.scalar()
            
            if count > 0:
                print("✅ Tabela user_feedback confirmada no banco de dados!")
            else:
                print("❌ Erro: Tabela user_feedback não foi encontrada!")
        
    except Exception as e:
        logger.error(f"Erro ao criar tabela user_feedback: {str(e)}")
        print(f"❌ Erro: {str(e)}")
        return False
    
    finally:
        await close_database()
    
    return True


async def check_feedback_table():
    """Verifica se a tabela user_feedback existe."""
    try:
        await init_database()
        
        from src.database.connection import db_connection
        
        async with db_connection.engine.begin() as conn:
            result = await conn.execute(
                """
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'user_feedback'
                ORDER BY ordinal_position
                """
            )
            columns = result.fetchall()
            
            if columns:
                print("✅ Tabela user_feedback encontrada com as seguintes colunas:")
                for col in columns:
                    print(f"   - {col[0]}: {col[1]}")
            else:
                print("❌ Tabela user_feedback não encontrada!")
                return False
    
    except Exception as e:
        print(f"❌ Erro ao verificar tabela: {str(e)}")
        return False
    
    finally:
        await close_database()
    
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Gerenciar tabela user_feedback")
    parser.add_argument(
        "--check", 
        action="store_true", 
        help="Apenas verifica se a tabela existe"
    )
    
    args = parser.parse_args()
    
    if args.check:
        print("🔍 Verificando tabela user_feedback...")
        asyncio.run(check_feedback_table())
    else:
        print("🚀 Criando tabela user_feedback...")
        success = asyncio.run(create_feedback_table())
        if success:
            print("🎉 Processo concluído com sucesso!")
        else:
            print("💥 Processo falhou!")
            sys.exit(1) 