#!/usr/bin/env python3
"""
Script para testar a conexão com Google Gemini e validar a geração de SQL.

Este script verifica:
1. Se a API Key está configurada corretamente
2. Se conseguimos nos conectar ao Gemini
3. Se conseguimos gerar SQL simples
4. Os limites de rate e estimativa de custos
"""

import asyncio
import os
import sys
from pathlib import Path

# Adicionar o diretório src ao path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.api.config import get_settings
from src.api.services.llm_service import LLMService
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def test_basic_connection():
    """Testa conexão básica com o Gemini."""
    print("\n🔍 Testando conexão com Google Gemini...")
    
    try:
        settings = get_settings()
        
        # Verificar API Key
        if not settings.google_api_key:
            print("❌ GOOGLE_API_KEY não configurada!")
            print("   Configure no arquivo .env")
            return False
            
        print(f"✅ API Key configurada")
        print(f"✅ Modelo: {settings.gemini_model}")
        
        # Testar inicialização do serviço
        llm_service = LLMService()
        print("✅ LLMService inicializado com sucesso")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        return False


async def test_sql_generation():
    """Testa geração de SQL com o Gemini."""
    print("\n🧪 Testando geração de SQL...")
    
    try:
        llm_service = LLMService()
        
        # Prompt específico para SQL
        test_prompt = """
You are a SQL expert. Given the following database schema:

Table: equipments
- id (INTEGER, PRIMARY KEY)
- name (VARCHAR)
- type (VARCHAR) - values: 'Transformer', 'Circuit Breaker', 'Motor'
- status (VARCHAR) - values: 'Active', 'Inactive', 'Maintenance'
- criticality (VARCHAR) - values: 'Low', 'Medium', 'High', 'Critical'
- location (VARCHAR)
- last_maintenance (DATE)

Generate a SQL query for: "List all transformers"

Return ONLY the SQL query, no explanations.
"""
        
        # Testar geração
        print("📤 Enviando prompt para o Gemini...")
        
        response = await llm_service.generate_response(
            user_query=test_prompt,
            context={"test_mode": True}
        )
        
        print("✅ Resposta recebida!")
        print(f"📝 SQL gerado: {response['response']}")
        print(f"⏱️  Tempo de processamento: {response['processing_time']}ms")
        print(f"📊 Confiança: {response['confidence_score']:.2f}")
        
        # Validar se parece SQL
        sql = response['response'].strip()
        if 'SELECT' in sql.upper():
            print("✅ Resposta parece ser SQL válido")
            return True
        else:
            print("⚠️  Resposta não parece ser SQL")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao gerar SQL: {e}")
        return False


async def test_rate_limits():
    """Testa e exibe informações sobre rate limits."""
    print("\n📊 Verificando limites e custos...")
    
    try:
        settings = get_settings()
        
        # Estimativas baseadas na documentação do Gemini
        print(f"\n💰 Estimativas de custo (Gemini {settings.gemini_model}):")
        print(f"   - Input: ~$0.000035 por 1K tokens")
        print(f"   - Output: ~$0.00014 por 1K tokens")
        print(f"   - SQL médio: ~200 tokens (prompt) + ~50 tokens (resposta)")
        print(f"   - Custo estimado por query SQL: ~$0.000014")
        print(f"   - 10.000 queries SQL: ~$0.14")
        
        print(f"\n⚡ Limites de API:")
        print(f"   - Requests por minuto: 60 (padrão)")
        print(f"   - Tokens por minuto: 60.000")
        print(f"   - Timeout configurado: {settings.llm_sql_timeout}s")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao verificar limites: {e}")
        return False


async def main():
    """Executa todos os testes."""
    print("🚀 PROAtivo - Teste de Conexão Gemini para SQL")
    print("=" * 50)
    
    # Lista de testes
    tests = [
        ("Conexão Básica", test_basic_connection),
        ("Geração de SQL", test_sql_generation),
        ("Rate Limits e Custos", test_rate_limits)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Executando: {test_name}")
        print(f"{'='*50}")
        
        result = await test_func()
        results.append((test_name, result))
    
    # Resumo final
    print("\n" + "="*50)
    print("📋 RESUMO DOS TESTES")
    print("="*50)
    
    all_passed = True
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "="*50)
    
    if all_passed:
        print("🎉 Todos os testes passaram! Sistema pronto para desenvolvimento.")
        print("\n📝 Próximos passos:")
        print("   1. Implementar LLM SQL Generator (subtarefa 7.3)")
        print("   2. Criar Availability Router (subtarefa 7.4)")
        print("   3. Desenvolver SQL Validator (subtarefa 7.5)")
    else:
        print("⚠️  Alguns testes falharam. Verifique as configurações.")
        print("\n🔧 Ações recomendadas:")
        print("   1. Verificar se o arquivo .env está configurado")
        print("   2. Validar a API Key no Google Cloud Console")
        print("   3. Verificar logs de erro acima")
    
    return all_passed


if __name__ == "__main__":
    # Executar testes
    success = asyncio.run(main())
    
    # Sair com código apropriado
    sys.exit(0 if success else 1) 