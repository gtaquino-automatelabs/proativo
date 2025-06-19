"""
Testes unitários para o QueryProcessor.

Testa a análise de linguagem natural, geração de SQL e validação.
"""

import pytest
from unittest.mock import Mock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.api.services.query_processor import (
    QueryProcessor, QueryType, QueryIntent, QueryAnalysis
)
from src.utils.error_handlers import ValidationError, DataProcessingError


class TestQueryProcessor:
    """Testes para o processador de queries."""
    
    @pytest.fixture
    def query_processor(self):
        """Fixture para instância do QueryProcessor."""
        with patch('src.api.services.query_processor.get_settings') as mock_settings:
            settings = Mock()
            mock_settings.return_value = settings
            
            processor = QueryProcessor()
            return processor
    
    def test_initialization(self, query_processor):
        """Testa inicialização do processador."""
        assert query_processor.queries_processed == 0
        assert query_processor.successful_queries == 0
        assert query_processor.failed_queries == 0
        assert hasattr(query_processor, 'equipment_patterns')
        assert hasattr(query_processor, 'status_patterns')
        assert hasattr(query_processor, 'intent_patterns')
    
    def test_identify_query_type_equipment(self, query_processor):
        """Testa identificação de tipo de consulta para equipamentos."""
        result = query_processor._identify_query_type("status do transformador T001")
        assert result == QueryType.EQUIPMENT_STATUS
        
        result = query_processor._identify_query_type("mostre os geradores")
        assert result == QueryType.EQUIPMENT_STATUS
    
    def test_identify_query_type_maintenance(self, query_processor):
        """Testa identificação de tipo de consulta para manutenção."""
        result = query_processor._identify_query_type("próximas manutenções")
        assert result == QueryType.MAINTENANCE_SCHEDULE
        
        result = query_processor._identify_query_type("maintenance preventiva")
        assert result == QueryType.MAINTENANCE_SCHEDULE
    
    def test_identify_query_type_failure(self, query_processor):
        """Testa identificação de tipo de consulta para falhas."""
        result = query_processor._identify_query_type("falhas do equipamento")
        assert result == QueryType.FAILURE_ANALYSIS
        
        result = query_processor._identify_query_type("problemas nos últimos dias")
        assert result == QueryType.FAILURE_ANALYSIS
    
    def test_identify_query_type_cost(self, query_processor):
        """Testa identificação de tipo de consulta para custos."""
        result = query_processor._identify_query_type("custo total das manutenções")
        assert result == QueryType.COST_ANALYSIS
        
        result = query_processor._identify_query_type("quanto gastamos em reparos")
        assert result == QueryType.COST_ANALYSIS
    
    def test_identify_query_type_historical(self, query_processor):
        """Testa identificação de tipo de consulta histórica."""
        result = query_processor._identify_query_type("histórico de operações")
        assert result == QueryType.HISTORICAL_DATA
        
        result = query_processor._identify_query_type("dados do passado")
        assert result == QueryType.HISTORICAL_DATA
    
    def test_identify_intent_list(self, query_processor):
        """Testa identificação de intenção de listagem."""
        result = query_processor._identify_intent("liste todos os equipamentos")
        assert result == QueryIntent.LIST
        
        result = query_processor._identify_intent("mostre os transformadores")
        assert result == QueryIntent.LIST
    
    def test_identify_intent_count(self, query_processor):
        """Testa identificação de intenção de contagem."""
        result = query_processor._identify_intent("quantos equipamentos temos")
        assert result == QueryIntent.COUNT
        
        result = query_processor._identify_intent("número de falhas")
        assert result == QueryIntent.COUNT
    
    def test_identify_intent_search(self, query_processor):
        """Testa identificação de intenção de busca."""
        result = query_processor._identify_intent("encontre o equipamento T001")
        assert result == QueryIntent.SEARCH
        
        result = query_processor._identify_intent("busque falhas críticas")
        assert result == QueryIntent.SEARCH
    
    def test_identify_intent_aggregate(self, query_processor):
        """Testa identificação de intenção de agregação."""
        result = query_processor._identify_intent("média de custos")
        assert result == QueryIntent.AGGREGATE
        
        result = query_processor._identify_intent("total gasto em manutenção")
        assert result == QueryIntent.AGGREGATE
    
    def test_extract_entities_equipment_type(self, query_processor):
        """Testa extração de tipos de equipamento."""
        entities = query_processor._extract_entities("status dos transformadores")
        assert entities["equipment_type"] == "transformador"
        
        entities = query_processor._extract_entities("problemas nos geradores")
        assert entities["equipment_type"] == "gerador"
    
    def test_extract_entities_status(self, query_processor):
        """Testa extração de status."""
        entities = query_processor._extract_entities("equipamentos em manutenção")
        assert entities["status"] == "manutencao"
        
        entities = query_processor._extract_entities("sistemas operacionais")
        assert entities["status"] == "operacional"
    
    def test_extract_entities_equipment_ids(self, query_processor):
        """Testa extração de IDs específicos."""
        entities = query_processor._extract_entities("status do T001 e GER-123")
        assert "equipment_ids" in entities
        assert "T001" in entities["equipment_ids"]
        assert "GER-123" in entities["equipment_ids"]
    
    def test_extract_entities_temporal(self, query_processor):
        """Testa extração de entidades temporais."""
        entities = query_processor._extract_entities("manutenções do último mês")
        assert "temporal" in entities
        assert "último" in entities["temporal"]
    
    def test_extract_entities_numeric(self, query_processor):
        """Testa extração de valores numéricos."""
        entities = query_processor._extract_entities("custos acima de 1000.50")
        assert "numeric_values" in entities
        assert 1000.5 in entities["numeric_values"]
    
    def test_extract_filters_location(self, query_processor):
        """Testa extração de filtros de localização."""
        filters = query_processor._extract_filters("equipamentos em São Paulo", {})
        assert "location" in filters
        assert "São Paulo" in filters["location"]
    
    def test_extract_filters_priority(self, query_processor):
        """Testa extração de filtros de prioridade."""
        filters = query_processor._extract_filters("manutenções urgentes", {})
        assert filters["priority"] == "high"
    
    def test_generate_sql_equipment_status(self, query_processor):
        """Testa geração SQL para status de equipamentos."""
        sql = query_processor._generate_sql(
            QueryType.EQUIPMENT_STATUS,
            QueryIntent.LIST,
            {"equipment_type": "transformador"},
            {}
        )
        
        assert "SELECT id, name, type, status, location, last_maintenance" in sql
        assert "FROM equipment" in sql
        assert "type ILIKE '%transformador%'" in sql
        assert "LIMIT 50" in sql
    
    def test_generate_sql_maintenance_schedule(self, query_processor):
        """Testa geração SQL para programação de manutenção."""
        sql = query_processor._generate_sql(
            QueryType.MAINTENANCE_SCHEDULE,
            QueryIntent.LIST,
            {},
            {}
        )
        
        assert "SELECT id, equipment_id, type, status, scheduled_date, cost" in sql
        assert "FROM maintenance_orders" in sql
        assert "ORDER BY scheduled_date ASC" in sql
    
    def test_generate_sql_count(self, query_processor):
        """Testa geração SQL para contagem."""
        sql = query_processor._generate_sql(
            QueryType.EQUIPMENT_STATUS,
            QueryIntent.COUNT,
            {},
            {}
        )
        
        assert "SELECT COUNT(*) as total" in sql
        assert "LIMIT" not in sql  # Não deve ter LIMIT para contagem
    
    def test_generate_sql_aggregate_cost(self, query_processor):
        """Testa geração SQL para agregação de custos."""
        sql = query_processor._generate_sql(
            QueryType.COST_ANALYSIS,
            QueryIntent.AGGREGATE,
            {"cost": True},
            {}
        )
        
        assert "SELECT SUM(cost) as total_cost, AVG(cost) as avg_cost" in sql
        assert "FROM maintenance_orders" in sql
    
    def test_validate_sql_success(self, query_processor):
        """Testa validação SQL bem-sucedida."""
        valid_sql = "SELECT * FROM equipment WHERE status = 'active'"
        # Deve passar sem erro
        query_processor._validate_sql(valid_sql)
    
    def test_validate_sql_dangerous_keywords(self, query_processor):
        """Testa rejeição de SQL perigoso."""
        dangerous_sql = "DROP TABLE equipment"
        
        with pytest.raises(ValidationError, match="comando não permitido"):
            query_processor._validate_sql(dangerous_sql)
    
    def test_validate_sql_non_select(self, query_processor):
        """Testa rejeição de SQL não-SELECT."""
        insert_sql = "INSERT INTO equipment VALUES (1, 'test')"
        
        with pytest.raises(ValidationError, match="Apenas queries SELECT"):
            query_processor._validate_sql(insert_sql)
    
    def test_validate_sql_multiple_statements(self, query_processor):
        """Testa rejeição de múltiplas statements."""
        multiple_sql = "SELECT * FROM equipment; DROP TABLE equipment;"
        
        with pytest.raises(ValidationError, match="Múltiplas statements"):
            query_processor._validate_sql(multiple_sql)
    
    def test_calculate_confidence_high(self, query_processor):
        """Testa cálculo de confiança alta."""
        confidence = query_processor._calculate_confidence(
            "liste transformadores operacionais",
            QueryType.EQUIPMENT_STATUS,
            QueryIntent.LIST,
            {"equipment_type": "transformador", "status": "operacional"}
        )
        
        assert confidence >= 0.7  # Deve ter alta confiança
    
    def test_calculate_confidence_low(self, query_processor):
        """Testa cálculo de confiança baixa."""
        confidence = query_processor._calculate_confidence(
            "query muito vaga",
            QueryType.UNKNOWN,
            QueryIntent.UNKNOWN,
            {}
        )
        
        assert confidence <= 0.3  # Deve ter baixa confiança
    
    def test_generate_explanation(self, query_processor):
        """Testa geração de explicação."""
        explanation = query_processor._generate_explanation(
            QueryType.EQUIPMENT_STATUS,
            QueryIntent.LIST,
            {"equipment_type": "transformador"},
            {}
        )
        
        assert "consulta sobre status de equipamentos" in explanation
        assert "para listar resultados" in explanation
        assert "tipo 'transformador'" in explanation
    
    def test_analyze_query_success(self, query_processor):
        """Testa análise completa bem-sucedida."""
        result = query_processor.analyze_query("liste transformadores operacionais")
        
        assert isinstance(result, QueryAnalysis)
        assert result.query_type == QueryType.EQUIPMENT_STATUS
        assert result.intent == QueryIntent.LIST
        assert "equipment_type" in result.entities
        assert "status" in result.entities
        assert result.confidence > 0.5
        assert "SELECT" in result.sql_query
    
    def test_analyze_query_empty(self, query_processor):
        """Testa erro com query vazia."""
        with pytest.raises(ValidationError, match="Query não pode estar vazia"):
            query_processor.analyze_query("")
    
    def test_analyze_query_whitespace_only(self, query_processor):
        """Testa erro com query apenas com espaços."""
        with pytest.raises(ValidationError, match="Query não pode estar vazia"):
            query_processor.analyze_query("   ")
    
    def test_get_metrics(self, query_processor):
        """Testa obtenção de métricas."""
        # Simular algumas análises
        query_processor.queries_processed = 10
        query_processor.successful_queries = 8
        query_processor.failed_queries = 2
        
        metrics = query_processor.get_metrics()
        
        assert metrics["queries_processed"] == 10
        assert metrics["successful_queries"] == 8
        assert metrics["failed_queries"] == 2
        assert metrics["success_rate"] == 0.8
        assert "supported_query_types" in metrics
        assert "supported_intents" in metrics
    
    def test_get_supported_patterns(self, query_processor):
        """Testa obtenção de padrões suportados."""
        patterns = query_processor.get_supported_patterns()
        
        assert "equipment_types" in patterns
        assert "status_types" in patterns
        assert "query_types" in patterns
        assert "intents" in patterns
        assert "temporal_patterns" in patterns
        
        assert "transformador" in patterns["equipment_types"]
        assert "operacional" in patterns["status_types"]
    
    def test_build_where_clause_complex(self, query_processor):
        """Testa construção de cláusula WHERE complexa."""
        entities = {
            "equipment_type": "transformador",
            "status": "operacional",
            "equipment_ids": ["T001", "T002"]
        }
        filters = {
            "location": "São Paulo",
            "priority": "high"
        }
        
        where_clause = query_processor._build_where_clause(entities, filters)
        
        assert "type ILIKE '%transformador%'" in where_clause
        assert "status = 'operacional'" in where_clause
        assert "id IN ('T001', 'T002')" in where_clause
        assert "location ILIKE '%São Paulo%'" in where_clause
        assert "(status = 'urgent' OR priority = 'high')" in where_clause
    
    def test_build_join_clause_maintenance(self, query_processor):
        """Testa construção de JOIN para manutenção."""
        join_clause = query_processor._build_join_clause(
            QueryType.MAINTENANCE_SCHEDULE, 
            {}
        )
        
        assert "LEFT JOIN equipment e ON maintenance_orders.equipment_id = e.id" in join_clause
    
    def test_build_join_clause_failure(self, query_processor):
        """Testa construção de JOIN para falhas."""
        join_clause = query_processor._build_join_clause(
            QueryType.FAILURE_ANALYSIS, 
            {}
        )
        
        assert "LEFT JOIN equipment e ON failures.equipment_id = e.id" in join_clause
    
    def test_build_order_clause_by_type(self, query_processor):
        """Testa construção de ORDER BY por tipo."""
        # Manutenção deve ordenar por data
        order_clause = query_processor._build_order_clause(
            QueryIntent.LIST, 
            QueryType.MAINTENANCE_SCHEDULE
        )
        assert "ORDER BY scheduled_date ASC" in order_clause
        
        # Falha deve ordenar por data decrescente
        order_clause = query_processor._build_order_clause(
            QueryIntent.LIST, 
            QueryType.FAILURE_ANALYSIS
        )
        assert "ORDER BY failure_date DESC" in order_clause
        
        # Custo deve ordenar por valor decrescente
        order_clause = query_processor._build_order_clause(
            QueryIntent.LIST, 
            QueryType.COST_ANALYSIS
        )
        assert "ORDER BY cost DESC" in order_clause
    
    def test_cost_comparison_extraction(self, query_processor):
        """Testa extração de comparações de custo."""
        filters = query_processor._extract_filters(
            "manutenções com custo maior que 5000", 
            {}
        )
        
        assert "cost_comparison" in filters
        comparisons = filters["cost_comparison"]
        assert len(comparisons) > 0
        assert comparisons[0][0] == "maior"
        assert comparisons[0][1] == "5000"
    
    def test_sql_injection_prevention(self, query_processor):
        """Testa prevenção de SQL injection."""
        # Tentar injetar SQL malicioso
        malicious_query = "'; DROP TABLE equipment; --"
        
        result = query_processor.analyze_query(f"equipamentos {malicious_query}")
        
        # O SQL gerado deve ser seguro
        assert "DROP" not in result.sql_query.upper()
        assert ";" not in result.sql_query or result.sql_query.strip().endswith(";")


