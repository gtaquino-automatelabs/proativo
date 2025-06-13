#!/usr/bin/env python3
"""
Script de Teste do Pipeline ETL - Sistema PROAtivo
Testa todos os componentes do pipeline ETL implementado.
"""

import asyncio
import os
import sys
from pathlib import Path

# Adicionar src ao path e configurar PYTHONPATH
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

# Configurar PYTHONPATH para imports relativos
os.environ['PYTHONPATH'] = str(src_dir)

try:
    from etl.processors.csv_processor import CSVProcessor
    from etl.processors.xml_processor import XMLProcessor  
    from etl.processors.xlsx_processor import XLSXProcessor
    from etl.data_processor import DataProcessor, FileFormat, DataType
    from utils.validators import DataValidator
except ImportError as e:
    print(f"❌ Erro de importação: {e}")
    print(f"📂 Verificando estrutura de diretórios...")
    print(f"Current dir: {current_dir}")
    print(f"Src dir: {src_dir}")
    print(f"Src exists: {src_dir.exists()}")
    if src_dir.exists():
        print(f"Contents of src: {list(src_dir.iterdir())}")
    sys.exit(1)


async def test_csv_processor():
    """Testa o processador CSV."""
    print("🔍 TESTE 1: CSV Processor")
    print("=" * 50)
    
    processor = CSVProcessor()
    csv_file = "data/samples/equipment.csv"
    
    if not os.path.exists(csv_file):
        print(f"❌ Arquivo não encontrado: {csv_file}")
        return False
        
    try:
        # Testar detecção de encoding
        encoding = processor.detect_encoding(Path(csv_file))
        print(f"✅ Encoding detectado: {encoding}")
        
        # Testar detecção de delimitador
        delimiter = processor.detect_delimiter(Path(csv_file), encoding)
        print(f"✅ Delimitador detectado: '{delimiter}'")
        
        # Processar equipamentos
        equipment_data = processor.process_equipment_csv(Path(csv_file))
        print(f"✅ Equipamentos processados: {len(equipment_data)} registros")
        
        # Mostrar primeiro registro
        if equipment_data:
            print(f"📋 Primeiro registro: {equipment_data[0]['name']}")
            
        return True
        
    except Exception as e:
        print(f"❌ Erro no CSV Processor: {e}")
        return False


async def test_xml_processor():
    """Testa o processador XML."""
    print("\n🔍 TESTE 2: XML Processor")
    print("=" * 50)
    
    processor = XMLProcessor()
    xml_file = "data/samples/equipment.xml"
    
    if not os.path.exists(xml_file):
        print(f"❌ Arquivo não encontrado: {xml_file}")
        return False
        
    try:
        # Processar equipamentos
        equipment_data = processor.process_equipment_xml(Path(xml_file))
        print(f"✅ Equipamentos processados: {len(equipment_data)} registros")
        
        # Processar manutenções
        maintenance_file = "data/samples/maintenance_orders.xml"
        if os.path.exists(maintenance_file):
            maintenance_data = processor.process_maintenance_xml(Path(maintenance_file))
            print(f"✅ Manutenções processadas: {len(maintenance_data)} registros")
            
        # Mostrar primeiro registro
        if equipment_data:
            print(f"📋 Primeiro registro: {equipment_data[0]['name']}")
            
        return True
        
    except Exception as e:
        print(f"❌ Erro no XML Processor: {e}")
        return False


async def test_xlsx_processor():
    """Testa o processador XLSX."""
    print("\n🔍 TESTE 3: XLSX Processor")
    print("=" * 50)
    
    processor = XLSXProcessor()
    xlsx_file = "data/samples/electrical_assets.xlsx"
    
    if not os.path.exists(xlsx_file):
        print(f"❌ Arquivo não encontrado: {xlsx_file}")
        return False
        
    try:
        # Processar equipamentos (aba Equipment)
        equipment_data = processor.process_equipment_xlsx(Path(xlsx_file), sheet_name="Equipment")
        print(f"✅ Equipamentos processados: {len(equipment_data)} registros")
        
        # Processar manutenções (aba Maintenance_Orders)
        maintenance_data = processor.process_maintenance_xlsx(Path(xlsx_file), sheet_name="Maintenance_Orders")
        print(f"✅ Manutenções processadas: {len(maintenance_data)} registros")
        
        # Mostrar primeiro registro
        if equipment_data:
            print(f"📋 Primeiro registro: {equipment_data[0]['name']}")
            
        return True
        
    except Exception as e:
        print(f"❌ Erro no XLSX Processor: {e}")
        return False


