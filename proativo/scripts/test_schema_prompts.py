#!/usr/bin/env python3
"""
Script de teste para o sistema de prompts elaborado.

Este script verifica:
1. Carregamento correto do schema
2. Detecção de categorias
3. Geração de prompts contextualizados
4. Qualidade das queries SQL geradas
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import Dict, Any, List
from colorama import init, Fore, Style

# Adicionar diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.services.llm_schema_prompts import LLMSchemaPrompts, QueryCategory
from src.api.services.llm_sql_generator import LLMSQLGenerator
from src.utils.logger import get_logger

# Inicializar colorama
init(autoreset=True)

# Configurar logger
logger = get_logger(__name__)


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


def test_schema_loading():
    """Testa o carregamento do schema."""
    print_header("1. TESTE DE CARREGAMENTO DO SCHEMA")
    
    try:
        prompts = LLMSchemaPrompts()
        
        # Verificar tabelas carregadas
        print_info("Tabelas carregadas:")
        for table_name, table in prompts.schema_tables.items():
            print(f"  - {table_name}: {len(table.columns)} colunas, {len(table.relationships)} relacionamentos")
        
        # Verificar resumo do schema
        summary = prompts.get_schema_summary()
        print_info(f"\nResumo do Schema:")
        print(f"  - Total de tabelas: {summary['total_tables']}")
        print(f"  - Domínio: {summary['domain']}")
        print(f"  - Entidades principais: {', '.join(summary['main_entities'])}")
        
        # Verificar regras de validação
        rules = prompts.get_validation_rules()
        print_info(f"\nRegras de validação: {len(rules)} regras carregadas")
        
        print_success("Schema carregado com sucesso!")
        return True
        
    except Exception as e:
        print_error(f"Erro ao carregar schema: {str(e)}")
        return False


def test_category_detection():
    """Testa a detecção de categorias."""
    print_header("2. TESTE DE DETECÇÃO DE CATEGORIAS")
    
    try:
        prompts = LLMSchemaPrompts()
        
        # Casos de teste
        test_cases = [
            ("Qual o status dos equipamentos?", QueryCategory.STATUS),
            ("Liste as manutenções preventivas", QueryCategory.MAINTENANCE),
            ("Análise de temperatura dos transformadores", QueryCategory.ANALYSIS),
            ("Quanto gastamos em manutenção este ano?", QueryCategory.COSTS),
            ("Histórico do transformador TR-001", QueryCategory.TIMELINE),
            ("Top 10 equipamentos com mais falhas", QueryCategory.RANKING),
            ("Previsão de falhas para próximo mês", QueryCategory.PREDICTIVE),
            ("Auditoria de conformidade com NR-10", QueryCategory.AUDIT),
            ("Quantos transformadores temos?", None),  # Categoria genérica
        ]
        
        success_count = 0
        for query, expected_category in test_cases:
            detected = prompts._detect_category(query)
            
            if detected == expected_category:
                print_success(f"'{query}' → {detected}")
                success_count += 1
            else:
                print_error(f"'{query}' → Esperado: {expected_category}, Detectado: {detected}")
        
        print_info(f"\nTaxa de acerto: {success_count}/{len(test_cases)} ({success_count/len(test_cases)*100:.1f}%)")
        
        return success_count == len(test_cases)
        
    except Exception as e:
        print_error(f"Erro na detecção de categorias: {str(e)}")
        return False


async def test_prompt_generation():
    """Testa a geração de prompts contextualizados."""
    print_header("3. TESTE DE GERAÇÃO DE PROMPTS")
    
    try:
        prompts = LLMSchemaPrompts()
        
        # Queries de teste por categoria
        test_queries = [
            "Equipamentos críticos em manutenção",
            "Custo total de manutenção por tipo",
            "Tendência de temperatura dos transformadores",
            "Timeline de eventos do disjuntor DJ-042",
        ]
        
        for query in test_queries:
            print_subheader(f"Query: {query}")
            
            # Gerar prompt base
            base_prompt = prompts.get_base_prompt()
            print_info(f"Prompt base tem {len(base_prompt)} caracteres")
            
            # Gerar prompt enhanced
            enhanced_prompt = prompts.get_enhanced_prompt(query)
            print_info(f"Prompt enhanced tem {len(enhanced_prompt)} caracteres")
            
            # Verificar se o prompt inclui elementos essenciais
            essential_elements = [
                "DATABASE SCHEMA",
                "equipments",
                "maintenances",
                "CONTEXT",
                "EXAMPLES",
                query  # A query original deve estar no prompt
            ]
            
            missing = []
            for element in essential_elements:
                if element not in enhanced_prompt:
                    missing.append(element)
            
            if not missing:
                print_success("Prompt contém todos elementos essenciais")
            else:
                print_error(f"Elementos faltantes no prompt: {missing}")
        
        return True
        
    except Exception as e:
        print_error(f"Erro na geração de prompts: {str(e)}")
        return False


async def test_sql_generation_quality():
    """Testa a qualidade das queries SQL geradas."""
    print_header("4. TESTE DE QUALIDADE SQL COM PROMPTS ELABORADOS")
    
    # Verificar se LLM está habilitado
    from src.api.config import get_settings
    settings = get_settings()
    
    if not settings.llm_sql_feature_enabled:
        print_info("LLM SQL está desabilitado. Habilitando temporariamente para teste...")
        settings.llm_sql_feature_enabled = True
    
    try:
        generator = LLMSQLGenerator()
        
        # Queries de teste diversificadas
        test_queries = [
            # Status
            {
                "query": "Quantos equipamentos críticos estão em manutenção?",
                "expected_elements": ["COUNT", "criticality", "Critical", "status", "Maintenance"]
            },
            # Manutenção
            {
                "query": "Liste as próximas 5 manutenções preventivas programadas",
                "expected_elements": ["maintenances", "Preventive", "scheduled_date", "LIMIT 5"]
            },
            # Análise
            {
                "query": "Qual a temperatura média dos transformadores este mês?",
                "expected_elements": ["AVG", "data_history", "Transformer", "Temperature", "timestamp"]
            },
            # Custos
            {
                "query": "Total gasto em manutenção corretiva este ano",
                "expected_elements": ["SUM", "actual_cost", "Corrective", "EXTRACT(YEAR"]
            },
            # Timeline
            {
                "query": "Histórico de manutenções do transformador TR-001",
                "expected_elements": ["equipments", "maintenances", "code", "TR-001", "ORDER BY"]
            },
            # Ranking
            {
                "query": "Top 10 equipamentos com maior custo de manutenção",
                "expected_elements": ["SUM", "actual_cost", "GROUP BY", "ORDER BY", "LIMIT 10"]
            },
        ]
        
        success_count = 0
        total_time = 0
        
        for test in test_queries:
            print_subheader(f"Query: {test['query']}")
            
            # Gerar SQL
            result = await generator.generate_sql(test['query'])
            
            if result["success"]:
                sql = result["sql"]
                print_info(f"SQL gerado em {result['generation_time_ms']:.0f}ms")
                print_info(f"Categoria detectada: {result.get('query_category', 'None')}")
                print(f"\n{Fore.MAGENTA}SQL:\n{sql}\n")
                
                # Verificar elementos esperados
                missing_elements = []
                for element in test["expected_elements"]:
                    if element.lower() not in sql.lower():
                        missing_elements.append(element)
                
                if not missing_elements:
                    print_success("Query contém todos elementos esperados")
                    success_count += 1
                else:
                    print_error(f"Elementos faltantes: {missing_elements}")
                
                total_time += result['generation_time_ms']
            else:
                print_error(f"Erro ao gerar SQL: {result['error']}")
        
        # Estatísticas finais
        print_header("ESTATÍSTICAS FINAIS")
        print_info(f"Taxa de sucesso: {success_count}/{len(test_queries)} ({success_count/len(test_queries)*100:.1f}%)")
        print_info(f"Tempo médio de geração: {total_time/len(test_queries):.0f}ms")
        
        # Health check
        health = await generator.health_check()
        print_info(f"Status do gerador: {health['status']}")
        print_info(f"Schema carregado: {health.get('schema_loaded', False)}")
        print_info(f"Total de tabelas: {health.get('total_tables', 0)}")
        
        return success_count >= len(test_queries) * 0.8  # 80% de sucesso
        
    except Exception as e:
        print_error(f"Erro no teste de geração SQL: {str(e)}")
        return False


async def main():
    """Executa todos os testes."""
    print_header("TESTE DO SISTEMA DE PROMPTS ELABORADO")
    print_info(f"Iniciado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("Carregamento do Schema", test_schema_loading),
        ("Detecção de Categorias", test_category_detection),
        ("Geração de Prompts", test_prompt_generation),
        ("Qualidade SQL", test_sql_generation_quality),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"Erro no teste {test_name}: {str(e)}")
            results.append((test_name, False))
    
    # Resumo final
    print_header("RESUMO DOS TESTES")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        if result:
            print_success(f"{test_name}: PASSOU")
        else:
            print_error(f"{test_name}: FALHOU")
    
    print_info(f"\nTotal: {passed}/{total} testes passaram ({passed/total*100:.1f}%)")
    
    # Retornar código de saída
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    asyncio.run(main()) 