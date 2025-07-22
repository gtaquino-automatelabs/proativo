#!/usr/bin/env python3
"""
Script para criação da tabela PMM_2 no banco de dados.

Este script cria a tabela pmm_2 com todas as constraints, índices e relacionamentos
necessários para armazenar os dados do Plano de Manutenção Maestro importados do SAP.
"""

import asyncio
import logging
from pathlib import Path
import sys

# Adiciona o diretório raiz do projeto ao Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.database.connection import get_engine, Base
from src.database.models import PMM_2, Equipment, Maintenance
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


async def create_pmm_2_table():
    """Cria a tabela PMM_2 no banco de dados."""
    
    try:
        logger.info("Iniciando criação da tabela PMM_2...")
        
        # Obtém o engine do banco
        engine = get_engine()
        
        # Cria todas as tabelas definidas nos modelos
        async with engine.begin() as conn:
            # Cria apenas a tabela PMM_2 se não existir
            await conn.run_sync(Base.metadata.create_all, tables=[PMM_2.__table__])
            
            logger.info("Tabela PMM_2 criada com sucesso!")
            
            # Verifica se a tabela foi criada
            result = await conn.execute(
                "SELECT tablename FROM pg_tables WHERE tablename = 'pmm_2'"
            )
            
            if result.rowcount > 0:
                logger.info("✓ Tabela pmm_2 confirmada no banco de dados")
            else:
                logger.error("✗ Erro: Tabela pmm_2 não foi encontrada após criação")
                return False
                
        await engine.dispose()
        
        logger.info("Criação da tabela PMM_2 concluída com sucesso!")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao criar tabela PMM_2: {e}")
        return False


async def verify_table_structure():
    """Verifica a estrutura da tabela PMM_2."""
    
    try:
        logger.info("Verificando estrutura da tabela PMM_2...")
        
        engine = get_engine()
        
        async with engine.begin() as conn:
            # Verifica colunas
            result = await conn.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'pmm_2' 
                ORDER BY ordinal_position
            """)
            
            columns = result.fetchall()
            
            if columns:
                logger.info(f"Tabela PMM_2 possui {len(columns)} colunas:")
                for col in columns:
                    logger.info(f"  - {col[0]}: {col[1]} (nullable: {col[2]})")
            else:
                logger.warning("Nenhuma coluna encontrada na tabela PMM_2")
                
            # Verifica índices
            result = await conn.execute("""
                SELECT indexname, indexdef
                FROM pg_indexes 
                WHERE tablename = 'pmm_2'
                ORDER BY indexname
            """)
            
            indexes = result.fetchall()
            
            if indexes:
                logger.info(f"Tabela PMM_2 possui {len(indexes)} índices:")
                for idx in indexes:
                    logger.info(f"  - {idx[0]}")
            else:
                logger.warning("Nenhum índice encontrado na tabela PMM_2")
                
            # Verifica constraints
            result = await conn.execute("""
                SELECT conname, contype, consrc
                FROM pg_constraint 
                WHERE conrelid = 'pmm_2'::regclass
                ORDER BY conname
            """)
            
            constraints = result.fetchall()
            
            if constraints:
                logger.info(f"Tabela PMM_2 possui {len(constraints)} constraints:")
                for cons in constraints:
                    logger.info(f"  - {cons[0]} ({cons[1]})")
            else:
                logger.warning("Nenhuma constraint encontrada na tabela PMM_2")
                
        await engine.dispose()
        
        logger.info("Verificação da estrutura da tabela PMM_2 concluída!")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao verificar estrutura da tabela PMM_2: {e}")
        return False


async def drop_pmm_2_table():
    """Remove a tabela PMM_2 do banco de dados."""
    
    try:
        logger.info("Removendo tabela PMM_2...")
        
        engine = get_engine()
        
        async with engine.begin() as conn:
            await conn.execute("DROP TABLE IF EXISTS pmm_2 CASCADE")
            logger.info("Tabela PMM_2 removida com sucesso!")
            
        await engine.dispose()
        
        return True
        
    except Exception as e:
        logger.error(f"Erro ao remover tabela PMM_2: {e}")
        return False


async def main():
    """Função principal do script."""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Gerenciamento da tabela PMM_2")
    parser.add_argument(
        "--action", 
        choices=["create", "verify", "drop", "recreate"],
        default="create",
        help="Ação a ser executada"
    )
    parser.add_argument(
        "--force", 
        action="store_true",
        help="Força a operação sem confirmação"
    )
    
    args = parser.parse_args()
    
    if args.action == "create":
        success = await create_pmm_2_table()
        if success:
            await verify_table_structure()
            
    elif args.action == "verify":
        await verify_table_structure()
        
    elif args.action == "drop":
        if not args.force:
            confirm = input("Tem certeza que deseja remover a tabela PMM_2? (s/N): ")
            if confirm.lower() != 's':
                logger.info("Operação cancelada.")
                return
                
        await drop_pmm_2_table()
        
    elif args.action == "recreate":
        if not args.force:
            confirm = input("Tem certeza que deseja recriar a tabela PMM_2? (s/N): ")
            if confirm.lower() != 's':
                logger.info("Operação cancelada.")
                return
                
        logger.info("Recriando tabela PMM_2...")
        await drop_pmm_2_table()
        success = await create_pmm_2_table()
        if success:
            await verify_table_structure()
    
    logger.info("Script concluído!")


if __name__ == "__main__":
    asyncio.run(main()) 