# File: scripts/setup/populate_database.py

import asyncio
import os
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime
from sqlalchemy import text # Import text for raw SQL queries

# Configurar paths (already present in your file)
current_dir = Path(__file__).parent
project_dir = current_dir.parent.parent
sys.path.insert(0, str(project_dir))
os.environ['PYTHONPATH'] = str(project_dir)

from src.etl.data_processor import DataProcessor, DataType
from src.database.repositories import RepositoryManager
from src.database.connection import db_connection, create_tables, init_database


async def derive_and_populate_equipments():
    """
    Derives equipment data from the PMM_2 table and populates the equipments table.
    Links equipments to SAP locations based on location codes.
    """
    print("📊 ETAPA 1: Derivando e populando equipamentos a partir da PMM_2...")
    
    async with db_connection.get_session() as session:
        repo_manager = RepositoryManager(session)
        processor = DataProcessor(repo_manager) # Use the existing ETL DataProcessor

        # COMENTANDO/REMOVENDO O BLOCO TRUNCATE
        # print("   ⚠️  Limpando tabelas de falhas, manutenções e equipamentos existentes para substituição completa...")
        # try:
        #     await session.execute(text("TRUNCATE TABLE failures RESTART IDENTITY CASCADE;"))
        #     await session.execute(text("TRUNCATE TABLE maintenances RESTART IDENTITY CASCADE;"))
        #     await session.execute(text("TRUNCATE TABLE equipments RESTART IDENTITY CASCADE;"))
        #     await session.commit()
        #     print("   ✅ Tabelas limpas com sucesso.")
        # except Exception as e:
        #     print(f"   ❌ Erro ao limpar tabelas: {e}. Abortando derivação de equipamentos.")
        #     await session.rollback()
        #     raise  

         # --- Adicionar logs de depuração AQUI ---
        print("   📚 Coletando dados da PMM_2 e localidades SAP do banco de dados...")
        try:
            # Primeiro, uma contagem bruta na sessão atual
            current_session_pmm_2_count = await session.execute(text("SELECT COUNT(*) FROM pmm_2;"))
            count_result = current_session_pmm_2_count.scalar_one()
            print(f"   DEBUG: Contagem de PMM_2 na sessão atual ANTES do list_all(): {count_result} registros.")

            # Agora, tente o list_all
            pmm_2_records = await repo_manager.pmm_2.list_all()
            sap_locations = await repo_manager.sap_location.list_all()
            
            print(f"   DEBUG: Quantidade de registros PMM_2 coletados pelo list_all(): {len(pmm_2_records)}")
            if len(pmm_2_records) > 0:
                print(f"   DEBUG: Primeiro registro PMM_2: {pmm_2_records[0].__dict__}")
            else:
                print("   DEBUG: pmm_2_records está REALMENTE vazio nesta sessão.")

        except Exception as e:
            print(f"   ❌ ERRO DE DEBUG: Falha ao tentar ler PMM_2 ou SAP Locations: {e}")
            # Isso capturaria erros se a tabela pmm_2 não existisse, mas pelos logs anteriores ela existe.
            # Ou se a conexão com o banco se perdeu.
            pmm_2_records = [] # Define como vazio para o fluxo continuar

        # --- Fim dos logs de depuração ---
        # Create a map for quick lookup of SAP location UUIDs by their code
        sap_location_map = {loc.location_code: str(loc.id) for loc in sap_locations}

        if not pmm_2_records:
            print("   ⚠️  Nenhum registro encontrado na tabela PMM_2. Verifique se o PMM_2 foi populado antes.")
            return {}

        derived_equipments_for_save = []
        unique_equipment_codes = set() # To ensure we create unique equipment records

        for pmm_record in pmm_2_records:
            # Assuming pmm_processor.py already extracted 'equipment_code' and 'installation_location'
            # and they are available as attributes on the PMM_2 model objects.
            equipment_code = getattr(pmm_record, 'equipment_code', None)
            full_installation_code = getattr(pmm_record, 'installation_location', None)

            if not equipment_code or not full_installation_code:
                print(f"   ⚠️  Registro PMM_2 ({getattr(pmm_record, 'maintenance_plan_code', 'N/A')}) sem 'equipment_code' ou 'installation_location' completo. Pulando derivação.")
                continue
            
            if equipment_code in unique_equipment_codes:
                continue # Already processed this equipment from another PMM_2 entry

            unique_equipment_codes.add(equipment_code)

            # Extract SAP Location Code (e.g., MT-S-70113 from MT-S-70113-FE01-CH-301F7T)
            # This logic should be consistent with how sap_location codes are stored.
            sap_location_prefix_parts = full_installation_code.split('-')[0:3]
            sap_location_code = "-".join(sap_location_prefix_parts) if len(sap_location_prefix_parts) == 3 else None

            sap_location_id = None
            if sap_location_code:
                sap_location_id = sap_location_map.get(sap_location_code)
                if not sap_location_id:
                    print(f"   ⚠️  Localidade SAP '{sap_location_code}' não encontrada para o código de instalação '{full_installation_code}'. Equipamento '{equipment_code}' não será associado a uma localidade SAP existente.")
            
            # Derive equipment_type (e.g., 'CH', 'DJ') from equipment_code
            equipment_type = equipment_code.split('-')[0] if '-' in equipment_code else 'UNKNOWN'

            # Construct the new equipment record for DataProcessor.save_to_database
            equipment_record = {
                'code': equipment_code,
                'name': f"Equipamento {equipment_code} ({full_installation_code})", 
                'type': equipment_type, # Derived from equipment_code
                'location': full_installation_code, # Store the full string as textual location
                'sap_location_id': sap_location_id, # Link to SAP_Location UUID
                'manufacturer': 'PMM_2 Source', # Placeholder as it's not in PMM_2 data
                'model': 'Derived', # Placeholder
                'installation_date': datetime.now(), # Use current datetime or try to parse from PMM_2 if a relevant date exists
                'rated_power': 0.0, # Default
                'voltage_level': 'N/A', # Default
                'status': 'Active', # Default in English for consistency
                'criticality': 'Medium', # Default in English for consistency
                'description': f"Equipamento derivado do plano de manutenção {getattr(pmm_record, 'maintenance_plan_code', 'N/A')} - {getattr(pmm_record, 'maintenance_item_text', 'N/A')}.",
                'data_source': 'PMM_2_Derived',
                'source_file': 'PMM_2.csv (derived)',
                'is_validated': True,
                'validation_status': 'Valid',
                'metadata_json': {
                    'derived_from_pmm_2_plan_code': getattr(pmm_record, 'maintenance_plan_code', 'N/A'),
                    'original_installation_location': full_installation_code,
                    'processed_at': datetime.now().isoformat()
                }
            }
            derived_equipments_for_save.append(equipment_record)

        if not derived_equipments_for_save:
            print("   ℹ️  Nenhum equipamento válido para criar a partir dos dados da PMM_2.")
            return {}
        
        # Use the DataProcessor to save the derived equipment records
        print(f"   📝 Salvando {len(derived_equipments_for_save)} equipamentos derivados no banco...")
        save_result = await processor.save_to_database(derived_equipments_for_save, DataType.EQUIPMENT)
        
        # Get the new equipment map (code -> UUID) after saving
        newly_created_equipments = await repo_manager.equipment.list_all() 
        equipment_map = {eq.code: str(eq.id) for eq in newly_created_equipments if eq.code} # Ensure code exists
        
        # Ensure session is committed
        await session.commit()

        print(f"   📈 Total: {save_result} equipamentos salvos/atualizados. Mapeamento de {len(equipment_map)} códigos para UUIDs.")
        
        return equipment_map


