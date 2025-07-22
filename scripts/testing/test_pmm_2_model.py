#!/usr/bin/env python3
"""
Script de teste para validar o modelo PMM_2 e seus relacionamentos.

Este script testa a criação, consulta e relacionamentos do modelo PMM_2
com os modelos existentes de Equipment e Maintenance.
"""

import asyncio
import logging
from pathlib import Path
import sys
from datetime import datetime, date
from typing import List, Optional

# Adiciona o diretório raiz do projeto ao Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.database.connection import get_db_session
from src.database.models import PMM_2, Equipment, Maintenance
from src.database.repositories import PMM_2Repository, EquipmentRepository, MaintenanceRepository
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


async def test_pmm_2_model_creation():
    """Testa a criação de registros PMM_2."""
    
    logger.info("Testando criação de registros PMM_2...")
    
    async with get_db_session() as session:
        pmm_2_repo = PMM_2Repository(session)
        
        # Dados de teste
        test_data = {
            "maintenance_plan_code": "TEST001A",
            "work_center": "TTESTPM",
            "maintenance_item_text": "Teste operativo (TEST) CH-001",
            "installation_location": "MT-S-TEST-FE01-CH-001",
            "equipment_code": "CH-001",
            "planned_date": datetime(2025, 1, 15),
            "scheduled_start_date": datetime(2025, 1, 10),
            "completion_date": None,
            "last_order": "2200000001",
            "current_order": "2200000001",
            "status": "Active",
            "data_source": "SAP",
            "import_batch_id": "TEST_BATCH_001"
        }
        
        try:
            # Criar registro
            pmm_2_record = await pmm_2_repo.create(**test_data)
            
            logger.info(f"✓ Registro PMM_2 criado com sucesso: {pmm_2_record.id}")
            logger.info(f"  - Código: {pmm_2_record.maintenance_plan_code}")
            logger.info(f"  - Centro de trabalho: {pmm_2_record.work_center}")
            logger.info(f"  - Equipamento: {pmm_2_record.equipment_code}")
            
            # Buscar registro criado
            found_record = await pmm_2_repo.find_by_maintenance_plan_code("TEST001A")
            
            if found_record:
                logger.info("✓ Registro encontrado pela busca")
                assert found_record.id == pmm_2_record.id
                assert found_record.maintenance_plan_code == test_data["maintenance_plan_code"]
                assert found_record.work_center == test_data["work_center"]
                logger.info("✓ Dados do registro validados com sucesso")
            else:
                logger.error("✗ Registro não encontrado pela busca")
                return False
                
            await session.commit()
            return True
            
        except Exception as e:
            logger.error(f"✗ Erro ao criar registro PMM_2: {e}")
            await session.rollback()
            return False


async def test_pmm_2_equipment_relationship():
    """Testa o relacionamento entre PMM_2 e Equipment."""
    
    logger.info("Testando relacionamento PMM_2 <-> Equipment...")
    
    async with get_db_session() as session:
        pmm_2_repo = PMM_2Repository(session)
        equipment_repo = EquipmentRepository(session)
        
        try:
            # Criar equipamento de teste
            equipment_data = {
                "code": "CH-TEST-001",
                "name": "Chave Teste 001",
                "equipment_type": "Chave",
                "criticality": "Medium",
                "location": "MT-S-TEST-FE01-CH-001",
                "status": "Active"
            }
            
            equipment = await equipment_repo.create(**equipment_data)
            logger.info(f"✓ Equipamento criado: {equipment.code}")
            
            # Criar PMM_2 associado ao equipamento
            pmm_2_data = {
                "maintenance_plan_code": "TEST002A",
                "work_center": "TTESTPM",
                "maintenance_item_text": "Teste relacionamento equipamento",
                "installation_location": "MT-S-TEST-FE01-CH-001",
                "equipment_code": "CH-TEST-001",
                "equipment_id": equipment.id,
                "planned_date": datetime(2025, 2, 15),
                "status": "Active",
                "data_source": "SAP"
            }
            
            pmm_2_record = await pmm_2_repo.create(**pmm_2_data)
            logger.info(f"✓ PMM_2 criado com relacionamento: {pmm_2_record.maintenance_plan_code}")
            
            # Testar busca por equipamento
            pmm_2_plans = await pmm_2_repo.find_by_equipment_code("CH-TEST-001")
            
            if pmm_2_plans:
                logger.info(f"✓ Encontrados {len(pmm_2_plans)} planos para o equipamento")
                assert pmm_2_plans[0].equipment_id == equipment.id
                logger.info("✓ Relacionamento validado com sucesso")
            else:
                logger.error("✗ Planos não encontrados para o equipamento")
                return False
                
            # Testar linking programático
            pmm_2_orphan = await pmm_2_repo.create(
                maintenance_plan_code="TEST003A",
                work_center="TTESTPM",
                maintenance_item_text="Teste linking",
                installation_location="MT-S-TEST-FE01-CH-001",
                equipment_code="CH-TEST-001",
                status="Active"
            )
            
            success = await pmm_2_repo.link_to_equipment(pmm_2_orphan.id, equipment.id)
            
            if success:
                logger.info("✓ Linking programático funcionou")
            else:
                logger.error("✗ Erro no linking programático")
                return False
                
            await session.commit()
            return True
            
        except Exception as e:
            logger.error(f"✗ Erro ao testar relacionamento: {e}")
            await session.rollback()
            return False


