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


async def check_database_status():
    """
    Verifica o status detalhado do banco de dados.
    
    Returns:
        dict: Status detalhado de cada tabela
    """
    try:
        print("🔍 Verificando status detalhado do banco de dados...")
        
        # Inicializa conexão
        await init_database()
        
        async with db_connection.get_session() as session:
            repo_manager = RepositoryManager(session)
            
            # Verifica cada tabela individualmente
            status = {
                'equipment': {'count': 0, 'needs_population': True, 'table_exists': False},
                'maintenance': {'count': 0, 'needs_population': True, 'table_exists': False},
                'failure': {'count': 0, 'needs_population': True, 'table_exists': False},
                'sap_location': {'count': 0, 'needs_population': True, 'table_exists': False},
                'pmm_2': {'count': 0, 'needs_population': True, 'table_exists': False}
            }
            
            # Equipamentos
            try:
                equipment_count = await repo_manager.equipment.count()
                status['equipment']['count'] = equipment_count
                status['equipment']['needs_population'] = equipment_count == 0
                status['equipment']['table_exists'] = True
            except Exception as e:
                print(f"   ⚠️  Erro ao verificar equipamentos: {e}")
                status['equipment']['table_exists'] = False
            
            # Manutenções
            try:
                maintenance_count = await repo_manager.maintenance.count()
                status['maintenance']['count'] = maintenance_count
                status['maintenance']['needs_population'] = maintenance_count == 0
                status['maintenance']['table_exists'] = True
            except Exception as e:
                print(f"   ⚠️  Erro ao verificar manutenções: {e}")
                status['maintenance']['table_exists'] = False
            
            # Falhas
            try:
                failure_count = await repo_manager.failures.count()
                status['failure']['count'] = failure_count
                status['failure']['needs_population'] = failure_count == 0
                status['failure']['table_exists'] = True
            except Exception as e:
                print(f"   ⚠️  Erro ao verificar falhas: {e}")
                status['failure']['table_exists'] = False
            
            # Localidades SAP
            try:
                sap_location_count = await repo_manager.sap_location.count()
                status['sap_location']['count'] = sap_location_count
                status['sap_location']['needs_population'] = sap_location_count == 0
                status['sap_location']['table_exists'] = True
            except Exception as e:
                print(f"   ⚠️  Erro ao verificar localidades SAP: {e}")
                status['sap_location']['table_exists'] = False
            
            # PMM_2
            try:
                pmm_2_count = await repo_manager.pmm_2.count()
                status['pmm_2']['count'] = pmm_2_count
                status['pmm_2']['needs_population'] = pmm_2_count == 0
                status['pmm_2']['table_exists'] = True
            except Exception as e:
                print(f"   ⚠️  Erro ao verificar PMM_2: {e}")
                status['pmm_2']['table_exists'] = False
            
            # Exibe status detalhado
            total_records = sum(table['count'] for table in status.values())
            
            print(f"📊 Status detalhado do banco:")
            print(f"   Equipamentos: {status['equipment']['count']} {'❌' if status['equipment']['needs_population'] else '✅'}")
            print(f"   Manutenções: {status['maintenance']['count']} {'❌' if status['maintenance']['needs_population'] else '✅'}")
            print(f"   Falhas: {status['failure']['count']} {'❌' if status['failure']['needs_population'] else '✅'}")
            print(f"   Localidades SAP: {status['sap_location']['count']} {'❌' if status['sap_location']['needs_population'] else '✅'}")
            print(f"   Planos PMM_2: {status['pmm_2']['count']} {'❌' if status['pmm_2']['needs_population'] else '✅'}")
            print(f"   Total: {total_records}")
            
            # Identifica tabelas que precisam ser populadas
            empty_tables = [table for table, info in status.items() if info['needs_population'] and info['table_exists']]
            missing_tables = [table for table, info in status.items() if not info['table_exists']]
            
            if empty_tables:
                print(f"📋 Tabelas que precisam ser populadas: {', '.join(empty_tables)}")
            
            if missing_tables:
                print(f"🔧 Tabelas que não existem: {', '.join(missing_tables)}")
            
            return status
                
    except Exception as e:
        print(f"❌ Erro ao verificar banco: {e}")
        # Em caso de erro, assume que tudo precisa ser populado
        return {
            'equipment': {'count': 0, 'needs_population': True, 'table_exists': False},
            'maintenance': {'count': 0, 'needs_population': True, 'table_exists': False},
            'failure': {'count': 0, 'needs_population': True, 'table_exists': False},
            'sap_location': {'count': 0, 'needs_population': True, 'table_exists': False},
            'pmm_2': {'count': 0, 'needs_population': True, 'table_exists': False}
        }


async def check_database_empty():
    """
    Verifica se o banco está vazio (compatibilidade com versão anterior).
    
    Returns:
        bool: True se vazio, False se já tem dados
    """
    status = await check_database_status()
    total_records = sum(table['count'] for table in status.values())
    
    is_empty = total_records == 0
    
    if is_empty:
        print("💡 Banco está vazio - população necessária")
        return True
    else:
        print("✅ Banco já contém dados - população não necessária")
        return False


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