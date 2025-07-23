# File: scripts/setup/setup_complete_database.py

import asyncio
import sys
import os
from pathlib import Path

# Configurar paths (already present in your file)
current_dir = Path(__file__).parent
project_dir = current_dir.parent.parent
sys.path.insert(0, str(project_dir))
os.environ['PYTHONPATH'] = str(project_dir)

from src.database.connection import db_connection, init_database
# Import check_database_status directly to use it multiple times
from scripts.setup.check_database import check_database_status


async def run_script(script_name, description):
    """Executa um script e retorna sucesso/falha. (Function remains unchanged)"""
    print(f"\n🔄 {description}")
    print("=" * 50)
    
    script_path = current_dir / script_name
    
    if not script_path.exists():
        print(f"❌ Script não encontrado: {script_path}")
        return False
    
    try:
        # Importa e executa o script
        if script_name == "create_tables.py":
            from scripts.setup.create_tables import main as create_main
            success = await create_main()
        elif script_name == "populate_database.py":
            from scripts.setup.populate_database import main as populate_main
            success = await populate_main()
        elif script_name == "import_localidades_sap.py":
            from scripts.setup.import_localidades_sap import main as import_main
            success = await import_main()
        elif script_name == "correlate_equipment_locations.py":
            from scripts.setup.correlate_equipment_locations import main as correlate_main
            success = await correlate_main()
        elif script_name == "populate_pmm_2.py":
            from scripts.setup.populate_pmm_2 import main as populate_pmm_2_main
            success = await populate_pmm_2_main()
        elif script_name == "check_database.py":
            from scripts.setup.check_database import check_database_empty
            success = not await check_database_empty()
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


async def check_initial_status_wrapper(): # Renomeado para evitar conflito de nome se check_database_status for importado diretamente
    """Verifica o status detalhado do banco e determina que ações são necessárias. (Function remains unchanged)"""
    print("🔍 VERIFICAÇÃO INICIAL")
    print("=" * 50)
    
    try:
        await init_database()
        
        status = await check_database_status()
        
        missing_tables = [table for table, info in status.items() if not info['table_exists']]
        empty_tables = [table for table, info in status.items() if info['needs_population'] and info['table_exists']]
        total_records = sum(table['count'] for table in status.values())
        
        if missing_tables:
            print("🔧 Algumas tabelas não existem - criação necessária")
            return status, "Tabelas faltando"
        elif total_records == 0:
            print("💡 Banco vazio - configuração completa necessária")
            return status, "Vazio"
        elif empty_tables:
            print(f"📋 Algumas tabelas precisam ser populadas: {', '.join(empty_tables)}")
            return status, "População parcial"
        else:
            print("✅ Banco já está completamente populado")
            return status, "Populado"
            
    except Exception as e:
        print(f"❌ Erro na verificação inicial: {e}")
        error_status = {
            'equipment': {'count': 0, 'needs_population': True, 'table_exists': False},
            'maintenance': {'count': 0, 'needs_population': True, 'table_exists': False},
            'failure': {'count': 0, 'needs_population': True, 'table_exists': False},
            'sap_location': {'count': 0, 'needs_population': True, 'table_exists': False},
            'pmm_2': {'count': 0, 'needs_population': True, 'table_exists': False}
        }
        return error_status, "error"


def determine_required_scripts(status, status_type):
    """
    Determines which scripts should be executed based on table status. (Function remains unchanged)
    
    Args:
        status: Dict with detailed table status
        status_type: Type of status ("empty", "missing_tables", "partial_population", "populated")
    
    Returns:
        Dict with scripts that should be executed
    """
    scripts_to_run = {
        'create_tables': False,
        'populate_database': False, # This will now encompass deriving equipments
        'import_localidades_sap': False,
        'correlate_equipment_locations': False, # This step is now effectively merged into populate_database
        'populate_pmm_2': False
    }
    
    if status_type in ["Vazio", "Tabelas faltando", "error"]: # Updated status_type names
        # If empty or tables missing, run everything in correct order
        scripts_to_run['create_tables'] = True
        scripts_to_run['import_localidades_sap'] = True # Need SAP locations first
        scripts_to_run['populate_pmm_2'] = True # Need PMM_2 data first
        scripts_to_run['populate_database'] = True # This now derives equipment and populates other data
    
    elif status_type == "População parcial": # Updated status_type name
        # If partial, execute only necessary parts
        if not status['equipment']['table_exists'] or not status['maintenance']['table_exists'] or not status['failure']['table_exists'] or not status['sap_location']['table_exists'] or not status['pmm_2']['table_exists']:
            scripts_to_run['create_tables'] = True # Ensure tables exist if any are missing

        if status['sap_location']['needs_population']:
            scripts_to_run['import_localidades_sap'] = True
        
        if status['pmm_2']['needs_population']:
            scripts_to_run['populate_pmm_2'] = True
        
        # If equipments, maintenances, or failures need population, run populate_database.
        # This implicitly means SAP locations and PMM_2 should have been populated first.
        if (status['equipment']['needs_population'] or 
            status['maintenance']['needs_population'] or 
            status['failure']['needs_population']):
            scripts_to_run['populate_database'] = True
            
    return scripts_to_run


