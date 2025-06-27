#!/usr/bin/env python3
"""
Script para validar o dataset de queries de teste do PROAtivo.
Executa teste de todas as queries para verificar o comportamento do sistema.
"""

import json
import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Any
import logging
from datetime import datetime
import aiohttp

# Adicionar o diretório src ao path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from api.services.availability_router import AvailabilityRouter
from api.config import config

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('query_dataset_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class QueryDatasetTester:
    """Testa o dataset de queries contra o sistema PROAtivo"""
    
    def __init__(self):
        self.dataset_path = Path(__file__).parent.parent / "data" / "test_dataset" / "query_test_dataset.json"
        self.availability_router = AvailabilityRouter()
        self.results = []
        
    async def load_dataset(self) -> Dict[str, Any]:
        """Carrega o dataset de queries"""
        try:
            with open(self.dataset_path, 'r', encoding='utf-8') as f:
                dataset = json.load(f)
            logger.info(f"Dataset carregado: {dataset['metadata']['total_queries']} queries")
            return dataset
        except FileNotFoundError:
            logger.error(f"Dataset não encontrado: {self.dataset_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON: {e}")
            raise
    
    async def test_single_query(self, query_data: Dict[str, Any]) -> Dict[str, Any]:
        """Testa uma única query"""
        query_id = query_data['id']
        query_text = query_data['query']
        expected_route = query_data['expected_route']
        
        logger.info(f"Testando {query_id}: {query_text[:50]}...")
        
        result = {
            'query_id': query_id,
            'query_text': query_text,
            'expected_route': expected_route,
            'category': query_data['category'],
            'complexity': query_data['complexity'],
            'test_priority': query_data['test_priority'],
            'test_timestamp': datetime.now().isoformat(),
            'success': False,
            'actual_route': None,
            'response_time_ms': None,
            'error': None,
            'confidence': None,
            'sql_generated': None
        }
        
        try:
            start_time = datetime.now()
            
            # Testar através do AvailabilityRouter
            route_result = await self.availability_router.route_query(query_text)
            
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            result.update({
                'success': True,
                'actual_route': route_result.get('route_type', 'unknown'),
                'response_time_ms': round(response_time, 2),
                'confidence': route_result.get('confidence', None),
                'sql_generated': route_result.get('sql_query', None)
            })
            
            # Verificar se o roteamento foi correto
            route_match = result['actual_route'] == expected_route
            result['route_match'] = route_match
            
            if route_match:
                logger.info(f"✅ {query_id}: Roteamento correto ({expected_route})")
            else:
                logger.warning(f"⚠️  {query_id}: Roteamento diferente - Esperado: {expected_route}, Obtido: {result['actual_route']}")
                
        except Exception as e:
            logger.error(f"❌ {query_id}: Erro - {str(e)}")
            result['error'] = str(e)
            
        return result
    
    async def run_tests(self, max_queries: int = None, high_priority_only: bool = False) -> Dict[str, Any]:
        """Executa todos os testes do dataset"""
        logger.info("🚀 Iniciando testes do dataset de queries")
        
        dataset = await self.load_dataset()
        queries = dataset['queries']
        
        # Filtrar por prioridade se solicitado
        if high_priority_only:
            queries = [q for q in queries if q['test_priority'] == 'high']
            logger.info(f"Testando apenas queries de alta prioridade: {len(queries)}")
        
        if max_queries:
            queries = queries[:max_queries]
            logger.info(f"Limitando testes a {max_queries} queries")
        
        # Executar testes
        for query_data in queries:
            result = await self.test_single_query(query_data)
            self.results.append(result)
            
            # Pequena pausa para não sobrecarregar
            await asyncio.sleep(0.1)
        
        return self.generate_report()
    
    def generate_report(self) -> Dict[str, Any]:
        """Gera relatório dos testes"""
        if not self.results:
            return {"error": "Nenhum resultado para gerar relatório"}
        
        total_tests = len(self.results)
        successful_tests = len([r for r in self.results if r['success']])
        route_matches = len([r for r in self.results if r.get('route_match', False)])
        
        # Estatísticas por categoria
        by_category = {}
        by_complexity = {}
        by_route = {}
        
        for result in self.results:
            # Por categoria
            cat = result['category']
            if cat not in by_category:
                by_category[cat] = {'total': 0, 'success': 0, 'route_match': 0}
            by_category[cat]['total'] += 1
            if result['success']:
                by_category[cat]['success'] += 1
            if result.get('route_match', False):
                by_category[cat]['route_match'] += 1
                
            # Por complexidade
            comp = result['complexity']
            if comp not in by_complexity:
                by_complexity[comp] = {'total': 0, 'success': 0, 'route_match': 0}
            by_complexity[comp]['total'] += 1
            if result['success']:
                by_complexity[comp]['success'] += 1
            if result.get('route_match', False):
                by_complexity[comp]['route_match'] += 1
                
            # Por rota
            route = result['actual_route'] or 'error'
            if route not in by_route:
                by_route[route] = {'count': 0, 'response_times': []}
            by_route[route]['count'] += 1
            if result['response_time_ms']:
                by_route[route]['response_times'].append(result['response_time_ms'])
        
        # Calcular tempos médios de resposta por rota
        for route in by_route:
            times = by_route[route]['response_times']
            by_route[route]['avg_response_time'] = round(sum(times) / len(times), 2) if times else 0
            del by_route[route]['response_times']  # Remover lista para economizar espaço
        
        # Queries problemáticas
        failed_queries = [r for r in self.results if not r['success']]
        route_mismatches = [r for r in self.results if r['success'] and not r.get('route_match', False)]
        
        report = {
            'test_summary': {
                'total_queries_tested': total_tests,
                'successful_queries': successful_tests,
                'success_rate': round((successful_tests / total_tests) * 100, 2) if total_tests > 0 else 0,
                'route_matches': route_matches,
                'route_accuracy': round((route_matches / total_tests) * 100, 2) if total_tests > 0 else 0,
                'test_date': datetime.now().isoformat()
            },
            'performance_stats': {
                'avg_response_time_ms': round(
                    sum(r['response_time_ms'] for r in self.results if r['response_time_ms']) / 
                    len([r for r in self.results if r['response_time_ms']]), 2
                ) if [r for r in self.results if r['response_time_ms']] else 0,
                'by_route': by_route
            },
            'category_breakdown': by_category,
            'complexity_breakdown': by_complexity,
            'failed_queries': [
                {
                    'id': r['query_id'],
                    'query': r['query_text'][:100] + '...' if len(r['query_text']) > 100 else r['query_text'],
                    'error': r['error']
                }
                for r in failed_queries
            ],
            'route_mismatches': [
                {
                    'id': r['query_id'],
                    'query': r['query_text'][:50] + '...' if len(r['query_text']) > 50 else r['query_text'],
                    'expected': r['expected_route'],
                    'actual': r['actual_route']
                }
                for r in route_mismatches
            ]
        }
        
        return report
    
    def save_results(self, filename: str = None):
        """Salva os resultados detalhados em arquivo"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"query_dataset_results_{timestamp}.json"
        
        results_data = {
            'metadata': {
                'test_date': datetime.now().isoformat(),
                'total_tests': len(self.results)
            },
            'results': self.results,
            'report': self.generate_report()
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Resultados salvos em: {filename}")
        return filename

async def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Testa dataset de queries do PROAtivo')
    parser.add_argument('--max-queries', type=int, help='Máximo de queries para testar')
    parser.add_argument('--save-results', action='store_true', help='Salvar resultados em arquivo')
    parser.add_argument('--high-priority-only', action='store_true', help='Testar apenas queries de alta prioridade')
    
    args = parser.parse_args()
    
    tester = QueryDatasetTester()
    
    try:
        # Executar testes
        report = await tester.run_tests(
            max_queries=args.max_queries,
            high_priority_only=args.high_priority_only
        )
        
        # Exibir relatório
        print("\n" + "="*80)
        print("📊 RELATÓRIO DE TESTES DO DATASET DE QUERIES")
        print("="*80)
        
        summary = report['test_summary']
        print(f"🔢 Total de queries testadas: {summary['total_queries_tested']}")
        print(f"✅ Queries bem-sucedidas: {summary['successful_queries']} ({summary['success_rate']:.1f}%)")
        print(f"🎯 Roteamento correto: {summary['route_matches']} ({summary['route_accuracy']:.1f}%)")
        
        print(f"\n⚡ Performance:")
        perf = report['performance_stats']
        print(f"   Tempo médio de resposta: {perf['avg_response_time_ms']:.2f}ms")
        
        print(f"\n📈 Por Categoria:")
        for cat, stats in report['category_breakdown'].items():
            success_rate = (stats['success'] / stats['total']) * 100 if stats['total'] > 0 else 0
            route_rate = (stats['route_match'] / stats['total']) * 100 if stats['total'] > 0 else 0
            print(f"   {cat}: {stats['total']} queries, {success_rate:.1f}% sucesso, {route_rate:.1f}% roteamento correto")
        
        print(f"\n🔄 Por Rota:")
        for route, stats in perf['by_route'].items():
            print(f"   {route}: {stats['count']} queries, {stats['avg_response_time']:.2f}ms médio")
        
        if report['failed_queries']:
            print(f"\n❌ Queries com falha ({len(report['failed_queries'])}):")
            for fail in report['failed_queries'][:5]:  # Mostrar apenas as primeiras 5
                print(f"   {fail['id']}: {fail['query']} - {fail['error']}")
        
        if report['route_mismatches']:
            print(f"\n⚠️  Roteamento incorreto ({len(report['route_mismatches'])}):")
            for mismatch in report['route_mismatches'][:5]:  # Mostrar apenas as primeiras 5
                print(f"   {mismatch['id']}: {mismatch['query']}")
                print(f"      Esperado: {mismatch['expected']}, Obtido: {mismatch['actual']}")
        
        # Salvar resultados se solicitado
        if args.save_results:
            filename = tester.save_results()
            print(f"\n💾 Resultados detalhados salvos: {filename}")
        
        print("\n" + "="*80)
        
    except Exception as e:
        logger.error(f"Erro durante execução dos testes: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