async def test_pmm_2_maintenance_relationship():
    """Testa o relacionamento entre PMM_2 e Maintenance."""
    
    logger.info("Testando relacionamento PMM_2 <-> Maintenance...")
    
    async with get_db_session() as session:
        pmm_2_repo = PMM_2Repository(session)
        equipment_repo = EquipmentRepository(session)
        maintenance_repo = MaintenanceRepository(session)
        
        try:
            # Usar equipamento existente ou criar novo
            equipment = await equipment_repo.find_by_code("CH-TEST-001")
            if not equipment:
                equipment = await equipment_repo.create(
                    code="CH-TEST-002",
                    name="Chave Teste 002",
                    equipment_type="Chave",
                    criticality="Medium",
                    status="Active"
                )
                logger.info(f"✓ Equipamento criado: {equipment.code}")
            
            # Criar manutenção
            maintenance_data = {
                "equipment_id": equipment.id,
                "maintenance_code": "MAINT-TEST-001",
                "maintenance_type": "Preventive",
                "priority": "Medium",
                "title": "Manutenção de teste",
                "description": "Teste de relacionamento com PMM_2",
                "scheduled_date": datetime(2025, 3, 15),
                "status": "Planned"
            }
            
            maintenance = await maintenance_repo.create(**maintenance_data)
            logger.info(f"✓ Manutenção criada: {maintenance.maintenance_code}")
            
            # Criar PMM_2 associado à manutenção
            pmm_2_data = {
                "maintenance_plan_code": "TEST004A",
                "work_center": "TTESTPM",
                "maintenance_item_text": "Teste relacionamento manutenção",
                "installation_location": "MT-S-TEST-FE01-CH-002",
                "equipment_code": "CH-TEST-002",
                "equipment_id": equipment.id,
                "maintenance_id": maintenance.id,
                "planned_date": datetime(2025, 3, 15),
                "status": "Active",
                "data_source": "SAP"
            }
            
            pmm_2_record = await pmm_2_repo.create(**pmm_2_data)
            logger.info(f"✓ PMM_2 criado com relacionamento de manutenção: {pmm_2_record.maintenance_plan_code}")
            
            # Verificar relacionamento
            assert pmm_2_record.equipment_id == equipment.id
            assert pmm_2_record.maintenance_id == maintenance.id
            
            logger.info("✓ Relacionamento PMM_2 <-> Maintenance validado")
            
            await session.commit()
            return True
            
        except Exception as e:
            logger.error(f"✗ Erro ao testar relacionamento com manutenção: {e}")
            await session.rollback()
            return False


async def test_pmm_2_repository_methods():
    """Testa os métodos específicos do PMM_2Repository."""
    
    logger.info("Testando métodos do PMM_2Repository...")
    
    async with get_db_session() as session:
        pmm_2_repo = PMM_2Repository(session)
        
        try:
            # Testar busca por centro de trabalho
            work_center_plans = await pmm_2_repo.find_by_work_center("TTESTPM")
            logger.info(f"✓ Encontrados {len(work_center_plans)} planos para centro de trabalho TTESTPM")
            
            # Testar busca por localização
            location_plans = await pmm_2_repo.find_by_installation_location("MT-S-TEST-FE01-CH-001")
            logger.info(f"✓ Encontrados {len(location_plans)} planos para localização")
            
            # Testar busca por intervalo de datas
            date_range_plans = await pmm_2_repo.find_by_date_range(
                date(2025, 1, 1), 
                date(2025, 12, 31)
            )
            logger.info(f"✓ Encontrados {len(date_range_plans)} planos no intervalo de datas")
            
            # Testar busca por status
            active_plans = await pmm_2_repo.find_by_status("Active")
            logger.info(f"✓ Encontrados {len(active_plans)} planos ativos")
            
            # Testar busca de planos órfãos
            orphaned_plans = await pmm_2_repo.find_orphaned_plans()
            logger.info(f"✓ Encontrados {len(orphaned_plans)} planos órfãos")
            
            # Testar busca de planos com equipamento
            with_equipment_plans = await pmm_2_repo.find_with_equipment()
            logger.info(f"✓ Encontrados {len(with_equipment_plans)} planos com equipamento")
            
            # Testar estatísticas
            statistics = await pmm_2_repo.get_statistics()
            logger.info("✓ Estatísticas obtidas:")
            logger.info(f"  - Total de planos: {statistics['total_plans']}")
            logger.info(f"  - Planos órfãos: {statistics['orphaned_plans']}")
            logger.info(f"  - Taxa de vinculação: {statistics['linked_rate']:.1f}%")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Erro ao testar métodos do repository: {e}")
            return False


