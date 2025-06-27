#!/usr/bin/env python3
"""
Script de Teste para InputSanitizer - PROAtivo
Testa a eficácia das mitigações de segurança implementadas.
"""

import sys
from pathlib import Path
from typing import Dict, List

# Adicionar o diretório src ao path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from api.services.input_sanitizer import InputSanitizer, ValidationResult

class SanitizerTester:
    """Testador do sistema de sanitização"""
    
    def __init__(self):
        self.sanitizer = InputSanitizer()
        
        # Payloads maliciosos para testar
        self.malicious_payloads = [
            "'; DROP TABLE equipments; --",
            "' OR '1'='1",
            "' OR 1=1 --",
            "' UNION SELECT * FROM equipments --",
            "admin'--",
            "' OR 'x'='x",
            "') OR ('1'='1",
            "' UNION SELECT username,password FROM users --",
            "' AND 1=1 --",
            "'; INSERT INTO equipments VALUES('hack','attack','test'); --",
            "/**/UNION/**/SELECT/**/*/**/FROM/**/equipments/**/--",
            "' UNI%00ON SEL%00ECT * FR%00OM equipments --"
        ]
        
        # Queries legítimas que devem passar
        self.legitimate_queries = [
            "Liste todos os transformadores",
            "Quantos equipamentos estão operacionais?",
            "Status do transformador TR-001",
            "Manutenções programadas para esta semana",
            "Última manutenção do gerador GE-002",
            "Custo total de manutenções este mês",
            "Top 5 equipamentos com mais falhas",
            "Equipamentos críticos sem manutenção",
            "Equipamentos em manutenção agora",
            "Qual o status dos equipamentos na subestação Sul?"
        ]

    def test_malicious_payloads(self) -> Dict[str, int]:
        """Testa payloads maliciosos"""
        print("🔍 Testando payloads maliciosos...")
        
        results = {'blocked': 0, 'passed': 0, 'total': len(self.malicious_payloads)}
        
        for i, payload in enumerate(self.malicious_payloads, 1):
            print(f"\n{i:2d}. Testando: {payload}")
            
            result = self.sanitizer.validate_and_sanitize(payload)
            is_safe, reason = self.sanitizer.is_safe_for_sql_generation(payload)
            
            if not is_safe or result.risk_level == 'HIGH':
                print(f"    ✅ BLOQUEADO - Risco: {result.risk_level}")
                print(f"    📋 Ameaças: {', '.join(result.threats_detected)}")
                print(f"    🔒 Razão: {reason}")
                results['blocked'] += 1
            else:
                print(f"    ⚠️  PASSOU - Risco: {result.risk_level}")
                print(f"    📝 Sanitizado: {result.sanitized_input}")
                print(f"    📊 Confiança: {result.confidence_score:.1f}%")
                results['passed'] += 1
        
        return results

    def test_legitimate_queries(self) -> Dict[str, int]:
        """Testa queries legítimas"""
        print("\n✅ Testando queries legítimas...")
        
        results = {'passed': 0, 'blocked': 0, 'total': len(self.legitimate_queries)}
        
        for i, query in enumerate(self.legitimate_queries, 1):
            print(f"\n{i:2d}. Testando: {query}")
            
            result = self.sanitizer.validate_and_sanitize(query)
            is_safe, reason = self.sanitizer.is_safe_for_sql_generation(query)
            
            if is_safe and result.is_valid:
                print(f"    ✅ APROVADO - Risco: {result.risk_level}")
                print(f"    📊 Confiança: {result.confidence_score:.1f}%")
                if result.sanitized_input != query:
                    print(f"    📝 Sanitizado: {result.sanitized_input}")
                results['passed'] += 1
            else:
                print(f"    ❌ REJEITADO - Risco: {result.risk_level}")
                print(f"    📋 Ameaças: {', '.join(result.threats_detected)}")
                print(f"    🔒 Razão: {reason}")
                results['blocked'] += 1
        
        return results

    def test_edge_cases(self) -> Dict[str, int]:
        """Testa casos extremos"""
        print("\n🧪 Testando casos extremos...")
        
        edge_cases = [
            "",  # Vazio
            " ",  # Apenas espaço
            "a" * 600,  # Muito longo
            "'''''''",  # Muitas aspas
            "SELECT * FROM equipments",  # SQL direto
            "Como funciona o sistema?",  # Pergunta geral
            "123456",  # Apenas números
            "Equipamento TR-001, GE-002",  # IDs válidos
            "equipamentos críticos!!!",  # Com pontuação
            "🔧 manutenção",  # Com emoji
        ]
        
        results = {'total': len(edge_cases), 'passed': 0, 'blocked': 0}
        
        for i, case in enumerate(edge_cases, 1):
            display_case = case if len(case) <= 50 else case[:50] + "..."
            print(f"\n{i:2d}. Testando: '{display_case}'")
            
            result = self.sanitizer.validate_and_sanitize(case)
            is_safe, reason = self.sanitizer.is_safe_for_sql_generation(case)
            
            print(f"    📊 Resultado: Válido={result.is_valid}, Risco={result.risk_level}")
            print(f"    📈 Confiança: {result.confidence_score:.1f}%")
            
            if result.threats_detected:
                print(f"    ⚠️  Ameaças: {', '.join(result.threats_detected)}")
            
            if is_safe:
                results['passed'] += 1
            else:
                results['blocked'] += 1
        
        return results

    def generate_report(self, malicious_results: Dict, legitimate_results: Dict, edge_results: Dict):
        """Gera relatório final dos testes"""
        print("\n" + "="*80)
        print("📊 RELATÓRIO FINAL - TESTE DE SANITIZAÇÃO")
        print("="*80)
        
        # Testes de payloads maliciosos
        mal_block_rate = (malicious_results['blocked'] / malicious_results['total']) * 100
        print(f"\n🚨 PAYLOADS MALICIOSOS:")
        print(f"   Total testados: {malicious_results['total']}")
        print(f"   Bloqueados: {malicious_results['blocked']} ({mal_block_rate:.1f}%)")
        print(f"   Passaram: {malicious_results['passed']} ({100-mal_block_rate:.1f}%)")
        
        # Testes de queries legítimas
        leg_pass_rate = (legitimate_results['passed'] / legitimate_results['total']) * 100
        print(f"\n✅ QUERIES LEGÍTIMAS:")
        print(f"   Total testadas: {legitimate_results['total']}")
        print(f"   Aprovadas: {legitimate_results['passed']} ({leg_pass_rate:.1f}%)")
        print(f"   Rejeitadas: {legitimate_results['blocked']} ({100-leg_pass_rate:.1f}%)")
        
        # Casos extremos
        edge_pass_rate = (edge_results['passed'] / edge_results['total']) * 100
        print(f"\n🧪 CASOS EXTREMOS:")
        print(f"   Total testados: {edge_results['total']}")
        print(f"   Aprovados: {edge_results['passed']} ({edge_pass_rate:.1f}%)")
        print(f"   Rejeitados: {edge_results['blocked']} ({100-edge_pass_rate:.1f}%)")
        
        # Score geral de segurança
        security_score = (mal_block_rate + leg_pass_rate) / 2
        print(f"\n🛡️ SCORE DE SEGURANÇA GERAL: {security_score:.1f}%")
        
        # Avaliação
        if security_score >= 90:
            print("🟢 EXCELENTE - Sistema muito seguro")
        elif security_score >= 80:
            print("🟡 BOM - Sistema adequadamente seguro")
        elif security_score >= 70:
            print("🟠 REGULAR - Melhorias necessárias")
        else:
            print("🔴 CRÍTICO - Sistema vulnerável")
        
        # Recomendações
        print(f"\n💡 RECOMENDAÇÕES:")
        if malicious_results['passed'] > 0:
            print(f"   🚨 URGENTE: {malicious_results['passed']} payloads maliciosos passaram!")
            print("   🔧 Revisar padrões de detecção de ameaças")
            print("   🛡️ Considerar whitelist mais restritiva")
        
        if legitimate_results['blocked'] > 2:
            print(f"   ⚠️  Muitas queries legítimas rejeitadas ({legitimate_results['blocked']})")
            print("   🔧 Ajustar thresholds de confiança")
            print("   📝 Expandir vocabulário do domínio")
        
        if security_score >= 85:
            print("   ✅ Sistema bem protegido contra SQL injection")
            print("   🔄 Manter testes regulares")
        
        print("\n" + "="*80)

def main():
    """Função principal"""
    print("🧪 INICIANDO TESTES DE SANITIZAÇÃO DE INPUTS")
    print("="*50)
    
    tester = SanitizerTester()
    
    # Executar testes
    malicious_results = tester.test_malicious_payloads()
    legitimate_results = tester.test_legitimate_queries()
    edge_results = tester.test_edge_cases()
    
    # Gerar relatório
    tester.generate_report(malicious_results, legitimate_results, edge_results)

if __name__ == "__main__":
    main() 