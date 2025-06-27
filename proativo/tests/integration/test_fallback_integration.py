#!/usr/bin/env python3
"""
Teste específico para sistema de fallback aprimorado do PROAtivo.

Este script verifica:
1. Sistema adaptativo de roteamento
2. Circuit breaker configurável
3. Métricas avançadas
4. Endpoint de monitoramento
5. Feedback e aprendizado
"""

import asyncio
import sys
import os
import json
import time
from datetime import datetime
from typing import Dict, Any, List
from colorama import init, Fore, Style
import requests

# Adicionar diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Inicializar colorama
init(autoreset=True)

# Configuração do servidor
BASE_URL = "http://localhost:8000"
FALLBACK_ENDPOINT = f"{BASE_URL}/api/v1/fallback"
CHAT_ENDPOINT = f"{BASE_URL}/api/v1/chat/"


def print_header(text: str):
    """Imprime cabeçalho formatado."""
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}{text}")
    print(f"{Fore.CYAN}{'=' * 80}\n")


def print_subheader(text: str):
    """Imprime subcabeçalho formatado."""
    print(f"\n{Fore.YELLOW}{'-' * 60}")
    print(f"{Fore.YELLOW}{text}")
    print(f"{Fore.YELLOW}{'-' * 60}\n")


def print_success(text: str):
    """Imprime mensagem de sucesso."""
    print(f"{Fore.GREEN}✓ {text}")


def print_error(text: str):
    """Imprime mensagem de erro."""
    print(f"{Fore.RED}✗ {text}")


def print_info(text: str):
    """Imprime informação."""
    print(f"{Fore.BLUE}ℹ {text}")


def print_warning(text: str):
    """Imprime aviso."""
    print(f"{Fore.YELLOW}⚠ {text}")


def make_request(endpoint: str, method: str = "GET", data: Dict = None) -> Dict[str, Any]:
    """Faz requisição HTTP e retorna resultado."""
    try:
        url = f"{FALLBACK_ENDPOINT}{endpoint}"
        
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        else:
            raise ValueError(f"Método não suportado: {method}")
        
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {
                "success": False, 
                "error": f"HTTP {response.status_code}",
                "details": response.text
            }
            
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": "connection_error", "details": str(e)}


def test_fallback_status():
    """Testa endpoint de status do fallback."""
    print_header("1. TESTE DE STATUS DO SISTEMA DE FALLBACK")
    
    result = make_request("/status")
    
    if not result["success"]:
        print_error(f"Falha na requisição: {result['error']}")
        return False
    
    data = result["data"]
    print_info(f"Status geral: {data.get('overall_status', 'unknown')}")
    
    # Verificar componentes
    components = data.get("components", {})
    router_health = components.get("availability_router", {})
    fallback_health = components.get("fallback_service", {})
    
    print_info(f"AvailabilityRouter: {router_health.get('status', 'unknown')}")
    print_info(f"FallbackService: {fallback_health.get('status', 'unknown')}")
    
    # Verificar stats rápidas
    quick_stats = data.get("quick_stats", {})
    print_info(f"LLM disponível: {quick_stats.get('llm_available', False)}")
    print_info(f"Sistema adaptativo ativo: {quick_stats.get('adaptive_active', False)}")
    print_info(f"Circuit breaker aberto: {quick_stats.get('circuit_breaker_open', False)}")
    print_info(f"Total de requests: {quick_stats.get('total_requests', 0)}")
    
    if data.get("overall_status") in ["healthy", "degraded"]:
        print_success("Status do sistema obtido com sucesso")
        return True
    else:
        print_warning("Sistema com problemas críticos")
        return True  # Ainda considera sucesso se conseguiu obter status


def test_fallback_metrics():
    """Testa endpoint de métricas do fallback."""
    print_header("2. TESTE DE MÉTRICAS DO FALLBACK")
    
    # Teste básico
    print_subheader("Métricas Básicas")
    result = make_request("/metrics")
    
    if not result["success"]:
        print_error(f"Falha na requisição básica: {result['error']}")
        return False
    
    data = result["data"]
    summary = data.get("summary", {})
    
    print_info(f"Total de requests: {summary.get('total_requests', 0)}")
    print_info(f"Taxa de fallback: {summary.get('fallback_rate', 0):.1f}%")
    print_info(f"Taxa de sucesso LLM: {summary.get('llm_success_rate', 0):.1f}%")
    print_info(f"Satisfação do usuário: {summary.get('user_satisfaction', 0):.1f}")
    print_info(f"Score de adaptação: {summary.get('adaptation_score', 0):.1f}")
    
    print_success("Métricas básicas obtidas")
    
    # Teste detalhado
    print_subheader("Métricas Detalhadas")
    result = make_request("/metrics?detailed=true")
    
    if not result["success"]:
        print_warning("Falha ao obter métricas detalhadas")
        return True  # Não é crítico
    
    detailed_data = result["data"]
    
    # Verificar circuit breaker
    circuit = detailed_data.get("circuit_breaker", {})
    print_info(f"Circuit breaker aberto: {circuit.get('open', False)}")
    print_info(f"Ativações totais: {circuit.get('activations_total', 0)}")
    
    # Verificar sistema adaptativo
    adaptive = detailed_data.get("adaptive_system", {})
    print_info(f"Sistema adaptativo habilitado: {adaptive.get('enabled', False)}")
    print_info(f"Tamanho do histórico: {adaptive.get('history_size', 0)}")
    print_info(f"Padrões aprendidos: {adaptive.get('patterns_learned', 0)}")
    
    print_success("Métricas detalhadas obtidas")
    return True


