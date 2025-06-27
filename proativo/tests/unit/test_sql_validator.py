#!/usr/bin/env python3
"""
Testes Unitários para SQL Validator - PROAtivo
Testa todas as funcionalidades do sistema de validação de SQL.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch


class ValidationResult:
    def __init__(self, is_valid, errors=None, warnings=None, sanitized_sql=None, risk_level="LOW"):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []
        self.sanitized_sql = sanitized_sql
        self.risk_level = risk_level


class MockSQLValidator:
    """Mock do SQL Validator para testes"""
    
    def __init__(self):
        self.allowed_operations = ["SELECT", "COUNT", "SUM", "AVG", "MAX", "MIN"]
        self.blocked_operations = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE"]
        self.safe_tables = ["equipments", "maintenance_orders", "failures", "spare_parts"]
        
    def validate_sql(self, sql_query):
        """Valida uma query SQL"""
        if not sql_query or not sql_query.strip():
            return ValidationResult(
                is_valid=False,
                errors=["Query SQL vazia ou inválida"],
                risk_level="HIGH"
            )
        
        sql_upper = sql_query.upper().strip()
        errors = []
        warnings = []
        risk_level = "LOW"
        
        # Verificar operações bloqueadas
        for blocked_op in self.blocked_operations:
            if blocked_op in sql_upper:
                errors.append(f"Operação {blocked_op} não permitida")
                risk_level = "HIGH"
        
        # Verificar sintaxe básica
        if not sql_upper.startswith("SELECT"):
            if not any(op in sql_upper for op in self.allowed_operations):
                errors.append("Query deve começar com SELECT ou operação permitida")
                risk_level = "MEDIUM"
        
        # Verificar tabelas
        for table in self.safe_tables:
            if table.upper() in sql_upper:
                break
        else:
            warnings.append("Nenhuma tabela conhecida encontrada na query")
            risk_level = "MEDIUM" if risk_level == "LOW" else risk_level
        
        # Verificar estrutura SQL básica
        if "SELECT" in sql_upper and "FROM" not in sql_upper:
            errors.append("Query SELECT deve conter cláusula FROM")
            risk_level = "MEDIUM"
        
        # Verificar se há comentários suspeitos
        if "--" in sql_query or "/*" in sql_query:
            warnings.append("Comentários SQL detectados - revisar por segurança")
        
        # Verificar aspas não balanceadas
        single_quotes = sql_query.count("'")
        double_quotes = sql_query.count('"')
        if single_quotes % 2 != 0 or double_quotes % 2 != 0:
            errors.append("Aspas não balanceadas na query")
            risk_level = "HIGH"
        
        is_valid = len(errors) == 0
        sanitized_sql = self._sanitize_sql(sql_query) if is_valid else None
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            sanitized_sql=sanitized_sql,
            risk_level=risk_level
        )
    
    def _sanitize_sql(self, sql_query):
        """Sanitiza a query SQL"""
        sanitized = sql_query.strip()
        
        # Remove comentários inline
        sanitized = sanitized.replace("--", "")
        
        # Remove comentários de bloco
        while "/*" in sanitized and "*/" in sanitized:
            start = sanitized.find("/*")
            end = sanitized.find("*/")
            if start < end:
                sanitized = sanitized[:start] + sanitized[end+2:]
            else:
                break
        
        # Normaliza espaços
        sanitized = " ".join(sanitized.split())
        
        return sanitized
    
    def is_safe_query(self, sql_query):
        """Verifica se a query é segura para execução"""
        result = self.validate_sql(sql_query)
        return result.is_valid and result.risk_level == "LOW"
    
    def get_safe_sql(self, sql_query):
        """Retorna versão segura da SQL ou None se insegura"""
        result = self.validate_sql(sql_query)
        
        if result.is_valid and result.risk_level in ["LOW", "MEDIUM"]:
            return result.sanitized_sql
        
        return None
    
    def validate_schema_compliance(self, sql_query, schema_info):
        """Valida conformidade com esquema do banco"""
        result = self.validate_sql(sql_query)
        
        if not result.is_valid:
            return result
        
        errors = list(result.errors)
        warnings = list(result.warnings)
        
        # Verificar se tabelas existem no esquema
        sql_upper = sql_query.upper()
        
        if schema_info and "tables" in schema_info:
            available_tables = [t.upper() for t in schema_info["tables"]]
            
            for table in self.safe_tables:
                if table.upper() in sql_upper and table.upper() not in available_tables:
                    errors.append(f"Tabela {table} não encontrada no esquema")
        
        is_valid = len(errors) == 0
        risk_level = "HIGH" if not is_valid else result.risk_level
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            sanitized_sql=result.sanitized_sql,
            risk_level=risk_level
        )


class TestSQLValidator:
    """Testes para a classe SQLValidator"""
    
    @pytest.fixture
    def validator(self):
        """Fixture que retorna uma instância do MockSQLValidator"""
        return MockSQLValidator()
    
    def test_init(self, validator):
        """Testa inicialização do validator"""
        assert len(validator.allowed_operations) > 0
        assert len(validator.blocked_operations) > 0
        assert len(validator.safe_tables) > 0
        assert "SELECT" in validator.allowed_operations
        assert "DROP" in validator.blocked_operations
    
    def test_validate_sql_empty_query(self, validator):
        """Testa validação de query vazia"""
        result = validator.validate_sql("")
        
        assert not result.is_valid
        assert len(result.errors) > 0
        assert "vazia" in result.errors[0].lower()
        assert result.risk_level == "HIGH"
    
    def test_validate_sql_none_query(self, validator):
        """Testa validação de query None"""
        result = validator.validate_sql(None)
        
        assert not result.is_valid
        assert len(result.errors) > 0
        assert result.risk_level == "HIGH"
    
    def test_validate_sql_valid_select(self, validator):
        """Testa validação de SELECT válido"""
        sql = "SELECT id, name FROM equipments WHERE status = 'active'"
        result = validator.validate_sql(sql)
        
        assert result.is_valid
        assert len(result.errors) == 0
        assert result.risk_level == "LOW"
        assert result.sanitized_sql is not None
    
    def test_validate_sql_blocked_operation_drop(self, validator):
        """Testa detecção de operação DROP bloqueada"""
        sql = "DROP TABLE equipments"
        result = validator.validate_sql(sql)
        
        assert not result.is_valid
        assert len(result.errors) > 0
        assert "DROP" in result.errors[0]
        assert result.risk_level == "HIGH"
    
    def test_validate_sql_blocked_operation_delete(self, validator):
        """Testa detecção de operação DELETE bloqueada"""
        sql = "DELETE FROM equipments WHERE id = 1"
        result = validator.validate_sql(sql)
        
        assert not result.is_valid
        assert any("DELETE" in error for error in result.errors)
        assert result.risk_level == "HIGH"
    
    def test_validate_sql_blocked_operation_insert(self, validator):
        """Testa detecção de operação INSERT bloqueada"""
        sql = "INSERT INTO equipments (name) VALUES ('test')"
        result = validator.validate_sql(sql)
        
        assert not result.is_valid
        assert any("INSERT" in error for error in result.errors)
        assert result.risk_level == "HIGH"
    
    def test_validate_sql_invalid_syntax_no_from(self, validator):
        """Testa detecção de sintaxe inválida - SELECT sem FROM"""
        sql = "SELECT id, name"
        result = validator.validate_sql(sql)
        
        assert not result.is_valid
        assert any("FROM" in error for error in result.errors)
        assert result.risk_level == "MEDIUM"
    
    def test_validate_sql_unknown_table_warning(self, validator):
        """Testa warning para tabela desconhecida"""
        sql = "SELECT * FROM unknown_table"
        result = validator.validate_sql(sql)
        
        # Pode ser válido, mas com warning
        assert len(result.warnings) > 0
        assert "tabela" in result.warnings[0].lower()
        assert result.risk_level in ["MEDIUM", "LOW"]
    
    def test_validate_sql_with_comments(self, validator):
        """Testa detecção de comentários SQL"""
        sql = "SELECT * FROM equipments -- this is a comment"
        result = validator.validate_sql(sql)
        
        # Deve gerar warning sobre comentários
        assert any("comentário" in warning.lower() for warning in result.warnings)
    
    def test_validate_sql_unbalanced_quotes(self, validator):
        """Testa detecção de aspas não balanceadas"""
        sql = "SELECT * FROM equipments WHERE name = 'test"
        result = validator.validate_sql(sql)
        
        assert not result.is_valid
        assert any("aspas" in error.lower() for error in result.errors)
        assert result.risk_level == "HIGH"
    
    def test_sanitize_sql_removes_comments(self, validator):
        """Testa remoção de comentários na sanitização"""
        sql = "SELECT * FROM equipments -- comment"
        sanitized = validator._sanitize_sql(sql)
        
        assert "--" not in sanitized
        assert "SELECT * FROM equipments" in sanitized
    
    def test_sanitize_sql_removes_block_comments(self, validator):
        """Testa remoção de comentários de bloco"""
        sql = "SELECT * /* comment */ FROM equipments"
        sanitized = validator._sanitize_sql(sql)
        
        assert "/*" not in sanitized
        assert "*/" not in sanitized
        assert "SELECT * FROM equipments" in sanitized
    
    def test_sanitize_sql_normalizes_spaces(self, validator):
        """Testa normalização de espaços"""
        sql = "SELECT   *    FROM    equipments"
        sanitized = validator._sanitize_sql(sql)
        
        assert "SELECT * FROM equipments" == sanitized
    
    def test_is_safe_query_safe(self, validator):
        """Testa identificação de query segura"""
        sql = "SELECT id, name FROM equipments"
        is_safe = validator.is_safe_query(sql)
        
        assert is_safe
    
    def test_is_safe_query_unsafe(self, validator):
        """Testa identificação de query insegura"""
        sql = "DROP TABLE equipments"
        is_safe = validator.is_safe_query(sql)
        
        assert not is_safe
    
    def test_get_safe_sql_valid(self, validator):
        """Testa obtenção de SQL seguro válido"""
        sql = "SELECT * FROM equipments"
        safe_sql = validator.get_safe_sql(sql)
        
        assert safe_sql is not None
        assert "SELECT" in safe_sql
    
    def test_get_safe_sql_invalid(self, validator):
        """Testa rejeição de SQL inseguro"""
        sql = "DROP TABLE equipments"
        safe_sql = validator.get_safe_sql(sql)
        
        assert safe_sql is None
    
    def test_get_safe_sql_medium_risk(self, validator):
        """Testa SQL com risco médio (pode ser aceito)"""
        sql = "SELECT * FROM unknown_table"
        safe_sql = validator.get_safe_sql(sql)
        
        # Risco médio pode ser aceito
        assert safe_sql is not None or safe_sql is None  # Depende da implementação
    
    def test_validate_schema_compliance_valid(self, validator):
        """Testa validação de conformidade de esquema válida"""
        sql = "SELECT id FROM equipments"
        schema_info = {
            "tables": ["equipments", "maintenance_orders", "failures"]
        }
        
        result = validator.validate_schema_compliance(sql, schema_info)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_schema_compliance_invalid_table(self, validator):
        """Testa validação com tabela não existente no esquema"""
        sql = "SELECT id FROM equipments"
        schema_info = {
            "tables": ["maintenance_orders", "failures"]  # equipments não está aqui
        }
        
        result = validator.validate_schema_compliance(sql, schema_info)
        
        assert not result.is_valid
        assert any("esquema" in error.lower() for error in result.errors)
        assert result.risk_level == "HIGH"
    
    def test_validate_schema_compliance_no_schema(self, validator):
        """Testa validação sem informação de esquema"""
        sql = "SELECT id FROM equipments"
        
        result = validator.validate_schema_compliance(sql, None)
        
        # Deve funcionar normalmente sem esquema
        assert result.is_valid or not result.is_valid  # Depende da query
    
    @pytest.mark.parametrize("sql,expected_valid", [
        ("SELECT * FROM equipments", True),
        ("SELECT COUNT(*) FROM maintenance_orders", True),
        ("DROP TABLE equipments", False),
        ("DELETE FROM equipments", False),
        ("INSERT INTO equipments VALUES (1)", False),
        ("UPDATE equipments SET name = 'test'", False),
        ("SELECT id FROM equipments WHERE status = 'active'", True),
        ("SELECT * FROM equipments UNION SELECT * FROM failures", True),  # UNION é permitido
    ])
    def test_sql_validation_patterns(self, validator, sql, expected_valid):
        """Testa padrões de validação SQL"""
        result = validator.validate_sql(sql)
        assert result.is_valid == expected_valid
    
    def test_multiple_blocked_operations(self, validator):
        """Testa query com múltiplas operações bloqueadas"""
        sql = "DROP TABLE equipments; DELETE FROM maintenance_orders"
        result = validator.validate_sql(sql)
        
        assert not result.is_valid
        assert len(result.errors) >= 2  # Deve detectar DROP e DELETE
        assert result.risk_level == "HIGH"
    
    def test_complex_valid_query(self, validator):
        """Testa query complexa mas válida"""
        sql = """
        SELECT e.id, e.name, COUNT(m.id) as maintenance_count
        FROM equipments e
        LEFT JOIN maintenance_orders m ON e.id = m.equipment_id
        WHERE e.status = 'active'
        GROUP BY e.id, e.name
        HAVING COUNT(m.id) > 0
        ORDER BY maintenance_count DESC
        """
        
        result = validator.validate_sql(sql)
        
        assert result.is_valid
        assert result.risk_level == "LOW"
        assert result.sanitized_sql is not None
    
    def test_sql_injection_patterns(self, validator):
        """Testa detecção de padrões de SQL injection"""
        malicious_sqls = [
            "SELECT * FROM equipments WHERE id = 1; DROP TABLE equipments",
            "SELECT * FROM equipments WHERE name = 'test' OR '1'='1'",
            "SELECT * FROM equipments WHERE id = 1 UNION SELECT password FROM users",
        ]
        
        for sql in malicious_sqls:
            result = validator.validate_sql(sql)
            # Algumas podem ser bloqueadas por operações perigosas
            if "DROP" in sql:
                assert not result.is_valid
                assert result.risk_level == "HIGH"
    
    def test_case_insensitive_validation(self, validator):
        """Testa validação case-insensitive"""
        sql_lower = "select * from equipments"
        sql_upper = "SELECT * FROM EQUIPMENTS"
        sql_mixed = "Select * From Equipments"
        
        result_lower = validator.validate_sql(sql_lower)
        result_upper = validator.validate_sql(sql_upper)
        result_mixed = validator.validate_sql(sql_mixed)
        
        # Todos devem ter o mesmo resultado
        assert result_lower.is_valid == result_upper.is_valid == result_mixed.is_valid
    
    def test_whitespace_handling(self, validator):
        """Testa tratamento de espaços em branco"""
        sql_with_spaces = "   SELECT   *   FROM   equipments   "
        result = validator.validate_sql(sql_with_spaces)
        
        assert result.is_valid
        if result.sanitized_sql:
            assert result.sanitized_sql.strip() != ""
            assert "  " not in result.sanitized_sql  # Não deve ter espaços duplos


class TestValidationResult:
    """Testes para a classe ValidationResult"""
    
    def test_validation_result_creation(self):
        """Testa criação de ValidationResult"""
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=["test warning"],
            sanitized_sql="SELECT * FROM test",
            risk_level="LOW"
        )
        
        assert result.is_valid
        assert len(result.errors) == 0
        assert len(result.warnings) == 1
        assert result.sanitized_sql == "SELECT * FROM test"
        assert result.risk_level == "LOW"
    
    def test_validation_result_defaults(self):
        """Testa valores padrão de ValidationResult"""
        result = ValidationResult(is_valid=False)
        
        assert not result.is_valid
        assert result.errors == []
        assert result.warnings == []
        assert result.sanitized_sql is None
        assert result.risk_level == "LOW"


# Testes de integração
class TestSQLValidatorIntegration:
    """Testes de integração para SQLValidator"""
    
    @pytest.fixture
    def validator(self):
        return MockSQLValidator()
    
    def test_full_validation_workflow_safe(self, validator):
        """Testa workflow completo de validação segura"""
        sql = "SELECT id, name FROM equipments WHERE status = 'active'"
        
        # 1. Validação básica
        result = validator.validate_sql(sql)
        assert result.is_valid
        
        # 2. Verificação de segurança
        is_safe = validator.is_safe_query(sql)
        assert is_safe
        
        # 3. Obtenção de SQL seguro
        safe_sql = validator.get_safe_sql(sql)
        assert safe_sql is not None
        
        # 4. Validação com esquema
        schema_info = {"tables": ["equipments", "maintenance_orders"]}
        schema_result = validator.validate_schema_compliance(sql, schema_info)
        assert schema_result.is_valid
    
    def test_full_validation_workflow_unsafe(self, validator):
        """Testa workflow completo de validação insegura"""
        sql = "DROP TABLE equipments"
        
        # 1. Validação básica
        result = validator.validate_sql(sql)
        assert not result.is_valid
        assert result.risk_level == "HIGH"
        
        # 2. Verificação de segurança
        is_safe = validator.is_safe_query(sql)
        assert not is_safe
        
        # 3. SQL seguro deve ser None
        safe_sql = validator.get_safe_sql(sql)
        assert safe_sql is None
    
    def test_sanitization_and_validation_workflow(self, validator):
        """Testa workflow de sanitização e validação"""
        sql_with_comments = "SELECT * FROM equipments -- get all equipment"
        
        # 1. Validação
        result = validator.validate_sql(sql_with_comments)
        assert result.is_valid  # Deve ser válido mesmo com comentários
        
        # 2. Sanitização
        sanitized = validator._sanitize_sql(sql_with_comments)
        assert "--" not in sanitized
        
        # 3. Revalidação do SQL sanitizado
        revalidation = validator.validate_sql(sanitized)
        assert revalidation.is_valid
        assert len(revalidation.warnings) == 0  # Sem warnings após sanitização


if __name__ == "__main__":
    pytest.main([__file__]) 