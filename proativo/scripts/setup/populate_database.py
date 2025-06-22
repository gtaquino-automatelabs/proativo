#!/usr/bin/env python3
"""
Script melhorado para popular o banco de dados.
Processa equipamentos primeiro, depois manutenções com conversão de códigos.
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Any

# Configurar paths
current_dir = Path(__file__).parent
project_dir = current_dir.parent
src_dir = project_dir / "src"
sys.path.insert(0, str(project_dir))
os.environ['PYTHONPATH'] = str(src_dir)

try:
    from src.etl.data_processor import DataProcessor, DataType, FileFormat
    from src.database.repositories import RepositoryManager
except ImportError as e:
    print(f"ERRO de importação: {e}")
    sys.exit(1)

async def populate_database():
    """Popula o banco de dados em duas etapas: equipamentos depois manutenções."""
    print("INICIANDO POPULAÇÃO DO BANCO DE DADOS V2...")
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
            
            # ETAPA 1: Processar APENAS equipamentos
            print("\n" + "=" * 60)
            print("ETAPA 1: PROCESSANDO EQUIPAMENTOS")
            print("=" * 60)
            
            equipment_files = [
                "data/samples/equipment.csv",
                "data/samples/equipment.xml", 
                "data/samples/electrical_assets.xlsx"
            ]
            
            equipment_saved = 0
            equipment_map = {}  # código -> UUID
            
            for file_path_str in equipment_files:
                file_path = Path(file_path_str)
                if not file_path.exists():
                    print(f"Arquivo não encontrado: {file_path}")
                    continue
                
                print(f"\nProcessando equipamentos: {file_path.name}")
                
                try:
                    # Força tipo EQUIPMENT
                    result = await processor.process_and_save(file_path, DataType.EQUIPMENT)
                    
                    if result['success'] and result['saved_records'] > 0:
                        equipment_saved += result['saved_records']
                        print(f"   SUCESSO: {result['saved_records']} equipamentos salvos")
                        
                        # Buscar equipamentos criados para mapear código->UUID
                        equipments = await repository_manager.equipment.get_all()
                        for eq in equipments:
                            if eq.code not in equipment_map:
                                equipment_map[eq.code] = str(eq.id)
                    else:
                        print(f"   FALHA: {result.get('error', 'Erro desconhecido')}")
                        
                except Exception as e:
                    print(f"   ERRO ao processar {file_path.name}: {e}")
            
            print(f"\nTotal de equipamentos criados: {equipment_saved}")
            print(f"Mapeamento código->UUID: {len(equipment_map)} equipamentos")
            
            if equipment_saved == 0:
                print("ERRO: Nenhum equipamento foi criado. Não é possível processar manutenções.")
                return False
            
            # ETAPA 2: Processar manutenções com conversão de códigos
            print("\n" + "=" * 60)
            print("ETAPA 2: PROCESSANDO MANUTENÇÕES")
            print("=" * 60)
            
            maintenance_files = [
                "data/samples/maintenance_orders.csv",
                "data/samples/maintenance_schedules.csv",
                "data/samples/maintenance_orders.xml"
            ]
            
            maintenance_saved = 0
            
            for file_path_str in maintenance_files:
                file_path = Path(file_path_str)
                if not file_path.exists():
                    print(f"Arquivo não encontrado: {file_path}")
                    continue
                
                print(f"\nProcessando manutenções: {file_path.name}")
                
                try:
                    # Processar arquivo mas NÃO salvar ainda
                    valid_records, validation_errors = processor.process_file(file_path, DataType.MAINTENANCE)
                    
                    print(f"   Registros processados: {len(valid_records)} válidos, {len(validation_errors)} inválidos")
                    
                    # Converter códigos para UUIDs
                    converted_records = []
                    conversion_errors = 0
                    
                    for record in valid_records:
                        equipment_code = record.get('equipment_id')
                        
                        if equipment_code and equipment_code in equipment_map:
                            # Converte código para UUID
                            record['equipment_id'] = equipment_map[equipment_code]
                            converted_records.append(record)
                        else:
                            conversion_errors += 1
                            print(f"   AVISO: Equipamento '{equipment_code}' não encontrado")
                    
                    print(f"   Conversões: {len(converted_records)} sucesso, {conversion_errors} falhas")
                    
                    # Salvar registros convertidos
                    if converted_records:
                        saved_count = await processor.save_to_database(converted_records, DataType.MAINTENANCE)
                        maintenance_saved += saved_count
                        print(f"   SUCESSO: {saved_count} manutenções salvas")
                    
                except Exception as e:
                    print(f"   ERRO ao processar {file_path.name}: {e}")
            
            # Commit das transações
            await session.commit()
            
            # Resumo final
            print("\n" + "=" * 60)
            print("RESUMO DA POPULAÇÃO V2")
            print("=" * 60)
            print(f"Equipamentos criados: {equipment_saved}")
            print(f"Manutenções criadas: {maintenance_saved}")
            print(f"Total de registros: {equipment_saved + maintenance_saved}")
            
            if equipment_saved > 0 or maintenance_saved > 0:
                print("BANCO DE DADOS POPULADO COM SUCESSO!")
                return True
            else:
                print("ERRO: Nenhum registro foi criado")
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