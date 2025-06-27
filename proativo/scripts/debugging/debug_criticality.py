#!/usr/bin/env python3
"""
Script de debug para verificar conversão de criticidade.
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

def debug_criticality():
    """Debug da conversão de criticidade."""
    print("=== DEBUG CRITICALITY CONVERSION ===")
    
    processor = CSVProcessor()
    
    # Teste com equipment.csv
    file_path = Path("data/samples/equipment.csv")
    
    print(f"Processando arquivo: {file_path}")
    
    try:
        # Processar como equipamento
        print("\n--- Processando como equipamento ---")
        equipment_data = processor.process_equipment_csv(file_path)
        
        print(f"Total de registros processados: {len(equipment_data)}")
        
        # Verificar primeiros registros
        for i, record in enumerate(equipment_data[:5]):
            print(f"\nRegistro {i+1}:")
            print(f"  Code: {record.get('code', 'N/A')}")
            print(f"  Name: {record.get('name', 'N/A')}")
            print(f"  Criticality original: {record.get('criticality', 'N/A')}")
            print(f"  Equipment Type: {record.get('equipment_type', 'N/A')}")
        
    except Exception as e:
        print(f"ERRO: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_criticality() 