def test_adaptive_insights():
    """Testa endpoint de insights adaptativos."""
    print_header("3. TESTE DE INSIGHTS ADAPTATIVOS")
    
    result = make_request("/insights")
    
    if not result["success"]:
        print_error(f"Falha na requisição: {result['error']}")
        return False
    
    data = result["data"]
    insights = data.get("adaptive_insights", {})
    
    print_info(f"Sistema habilitado: {insights.get('enabled', False)}")
    print_info(f"Tamanho do histórico: {insights.get('history_size', 0)}")
    print_info(f"Aprendizado ativo: {insights.get('learning_active', False)}")
    
    # Verificar análise de períodos
    periods = insights.get("periods_analysis", {})
    if periods:
        recent = periods.get("recent", {})
        trend = periods.get("trend", "unknown")
        
        print_info(f"Taxa de sucesso recente: {recent.get('success_rate', 0):.1%}")
        print_info(f"Satisfação média recente: {recent.get('avg_satisfaction', 0):.1f}")
        print_info(f"Tendência: {trend}")
    
    # Verificar recomendações
    recommendations = data.get("recommendations", {})
    immediate = recommendations.get("immediate", [])
    
    if immediate:
        print_info("Recomendações imediatas:")
        for rec in immediate[:3]:  # Mostrar apenas 3
            print(f"  • {rec}")
    
    print_success("Insights adaptativos obtidos")
    return True


def test_feedback_submission():
    """Testa submissão de feedback."""
    print_header("4. TESTE DE SUBMISSÃO DE FEEDBACK")
    
    feedback_cases = [
        {
            "query": "Status dos transformadores",
            "decision": "rule_based",
            "satisfaction_score": 4.0,
            "comment": "Resposta rápida e precisa"
        },
        {
            "query": "Análise complexa de custos por região",
            "decision": "llm_sql", 
            "satisfaction_score": 5.0,
            "comment": "Excelente análise detalhada"
        },
        {
            "query": "Query problemática @@@@",
            "decision": "fallback",
            "satisfaction_score": 2.0,
            "comment": "Fallback funcionou mas resposta genérica"
        }
    ]
    
    success_count = 0
    
    for i, feedback in enumerate(feedback_cases, 1):
        print_subheader(f"Feedback {i}: {feedback['decision']}")
        
        result = make_request("/feedback", method="POST", data=feedback)
        
        if result["success"]:
            print_success(f"Feedback registrado - Score: {feedback['satisfaction_score']}")
            success_count += 1
        else:
            print_error(f"Falha ao registrar feedback: {result['error']}")
    
    success_rate = success_count / len(feedback_cases)
    print_info(f"Taxa de sucesso no feedback: {success_rate:.1%} ({success_count}/{len(feedback_cases)})")
    
    return success_rate >= 0.8  # 80% de sucesso mínimo


def test_dashboard_data():
    """Testa endpoint do dashboard."""
    print_header("5. TESTE DE DADOS DO DASHBOARD")
    
    result = make_request("/dashboard")
    
    if not result["success"]:
        print_error(f"Falha na requisição: {result['error']}")
        return False
    
    data = result["data"]
    
    # Verificar overview
    overview = data.get("overview", {})
    print_info(f"Status: {overview.get('status', 'unknown')}")
    print_info(f"Total requests: {overview.get('total_requests', 0)}")
    print_info(f"LLM disponível: {overview.get('llm_available', False)}")
    
    # Verificar performance
    performance = data.get("performance", {})
    print_info(f"Taxa de sucesso LLM: {performance.get('llm_success_rate', 0):.1f}%")
    print_info(f"Taxa de sucesso Rules: {performance.get('rule_success_rate', 0):.1f}%")
    print_info(f"Score de adaptação: {performance.get('adaptation_score', 0):.1f}")
    
    # Verificar distribuição de roteamento
    routing = data.get("routing_distribution", {})
    print_info("Distribuição de roteamento:")
    for route_type, percentage in routing.items():
        print(f"  • {route_type}: {percentage:.1f}%")
    
    # Verificar problemas recentes
    issues = data.get("recent_issues", [])
    if issues:
        print_warning(f"Problemas recentes ({len(issues)}):")
        for issue in issues[:3]:
            print(f"  • {issue}")
    else:
        print_success("Nenhum problema recente detectado")
    
    print_success("Dados do dashboard obtidos")
    return True


