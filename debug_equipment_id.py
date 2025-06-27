#!/usr/bin/env python3
"""
Script de debug para identificar onde o equipment_id está sendo perdido
"""

import sys
from pathlib import Path

# Adicionar src ao Python path
sys.path.insert(0, str(Path(__file__).parent / 'proativo' / 'src'))

from etl.processors.csv_processor import CSVProcessor
import pandas as pd

def debug_csv_processing():
    """Debug do processamento CSV de manutenções"""
    print("=== DEBUG: PROCESSAMENTO CSV DE MANUTENÇÕES ===")
    
    # Arquivo de teste
    csv_file = Path("proativo/data/samples/maintenance_orders.csv")
    print(f"Arquivo: {csv_file}")
    
    # 1. Ler CSV diretamente com pandas
    print("\n1. LENDO CSV DIRETAMENTE:")
    df_raw = pd.read_csv(csv_file)
    print(f"Colunas: {list(df_raw.columns)}")
    print(f"equipment_id primeiros 5: {df_raw['equipment_id'].head().tolist()}")
    print(f"Tipos: {df_raw.dtypes}")
    
    # 2. Processar com CSVProcessor
    print("\n2. PROCESSANDO COM CSVProcessor:")
    processor = CSVProcessor()
    
    try:
        records = processor.process_maintenance_csv(csv_file)
        print(f"Total de records retornados: {len(records)}")
        
        if records:
            first_record = records[0]
            print(f"Primeiro record: {first_record}")
            print(f"equipment_id no primeiro record: {first_record.get('equipment_id', 'AUSENTE!')}")
            print(f"Todas as chaves: {list(first_record.keys())}")
            
            # Verificar se algum record tem equipment_id
            records_with_equipment_id = [r for r in records if r.get('equipment_id')]
            print(f"Records com equipment_id: {len(records_with_equipment_id)}")
            
            if records_with_equipment_id:
                print(f"Exemplo de record com equipment_id: {records_with_equipment_id[0].get('equipment_id')}")
    
    except Exception as e:
        print(f"ERRO: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_csv_processing() 