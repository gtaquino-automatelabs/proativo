#!/usr/bin/env python3
"""
Script para popular a tabela data_history com dados de incidentes e falhas.
Converte dados de failures_incidents.csv para o formato da tabela data_history.
"""

import sys
import os
import asyncio
import pandas as pd
from pathlib import Path
from datetime import datetime

# Configurar paths
current_dir = Path(__file__).parent
project_dir = current_dir.parent.parent
src_dir = project_dir / "src"
sys.path.insert(0, str(project_dir))
os.environ['PYTHONPATH'] = str(src_dir)

from src.database.connection import db_connection, init_database
from src.database.repositories import RepositoryManager


async def populate_data_history():
    """Popula a tabela data_history com dados de incidentes."""
    print("=== POPULANDO DATA_HISTORY ===")
    
    # Inicializa conexão com banco
    await init_database()
    
    async with db_connection.get_session() as session:
        repo_manager = RepositoryManager(session)
        
        # 1. Busca mapeamento código → UUID dos equipamentos
        print("\n1. Buscando equipamentos no banco...")
        equipments = await repo_manager.equipment.list_all(limit=1000)
        
        code_to_uuid = {}
        for equipment in equipments:
            code_to_uuid[equipment.code] = equipment.id
        
        print(f"   Encontrados {len(equipments)} equipamentos")
        
        # 2. Lê dados de incidentes
        print("\n2. Processando failures_incidents.csv...")
        file_path = Path("data/samples/failures_incidents.csv")
        
        df = pd.read_csv(file_path, dtype=str)
        print(f"   {len(df)} incidentes encontrados")
        
        # 3. Converte dados para formato data_history
        print("\n3. Convertendo dados para data_history...")
        
        history_records = []
        errors = []
        
        for _, row in df.iterrows():
            equipment_code = row['equipment_id']
            
            if equipment_code not in code_to_uuid:
                errors.append(f"Equipamento não encontrado: {equipment_code}")
                continue
            
            # Mapeia impacto para condition_status
            impact_mapping = {
                'Alto': 'Critical',
                'Médio': 'Warning', 
                'Baixo': 'Good'
            }
            
            # Converte data COM timezone (UTC)
            try:
                occurrence_date = pd.to_datetime(row['occurrence_date'])
                # Adiciona timezone UTC se a data não tiver timezone
                if occurrence_date.tz is None:
                    occurrence_date = occurrence_date.tz_localize('UTC')
            except:
                errors.append(f"Data inválida: {row['occurrence_date']}")
                continue
            
            record = {
                'equipment_id': code_to_uuid[equipment_code],
                'data_source': 'CSV',
                'data_type': 'Event',
                'timestamp': occurrence_date,
                
                # Dados do incidente
                'measurement_type': row['failure_type'],
                'measurement_value': float(row['downtime_hours']) if row['downtime_hours'] else None,
                'measurement_unit': 'hours',
                'text_value': row['incident_number'],
                
                # Status e condição
                'condition_status': impact_mapping.get(row['impact_level'], 'Unknown'),
                'alert_level': 'Critical' if row['impact_level'] == 'Alto' else 
                             'Warning' if row['impact_level'] == 'Médio' else 'Normal',
                
                # Contexto
                'inspector': 'Sistema Automático',
                'collection_method': 'Manual',
                'source_file': 'failures_incidents.csv',
                'source_row': _ + 2,  # +2 por causa do header e índice 0
                
                # Validação
                'is_validated': True,
                'validation_status': 'Valid',
                'quality_score': 0.95,  # Alta qualidade - dados sintéticos controlados
                
                # Dados estruturados
                'raw_data': {
                    'incident_id': row['id'],
                    'incident_number': row['incident_number'],
                    'root_cause': row['root_cause'],
                    'affected_customers': int(row['affected_customers']) if row['affected_customers'] else 0,
                    'original_data': dict(row)
                },
                'processed_data': {
                    'failure_type': row['failure_type'],
                    'root_cause': row['root_cause'],
                    'resolution_description': row['resolution_description'],
                    'lessons_learned': row['lessons_learned'],
                    'impact_summary': {
                        'level': row['impact_level'],
                        'downtime_hours': float(row['downtime_hours']) if row['downtime_hours'] else 0,
                        'customers_affected': int(row['affected_customers']) if row['affected_customers'] else 0
                    }
                },
                
                # Metadados
                'metadata_json': {
                    'source_file': 'failures_incidents.csv',
                    'processing_method': 'populate_data_history.py',
                    'processed_at': datetime.now().isoformat(),
                    'data_category': 'Historical_Incident'
                }
            }
            
            history_records.append(record)
            print(f"   ✅ {equipment_code} → {row['failure_type']} ({row['occurrence_date']})")
        
        print(f"\n   Registros preparados: {len(history_records)}")
        print(f"   Erros: {len(errors)}")
        
        if errors:
            print("\nErros encontrados:")
            for error in errors:
                print(f"   - {error}")
        
        # 4. Salva no banco de dados
        if history_records:
            print(f"\n4. Salvando {len(history_records)} registros em data_history...")
            
            # Remove registros existentes de incidentes (se houver)
            existing_records = await repo_manager.data_history.list_all(limit=1000)
            incident_records = [r for r in existing_records if r.data_type == 'Event']
            
            if incident_records:
                print(f"   Removendo {len(incident_records)} registros de eventos existentes...")
                for record in incident_records:
                    await repo_manager.data_history.delete(record.id)
            
            # Salva novos registros
            saved_count = 0
            for record in history_records:
                try:
                    await repo_manager.data_history.create(**record)
                    saved_count += 1
                except Exception as e:
                    print(f"   ❌ Erro ao salvar registro: {e}")
                    print(f"      Equipment: {record.get('equipment_id')}")
            
            await session.commit()
            print(f"   ✅ {saved_count} registros salvos com sucesso!")
        
        # 5. Estatísticas finais
        print("\n5. Verificando dados inseridos...")
        total_history = await repo_manager.data_history.count()
        print(f"   Total de registros em data_history: {total_history}")
        
        # Mostra alguns exemplos
        recent_records = await repo_manager.data_history.list_all(limit=3)
        if recent_records:
            print("\n   Exemplos de registros inseridos:")
            for record in recent_records:
                print(f"   - {record.measurement_type} | {record.timestamp} | {record.condition_status}")
        
        print("\n=== POPULAÇÃO CONCLUÍDA ===")


if __name__ == "__main__":
    asyncio.run(populate_data_history()) 