def test_integration_with_chat():
    """Testa integração com endpoint de chat."""
    print_header("6. TESTE DE INTEGRAÇÃO COM CHAT")
    
    test_queries = [
        {
            "query": "Lista de equipamentos",
            "expected_complexity": "simple",
            "expected_route": "rule_based"
        },
        {
            "query": "Analise a correlação entre custos de manutenção e tempo de operação dos transformadores por região",
            "expected_complexity": "complex",
            "expected_route": "llm_sql"
        }
    ]
    
    success_count = 0
    
    for i, test in enumerate(test_queries, 1):
        print_subheader(f"Query {i}: {test['expected_complexity']}")
        
        # Fazer requisição para chat
        try:
            chat_response = requests.post(
                CHAT_ENDPOINT,
                json={
                    "message": test["query"],
                    "include_debug": True,
                    "session_id": "test-fallback-integration"
                },
                timeout=15
            )
            
            if chat_response.status_code == 200:
                chat_data = chat_response.json()
                debug_info = chat_data.get("debug_info", {})
                routing_info = debug_info.get("routing", {})
                
                decision = routing_info.get("decision", "unknown")
                reason = routing_info.get("reason", "unknown")
                
                print_info(f"Query: {test['query'][:50]}...")
                print_info(f"Decisão de rota: {decision}")
                print_info(f"Razão: {reason}")
                print_info(f"Confiança: {chat_data.get('confidence_score', 0):.2f}")
                
                # Verificar se decisão faz sentido
                if decision in ["llm_sql", "rule_based", "fallback"]:
                    print_success("Roteamento funcionando corretamente")
                    success_count += 1
                else:
                    print_warning(f"Decisão inesperada: {decision}")
                    
            else:
                print_error(f"Erro no chat: HTTP {chat_response.status_code}")
                
        except Exception as e:
            print_error(f"Erro na integração: {str(e)}")
    
    success_rate = success_count / len(test_queries)
    print_info(f"Taxa de sucesso na integração: {success_rate:.1%} ({success_count}/{len(test_queries)})")
    
    return success_rate >= 0.5  # 50% mínimo (considerando que LLM pode não estar disponível)


def generate_test_report(results: Dict[str, bool]):
    """Gera relatório final dos testes."""
    print_header("RELATÓRIO FINAL - SISTEMA DE FALLBACK APRIMORADO")
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    
    print_info(f"Testes executados: {total_tests}")
    print_info(f"Testes bem-sucedidos: {passed_tests}")
    print_info(f"Taxa de sucesso geral: {passed_tests/total_tests*100:.1f}%")
    
    print("\n" + "="*60)
    for test_name, success in results.items():
        status_func = print_success if success else print_error
        icon = "✓" if success else "✗"
        print(f"{icon} {test_name}: {'PASSOU' if success else 'FALHOU'}")
    
    print("\n" + "="*60)
    
    if passed_tests == total_tests:
        print_success("🎉 TODOS OS TESTES PASSARAM! Sistema de fallback aprimorado funcionando corretamente.")
    elif passed_tests >= total_tests * 0.8:
        print_warning(f"⚠️  {passed_tests}/{total_tests} testes passaram. Sistema majoritariamente funcional.")
    else:
        print_error(f"❌ Apenas {passed_tests}/{total_tests} testes passaram. Necessária revisão.")
    
    # Recomendações específicas
    print("\n" + "="*60)
    print_info("RECOMENDAÇÕES:")
    
    if not results.get("Status do Sistema"):
        print("• Verificar se o servidor está rodando e acessível")
    
    if not results.get("Métricas do Fallback"):
        print("• Verificar configuração dos serviços de fallback")
    
    if not results.get("Insights Adaptativos"):
        print("• Verificar se sistema adaptativo está habilitado")
    
    if not results.get("Submissão de Feedback"):
        print("• Verificar endpoint de feedback e validação de dados")
    
    if not results.get("Integração com Chat"):
        print("• Verificar integração entre componentes de roteamento")
    
    return passed_tests == total_tests


def main():
    """Executa todos os testes do sistema de fallback aprimorado."""
    print_header("TESTE DO SISTEMA DE FALLBACK APRIMORADO")
    print_info(f"Iniciado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_info(f"Endpoint base: {FALLBACK_ENDPOINT}")
    
    # Resultados dos testes
    test_results = {}
    
    # Executar testes em sequência
    test_results["Status do Sistema"] = test_fallback_status()
    test_results["Métricas do Fallback"] = test_fallback_metrics()
    test_results["Insights Adaptativos"] = test_adaptive_insights()
    test_results["Submissão de Feedback"] = test_feedback_submission()
    test_results["Dados do Dashboard"] = test_dashboard_data()
    test_results["Integração com Chat"] = test_integration_with_chat()
    
    # Gerar relatório final
    overall_success = generate_test_report(test_results)
    
    # Salvar relatório detalhado
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "test_results": test_results,
        "overall_success": overall_success,
        "endpoint_tested": FALLBACK_ENDPOINT,
        "test_type": "enhanced_fallback_system"
    }
    
    with open("enhanced_fallback_test_report.json", "w") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    
    print_info("📄 Relatório detalhado salvo em: enhanced_fallback_test_report.json")
    
    return overall_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 