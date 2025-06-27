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

# Configurar paths - usar mesma lógica dos testes que funciona
current_script_dir = os.path.dirname(__file__)
project_root = os.path.join(current_script_dir, "..", "..")  # scripts/setup -> proativo/
src_path = os.path.join(project_root, "src")

print("=" * 50)
print("🐍 INICIANDO CONFIGURAÇÃO DE PATHS")
print(f"🛠️  Script dir: {current_script_dir}")
print(f"📁 Project root: {project_root}")
print(f"📦 Src path: {src_path}")

# Verificar se os paths existem
import os
print(f"✅ Project root exists: {os.path.exists(project_root)}")
print(f"✅ Src path exists: {os.path.exists(src_path)}")

# Adicionar src ao path para imports (mesma lógica do conftest.py)
sys.path.insert(0, src_path)
sys.path.insert(0, project_root)

print(f"🛤️  Python path configurado!")
print(f"🔍 sys.path primeiros 5 itens:")
for i, path in enumerate(sys.path[:5]):
    print(f"   {i}: {path}")
print("=" * 50)

try:
    print("🔄 Tentando importar módulos...")
    from src.etl.data_processor import DataProcessor, DataType, FileFormat
    from src.database.repositories import RepositoryManager
    print("✅ Importações realizadas com sucesso!")
except ImportError as e:
    print(f"❌ ERRO de importação: {e}")
    print("📋 Conteúdo do diretório src:")
    if os.path.exists(src_path):
        for item in os.listdir(src_path):
            print(f"   - {item}")
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
            
            # ==========================================
            # TRANSAÇÃO 1: EQUIPAMENTOS (SEPARADA)
            # ==========================================
            print("\n" + "=" * 60)
            print("ETAPA 1: PROCESSANDO EQUIPAMENTOS (APENAS CSV)")
            print("=" * 60)
            
            # PROCESSAR APENAS equipment.csv para evitar duplicações
            equipment_files = [
                Path(project_root) / "data/samples/equipment.csv"
                # Removidos: equipment.xml e electrical_assets.xlsx (duplicados)
            ]
            
            equipment_saved = 0
            
            for file_path in equipment_files:
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
                    else:
                        print(f"   FALHA: {result.get('error', 'Erro desconhecido')}")
                        
                except Exception as e:
                    print(f"   ERRO ao processar {file_path.name}: {e}")
            
            # COMMIT EQUIPAMENTOS (transação separada)
            await session.commit()
            print(f"\n✅ TRANSAÇÃO DE EQUIPAMENTOS CONFIRMADA: {equipment_saved} equipamentos")
            
            # Buscar TODOS os equipamentos para mapeamento código->UUID
            equipments = await repository_manager.equipment.get_all()
            equipment_map = {}
            for eq in equipments:
                equipment_map[eq.code] = str(eq.id)
            
            print(f"Mapeamento código->UUID: {len(equipment_map)} equipamentos")
            
            if equipment_saved == 0:
                print("ERRO: Nenhum equipamento foi criado. Não é possível processar manutenções.")
                return False
        
        # ==========================================
        # TRANSAÇÃO 2: MANUTENÇÕES (NOVA SESSÃO)
        # ==========================================
        async with db_connection.get_session() as maintenance_session:
            print("\n" + "=" * 60)
            print("ETAPA 2: PROCESSANDO MANUTENÇÕES (NOVA TRANSAÇÃO)")
            print("=" * 60)
            
            # Repositórios para nova sessão
            maintenance_repository_manager = RepositoryManager(maintenance_session)
            maintenance_processor = DataProcessor(maintenance_repository_manager)
            
            maintenance_files = [
                Path(project_root) / "data/samples/maintenance_orders.csv",
                Path(project_root) / "data/samples/maintenance_schedules.csv",
                Path(project_root) / "data/samples/maintenance_orders.xml"
            ]
            
            maintenance_saved = 0
            
            for file_path in maintenance_files:
                if not file_path.exists():
                    print(f"Arquivo não encontrado: {file_path}")
                    continue
                
                print(f"\nProcessando manutenções: {file_path.name}")
                
                try:
                    # Processar arquivo mas NÃO salvar ainda
                    valid_records, validation_errors = maintenance_processor.process_file(file_path, DataType.MAINTENANCE)
                    
                    print(f"   Registros processados: {len(valid_records)} válidos, {len(validation_errors)} inválidos")
                    
                    # Converter códigos para UUIDs
                    converted_records = []
                    conversion_errors = 0
                    
                    for i, record in enumerate(valid_records):
                        equipment_code = record.get('equipment_id')
                        
                        # 🔍 DEBUG DETALHADO
                        if i < 3:  # Só os primeiros 3 registros para não poluir
                            print(f"   🔍 DEBUG REGISTRO {i}: equipment_id = '{equipment_code}', todas chaves: {list(record.keys())}")
                        
                        if equipment_code and equipment_code in equipment_map:
                            # Converte código para UUID
                            record['equipment_id'] = equipment_map[equipment_code]
                            converted_records.append(record)
                            print(f"   ✅ Equipamento '{equipment_code}' mapeado com sucesso")
                        else:
                            conversion_errors += 1
                            print(f"   ⚠️  Equipamento '{equipment_code}' não encontrado")
                    
                    print(f"   Conversões: {len(converted_records)} sucesso, {conversion_errors} falhas")
                    
                    # Salvar registros convertidos
                    if converted_records:
                        saved_count = await maintenance_processor.save_to_database(converted_records, DataType.MAINTENANCE)
                        maintenance_saved += saved_count
                        print(f"   SUCESSO: {saved_count} manutenções salvas")
                    
                except Exception as e:
                    print(f"   ERRO ao processar {file_path.name}: {e}")
            
            # COMMIT MANUTENÇÕES (transação separada)
            await maintenance_session.commit()
            print(f"\n✅ TRANSAÇÃO DE MANUTENÇÕES CONFIRMADA: {maintenance_saved} manutenções")
            
            # Resumo final
            print("\n" + "=" * 60)
            print("RESUMO DA POPULAÇÃO V3 - TRANSAÇÕES SEPARADAS")
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