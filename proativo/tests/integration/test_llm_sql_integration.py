#!/usr/bin/env python3
"""
Script de teste para integração completa LLM-SQL com endpoint de chat.

Este script verifica:
1. Funcionamento do AvailabilityRouter
2. Integração com endpoint de chat
3. Roteamento automático entre LLM SQL e sistema de regras
4. Fallback e tratamento de erros
5. Fluxo end-to-end completo
"""

import asyncio
import sys
import os
import json
from datetime import datetime
from typing import Dict, Any, List
from colorama import init, Fore, Style
import requests
import time

# Adicionar diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Inicializar colorama
init(autoreset=True)

# Configuração do servidor
BASE_URL = "http://localhost:8000"
CHAT_ENDPOINT = f"{BASE_URL}/chat/"
HEALTH_ENDPOINT = f"{BASE_URL}/health"


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


def check_server_health() -> bool:
    """Verifica se o servidor está rodando."""
    try:
        response = requests.get(HEALTH_ENDPOINT, timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print_success(f"Servidor rodando: {health_data.get('status', 'unknown')}")
            return True
        else:
            print_error(f"Servidor retornou status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print_error(f"Erro ao conectar com servidor: {str(e)}")
        return False


def send_chat_message(message: str, include_debug: bool = True) -> Dict[str, Any]:
    """Envia mensagem para o endpoint de chat."""
    payload = {
        "message": message,
        "include_debug": include_debug,
        "session_id": "test-session-llm-integration"
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            CHAT_ENDPOINT, 
            json=payload, 
            timeout=30,
            headers={"Content-Type": "application/json"}
        )
        response_time = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            data = response.json()
            data["_test_response_time"] = response_time
            return data
        else:
            print_error(f"Erro HTTP {response.status_code}: {response.text}")
            return {"error": f"HTTP {response.status_code}", "details": response.text}
            
    except requests.exceptions.RequestException as e:
        print_error(f"Erro na requisição: {str(e)}")
        return {"error": "request_failed", "details": str(e)}


def analyze_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """Analisa resposta do chat para extrair informações de teste."""
    analysis = {
        "success": "error" not in response,
        "response_time": response.get("_test_response_time", 0),
        "processing_time": response.get("processing_time_ms", 0),
        "confidence": response.get("confidence_score", 0),
        "sources": response.get("sources_used", []),
        "route_decision": None,
        "llm_sql_used": False,
        "data_found": response.get("data_found", 0),
        "suggestions": len(response.get("suggested_followup", []))
    }
    
    # Extrair informações de debug se disponíveis
    debug_info = response.get("debug_info", {})
    if debug_info:
        routing_info = debug_info.get("routing", {})
        analysis["route_decision"] = routing_info.get("decision")
        analysis["route_reason"] = routing_info.get("reason")
        analysis["llm_sql_used"] = routing_info.get("decision") == "llm_sql"
        analysis["llm_sql_success"] = routing_info.get("llm_sql_success")
        analysis["method_used"] = routing_info.get("method_used")
    
    return analysis


def test_health_check():
    """Testa se o servidor está saudável."""
    print_header("1. TESTE DE HEALTH CHECK")
    
    if check_server_health():
        print_success("Servidor está operacional")
        return True
    else:
        print_error("Servidor não está acessível")
        return False


def test_routing_decisions():
    """Testa diferentes decisões de roteamento."""
    print_header("2. TESTE DE DECISÕES DE ROTEAMENTO")
    
    test_cases = [
        {
            "message": "Quantos transformadores temos?",
            "expected_route": "rule_based",
            "description": "Query simples → Rule-based"
        },
        {
            "message": "Analise a evolução dos custos de manutenção dos transformadores nos últimos 6 meses",
            "expected_route": "llm_sql",
            "description": "Query complexa → LLM SQL"
        },
        {
            "message": "Liste todos os equipamentos",
            "expected_route": "rule_based", 
            "description": "Query muito simples → Rule-based"
        },
        {
            "message": "Compare a eficiência entre manutenção preventiva e corretiva por tipo de equipamento",
            "expected_route": "llm_sql",
            "description": "Análise complexa → LLM SQL"
        }
    ]
    
    results = []
    
    for test in test_cases:
        print_subheader(f"Testando: {test['description']}")
        print_info(f"Query: '{test['message']}'")
        
        response = send_chat_message(test["message"])
        analysis = analyze_response(response)
        
        if analysis["success"]:
            actual_route = analysis["route_decision"]
            print_info(f"Rota decidida: {actual_route}")
            print_info(f"Tempo de resposta: {analysis['response_time']:.0f}ms")
            print_info(f"Confiança: {analysis['confidence']:.2f}")
            
            if actual_route == test["expected_route"]:
                print_success("Roteamento correto!")
                results.append(True)
            else:
                print_warning(f"Roteamento inesperado (esperado: {test['expected_route']})")
                results.append(False)
        else:
            print_error(f"Falha na requisição: {response.get('error', 'unknown')}")
            results.append(False)
    
    success_rate = sum(results) / len(results) * 100
    print_info(f"\nTaxa de sucesso no roteamento: {success_rate:.1f}% ({sum(results)}/{len(results)})")
    
    return success_rate >= 75  # 75% de sucesso mínimo


def test_llm_sql_functionality():
    """Testa funcionalidade específica do LLM SQL."""
    print_header("3. TESTE DE FUNCIONALIDADE LLM SQL")
    
    # Queries que devem usar LLM SQL
    llm_queries = [
        "Top 5 equipamentos com maior custo de manutenção",
        "Tendência de falhas por tipo de equipamento este ano",
        "Equipamentos críticos que não tiveram manutenção nos últimos 3 meses",
        "Custo médio de manutenção por subestação"
    ]
    
    results = []
    llm_responses = []
    
    for query in llm_queries:
        print_subheader(f"Query LLM: {query}")
        
        response = send_chat_message(query)
        analysis = analyze_response(response)
        
        if analysis["success"]:
            print_info(f"Rota: {analysis['route_decision']}")
            print_info(f"LLM SQL usado: {analysis['llm_sql_used']}")
            print_info(f"Método: {analysis.get('method_used', 'unknown')}")
            print_info(f"Dados encontrados: {analysis['data_found']}")
            print_info(f"Tempo: {analysis['processing_time']}ms")
            
            # Verificar se usou LLM SQL ou explicar por que não usou
            if analysis["llm_sql_used"]:
                if analysis.get("llm_sql_success"):
                    print_success("LLM SQL executado com sucesso!")
                    results.append(True)
                else:
                    print_warning("LLM SQL tentado mas falhou")
                    results.append(False)
            else:
                reason = analysis.get("route_reason", "unknown")
                print_warning(f"LLM SQL não usado: {reason}")
                results.append(False)
            
            llm_responses.append({
                "query": query,
                "analysis": analysis,
                "response_preview": response.get("response", "")[:100] + "..."
            })
        else:
            print_error(f"Falha: {response.get('error', 'unknown')}")
            results.append(False)
    
    success_rate = sum(results) / len(results) * 100
    print_info(f"\nTaxa de sucesso LLM SQL: {success_rate:.1f}% ({sum(results)}/{len(results)})")
    
    return success_rate >= 50, llm_responses  # 50% de sucesso mínimo para LLM


def test_fallback_system():
    """Testa sistema de fallback."""
    print_header("4. TESTE DE SISTEMA DE FALLBACK")
    
    # Queries que podem forçar fallback
    fallback_queries = [
        "Esta query não faz sentido e deve gerar fallback @@@@",
        "",  # Query vazia
        "SELECT * FROM tabela_inexistente;",  # SQL inválido
    ]
    
    results = []
    
    for query in fallback_queries:
        if not query:
            print_subheader("Query vazia")
            continue
            
        print_subheader(f"Query problemática: {query}")
        
        response = send_chat_message(query)
        analysis = analyze_response(response)
        
        if analysis["success"]:
            route = analysis["route_decision"]
            print_info(f"Rota: {route}")
            print_info(f"Sugestões fornecidas: {analysis['suggestions']}")
            
            # Fallback pode ser explícito ou através de resposta de fallback do LLM
            if route == "fallback" or analysis["confidence"] < 0.5:
                print_success("Sistema de fallback ativado corretamente")
                results.append(True)
            else:
                print_warning("Sistema tentou processar query problemática")
                results.append(False)
        else:
            # Erro HTTP é aceitável para queries ruins
            print_info("Query rejeitada pelo sistema (comportamento esperado)")
            results.append(True)
    
    success_rate = sum(results) / max(1, len(results)) * 100
    print_info(f"\nTaxa de sucesso no fallback: {success_rate:.1f}% ({sum(results)}/{max(1, len(results))})")
    
    return success_rate >= 80  # 80% de sucesso no fallback


def test_end_to_end_scenarios():
    """Testa cenários end-to-end realistas."""
    print_header("5. TESTE DE CENÁRIOS END-TO-END")
    
    scenarios = [
        {
            "name": "Consulta de Status",
            "message": "Qual o status dos transformadores na subestação norte?",
            "min_confidence": 0.6
        },
        {
            "name": "Análise de Custos",
            "message": "Quanto gastamos em manutenção corretiva este mês?",
            "min_confidence": 0.7
        },
        {
            "name": "Busca por Equipamento",
            "message": "Informações sobre o transformador TR-001",
            "min_confidence": 0.8
        },
        {
            "name": "Análise Temporal",
            "message": "Histórico de manutenções dos últimos 30 dias",
            "min_confidence": 0.6
        }
    ]
    
    results = []
    scenario_details = []
    
    for scenario in scenarios:
        print_subheader(f"Cenário: {scenario['name']}")
        print_info(f"Query: '{scenario['message']}'")
        
        response = send_chat_message(scenario["message"])
        analysis = analyze_response(response)
        
        if analysis["success"]:
            confidence = analysis["confidence"]
            response_text = response.get("response", "")
            
            print_info(f"Confiança: {confidence:.2f}")
            print_info(f"Rota: {analysis['route_decision']}")
            print_info(f"Resposta: {response_text[:150]}...")
            
            # Verificar se atende critérios mínimos
            if confidence >= scenario["min_confidence"]:
                print_success("Cenário executado com sucesso!")
                results.append(True)
            else:
                print_warning(f"Confiança baixa (min: {scenario['min_confidence']})")
                results.append(False)
            
            scenario_details.append({
                "name": scenario["name"],
                "success": confidence >= scenario["min_confidence"],
                "confidence": confidence,
                "route": analysis["route_decision"],
                "response_time": analysis["response_time"]
            })
        else:
            print_error(f"Falha: {response.get('error', 'unknown')}")
            results.append(False)
    
    success_rate = sum(results) / len(results) * 100
    print_info(f"\nTaxa de sucesso end-to-end: {success_rate:.1f}% ({sum(results)}/{len(results)})")
    
    return success_rate >= 70, scenario_details


def generate_test_report(results: Dict[str, Any]):
    """Gera relatório final dos testes."""
    print_header("RELATÓRIO FINAL DE INTEGRAÇÃO")
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    
    print_info(f"Testes executados: {total_tests}")
    print_info(f"Testes bem-sucedidos: {passed_tests}")
    print_info(f"Taxa de sucesso geral: {passed_tests/total_tests*100:.1f}%")
    
    print("\n" + "="*60)
    for test_name, success in results.items():
        status = print_success if success else print_error
        icon = "✓" if success else "✗"
        print(f"{icon} {test_name}: {'PASSOU' if success else 'FALHOU'}")
    
    print("\n" + "="*60)
    
    if passed_tests == total_tests:
        print_success("🎉 TODOS OS TESTES PASSARAM! Integração LLM-SQL funcionando corretamente.")
    elif passed_tests >= total_tests * 0.8:
        print_warning(f"⚠️  {passed_tests}/{total_tests} testes passaram. Sistema majoritariamente funcional.")
    else:
        print_error(f"❌ Apenas {passed_tests}/{total_tests} testes passaram. Necessária revisão.")
    
    return passed_tests == total_tests


def main():
    """Executa todos os testes de integração."""
    print_header("TESTE DE INTEGRAÇÃO LLM-SQL COMPLETO")
    print_info(f"Iniciado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_info(f"Endpoint: {CHAT_ENDPOINT}")
    
    # Resultados dos testes
    test_results = {}
    
    # 1. Health Check
    test_results["Health Check"] = test_health_check()
    if not test_results["Health Check"]:
        print_error("⚠️  Servidor não está rodando. Certifique-se de que o servidor está ativo!")
        print_info("Para iniciar o servidor: cd proativo && python -m uvicorn src.api.main:app --reload")
        return False
    
    # 2. Teste de Roteamento
    test_results["Roteamento Inteligente"] = test_routing_decisions()
    
    # 3. Teste LLM SQL
    llm_success, llm_details = test_llm_sql_functionality()
    test_results["Funcionalidade LLM SQL"] = llm_success
    
    # 4. Teste Fallback
    test_results["Sistema de Fallback"] = test_fallback_system()
    
    # 5. Cenários End-to-End
    e2e_success, e2e_details = test_end_to_end_scenarios()
    test_results["Cenários End-to-End"] = e2e_success
    
    # 6. Relatório Final
    overall_success = generate_test_report(test_results)
    
    # Salvar detalhes em arquivo
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "test_results": test_results,
        "llm_details": llm_details,
        "e2e_details": e2e_details,
        "overall_success": overall_success
    }
    
    with open("integration_test_report.json", "w") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    
    print_info("📄 Relatório detalhado salvo em: integration_test_report.json")
    
    return overall_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 