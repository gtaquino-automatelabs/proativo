#!/usr/bin/env python3
"""
Script para configuração inicial do modelo Vanna.ai.

Este script:
1. Configura o modelo Vanna para o PROAtivo
2. Treina no schema do banco de dados
3. Adiciona exemplos de queries comuns
4. Valida o funcionamento básico
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Adicionar src ao path para execução dentro do container
current_dir = Path(__file__).parent
src_path = current_dir.parent.parent / "src"
sys.path.insert(0, str(src_path))

try:
    from api.services.vanna_service import get_vanna_service
    from api.services.vanna_query_processor import get_vanna_query_processor
    from database.connection import get_database_session
except ImportError:
    # Fallback para execução dentro do container Docker
    sys.path.insert(0, "/app/src")
    from api.services.vanna_service import get_vanna_service
    from api.services.vanna_query_processor import get_vanna_query_processor
    from database.connection import get_database_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def setup_vanna_model():
    """Configura e treina o modelo Vanna inicial."""
    logger.info("🚀 Iniciando setup do modelo Vanna.ai...")
    
    try:
        # 1. Inicializar serviços
        vanna_service = get_vanna_service()
        
        if not vanna_service.is_initialized:
            logger.error("❌ Vanna.ai não foi inicializado corretamente")
            return False
        
        logger.info("✅ Vanna.ai inicializado com sucesso")
        
        # 2. Treinar no schema do banco
        logger.info("📚 Treinando modelo no schema do banco de dados...")
        async with get_database_session() as db:
            success = await vanna_service.train_on_database_schema(db)
            
        if not success:
            logger.error("❌ Falha no treinamento do schema")
            return False
        
        logger.info("✅ Modelo treinado no schema do banco")
        
        # 3. Adicionar exemplos de queries comuns
        logger.info("📝 Adicionando exemplos de queries comuns...")
        await add_training_examples(vanna_service)
        
        # 3.5. Adicionar treinamento específico para subestações
        logger.info("🏭 Adicionando treinamento específico para relacionamento de subestações...")
        await add_substation_training(vanna_service)
        
        # 4. Testar funcionamento
        logger.info("🧪 Testando funcionamento do modelo...")
        success = await test_model_functionality()
        
        if success:
            logger.info("🎉 Setup do Vanna.ai concluído com sucesso!")
            return True
        else:
            logger.error("❌ Testes de funcionamento falharam")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro durante setup: {e}")
        return False

async def add_training_examples(vanna_service):
    """Adiciona exemplos de treinamento ao modelo."""
    
    # Exemplos de queries SQL com perguntas correspondentes
    training_examples = [
        {
            "question": "Quantos equipamentos temos no total?",
            "sql": "SELECT COUNT(*) as total_equipments FROM equipments WHERE status = 'Active';"
        },
        {
            "question": "Quais são os equipamentos críticos?",
            "sql": "SELECT code, name, equipment_type, criticality FROM equipments WHERE is_critical = true AND status = 'Active';"
        },
        {
            "question": "Liste os transformadores",
            "sql": "SELECT code, name, rated_voltage, rated_power FROM equipments WHERE equipment_type = 'Transformador' AND status = 'Active';"
        },
        {
            "question": "Manutenções pendentes este mês",
            "sql": """SELECT m.title, e.name as equipment_name, m.scheduled_date, m.priority 
                     FROM maintenances m 
                     JOIN equipments e ON m.equipment_id = e.id 
                     WHERE m.status = 'Planned' 
                     AND m.scheduled_date >= DATE_TRUNC('month', CURRENT_DATE) 
                     AND m.scheduled_date < DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month'
                     ORDER BY m.scheduled_date;"""
        },
        {
            "question": "Falhas críticas nos últimos 30 dias",
            "sql": """SELECT f.failure_type, e.name as equipment_name, f.failure_date, f.severity 
                     FROM failures f 
                     JOIN equipments e ON f.equipment_id = e.id 
                     WHERE f.severity = 'Critical' 
                     AND f.failure_date >= CURRENT_DATE - INTERVAL '30 days'
                     ORDER BY f.failure_date DESC;"""
        },
        {
            "question": "Planos de manutenção do PMM para próxima semana",
            "sql": """SELECT pmm.maintenance_plan_code, pmm.maintenance_item_text, 
                            pmm.planned_date, e.name as equipment_name
                     FROM pmm_2 pmm
                     LEFT JOIN equipments e ON pmm.equipment_id = e.id
                     WHERE pmm.status = 'Active'
                     AND pmm.planned_date >= CURRENT_DATE
                     AND pmm.planned_date <= CURRENT_DATE + INTERVAL '7 days'
                     ORDER BY pmm.planned_date;"""
        },
        {
            "question": "Equipamentos por localidade",
            "sql": """SELECT sl.denomination, COUNT(e.id) as total_equipments
                     FROM sap_locations sl
                     LEFT JOIN equipments e ON sl.id = e.sap_location_id
                     WHERE sl.status = 'Active'
                     GROUP BY sl.denomination
                     ORDER BY total_equipments DESC;"""
        },
        {
            "question": "Custo total de manutenções este ano",
            "sql": """SELECT SUM(actual_cost) as total_cost
                     FROM maintenances
                     WHERE completion_date >= DATE_TRUNC('year', CURRENT_DATE)
                     AND completion_date < DATE_TRUNC('year', CURRENT_DATE) + INTERVAL '1 year'
                     AND actual_cost IS NOT NULL;"""
        },
        {
            "question": "Disjuntores que precisam de manutenção",
            "sql": """SELECT e.code, e.name, m.scheduled_date, m.title
                     FROM equipments e
                     JOIN maintenances m ON e.id = m.equipment_id
                     WHERE e.equipment_type = 'Disjuntor'
                     AND m.status = 'Planned'
                     AND m.scheduled_date IS NOT NULL
                     ORDER BY m.scheduled_date;"""
        },
        {
            "question": "Histórico de falhas por tipo de equipamento",
            "sql": """SELECT e.equipment_type, COUNT(f.id) as total_failures, 
                            AVG(f.downtime_hours) as avg_downtime
                     FROM equipments e
                     LEFT JOIN failures f ON e.id = f.equipment_id
                     WHERE f.failure_date >= CURRENT_DATE - INTERVAL '1 year'
                     GROUP BY e.equipment_type
                     ORDER BY total_failures DESC;"""
        }
    ]
    
    # Treinar com cada exemplo
    for example in training_examples:
        try:
            vanna_service.vanna.train(
                question=example["question"],
                sql=example["sql"]
            )
            logger.info(f"✅ Treinado: {example['question']}")
        except Exception as e:
            logger.error(f"❌ Erro treinando exemplo '{example['question']}': {e}")

async def add_substation_training(vanna_service):
    """Adiciona treinamento específico para relacionamento de subestações."""
    
    # 1. Documentação sobre relacionamento de subestações
    documentation = """
    IMPORTANTE: Relacionamento entre Equipamentos e Subestações
    
    - A tabela 'equipments' contém uma coluna 'substation' com CÓDIGOS de localização (ex: MT-S-74399, MT-S-74102)
    - A tabela 'sap_locations' contém os nomes reais das subestações na coluna 'denomination' (ex: Emborcação, Itabira 2)
    - A tabela 'sap_locations' contém os nomes abreviados das subestações na coluna 'abbreviation' (ex: UEM, UJG)
    - Para filtrar equipamentos por nome de subestação, SEMPRE faça JOIN entre:
      equipments.substation = sap_locations.location_code
    - Nunca use WHERE equipments.substation = 'nome_subestacao' diretamente
    - Use sempre sap_locations.denomination para filtrar por nome de subestação
    - Use sempre sap_locations.abbreviation para filtrar por abreviação de subestação
    """
    
    # 2. Exemplos específicos de queries com JOIN para subestações
    substation_examples = [
        {
            "question": "Quantos equipamentos estão na subestação UEM?",
            "sql": """SELECT COUNT(e.id) as total_equipments
                     FROM equipments e 
                     JOIN sap_locations s ON e.substation = s.location_code 
                     WHERE s.abbreviation = 'UEM' AND e.status = 'Active';"""
        },
        {
            "question": "Quantos equipamentos estão ativos em UEM?",
            "sql": """SELECT COUNT(e.id) as total_equipments
                     FROM equipments e 
                     JOIN sap_locations s ON e.substation = s.location_code 
                     WHERE s.abbreviation = 'UEM' AND e.status = 'Active';"""
        },
        {
            "question": "Quantos equipamentos temos na subestação Emborcação?",
            "sql": """SELECT COUNT(e.id) as total_equipments
                     FROM equipments e 
                     JOIN sap_locations s ON e.substation = s.location_code 
                     WHERE s.denomination = 'Emborcação' AND e.status = 'Active';"""
        },
        {
            "question": "Quantos equipamentos estão ativos em UJG?",
            "sql": """SELECT COUNT(e.id) as total_equipments
                     FROM equipments e 
                     JOIN sap_locations s ON e.substation = s.location_code 
                     WHERE s.abbreviation = 'UJG' AND e.status = 'Active';"""
        },
        {
            "question": "Liste os equipamentos da subestação Itabira 2",
            "sql": """SELECT e.code, e.name, e.equipment_type, e.criticality, s.denomination
                     FROM equipments e 
                     JOIN sap_locations s ON e.substation = s.location_code 
                     WHERE s.denomination = 'Itabira 2' AND e.status = 'Active'
                     ORDER BY e.name;"""
        },
        {
            "question": "Transformadores na subestação Governador Valadares 2",
            "sql": """SELECT e.code, e.name, e.rated_voltage, e.rated_power, s.denomination
                     FROM equipments e 
                     JOIN sap_locations s ON e.substation = s.location_code 
                     WHERE s.denomination = 'Governador Valadares 2' 
                     AND e.equipment_type = 'Transformador' 
                     AND e.status = 'Active'
                     ORDER BY e.rated_power DESC;"""
        },
        {
            "question": "Equipamentos críticos na subestação São Gonçalo Pará",
            "sql": """SELECT e.code, e.name, e.equipment_type, e.criticality, s.denomination
                     FROM equipments e 
                     JOIN sap_locations s ON e.substation = s.location_code 
                     WHERE s.denomination = 'São Gonçalo Pará' 
                     AND e.is_critical = true 
                     AND e.status = 'Active'
                     ORDER BY e.name;"""
        }
    ]
    
    try:
        # Treinar com documentação
        vanna_service.vanna.train(documentation=documentation)
        logger.info("✅ Documentação de subestações treinada")
        
        # Treinar com exemplos específicos
        for example in substation_examples:
            try:
                vanna_service.vanna.train(
                    question=example["question"],
                    sql=example["sql"]
                )
                logger.info(f"✅ Treinado subestação: {example['question']}")
            except Exception as e:
                logger.error(f"❌ Erro treinando exemplo de subestação '{example['question']}': {e}")
                
        logger.info("🏭 Treinamento de subestações concluído")
        
    except Exception as e:
        logger.error(f"❌ Erro durante treinamento de subestações: {e}")

async def test_model_functionality():
    """Testa a funcionalidade básica do modelo."""
    hybrid_processor = get_vanna_query_processor()
    
    test_queries = [
        "Quantos equipamentos temos?",
        "Liste os transformadores críticos",
        "Manutenções pendentes",
        "Falhas dos últimos 30 dias",
        "Planos do PMM para esta semana"
    ]
    
    success_count = 0
    
    for query in test_queries:
        try:
            logger.info(f"🧪 Testando: {query}")
            result = await hybrid_processor.process_query(query)
            
            if result.sql_query:
                logger.info(f"✅ SQL gerado: {result.sql_query[:100]}...")
                logger.info(f"   Método: {result.processing_method}, Confiança: {result.confidence_score:.2f}")
                success_count += 1
            else:
                logger.warning(f"⚠️ Nenhum SQL gerado para: {query}")
                
        except Exception as e:
            logger.error(f"❌ Erro testando '{query}': {e}")
    
    success_rate = success_count / len(test_queries)
    logger.info(f"📊 Taxa de sucesso nos testes: {success_rate:.1%} ({success_count}/{len(test_queries)})")
    
    return success_rate >= 0.5  # Pelo menos 50% de sucesso

def print_usage_info():
    """Imprime informações de uso e próximos passos."""
    print("\n" + "="*50)
    print("📋 PRÓXIMOS PASSOS:")
    print("="*50)
    print("1. ✅ Vanna.ai configurado e treinado")
    print("2. 🔧 Integre no endpoint de chat:")
    print("   - Importe get_vanna_query_processor")
    print("   - Use process_query() em vez de query_processor")
    print("3. 📊 Monitore as métricas de uso:")
    print("   - hybrid_processor.get_usage_statistics()")
    print("4. 🎯 Ajuste o threshold de confiança se necessário:")
    print("   - hybrid_processor.update_confidence_threshold(0.8)")
    print("5. 🔄 Implemente feedback do usuário para melhoria contínua")
    print("\n💡 DICAS:")
    print("- Threshold padrão: 0.7 (70% confiança)")
    print("- Queries abaixo do threshold usam fallback")
    print("- Feedback positivo treina o modelo automaticamente")
    print("="*50)

if __name__ == "__main__":
    print("🔧 PROAtivo - Setup Vanna.ai Model")
    print("="*50)
    
    result = asyncio.run(setup_vanna_model())
    
    if result:
        print_usage_info()
        sys.exit(0)
    else:
        print("\n❌ Setup falhou. Verifique os logs acima.")
        sys.exit(1) 