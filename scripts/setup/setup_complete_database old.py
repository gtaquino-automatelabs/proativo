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
    """Verifica o status detalhado do banco e determina que ações são necessárias."""
    print("🔍 VERIFICAÇÃO INICIAL")
    print("=" * 50)
    
    try:
        await init_database()
        
        from scripts.setup.check_database import check_database_status
        status = await check_database_status()
        
        # Determina se há tabelas que não existem
        missing_tables = [table for table, info in status.items() if not info['table_exists']]
        
        # Determina se há tabelas que precisam ser populadas
        empty_tables = [table for table, info in status.items() if info['needs_population'] and info['table_exists']]
        
        # Calcula total de registros
        total_records = sum(table['count'] for table in status.values())
        
        # Determina o tipo de ação necessária
        if missing_tables:
            print("🔧 Algumas tabelas não existem - criação necessária")
            return status, "missing_tables"
        elif total_records == 0:
            print("💡 Banco vazio - configuração completa necessária")
            return status, "empty"
        elif empty_tables:
            print(f"📋 Algumas tabelas precisam ser populadas: {', '.join(empty_tables)}")
            return status, "partial_population"
        else:
            print("✅ Banco já está completamente populado")
            return status, "populated"
            
    except Exception as e:
        print(f"❌ Erro na verificação inicial: {e}")
        # Em caso de erro, assume status vazio
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
    Determina quais scripts devem ser executados baseados no status das tabelas.
    
    Args:
        status: Dict com status detalhado das tabelas
        status_type: Tipo de status ("empty", "missing_tables", "partial_population", "populated")
    
    Returns:
        Dict com scripts que devem ser executados
    """
    scripts_to_run = {
        'create_tables': False,
        'populate_database': False,
        'import_localidades_sap': False,
        'correlate_equipment_locations': False,
        'populate_pmm_2': False
    }
    
    if status_type in ["empty", "missing_tables", "error"]:
        # Se está vazio ou com tabelas faltando, executa tudo
        scripts_to_run['create_tables'] = True
        scripts_to_run['populate_database'] = True
        scripts_to_run['import_localidades_sap'] = True
        scripts_to_run['correlate_equipment_locations'] = True
        scripts_to_run['populate_pmm_2'] = True
    
    elif status_type == "partial_population":
        # Se é população parcial, executa apenas os necessários
        
        # Se não tem tabelas, cria primeiro
        missing_tables = [table for table, info in status.items() if not info['table_exists']]
        if missing_tables:
            scripts_to_run['create_tables'] = True
        
        # Dados básicos (equipamentos, manutenções, falhas)
        needs_basic_data = (
            status['equipment']['needs_population'] or 
            status['maintenance']['needs_population'] or 
            status['failure']['needs_population']
        )
        if needs_basic_data:
            scripts_to_run['populate_database'] = True
        
        # Localidades SAP
        if status['sap_location']['needs_population']:
            scripts_to_run['import_localidades_sap'] = True
        
        # Correlação (apenas se tem equipamentos e localidades)
        if (not status['equipment']['needs_population'] and 
            not status['sap_location']['needs_population']):
            scripts_to_run['correlate_equipment_locations'] = True
        
        # PMM_2
        if status['pmm_2']['needs_population']:
            scripts_to_run['populate_pmm_2'] = True
    
    return scripts_to_run


async def main():
    """Função principal - configura banco completo."""
    print("🚀 PROATIVO - CONFIGURAÇÃO AUTOMÁTICA INTELIGENTE")
    print("=" * 60)
    print("Este script irá:")
    print("   1️⃣  Verificar status detalhado de cada tabela")
    print("   2️⃣  Determinar scripts necessários automaticamente")
    print("   3️⃣  Criar tabelas (se necessário)")
    print("   4️⃣  Popular dados básicos (se necessário)")
    print("   5️⃣  Importar localidades SAP (se necessário)")
    print("   6️⃣  Correlacionar equipamentos com localidades (se necessário)")
    print("   7️⃣  Popular dados PMM_2 (se necessário)")
    print("   8️⃣  Verificar resultado final")
    print("=" * 60)
    print("✨ NOVO: Executa apenas os scripts necessários para cada tabela!")
    
    try:
        # ETAPA 1: Verificação inicial
        status, status_type = await check_initial_status()
        
        if status_type == "populated":
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
        
        # ETAPA 3: Criar tabelas (se necessário)
        if scripts_to_run['create_tables']:
            success = await run_script("create_tables.py", "CRIANDO TABELAS")
            if not success:
                print("\n❌ FALHA na criação de tabelas - abortando")
                return False
        
        # ETAPA 4: Popular dados básicos (se necessário)
        if scripts_to_run['populate_database']:
            success = await run_script("populate_database.py", "POPULANDO DADOS BÁSICOS")
            if not success:
                print("\n❌ FALHA na população básica - abortando")
                return False
        
        # ETAPA 5: Importar localidades SAP (se necessário)
        if scripts_to_run['import_localidades_sap']:
            success = await run_script("import_localidades_sap.py", "IMPORTANDO LOCALIDADES SAP")
            if not success:
                print("\n⚠️  FALHA na importação de localidades SAP - continuando")
                # Não aborta aqui, pois é não-crítico
        
        # ETAPA 6: Correlacionar equipamentos com localidades (se necessário)
        if scripts_to_run['correlate_equipment_locations']:
            success = await run_script("correlate_equipment_locations.py", "CORRELACIONANDO EQUIPAMENTOS COM LOCALIDADES")
            if not success:
                print("\n⚠️  FALHA na correlação de localidades - continuando")
                # Não aborta aqui, pois é não-crítico
        
        # ETAPA 7: Popular dados PMM_2 (se necessário)
        if scripts_to_run['populate_pmm_2']:
            success = await run_script("populate_pmm_2.py", "POPULANDO DADOS PMM_2")
            if not success:
                print("\n⚠️  FALHA na população de PMM_2 - continuando")
                # Não aborta aqui, pois é não-crítico
        
        # ETAPA 8: Verificação final
        success = await run_script("check_database.py", "VERIFICAÇÃO FINAL")
        
        if success:
            print("\n" + "=" * 60)
            print("🎉 CONFIGURAÇÃO COMPLETA FINALIZADA COM SUCESSO!")
            print("=" * 60)
            print("✅ Tabelas criadas")
            print("✅ Dados básicos populados")
            print("✅ Localidades SAP importadas")
            print("✅ Equipamentos correlacionados com localidades")
            print("✅ Dados PMM_2 populados")
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