#!/usr/bin/env python3
"""
Script para popular dados PMM_2 (Plano de Manutenção Maestro) do SAP.
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# Configurar paths
current_dir = Path(__file__).parent
project_dir = current_dir.parent.parent
sys.path.insert(0, str(project_dir))
os.environ['PYTHONPATH'] = str(project_dir)

from src.etl.data_processor import DataProcessor, DataType
from src.database.repositories import RepositoryManager
from src.database.connection import db_connection, init_database


async def populate_pmm_2():
    """Popula dados PMM_2 no banco."""
    print("📋 ETAPA PMM_2: Populando planos de manutenção...")
    
    async with db_connection.get_session() as session:
        repo_manager = RepositoryManager(session)
        processor = DataProcessor(repo_manager)
        
        # Procurar arquivos PMM_2 em diferentes locais
        pmm_2_files = [
            "data/samples/PMM_2.csv",            
            #"../../Planilhas SAP_Proativo/PMM_2.csv",
        ]
        
        total_processed = 0
        
        for file_path_str in pmm_2_files:
            file_path = Path(file_path_str)
            if not file_path.exists():
                print(f"   ⚠️  Arquivo não encontrado: {file_path}")
                continue
            
            print(f"   📁 Processando: {file_path.name}")
            
            try:
                result = await processor.process_and_save(file_path, DataType.PMM_2)
                
                if result['success']:
                    total_processed += result['saved_records']
                    print(f"   ✅ {result['saved_records']} planos PMM_2 salvos")
                else:
                    print(f"   ❌ Erro: {result.get('error', 'Desconhecido')}")
                    
            except Exception as e:
                print(f"   ❌ Erro ao processar {file_path.name}: {e}")
                continue
                
            # Se encontrou e processou um arquivo, para
            if total_processed > 0:
                break
        
        print(f"   📈 Total: {total_processed} planos PMM_2 processados")
        await session.commit()
        
        return total_processed


async def verify_pmm_2():
    """Verifica dados PMM_2 populados."""
    print("🔍 ETAPA PMM_2: Verificando população...")
    
    async with db_connection.get_session() as session:
        repo_manager = RepositoryManager(session)
        
        pmm_2_count = await repo_manager.pmm_2.count()
        
        print(f"   📊 Planos PMM_2: {pmm_2_count}")
        
        if pmm_2_count > 0:
            # Estatísticas detalhadas
            stats = await repo_manager.pmm_2.get_statistics()
            print(f"   📊 Por status: {stats['by_status']}")
            print(f"   📊 Por centro de trabalho (amostra): {list(stats['by_work_center'].items())[:5]}")  # Top 5
            print(f"   📊 Planos órfãos: {stats['orphaned_plans']}")
            print(f"   📊 Planos futuros: {stats['future_plans']}")
        
        return pmm_2_count > 0


async def main():
    """Função principal - popula dados PMM_2."""
    print("🚀 POPULAÇÃO DE DADOS PMM_2")
    print("============================")
    
    try:
        # Inicializar conexão com banco
        await init_database()
        
        # Verificar se tabela existe
        async with db_connection.get_session() as session:
            repo_manager = RepositoryManager(session)
            
            try:
                # Tenta acessar o repository PMM_2
                await repo_manager.pmm_2.count()
                print("✅ Tabela PMM_2 existe")
            except Exception as e:
                print(f"❌ Tabela PMM_2 não existe ou não acessível: {e}")
                return False
        
        # Verificar se já há dados
        async with db_connection.get_session() as session:
            repo_manager = RepositoryManager(session)
            existing_count = await repo_manager.pmm_2.count()
            
            if existing_count > 0:
                print(f"⚠️  Já existem {existing_count} planos PMM_2 no banco")
                print("   Pulando população")
                return True
        
        # Etapa 1: Popular dados PMM_2
        total_processed = await populate_pmm_2()
        
        if total_processed == 0:
            print("⚠️  Nenhum arquivo PMM_2 encontrado ou processado")
            return False
        
        # Etapa 2: Verificação
        success = await verify_pmm_2()
        
        if success:
            print("\n🎉 DADOS PMM_2 POPULADOS COM SUCESSO!")
            return True
        else:
            print("\n❌ POPULAÇÃO PMM_2 INCOMPLETA")
            return False
            
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 