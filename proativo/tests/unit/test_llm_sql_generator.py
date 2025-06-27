#!/usr/bin/env python3
"""
Script de teste para o LLM SQL Generator.

Testa a funcionalidade básica de geração de SQL a partir de perguntas em linguagem natural.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Adicionar diretório pai ao PATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.services.llm_sql_generator import LLMSQLGenerator
from src.utils.logger import get_logger

# Configurar logger
logger = get_logger(__name__)

# Lista de perguntas de teste
TEST_QUESTIONS = [
    # Perguntas básicas
    "Quantos equipamentos temos no total?",
    "Liste todos os transformadores",
    "Quais equipamentos estão em manutenção?",
    
    # Perguntas com filtros
    "Mostre os equipamentos críticos que estão ativos",
    "Equipamentos instalados em 2024",
    
    # Perguntas com JOINs
    "Qual foi a última manutenção do transformador T001?",
    "Quantas manutenções cada equipamento teve?",
    
    # Perguntas com agregação
    "Qual o custo total de manutenções este ano?",
    "Quantas manutenções preventivas foram feitas?",
    
    # Pergunta inválida (deve falhar na validação)
    "Delete todos os equipamentos"
]


async def test_sql_generation():
    """Testa a geração de SQL para várias perguntas."""
    print("\n" + "="*80)
    print("TESTE DO LLM SQL GENERATOR")
    print("="*80)
    
    # Verificar se LLM_SQL_FEATURE_ENABLED está como true
    from src.api.config import get_settings
    settings = get_settings()
    
    if not settings.llm_sql_feature_enabled:
        print("\n⚠️  AVISO: LLM_SQL_FEATURE_ENABLED está desabilitado no .env")
        print("   Para habilitar, defina: LLM_SQL_FEATURE_ENABLED=true")
        print("   Continuando com teste mesmo assim...\n")
    
    try:
        # Temporariamente habilitar a feature para teste
        original_value = settings.llm_sql_feature_enabled
        settings.llm_sql_feature_enabled = True
        
        # Inicializar gerador
        generator = LLMSQLGenerator()
        
        # Testar health check
        print("\n1. Testando Health Check...")
        health = await generator.health_check()
        print(f"   Status: {health['status']}")
        print(f"   Model: {health['model']}")
        print(f"   Feature Enabled: {health['feature_enabled']}")
        
        # Testar geração de SQL
        print("\n2. Testando Geração de SQL:")
        print("-" * 60)
        
        success_count = 0
        failed_count = 0
        
        for i, question in enumerate(TEST_QUESTIONS, 1):
            print(f"\n{i}. Pergunta: {question}")
            
            result = await generator.generate_sql(question)
            
            if result["success"]:
                success_count += 1
                print(f"   ✅ SQL Gerado: {result['sql']}")
                print(f"   Tempo: {result['generation_time_ms']:.0f}ms")
            else:
                failed_count += 1
                print(f"   ❌ Erro: {result['error']}")
            
            # Pequena pausa entre requisições
            await asyncio.sleep(0.5)
        
        # Restaurar valor original
        settings.llm_sql_feature_enabled = original_value
        
        # Resumo
        print("\n" + "="*80)
        print("RESUMO DO TESTE")
        print("="*80)
        print(f"Total de perguntas: {len(TEST_QUESTIONS)}")
        print(f"✅ Sucesso: {success_count}")
        print(f"❌ Falhas: {failed_count}")
        print(f"Taxa de sucesso: {(success_count/len(TEST_QUESTIONS)*100):.1f}%")
        
        # Avisos importantes
        print("\n⚠️  OBSERVAÇÕES:")
        print("   - As queries geradas precisam passar pelo SQL Validator antes de execução")
        print("   - Este é apenas um teste de geração, não de execução")
        print("   - Para usar em produção, habilite LLM_SQL_FEATURE_ENABLED=true no .env")
        
    except Exception as e:
        logger.error(f"Erro durante teste: {str(e)}", exc_info=True)
        print(f"\n❌ Erro crítico: {str(e)}")
        return 1
    
    return 0


def main():
    """Função principal."""
    # Carregar variáveis de ambiente
    load_dotenv()
    
    # Executar teste
    exit_code = asyncio.run(test_sql_generation())
    sys.exit(exit_code)


if __name__ == "__main__":
    main() 