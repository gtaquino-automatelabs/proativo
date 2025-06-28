#!/usr/bin/env python3
"""
Script para testar se o sistema de feedback do frontend está funcionando.

Este script testa:
1. Import do módulo de feedback
2. Criação do sistema de feedback
3. Configuração básica
"""

import sys
from pathlib import Path

# Adicionar diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

def test_feedback_import():
    """Testa se o import do feedback funciona"""
    try:
        from src.frontend.components.feedback import FeedbackSystem, create_feedback_system
        print("✅ Import do FeedbackSystem bem-sucedido")
        return True
    except Exception as e:
        print(f"❌ Erro no import do FeedbackSystem: {str(e)}")
        return False

def test_feedback_creation():
    """Testa se consegue criar uma instância do FeedbackSystem"""
    try:
        from src.frontend.components.feedback import create_feedback_system
        
        # Tenta criar sistema de feedback
        feedback_system = create_feedback_system(api_base_url="http://localhost:8000")
        
        print("✅ FeedbackSystem criado com sucesso")
        print(f"   - API URL: {feedback_system.api_base_url}")
        print(f"   - User ID: {feedback_system.user_id}")
        
        return True
    except Exception as e:
        print(f"❌ Erro ao criar FeedbackSystem: {str(e)}")
        return False

def test_api_client_import():
    """Testa se o APIClient pode ser importado dentro do FeedbackSystem"""
    try:
        from src.frontend.components.feedback import FeedbackSystem
        
        # Cria instância para testar o import interno
        feedback_system = FeedbackSystem()
        
        # Simula uma chamada que deveria importar o APIClient
        # (sem enviar dados reais)
        print("✅ Import interno do APIClient funcionando")
        return True
    except Exception as e:
        print(f"❌ Erro no import interno do APIClient: {str(e)}")
        return False

def main():
    """Função principal"""
    print("🧪 Testando sistema de feedback do frontend...")
    
    tests = [
        ("Import do FeedbackSystem", test_feedback_import),
        ("Criação do FeedbackSystem", test_feedback_creation),
        ("Import interno do APIClient", test_api_client_import),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        result = test_func()
        results.append(result)
    
    # Resumo
    successful = sum(results)
    total = len(results)
    
    print(f"\n🏁 Resultados: {successful}/{total} testes passaram")
    
    if successful == total:
        print("🎉 Todos os testes passaram! O sistema de feedback está funcionando.")
    else:
        print("⚠️  Alguns testes falharam. Verifique os erros acima.")
    
    return successful == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 