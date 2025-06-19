#!/usr/bin/env python3
"""
Script de validação do sistema PROAtivo.
Verifica se todos os componentes estão funcionando corretamente.
"""

import asyncio
import sys
import traceback
from pathlib import Path

# Adicionar path do projeto (diretório pai para acessar src/)
sys.path.append(str(Path(__file__).parent.parent))

async def validate_imports():
    """Valida se todos os imports estão funcionando."""
    print("🔍 Validando imports...")
    
    results = {}
    
    # Testar LLMService
    try:
        from src.api.services.llm_service import LLMService
        print("✅ LLMService importado com sucesso")
        results["llm_service"] = True
    except Exception as e:
        print(f"❌ Erro ao importar LLMService: {e}")
        results["llm_service"] = False
    
    # Testar CacheService
    try:
        from src.api.services.cache_service import CacheService
        print("✅ CacheService importado com sucesso") 
        results["cache_service"] = True
    except Exception as e:
        print(f"❌ Erro ao importar CacheService: {e}")
        results["cache_service"] = False
    
    # Testar FallbackService
    try:
        from src.api.services.fallback_service import FallbackService
        print("✅ FallbackService importado com sucesso")
        results["fallback_service"] = True
    except Exception as e:
        print(f"❌ Erro ao importar FallbackService: {e}")
        results["fallback_service"] = False
    
    # Testar QueryProcessor
    try:
        from src.api.services.query_processor import QueryProcessor
        print("✅ QueryProcessor importado com sucesso")
        results["query_processor"] = True
    except Exception as e:
        print(f"❌ Erro ao importar QueryProcessor: {e}")
        results["query_processor"] = False
    
    return results

async def test_cache_service():
    """Testa funcionalidade básica do cache."""
    try:
        from src.api.services.cache_service import CacheService
        
        print("\n🧪 Testando CacheService...")
        cache = CacheService()
        
        # Teste básico
        test_response = {"answer": "Teste", "confidence": 0.8}
        cache_key = await cache.set("teste", test_response)
        
        cached = await cache.get("teste")
        
        if cached and cached.get("answer") == "Teste":
            print("✅ Cache funcionando corretamente")
            return True
        else:
            print("❌ Cache não retornou dados esperados")
            return False
            
    except Exception as e:
        print(f"❌ Erro no teste de cache: {e}")
        traceback.print_exc()
        return False

async def test_fallback_service():
    """Testa funcionalidade básica do fallback."""
    try:
        from src.api.services.fallback_service import FallbackService, FallbackTrigger
        
        print("\n🧪 Testando FallbackService...")
        fallback = FallbackService()
        
        # Teste básico
        response = fallback.generate_fallback_response(
            trigger=FallbackTrigger.OUT_OF_DOMAIN,
            original_query="Como está o tempo?",
            context={}
        )
        
        if response and response.message:
            print("✅ Fallback funcionando corretamente")
            return True
        else:
            print("❌ Fallback não gerou resposta")
            return False
            
    except Exception as e:
        print(f"❌ Erro no teste de fallback: {e}")
        traceback.print_exc()
        return False

async def test_query_processor():
    """Testa funcionalidade básica do processador de queries."""
    try:
        from src.api.services.query_processor import QueryProcessor
        
        print("\n🧪 Testando QueryProcessor...")
        processor = QueryProcessor()
        
        # Teste básico
        result = await processor.process_query("Status do transformador TR001")
        
        if result and result.query_type:
            print("✅ QueryProcessor funcionando corretamente")
            return True
        else:
            print("❌ QueryProcessor não processou query")
            return False
            
    except Exception as e:
        print(f"❌ Erro no teste de query processor: {e}")
        traceback.print_exc()
        return False

async def test_integration():
    """Teste de integração básica."""
    print("\n🔗 Testando integração entre serviços...")
    
    try:
        # Simular fluxo completo
        from src.api.services.cache_service import CacheService
        from src.api.services.query_processor import QueryProcessor
        
        cache = CacheService()
        processor = QueryProcessor()
        
        query = "Status dos equipamentos"
        
        # 1. Verificar cache (miss esperado)
        cached = await cache.get(query)
        if cached is None:
            print("✅ Cache miss detectado corretamente")
        
        # 2. Processar query
        processed = await processor.process_query(query)
        if processed:
            print("✅ Query processada com sucesso")
        
        # 3. Simular resposta e cache
        mock_response = {
            "response": "Simulação de resposta do LLM",
            "confidence": 0.8,
            "processing_time": 1000
        }
        
        await cache.set(query, mock_response)
        
        # 4. Verificar cache hit
        cached = await cache.get(query)
        if cached and cached.get("response"):
            print("✅ Integração cache funcionando")
            return True
        
        return False
        
    except Exception as e:
        print(f"❌ Erro no teste de integração: {e}")
        traceback.print_exc()
        return False

async def main():
    """Função principal de validação."""
    print("🚀 Iniciando validação do sistema PROAtivo...")
    print("=" * 60)
    
    # 1. Validar imports
    import_results = await validate_imports()
    
    total_services = len(import_results)
    working_services = sum(import_results.values())
    
    print(f"\n📊 Serviços disponíveis: {working_services}/{total_services}")
    
    if working_services == 0:
        print("❌ Nenhum serviço disponível - verificar instalação")
        return 1
    
    # 2. Testar serviços individuais
    test_results = []
    
    if import_results.get("cache_service"):
        cache_ok = await test_cache_service()
        test_results.append(cache_ok)
    
    if import_results.get("fallback_service"):
        fallback_ok = await test_fallback_service()
        test_results.append(fallback_ok)
    
    if import_results.get("query_processor"):
        processor_ok = await test_query_processor()
        test_results.append(processor_ok)
    
    # 3. Teste de integração
    if len(test_results) > 1 and all(test_results):
        integration_ok = await test_integration()
        test_results.append(integration_ok)
    
    # 4. Resultado final
    successful_tests = sum(test_results)
    total_tests = len(test_results)
    
    print("\n" + "=" * 60)
    print("📋 RESUMO DA VALIDAÇÃO")
    print("=" * 60)
    print(f"Serviços importados: {working_services}/{total_services}")
    print(f"Testes executados: {total_tests}")
    print(f"Testes bem-sucedidos: {successful_tests}")
    print(f"Taxa de sucesso: {successful_tests/total_tests*100:.1f}%" if total_tests > 0 else "0%")
    
    if successful_tests == total_tests and working_services >= 3:
        print("\n🎉 Sistema validado com sucesso!")
        print("✅ Todos os componentes estão funcionando")
        return 0
    elif successful_tests >= total_tests * 0.7:
        print("\n⚠️ Sistema parcialmente funcional")
        print("🔧 Alguns componentes precisam de atenção")
        return 0
    else:
        print("\n❌ Sistema com problemas significativos")
        print("🔧 Revisar configuração e dependências")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 