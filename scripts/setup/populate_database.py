#!/usr/bin/env python3
"""
Script unificado para popular TODOS os dados no banco PROAtivo.
Substitui: populate_equipment.py + populate_failures.py
"""

import asyncio
import os
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

# Configurar paths
current_dir = Path(__file__).parent
project_dir = current_dir.parent.parent
sys.path.insert(0, str(project_dir))
os.environ['PYTHONPATH'] = str(project_dir)

from src.etl.data_processor import DataProcessor, DataType
from src.database.repositories import RepositoryManager
from src.database.connection import db_connection, create_tables, init_database


async def populate_equipments():
    """Popula equipamentos no banco."""
    print("📊 ETAPA 1: Populando equipamentos...")
    
    async with db_connection.get_session() as session:
        repo_manager = RepositoryManager(session)
        processor = DataProcessor(repo_manager)
        
        equipment_files = [
            "data/samples/equipment.csv",
            # Adicionar outros se necessário
        ]
        
        total_processed = 0
        equipment_map = {}
        
        for file_path_str in equipment_files:
            file_path = Path(file_path_str)
            if not file_path.exists():
                print(f"   ⚠️  Arquivo não encontrado: {file_path}")
                continue
            
            print(f"   📁 Processando: {file_path.name}")
            
            try:
                result = await processor.process_and_save(file_path, DataType.EQUIPMENT)
                
                if result['success']:
                    total_processed += result['saved_records']
                    print(f"   ✅ {result['saved_records']} equipamentos salvos")
                else:
                    print(f"   ❌ Erro: {result.get('error', 'Desconhecido')}")
                    
            except Exception as e:
                print(f"   ❌ Erro: {e}")
        
        # Atualizar mapeamento código->UUID
        equipments = await repo_manager.equipment.list_all(limit=1000)
        for eq in equipments:
            equipment_map[eq.code] = str(eq.id)
        
        print(f"   📈 Total: {total_processed} equipamentos, {len(equipment_map)} no banco")
        await session.commit()
        
        return equipment_map


async def populate_maintenances(equipment_map):
    """Popula manutenções no banco."""
    print("🔧 ETAPA 2: Populando manutenções...")
    
    async with db_connection.get_session() as session:
        repo_manager = RepositoryManager(session)
        processor = DataProcessor(repo_manager)
        
        maintenance_files = [
            "data/samples/maintenance_orders.csv",
            "data/samples/maintenance_schedules.csv",
        ]
        
        total_processed = 0
        
        for file_path_str in maintenance_files:
            file_path = Path(file_path_str)
            if not file_path.exists():
                print(f"   ⚠️  Arquivo não encontrado: {file_path}")
                continue
            
            print(f"   📁 Processando: {file_path.name}")
            
            try:
                # Processar arquivo
                valid_records, validation_errors = processor.process_file(file_path, DataType.MAINTENANCE)
                
                # Converter códigos para UUIDs
                converted_records = []
                for record in valid_records:
                    equipment_code = record.get('equipment_id')
                    if equipment_code and equipment_code in equipment_map:
                        record['equipment_id'] = equipment_map[equipment_code]
                        converted_records.append(record)
                
                # Salvar
                if converted_records:
                    saved_count = await processor.save_to_database(converted_records, DataType.MAINTENANCE)
                    total_processed += saved_count
                    print(f"   ✅ {saved_count} manutenções salvas")
                
            except Exception as e:
                print(f"   ❌ Erro: {e}")
        
        print(f"   📈 Total: {total_processed} manutenções processadas")
        await session.commit()


