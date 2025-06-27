#!/usr/bin/env python3
"""
Teste Simplificado do InputSanitizer - PROAtivo
"""

import sys
import re
from pathlib import Path
from typing import List

# Simular a funcionalidade do InputSanitizer para teste
class SimpleSanitizer:
    def __init__(self):
        self.dangerous_patterns = [
            r'\bdrop\s+table\b',
            r'\bunion\s+select\b', 
            r'--',
            r'/\*',
            r';\s*\w+',
            r'\bdelete\s+',
            r'\binsert\s+',
            r'\bupdate\s+',
            r"'\s*or\s*'",
            r'\bexec\s*\('
        ]
    
    def is_malicious(self, text: str) -> tuple[bool, List[str]]:
        """Detecta se o texto é malicioso"""
        threats = []
        text_lower = text.lower()
        
        for pattern in self.dangerous_patterns:
            if re.search(pattern, text_lower):
                threats.append(pattern)
        
        return len(threats) > 0, threats
    
    def sanitize(self, text: str) -> str:
        """Sanitiza o texto"""
        sanitized = text
        
        # Remover comentários
        sanitized = re.sub(r'--[^\r\n]*', '', sanitized)
        sanitized = re.sub(r'/\*.*?\*/', '', sanitized)
        
        # Remover múltiplas queries
        sanitized = re.sub(r';\s*\w+.*$', '', sanitized)
        
        # Normalizar espaços
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        return sanitized

def test_security():
    """Executa testes de segurança"""
    sanitizer = SimpleSanitizer()
    
    # Payloads maliciosos
    malicious_payloads = [
        "'; DROP TABLE equipments; --",
        "' OR '1'='1",
        "' OR 1=1 --",
        "' UNION SELECT * FROM equipments --",
        "admin'--",
        "' OR 'x'='x",
        "'; INSERT INTO equipments VALUES('hack','attack'); --",
        "/**/UNION/**/SELECT/**/",
        "' AND 1=1 --"
    ]
    
    # Queries legítimas
    legitimate_queries = [
        "Liste todos os transformadores",
        "Quantos equipamentos estão operacionais?",
        "Status do transformador TR-001",
        "Manutenções programadas para esta semana",
        "Custo total de manutenções este mês",
        "Equipamentos críticos sem manutenção",
        "Equipamentos em manutenção agora"
    ]
    
    print("🧪 TESTE SIMPLIFICADO DE SANITIZAÇÃO")
    print("="*50)
    
    # Testar payloads maliciosos
    print("\n🚨 Testando payloads maliciosos:")
    blocked_malicious = 0
    for i, payload in enumerate(malicious_payloads, 1):
        is_malicious, threats = sanitizer.is_malicious(payload)
        sanitized = sanitizer.sanitize(payload)
        
        print(f"\n{i:2d}. {payload}")
        if is_malicious:
            print(f"    ✅ DETECTADO como malicioso")
            print(f"    🔍 Padrões: {threats}")
            blocked_malicious += 1
        else:
            print(f"    ⚠️  NÃO detectado como malicioso")
        
        if sanitized != payload:
            print(f"    🧹 Sanitizado: {sanitized}")
    
    # Testar queries legítimas
    print(f"\n✅ Testando queries legítimas:")
    passed_legitimate = 0
    for i, query in enumerate(legitimate_queries, 1):
        is_malicious, threats = sanitizer.is_malicious(query)
        sanitized = sanitizer.sanitize(query)
        
        print(f"\n{i:2d}. {query}")
        if not is_malicious:
            print(f"    ✅ APROVADO como legítimo")
            passed_legitimate += 1
        else:
            print(f"    ❌ REJEITADO incorretamente")
            print(f"    🔍 Padrões detectados: {threats}")
        
        if sanitized != query:
            print(f"    🧹 Sanitizado: {sanitized}")
    
    # Relatório final
    print(f"\n" + "="*60)
    print("📊 RELATÓRIO FINAL")
    print("="*60)
    
    malicious_block_rate = (blocked_malicious / len(malicious_payloads)) * 100
    legitimate_pass_rate = (passed_legitimate / len(legitimate_queries)) * 100
    
    print(f"\n🚨 Payloads Maliciosos:")
    print(f"   Bloqueados: {blocked_malicious}/{len(malicious_payloads)} ({malicious_block_rate:.1f}%)")
    
    print(f"\n✅ Queries Legítimas:")  
    print(f"   Aprovadas: {passed_legitimate}/{len(legitimate_queries)} ({legitimate_pass_rate:.1f}%)")
    
    overall_score = (malicious_block_rate + legitimate_pass_rate) / 2
    print(f"\n🛡️ Score Geral de Segurança: {overall_score:.1f}%")
    
    if overall_score >= 90:
        print("🟢 EXCELENTE - Muito seguro")
    elif overall_score >= 80:
        print("🟡 BOM - Adequadamente seguro") 
    elif overall_score >= 70:
        print("🟠 REGULAR - Melhorias necessárias")
    else:
        print("🔴 CRÍTICO - Sistema vulnerável")
    
    print(f"\n💡 Análise:")
    if blocked_malicious == len(malicious_payloads):
        print("   ✅ Todos os payloads maliciosos foram detectados!")
    else:
        missed = len(malicious_payloads) - blocked_malicious
        print(f"   ⚠️  {missed} payloads maliciosos não foram detectados")
    
    if passed_legitimate == len(legitimate_queries):
        print("   ✅ Todas as queries legítimas foram aprovadas!")
    else:
        rejected = len(legitimate_queries) - passed_legitimate  
        print(f"   ⚠️  {rejected} queries legítimas foram rejeitadas")

if __name__ == "__main__":
    test_security() 