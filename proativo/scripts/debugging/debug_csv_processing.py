#!/usr/bin/env python3
"""
Script de debug para verificar o processamento CSV.
"""

import sys
import os
from pathlib import Path

# Configurar paths
current_dir = Path(__file__).parent
project_dir = current_dir.parent
src_dir = project_dir / "src"
sys.path.insert(0, str(project_dir))
os.environ['PYTHONPATH'] = str(src_dir)

from src.etl.processors.csv_processor import CSVProcessor

def debug_csv_processing():
    """Debug do processamento CSV."""
    print("=== DEBUG CSV PROCESSING ===")
    
    processor = CSVProcessor()
    
    # Teste com maintenance_orders.csv
    file_path = Path("data/samples/maintenance_orders.csv")
    
    print(f"Processando arquivo: {file_path}")
    
    try:
        # Processar como manutenção
        print("\n--- Processando como manutenção ---")
        maintenance_records = processor.process_maintenance_csv(file_path)
        
        print(f"Total de registros: {len(maintenance_records)}")
        
        if maintenance_records:
            print("\nPrimeiro registro:")
            first_record = maintenance_records[0]
            for key, value in first_record.items():
                print(f"  {key}: {value}")
            
            # Verificar especificamente o equipment_id
            print(f"\nequipment_id do primeiro registro: '{first_record.get('equipment_id')}'")
            
            print("\nTodos os equipment_ids:")
            for i, record in enumerate(maintenance_records[:5]):  # Primeiros 5
                equipment_id = record.get('equipment_id')
                print(f"  Registro {i+1}: '{equipment_id}' (tipo: {type(equipment_id)})")
    
    except Exception as e:
        print(f"ERRO: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_csv_processing() 