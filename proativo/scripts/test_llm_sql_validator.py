#!/usr/bin/env python3
"""
Script de teste para o LLM SQL Validator simplificado.

Testa a validação de queries SQL geradas por LLM com foco em segurança essencial.
"""

import os
import sys
from dotenv import load_dotenv

# Adicionar diretório pai ao PATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.services.llm_sql_validator import LLMSQLValidator, ValidationStatus
from src.utils.logger import get_logger

# Configurar logger
logger = get_logger(__name__)

# Queries de teste organizadas por categoria
TEST_QUERIES = {
    "safe_queries": [
        # Queries básicas seguras
        "SELECT * FROM equipments;",
        "SELECT COUNT(*) FROM maintenances;",
        "SELECT name, type FROM equipments WHERE status = 'Active';",
        
        # Queries com JOINs
        """SELECT e.name, m.maintenance_type 
           FROM equipments e 
           JOIN maintenances m ON e.id = m.equipment_id;""",
        
        # Queries com agregação
        """SELECT equipment_type, COUNT(*) as total 
           FROM equipments 
           GROUP BY equipment_type 
           HAVING COUNT(*) > 1;""",
        
        # Queries com subqueries
        """SELECT name FROM equipments 
           WHERE id IN (SELECT equipment_id FROM maintenances 
                       WHERE status = 'Completed');""",
        
        # Query com CTE
        """WITH active_equipment AS (
               SELECT id, name FROM equipments WHERE status = 'Active'
           )
           SELECT * FROM active_equipment;""",
    ],
    
    "unsafe_queries": [
        # Comandos perigosos óbvios
        "DROP TABLE equipments;",
        "DELETE FROM maintenances WHERE id = 1;",
        "UPDATE equipments SET status = 'Hacked';",
        "INSERT INTO equipments (name) VALUES ('Malicious');",
        
        # SQL Injection attempts
        "SELECT * FROM equipments WHERE id = 1; DROP TABLE users;--",
        "SELECT * FROM equipments WHERE name = '' OR '1'='1' --",
        
        # Comandos misturados
        "SELECT * FROM equipments; DELETE FROM maintenances;",
        
        # Tentativas de bypass
        "SELECT * FROM equipments UNION ALL SELECT * FROM pg_tables;",
    ],
    
    "warning_queries": [
        # Queries válidas mas com avisos
        "SELECT * FROM equipments WHERE (id = 1",  # Parênteses desbalanceados
        "SELECT * FROM equipments WHERE name = 'Test",  # Aspas desbalanceadas
        
        # Query muito complexa
        " ".join([f"SELECT * FROM equipments e{i} JOIN maintenances m{i} ON e{i}.id = m{i}.equipment_id" 
                  for i in range(15)]),  # Muitos JOINs
    ]
}


def test_safe_queries():
    """Testa queries que devem passar na validação."""
    print("\n" + "="*80)
    print("TESTE DE QUERIES SEGURAS")
    print("="*80)
    
    validator = LLMSQLValidator()
    passed = 0
    failed = 0
    
    for i, query in enumerate(TEST_QUERIES["safe_queries"], 1):
        print(f"\n{i}. Testando query segura:")
        print(f"   Query: {query[:100]}{'...' if len(query) > 100 else ''}")
        
        result = validator.validate(query)
        
        if result.is_valid:
            passed += 1
            print(f"   ✅ Status: {result.status.value}")
            if result.warnings:
                print(f"   ⚠️  Avisos: {result.warnings}")
        else:
            failed += 1
            print(f"   ❌ Rejeitada: {result.error}")
    
    print(f"\n📊 Resultado: {passed} passaram, {failed} falharam")
    return passed, failed


def test_unsafe_queries():
    """Testa queries que devem ser bloqueadas."""
    print("\n" + "="*80)
    print("TESTE DE QUERIES PERIGOSAS")
    print("="*80)
    
    validator = LLMSQLValidator()
    blocked = 0
    passed = 0
    
    for i, query in enumerate(TEST_QUERIES["unsafe_queries"], 1):
        print(f"\n{i}. Testando query perigosa:")
        print(f"   Query: {query[:100]}{'...' if len(query) > 100 else ''}")
        
        result = validator.validate(query)
        
        if not result.is_valid:
            blocked += 1
            print(f"   ✅ Bloqueada corretamente: {result.error}")
        else:
            passed += 1
            print(f"   ❌ ERRO: Query perigosa passou na validação!")
    
    print(f"\n📊 Resultado: {blocked} bloqueadas corretamente, {passed} passaram (erro)")
    return blocked, passed


