#!/usr/bin/env python3
"""
Script simplificado para validar o dataset de queries de teste do PROAtivo.
Valida a estrutura JSON e fornece estatísticas do dataset.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

class DatasetValidator:
    """Validador do dataset de queries"""
    
    def __init__(self):
        self.dataset_path = Path(__file__).parent.parent / "data" / "test_dataset" / "query_test_dataset.json"
        
    def load_dataset(self) -> Dict[str, Any]:
        """Carrega e valida o dataset de queries"""
        try:
            with open(self.dataset_path, 'r', encoding='utf-8') as f:
                dataset = json.load(f)
            return dataset
        except FileNotFoundError:
            raise FileNotFoundError(f"Dataset não encontrado: {self.dataset_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Erro ao decodificar JSON: {e}")
    
    def validate_structure(self, dataset: Dict[str, Any]) -> Dict[str, Any]:
        """Valida a estrutura do dataset"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Verificar metadados
        if 'metadata' not in dataset:
            validation_result['errors'].append("Campo 'metadata' ausente")
        else:
            metadata = dataset['metadata']
            required_meta_fields = ['name', 'version', 'total_queries', 'categories']
            for field in required_meta_fields:
                if field not in metadata:
                    validation_result['errors'].append(f"Campo 'metadata.{field}' ausente")
        
        # Verificar queries
        if 'queries' not in dataset:
            validation_result['errors'].append("Campo 'queries' ausente")
        else:
            queries = dataset['queries']
            if not isinstance(queries, list):
                validation_result['errors'].append("Campo 'queries' deve ser uma lista")
            else:
                # Validar cada query
                required_query_fields = ['id', 'query', 'category', 'complexity', 'expected_route']
                for i, query in enumerate(queries):
                    for field in required_query_fields:
                        if field not in query:
                            validation_result['errors'].append(f"Query {i}: Campo '{field}' ausente")
                    
                    # Verificar IDs únicos
                    query_ids = [q.get('id') for q in queries]
                    if len(query_ids) != len(set(query_ids)):
                        validation_result['errors'].append("IDs de queries não são únicos")
        
        # Verificar estatísticas
        if 'statistics' not in dataset:
            validation_result['warnings'].append("Campo 'statistics' ausente")
        
        validation_result['valid'] = len(validation_result['errors']) == 0
        return validation_result
    
    def analyze_dataset(self, dataset: Dict[str, Any]) -> Dict[str, Any]:
        """Analisa o conteúdo do dataset"""
        queries = dataset.get('queries', [])
        
        analysis = {
            'total_queries': len(queries),
            'categories': {},
            'complexity_levels': {},
            'expected_routes': {},
            'priorities': {},
            'domain_coverage': {}
        }
        
        # Análise detalhada
        for query in queries:
            # Por categoria
            cat = query.get('category', 'unknown')
            analysis['categories'][cat] = analysis['categories'].get(cat, 0) + 1
            
            # Por complexidade
            comp = query.get('complexity', 'unknown')
            analysis['complexity_levels'][comp] = analysis['complexity_levels'].get(comp, 0) + 1
            
            # Por rota esperada
            route = query.get('expected_route', 'unknown')
            analysis['expected_routes'][route] = analysis['expected_routes'].get(route, 0) + 1
            
            # Por prioridade
            priority = query.get('test_priority', 'unknown')
            analysis['priorities'][priority] = analysis['priorities'].get(priority, 0) + 1
            
            # Cobertura de domínio (palavras-chave)
            keywords = query.get('domain_keywords', [])
            for keyword in keywords:
                analysis['domain_coverage'][keyword] = analysis['domain_coverage'].get(keyword, 0) + 1
        
        return analysis
    
    def generate_report(self, dataset: Dict[str, Any], validation: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """Gera relatório completo do dataset"""
        report = []
        report.append("=" * 80)
        report.append("📊 RELATÓRIO DE VALIDAÇÃO DO DATASET DE QUERIES")
        report.append("=" * 80)
        report.append(f"📅 Data de validação: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"📁 Arquivo: {self.dataset_path}")
        report.append("")
        
        # Status de validação
        if validation['valid']:
            report.append("✅ VALIDAÇÃO: APROVADO")
        else:
            report.append("❌ VALIDAÇÃO: REPROVADO")
        
        if validation['errors']:
            report.append(f"\n❌ Erros encontrados ({len(validation['errors'])}):")
            for error in validation['errors']:
                report.append(f"   • {error}")
        
        if validation['warnings']:
            report.append(f"\n⚠️  Avisos ({len(validation['warnings'])}):")
            for warning in validation['warnings']:
                report.append(f"   • {warning}")
        
        # Estatísticas do dataset
        report.append(f"\n📈 ESTATÍSTICAS DO DATASET")
        report.append(f"🔢 Total de queries: {analysis['total_queries']}")
        
        report.append(f"\n📊 Distribuição por Categoria:")
        for cat, count in sorted(analysis['categories'].items()):
            percentage = (count / analysis['total_queries']) * 100
            report.append(f"   {cat}: {count} queries ({percentage:.1f}%)")
        
        report.append(f"\n🎯 Distribuição por Complexidade:")
        for comp, count in sorted(analysis['complexity_levels'].items()):
            percentage = (count / analysis['total_queries']) * 100
            report.append(f"   {comp}: {count} queries ({percentage:.1f}%)")
        
        report.append(f"\n🔄 Distribuição por Rota Esperada:")
        for route, count in sorted(analysis['expected_routes'].items()):
            percentage = (count / analysis['total_queries']) * 100
            report.append(f"   {route}: {count} queries ({percentage:.1f}%)")
        
        report.append(f"\n🎯 Distribuição por Prioridade de Teste:")
        for priority, count in sorted(analysis['priorities'].items()):
            percentage = (count / analysis['total_queries']) * 100
            report.append(f"   {priority}: {count} queries ({percentage:.1f}%)")
        
        # Top 10 palavras-chave mais comuns
        if analysis['domain_coverage']:
            top_keywords = sorted(analysis['domain_coverage'].items(), key=lambda x: x[1], reverse=True)[:10]
            report.append(f"\n🔑 Top 10 Palavras-chave do Domínio:")
            for keyword, count in top_keywords:
                report.append(f"   {keyword}: {count} ocorrências")
        
        # Amostras por categoria
        queries = dataset.get('queries', [])
        report.append(f"\n📋 AMOSTRAS DE QUERIES POR CATEGORIA:")
        for category in sorted(analysis['categories'].keys()):
            category_queries = [q for q in queries if q.get('category') == category][:2]  # Primeiras 2
            report.append(f"\n   📂 {category.upper()}:")
            for query in category_queries:
                query_text = query.get('query', '')
                if len(query_text) > 60:
                    query_text = query_text[:60] + "..."
                report.append(f"     • {query.get('id')}: {query_text}")
                report.append(f"       Complexidade: {query.get('complexity')} | Rota: {query.get('expected_route')}")
        
        report.append("\n" + "=" * 80)
        return "\n".join(report)

def main():
    """Função principal"""
    validator = DatasetValidator()
    
    try:
        print("🔍 Carregando dataset...")
        dataset = validator.load_dataset()
        
        print("✅ Dataset carregado com sucesso!")
        print(f"📊 Total de queries: {len(dataset.get('queries', []))}")
        
        print("\n🔎 Validando estrutura...")
        validation = validator.validate_structure(dataset)
        
        print("📈 Analisando conteúdo...")
        analysis = validator.analyze_dataset(dataset)
        
        print("📋 Gerando relatório...")
        report = validator.generate_report(dataset, validation, analysis)
        
        print(report)
        
        # Salvar relatório em arquivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"dataset_validation_report_{timestamp}.txt"
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"💾 Relatório salvo em: {report_filename}")
        
        # Status de saída
        if not validation['valid']:
            print("\n❌ Validação falhou. Verifique os erros acima.")
            sys.exit(1)
        else:
            print("\n✅ Dataset validado com sucesso!")
            sys.exit(0)
            
    except Exception as e:
        print(f"❌ Erro durante validação: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 