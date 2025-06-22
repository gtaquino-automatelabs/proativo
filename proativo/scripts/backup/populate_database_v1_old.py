#!/usr/bin/env python3
"""
Script para popular o banco de dados com os dados de exemplo.
Executa o pipeline ETL para processar e carregar os arquivos da pasta data/samples.
"""

import asyncio
import os
import sys
import logging
from pathlib import Path

# Adicionar path do projeto (diretório pai para acessar src/)
current_dir = Path(__file__).parent
project_dir = current_dir.parent
src_dir = project_dir / "src"
sys.path.insert(0, str(project_dir))

# Configurar PYTHONPATH para imports relativos
os.environ['PYTHONPATH'] = str(src_dir)

try:
    from src.etl.data_processor import DataProcessor, DataType, FileFormat
    from src.database.repositories import RepositoryManager
except ImportError as e:
    print(f"ERRO de importação: {e}")
    print(f"Verificando estrutura de diretórios...")
    print(f"Current dir: {current_dir}")
    print(f"Src dir: {src_dir}")
    print(f"Src exists: {src_dir.exists()}")
    if src_dir.exists():
        print(f"Contents of src: {list(src_dir.iterdir())}")
    sys.exit(1)

async def populate_database():
    """Popula o banco de dados com dados de exemplo."""
    print("INICIANDO POPULAÇÃO DO BANCO DE DADOS...")
    print("=" * 60)
    
    try:
        print("Módulos importados com sucesso")
        
        # Configurar logging
        logging.basicConfig(level=logging.INFO)
        
        # Inicializar conexão com banco de dados
        print("Inicializando conexão com banco de dados...")
        from src.database.connection import db_connection, create_tables
        
        await db_connection.initialize()
        
        # Criar tabelas se não existirem
        print("Criando tabelas se necessário...")
        await create_tables()
        
        # Criar sessão do banco
        async with db_connection.get_session() as session:
            # Inicializar repositórios
            print("Inicializando repositórios...")
            repository_manager = RepositoryManager(session)
            
            # Inicializar processador ETL
            print("Inicializando processador ETL...")
            processor = DataProcessor(repository_manager)
            
            # Diretório com dados de exemplo
            samples_dir = Path("data/samples")
            
            if not samples_dir.exists():
                print(f"ERRO: Diretório de amostras não encontrado: {samples_dir}")
                return False
            
            print(f"Processando arquivos em: {samples_dir}")
            
            # Listar arquivos disponíveis
            files_to_process = []
            for extension in ['.csv', '.xml', '.xlsx']:
                files_to_process.extend(list(samples_dir.glob(f'*{extension}')))
            
            print(f"Encontrados {len(files_to_process)} arquivos:")
            for file_path in files_to_process:
                print(f"   - {file_path.name}")
            
            if not files_to_process:
                print("ERRO: Nenhum arquivo para processar encontrado")
                return False
            
            # Processar cada arquivo
            total_records = 0
            successful_files = 0
            
            for file_path in files_to_process:
                print(f"\nProcessando: {file_path.name}")
                
                try:
                    result = await processor.process_and_save(file_path)
                    
                    if result['success']:
                        successful_files += 1
                        total_records += result['saved_records']
                        print(f"   SUCESSO: {result['saved_records']} registros salvos")
                    else:
                        print(f"   ERRO: {result.get('error', 'Erro desconhecido')}")
                        
                except Exception as e:
                    print(f"   ERRO ao processar {file_path.name}: {e}")
            
            # Commit das transações
            await session.commit()
            
            # Resumo final
            print("\n" + "=" * 60)
            print("RESUMO DA POPULAÇÃO")
            print("=" * 60)
            print(f"Arquivos processados: {successful_files}/{len(files_to_process)}")
            print(f"Total de registros salvos: {total_records}")
            
            if successful_files > 0:
                print("BANCO DE DADOS POPULADO COM SUCESSO!")
                
                # Mostrar estatísticas do processador
                stats = processor.get_processing_statistics()
                print(f"Taxa de sucesso: {stats['success_rate_percent']}%")
                print(f"Registros válidos: {stats['valid_records']}")
                print(f"Registros inválidos: {stats['invalid_records']}")
                
                return True
            else:
                print("ERRO: Nenhum arquivo foi processado com sucesso")
                return False
            
    except ImportError as e:
        print(f"ERRO de importação: {e}")
        print("Verifique se o sistema está configurado corretamente")
        return False
    except Exception as e:
        print(f"ERRO inesperado: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal."""
    try:
        success = asyncio.run(populate_database())
        if success:
            print("\nScript executado com sucesso!")
            return 0
        else:
            print("\nScript executado com problemas")
            return 1
    except KeyboardInterrupt:
        print("\nScript interrompido pelo usuário")
        return 1
    except Exception as e:
        print(f"\nErro fatal: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 