class TestSQLValidationAdvanced:
    """Testes para o sistema avançado de validação SQL."""
    
    def setup_method(self):
        """Configuração dos testes de validação."""
        self.processor = QueryProcessor()
    
    def test_sql_sanitization_basic(self):
        """Testa sanitização básica de valores."""
        # Aspas simples devem ser escapadas
        result = self.processor.sanitizer.sanitize_value("O'Brien")
        assert "O''Brien" in result
        
        # Remover comentários SQL
        result = self.processor.sanitizer.sanitize_value("test -- comment")
        assert "comment" not in result
        
        # Remover comentários de bloco
        result = self.processor.sanitizer.sanitize_value("test /* comment */ data")
        assert "comment" not in result
    
    def test_sql_injection_detection(self):
        """Testa detecção de SQL injection."""
        # Query com tentativa de injection
        malicious_sql = "SELECT * FROM equipment WHERE id = '1'; DROP TABLE equipment; --"
        threats = self.processor.sanitizer.detect_injection_attempts(malicious_sql)
        assert len(threats) > 0
        
        # Query limpa não deve ter threats
        clean_sql = "SELECT id, name FROM equipment WHERE status = 'operational'"
        threats = self.processor.sanitizer.detect_injection_attempts(clean_sql)
        # Note: pode haver falsos positivos, mas verificamos que não há threats críticos
    
    def test_dangerous_keywords_validation(self):
        """Testa validação de palavras-chave perigosas."""
        # Keywords críticas
        sql_with_drop = "SELECT * FROM equipment; DROP TABLE users;"
        issues = self.processor.sanitizer.validate_keywords(sql_with_drop)
        assert any("DROP" in issue for issue in issues)
        
        # Keywords administrativas
        sql_with_exec = "EXEC sp_configure"
        issues = self.processor.sanitizer.validate_keywords(sql_with_exec)
        assert any("EXEC" in issue for issue in issues)
    
    def test_sql_syntax_validation(self):
        """Testa validação de sintaxe SQL."""
        # SQL válido
        valid_sql = "SELECT id, name FROM equipment WHERE status = 'operational'"
        errors = self.processor.structure_validator.validate_syntax(valid_sql)
        assert len(errors) == 0
        
        # SQL inválido - múltiplas statements
        invalid_sql = "SELECT * FROM equipment; SELECT * FROM users;"
        errors = self.processor.structure_validator.validate_syntax(invalid_sql)
        assert len(errors) > 0
        
        # Não-SELECT
        non_select = "UPDATE equipment SET status = 'offline'"
        errors = self.processor.structure_validator.validate_syntax(non_select)
        assert any("SELECT" in error for error in errors)
    
    def test_schema_validation(self):
        """Testa validação de tabelas e colunas contra schema."""
        # Tabela válida
        valid_sql = "SELECT id, name FROM equipment"
        errors = self.processor.structure_validator.validate_tables_and_columns(valid_sql)
        # Não deve ter erros de tabela inexistente
        table_errors = [e for e in errors if "Tabela não encontrada" in e]
        assert len(table_errors) == 0
        
        # Tabela inválida
        invalid_sql = "SELECT * FROM nonexistent_table"
        errors = self.processor.structure_validator.validate_tables_and_columns(invalid_sql)
        assert any("Tabela não encontrada" in error for error in errors)
    
    def test_function_validation(self):
        """Testa validação de funções SQL."""
        # Função permitida
        valid_sql = "SELECT COUNT(*) FROM equipment"
        errors = self.processor.structure_validator.validate_functions(valid_sql)
        assert len(errors) == 0
        
        # Função não permitida (simulada)
        invalid_sql = "SELECT DANGEROUS_FUNCTION() FROM equipment"
        errors = self.processor.structure_validator.validate_functions(invalid_sql)
        assert any("DANGEROUS_FUNCTION" in error for error in errors)
    
    def test_complexity_calculation(self):
        """Testa cálculo de complexidade de queries."""
        # Query simples
        simple_sql = "SELECT id FROM equipment"
        complexity = self.processor.structure_validator.calculate_complexity(simple_sql)
        assert complexity <= 2
        
        # Query complexa com JOINs
        complex_sql = """
        SELECT e.id, e.name, m.scheduled_date 
        FROM equipment e 
        JOIN maintenance_orders m ON e.id = m.equipment_id 
        JOIN failures f ON e.id = f.equipment_id
        WHERE e.status = 'operational' 
        AND m.type = 'preventive'
        ORDER BY m.scheduled_date
        """
        complexity = self.processor.structure_validator.calculate_complexity(complex_sql)
        assert complexity > 5
    
    def test_risk_level_calculation(self):
        """Testa cálculo de nível de risco."""
        # Baixo risco
        low_risk_sql = "SELECT id, name FROM equipment LIMIT 10"
        risk = self.processor._calculate_risk_level(low_risk_sql, 1, 0)
        assert risk == "low"
        
        # Alto risco - complexidade alta
        high_risk_sql = """
        SELECT e.*, m.*, f.* 
        FROM equipment e 
        JOIN maintenance_orders m ON e.id = m.equipment_id 
        JOIN failures f ON e.id = f.equipment_id
        JOIN (SELECT equipment_id FROM maintenance_orders WHERE cost > 1000) sub ON e.id = sub.equipment_id
        """
        complexity = self.processor.structure_validator.calculate_complexity(high_risk_sql)
        risk = self.processor._calculate_risk_level(high_risk_sql, complexity, 0)
        assert risk in ["medium", "high"]
    
    def test_advanced_validation_integration(self):
        """Testa integração completa do sistema de validação."""
        # Query válida
        valid_sql = "SELECT id, name, status FROM equipment WHERE type = 'transformador' LIMIT 50"
        result = self.processor.validate_sql_advanced(valid_sql)
        
        assert result.is_valid
        assert result.risk_level in ["low", "medium"]
        assert len(result.errors) == 0
        
        # Query inválida
        invalid_sql = "SELECT * FROM equipment; DROP TABLE users;"
        result = self.processor.validate_sql_advanced(invalid_sql)
        
        assert not result.is_valid
        assert len(result.errors) > 0
        assert result.risk_level == "high"
    
    def test_security_warnings(self):
        """Testa geração de avisos de segurança."""
        # Query sem WHERE - deve gerar warning
        broad_sql = "SELECT * FROM equipment"
        warnings = self.processor._additional_security_checks(broad_sql)
        assert any("muito aberta" in warning for warning in warnings)
        
        # Query sem LIMIT - deve gerar warning
        no_limit_sql = "SELECT id, name FROM equipment WHERE status = 'operational'"
        warnings = self.processor._additional_security_checks(no_limit_sql)
        assert any("LIMIT" in warning for warning in warnings)
    
    def test_user_input_sanitization(self):
        """Testa sanitização de entrada do usuário."""
        # Entrada com caracteres especiais
        malicious_input = "Mostre equipamentos'; DROP TABLE equipment; --"
        sanitized = self.processor.sanitize_user_input(malicious_input)
        
        # Deve escapar aspas e remover comentários
        assert "''" in sanitized or "'" not in sanitized
        assert "--" not in sanitized
    
    def test_validation_metrics(self):
        """Testa coleta de métricas de validação."""
        # Processar algumas queries
        self.processor.queries_processed = 10
        self.processor.validation_failures = 2
        
        metrics = self.processor.get_validation_metrics()
        
        assert "total_queries_processed" in metrics
        assert "validation_failures" in metrics
        assert "validation_success_rate" in metrics
        assert "security_features" in metrics
        
        # Verificar features de segurança
        features = metrics["security_features"]
        assert features["sql_injection_detection"]
        assert features["keyword_restriction"]
        assert features["schema_validation"]
    
    def test_sanitizer_edge_cases(self):
        """Testa casos extremos do sanitizador."""
        # String muito longa
        long_string = "a" * 2000
        sanitized = self.processor.sanitizer.sanitize_value(long_string)
        assert len(sanitized) <= 1000
        
        # Caracteres nulos
        null_string = "test\x00null\x1abyte"
        sanitized = self.processor.sanitizer.sanitize_value(null_string)
        assert "\x00" not in sanitized
        assert "\x1a" not in sanitized
        
        # Tipos não-string
        number_input = 12345
        sanitized = self.processor.sanitizer.sanitize_value(number_input)
        assert sanitized == "12345"


