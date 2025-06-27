#!/usr/bin/env python3
"""
Serviço de Sanitização de Inputs - PROAtivo
Implementa validação e sanitização de entradas para prevenir SQL injection.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import unicodedata

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Resultado da validação de input"""
    is_valid: bool
    sanitized_input: str
    risk_level: str  # LOW, MEDIUM, HIGH
    threats_detected: List[str]
    confidence_score: float  # 0-100

class InputSanitizer:
    """
    Serviço responsável por sanitizar e validar inputs do usuário
    para prevenir SQL injection e outros ataques.
    """
    
    def __init__(self):
        # Padrões SQL perigosos que devem ser detectados
        self.dangerous_sql_patterns = {
            # Comandos DDL perigosos
            r'\b(drop|truncate|alter)\s+(table|database|schema)\b': 'DDL_COMMAND',
            r'\b(create|drop)\s+(user|role|function|procedure)\b': 'DDL_COMMAND',
            
            # Comandos DML perigosos
            r'\b(delete|update|insert)\s+': 'DML_COMMAND',
            r'\b(exec|execute)\s*\(': 'EXEC_COMMAND',
            
            # Union-based injection
            r'\bunion\s+(all\s+)?select\b': 'UNION_INJECTION',
            r'\bunion\s*\(': 'UNION_INJECTION',
            
            # Boolean-based injection
            r"'\s*(or|and)\s*'[^']*'\s*=\s*'[^']*'": 'BOOLEAN_INJECTION',
            r"'\s*(or|and)\s*\d+\s*=\s*\d+": 'BOOLEAN_INJECTION',
            
            # Comment-based injection
            r'--\s*[^\r\n]*': 'SQL_COMMENT',
            r'/\*.*?\*/': 'BLOCK_COMMENT',
            r'#[^\r\n]*': 'MYSQL_COMMENT',
            
            # Stacked queries
            r';\s*\w+': 'STACKED_QUERY',
            
            # Information disclosure
            r'\b(information_schema|sys\.|master\.)\w+': 'INFO_DISCLOSURE',
            r'\b(version|user|database|schema)\s*\(\s*\)': 'INFO_FUNCTION',
            
            # Time-based injection
            r'\b(waitfor|delay|sleep|benchmark)\s*\(': 'TIME_BASED',
            
            # Error-based injection
            r'\b(extractvalue|updatexml|exp)\s*\(': 'ERROR_BASED',
            
            # Bypass attempts
            r'%[0-9a-f]{2}': 'URL_ENCODING',
            r'\\x[0-9a-f]{2}': 'HEX_ENCODING',
            r'char\s*\(\s*\d+\s*\)': 'CHAR_FUNCTION',
            r'0x[0-9a-f]+': 'HEX_LITERAL',
        }
        
        # Caracteres permitidos em queries de domínio
        self.allowed_chars_pattern = re.compile(r'^[a-zA-Z0-9À-ÿ\s\-_.,!?()]+$')
        
        # Palavras-chave do domínio permitidas
        self.domain_keywords = {
            'equipamentos', 'equipment', 'equipamento',
            'manutenção', 'manutencao', 'maintenance', 'manutenções',
            'transformador', 'transformadores', 'transformer',
            'gerador', 'geradores', 'generator',
            'disjuntor', 'disjuntores', 'breaker',
            'status', 'estado', 'condition',
            'critico', 'crítico', 'critical',
            'operacional', 'operational',
            'preventiva', 'corretiva', 'preventive', 'corrective',
            'custo', 'custos', 'cost', 'costs',
            'falha', 'falhas', 'failure', 'failures',
            'técnico', 'tecnico', 'technician',
            'norte', 'sul', 'leste', 'oeste',
            'subestação', 'subestacao', 'substation'
        }

    def validate_and_sanitize(self, user_input: str) -> ValidationResult:
        """
        Valida e sanitiza input do usuário
        
        Args:
            user_input: String de entrada do usuário
            
        Returns:
            ValidationResult com resultado da validação
        """
        if not user_input or not isinstance(user_input, str):
            return ValidationResult(
                is_valid=False,
                sanitized_input="",
                risk_level="HIGH",
                threats_detected=["EMPTY_OR_INVALID_INPUT"],
                confidence_score=0.0
            )
        
        # Normalizar unicode
        normalized_input = unicodedata.normalize('NFKC', user_input.strip())
        
        # Detectar ameaças
        threats_detected = self._detect_threats(normalized_input)
        
        # Calcular nível de risco
        risk_level = self._calculate_risk_level(threats_detected)
        
        # Sanitizar input
        sanitized_input = self._sanitize_input(normalized_input, threats_detected)
        
        # Calcular score de confiança
        confidence_score = self._calculate_confidence_score(
            sanitized_input, threats_detected, risk_level
        )
        
        # Determinar se é válido
        is_valid = (
            risk_level in ['LOW', 'MEDIUM'] and
            confidence_score >= 70 and
            len(sanitized_input.strip()) > 0
        )
        
        result = ValidationResult(
            is_valid=is_valid,
            sanitized_input=sanitized_input,
            risk_level=risk_level,
            threats_detected=threats_detected,
            confidence_score=confidence_score
        )
        
        if threats_detected:
            logger.warning(
                f"Threats detected in input: {threats_detected}. "
                f"Risk level: {risk_level}. Input: {user_input[:100]}..."
            )
        
        return result

    def _detect_threats(self, input_text: str) -> List[str]:
        """Detecta ameaças no texto de entrada"""
        threats = []
        input_lower = input_text.lower()
        
        # Verificar padrões SQL perigosos
        for pattern, threat_type in self.dangerous_sql_patterns.items():
            if re.search(pattern, input_lower, re.IGNORECASE | re.MULTILINE):
                threats.append(threat_type)
        
        # Verificar caracteres suspeitos
        if not self.allowed_chars_pattern.match(input_text):
            threats.append('INVALID_CHARACTERS')
        
        # Verificar comprimento excessivo
        if len(input_text) > 500:
            threats.append('EXCESSIVE_LENGTH')
        
        # Verificar múltiplas aspas
        if input_text.count("'") > 2 or input_text.count('"') > 2:
            threats.append('EXCESSIVE_QUOTES')
        
        # Verificar padrões de bypass
        if re.search(r'(/\*|\*/|%[0-9a-f]{2})', input_lower):
            threats.append('BYPASS_ATTEMPT')
        
        return list(set(threats))  # Remover duplicatas

    def _calculate_risk_level(self, threats: List[str]) -> str:
        """Calcula nível de risco baseado nas ameaças detectadas"""
        if not threats:
            return 'LOW'
        
        high_risk_threats = {
            'DDL_COMMAND', 'DML_COMMAND', 'EXEC_COMMAND',
            'STACKED_QUERY', 'UNION_INJECTION', 'ERROR_BASED'
        }
        
        medium_risk_threats = {
            'BOOLEAN_INJECTION', 'SQL_COMMENT', 'BLOCK_COMMENT',
            'TIME_BASED', 'INFO_DISCLOSURE', 'BYPASS_ATTEMPT'
        }
        
        # Se há ameaças de alto risco
        if any(threat in high_risk_threats for threat in threats):
            return 'HIGH'
        
        # Se há ameaças de médio risco
        if any(threat in medium_risk_threats for threat in threats):
            return 'MEDIUM'
        
        # Outras ameaças são consideradas baixo risco
        return 'LOW' if len(threats) <= 2 else 'MEDIUM'

    def _sanitize_input(self, input_text: str, threats: List[str]) -> str:
        """Sanitiza o input removendo elementos perigosos"""
        sanitized = input_text
        
        # Remover comentários SQL
        sanitized = re.sub(r'--[^\r\n]*', '', sanitized)
        sanitized = re.sub(r'/\*.*?\*/', '', sanitized, flags=re.DOTALL)
        sanitized = re.sub(r'#[^\r\n]*', '', sanitized)
        
        # Remover múltiplas queries (ponto e vírgula seguido de código)
        sanitized = re.sub(r';\s*\w+.*$', '', sanitized, flags=re.MULTILINE)
        
        # Remover encodings perigosos
        sanitized = re.sub(r'%[0-9a-f]{2}', '', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'\\x[0-9a-f]{2}', '', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'0x[0-9a-f]+', '', sanitized, flags=re.IGNORECASE)
        
        # Limitar aspas consecutivas
        sanitized = re.sub(r"'{3,}", "''", sanitized)
        sanitized = re.sub(r'"{3,}', '""', sanitized)
        
        # Normalizar espaços
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        # Truncar se muito longo
        if len(sanitized) > 200:
            sanitized = sanitized[:200].rsplit(' ', 1)[0] + '...'
        
        return sanitized

    def _calculate_confidence_score(
        self, 
        sanitized_input: str, 
        threats: List[str], 
        risk_level: str
    ) -> float:
        """Calcula score de confiança do input sanitizado"""
        base_score = 100.0
        
        # Penalizar por ameaças detectadas
        threat_penalty = len(threats) * 15
        base_score -= threat_penalty
        
        # Penalizar por nível de risco
        risk_penalties = {'LOW': 0, 'MEDIUM': 20, 'HIGH': 50}
        base_score -= risk_penalties.get(risk_level, 50)
        
        # Penalizar inputs muito curtos ou muito longos
        length = len(sanitized_input.strip())
        if length < 5:
            base_score -= 30
        elif length > 150:
            base_score -= 10
        
        # Bonificar se contém palavras do domínio
        words = set(sanitized_input.lower().split())
        domain_matches = words.intersection(self.domain_keywords)
        domain_bonus = min(len(domain_matches) * 5, 20)
        base_score += domain_bonus
        
        # Bonificar se parece uma pergunta natural
        if any(word in sanitized_input.lower() for word in 
               ['quantos', 'quais', 'qual', 'como', 'onde', 'quando', 'liste', 'mostre']):
            base_score += 10
        
        return max(0.0, min(100.0, base_score))

    def is_safe_for_sql_generation(self, user_input: str) -> Tuple[bool, str]:
        """
        Verifica se input é seguro para geração de SQL
        
        Returns:
            Tuple[bool, str]: (is_safe, reason)
        """
        result = self.validate_and_sanitize(user_input)
        
        if not result.is_valid:
            return False, f"Input rejeitado - Risco {result.risk_level}: {', '.join(result.threats_detected)}"
        
        if result.risk_level == 'HIGH':
            return False, f"Alto risco de SQL injection detectado: {', '.join(result.threats_detected)}"
        
        if result.confidence_score < 60:
            return False, f"Baixa confiança no input (score: {result.confidence_score:.1f})"
        
        return True, "Input aprovado para processamento"

    def get_safe_input(self, user_input: str) -> Optional[str]:
        """
        Retorna versão segura do input ou None se não for possível sanitizar
        
        Args:
            user_input: Input original do usuário
            
        Returns:
            String sanitizada ou None se muito perigoso
        """
        result = self.validate_and_sanitize(user_input)
        
        if result.is_valid and result.risk_level != 'HIGH':
            return result.sanitized_input
        
        return None 