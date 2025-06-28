#!/usr/bin/env python3
"""
Script para limpar equipamentos duplicados no banco de dados.
Remove registros duplicados mantendo apenas o mais recente de cada código.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, List
from collections import defaultdict

# Configurar paths
current_dir = Path(__file__).parent.parent.parent  # proativo/
sys.path.insert(0, str(current_dir))
os.environ['PYTHONPATH'] = str(current_dir)

from src.database.connection import db_connection
from src.database.repositories import RepositoryManager


async def clean_duplicate_equipment():
    """Remove equipamentos duplicados do banco de dados."""
    print("INICIANDO LIMPEZA DE EQUIPAMENTOS DUPLICADOS...")
    print("=" * 60)
    
    try:
        # Inicializar conexão com banco de dados
        print("Conectando ao banco de dados...")
        await db_connection.initialize()
        
        async with db_connection.get_session() as session:
            repo_manager = RepositoryManager(session)
            
            # 1. Buscar todos os equipamentos
            print("\n1. Buscando todos os equipamentos...")
            all_equipment = await repo_manager.equipment.list_all(limit=10000)
            print(f"   Encontrados {len(all_equipment)} equipamentos")
            
            # 2. Agrupar por código
            print("\n2. Agrupando equipamentos por código...")
            equipment_by_code = defaultdict(list)
            
            for equipment in all_equipment:
                equipment_by_code[equipment.code].append(equipment)
            
            # 3. Identificar duplicatas
            print("\n3. Identificando duplicatas...")
            duplicates_found = 0
            equipments_to_delete = []
            
            for code, equipments in equipment_by_code.items():
                if len(equipments) > 1:
                    duplicates_found += 1
                    print(f"   Código {code}: {len(equipments)} registros duplicados")
                    
                    # Ordena por data de criação (mais recente primeiro)
                    equipments.sort(key=lambda x: x.created_at, reverse=True)
                    
                    # Manter o primeiro (mais recente), marcar outros para deletar
                    keep_equipment = equipments[0]
                    delete_equipments = equipments[1:]
                    
                    print(f"     ✅ Mantendo: ID {keep_equipment.id} (criado em {keep_equipment.created_at})")
                    
                    for eq in delete_equipments:
                        equipments_to_delete.append(eq)
                        print(f"     ❌ Removendo: ID {eq.id} (criado em {eq.created_at})")
            
            print(f"\nResumo:")
            print(f"   Códigos únicos: {len(equipment_by_code)}")
            print(f"   Códigos com duplicatas: {duplicates_found}")
            print(f"   Equipamentos para remover: {len(equipments_to_delete)}")
            
            # 4. Confirmar limpeza
            if equipments_to_delete:
                print(f"\n4. Removendo {len(equipments_to_delete)} equipamentos duplicados...")
                removed_count = 0
                
                for equipment in equipments_to_delete:
                    try:
                        success = await repo_manager.equipment.delete(equipment.id)
                        if success:
                            removed_count += 1
                            print(f"   ✅ Removido equipamento ID {equipment.id} (código: {equipment.code})")
                        else:
                            print(f"   ❌ Falha ao remover equipamento ID {equipment.id}")
                    except Exception as e:
                        print(f"   ❌ Erro ao remover equipamento ID {equipment.id}: {e}")
                
                # Commit das mudanças
                await session.commit()
                
                print(f"\n✅ Limpeza concluída!")
                print(f"   Equipamentos removidos: {removed_count}")
                print(f"   Equipamentos restantes: {len(all_equipment) - removed_count}")
                
                return True
            else:
                print("\n✅ Nenhum equipamento duplicado encontrado!")
                return True
                
    except Exception as e:
        print(f"\n❌ Erro durante a limpeza: {e}")
        import traceback
        traceback.print_exc()
        return False


async def verify_cleanup():
    """Verifica se a limpeza foi bem-sucedida."""
    print("\n" + "=" * 60)
    print("VERIFICANDO RESULTADO DA LIMPEZA...")
    print("=" * 60)
    
    try:
        await db_connection.initialize()
        
        async with db_connection.get_session() as session:
            repo_manager = RepositoryManager(session)
            
            # Buscar todos os equipamentos novamente
            all_equipment = await repo_manager.equipment.list_all(limit=10000)
            
            # Agrupar por código
            equipment_by_code = defaultdict(list)
            for equipment in all_equipment:
                equipment_by_code[equipment.code].append(equipment)
            
            # Verificar duplicatas
            remaining_duplicates = 0
            for code, equipments in equipment_by_code.items():
                if len(equipments) > 1:
                    remaining_duplicates += 1
                    print(f"   ⚠️  Ainda há duplicatas para código {code}: {len(equipments)} registros")
            
            print(f"\nResultado final:")
            print(f"   Total de equipamentos: {len(all_equipment)}")
            print(f"   Códigos únicos: {len(equipment_by_code)}")
            print(f"   Duplicatas restantes: {remaining_duplicates}")
            
            if remaining_duplicates == 0:
                print("   ✅ Todos os equipamentos têm códigos únicos!")
                return True
            else:
                print("   ❌ Ainda existem duplicatas no banco!")
                return False
                
    except Exception as e:
        print(f"❌ Erro na verificação: {e}")
        return False


def main():
    """Função principal."""
    print("SCRIPT DE LIMPEZA DE EQUIPAMENTOS DUPLICADOS")
    print("=" * 60)
    
    try:
        # Executar limpeza
        success = asyncio.run(clean_duplicate_equipment())
        
        if success:
            # Verificar resultado
            verification = asyncio.run(verify_cleanup())
            
            if verification:
                print("\n🎉 LIMPEZA CONCLUÍDA COM SUCESSO!")
                return 0
            else:
                print("\n⚠️  LIMPEZA PARCIAL - VERIFICAR LOGS")
                return 1
        else:
            print("\n❌ FALHA NA LIMPEZA")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️  Script interrompido pelo usuário")
        return 1
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 