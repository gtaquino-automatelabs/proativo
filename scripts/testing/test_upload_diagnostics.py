#!/usr/bin/env python3
"""
Script de teste para validar a funcionalidade de diagnóstico de upload.

Este script testa se os componentes de diagnóstico conseguem executar
os testes de upload corretamente.
"""

import sys
import os
from pathlib import Path

# Adicionar o diretório src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_diagnostics_import():
    """Testa se conseguimos importar o sistema de diagnósticos"""
    try:
        from frontend.components.diagnostics import SystemDiagnostics, create_diagnostics_interface
        print("✅ Import do sistema de diagnósticos bem-sucedido")
        return True
    except Exception as e:
        print(f"❌ Erro no import do sistema de diagnósticos: {e}")
        return False

def test_diagnostics_creation():
    """Testa se conseguimos criar uma instância do sistema de diagnósticos"""
    try:
        from frontend.components.diagnostics import SystemDiagnostics
        diagnostics = SystemDiagnostics()
        print("✅ Criação da instância de diagnósticos bem-sucedida")
        return True
    except Exception as e:
        print(f"❌ Erro na criação da instância: {e}")
        return False

def test_upload_tests_method():
    """Testa se o método run_upload_tests existe e pode ser chamado"""
    try:
        from frontend.components.diagnostics import SystemDiagnostics
        diagnostics = SystemDiagnostics()
        
        # Testar com tipo inválido para verificar tratamento de erro
        success, output, details = diagnostics.run_upload_tests("invalid_type")
        
        if not success and details.get("error") == "invalid_test_type":
            print("✅ Método run_upload_tests funciona corretamente (tratamento de erro OK)")
            return True
        else:
            print(f"❌ Comportamento inesperado: success={success}, details={details}")
            return False
            
    except Exception as e:
        print(f"❌ Erro no método run_upload_tests: {e}")
        return False

def test_file_paths():
    """Verifica se os arquivos de teste existem"""
    test_files = [
        "tests/unit/test_upload_performance.py",
        "tests/unit/test_upload_concurrency.py", 
        "tests/unit/test_upload_cleanup.py",
        "tests/integration/test_upload_workflow.py"
    ]
    
    all_exist = True
    for test_file in test_files:
        file_path = Path(__file__).parent.parent / test_file
        if file_path.exists():
            print(f"✅ Arquivo encontrado: {test_file}")
        else:
            print(f"❌ Arquivo não encontrado: {test_file}")
            all_exist = False
    
    return all_exist

def main():
    """Executa todos os testes"""
    print("🔧 Testando funcionalidade de diagnóstico de upload...")
    print("=" * 50)
    
    tests = [
        ("Import do sistema", test_diagnostics_import),
        ("Criação da instância", test_diagnostics_creation),
        ("Método run_upload_tests", test_upload_tests_method),
        ("Arquivos de teste", test_file_paths)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 Executando: {test_name}")
        result = test_func()
        results.append((test_name, result))
    
    print("\n" + "=" * 50)
    print("📊 RESUMO DOS TESTES:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"  {status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Resultado: {passed}/{len(results)} testes passaram")
    
    if passed == len(results):
        print("✅ Todos os testes passaram! A funcionalidade está pronta.")
        return 0
    else:
        print("❌ Alguns testes falharam. Verifique os erros acima.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 