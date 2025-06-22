#!/usr/bin/env python3
"""
Script para corrigir o mapeamento de equipment_id nas manutenções.
Converte códigos de equipamentos (TR-001, DJ-001) para UUIDs corretos.
"""

import sys
import os
import asyncio
from pathlib import Path

# Configurar paths
current_dir = Path(__file__).parent
project_dir = current_dir.parent
src_dir = project_dir / "src"
sys.path.insert(0, str(project_dir))
os.environ['PYTHONPATH'] = str(src_dir)

from src.database.connection import db_connection, init_database
from src.database.repositories import RepositoryManager
from src.etl.processors.csv_processor import CSVProcessor


async def fix_equipment_mapping():
    """Corrige o mapeamento de equipment_id nas manutenções."""
    print("=== CORREÇÃO DE MAPEAMENTO EQUIPMENT_ID ===")
    
    # Inicializa conexão com banco
    await init_database()
    
    # Inicializa session e repositório
    async with db_connection.get_session() as session:
        repo_manager = RepositoryManager(session)
        
        # 1. Busca todos os equipamentos para criar mapeamento código -> ID
        print("\n1. Buscando equipamentos no banco...")
        equipments = await repo_manager.equipment.list_all(limit=1000)
        
        # Cria mapeamento código -> UUID
        code_to_uuid = {}
        for equipment in equipments:
            code_to_uuid[equipment.code] = equipment.id
        
        print(f"   Encontrados {len(equipments)} equipamentos")
        print("   Alguns mapeamentos:")
        for i, (code, uuid) in enumerate(list(code_to_uuid.items())[:5]):
            print(f"   {code} -> {uuid}")
        
        # 2. Processa arquivo CSV de manutenções
        print("\n2. Processando arquivo de manutenções...")
        csv_processor = CSVProcessor()
        file_path = Path("data/samples/maintenance_orders.csv")
        
        maintenance_records = csv_processor.process_maintenance_csv(file_path)
        print(f"   {len(maintenance_records)} registros de manutenção processados")
        
        # 3. Corrige mapeamento equipment_id
        print("\n3. Corrigindo mapeamento equipment_id...")
        fixed_records = []
        errors = []
        
        for record in maintenance_records:
            original_equipment_id = record.get('equipment_id')
            
            if original_equipment_id and original_equipment_id in code_to_uuid:
                # Converte código para UUID
                record['equipment_id'] = code_to_uuid[original_equipment_id]
                fixed_records.append(record)
                print(f"   ✅ {original_equipment_id} -> {record['equipment_id']}")
            else:
                error_msg = f"Equipamento não encontrado: {original_equipment_id}"
                errors.append(error_msg)
                print(f"   ❌ {error_msg}")
        
        print(f"\n   Registros corrigidos: {len(fixed_records)}")
        print(f"   Erros: {len(errors)}")
        
        if errors:
            print("\nErros encontrados:")
            for error in errors:
                print(f"   - {error}")
        
        # 4. Salva manutenções corrigidas no banco
        if fixed_records:
            print(f"\n4. Salvando {len(fixed_records)} manutenções no banco...")
            
            # Remove manutenções existentes primeiro (para evitar duplicatas)
            existing_maintenances = await repo_manager.maintenance.list_all(limit=1000)
            print(f"   Removendo {len(existing_maintenances)} manutenções existentes...")
            
            for maintenance in existing_maintenances:
                await repo_manager.maintenance.delete(maintenance.id)
            
            # Salva manutenções corrigidas
            saved_count = 0
            for record in fixed_records:
                try:
                    # Mapeia campos do CSV para modelo de banco
                    clean_record = {}
                    
                    # Campos obrigatórios
                    clean_record['equipment_id'] = record['equipment_id']  # Já convertido para UUID
                    
                    # Mapeia tipo de manutenção
                    type_mapping = {
                        'preventiva': 'Preventive',
                        'corretiva': 'Corrective', 
                        'preditiva': 'Predictive',
                        'emergencial': 'Emergency'
                    }
                    clean_record['maintenance_type'] = type_mapping.get(
                        record.get('type', '').lower(), 'Preventive'
                    )
                    
                    clean_record['title'] = record.get('description', 'Manutenção')
                    
                    # Mapeia prioridade
                    priority_mapping = {
                        'alta': 'High',
                        'média': 'Medium',
                        'media': 'Medium', 
                        'baixa': 'Low'
                    }
                    clean_record['priority'] = priority_mapping.get(
                        record.get('priority', '').lower(), 'Medium'
                    )
                    
                    # Campos opcionais com mapeamento
                    if 'order_number' in record:
                        clean_record['maintenance_code'] = record['order_number']
                    if 'description' in record:
                        clean_record['description'] = record['description']
                    if 'scheduled_date' in record:
                        clean_record['scheduled_date'] = record['scheduled_date']
                    if 'start_date' in record:
                        clean_record['start_date'] = record['start_date']
                    if 'completion_date' in record:
                        clean_record['completion_date'] = record['completion_date']
                    
                    # Mapeia status
                    if 'status' in record:
                        status_mapping = {
                            'aberta': 'Planned',
                            'em andamento': 'InProgress',
                            'concluída': 'Completed',
                            'concluida': 'Completed',
                            'cancelada': 'Cancelled'
                        }
                        clean_record['status'] = status_mapping.get(
                            record['status'].lower(), 'Planned'
                        )
                    
                    if 'cost' in record:
                        clean_record['actual_cost'] = record['cost']
                    if 'technician_team' in record:
                        clean_record['team'] = record['technician_team']
                    
                    await repo_manager.maintenance.create(**clean_record)
                    saved_count += 1
                    
                except Exception as e:
                    print(f"   ❌ Erro ao salvar manutenção: {e}")
                    print(f"      Dados: {clean_record}")
            
            await session.commit()
            print(f"   ✅ {saved_count} manutenções salvas com sucesso!")
        
        print("\n=== CORREÇÃO CONCLUÍDA ===")


if __name__ == "__main__":
    asyncio.run(fix_equipment_mapping()) 