def test_warning_queries():
    """Testa queries que devem gerar avisos."""
    print("\n" + "="*80)
    print("TESTE DE QUERIES COM AVISOS")
    print("="*80)
    
    validator = LLMSQLValidator()
    
    for i, query in enumerate(TEST_QUERIES["warning_queries"], 1):
        print(f"\n{i}. Testando query com possíveis avisos:")
        print(f"   Query: {query[:100]}{'...' if len(query) > 100 else ''}")
        
        result = validator.validate(query)
        
        print(f"   Status: {result.status.value}")
        print(f"   Válida: {result.is_valid}")
        if result.warnings:
            print(f"   ⚠️  Avisos: {result.warnings}")
        if result.error:
            print(f"   ❌ Erro: {result.error}")


def test_helper_methods():
    """Testa métodos auxiliares do validador."""
    print("\n" + "="*80)
    print("TESTE DE MÉTODOS AUXILIARES")
    print("="*80)
    
    validator = LLMSQLValidator()
    
    # Teste is_read_only
    print("\n1. Testando is_read_only():")
    test_cases = [
        ("SELECT * FROM equipments", True),
        ("DELETE FROM equipments", False),
        ("", False)
    ]
    
    for query, expected in test_cases:
        result = validator.is_read_only(query)
        status = "✅" if result == expected else "❌"
        print(f"   {status} '{query[:30]}...' -> {result} (esperado: {expected})")
    
    # Teste get_safe_query
    print("\n2. Testando get_safe_query():")
    query = "SELECT * FROM equipments WHERE status = 'Active'"
    safe_query = validator.get_safe_query(query)
    print(f"   Query original: {query}")
    print(f"   Query limpa: {safe_query}")
    
    # Teste explain_rejection
    print("\n3. Testando explain_rejection():")
    bad_query = "DROP TABLE equipments;"
    explanation = validator.explain_rejection(bad_query)
    print(f"   Query: {bad_query}")
    print(f"   Explicação: {explanation}")


def test_real_llm_queries():
    """Testa com queries reais que o LLM geraria."""
    print("\n" + "="*80)
    print("TESTE COM QUERIES TÍPICAS DO LLM")
    print("="*80)
    
    validator = LLMSQLValidator()
    
    # Queries que o LLM SQL Generator produziria
    llm_queries = [
        "SELECT COUNT(*) AS total FROM equipments WHERE type = 'Transformer';",
        "SELECT name, type, location FROM equipments WHERE status = 'Maintenance' ORDER BY name;",
        """SELECT e.name, m.maintenance_date, m.maintenance_type, m.description 
           FROM equipments e 
           JOIN maintenances m ON e.id = m.equipment_id 
           WHERE e.name = 'T001' 
           ORDER BY m.maintenance_date DESC 
           LIMIT 1;""",
        "SELECT COUNT(*) AS total FROM maintenances WHERE EXTRACT(YEAR FROM maintenance_date) = EXTRACT(YEAR FROM CURRENT_DATE);",
    ]
    
    all_valid = True
    
    for i, query in enumerate(llm_queries, 1):
        print(f"\n{i}. Query típica do LLM:")
        result = validator.validate(query)
        
        if result.is_valid:
            print(f"   ✅ Válida (status: {result.status.value})")
        else:
            print(f"   ❌ Rejeitada: {result.error}")
            all_valid = False
    
    if all_valid:
        print("\n✅ Todas as queries típicas do LLM passaram!")
    else:
        print("\n❌ Algumas queries do LLM foram rejeitadas incorretamente")


def main():
    """Função principal."""
    # Carregar variáveis de ambiente
    load_dotenv()
    
    print("\n🔒 INICIANDO TESTES DO LLM SQL VALIDATOR\n")
    
    # Executar todos os testes
    safe_passed, safe_failed = test_safe_queries()
    unsafe_blocked, unsafe_passed = test_unsafe_queries()
    test_warning_queries()
    test_helper_methods()
    test_real_llm_queries()
    
    # Resumo final
    print("\n" + "="*80)
    print("RESUMO DOS TESTES")
    print("="*80)
    
    total_tests = (safe_passed + safe_failed + unsafe_blocked + unsafe_passed)
    successful = safe_passed + unsafe_blocked
    
    print(f"Total de testes: {total_tests}")
    print(f"✅ Sucessos: {successful}")
    print(f"❌ Falhas: {safe_failed + unsafe_passed}")
    print(f"Taxa de sucesso: {(successful/total_tests*100):.1f}%")
    
    print("\n💡 OBSERVAÇÕES:")
    print("- Validador focado em segurança essencial")
    print("- Apenas SELECT statements permitidos")
    print("- Detecção de SQL injection básica")
    print("- Avisos para queries complexas mas não bloqueio")
    print("- Otimizado para queries geradas por LLM")


if __name__ == "__main__":
    main() 