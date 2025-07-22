#!/usr/bin/env python3
"""
Script para importar localidades SAP do arquivo CSV.
Processa o arquivo Localidades_SAP.csv e insere no banco de dados.
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Configurar paths
current_dir = Path(__file__).parent
project_dir = current_dir.parent.parent
sys.path.insert(0, str(project_dir))
os.environ['PYTHONPATH'] = str(project_dir)

from src.etl.processors.localidades_processor import LocalidadesProcessor
from src.database.repositories import RepositoryManager
from src.database.connection import db_connection, create_tables, init_database
from src.utils.logger import get_logger

# Configurar logging
logger = get_logger(__name__)


async def import_localidades_sap(csv_file_path: Path, batch_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Importa localidades SAP do arquivo CSV.
    
    Args:
        csv_file_path: Caminho para o arquivo CSV
        batch_id: ID do lote de importação (opcional)
        
    Returns:
        Dicionário com estatísticas da importação
    """
    if not csv_file_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {csv_file_path}")
    
    print(f"🏗️  Importando localidades SAP de: {csv_file_path.name}")
    
    # Processar arquivo CSV
    processor = LocalidadesProcessor()
    
    try:
        processed_result = processor.process_file(csv_file_path, batch_id)
        
        if processed_result['valid_records'] == 0:
            print("   ⚠️  Nenhum registro válido encontrado")
            return processed_result
        
        print(f"   📊 Registros processados: {processed_result['total_records']}")
        print(f"   ✅ Registros válidos: {processed_result['valid_records']}")
        print(f"   ❌ Registros inválidos: {processed_result['invalid_records']}")
        
        # Preparar dados para inserção
        location_records = processor.create_location_records(processed_result['data'])
        
        # Inserir no banco de dados
        async with db_connection.get_session() as session:
            repo_manager = RepositoryManager(session)
            
            # Verificar localidades já existentes
            existing_codes = set()
            for record in location_records:
                existing_location = await repo_manager.sap_location.get_by_code(record['location_code'])
                if existing_location:
                    existing_codes.add(record['location_code'])
            
            # Filtrar registros novos
            new_records = [r for r in location_records if r['location_code'] not in existing_codes]
            
            if existing_codes:
                print(f"   🔄 Localidades já existentes (puladas): {len(existing_codes)}")
            
            if new_records:
                print(f"   📝 Inserindo {len(new_records)} novas localidades...")
                
                # Inserir em lote
                created_locations = await repo_manager.sap_location.bulk_create(new_records)
                await repo_manager.commit()
                
                print(f"   ✅ {len(created_locations)} localidades inseridas com sucesso")
            else:
                print("   ℹ️  Nenhuma localidade nova para inserir")
        
        # Estatísticas finais
        final_stats = {
            'file_processed': str(csv_file_path),
            'total_records': processed_result['total_records'],
            'valid_records': processed_result['valid_records'],
            'invalid_records': processed_result['invalid_records'],
            'existing_records': len(existing_codes),
            'new_records': len(new_records),
            'processing_time': datetime.now().isoformat(),
            'batch_id': processed_result['import_batch_id']
        }
        
        return final_stats
        
    except Exception as e:
        logger.error(f"Erro na importação de localidades: {str(e)}")
        raise


async def validate_and_report_data():
    """Valida e gera relatório dos dados importados."""
    print("\n📋 Validando dados importados...")
    
    async with db_connection.get_session() as session:
        repo_manager = RepositoryManager(session)
        
        # Estatísticas gerais
        stats = await repo_manager.sap_location.get_stats()
        
        print(f"   📊 Total de localidades: {stats['total_locations']}")
        print(f"   📈 Status: {stats['by_status']}")
        print(f"   🗺️  Por região: {stats['by_region']}")
        print(f"   🔗 Taxa de vinculação: {stats['linking_rate']:.1f}%")
        
        # Listar algumas localidades como exemplo
        locations = await repo_manager.sap_location.list_active()
        if locations:
            print(f"\n   🏛️  Exemplos de localidades importadas:")
            for loc in locations[:5]:  # Mostrar 5 primeiras
                abbrev = f" ({loc.abbreviation})" if loc.abbreviation else ""
                print(f"      • {loc.location_code} - {loc.denomination}{abbrev}")
        
        return stats


async def main():
    """Função principal do script."""
    print("🚀 Iniciando importação de localidades SAP...\n")
    
    try:
        # Inicializar banco de dados
        await init_database()
        
        # Definir caminho do arquivo CSV
        csv_files = [
            "data/samples/Localidades_SAP.csv",
            #"Localidades_SAP.csv"  # Fallback
        ]
        
        csv_file_path = None
        for file_path in csv_files:
            path = Path(file_path)
            if path.exists():
                csv_file_path = path
                break
        
        if not csv_file_path:
            print("❌ Arquivo CSV de localidades não encontrado")
            print("   Procurado em:")
            for file_path in csv_files:
                print(f"   • {file_path}")
            return
        
        # Importar localidades
        batch_id = f"localidades_sap_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        import_stats = await import_localidades_sap(csv_file_path, batch_id)
        
        # Validar e gerar relatório
        validation_stats = await validate_and_report_data()
        
        # Relatório final
        print(f"\n🎉 Importação concluída com sucesso!")
        print(f"   📁 Arquivo: {csv_file_path.name}")
        print(f"   📊 Registros processados: {import_stats['total_records']}")
        print(f"   ✅ Registros válidos: {import_stats['valid_records']}")
        print(f"   🆕 Novos registros: {import_stats['new_records']}")
        print(f"   🔄 Registros existentes: {import_stats['existing_records']}")
        print(f"   🆔 Batch ID: {import_stats['batch_id']}")
        
        if import_stats['invalid_records'] > 0:
            print(f"   ⚠️  Registros com problemas: {import_stats['invalid_records']}")
        
    except Exception as e:
        logger.error(f"Erro na execução do script: {str(e)}")
        print(f"❌ Erro: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 