async def populate_failures(equipment_map):
    """Popula registros de falhas."""
    print("💥 ETAPA 3: Populando falhas...")
    
    file_path = Path("data/samples/failures_incidents.csv")
    if not file_path.exists():
        print("   ⚠️  Arquivo failures_incidents.csv não encontrado")
        return
    
    print(f"   📁 Processando: {file_path.name}")
    
    async with db_connection.get_session() as session:
        repo_manager = RepositoryManager(session)
        
        # Ler CSV
        df = pd.read_csv(file_path, dtype=str)
        
        # Processar registros
        failure_records = []
        for _, row in df.iterrows():
            equipment_code = row['equipment_id']
            
            if equipment_code not in equipment_map:
                continue
            
            # Mapear nível de impacto para severidade
            severity_mapping = {
                'Alto': 'Critical',
                'Médio': 'High', 
                'Baixo': 'Medium'
            }
            
            # Converter data
            try:
                failure_date = pd.to_datetime(row['occurrence_date'])
                if failure_date.tz is None:
                    failure_date = failure_date.tz_localize('UTC')
            except:
                continue
            
            # Converter valores numéricos
            downtime_hours = None
            affected_customers = None
            
            try:
                downtime_str = str(row['downtime_hours']).strip()
                if downtime_str and downtime_str.lower() not in ['nan', 'none', '']:
                    downtime_hours = float(downtime_str)
            except (ValueError, TypeError):
                pass
            
            try:
                customers_str = str(row['affected_customers']).strip()
                if customers_str and customers_str.lower() not in ['nan', 'none', '']:
                    affected_customers = int(customers_str)
            except (ValueError, TypeError):
                pass
            
            record = {
                'equipment_id': equipment_map[equipment_code],
                'incident_id': row['id'],
                'incident_number': row['incident_number'],
                'failure_date': failure_date,
                'failure_type': row['failure_type'],
                'description': f"Falha do tipo {row['failure_type']} - {str(row['root_cause'])}",
                'root_cause': str(row['root_cause']),
                'severity': severity_mapping.get(str(row['impact_level']), 'Medium'),
                'impact_level': row['impact_level'],
                'downtime_hours': downtime_hours,
                'affected_customers': affected_customers,
                'resolution_description': str(row['resolution_description']) if str(row['resolution_description']) != 'nan' else '',
                'lessons_learned': str(row['lessons_learned']) if str(row['lessons_learned']) != 'nan' else '',
                'data_source': 'CSV',
                'source_file': 'failures_incidents.csv',
                'status': 'Resolved',  # Assumindo que incidentes históricos já foram resolvidos
                'is_validated': True,
                'validation_status': 'Valid',
                'raw_data': {
                    'original_incident_id': row['id'],
                    'original_data': dict(row)
                },
                'processed_data': {
                    'severity_mapping': {
                        'original': row['impact_level'],
                        'mapped': severity_mapping.get(str(row['impact_level']), 'Medium')
                    },
                    'data_quality': {
                        'downtime_parsed': downtime_hours is not None,
                        'customers_parsed': affected_customers is not None
                    }
                },
                'metadata_json': {
                    'source_file': 'failures_incidents.csv',
                    'processed_at': datetime.now().isoformat(),
                    'data_version': '1.0'
                }
            }
            
            failure_records.append(record)
        
        # Salvar registros
        saved_count = 0
        for record in failure_records:
            try:
                await repo_manager.failures.create(**record)
                saved_count += 1
            except Exception as e:
                print(f"   ⚠️  Erro ao salvar falha: {e}")
        
        await session.commit()
        print(f"   ✅ {saved_count} registros de falhas salvos")


async def verify_population():
    """Verifica dados populados."""
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
    """Função principal - popula todos os dados."""
    print("🚀 POPULAÇÃO UNIFICADA DE DADOS")
    print("=================================")
    
    try:
        # Inicializar conexão com banco
        await init_database()
        
        # Criar tabelas se necessário
        await create_tables()
        
        # Etapa 1: Equipamentos
        equipment_map = await populate_equipments()
        
        if not equipment_map:
            print("❌ Nenhum equipamento processado - abortando")
            return False
        
        # Etapa 2: Manutenções
        await populate_maintenances(equipment_map)
        
        # Etapa 3: Falhas
        await populate_failures(equipment_map)
        
        # Etapa 4: Verificação
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