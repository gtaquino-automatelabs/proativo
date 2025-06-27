#!/usr/bin/env python3
"""
Script de teste para o Availability Router.

Testa o roteamento inteligente entre LLM SQL e sistema baseado em regras.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Adicionar diretório pai ao PATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.services.availability_router import AvailabilityRouter, RouteDecision
from src.utils.logger import get_logger

# Configurar logger
logger = get_logger(__name__)

# Lista de queries de teste
TEST_QUERIES = [
    # Queries simples (devem ir para regras)
    "Quantos equipamentos?",
    "Liste todos os transformadores",
    "Total de manutenções",
    
    # Queries médias (devem ir para LLM se disponível)
    "Quais equipamentos estão em manutenção e quando foram instalados?",
    "Mostre transformadores com suas últimas manutenções",
    
    # Queries complexas (devem ir para LLM se disponível)
    "Qual a média de custo de manutenção por tipo de equipamento nos últimos 6 meses?",
    "Compare a frequência de falhas entre transformadores e geradores agrupados por criticidade",
    "Análise de tendência de custos de manutenção preventiva vs corretiva"
]


async def test_routing_decisions():
    """Testa as decisões de roteamento."""
    print("\n" + "="*80)
    print("TESTE DO AVAILABILITY ROUTER - DECISÕES DE ROTEAMENTO")
    print("="*80)
    
    try:
        # Inicializar router
        router = AvailabilityRouter()
        
        # Verificar disponibilidade inicial
        print("\n1. Verificando disponibilidade inicial do LLM...")
        llm_available = await router.check_llm_availability()
        print(f"   LLM disponível: {llm_available}")
        
        if not llm_available:
            from src.api.config import get_settings
            settings = get_settings()
            
            reasons = []
            if not settings.llm_sql_feature_enabled:
                reasons.append("LLM_SQL_FEATURE_ENABLED=false")
            if not settings.google_api_key:
                reasons.append("Google API Key não configurada")
            
            if reasons:
                print(f"   Motivos: {', '.join(reasons)}")
        
        # Testar decisões de roteamento
        print("\n2. Testando decisões de roteamento:")
        print("-" * 60)
        
        for i, query in enumerate(TEST_QUERIES, 1):
            decision, reason = await router.route_query(query)
            
            # Determinar ícone baseado na decisão
            if decision == RouteDecision.LLM_SQL:
                icon = "🤖"
            elif decision == RouteDecision.RULE_BASED:
                icon = "📋"
            else:
                icon = "🔄"
            
            print(f"\n{i}. Query: {query}")
            print(f"   {icon} Decisão: {decision.value}")
            print(f"   Motivo: {reason}")
        
        # Mostrar métricas
        print("\n3. Métricas de roteamento:")
        print("-" * 60)
        
        metrics = router.get_metrics()
        
        print(f"   Total de requisições: {metrics['total_requests']}")
        print(f"   Rotas:")
        print(f"      - LLM SQL: {metrics['routes']['llm_sql']} ({metrics['percentages']['llm_sql']:.1f}%)")
        print(f"      - Regras: {metrics['routes']['rule_based']} ({metrics['percentages']['rule_based']:.1f}%)")
        print(f"      - Fallback: {metrics['routes']['fallback']} ({metrics['percentages']['fallback']:.1f}%)")
        
        if metrics['llm_metrics']['circuit_breaker_open']:
            print(f"   ⚠️  Circuit Breaker: ABERTO")
        
        # Health check do router
        print("\n4. Health Check do Router:")
        health = await router.health_check()
        print(f"   Status: {health['status']}")
        print(f"   LLM disponível: {health['llm_available']}")
        print(f"   Circuit breaker aberto: {health['circuit_breaker']['open']}")
        
    except Exception as e:
        logger.error(f"Erro durante teste: {str(e)}", exc_info=True)
        print(f"\n❌ Erro crítico: {str(e)}")
        return 1
    
    return 0


async def test_processing():
    """Testa o processamento real de algumas queries."""
    print("\n" + "="*80)
    print("TESTE DO AVAILABILITY ROUTER - PROCESSAMENTO")
    print("="*80)
    
    try:
        router = AvailabilityRouter()
        
        # Queries para testar processamento
        test_cases = [
            "Quantos transformadores estão operacionais?",
            "Qual o custo médio de manutenção por equipamento?"
        ]
        
        for query in test_cases:
            print(f"\n🔍 Processando: {query}")
            
            # Decidir rota
            decision, reason = await router.route_query(query)
            print(f"   Rota escolhida: {decision.value} ({reason})")
            
            # Processar baseado na decisão
            if decision == RouteDecision.LLM_SQL:
                print("   Processando com LLM SQL...")
                result = await router.process_with_llm_sql(query)
            elif decision == RouteDecision.RULE_BASED:
                print("   Processando com sistema de regras...")
                result = await router.process_with_rule_based(query)
            else:
                print("   Usando fallback...")
                # Fallback já seria tratado internamente
                continue
            
            # Mostrar resultado
            if result['success']:
                print(f"   ✅ Sucesso!")
                if 'sql' in result:
                    print(f"   SQL gerado: {result['sql']}")
                print(f"   Tempo: {result['response_time_ms']:.0f}ms")
            else:
                print(f"   ❌ Falha: {result.get('error', 'Erro desconhecido')}")
                if 'suggestions' in result:
                    print(f"   Sugestões: {', '.join(result['suggestions'][:3])}")
        
        # Métricas finais
        print("\n📊 Métricas finais:")
        metrics = router.get_metrics()
        print(f"   Taxa de sucesso LLM: {metrics['llm_metrics']['success_rate']:.1f}%")
        print(f"   Tempo médio LLM: {metrics['llm_metrics']['average_response_time_ms']:.0f}ms")
        
    except Exception as e:
        logger.error(f"Erro durante teste de processamento: {str(e)}", exc_info=True)
        print(f"\n❌ Erro: {str(e)}")
        return 1
    
    return 0


async def simulate_circuit_breaker():
    """Simula comportamento do circuit breaker."""
    print("\n" + "="*80)
    print("TESTE DO CIRCUIT BREAKER")
    print("="*80)
    
    try:
        router = AvailabilityRouter()
        
        # Forçar falhas para testar circuit breaker
        print("\n1. Simulando falhas consecutivas...")
        
        # Temporariamente sabotar o LLM para simular falhas
        original_generator = router._llm_sql_generator
        router._llm_sql_generator = None  # Forçar erro
        
        for i in range(4):
            print(f"\n   Tentativa {i+1}:")
            try:
                result = await router.process_with_llm_sql("teste query")
                print(f"   Resultado: {result.get('route', 'unknown')}")
            except:
                pass
            
            # Verificar estado do circuit breaker
            health = await router.health_check()
            failures = health['circuit_breaker']['consecutive_failures']
            is_open = health['circuit_breaker']['open']
            
            print(f"   Falhas consecutivas: {failures}")
            print(f"   Circuit breaker: {'ABERTO 🔴' if is_open else 'FECHADO 🟢'}")
        
        # Restaurar
        router._llm_sql_generator = original_generator
        
        print("\n2. Circuit breaker deve estar aberto agora.")
        print("   O sistema usará fallback por 10 minutos.")
        
    except Exception as e:
        print(f"\n❌ Erro na simulação: {str(e)}")
        return 1
    
    return 0


def main():
    """Função principal."""
    # Carregar variáveis de ambiente
    load_dotenv()
    
    print("\n🚀 INICIANDO TESTES DO AVAILABILITY ROUTER\n")
    
    async def run_all_tests():
        # Teste 1: Decisões de roteamento
        result1 = await test_routing_decisions()
        
        # Teste 2: Processamento
        result2 = await test_processing()
        
        # Teste 3: Circuit breaker (opcional)
        print("\n" + "="*80)
        print("Deseja testar o Circuit Breaker? (s/n): ", end="")
        if input().lower() == 's':
            result3 = await simulate_circuit_breaker()
        else:
            result3 = 0
        
        return max(result1, result2, result3)
    
    # Executar testes
    exit_code = asyncio.run(run_all_tests())
    
    print("\n" + "="*80)
    print("✅ TESTES CONCLUÍDOS")
    print("="*80)
    
    print("\n💡 OBSERVAÇÕES:")
    print("- O roteador escolhe automaticamente entre LLM SQL e regras")
    print("- Queries simples vão para regras (mais rápido)")
    print("- Queries complexas vão para LLM (se disponível)")
    print("- Circuit breaker protege contra falhas consecutivas")
    print("- Fallback sempre disponível como última opção")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main() 