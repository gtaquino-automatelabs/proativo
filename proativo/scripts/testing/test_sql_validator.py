#!/usr/bin/env python3
"""
Script para testar o validador SQL e identificar onde está sendo muito restritivo.
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

from src.api.services.sql_validator import SQLValidator, SQLSecurityLevel


def test_simple_queries():
    """Testa queries simples que deveriam passar."""
    print("=== TESTE QUERIES SIMPLES ===")
    
    validator = SQLValidator(SQLSecurityLevel.STRICT)
    
    simple_queries = [
        "SELECT * FROM equipments",
        "SELECT id, name FROM equipments WHERE status = 'Active'",
        "SELECT COUNT(*) FROM maintenances",
        "SELECT e.name, m.description FROM equipments e JOIN maintenances m ON e.id = m.equipment_id",
        "SELECT * FROM equipments ORDER BY name LIMIT 10;"
    ]
    
    for query in simple_queries:
        print(f"\n🔍 Testando: {query}")
        try:
            result = validator.validate_sql(query)
            print(f"   ✅ Resultado: {result.validation_result.value}")
            if result.issues_found:
                print(f"   ⚠️  Issues: {result.issues_found}")
        except Exception as e:
            print(f"   ❌ Erro: {e}")


def test_complex_queries():
    """Testa queries mais complexas."""
    print("\n=== TESTE QUERIES COMPLEXAS ===")
    
    validator = SQLValidator(SQLSecurityLevel.STRICT)
    
    complex_queries = [
        """
        SELECT e.name, e.equipment_type, m.maintenance_type, m.status
        FROM equipments e 
        LEFT JOIN maintenances m ON e.id = m.equipment_id 
        WHERE e.criticality = 'High' 
        AND m.status IN ('Planned', 'InProgress')
        ORDER BY e.name, m.scheduled_date
        """,
        """
        SELECT equipment_type, COUNT(*) as total,
               AVG(CASE WHEN status = 'Active' THEN 1 ELSE 0 END) as active_rate
        FROM equipments 
        GROUP BY equipment_type
        HAVING COUNT(*) > 1
        ORDER BY total DESC
        """
    ]
    
    for query in complex_queries:
        print(f"\n🔍 Testando query complexa...")
        try:
            result = validator.validate_sql(query)
            print(f"   ✅ Resultado: {result.validation_result.value}")
            print(f"   📊 Complexidade: {result.complexity_score}")
            if result.issues_found:
                print(f"   ⚠️  Issues: {result.issues_found}")
        except Exception as e:
            print(f"   ❌ Erro: {e}")


def test_different_security_levels():
    """Testa diferentes níveis de segurança."""
    print("\n=== TESTE NÍVEIS DE SEGURANÇA ===")
    
    test_query = """
    SELECT e.name, e.equipment_type, m.maintenance_type 
    FROM equipments e 
    JOIN maintenances m ON e.id = m.equipment_id 
    JOIN data_history d ON e.id = d.equipment_id
    WHERE e.criticality = 'High' 
    AND m.status = 'Planned'
    AND d.timestamp > '2024-01-01'
    ORDER BY e.name
    """
    
    for level in [SQLSecurityLevel.STRICT, SQLSecurityLevel.MODERATE, SQLSecurityLevel.PERMISSIVE]:
        print(f"\n🔒 Nível: {level.value}")
        validator = SQLValidator(level)
        
        try:
            result = validator.validate_sql(test_query)
            print(f"   ✅ Resultado: {result.validation_result.value}")
            print(f"   📊 Issues: {len(result.issues_found)}")
            if result.issues_found:
                for issue in result.issues_found[:3]:  # Mostra apenas os primeiros 3
                    print(f"      - {issue}")
        except Exception as e:
            print(f"   ❌ Erro: {e}")


def test_table_validation():
    """Testa validação de tabelas."""
    print("\n=== TESTE VALIDAÇÃO DE TABELAS ===")
    
    validator = SQLValidator(SQLSecurityLevel.MODERATE)
    
    queries_with_tables = [
        "SELECT * FROM equipments",  # Deveria funcionar
        "SELECT * FROM maintenances",  # Deveria funcionar
        "SELECT * FROM data_history",  # Pode não funcionar - teste
        "SELECT * FROM equipment",  # Nome antigo - pode não funcionar
        "SELECT * FROM maintenance_orders",  # Nome antigo - pode não funcionar
    ]
    
    for query in queries_with_tables:
        print(f"\n🔍 Testando: {query}")
        try:
            result = validator.validate_sql(query)
            print(f"   ✅ Resultado: {result.validation_result.value}")
            print(f"   📋 Tabelas detectadas: {result.tables_accessed}")
            if result.issues_found:
                table_issues = [issue for issue in result.issues_found if "Tabela" in issue]
                if table_issues:
                    print(f"   ⚠️  Issues de tabela: {table_issues}")
        except Exception as e:
            print(f"   ❌ Erro: {e}")


if __name__ == "__main__":
    test_simple_queries()
    test_complex_queries()
    test_different_security_levels()
    test_table_validation() 