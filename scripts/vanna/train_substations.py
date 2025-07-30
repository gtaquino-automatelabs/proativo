#!/usr/bin/env python3
"""
Script para treinar especificamente o relacionamento de subestações no Vanna.ai.
Utiliza o VannaAutoTrainer para um treinamento gerenciado.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Adicionar src ao path para execução dentro do container
current_dir = Path(__file__).parent
src_path = current_dir.parent.parent / "src"
sys.path.insert(0, str(src_path))

try:
    from api.services.vanna_auto_trainer import VannaAutoTrainer
except ImportError:
    # Fallback para execução dentro do container Docker
    sys.path.insert(0, "/app/src")
    from api.services.vanna_auto_trainer import VannaAutoTrainer

async def main():
    """Executa o treinamento de subestações."""
    logger.info("🚀 Iniciando treinamento específico de subestações...")
    
    try:
        # Inicializar auto trainer
        trainer = VannaAutoTrainer()
        
        # Executar treinamento específico de subestações
        success = await trainer.train_substations_only()
        
        if success:
            logger.info("🎉 Treinamento de subestações concluído com sucesso!")
            
            # Mostrar status final
            status = trainer.get_status()
            logger.info(f"Status do trainer: {status}")
            
            return True
        else:
            logger.error("❌ Falha no treinamento de subestações")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro durante execução: {e}")
        import traceback
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return False

def test_training():
    """Testa o treinamento executando algumas queries."""
    logger.info("🧪 Testando queries após treinamento...")
    
    test_queries = [
        "Quantos equipamentos estão ativos em UEM?",
        "Quantos equipamentos temos na subestação Emborcação?",
        "Liste os transformadores em UJG",
    ]
    
    for query in test_queries:
        logger.info(f"Teste: {query}")
        # Aqui poderíamos testar as queries, mas para simplificar vamos apenas logar
    
    logger.info("✅ Testes de exemplo listados. Execute no sistema para validar.")

if __name__ == "__main__":
    try:
        # Executar treinamento
        success = asyncio.run(main())
        
        if success:
            # Executar testes exemplo
            test_training()
            
            logger.info("\n" + "="*60)
            logger.info("🎯 PRÓXIMOS PASSOS:")
            logger.info("1. Teste no frontend: 'Quantos equipamentos estão ativos em UEM?'")
            logger.info("2. Verifique se o SQL gerado inclui JOIN com sap_locations")
            logger.info("3. Confirme se usa s.abbreviation = 'UEM' para abreviações")
            logger.info("4. Confirme se usa s.denomination = 'Nome' para nomes completos")
            logger.info("="*60)
            
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("❌ Treinamento interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        sys.exit(1) 