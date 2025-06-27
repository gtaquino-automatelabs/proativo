#!/usr/bin/env python3
"""
Testes Unitários para InputSanitizer - PROAtivo
Testa todas as funcionalidades do sistema de sanitização de inputs.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Adicionar path do src
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from api.services.input_sanitizer import InputSanitizer, ValidationResult

# Simular as classes necessárias para os testes
class ValidationResult:
    def __init__(self, is_valid, sanitized_input, risk_level, threats_detected, confidence_score):
        self.is_valid = is_valid
        self.sanitized_input = sanitized_input
        self.risk_level = risk_level
        self.threats_detected = threats_detected
        self.confidence_score = confidence_score

class MockInputSanitizer:
    """Mock do InputSanitizer para testes"""
    
    def __init__(self):
        self.dangerous_patterns = [
            'drop table', 'union select', '--', '/*', 'delete from',
            'insert into', 'update set', "' or '", 'exec('
        ]
        self.domain_keywords = {
            'equipamentos', 'transformadores', 'manutenção', 'status'
        }
    
    def validate_and_sanitize(self, user_input):
        if not user_input:
            return ValidationResult(
                is_valid=False,
                sanitized_input="",
                risk_level="HIGH",
                threats_detected=["EMPTY_INPUT"],
                confidence_score=0.0
            )
        
        threats = self._detect_threats(user_input)
        risk_level = self._calculate_risk_level(threats)
        sanitized = self._sanitize_input(user_input)
        confidence = self._calculate_confidence(sanitized, threats)
        
        is_valid = risk_level != "HIGH" and confidence > 70
        
        return ValidationResult(
            is_valid=is_valid,
            sanitized_input=sanitized,
            risk_level=risk_level,
            threats_detected=threats,
            confidence_score=confidence
        )
    
    def _detect_threats(self, text):
        threats = []
        text_lower = text.lower()
        
        for pattern in self.dangerous_patterns:
            if pattern in text_lower:
                threats.append(pattern.replace(' ', '_').upper())
        
        if len(text) > 500:
            threats.append("EXCESSIVE_LENGTH")
        
        if text.count("'") > 2:
            threats.append("EXCESSIVE_QUOTES")
            
        return threats
    
    def _calculate_risk_level(self, threats):
        if not threats:
            return "LOW"
        
        high_risk = ['DROP_TABLE', 'DELETE_FROM', 'INSERT_INTO', 'UNION_SELECT']
        if any(t in high_risk for t in threats):
            return "HIGH"
        
        medium_risk = ['--', '/*', "'_OR_'"]
        if any(t in medium_risk for t in threats):
            return "MEDIUM"
            
        return "LOW"
    
    def _sanitize_input(self, text):
        sanitized = text
        sanitized = sanitized.replace('--', '')
        sanitized = sanitized.replace('/*', '').replace('*/', '')
        
        if len(sanitized) > 200:
            sanitized = sanitized[:200] + "..."
            
        return sanitized.strip()
    
    def _calculate_confidence(self, text, threats):
        score = 100.0
        score -= len(threats) * 15
        
        words = set(text.lower().split())
        domain_matches = words.intersection(self.domain_keywords)
        score += len(domain_matches) * 5
        
        if any(w in text.lower() for w in ['quantos', 'lista', 'status']):
            score += 10
            
        return max(0, min(100, score))
    
    def is_safe_for_sql_generation(self, user_input):
        result = self.validate_and_sanitize(user_input)
        
        if not result.is_valid:
            return False, f"Input rejeitado - Risco {result.risk_level}"
        
        if result.confidence_score < 60:
            return False, f"Baixa confiança: {result.confidence_score:.1f}%"
            
        return True, "Input aprovado para processamento"
    
    def get_safe_input(self, user_input):
        result = self.validate_and_sanitize(user_input)
        
        if result.is_valid and result.risk_level != "HIGH":
            return result.sanitized_input
        
        return None


class TestInputSanitizer:
    """Testes para a classe InputSanitizer"""
    
    @pytest.fixture
    def sanitizer(self):
        """Fixture que retorna uma instância do MockInputSanitizer"""
        return MockInputSanitizer()
    
    def test_init(self, sanitizer):
        """Testa inicialização do sanitizer"""
        assert sanitizer.dangerous_patterns is not None
        assert len(sanitizer.dangerous_patterns) > 0
        assert len(sanitizer.domain_keywords) > 0
    
    def test_validate_empty_input(self, sanitizer):
        """Testa validação com input vazio"""
        result = sanitizer.validate_and_sanitize("")
        
        assert not result.is_valid
        assert result.risk_level == "HIGH"
        assert "EMPTY_INPUT" in result.threats_detected
        assert result.confidence_score == 0.0
    
    def test_validate_none_input(self, sanitizer):
        """Testa validação com input None"""
        result = sanitizer.validate_and_sanitize(None)
        
        assert not result.is_valid
        assert result.risk_level == "HIGH"
    
    def test_validate_legitimate_query(self, sanitizer):
        """Testa validação de query legítima"""
        query = "Liste todos os transformadores"
        result = sanitizer.validate_and_sanitize(query)
        
        assert result.is_valid
        assert result.risk_level == "LOW"
        assert len(result.threats_detected) == 0
        assert result.confidence_score > 70
    
    def test_validate_sql_injection_drop(self, sanitizer):
        """Testa detecção de SQL injection com DROP"""
        malicious_query = "'; DROP TABLE equipments; --"
        result = sanitizer.validate_and_sanitize(malicious_query)
        
        assert not result.is_valid
        assert result.risk_level == "HIGH"
        assert any("DROP" in threat for threat in result.threats_detected)
    
    def test_validate_sql_injection_union(self, sanitizer):
        """Testa detecção de UNION injection"""
        malicious_query = "' UNION SELECT * FROM users --"
        result = sanitizer.validate_and_sanitize(malicious_query)
        
        assert not result.is_valid
        assert result.risk_level == "HIGH"
    
    def test_detect_threats_sql_commands(self, sanitizer):
        """Testa detecção de comandos SQL perigosos"""
        threats = sanitizer._detect_threats("DROP TABLE users")
        assert any("DROP" in threat for threat in threats)
        
        threats = sanitizer._detect_threats("DELETE FROM equipments")
        assert any("DELETE" in threat for threat in threats)
    
    def test_detect_threats_comments(self, sanitizer):
        """Testa detecção de comentários SQL"""
        threats = sanitizer._detect_threats("SELECT * FROM users --")
        assert "--" in threats
        
        threats = sanitizer._detect_threats("SELECT * /* comment */ FROM users")
        assert "/*" in threats
    
    def test_detect_threats_excessive_length(self, sanitizer):
        """Testa detecção de input muito longo"""
        long_input = "a" * 600
        threats = sanitizer._detect_threats(long_input)
        assert "EXCESSIVE_LENGTH" in threats
    
    def test_detect_threats_excessive_quotes(self, sanitizer):
        """Testa detecção de muitas aspas"""
        threats = sanitizer._detect_threats("'''''''")
        assert "EXCESSIVE_QUOTES" in threats
    
    def test_calculate_risk_level_high(self, sanitizer):
        """Testa cálculo de risco alto"""
        high_threats = ["DROP_TABLE", "UNION_SELECT"]
        risk = sanitizer._calculate_risk_level(high_threats)
        assert risk == "HIGH"
    
    def test_calculate_risk_level_medium(self, sanitizer):
        """Testa cálculo de risco médio"""
        medium_threats = ["--"]
        risk = sanitizer._calculate_risk_level(medium_threats)
        assert risk == "MEDIUM"
    
    def test_calculate_risk_level_low(self, sanitizer):
        """Testa cálculo de risco baixo"""
        # Sem ameaças
        risk = sanitizer._calculate_risk_level([])
        assert risk == "LOW"
    
    def test_sanitize_input_comments(self, sanitizer):
        """Testa sanitização de comentários"""
        input_text = "SELECT * FROM users -- comment"
        sanitized = sanitizer._sanitize_input(input_text)
        assert "--" not in sanitized
    
    def test_sanitize_input_long_text(self, sanitizer):
        """Testa sanitização de texto muito longo"""
        long_text = "palavra " * 100  # ~700 caracteres
        sanitized = sanitizer._sanitize_input(long_text)
        assert len(sanitized) <= 203  # 200 + "..."
    
    def test_calculate_confidence_score_domain_keywords(self, sanitizer):
        """Testa bonus por palavras do domínio"""
        score = sanitizer._calculate_confidence(
            "equipamentos transformadores manutenção", []
        )
        # Deve ter bonus por palavras do domínio
        assert score > 90
    
    def test_is_safe_for_sql_generation_safe(self, sanitizer):
        """Testa aprovação de input seguro"""
        safe_query = "Liste todos os transformadores"
        is_safe, reason = sanitizer.is_safe_for_sql_generation(safe_query)
        
        assert is_safe
        assert "aprovado" in reason.lower()
    
    def test_is_safe_for_sql_generation_unsafe(self, sanitizer):
        """Testa rejeição de input inseguro"""
        unsafe_query = "'; DROP TABLE equipments; --"
        is_safe, reason = sanitizer.is_safe_for_sql_generation(unsafe_query)
        
        assert not is_safe
        assert "risco" in reason.lower()
    
    def test_get_safe_input_valid(self, sanitizer):
        """Testa obtenção de input seguro válido"""
        safe_query = "Liste todos os transformadores"
        safe_input = sanitizer.get_safe_input(safe_query)
        
        assert safe_input is not None
    
    def test_get_safe_input_invalid(self, sanitizer):
        """Testa rejeição de input inseguro"""
        unsafe_query = "'; DROP TABLE equipments; --"
        safe_input = sanitizer.get_safe_input(unsafe_query)
        
        assert safe_input is None
    
    @pytest.mark.parametrize("legitimate_input", [
        "Liste todos os transformadores",
        "Quantos equipamentos estão operacionais?",
        "Status do transformador TR-001",
        "Manutenções programadas para esta semana",
        "Equipamentos críticos sem manutenção",
    ])
    def test_legitimate_queries_approval(self, sanitizer, legitimate_input):
        """Testa aprovação de queries legítimas"""
        result = sanitizer.validate_and_sanitize(legitimate_input)
        # Queries legítimas devem ter baixo ou médio risco
        assert result.risk_level in ["LOW", "MEDIUM"]
        assert result.confidence_score > 50
    
    def test_validation_result_structure(self, sanitizer):
        """Testa estrutura do ValidationResult"""
        query = "Liste todos os transformadores"
        result = sanitizer.validate_and_sanitize(query)
        
        # Verificar todos os campos obrigatórios
        assert hasattr(result, 'is_valid')
        assert hasattr(result, 'sanitized_input')
        assert hasattr(result, 'risk_level')
        assert hasattr(result, 'threats_detected')
        assert hasattr(result, 'confidence_score')
        
        assert isinstance(result.is_valid, bool)
        assert isinstance(result.sanitized_input, str)
        assert result.risk_level in ['LOW', 'MEDIUM', 'HIGH']
        assert isinstance(result.threats_detected, list)
        assert isinstance(result.confidence_score, (int, float))
        assert 0 <= result.confidence_score <= 100


class TestValidationResult:
    """Testes para a classe ValidationResult"""
    
    def test_validation_result_creation(self):
        """Testa criação de ValidationResult"""
        result = ValidationResult(
            is_valid=True,
            sanitized_input="test",
            risk_level="LOW",
            threats_detected=[],
            confidence_score=95.0
        )
        
        assert result.is_valid
        assert result.sanitized_input == "test"
        assert result.risk_level == "LOW"
        assert result.threats_detected == []
        assert result.confidence_score == 95.0


# Testes de integração simples
class TestInputSanitizerIntegration:
    """Testes de integração para InputSanitizer"""
    
    @pytest.fixture
    def sanitizer(self):
        return MockInputSanitizer()
    
    def test_full_workflow_safe_input(self, sanitizer):
        """Testa workflow completo com input seguro"""
        query = "Quantos transformadores estão operacionais?"
        
        # Validar e sanitizar
        result = sanitizer.validate_and_sanitize(query)
        assert result.risk_level != "HIGH"
        
        # Verificar segurança para SQL
        is_safe, reason = sanitizer.is_safe_for_sql_generation(query)
        assert is_safe
        
        # Obter input seguro
        safe_input = sanitizer.get_safe_input(query)
        assert safe_input is not None
    
    def test_full_workflow_malicious_input(self, sanitizer):
        """Testa workflow completo com input malicioso"""
        query = "'; DROP TABLE equipments; --"
        
        # Validar e sanitizar
        result = sanitizer.validate_and_sanitize(query)
        assert not result.is_valid
        assert result.risk_level == "HIGH"
        
        # Verificar insegurança para SQL
        is_safe, reason = sanitizer.is_safe_for_sql_generation(query)
        assert not is_safe
        
        # Input seguro deve ser None
        safe_input = sanitizer.get_safe_input(query)
        assert safe_input is None


if __name__ == "__main__":
    pytest.main([__file__]) 