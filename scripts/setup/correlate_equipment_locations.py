#!/usr/bin/env python3
"""
Script para correlacionar equipamentos existentes com localidades SAP.
Analisa equipamentos e tenta fazer match com localidades por padrões de código.
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import re

# Configurar paths
current_dir = Path(__file__).parent
project_dir = current_dir.parent.parent
sys.path.insert(0, str(project_dir))
os.environ['PYTHONPATH'] = str(project_dir)

from src.database.repositories import RepositoryManager
from src.database.connection import db_connection, init_database
from src.utils.logger import get_logger

# Configurar logging
logger = get_logger(__name__)


class EquipmentLocationCorrelator:
    """Correlaciona equipamentos com localidades SAP."""
    
    def __init__(self, repo_manager: RepositoryManager):
        """Inicializa o correlacionador.
        
        Args:
            repo_manager: Instância do gerenciador de repositories
        """
        self.repo_manager = repo_manager
        self.location_patterns = [
            # Padrões de código de localização
            r'MT-S-\d+',  # MT-S-72183
            r'MT-S-\d+-\w+',  # MT-S-70113-FE01
            r'MT-\w-\d+',  # MT-S-72183 (formato genérico)
        ]
    
    def extract_location_code_from_text(self, text: str) -> Optional[str]:
        """Extrai código de localização de um texto.
        
        Args:
            text: Texto para análise
            
        Returns:
            Código de localização encontrado ou None
        """
        if not text:
            return None
        
        text = text.upper()
        
        for pattern in self.location_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        
        return None
    
    def extract_base_location_code(self, location_code: str) -> str:
        """Extrai código base da localização (sem sufixos).
        
        Args:
            location_code: Código completo da localização
            
        Returns:
            Código base da localização
        """
        # Remover sufixos comuns como -FE01, -CH-301F7T, etc.
        base_code = location_code.split('-')[0:3]  # MT-S-72183
        return '-'.join(base_code)
    
    async def find_matching_location(self, equipment_text: str) -> Optional[str]:
        """Encontra localidade correspondente baseada no texto do equipamento.
        
        Args:
            equipment_text: Texto do equipamento (location, description, etc.)
            
        Returns:
            ID da localidade correspondente ou None
        """
        # Extrair código de localização do texto
        location_code = self.extract_location_code_from_text(equipment_text)
        
        if not location_code:
            return None
        
        # Buscar localidade exata
        exact_location = await self.repo_manager.sap_location.get_by_code(location_code)
        if exact_location:
            return exact_location.id
        
        # Buscar por código base
        base_code = self.extract_base_location_code(location_code)
        if base_code != location_code:
            base_location = await self.repo_manager.sap_location.get_by_code(base_code)
            if base_location:
                return base_location.id
        
        # Buscar por padrão parcial
        matching_locations = await self.repo_manager.sap_location.find_matching_locations(base_code)
        if matching_locations:
            # Retornar o primeiro match por enquanto
            return matching_locations[0].id
        
        return None
    
    async def correlate_equipment(self, equipment_id: str, location_id: str) -> bool:
        """Correlaciona um equipamento com uma localidade.
        
        Args:
            equipment_id: ID do equipamento
            location_id: ID da localidade
            
        Returns:
            True se correlacionado com sucesso
        """
        try:
            # Atualizar equipamento com localidade
            equipment = await self.repo_manager.equipment.get_by_id(equipment_id)
            if not equipment:
                return False
            
            # Usar método do repository para correlacionar
            success = await self.repo_manager.sap_location.correlate_with_equipment(
                location_id, equipment_id
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Erro ao correlacionar equipamento {equipment_id} com localidade {location_id}: {str(e)}")
            return False
    
    async def correlate_all_equipments(self) -> Dict[str, Any]:
        """Correlaciona todos os equipamentos com localidades.
        
        Returns:
            Estatísticas da correlação
        """
        print("🔗 Iniciando correlação de equipamentos com localidades...")
        
        # Buscar todos os equipamentos
        equipments = await self.repo_manager.equipment.list_all()
        total_equipments = len(equipments)
        
        # Estatísticas
        correlated_count = 0
        already_correlated = 0
        not_found_count = 0
        error_count = 0
        correlations = []
        
        print(f"   📊 Total de equipamentos: {total_equipments}")
        
        for i, equipment in enumerate(equipments, 1):
            try:
                # Verificar se já tem localidade
                if equipment.sap_location_id:
                    already_correlated += 1
                    continue
                
                # Tentar encontrar localidade correspondente
                location_id = None
                
                # Buscar em diferentes campos
                search_fields = [
                    equipment.location,
                    equipment.description,
                    equipment.name,
                    equipment.code
                ]
                
                for field in search_fields:
                    if field:
                        location_id = await self.find_matching_location(field)
                        if location_id:
                            break
                
                if location_id:
                    # Correlacionar
                    success = await self.correlate_equipment(equipment.id, location_id)
                    if success:
                        correlated_count += 1
                        
                        # Buscar informações da localidade para o relatório
                        location = await self.repo_manager.sap_location.get_by_id(location_id)
                        correlations.append({
                            'equipment_code': equipment.code,
                            'equipment_name': equipment.name,
                            'location_code': location.location_code if location else 'Unknown',
                            'location_name': location.denomination if location else 'Unknown'
                        })
                        
                        if i % 10 == 0:  # Progress update
                            print(f"   🔄 Processado: {i}/{total_equipments} equipamentos")
                    else:
                        error_count += 1
                else:
                    not_found_count += 1
                    
            except Exception as e:
                logger.error(f"Erro ao processar equipamento {equipment.code}: {str(e)}")
                error_count += 1
        
        # Estatísticas finais
        stats = {
            'total_equipments': total_equipments,
            'correlated_count': correlated_count,
            'already_correlated': already_correlated,
            'not_found_count': not_found_count,
            'error_count': error_count,
            'correlations': correlations,
            'correlation_rate': (correlated_count / total_equipments * 100) if total_equipments > 0 else 0
        }
        
        return stats


async def generate_correlation_report(stats: Dict[str, Any]) -> None:
    """Gera relatório de correlação.
    
    Args:
        stats: Estatísticas da correlação
    """
    print("\n📋 Relatório de Correlação:")
    print(f"   📊 Total de equipamentos: {stats['total_equipments']}")
    print(f"   ✅ Correlacionados agora: {stats['correlated_count']}")
    print(f"   🔄 Já correlacionados: {stats['already_correlated']}")
    print(f"   ❌ Não encontrados: {stats['not_found_count']}")
    print(f"   💥 Erros: {stats['error_count']}")
    print(f"   📈 Taxa de correlação: {stats['correlation_rate']:.1f}%")
    
    if stats['correlations']:
        print(f"\n   🎯 Exemplos de correlações realizadas:")
        for correlation in stats['correlations'][:10]:  # Mostrar 10 primeiras
            print(f"      • {correlation['equipment_code']} → {correlation['location_code']} ({correlation['location_name']})")


async def validate_correlations() -> None:
    """Valida as correlações realizadas."""
    print("\n✅ Validando correlações...")
    
    async with db_connection.get_session() as session:
        repo_manager = RepositoryManager(session)
        
        # Estatísticas de localidades
        location_stats = await repo_manager.sap_location.get_stats()
        
        print(f"   📊 Localidades com equipamentos: {location_stats.get('linked_locations', 0)}")
        print(f"   📈 Taxa de vinculação: {location_stats.get('linking_rate', 0):.1f}%")


async def main():
    """Função principal do script."""
    print("🚀 Iniciando correlação de equipamentos com localidades SAP...\n")
    
    try:
        # Inicializar banco de dados
        await init_database()
        
        # Criar sessão e correlacionador
        async with db_connection.get_session() as session:
            repo_manager = RepositoryManager(session)
            correlator = EquipmentLocationCorrelator(repo_manager)
            
            # Executar correlação
            stats = await correlator.correlate_all_equipments()
            
            # Gerar relatório
            await generate_correlation_report(stats)
            
            # Validar correlações
            await validate_correlations()
            
            print(f"\n🎉 Correlação concluída com sucesso!")
            print(f"   ✅ {stats['correlated_count']} equipamentos correlacionados")
            print(f"   📈 Taxa final de correlação: {stats['correlation_rate']:.1f}%")
            
    except Exception as e:
        logger.error(f"Erro na execução do script: {str(e)}")
        print(f"❌ Erro: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 