#!/usr/bin/env python3
"""
Script para verificar se o banco de dados está vazio e precisa ser populado.
Retorna exit code 0 se estiver vazio, 1 se já tiver dados.
"""

import asyncio
import os
import sys
from pathlib import Path

# Configurar paths
current_dir = Path(__file__).parent
project_dir = current_dir.parent.parent
sys.path.insert(0, str(project_dir))
os.environ['PYTHONPATH'] = str(project_dir)

from src.database.connection import db_connection, init_database
from src.database.repositories import RepositoryManager


async def check_database_empty():
    """
    Verifica se o banco está vazio.
    
    Returns:
        bool: True se vazio, False se já tem dados
    """
    try:
        print("🔍 Verificando se banco de dados está vazio...")
        
        # Inicializa conexão
        await init_database()
        
        async with db_connection.get_session() as session:
            repo_manager = RepositoryManager(session)
            
            # Conta registros em tabelas principais
            equipment_count = await repo_manager.equipment.count()
            maintenance_count = await repo_manager.maintenance.count()
            history_count = await repo_manager.data_history.count()
            
            total_records = equipment_count + maintenance_count + history_count
            
            print(f"📊 Registros encontrados:")
            print(f"   Equipamentos: {equipment_count}")
            print(f"   Manutenções: {maintenance_count}")
            print(f"   Histórico: {history_count}")
            print(f"   Total: {total_records}")
            
            is_empty = total_records == 0
            
            if is_empty:
                print("💡 Banco está vazio - população necessária")
                return True
            else:
                print("✅ Banco já contém dados - população não necessária")
                return False
                
    except Exception as e:
        print(f"❌ Erro ao verificar banco: {e}")
        # Em caso de erro, assume que precisa popular
        return True


async def main():
    """Função principal."""
    is_empty = await check_database_empty()
    
    if is_empty:
        print("🚀 NECESSÁRIA POPULAÇÃO DO BANCO")
        sys.exit(0)  # Exit code 0 = precisa popular
    else:
        print("⏭️  POPULAÇÃO DESNECESSÁRIA")
        sys.exit(1)  # Exit code 1 = não precisa popular


if __name__ == "__main__":
    asyncio.run(main()) 