async def populate_maintenances(equipment_map):
    """Populates maintenance records in the database, using the new equipment_map."""
    print("🔧 ETAPA 2: Populando manutenções...")
    
    async with db_connection.get_session() as session:
        repo_manager = RepositoryManager(session)
        processor = DataProcessor(repo_manager) # Use the ETL DataProcessor
        
        maintenance_files = [
            "data/samples/maintenance_orders.csv",
            "data/samples/maintenance_schedules.csv",
        ]
        
        total_processed_records = 0
        
        for file_path_str in maintenance_files:
            file_path = Path(file_path_str)
            if not file_path.exists():
                print(f"   ⚠️  Arquivo não encontrado: {file_path}")
                continue
            
            print(f"   📁 Processando: {file_path.name}")
            
            try:
                # Use DataProcessor.process_file to read, standardize, and validate
                valid_records, validation_errors = processor.process_file(file_path, DataType.MAINTENANCE)
                
                converted_records = []
                for record in valid_records:
                    # Assuming equipment_id in maintenance CSVs now matches the new equipment_code (e.g., CH-301F7T)
                    equipment_code_from_csv = record.get('equipment_id') 
                    if equipment_code_from_csv and equipment_code_from_csv in equipment_map:
                        record['equipment_id'] = equipment_map[equipment_code_from_csv]
                        converted_records.append(record)
                    else:
                        print(f"   ⚠️  Manutenção para equipamento '{equipment_code_from_csv}' não encontrado no novo mapeamento de equipamentos. Pulando registro.")

                if converted_records:
                    # Use DataProcessor.save_to_database for bulk insert/upsert
                    saved_count = await processor.save_to_database(converted_records, DataType.MAINTENANCE)
                    total_processed_records += saved_count
                    print(f"   ✅ {saved_count} manutenções salvas.")
                else:
                    print("   ℹ️  Nenhuma manutenção válida para salvar após mapeamento.")
                
            except Exception as e:
                print(f"   ❌ Erro ao processar manutenções de {file_path.name}: {e}")
                import traceback
                traceback.print_exc() # Print full traceback for debugging
        
        print(f"   📈 Total: {total_processed_records} manutenções processadas.")
        await session.commit()