async def main():
    """Função principal - configura banco completo."""
    print("🚀 PROATIVO - CONFIGURAÇÃO AUTOMÁTICA INTELIGENTE")
    print("=" * 60)
    print("Este script irá:")
    print("   1️⃣  Verificar status detalhado de cada tabela")
    print("   2️⃣  Determinar scripts necessários automaticamente")
    print("   3️⃣  Criar tabelas (se necessário)")
    print("   4️⃣  Importar localidades SAP (se necessário)")
    print("   5️⃣  Popular dados PMM_2 (se necessário)")
    print("   6️⃣  Popular dados básicos (equipamentos, manutenções, falhas) a p partir de PMM_2 (se necessário)")
    print("   7️⃣  Verificar resultado final")
    print("=" * 60)
    print("✨ NOVO: Executa apenas os scripts necessários para cada tabela!")
    
    try:
        # ETAPA 1: Verificação inicial
        status, status_type = await check_initial_status_wrapper() # Updated function call
        
        if status_type == "Populado": # Updated status_type name
            print("\n🎉 BANCO JÁ ESTÁ COMPLETAMENTE CONFIGURADO!")
            print("   Nenhuma ação necessária.")
            return True
        
        # ETAPA 2: Determinar scripts necessários
        scripts_to_run = determine_required_scripts(status, status_type)
        
        print(f"\n📋 Status: {status_type}")
        print(f"📋 Scripts a executar:")
        for script, should_run in scripts_to_run.items():
            if should_run:
                print(f"   ✅ {script}")
            else:
                print(f"   ⏭️  {script} (não necessário)")
        
        # ETAPA 3: Criar tabelas (se necessário) - Must run first to ensure tables exist
        if scripts_to_run['create_tables']:
            success = await run_script("create_tables.py", "CRIANDO TABELAS")
            if not success:
                print("\n❌ FALHA na criação de tabelas - abortando")
                return False
        
        # ETAPA 4: Importar localidades SAP (MOVED HERE: needed before equipment population)
        if scripts_to_run['import_localidades_sap']:
            success = await run_script("import_localidades_sap.py", "IMPORTANDO LOCALIDADES SAP")
            if not success:
                print("\n⚠️  FALHA na importação de localidades SAP - continuando (mas pode afetar a vinculação de equipamentos)")
        
        # ETAPA 5: Popular dados PMM_2 (MOVED HERE: needed before equipment population)
        if scripts_to_run['populate_pmm_2']:
            success = await run_script("populate_pmm_2.py", "POPULANDO DADOS PMM_2")
            if not success:
                print("\n⚠️  FALHA na população de PMM_2 - continuando (mas pode afetar a derivação de equipamentos)")
            
            # --- NOVO PASSO CRÍTICO: RE-VALIDAR PMM_2 APÓS POPULAÇÃO ---
            print("\n🔍 Verificando status de PMM_2 após população...")
            pmm_2_status_after_populate = await check_database_status()
            if pmm_2_status_after_populate['pmm_2']['count'] == 0:
                print("❌ ERRO GRAVE: PMM_2 está vazio APÓS a população! Abortando.")
                return False
            print(f"✅ PMM_2 agora tem {pmm_2_status_after_populate['pmm_2']['count']} registros.")

        # ETAPA 6: Popular dados básicos (equipamentos, manutenções, falhas) 
        # This now includes equipment derivation from PMM_2 and relies on previous steps
        if scripts_to_run['populate_database']:
            success = await run_script("populate_database.py", "POPULANDO DADOS BÁSICOS (EQUIPAMENTOS, MANUTENÇÕES, FALHAS)")
            if not success:
                print("\n❌ FALHA na população básica - abortando")
                return False
        
        # ETAPA 7: Verificação final
        # Note: We now re-import check_database_empty here to avoid name conflicts with directly imported check_database_status
        from scripts.setup.check_database import check_database_empty as final_check_database_empty 
        success = not await final_check_database_empty() # Inverte lógica: True se tem dados (sucesso)
        
        if success:
            print("\n" + "=" * 60)
            print("🎉 CONFIGURAÇÃO COMPLETA FINALIZADA COM SUCESSO!")
            print("=" * 60)
            print("✅ Tabelas criadas")
            print("✅ Localidades SAP importadas")
            print("✅ Dados PMM_2 populados")
            print("✅ Dados básicos (equipamentos, manutenções, falhas) populados a partir de PMM_2")
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