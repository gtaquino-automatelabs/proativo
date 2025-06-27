#!/usr/bin/env python3
"""
Script para testar processadores XML e XLSX e identificar problemas com campos.
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

from src.etl.processors.xml_processor import XMLProcessor
from src.etl.processors.xlsx_processor import XLSXProcessor


def test_xml_processor():
    """Testa o processador XML."""
    print("=== TESTE PROCESSADOR XML ===")
    
    xml_processor = XMLProcessor()
    file_path = Path("data/samples/equipment.xml")
    
    try:
        equipment_records = xml_processor.process_equipment_xml(file_path)
        
        print(f"Total de registros processados: {len(equipment_records)}")
        
        if equipment_records:
            print("\nPrimeiro registro:")
            first_record = equipment_records[0]
            for key, value in first_record.items():
                print(f"  {key}: {type(value).__name__} = {value}")
            
            # Verifica se tem campo 'code'
            has_code = 'code' in first_record
            print(f"\n🔍 Campo 'code' presente: {has_code}")
            
            if not has_code:
                print("❌ PROBLEMA: Campo 'code' ausente!")
                print("Campos disponíveis que poderiam ser 'code':")
                for key in first_record.keys():
                    if key in ['id', 'equipment_id', 'codigo', 'equipamento']:
                        print(f"   - {key}: {first_record[key]}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")


def test_xlsx_processor():
    """Testa o processador XLSX."""
    print("\n=== TESTE PROCESSADOR XLSX ===")
    
    xlsx_processor = XLSXProcessor()
    file_path = Path("data/samples/electrical_assets.xlsx")
    
    try:
        equipment_records = xlsx_processor.process_equipment_xlsx(file_path)
        
        print(f"Total de registros processados: {len(equipment_records)}")
        
        if equipment_records:
            print("\nPrimeiro registro:")
            first_record = equipment_records[0]
            for key, value in first_record.items():
                print(f"  {key}: {type(value).__name__} = {value}")
            
            # Verifica se tem campo 'code'
            has_code = 'code' in first_record
            print(f"\n🔍 Campo 'code' presente: {has_code}")
            
            if not has_code:
                print("❌ PROBLEMA: Campo 'code' ausente!")
                print("Campos disponíveis que poderiam ser 'code':")
                for key in first_record.keys():
                    if key in ['id', 'equipment_id', 'codigo', 'equipamento']:
                        print(f"   - {key}: {first_record[key]}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")


def test_maintenance_xml_processor():
    """Testa o processador XML para manutenções."""
    print("\n=== TESTE PROCESSADOR XML MANUTENÇÕES ===")
    
    xml_processor = XMLProcessor()
    file_path = Path("data/samples/maintenance_orders.xml")
    
    try:
        maintenance_records = xml_processor.process_maintenance_xml(file_path)
        
        print(f"Total de registros processados: {len(maintenance_records)}")
        
        if maintenance_records:
            print("\nPrimeiro registro:")
            first_record = maintenance_records[0]
            for key, value in first_record.items():
                print(f"  {key}: {type(value).__name__} = {value}")
            
            # Verifica se tem campo 'equipment_id'
            has_equipment_id = 'equipment_id' in first_record
            print(f"\n🔍 Campo 'equipment_id' presente: {has_equipment_id}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")


if __name__ == "__main__":
    test_xml_processor()
    test_xlsx_processor()
    test_maintenance_xml_processor() 