async def test_pmm_2_upsert():
    """Testa a funcionalidade de upsert do PMM_2."""
    
    logger.info("Testando funcionalidade de upsert...")
    
    async with get_db_session() as session:
        pmm_2_repo = PMM_2Repository(session)
        
        try:
            # Primeiro upsert (insert)
            plan_data = {
                "work_center": "TTESTPM",
                "maintenance_item_text": "Teste upsert inicial",
                "installation_location": "MT-S-TEST-UPSERT",
                "equipment_code": "CH-UPSERT-001",
                "planned_date": datetime(2025, 4, 15),
                "status": "Active"
            }
            
            plan1 = await pmm_2_repo.upsert("UPSERT001A", **plan_data)
            logger.info(f"✓ Primeiro upsert (insert): {plan1.id}")
            
            # Segundo upsert (update)
            plan_data["maintenance_item_text"] = "Teste upsert atualizado"
            plan_data["status"] = "Completed"
            
            plan2 = await pmm_2_repo.upsert("UPSERT001A", **plan_data)
            logger.info(f"✓ Segundo upsert (update): {plan2.id}")
            
            # Verificar que é o mesmo registro
            assert plan1.id == plan2.id
            assert plan2.maintenance_item_text == "Teste upsert atualizado"
            assert plan2.status == "Completed"
            
            logger.info("✓ Funcionalidade de upsert validada")
            
            await session.commit()
            return True
            
        except Exception as e:
            logger.error(f"✗ Erro ao testar upsert: {e}")
            await session.rollback()
            return False


async def cleanup_test_data():
    """Remove dados de teste criados."""
    
    logger.info("Limpando dados de teste...")
    
    async with get_db_session() as session:
        try:
            # Remover registros PMM_2 de teste
            await session.execute(
                "DELETE FROM pmm_2 WHERE maintenance_plan_code LIKE 'TEST%' OR maintenance_plan_code LIKE 'UPSERT%'"
            )
            
            # Remover manutenções de teste
            await session.execute(
                "DELETE FROM maintenances WHERE maintenance_code LIKE 'MAINT-TEST%'"
            )
            
            # Remover equipamentos de teste
            await session.execute(
                "DELETE FROM equipments WHERE code LIKE 'CH-TEST%' OR code LIKE 'CH-UPSERT%'"
            )
            
            await session.commit()
            logger.info("✓ Dados de teste removidos")
            
        except Exception as e:
            logger.error(f"✗ Erro ao limpar dados de teste: {e}")
            await session.rollback()


async def main():
    """Função principal do script de teste."""
    
    logger.info("=== Iniciando testes do modelo PMM_2 ===")
    
    tests = [
        ("Criação de registros PMM_2", test_pmm_2_model_creation),
        ("Relacionamento PMM_2 <-> Equipment", test_pmm_2_equipment_relationship),
        ("Relacionamento PMM_2 <-> Maintenance", test_pmm_2_maintenance_relationship),
        ("Métodos do PMM_2Repository", test_pmm_2_repository_methods),
        ("Funcionalidade de upsert", test_pmm_2_upsert),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} ---")
        
        try:
            result = await test_func()
            results.append((test_name, result))
            
            if result:
                logger.info(f"✓ {test_name}: PASSOU")
            else:
                logger.error(f"✗ {test_name}: FALHOU")
                
        except Exception as e:
            logger.error(f"✗ {test_name}: ERRO - {e}")
            results.append((test_name, False))
    
    # Limpar dados de teste
    await cleanup_test_data()
    
    # Resumo dos resultados
    logger.info("\n=== RESUMO DOS TESTES ===")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSOU" if result else "✗ FALHOU"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nResultado final: {passed}/{total} testes passaram")
    
    if passed == total:
        logger.info("🎉 Todos os testes passaram! Modelo PMM_2 está funcionando corretamente.")
    else:
        logger.error("❌ Alguns testes falharam. Verifique os logs acima.")


if __name__ == "__main__":
    asyncio.run(main()) 