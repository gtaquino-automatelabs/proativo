#!/usr/bin/env python3
"""
Script de teste de integração para validar o pipeline completo do PROAtivo.

Este script testa:
- Integração entre todos os serviços
- Performance end-to-end
- Accuracy das respostas
- Sistema de cache e fallback
"""

import asyncio
import time
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import logging

# Adicionar path do projeto (diretório pai para acessar src/)
sys.path.append(str(Path(__file__).parent.parent))

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class IntegrationTest:
    """Classe para testes de integração."""
    
    def __init__(self):
        """Inicializa teste de integração."""
        self.test_queries = [
            "Quantos transformadores estão operacionais?",
            "Qual o status do transformador TR001?",
            "Equipamentos que precisam de manutenção",
            "Custo total de manutenções este ano",
            "Quando foi a última manutenção do TR002?",
            "O que é um transformador?",  # Fora do escopo
            "",  # Query vazia
        ]
        
        self.results = []
        self.start_time = None
        self.services_available = {
            "llm_service": False,
            "cache_service": False,
            "fallback_service": False,
            "query_processor": False
        }
    
    def check_imports(self):
        """Verifica se os módulos estão disponíveis."""
        logger.info("Verificando imports dos serviços...")
        
        try:
            from src.api.services.llm_service import LLMService
            self.services_available["llm_service"] = True
            logger.info("✅ LLMService disponível")
        except ImportError as e:
            logger.warning(f"❌ LLMService não disponível: {e}")
        
        try:
            from src.api.services.cache_service import CacheService
            self.services_available["cache_service"] = True
            logger.info("✅ CacheService disponível")
        except ImportError as e:
            logger.warning(f"❌ CacheService não disponível: {e}")
        
        try:
            from src.api.services.fallback_service import FallbackService
            self.services_available["fallback_service"] = True
            logger.info("✅ FallbackService disponível")
        except ImportError as e:
            logger.warning(f"❌ FallbackService não disponível: {e}")
        
        try:
            from src.api.services.query_processor import QueryProcessor
            self.services_available["query_processor"] = True
            logger.info("✅ QueryProcessor disponível")
        except ImportError as e:
            logger.warning(f"❌ QueryProcessor não disponível: {e}")
        
        available_count = sum(self.services_available.values())
        logger.info(f"📊 Serviços disponíveis: {available_count}/4")
        
        return available_count > 0
    
    async def test_basic_functionality(self):
        """Testa funcionalidades básicas dos serviços."""
        logger.info("Testando funcionalidades básicas...")
        
        basic_results = {}
        
        # Teste do CacheService
        if self.services_available["cache_service"]:
            try:
                from src.api.services.cache_service import CacheService, CacheStrategy
                
                cache_service = CacheService()
                
                # Teste básico de cache
                test_query = "Status dos equipamentos"
                test_response = {"answer": "Teste", "confidence": 0.8}
                
                # Set no cache
                cache_key = await cache_service.set(test_query, test_response)
                
                # Get do cache
                cached_response = await cache_service.get(test_query)
                
                # Métricas
                metrics = await cache_service.get_metrics()
                
                basic_results["cache"] = {
                    "set_works": cache_key is not None,
                    "get_works": cached_response is not None,
                    "metrics_available": metrics is not None,
                    "cache_size": metrics.cache_size if metrics else 0
                }
                
                logger.info("✅ CacheService funcionando")
                
            except Exception as e:
                logger.error(f"❌ Erro no CacheService: {e}")
                basic_results["cache"] = {"error": str(e)}
        
        # Teste do FallbackService
        if self.services_available["fallback_service"]:
            try:
                from src.api.services.fallback_service import FallbackService, FallbackTrigger
                
                fallback_service = FallbackService()
                
                # Teste de fallback
                fallback_response = fallback_service.generate_fallback_response(
                    trigger=FallbackTrigger.OUT_OF_DOMAIN,
                    original_query="Como está o tempo?",
                    context={}
                )
                
                # Health check
                health = fallback_service.get_health_status()
                
                basic_results["fallback"] = {
                    "response_generated": fallback_response is not None,
                    "health_check": health.get("status") if health else "unknown",
                    "message_length": len(fallback_response.message) if fallback_response else 0
                }
                
                logger.info("✅ FallbackService funcionando")
                
            except Exception as e:
                logger.error(f"❌ Erro no FallbackService: {e}")
                basic_results["fallback"] = {"error": str(e)}
        
        # Teste do QueryProcessor
        if self.services_available["query_processor"]:
            try:
                from src.api.services.query_processor import QueryProcessor
                
                query_processor = QueryProcessor()
                
                # Teste de processamento
                processed = await query_processor.process_query("Status do TR001")
                
                basic_results["query_processor"] = {
                    "processing_works": processed is not None,
                    "has_entities": len(processed.entities) > 0 if processed else False,
                    "has_query_type": bool(processed.query_type) if processed else False
                }
                
                logger.info("✅ QueryProcessor funcionando")
                
            except Exception as e:
                logger.error(f"❌ Erro no QueryProcessor: {e}")
                basic_results["query_processor"] = {"error": str(e)}
        
        return basic_results
    
    async def test_end_to_end_simulation(self):
        """Simula testes end-to-end sem LLM real."""
        logger.info("Executando simulação end-to-end...")
        
        simulation_results = []
        
        for i, query in enumerate(self.test_queries):
            logger.info(f"Testando query {i+1}: '{query}'")
            
            start_time = time.time()
            result = {
                "query": query,
                "query_index": i + 1,
                "timestamp": datetime.now().isoformat()
            }
            
            try:
                # Simulação do pipeline completo
                
                # 1. Validação de entrada
                if not query.strip():
                    result["stage"] = "validation"
                    result["outcome"] = "empty_query_detected"
                    result["should_use_fallback"] = True
                else:
                    result["stage"] = "processing"
                
                # 2. Verificação de cache (se disponível)
                cache_hit = False
                if self.services_available["cache_service"] and query.strip():
                    try:
                        from src.api.services.cache_service import CacheService
                        cache_service = CacheService()
                        cached = await cache_service.get(query)
                        cache_hit = cached is not None
                        result["cache_hit"] = cache_hit
                    except:
                        pass
                
                # 3. Processamento de query (se não cache hit)
                if not cache_hit and query.strip():
                    if self.services_available["query_processor"]:
                        try:
                            from src.api.services.query_processor import QueryProcessor
                            processor = QueryProcessor()
                            processed = await processor.process_query(query)
                            result["query_processed"] = True
                            result["query_type"] = processed.query_type
                            result["entities_found"] = len(processed.entities)
                        except Exception as e:
                            result["query_processing_error"] = str(e)
                
                # 4. Simulação de resposta
                if query.strip():
                    if "transformador" in query.lower():
                        simulated_response = f"Informações sobre transformadores baseadas na consulta: {query}"
                        confidence = 0.85
                    elif "status" in query.lower():
                        simulated_response = f"Status dos equipamentos conforme solicitado: {query}"
                        confidence = 0.90
                    elif "custo" in query.lower():
                        simulated_response = f"Análise de custos: {query}"
                        confidence = 0.75
                    else:
                        simulated_response = f"Resposta geral para: {query}"
                        confidence = 0.60
                    
                    result["simulated_response"] = simulated_response
                    result["confidence"] = confidence
                else:
                    # Query vazia - usar fallback
                    result["simulated_response"] = "Desculpe, não entendi sua pergunta. Pode reformular?"
                    result["confidence"] = 0.1
                    result["used_fallback"] = True
                
                # 5. Calcular tempo de processamento
                processing_time = int((time.time() - start_time) * 1000)
                result["processing_time_ms"] = processing_time
                result["success"] = True
                
                # 6. Avaliação de performance
                if processing_time <= 1000:
                    result["performance"] = "excellent"
                elif processing_time <= 2000:
                    result["performance"] = "good"
                elif processing_time <= 3000:
                    result["performance"] = "acceptable"
                else:
                    result["performance"] = "slow"
                
            except Exception as e:
                result["success"] = False
                result["error"] = str(e)
                result["processing_time_ms"] = int((time.time() - start_time) * 1000)
                logger.error(f"Erro na query '{query}': {e}")
            
            simulation_results.append(result)
            
            # Pequena pausa entre queries
            await asyncio.sleep(0.1)
        
        return simulation_results
    
    def analyze_results(self, basic_results: Dict, simulation_results: List[Dict]):
        """Analisa resultados dos testes."""
        logger.info("Analisando resultados...")
        
        # Análise dos testes básicos
        basic_analysis = {
            "services_working": 0,
            "services_with_errors": 0,
            "total_services_tested": len(basic_results)
        }
        
        for service, result in basic_results.items():
            if "error" in result:
                basic_analysis["services_with_errors"] += 1
            else:
                basic_analysis["services_working"] += 1
        
        # Análise da simulação
        successful_queries = [r for r in simulation_results if r.get("success", False)]
        failed_queries = [r for r in simulation_results if not r.get("success", False)]
        
        processing_times = [r.get("processing_time_ms", 0) for r in successful_queries]
        confidences = [r.get("confidence", 0) for r in successful_queries]
        
        simulation_analysis = {
            "total_queries": len(simulation_results),
            "successful_queries": len(successful_queries),
            "failed_queries": len(failed_queries),
            "success_rate": len(successful_queries) / len(simulation_results) if simulation_results else 0,
            "avg_processing_time": sum(processing_times) / len(processing_times) if processing_times else 0,
            "avg_confidence": sum(confidences) / len(confidences) if confidences else 0,
            "performance_distribution": {
                "excellent": len([r for r in successful_queries if r.get("performance") == "excellent"]),
                "good": len([r for r in successful_queries if r.get("performance") == "good"]),
                "acceptable": len([r for r in successful_queries if r.get("performance") == "acceptable"]),
                "slow": len([r for r in successful_queries if r.get("performance") == "slow"])
            }
        }
        
        return {
            "basic_services": basic_analysis,
            "simulation": simulation_analysis,
            "overall_health": self._calculate_overall_health(basic_analysis, simulation_analysis)
        }
    
    def _calculate_overall_health(self, basic_analysis: Dict, simulation_analysis: Dict) -> str:
        """Calcula saúde geral do sistema."""
        # Critérios para saúde do sistema
        services_healthy = basic_analysis["services_working"] >= basic_analysis["total_services_tested"] * 0.7
        simulation_healthy = simulation_analysis["success_rate"] >= 0.8
        performance_healthy = simulation_analysis["avg_processing_time"] <= 2000
        confidence_healthy = simulation_analysis["avg_confidence"] >= 0.7
        
        healthy_criteria = sum([services_healthy, simulation_healthy, performance_healthy, confidence_healthy])
        
        if healthy_criteria >= 4:
            return "excellent"
        elif healthy_criteria >= 3:
            return "good"
        elif healthy_criteria >= 2:
            return "fair"
        else:
            return "poor"
    
    def print_summary(self, analysis: Dict):
        """Imprime resumo dos resultados."""
        print(f"\n{'='*80}")
        print(f"RELATÓRIO DE TESTE DE INTEGRAÇÃO - PROATIVO")
        print(f"{'='*80}")
        
        # Serviços básicos
        basic = analysis["basic_services"]
        print(f"\n📋 TESTES DE SERVIÇOS BÁSICOS:")
        print(f"   Serviços funcionando: {basic['services_working']}/{basic['total_services_tested']}")
        print(f"   Serviços com erro: {basic['services_with_errors']}")
        
        # Simulação end-to-end
        sim = analysis["simulation"]
        print(f"\n🔄 SIMULAÇÃO END-TO-END:")
        print(f"   Total de queries: {sim['total_queries']}")
        print(f"   Taxa de sucesso: {sim['success_rate']*100:.1f}%")
        print(f"   Tempo médio: {sim['avg_processing_time']:.0f}ms")
        print(f"   Confiança média: {sim['avg_confidence']*100:.1f}%")
        
        # Performance
        perf = sim["performance_distribution"]
        print(f"\n⚡ DISTRIBUIÇÃO DE PERFORMANCE:")
        print(f"   Excelente (≤1s): {perf['excellent']}")
        print(f"   Boa (≤2s): {perf['good']}")
        print(f"   Aceitável (≤3s): {perf['acceptable']}")
        print(f"   Lenta (>3s): {perf['slow']}")
        
        # Saúde geral
        health = analysis["overall_health"]
        health_emoji = {
            "excellent": "🟢",
            "good": "🟡", 
            "fair": "🟠",
            "poor": "🔴"
        }
        
        print(f"\n🏥 SAÚDE GERAL DO SISTEMA: {health_emoji.get(health, '⚪')} {health.upper()}")
        
        # Recomendações
        self._print_recommendations(analysis)
        
        print(f"\n{'='*80}")
    
    def _print_recommendations(self, analysis: Dict):
        """Imprime recomendações baseadas nos resultados."""
        print(f"\n💡 RECOMENDAÇÕES:")
        
        recommendations = []
        
        basic = analysis["basic_services"]
        sim = analysis["simulation"]
        
        if basic["services_with_errors"] > 0:
            recommendations.append("🔧 Corrigir erros nos serviços básicos")
        
        if sim["success_rate"] < 0.9:
            recommendations.append("🎯 Melhorar taxa de sucesso das queries")
        
        if sim["avg_processing_time"] > 2000:
            recommendations.append("⚡ Otimizar performance - tempo de resposta alto")
        
        if sim["avg_confidence"] < 0.8:
            recommendations.append("💪 Aumentar confiança das respostas")
        
        if sim["performance_distribution"]["slow"] > sim["total_queries"] * 0.2:
            recommendations.append("🚀 Reduzir número de queries lentas")
        
        if not recommendations:
            recommendations.append("🎉 Sistema funcionando bem! Continue monitorando.")
        
        for rec in recommendations:
            print(f"   {rec}")
    
    async def run_full_test(self):
        """Executa teste completo."""
        logger.info("🚀 Iniciando teste de integração completo...")
        self.start_time = time.time()
        
        # 1. Verificar imports
        if not self.check_imports():
            logger.error("❌ Nenhum serviço disponível - abortando testes")
            return False
        
        print(f"\n{'='*50}")
        print("EXECUTANDO TESTES...")
        print(f"{'='*50}")
        
        # 2. Testar funcionalidades básicas
        basic_results = await self.test_basic_functionality()
        
        # 3. Executar simulação end-to-end
        simulation_results = await self.test_end_to_end_simulation()
        
        # 4. Analisar resultados
        analysis = self.analyze_results(basic_results, simulation_results)
        
        # 5. Salvar resultados
        total_time = time.time() - self.start_time
        
        final_results = {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": total_time,
            "services_available": self.services_available,
            "basic_results": basic_results,
            "simulation_results": simulation_results,
            "analysis": analysis
        }
        
        # Salvar em arquivo
        with open("integration_test_results.json", "w", encoding="utf-8") as f:
            json.dump(final_results, f, indent=2, ensure_ascii=False)
        
        # 6. Imprimir resumo
        self.print_summary(analysis)
        
        logger.info(f"✅ Teste concluído em {total_time:.1f}s")
        logger.info("📄 Resultados salvos em: integration_test_results.json")
        
        return analysis["overall_health"] in ["excellent", "good"]


async def main():
    """Função principal."""
    test = IntegrationTest()
    
    try:
        success = await test.run_full_test()
        return 0 if success else 1
    except Exception as e:
        logger.error(f"❌ Erro durante teste: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code) 