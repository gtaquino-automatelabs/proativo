#!/usr/bin/env python3
"""
Script melhorado para popular o banco de dados V3.
Usa lógica upsert para evitar duplicatas e é mais robusta.
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Any

# Configurar paths
current_dir = Path(__file__).parent              # scripts/setup/
project_dir = current_dir.parent.parent          # proativo/ (raiz do projeto)
src_dir = project_dir / "src"                    # proativo/src/
sys.path.insert(0, str(project_dir))             # adicionar raiz ao sys.path
os.environ['PYTHONPATH'] = str(project_dir)      # configurar PYTHONPATH para raiz

try:
    from src.etl.data_processor import DataProcessor, DataType, FileFormat
    from src.database.repositories import RepositoryManager
    from src.database.connection import db_connection, create_tables
except ImportError as e:
    print(f"ERRO de importação: {e}")
    sys.exit(1)


async def populate_database_v3():
    """Popula o banco de dados com lógica upsert melhorada."""
    print("INICIANDO POPULAÇÃO DO BANCO DE DADOS V3...")
    print("=" * 60)
    
    try:
        print("Módulos importados com sucesso")
        
        # Configurar logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Inicializar conexão com banco de dados
        print("Inicializando conexão com banco de dados...")
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
            
            # ETAPA 1: Processar equipamentos (com upsert)
            print("\n" + "=" * 60)
            print("ETAPA 1: PROCESSANDO EQUIPAMENTOS")
            print("=" * 60)
            
            equipment_files = [
                "data/samples/equipment.csv",
                # Adicione outros arquivos conforme necessário
                # "data/samples/equipment.xml",
                # "data/samples/electrical_assets.xlsx"
            ]
            
            equipment_processed = 0
            equipment_map = {}  # código -> UUID
            
            for file_path_str in equipment_files:
                file_path = Path(file_path_str)
                if not file_path.exists():
                    print(f"⚠️  Arquivo não encontrado: {file_path}")
                    continue
                
                print(f"\n📁 Processando equipamentos: {file_path.name}")
                
                try:
                    # Processa e salva com lógica upsert
                    result = await processor.process_and_save(file_path, DataType.EQUIPMENT)
                    
                    if result['success']:
                        equipment_processed += result['saved_records']
                        print(f"   ✅ SUCESSO: {result['saved_records']} equipamentos processados")
                        print(f"   📊 Tempo: {result['processing_time_seconds']:.2f}s")
                        
                        if result['validation_errors']:
                            print(f"   ⚠️  {len(result['validation_errors'])} erros de validação")
                            for error in result['validation_errors'][:3]:  # Mostra apenas os 3 primeiros
                                print(f"      - {error}")
                            if len(result['validation_errors']) > 3:
                                print(f"      ... e mais {len(result['validation_errors'])-3} erros")
                    else:
                        print(f"   ❌ FALHA: {result.get('error', 'Erro desconhecido')}")
                        
                except Exception as e:
                    print(f"   ❌ ERRO ao processar {file_path.name}: {e}")
            
            # Atualizar mapeamento código->UUID
            print("\n📋 Atualizando mapeamento código->UUID...")
            try:
                equipments = await repository_manager.equipment.list_all(limit=1000)
                for eq in equipments:
                    equipment_map[eq.code] = str(eq.id)
                print(f"   ✅ Mapeamento atualizado: {len(equipment_map)} equipamentos")
            except Exception as e:
                print(f"   ❌ Erro ao buscar equipamentos: {e}")
            
            print(f"\n📈 Resumo Etapa 1:")
            print(f"   Equipamentos processados: {equipment_processed}")
            print(f"   Equipamentos no banco: {len(equipment_map)}")
            
            # ETAPA 2: Processar manutenções
            print("\n" + "=" * 60)
            print("ETAPA 2: PROCESSANDO MANUTENÇÕES")
            print("=" * 60)
            
            if len(equipment_map) == 0:
                print("⚠️  AVISO: Nenhum equipamento no banco. Pulando manutenções.")
            else:
                maintenance_files = [
                    "data/samples/maintenance_orders.csv",
                    "data/samples/maintenance_schedules.csv",
                    # "data/samples/maintenance_orders.xml"
                ]
                
                maintenance_processed = 0
                
                for file_path_str in maintenance_files:
                    file_path = Path(file_path_str)
                    if not file_path.exists():
                        print(f"⚠️  Arquivo não encontrado: {file_path}")
                        continue
                    
                    print(f"\n📁 Processando manutenções: {file_path.name}")
                    
                    try:
                        # Processar arquivo mas NÃO salvar ainda
                        valid_records, validation_errors = processor.process_file(file_path, DataType.MAINTENANCE)
                        
                        print(f"   📊 Registros processados: {len(valid_records)} válidos, {len(validation_errors)} inválidos")
                        
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
                                if conversion_errors <= 5:  # Mostra apenas os 5 primeiros
                                    print(f"   ⚠️  Equipamento '{equipment_code}' não encontrado")
                        
                        if conversion_errors > 5:
                            print(f"   ⚠️  ... e mais {conversion_errors-5} equipamentos não encontrados")
                        
                        print(f"   🔄 Conversões: {len(converted_records)} sucesso, {conversion_errors} falhas")
                        
                        # Salvar registros convertidos
                        if converted_records:
                            saved_count = await processor.save_to_database(converted_records, DataType.MAINTENANCE)
                            maintenance_processed += saved_count
                            print(f"   ✅ SUCESSO: {saved_count} manutenções salvas")
                        
                    except Exception as e:
                        print(f"   ❌ ERRO ao processar {file_path.name}: {e}")
                
                print(f"\n📈 Resumo Etapa 2:")
                print(f"   Manutenções processadas: {maintenance_processed}")
            
            # Commit das transações
            print("\n💾 Salvando mudanças no banco...")
            await session.commit()
            
            # Estatísticas finais
            print("\n" + "=" * 60)
            print("📊 RESUMO FINAL DA POPULAÇÃO V3")
            print("=" * 60)
            
            # Buscar estatísticas atuais do banco
            try:
                total_equipments = await repository_manager.equipment.count()
                total_maintenances = await repository_manager.maintenance.count()
                
                print(f"✅ Equipamentos no banco: {total_equipments}")
                print(f"✅ Manutenções no banco: {total_maintenances}")
                print(f"✅ Total de registros: {total_equipments + total_maintenances}")
                
                if total_equipments > 0 or total_maintenances > 0:
                    print("\n🎉 BANCO DE DADOS POPULADO COM SUCESSO!")
                    return True
                else:
                    print("\n❌ ERRO: Nenhum registro foi criado")
                    return False
                    
            except Exception as e:
                print(f"❌ Erro ao buscar estatísticas finais: {e}")
                return False
            
    except Exception as e:
        print(f"❌ ERRO inesperado: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Função principal."""
    print("🚀 SCRIPT DE POPULAÇÃO DO BANCO DE DADOS V3")
    print("=" * 60)
    print("Características:")
    print("✅ Lógica upsert (insert ou update)")
    print("✅ Tratamento de duplicatas")
    print("✅ Logs detalhados")
    print("✅ Estatísticas em tempo real")
    print("=" * 60)
    
    try:
        success = asyncio.run(populate_database_v3())
        
        if success:
            print("\n🎉 Script executado com sucesso!")
            print("💡 Dica: Execute o script de limpeza se ainda houver duplicatas")
            return 0
        else:
            print("\n❌ Script executado com problemas")
            print("💡 Dica: Verifique os logs acima para mais detalhes")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️  Script interrompido pelo usuário")
        return 1
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 