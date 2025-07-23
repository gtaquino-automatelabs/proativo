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


async def _populate_pmm_2_logic():
    """
    Contém a lógica principal para processar o arquivo PMM_2.csv e salvar os dados.
    Esta função deve ser chamada apenas se for necessário popular a tabela PMM_2.
    """
    print("📋 ETAPA PMM_2: Populando planos de manutenção...")
    
    total_processed = 0
    
    # A SESSÃO DO BANCO DE DADOS E O COMMIT DEVEM ENVOLVER TODA A OPERAÇÃO DE INSERÇÃO
    async with db_connection.get_session() as session:
        repo_manager = RepositoryManager(session)
        processor = DataProcessor(repo_manager)
        
        # Caminhos possíveis para o arquivo PMM_2.csv
        pmm_2_files = [
            "data/samples/PMM_2.csv",            
            # Adicione outros caminhos de fallback aqui se necessário, por exemplo:
            # "../../Planilhas SAP_Proativo/PMM_2.csv",
        ]
        
        found_file = None
        for file_path_str in pmm_2_files:
            file_path = Path(file_path_str)
            if file_path.exists():
                found_file = file_path
                break
        
        if not found_file:
            print("   ⚠️  Nenhum arquivo PMM_2.csv encontrado nos caminhos esperados.")
            return 0 # Retorna 0 para indicar que nada foi processado
            
        print(f"   📁 Processando: {found_file.name}")
        
        try:
            # O processor.process_and_save usará a sessão que lhe foi passada via repo_manager.
            # Ele fará as inserções/atualizações no banco.
            result = await processor.process_and_save(found_file, DataType.PMM_2)
            
            if result['success']:
                total_processed += result['saved_records']
                print(f"   ✅ {result['saved_records']} planos PMM_2 salvos")
            else:
                print(f"   ❌ Erro durante o processamento de {found_file.name}: {result.get('error', 'Desconhecido')}")
                # Em caso de erro no processamento e salvamento de um arquivo, fazer rollback
                await session.rollback() 
                return 0 # Indica falha

        except Exception as e:
            print(f"   ❌ Erro crítico ao processar {found_file.name}: {e}")
            await session.rollback() # Garante rollback em caso de exceção
            raise # Re-lança a exceção para que o fluxo de setup_complete_database saiba que falhou
            
        # O COMMIT AQUI É ESSENCIAL E DEVE SER DENTRO DO BLOCO 'with session'
        # Garante que as mudanças sejam persistidas no banco e visíveis para outras sessões.
        await session.commit() 
        print(f"   📈 Total: {total_processed} planos PMM_2 processados e commitados.")
    
    return total_processed


async def verify_pmm_2():
    """Verifica dados PMM_2 populados e retorna estatísticas detalhadas."""
    print("🔍 ETAPA PMM_2: Verificando população...")
    
    async with db_connection.get_session() as session:
        repo_manager = RepositoryManager(session)
        
        pmm_2_count = await repo_manager.pmm_2.count()
        
        print(f"   📊 Planos PMM_2: {pmm_2_count}")
        
        if pmm_2_count > 0:
            # Estatísticas detalhadas
            stats = await repo_manager.pmm_2.get_statistics()
            print(f"   📊 Por status: {stats.get('by_status', {})}")
            print(f"   📊 Por centro de trabalho (amostra): {list(stats.get('by_work_center', {}).items())[:5]}")  # Top 5
            print(f"   📊 Planos órfãos: {stats.get('orphaned_plans', 'N/A')}")
            print(f"   📊 Planos futuros: {stats.get('future_plans', 'N/A')}")
        
        return pmm_2_count > 0


async def main():
    """Função principal para executar a população de dados PMM_2."""
    print("🚀 POPULAÇÃO DE DADOS PMM_2")
    print("============================")
    
    try:
        # Inicializar conexão com banco (é idempotente e pode ser chamada múltiplas vezes)
        await init_database()
        
        # Verificar se a tabela PMM_2 existe e está acessível
        async with db_connection.get_session() as session:
            repo_manager = RepositoryManager(session)
            try:
                # Tenta contar para verificar a existência e acessibilidade da tabela
                await repo_manager.pmm_2.count()
                print("✅ Tabela PMM_2 existe e está acessível.")
            except Exception as e:
                print(f"❌ Erro: Tabela PMM_2 não existe ou não está acessível: {e}")
                print("   Por favor, verifique se 'create_tables.py' foi executado com sucesso.")
                return False # Aborta se a tabela não estiver pronta
        
        # Verificar se já há dados na tabela para evitar repopulação desnecessária
        async with db_connection.get_session() as session:
            repo_manager = RepositoryManager(session)
            existing_count = await repo_manager.pmm_2.count()
            
            if existing_count > 0:
                print(f"⚠️  Já existem {existing_count} planos PMM_2 no banco. Pulando a etapa de população de arquivos.")
                print("\n🎉 VERIFICAÇÃO PMM_2 - CONCLUÍDA. DADOS EXISTENTES JÁ PRESENTES.") 
                return True # Retorna True porque o estado desejado (populado) já foi alcançado
        
        # Se não há dados, procede com a população
        print("   Tabela PMM_2 está vazia, iniciando população a partir do arquivo CSV.")
        total_processed = await _populate_pmm_2_logic() # Chama a função que contém a lógica de população e commit
        
        if total_processed == 0:
            print("⚠️  Nenhum plano PMM_2 foi processado ou salvo. Verifique o arquivo de entrada ou erros.")
            return False
        
        # Verifica a população após a execução
        success = await verify_pmm_2()
        
        if success:
            print("\n🎉 DADOS PMM_2 POPULADOS COM SUCESSO E VERIFICADOS!")
            return True
        else:
            print("\n❌ POPULAÇÃO PMM_2 INCOMPLETA ou FALHA NA VERIFICAÇÃO.")
            return False
            
    except Exception as e:
        print(f"\n❌ ERRO FATAL durante a população de PMM_2: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)