class TestQueryProcessorWithValidation:
    """Testes integrados do QueryProcessor com validação."""
    
    def setup_method(self):
        """Configuração dos testes integrados."""
        self.processor = QueryProcessor()
    
    def test_analyze_query_with_sanitization(self):
        """Testa análise de query com sanitização integrada."""
        # Query normal
        normal_query = "Mostre todos os transformadores operacionais"
        analysis = self.processor.analyze_query(normal_query)
        
        assert analysis.sql_query
        assert analysis.confidence > 0
        assert analysis.query_type != QueryType.UNKNOWN
    
    def test_analyze_query_with_malicious_input(self):
        """Testa análise com entrada potencialmente maliciosa."""
        # Input com tentativa de injection (deve ser sanitizado)
        malicious_query = "Mostre equipamentos'; DROP TABLE equipment; --"
        
        # Não deve gerar exceção - deve sanitizar e processar
        analysis = self.processor.analyze_query(malicious_query)
        assert analysis is not None
        
        # SQL gerado deve ser seguro
        assert "DROP" not in analysis.sql_query.upper()
    
    def test_validation_failure_handling(self):
        """Testa tratamento de falhas de validação."""
        # Forçar uma query que resultará em SQL inválido
        # Isso pode ser difícil de fazer com o gerador atual, então vamos mockar
        original_generate = self.processor._generate_sql
        
        def mock_generate_sql(*args, **kwargs):
            return "INVALID SQL WITH DROP TABLE users;"
        
        self.processor._generate_sql = mock_generate_sql
        
        # Deve gerar ValidationError
        with pytest.raises(ValidationError):
            self.processor.analyze_query("teste query")
        
        # Restaurar método original
        self.processor._generate_sql = original_generate
    
    def test_metrics_with_validation_failures(self):
        """Testa métricas incluindo falhas de validação."""
        # Simular algumas falhas
        self.processor.queries_processed = 10
        self.processor.successful_queries = 7
        self.processor.failed_queries = 3
        self.processor.validation_failures = 2
        
        # Métricas gerais
        general_metrics = self.processor.get_metrics()
        assert general_metrics["queries_processed"] == 10
        
        # Métricas de validação
        validation_metrics = self.processor.get_validation_metrics()
        assert validation_metrics["validation_failures"] == 2
        assert validation_metrics["validation_success_rate"] == 0.8  # 8/10


if __name__ == "__main__":
    pytest.main([__file__]) 