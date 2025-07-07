#!/usr/bin/env python3
"""
MASTER SCRIPT - Configuração completa automática do banco PROAtivo.
Orquestra: criação de tabelas + população de dados + verificação final.
"""

import asyncio
import sys
import os
from pathlib import Path

# Configurar paths
current_dir = Path(__file__).parent
project_dir = current_dir.parent.parent
sys.path.insert(0, str(project_dir))
os.environ['PYTHONPATH'] = str(project_dir)

from src.database.connection import db_connection, init_database


async def run_script(script_name, description):
    """Executa um script e retorna sucesso/falha."""
    print(f"\n🔄 {description}")
    print("=" * 50)
    
    script_path = current_dir / script_name
    
    if not script_path.exists():
        print(f"❌ Script não encontrado: {script_name}")
        return False
    
    try:
        # Importa e executa o script
        if script_name == "create_tables.py":
            from scripts.setup.create_tables import main as create_main
            success = await create_main()
        elif script_name == "populate_database.py":
            from scripts.setup.populate_database import main as populate_main
            success = await populate_main()
        elif script_name == "check_database.py":
            from scripts.setup.check_database import check_database_empty
            success = not await check_database_empty()  # Inverte lógica: True se tem dados (sucesso)
        else:
            print(f"❌ Script não reconhecido: {script_name}")
            return False
        
        if success:
            print(f"✅ {description} - CONCLUÍDO")
            return True
        else:
            print(f"❌ {description} - FALHOU")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao executar {script_name}: {e}")
        return False


async def check_initial_status():
    """Verifica se o banco está vazio e precisa de configuração."""
    print("🔍 VERIFICAÇÃO INICIAL")
    print("=" * 50)
    
    try:
        await init_database()
        
        async with db_connection.get_session() as session:
            from src.database.repositories import RepositoryManager
            repo_manager = RepositoryManager(session)
            
            # Conta registros existentes
            try:
                equipment_count = await repo_manager.equipment.count()
                maintenance_count = await repo_manager.maintenance.count()
                failure_count = await repo_manager.failures.count()
                
                total_records = equipment_count + maintenance_count + failure_count
                
                print(f"📊 Status atual do banco:")
                print(f"   Equipamentos: {equipment_count}")
                print(f"   Manutenções: {maintenance_count}")
                print(f"   Falhas: {failure_count}")
                print(f"   Total: {total_records}")
                
                if total_records == 0:
                    print("💡 Banco vazio - configuração completa necessária")
                    return True, "empty"
                else:
                    print("✅ Banco já contém dados")
                    return False, "populated"
                    
            except Exception:
                print("⚠️  Algumas tabelas não existem - criação necessária")
                return True, "missing_tables"
            
    except Exception as e:
        print(f"❌ Erro na verificação inicial: {e}")
        return True, "error"


async def main():
    """Função principal - configura banco completo."""
    print("🚀 PROATIVO - CONFIGURAÇÃO AUTOMÁTICA COMPLETA")
    print("=" * 60)
    print("Este script irá:")
    print("   1️⃣  Verificar status atual")
    print("   2️⃣  Criar tabelas (se necessário)")
    print("   3️⃣  Popular dados (se necessário)")
    print("   4️⃣  Verificar resultado final")
    print("=" * 60)
    
    try:
        # ETAPA 1: Verificação inicial
        needs_setup, status = await check_initial_status()
        
        if not needs_setup and status == "populated":
            print("\n🎉 BANCO JÁ ESTÁ CONFIGURADO!")
            print("   Nenhuma ação necessária.")
            return True
        
        # ETAPA 2: Criar tabelas
        print(f"\n📋 Status: {status}")
        if status in ["empty", "missing_tables", "error"]:
            success = await run_script("create_tables.py", "CRIANDO TABELAS")
            if not success:
                print("\n❌ FALHA na criação de tabelas - abortando")
                return False
        
        # ETAPA 3: Popular dados
        if status in ["empty", "missing_tables"]:
            success = await run_script("populate_database.py", "POPULANDO DADOS")
            if not success:
                print("\n❌ FALHA na população - abortando")
                return False
        
        # ETAPA 4: Verificação final
        success = await run_script("check_database.py", "VERIFICAÇÃO FINAL")
        
        if success:
            print("\n" + "=" * 60)
            print("🎉 CONFIGURAÇÃO COMPLETA FINALIZADA COM SUCESSO!")
            print("=" * 60)
            print("✅ Tabelas criadas")
            print("✅ Dados populados")
            print("✅ Sistema pronto para uso")
            print("=" * 60)
            return True
        else:
            print("\n❌ VERIFICAÇÃO FINAL FALHOU")
            return False
            
    except Exception as e:
        print(f"\n❌ ERRO INESPERADO: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("⚡ Iniciando configuração automática...")
    success = asyncio.run(main())
    
    if success:
        print("\n✨ Sistema PROAtivo pronto para uso!")
        sys.exit(0)
    else:
        print("\n💥 Configuração falhou!")
        sys.exit(1) 