#!/usr/bin/env python3
"""
Script para debugar o carregamento de equipamentos
"""
import sys
import pandas as pd
from pathlib import Path

# Adicionar o caminho do projeto
sys.path.append('proativo/src')

from database.connection import get_db_connection
from etl.data_processor import DataProcessor
from etl.processors.csv_processor import CSVProcessor

def debug_equipment_loading():
    print("🔍 DIAGNÓSTICO: Carregamento de Equipamentos")
    print("=" * 50)
    
    # 1. Verificar quantos equipamentos estão no CSV
    csv_path = Path("proativo/data/samples/equipment.csv")
    df_csv = pd.read_csv(csv_path)
    print(f"📄 CSV: {len(df_csv)} equipamentos encontrados")
    print(f"📋 Códigos no CSV: {list(df_csv['id'].head(10))}...")
    
    # 2. Verificar quantos estão no banco
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM equipments")
            db_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT code FROM equipments ORDER BY equipment_id")
            db_codes = [row[0] for row in cursor.fetchall()]
            
        print(f"🗄️ Banco: {db_count} equipamentos encontrados")
        print(f"📋 Códigos no banco: {db_codes}")
        
        # Encontrar quais não foram carregados
        csv_codes = set(df_csv['id'].tolist())
        db_codes_set = set(db_codes)
        missing_codes = csv_codes - db_codes_set
        
        print(f"\n❌ Equipamentos NOT LOADED ({len(missing_codes)}):")
        for code in sorted(missing_codes):
            print(f"   - {code}")
            
        conn.close()
        
    except Exception as e:
        print(f"❌ Erro ao acessar banco: {e}")
    
    # 3. Testar o processamento do CSV step by step
    print(f"\n🔧 TESTE: Processamento CSV Step-by-Step")
    print("-" * 40)
    
    try:
        processor = CSVProcessor()
        data_processor = DataProcessor()
        
        # Processar CSV
        raw_data = processor.process(csv_path)
        print(f"✅ CSV processado: {len(raw_data)} registros")
        
        # Validar dados
        validated_data = data_processor.validate_data(raw_data, 'equipment')
        print(f"✅ Dados validados: {len(validated_data)} registros")
        
        # Mostrar primeiros registros validados
        print(f"\n📋 Primeiros 3 registros validados:")
        for i, record in enumerate(validated_data[:3]):
            print(f"   {i+1}. Code: {record.get('code', 'N/A')} - Name: {record.get('name', 'N/A')[:50]}")
        
    except Exception as e:
        print(f"❌ Erro no processamento: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_equipment_loading() 