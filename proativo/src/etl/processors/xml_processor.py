"""
Processador para arquivos XML.

Responsável por ler, validar e transformar dados de equipamentos e manutenções
a partir de arquivos XML, preparando-os para inserção no banco de dados.
"""

import logging
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from pathlib import Path
import re

from etl.exceptions import DataProcessingError, ValidationError, FileFormatError

logger = logging.getLogger(__name__)


class XMLProcessor:
    """Processador para arquivos XML com suporte a múltiplos esquemas."""
    
    def __init__(self):
        """Inicializa o processador XML."""
        self.supported_namespaces = {
            'equipment': ['equip', 'equipment', 'eq'],
            'maintenance': ['maint', 'maintenance', 'mntn'],
            'data': ['data', 'hist', 'history']
        }
        
    def parse_xml(self, file_path: Path) -> ET.Element:
        """Faz parse do arquivo XML.
        
        Args:
            file_path: Caminho para o arquivo XML
            
        Returns:
            Elemento raiz do XML
            
        Raises:
            FileFormatError: Se o arquivo não for um XML válido
        """
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            logger.debug(f"XML parseado com sucesso. Raiz: {root.tag}")
            return root
        except ET.ParseError as e:
            raise FileFormatError(f"Arquivo XML inválido {file_path}: {str(e)}")
        except Exception as e:
            raise DataProcessingError(f"Erro ao ler arquivo XML {file_path}: {str(e)}")
    
    def normalize_tag_name(self, tag: str) -> str:
        """Normaliza nome de tag XML removendo namespace.
        
        Args:
            tag: Nome da tag XML
            
        Returns:
            Nome da tag normalizado
        """
        # Remove namespace
        if '}' in tag:
            tag = tag.split('}')[1]
        
        # Converte para lowercase e substitui hífens por underscores
        tag = tag.lower().replace('-', '_')
        
        return tag
    
    def xml_element_to_dict(self, element: ET.Element) -> Dict[str, Any]:
        """Converte elemento XML para dicionário.
        
        Args:
            element: Elemento XML
            
        Returns:
            Dicionário com dados do elemento
        """
        result = {}
        
        # Adiciona atributos
        for attr_name, attr_value in element.attrib.items():
            normalized_name = self.normalize_tag_name(attr_name)
            result[normalized_name] = attr_value
        
        # Processa elementos filhos
        for child in element:
            child_tag = self.normalize_tag_name(child.tag)
            
            # Se o elemento tem filhos, processa recursivamente
            if len(child) > 0:
                child_dict = self.xml_element_to_dict(child)
                if child_tag in result:
                    # Se já existe, converte para lista
                    if not isinstance(result[child_tag], list):
                        result[child_tag] = [result[child_tag]]
                    result[child_tag].append(child_dict)
                else:
                    result[child_tag] = child_dict
            else:
                # Elemento folha, pega o texto
                text_value = child.text.strip() if child.text else ''
                if child_tag in result:
                    # Se já existe, converte para lista
                    if not isinstance(result[child_tag], list):
                        result[child_tag] = [result[child_tag]]
                    result[child_tag].append(text_value)
                else:
                    result[child_tag] = text_value
        
        # Se não tem filhos, adiciona o texto do elemento
        if len(element) == 0 and element.text:
            text_value = element.text.strip()
            if text_value:
                result['text_content'] = text_value
        
        return result
    
    def standardize_equipment_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Padroniza campos de equipamento.
        
        Args:
            data: Dados do equipamento
            
        Returns:
            Dados padronizados
        """
        field_mapping = {
            'equipment_id': 'code',
            'equipment_code': 'code',
            'equipamento': 'code',
            'codigo': 'code',
            'equipment_name': 'name',
            'nome': 'name',
            'nome_equipamento': 'name',
            'description': 'description',
            'descricao': 'description',
            'type': 'equipment_type',
            'tipo': 'equipment_type',
            'equipment_type': 'equipment_type',
            'criticality': 'criticality',
            'criticidade': 'criticality',
            'location': 'location',
            'localizacao': 'location',
            'substation': 'substation',
            'subestacao': 'substation',
            'manufacturer': 'manufacturer',
            'fabricante': 'manufacturer',
            'model': 'model',
            'modelo': 'model',
            'serial_number': 'serial_number',
            'numero_serie': 'serial_number',
            'manufacturing_year': 'manufacturing_year',
            'ano_fabricacao': 'manufacturing_year',
            'installation_date': 'installation_date',
            'data_instalacao': 'installation_date',
            'rated_voltage': 'rated_voltage',
            'tensao_nominal': 'rated_voltage',
            'rated_power': 'rated_power',
            'potencia_nominal': 'rated_power',
            'rated_current': 'rated_current',
            'corrente_nominal': 'rated_current',
            'status': 'status'
        }
        
        standardized = {}
        for key, value in data.items():
            normalized_key = field_mapping.get(key, key)
            standardized[normalized_key] = value
        
        return standardized
    
    def standardize_maintenance_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Padroniza campos de manutenção.
        
        Args:
            data: Dados da manutenção
            
        Returns:
            Dados padronizados
        """
        field_mapping = {
            'maintenance_id': 'maintenance_code',
            'codigo_manutencao': 'maintenance_code',
            'type': 'maintenance_type',
            'tipo_manutencao': 'maintenance_type',
            'priority': 'priority',
            'prioridade': 'priority',
            'title': 'title',
            'titulo': 'title',
            'description': 'description',
            'descricao': 'description',
            'work_performed': 'work_performed',
            'trabalho_realizado': 'work_performed',
            'scheduled_date': 'scheduled_date',
            'data_programada': 'scheduled_date',
            'start_date': 'start_date',
            'data_inicio': 'start_date',
            'completion_date': 'completion_date',
            'data_conclusao': 'completion_date',
            'duration_hours': 'duration_hours',
            'duracao_horas': 'duration_hours',
            'result': 'result',
            'resultado': 'result',
            'technician': 'technician',
            'tecnico': 'technician',
            'team': 'team',
            'equipe': 'team',
            'contractor': 'contractor',
            'contratada': 'contractor',
            'estimated_cost': 'estimated_cost',
            'custo_estimado': 'estimated_cost',
            'actual_cost': 'actual_cost',
            'custo_real': 'actual_cost',
            'observations': 'observations',
            'observacoes': 'observations'
        }
        
        standardized = {}
        for key, value in data.items():
            normalized_key = field_mapping.get(key, key)
            standardized[normalized_key] = value
        
        return standardized
    
    def convert_data_types(self, data: Dict[str, Any], data_type: str) -> Dict[str, Any]:
        """Converte tipos de dados.
        
        Args:
            data: Dados para conversão
            data_type: Tipo de entidade ('equipment', 'maintenance')
            
        Returns:
            Dados com tipos convertidos
        """
        converted = data.copy()
        
        # Conversões de data
        date_fields = {
            'equipment': ['installation_date'],
            'maintenance': ['scheduled_date', 'start_date', 'completion_date']
        }
        
        if data_type in date_fields:
            for field in date_fields[data_type]:
                if field in converted and converted[field]:
                    try:
                        # Tenta diversos formatos de data
                        date_formats = [
                            '%Y-%m-%d',
                            '%d/%m/%Y',
                            '%Y-%m-%d %H:%M:%S',
                            '%d/%m/%Y %H:%M:%S',
                            '%Y-%m-%dT%H:%M:%S'
                        ]
                        
                        date_str = str(converted[field]).strip()
                        for fmt in date_formats:
                            try:
                                converted[field] = datetime.strptime(date_str, fmt)
                                break
                            except ValueError:
                                continue
                        else:
                            logger.warning(f"Não foi possível converter data {field}: {date_str}")
                            converted[field] = None
                    except Exception as e:
                        logger.warning(f"Erro ao converter data {field}: {e}")
                        converted[field] = None
        
        # Conversões numéricas
        numeric_fields = {
            'equipment': ['manufacturing_year', 'rated_voltage', 'rated_power', 'rated_current'],
            'maintenance': ['duration_hours', 'estimated_cost', 'actual_cost']
        }
        
        if data_type in numeric_fields:
            for field in numeric_fields[data_type]:
                if field in converted and converted[field]:
                    try:
                        # Remove formatação e converte
                        value_str = str(converted[field]).replace(',', '.').strip()
                        # Remove símbolos de moeda
                        value_str = re.sub(r'[R$\s]', '', value_str)
                        converted[field] = float(value_str)
                    except (ValueError, TypeError):
                        logger.warning(f"Não foi possível converter número {field}: {converted[field]}")
                        converted[field] = None
        
        return converted
    
    def process_equipment_xml(self, file_path: Path) -> List[Dict[str, Any]]:
        """Processa arquivo XML de equipamentos.
        
        Args:
            file_path: Caminho para o arquivo
            
        Returns:
            Lista de dicionários com dados de equipamentos
        """
        logger.info(f"Processando XML de equipamentos: {file_path}")
        
        try:
            root = self.parse_xml(file_path)
            equipment_records = []
            
            # Procura por elementos de equipamento
            equipment_elements = []
            
            # Tenta diferentes caminhos no XML
            possible_paths = [
                './/equipment',
                './/equipamento',
                './/item',
                './/record',
                './equipment',
                './equipamento'
            ]
            
            for path in possible_paths:
                elements = root.findall(path)
                if elements:
                    equipment_elements = elements
                    break
            
            # Se não encontrou elementos específicos, usa elementos filhos diretos
            if not equipment_elements:
                equipment_elements = list(root)
            
            for element in equipment_elements:
                # Converte elemento para dicionário
                equipment_data = self.xml_element_to_dict(element)
                
                # Padroniza campos
                equipment_data = self.standardize_equipment_fields(equipment_data)
                
                # Converte tipos de dados
                equipment_data = self.convert_data_types(equipment_data, 'equipment')
                
                # Adiciona metadados
                equipment_data['metadata_json'] = {
                    'source_file': file_path.name,
                    'source_format': 'XML',
                    'processed_at': datetime.now().isoformat()
                }
                
                equipment_records.append(equipment_data)
            
            logger.info(f"Processados {len(equipment_records)} equipamentos do XML")
            return equipment_records
            
        except Exception as e:
            raise DataProcessingError(f"Erro ao processar XML de equipamentos {file_path}: {str(e)}")
    
    def process_maintenance_xml(self, file_path: Path) -> List[Dict[str, Any]]:
        """Processa arquivo XML de manutenções.
        
        Args:
            file_path: Caminho para o arquivo
            
        Returns:
            Lista de dicionários com dados de manutenções
        """
        logger.info(f"Processando XML de manutenções: {file_path}")
        
        try:
            root = self.parse_xml(file_path)
            maintenance_records = []
            
            # Procura por elementos de manutenção
            maintenance_elements = []
            
            # Tenta diferentes caminhos no XML
            possible_paths = [
                './/maintenance',
                './/manutencao',
                './/manutenção',
                './/item',
                './/record',
                './maintenance',
                './manutencao'
            ]
            
            for path in possible_paths:
                elements = root.findall(path)
                if elements:
                    maintenance_elements = elements
                    break
            
            # Se não encontrou elementos específicos, usa elementos filhos diretos
            if not maintenance_elements:
                maintenance_elements = list(root)
            
            for element in maintenance_elements:
                # Converte elemento para dicionário
                maintenance_data = self.xml_element_to_dict(element)
                
                # Padroniza campos
                maintenance_data = self.standardize_maintenance_fields(maintenance_data)
                
                # Converte tipos de dados
                maintenance_data = self.convert_data_types(maintenance_data, 'maintenance')
                
                # Adiciona metadados
                maintenance_data['metadata_json'] = {
                    'source_file': file_path.name,
                    'source_format': 'XML',
                    'processed_at': datetime.now().isoformat()
                }
                
                maintenance_records.append(maintenance_data)
            
            logger.info(f"Processadas {len(maintenance_records)} manutenções do XML")
            return maintenance_records
            
        except Exception as e:
            raise DataProcessingError(f"Erro ao processar XML de manutenções {file_path}: {str(e)}")
    
    def detect_xml_type(self, file_path: Path) -> str:
        """Detecta o tipo de dados no XML baseado na estrutura.
        
        Args:
            file_path: Caminho para o arquivo
            
        Returns:
            Tipo detectado ('equipment', 'maintenance', 'unknown')
        """
        try:
            root = self.parse_xml(file_path)
            
            # Analisa tags para determinar o tipo
            equipment_keywords = ['equipment', 'equipamento', 'equip', 'asset']
            maintenance_keywords = ['maintenance', 'manutencao', 'manutenção', 'maint']
            
            xml_text = ET.tostring(root, encoding='unicode').lower()
            
            equipment_score = sum(xml_text.count(keyword) for keyword in equipment_keywords)
            maintenance_score = sum(xml_text.count(keyword) for keyword in maintenance_keywords)
            
            if equipment_score > maintenance_score:
                return 'equipment'
            elif maintenance_score > equipment_score:
                return 'maintenance'
            else:
                return 'unknown'
                
        except Exception as e:
            logger.warning(f"Erro ao detectar tipo do XML {file_path}: {e}")
            return 'unknown' 