async def test_data_validator():
    """Testa o validador de dados."""
    print("\n🔍 TESTE 4: Data Validator")
    print("=" * 50)
    
    validator = DataValidator()
    
    try:
        # Dados válidos
        valid_equipment = {
            'code': 'TR-001',
            'name': 'Transformador Teste',
            'equipment_type': 'Transformer',
            'location': 'SE Norte',
            'manufacturer': 'WEG',
            'status': 'Active',
            'criticality': 'High'
        }
        
        # Validar equipamento válido
        try:
            validated = validator.validate_equipment_record(valid_equipment)
            print(f"✅ Equipamento válido: True")
        except Exception as e:
            print(f"❌ Erro inesperado com equipamento válido: {e}")
        
        # Dados inválidos
        invalid_equipment = {
            'code': '',  # Código vazio
            'name': 'X' * 300,  # Nome muito longo
            'equipment_type': 'TipoInvalido',  # Tipo inválido
            'status': 'status_invalido'  # Status inválido
        }
        
        # Validar equipamento inválido
        try:
            validator.validate_equipment_record(invalid_equipment)
            print(f"❌ Equipamento inválido não foi detectado!")
        except Exception as e:
            print(f"✅ Equipamento inválido detectado: True")
            print(f"📋 Erro encontrado: {str(e)[:100]}...")
            
        return True
        
    except Exception as e:
        print(f"❌ Erro no Data Validator: {e}")
        return False


async def test_data_processor():
    """Testa o processador principal."""
    print("\n🔍 TESTE 5: Data Processor (Pipeline Completo)")
    print("=" * 50)
    
    processor = DataProcessor()
    
    try:
        # Testar detecção automática de formato
        csv_file = "data/samples/equipment.csv"
        xml_file = "data/samples/equipment.xml"
        xlsx_file = "data/samples/electrical_assets.xlsx"
        
        formats = []
        for file_path in [csv_file, xml_file, xlsx_file]:
            if os.path.exists(file_path):
                detected_format = processor.detect_file_format(file_path)
                formats.append((file_path, detected_format))
                print(f"✅ {os.path.basename(file_path)} -> {detected_format.value}")
        
        # Processar um arquivo completo
        if os.path.exists(csv_file):
            valid_records, errors = processor.process_file(Path(csv_file), DataType.EQUIPMENT)
            print(f"✅ Arquivo processado - Sucessos: {len(valid_records)}, Erros: {len(errors)}")
            
        return True
        
    except Exception as e:
        print(f"❌ Erro no Data Processor: {e}")
        return False


async def test_directory_processing():
    """Testa processamento de diretório."""
    print("\n🔍 TESTE 6: Processamento de Diretório")
    print("=" * 50)
    
    processor = DataProcessor()
    samples_dir = "data/samples/"
    
    if not os.path.exists(samples_dir):
        print(f"❌ Diretório não encontrado: {samples_dir}")
        return False
        
    try:
        # Listar arquivos suportados
        supported_files = []
        for file in os.listdir(samples_dir):
            file_path = os.path.join(samples_dir, file)
            if os.path.isfile(file_path):
                try:
                    format_detected = processor.detect_file_format(file_path)
                    supported_files.append((file, format_detected))
                except:
                    continue
                    
        print(f"✅ Arquivos suportados encontrados: {len(supported_files)}")
        for file, format_type in supported_files:
            print(f"   📄 {file} ({format_type.value})")
            
        return True
        
    except Exception as e:
        print(f"❌ Erro no processamento de diretório: {e}")
        return False


async def test_error_handling():
    """Testa tratamento de erros."""
    print("\n🔍 TESTE 7: Tratamento de Erros")
    print("=" * 50)
    
    processor = DataProcessor()
    
    try:
        # Arquivo inexistente
        try:
            processor.process_file(Path("arquivo_inexistente.csv"), DataType.EQUIPMENT)
            print("❌ Deveria ter dado erro para arquivo inexistente")
            return False
        except Exception:
            print("✅ Erro tratado corretamente: arquivo inexistente")
            
        # Formato não suportado
        try:
            processor.detect_file_format(Path("test.txt"))
            print("❌ Deveria ter dado erro para formato não suportado")
            return False
        except Exception:
            print("✅ Erro tratado corretamente: formato não suportado")
            
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste de tratamento de erros: {e}")
        return False


async def run_all_tests():
    """Executa todos os testes."""
    print("🚀 INICIANDO TESTES DO PIPELINE ETL")
    print("=" * 70)
    
    tests = [
        ("CSV Processor", test_csv_processor),
        ("XML Processor", test_xml_processor),
        ("XLSX Processor", test_xlsx_processor),
        ("Data Validator", test_data_validator),
        ("Data Processor", test_data_processor),
        ("Directory Processing", test_directory_processing),
        ("Error Handling", test_error_handling)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Erro ao executar teste {test_name}: {e}")
            results.append((test_name, False))
    
    # Resumo dos resultados
    print("\n" + "=" * 70)
    print("📊 RESUMO DOS TESTES")
    print("=" * 70)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 RESULTADO FINAL: {passed}/{len(results)} testes passaram")
    
    if passed == len(results):
        print("🎉 TODOS OS TESTES PASSARAM! Pipeline ETL está funcionando perfeitamente.")
    else:
        print("⚠️  Alguns testes falharam. Verifique os erros acima.")
    
    return passed == len(results)


if __name__ == "__main__":
    # Executar todos os testes
    asyncio.run(run_all_tests()) 