async def populate_failures(equipment_map):
    """Populates failure records in the database, using the new equipment_map."""
    print("💥 ETAPA 3: Populando falhas...")
    
    file_path = Path("data/samples/failures_incidents.csv")
    if not file_path.exists():
        print("   ⚠️  Arquivo failures_incidents.csv não encontrado")
        return
    
    print(f"   📁 Processando: {file_path.name}")
    
    async with db_connection.get_session() as session:
        repo_manager = RepositoryManager(session)
        processor = DataProcessor(repo_manager) # Use the ETL DataProcessor
        
        # Use DataProcessor.process_file to read, standardize, and validate
        valid_records, validation_errors = processor.process_file(file_path, DataType.FAILURE)

        failure_records_for_save = []
        for record in valid_records:
            equipment_code_from_csv = record.get('equipment_id') 
            if equipment_code_from_csv and equipment_code_from_csv in equipment_map:
                record['equipment_id'] = equipment_map[equipment_code_from_csv]
                failure_records_for_save.append(record)
            else:
                print(f"   ⚠️  Falha para equipamento '{equipment_code_from_csv}' não encontrado no novo mapeamento de equipamentos. Pulando registro.")

        if failure_records_for_save:
            # Use DataProcessor.save_to_database for bulk insert/upsert
            saved_count = await processor.save_to_database(failure_records_for_save, DataType.FAILURE)
            print(f"   ✅ {saved_count} registros de falhas salvos.")
        else:
            print("   ℹ️  Nenhuma falha válida para salvar após mapeamento.")
        
        await session.commit()


async def verify_population():
    """Verifies populated data. (Function remains unchanged)"""
    print("🔍 ETAPA 4: Verificando população...")
    
    async with db_connection.get_session() as session:
        repo_manager = RepositoryManager(session)
        
        equipment_count = await repo_manager.equipment.count()
        maintenance_count = await repo_manager.maintenance.count()
        failure_count = await repo_manager.failures.count()
        
        print(f"   📊 Equipamentos: {equipment_count}")
        print(f"   📊 Manutenções: {maintenance_count}")
        print(f"   📊 Falhas: {failure_count}")
        print(f"   📊 Total: {equipment_count + maintenance_count + failure_count}")
        
        return equipment_count > 0


async def main():
    """Main function - populates all data."""
    print("🚀 POPULAÇÃO UNIFICADA DE DADOS")
    print("=================================")
    
    try:
        await init_database()
        
        # NEW: Call the derived equipment population function
        equipment_map = await derive_and_populate_equipments()
        
        if not equipment_map:
            print("❌ Nenhum equipamento processado - abortando população de manutenções e falhas.")
            return False # Indicate failure if no equipment could be derived

        # The following steps now depend on the equipment_map generated above
        await populate_maintenances(equipment_map)
        
        await populate_failures(equipment_map)
        
        success = await verify_population()
        
        if success:
            print("\n🎉 BANCO POPULADO COM SUCESSO!")
            return True
        else:
            print("\n❌ POPULAÇÃO INCOMPLETA")
            return False
            
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)