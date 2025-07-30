"""
Serviço de Auto-Treinamento do Vanna.ai.

Este módulo monitora mudanças no schema do banco de dados e 
executa automaticamente o re-treinamento do modelo Vanna quando necessário.
"""

import asyncio
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from .vanna_service import get_vanna_service
from ..config import get_settings
from ...database.connection import get_async_session

logger = logging.getLogger(__name__)

@dataclass
class SchemaChecksum:
    """Checksum do schema do banco para detectar mudanças."""
    checksum: str
    timestamp: datetime
    tables_count: int
    columns_count: int

class VannaAutoTrainer:
    """
    Serviço de auto-treinamento do Vanna.ai.
    
    Funcionalidades:
    - Detecta mudanças no schema do banco
    - Executa re-treinamento automático
    - Agenda execuções periódicas
    - Monitora performance do modelo
    """
    
    def __init__(self):
        """Inicializa o auto-trainer."""
        self.settings = get_settings()
        self.vanna_service = get_vanna_service()
        self.last_schema_checksum: Optional[SchemaChecksum] = None
        self.last_training_time: Optional[datetime] = None
        self.training_in_progress = False
        
        # Configurações de monitoramento
        self.check_interval_minutes = 60  # Verificar a cada hora
        self.force_retrain_hours = 24 * 7  # Forçar re-treinamento semanal
        self.min_interval_between_training_hours = 2  # Mínimo 2h entre treinamentos
    
    async def start_monitoring(self):
        """Inicia o monitoramento automático do schema."""
        if not self.settings.vanna_enable_training:
            logger.info("Auto-training disabled in configuration")
            return
        
        logger.info("Starting Vanna auto-trainer monitoring")
        
        # Verificação inicial
        await self._check_and_retrain_if_needed()
        
        # Loop de monitoramento
        while True:
            try:
                await asyncio.sleep(self.check_interval_minutes * 60)
                await self._check_and_retrain_if_needed()
            except Exception as e:
                logger.error(f"Error in auto-trainer monitoring loop: {e}")
                await asyncio.sleep(300)  # Esperar 5 minutos antes de tentar novamente
    
    async def _check_and_retrain_if_needed(self):
        """Verifica se é necessário re-treinar o modelo."""
        if self.training_in_progress:
            logger.info("Training already in progress, skipping check")
            return
        
        try:
            # Calcular checksum atual do schema
            current_checksum = await self._calculate_schema_checksum()
            
            # Verificar se houve mudanças
            schema_changed = (
                self.last_schema_checksum is None or
                current_checksum.checksum != self.last_schema_checksum.checksum
            )
            
            # Verificar se precisa forçar re-treinamento por tempo
            time_based_retrain = (
                self.last_training_time is None or
                datetime.now() - self.last_training_time > timedelta(hours=self.force_retrain_hours)
            )
            
            # Verificar intervalo mínimo entre treinamentos
            min_interval_ok = (
                self.last_training_time is None or
                datetime.now() - self.last_training_time > timedelta(hours=self.min_interval_between_training_hours)
            )
            
            if (schema_changed or time_based_retrain) and min_interval_ok:
                reason = "schema_changed" if schema_changed else "scheduled_retrain"
                logger.info(f"Triggering auto-training: {reason}")
                
                await self._execute_training()
                self.last_schema_checksum = current_checksum
                self.last_training_time = datetime.now()
            else:
                logger.debug("No training needed at this time")
                
        except Exception as e:
            logger.error(f"Error checking training requirements: {e}")
    
    async def _calculate_schema_checksum(self) -> SchemaChecksum:
        """Calcula checksum do schema atual do banco."""
        async with get_async_session() as db:
            # Query para obter informações sobre todas as tabelas e colunas
            schema_query = """
            SELECT 
                t.table_name,
                c.column_name,
                c.data_type,
                c.is_nullable,
                c.column_default
            FROM information_schema.tables t
            JOIN information_schema.columns c ON t.table_name = c.table_name
            WHERE t.table_schema = 'public'
            AND t.table_name IN ('equipments', 'maintenances', 'failures', 'pmm_2', 'sap_locations', 'user_feedback', 'upload_status')
            ORDER BY t.table_name, c.ordinal_position;
            """
            
            result = await db.execute(text(schema_query))
            rows = result.fetchall()
            
            # Criar string representativa do schema
            schema_str = ""
            tables_count = 0
            columns_count = len(rows)
            current_table = None
            
            for row in rows:
                if row.table_name != current_table:
                    tables_count += 1
                    current_table = row.table_name
                
                schema_str += f"{row.table_name}|{row.column_name}|{row.data_type}|{row.is_nullable}|{row.column_default or ''}\n"
            
            # Calcular hash MD5 do schema
            checksum = hashlib.md5(schema_str.encode()).hexdigest()
            
            return SchemaChecksum(
                checksum=checksum,
                timestamp=datetime.now(),
                tables_count=tables_count,
                columns_count=columns_count
            )
    
    async def _execute_training(self):
        """Executa o treinamento do modelo Vanna."""
        if not self.vanna_service.is_initialized:
            logger.error("Vanna service not initialized, cannot train")
            return False
        
        self.training_in_progress = True
        
        try:
            logger.info("🤖 Starting automatic Vanna training...")
            
            # 1. Treinar no schema atualizado
            async with get_async_session() as db:
                schema_success = await self.vanna_service.train_on_database_schema(db)
            
            if not schema_success:
                logger.error("Schema training failed")
                return False
            
            # 2. Adicionar exemplos básicos (apenas se não existirem)
            await self._add_basic_training_examples()
            
            # 2.5. Adicionar treinamento específico para subestações
            await self._add_substation_training()
            
            # 3. Validar funcionamento básico
            validation_success = await self._validate_training()
            
            if validation_success:
                logger.info("✅ Automatic Vanna training completed successfully")
                return True
            else:
                logger.warning("⚠️ Training completed but validation failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error during automatic training: {e}")
            return False
        finally:
            self.training_in_progress = False
    
    async def _add_basic_training_examples(self):
        """Adiciona exemplos básicos de treinamento."""
        basic_examples = [
            {
                "question": "Quantos equipamentos ativos temos?",
                "sql": "SELECT COUNT(*) as total FROM equipments WHERE status = 'Active';"
            },
            {
                "question": "Liste equipamentos críticos",
                "sql": "SELECT code, name, equipment_type FROM equipments WHERE is_critical = true AND status = 'Active';"
            },
            {
                "question": "Manutenções planejadas",
                "sql": """SELECT 
                            pmm.maintenance_plan_code, pmm.maintenance_item_text as test_type,
                            pmm.equipment_code as equipment_name, s.denomination, pmm.planned_date
                            FROM pmm_2 pmm 
                            JOIN sap_locations s ON pmm.sap_location_id = s.id  
                            WHERE pmm.planned_date >= 'NOW' AND pmm.completion_date is NULL;"""
            }
        ]
        
        for example in basic_examples:
            try:
                self.vanna_service.vanna.train(
                    question=example["question"],
                    sql=example["sql"]
                )
                logger.debug(f"Added training example: {example['question']}")
            except Exception as e:
                logger.warning(f"Failed to add training example: {e}")
    
    async def _add_substation_training(self):
        """
        Adiciona treinamento específico para relacionamento de subestações.
        
        Este método treina o modelo para entender corretamente como relacionar
        equipamentos com subestações usando JOINs apropriados.
        """
        logger.info("🏭 Adding substation relationship training...")
        
        # 1. Documentação sobre relacionamento de subestações
        documentation = """
        IMPORTANTE: Relacionamento entre Equipamentos e Subestações
        
        - A tabela 'equipments' contém uma coluna 'substation' com CÓDIGOS de localização (ex: MT-S-74399, MT-S-74102)
        - A tabela 'sap_locations' contém os nomes reais das subestações na coluna 'denomination' (ex: Emborcação, Itabira 2)
        - A tabela 'sap_locations' contém os nomes abreviados das subestações na coluna 'abbreviation' (ex: UEM, UJG)
        - Para filtrar equipamentos por nome de subestação, SEMPRE faça JOIN entre:
          equipments.substation = sap_locations.location_code
        - Nunca use WHERE equipments.substation = 'nome_subestacao' diretamente
        - Para abreviações como UEM, UJG use: sap_locations.abbreviation 
        - Para nomes completos como Emborcação, Itabira 2 use: sap_locations.denomination
        
        EXEMPLOS DE PADRÕES CORRETOS:
        - "equipamentos em UEM" → WHERE s.abbreviation = 'UEM'
        - "equipamentos na subestação Emborcação" → WHERE s.denomination = 'Emborcação'
        - Sempre incluir: JOIN sap_locations s ON e.substation = s.location_code

        RELACIONAMENTO DE PLANOS DE MANUTENÇÃO:
        - A tabela 'pmm_2' contém os planos de manutenção na coluna 'maintenance_plan_code' que é único para cada tipo de teste de cada equipamento.
        - A tabela 'pmm_2' contém os itens de manutenção na coluna 'maintenance_item_text' que é o nome do teste.
        - A tabela 'pmm_2' contém o código do equipamento na coluna 'equipment_code' que é o código do equipamento. (ex: DJ-1U4, CH-1U5, TC-1U4, etc)
        - Para filtrar planos de manutenção por equipamento, SEMPRE faça: pmm_2.equipment_code ILIKE '%codigo_equipamento%'
        - A tabela 'pmm_2' contém o nome da subestação na coluna 'sap_location_id' que é o código da subestação.
        - Nunca use WHERE pmm_2.sap_location_id = 'nome_subestacao' diretamente
        - A tabela 'pmm_2' contém a data de planejamento na coluna 'planned_date' que é a data de planejamento do teste.
        - A tabela 'pmm_2' contém a data de conclusão na coluna 'completion_date' que é a data de conclusão do teste.
        - Para filtrar planos de manutenção por subestação, SEMPRE faça JOIN entre:
            pmm_2.sap_location_id = sap_locations.id
        - SEMPRE incluir: JOIN sap_locations s ON pmm.sap_location_id = s.id
        - Para determinar se um plano de manutenção está vencido, planejado ou a vencer, use a coluna 'planned_date' e 'completion_date'.

        EXEMPLOS CORRETOS:
        - "planos de manutenção para o equipamento 2U4 de São Simão" → WHERE pmm_2.equipment_code = '2U4' AND s.denomination = 'São Simão'
        - "planos de manutenção a vencer em Jaguara" → WHERE s.denomination = 'Jaguara' AND pmm_2.planned_date >= 'NOW' AND pmm_2.completion_date is NULL
        - "planos de manutenção vencidos em Nova Ponte" → WHERE s.denomination = 'Nova Ponte' AND pmm_2.planned_date < 'NOW' AND pmm_2.completion_date is NULL

        EXEMPLOS INCORRETOS:
        - "localizados em áreas como MT-S-41105-FT07 e MT-S-41105-FT06." → Este código númerico não é bom para linguagem natural,
            use sempre o nome da subestação (s.denomination).
        - "status 'Active' não é sinônimo de status de planejamento, mas de condição operativa (ativo ou inativo).
        - WHERE pmm.equipment_code = ILIKE '%4K4%' → WHERE pmm.equipment_code ILIKE '%4K4%'. Não use '=' ao usar ILIKE.
        
        RELACIONAMENTO DE EQUIPAMENTOS:
        - A tabela equipamentos contém na coluna equipment_code uma combinação de tipo de equipamento e id do equipamento.
        - A coluna location é um código de localização único que contém os parâmetros: {MT-S-41150 = sap_location.location_code}
                                                                                        DG02 = Representa a que função o equipamento está ligado (DG = Disjuntor Gerador, DL = Disjuntor Linha, FT = Transformador, etc)
                                                                                        DJ-1U4 = Representa o número do equipamento (DJ-1U4 = Disjuntor 1U4, CH-1U5 = Seccionadora 1U5, TC-1U4 = Transformador de Corrente 1U4, etc)
        
        EXEMPLOS DE PADRÕES CORRETOS:
        - "chave 4K3" → WHERE e.equipment_code ILIKE '%4K3%'
        """
        
        try:
            # Treinar com documentação
            self.vanna_service.vanna.train(documentation=documentation)
            logger.info("✅ Substation documentation trained")
        except Exception as e: 
            logger.warning(f"Failed to train substation documentation: {e}")
        
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
                "question": "Quantos equipamentos estão ativos em UJG?",
                "sql": """SELECT COUNT(e.id) as total_equipments
                         FROM equipments e 
                         JOIN sap_locations s ON e.substation = s.location_code 
                         WHERE s.abbreviation = 'UJG' AND e.status = 'Active';"""
            },
            {
                "question": "Quantos equipamentos temos na subestação Emborcação?",
                "sql": """SELECT COUNT(e.id) as total_equipments
                         FROM equipments e 
                         JOIN sap_locations s ON e.substation = s.location_code 
                         WHERE s.denomination = 'Emborcação' AND e.status = 'Active';"""
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
            },
            {
                "question": "Disjuntores em UJG",
                "sql": """SELECT e.code, e.name, e.rated_voltage, s.abbreviation
                         FROM equipments e 
                         JOIN sap_locations s ON e.substation = s.location_code 
                         WHERE s.abbreviation = 'UJG' 
                         AND e.equipment_type = 'Disjuntor' 
                         AND e.status = 'Active'
                         ORDER BY e.rated_voltage DESC;"""
            },
            {
                "question": "Quantos transformadores temos na subestação Pimenta (SPE)?",
                "sql": """SELECT COUNT(e.id) as total_transformers
                         FROM equipments e 
                         JOIN sap_locations s ON e.substation = s.location_code 
                         WHERE s.denomination = 'Pimenta (SPE)' 
                         AND e.equipment_type = 'Transformador' 
                         AND e.status = 'Active';"""
            },
            {
                "question": "Equipamentos por subestação - top 5",
                "sql": """SELECT s.denomination, s.abbreviation, COUNT(e.id) as total_equipments
                         FROM equipments e 
                         JOIN sap_locations s ON e.substation = s.location_code 
                         WHERE e.status = 'Active'
                         GROUP BY s.denomination, s.abbreviation
                         ORDER BY total_equipments DESC
                         LIMIT 5;"""
            }
        ]
        
        # Treinar com exemplos específicos
        successful_examples = 0
        for example in substation_examples:
            try:
                self.vanna_service.vanna.train(
                    question=example["question"],
                    sql=example["sql"]
                )
                successful_examples += 1
                logger.debug(f"✅ Trained substation example: {example['question']}")
            except Exception as e:
                logger.warning(f"❌ Failed to train substation example '{example['question']}': {e}")
        
        logger.info(f"🏭 Substation training completed. {successful_examples}/{len(substation_examples)} examples trained successfully")
    
    async def _validate_training(self) -> bool:
        """Valida se o treinamento foi bem-sucedido."""
        try:
            # Teste simples de geração SQL
            test_question = "Quantos equipamentos temos?"
            response = await self.vanna_service.generate_sql(test_question)
            
            # Verificar se gerou SQL válido
            if response.sql and response.confidence > 0.3:
                logger.info(f"Training validation successful: confidence={response.confidence:.2f}")
                return True
            else:
                logger.warning(f"Training validation failed: sql={bool(response.sql)}, confidence={response.confidence}")
                return False
                
        except Exception as e:
            logger.error(f"Training validation error: {e}")
            return False
    
    async def force_retrain(self) -> bool:
        """Força um re-treinamento imediato."""
        logger.info("🔄 Forcing immediate Vanna re-training...")
        
        # Ignorar verificações de intervalo mínimo
        original_min_interval = self.min_interval_between_training_hours
        self.min_interval_between_training_hours = 0
        
        try:
            success = await self._execute_training()
            if success:
                self.last_training_time = datetime.now()
                # Recalcular checksum
                self.last_schema_checksum = await self._calculate_schema_checksum()
            return success
        finally:
            # Restaurar configuração original
            self.min_interval_between_training_hours = original_min_interval
    
    async def train_substations_only(self) -> bool:
        """
        Executa treinamento específico apenas para subestações.
        
        Útil quando há mudanças na estrutura de localização ou novos
        exemplos de consultas por subestação são identificados.
        
        Returns:
            bool: True se o treinamento foi bem-sucedido
        """
        if not self.vanna_service.is_initialized:
            logger.error("Vanna service not initialized, cannot train substations")
            return False
        
        logger.info("🏭 Starting substation-specific training...")
        
        try:
            await self._add_substation_training()
            
            # Validar com query específica de subestação
            test_success = await self._validate_substation_training()
            
            if test_success:
                logger.info("✅ Substation training completed successfully")
                return True
            else:
                logger.warning("⚠️ Substation training completed but validation failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error during substation training: {e}")
            return False
    
    async def _validate_substation_training(self) -> bool:
        """Valida especificamente o treinamento de subestações."""
        try:
            # Teste com pergunta específica de subestação
            test_question = "Quantos equipamentos estão ativos em UEM?"
            response = await self.vanna_service.generate_sql(test_question)
            
            # Verificar se gerou SQL com JOIN correto
            if (response.sql and 
                response.confidence > 0.5 and 
                "JOIN sap_locations" in response.sql and
                ("s.abbreviation = 'UEM'" in response.sql or "s.denomination" in response.sql)):
                
                logger.info(f"Substation training validation successful: confidence={response.confidence:.2f}")
                logger.debug(f"Generated SQL: {response.sql}")
                return True
            else:
                logger.warning(f"Substation training validation failed")
                logger.warning(f"SQL: {response.sql}")
                logger.warning(f"Confidence: {response.confidence}")
                return False
                
        except Exception as e:
            logger.error(f"Substation training validation error: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status atual do auto-trainer."""
        return {
            "training_enabled": self.settings.vanna_enable_training,
            "vanna_initialized": self.vanna_service.is_initialized,
            "training_in_progress": self.training_in_progress,
            "last_training_time": self.last_training_time.isoformat() if self.last_training_time else None,
            "last_schema_check": self.last_schema_checksum.timestamp.isoformat() if self.last_schema_checksum else None,
            "schema_checksum": self.last_schema_checksum.checksum if self.last_schema_checksum else None,
            "tables_monitored": self.last_schema_checksum.tables_count if self.last_schema_checksum else 0,
            "columns_monitored": self.last_schema_checksum.columns_count if self.last_schema_checksum else 0,
            "check_interval_minutes": self.check_interval_minutes,
            "force_retrain_hours": self.force_retrain_hours
        }

# Instância global do auto-trainer
_auto_trainer = None

def get_vanna_auto_trainer() -> VannaAutoTrainer:
    """Retorna instância singleton do VannaAutoTrainer."""
    global _auto_trainer
    if _auto_trainer is None:
        _auto_trainer = VannaAutoTrainer()
    return _auto_trainer

# Função para inicializar o monitoramento automático
async def start_vanna_auto_training():
    """Inicia o serviço de auto-treinamento."""
    auto_trainer = get_vanna_auto_trainer()
    await auto_trainer.start_monitoring() 