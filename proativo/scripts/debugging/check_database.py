#!/usr/bin/env python3
"""
Script para verificar se o banco de dados está populado.
"""

import asyncio
import sys
import os
from pathlib import Path

# Configurar paths
current_dir = Path(__file__).parent
project_dir = current_dir.parent
src_dir = project_dir / "src"
sys.path.insert(0, str(project_dir))
os.environ['PYTHONPATH'] = str(src_dir)

async def check_database():
    """Verifica o conteúdo do banco de dados."""
    print("=== VERIFICAÇÃO DO BANCO DE DADOS ===")
    
    try:
        from src.database.connection import db_connection
        from src.database.repositories import RepositoryManager
        
        # Inicializar conexão
        await db_connection.initialize()
        
        # Criar sessão
        async with db_connection.get_session() as session:
            repository_manager = RepositoryManager(session)
            
            # Contar equipamentos
            equipments = await repository_manager.equipment.list_all()
            print(f"Equipamentos no banco: {len(equipments)}")
            
            if equipments:
                print("\nPrimeiros 5 equipamentos:")
                for eq in equipments[:5]:
                    print(f"  - {eq.code}: {eq.name} (criticidade: {eq.criticality})")
            
            # Contar manutenções
            maintenances = await repository_manager.maintenance.list_all()
            print(f"\nManutenções no banco: {len(maintenances)}")
            
            if maintenances:
                print("\nPrimeiras 3 manutenções:")
                for maint in maintenances[:3]:
                    print(f"  - {maint.title}: {maint.maintenance_type}")
            
        print("\n✅ Verificação concluída!")
        return True
        
    except Exception as e:
        print(f"ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(check_database())
    sys.exit(0 if result else 1) 