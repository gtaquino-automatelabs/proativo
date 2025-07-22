"""
Testes unitários para o PMM_2Processor.

Testa todas as funcionalidades do processador de dados PMM_2,
incluindo detecção de encoding, processamento de CSV, validação
e extração de códigos de equipamento.
"""

import pytest
import pandas as pd
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, mock_open
import tempfile
import os

from src.etl.processors.pmm_processor import PMM_2Processor
from src.etl.exceptions import DataProcessingError
from src.utils.validators import DataValidator


class TestPMM2Processor:
    """Testes para o PMM_2Processor."""
    
    def setup_method(self):
        """Configuração inicial para cada teste."""
        self.validator = Mock(spec=DataValidator)
        self.processor = PMM_2Processor(self.validator)
        
        # Dados de exemplo para testes
        self.sample_csv_content = """Plano manut.;CenTrab respon.;Texto item man.;Loc.instalação;Data planejada;Dta.início.progr.;Data encermto.;Última ordem;Ordem
TBDPDTCH001A;TTABDPM;Teste operativo (BDP) CH-301F7T;MT-S-70113-FE01-CH-301F7T;15/01/2028;11/03/2025;11/03/2025;2200264285;2200264285
TBDPDTCH002A;TTABDPM;Teste operativo (BDP) CH-302F8_8T;MT-S-70113-FE01-CH-302F8_8T;12/01/2025;13/01/2025;15/02/2022;2200264286;2200188699"""
        
        self.expected_processed_data = [
            {
                'maintenance_plan_code': 'TBDPDTCH001A',
                'work_center': 'TTABDPM',
                'maintenance_item_text': 'Teste operativo (BDP) CH-301F7T',
                'installation_location': 'MT-S-70113-FE01-CH-301F7T',
                'equipment_code': 'CH-301F7T',
                'planned_date': datetime(2028, 1, 15),
                'scheduled_start_date': datetime(2025, 3, 11),
                'completion_date': datetime(2025, 3, 11),
                'last_order': '2200264285',
                'current_order': '2200264285'
            }
        ]
    
    def test_init(self):
        """Testa inicialização do processador."""
        processor = PMM_2Processor()
        assert processor.validator is not None
        assert processor.supported_encodings == ['latin-1', 'cp1252', 'utf-8', 'iso-8859-1']
        assert 'plano manut.' in processor.column_mapping
        assert 'centrab respon.' in processor.column_mapping
    
    def test_detect_encoding_success(self):
        """Testa detecção de encoding bem-sucedida."""
        mock_content = "Plano manut.;CenTrab respon.;Texto item man.;Loc.instalação"
        
        with patch('builtins.open', mock_open(read_data=mock_content)):
            with patch('pathlib.Path.exists', return_value=True):
                file_path = Path("test_pmm2.csv")
                encoding = self.processor.detect_encoding(file_path)
                assert encoding in self.processor.supported_encodings
    
    def test_detect_encoding_no_keywords(self):
        """Testa detecção de encoding quando não encontra palavras-chave."""
        mock_content = "column1;column2;column3"
        
        with patch('builtins.open', mock_open(read_data=mock_content)):
            with patch('pathlib.Path.exists', return_value=True):
                file_path = Path("test_pmm2.csv")
                encoding = self.processor.detect_encoding(file_path)
                assert encoding == 'latin-1'  # Default
    
    def test_detect_delimiter_semicolon(self):
        """Testa detecção de delimitador ponto e vírgula."""
        mock_content = "Plano manut.;CenTrab respon.;Texto item man."
        
        with patch('builtins.open', mock_open(read_data=mock_content)):
            file_path = Path("test_pmm2.csv")
            delimiter = self.processor.detect_delimiter(file_path, 'latin-1')
            assert delimiter == ';'
    
    def test_detect_delimiter_comma(self):
        """Testa detecção de delimitador vírgula."""
        mock_content = "Plano manut.,CenTrab respon.,Texto item man."
        
        with patch('builtins.open', mock_open(read_data=mock_content)):
            file_path = Path("test_pmm2.csv")
            delimiter = self.processor.detect_delimiter(file_path, 'latin-1')
            assert delimiter == ','
    
    def test_detect_delimiter_error(self):
        """Testa detecção de delimitador com erro."""
        with patch('builtins.open', side_effect=IOError("File not found")):
            file_path = Path("test_pmm2.csv")
            delimiter = self.processor.detect_delimiter(file_path, 'latin-1')
            assert delimiter == ';'  # Default
    
    def test_standardize_column_names(self):
        """Testa padronização de nomes de colunas."""
        # Cria DataFrame com colunas do PMM_2
        df = pd.DataFrame({
            'Plano manut.': ['TBDPDTCH001A'],
            'CenTrab respon.': ['TTABDPM'],
            'Texto item man.': ['Teste operativo'],
            'Loc.instalação': ['MT-S-70113-FE01-CH-301F7T'],
            'Data planejada': ['15/01/2028'],
            'Dta.início.progr.': ['11/03/2025'],
            'Data encermto.': ['11/03/2025'],
            'Última ordem': ['2200264285'],
            'Ordem': ['2200264285']
        })
        
        result = self.processor.standardize_column_names(df)
        
        # Verifica se as colunas foram padronizadas corretamente
        expected_columns = [
            'maintenance_plan_code', 'work_center', 'maintenance_item_text',
            'installation_location', 'planned_date', 'scheduled_start_date',
            'completion_date', 'last_order', 'current_order'
        ]
        
        for col in expected_columns:
            assert col in result.columns
    
    def test_extract_equipment_code_success(self):
        """Testa extração de código de equipamento bem-sucedida."""
        test_cases = [
            ('MT-S-70113-FE01-CH-301F7T', 'CH-301F7T'),
            ('MT-S-70113-FE01-DJ-3U4', 'DJ-3U4'),
            ('MT-S-70113-INCA-GM-1', 'GM-1'),
            ('MT-S-70113-FE01-TR-001', 'TR-001'),
            ('MT-S-70113-FE01-BC-C1_F', 'BC-C1_F'),
        ]
        
        for location, expected_code in test_cases:
            result = self.processor.extract_equipment_code(location)
            assert result == expected_code
    
    def test_extract_equipment_code_fallback(self):
        """Testa extração de código de equipamento com fallback."""
        # Caso sem padrão específico
        location = 'MT-S-70113-FE01-UNKNOWN-DEVICE'
        result = self.processor.extract_equipment_code(location)
        assert result == 'UNKNOWN-DEVICE'
    
    def test_extract_equipment_code_none(self):
        """Testa extração de código de equipamento com valor None."""
        assert self.processor.extract_equipment_code(None) is None
        assert self.processor.extract_equipment_code('') is None
        assert self.processor.extract_equipment_code(pd.NA) is None
    
    def test_convert_sap_date_success(self):
        """Testa conversão de datas SAP bem-sucedida."""
        test_cases = [
            ('15/01/2025', datetime(2025, 1, 15)),
            ('15.01.2025', datetime(2025, 1, 15)),
            ('2025-01-15', datetime(2025, 1, 15)),
            ('15-01-2025', datetime(2025, 1, 15)),
            ('15/01/25', datetime(2025, 1, 15)),
            ('15.01.25', datetime(2025, 1, 15)),
        ]
        
        for date_str, expected_date in test_cases:
            result = self.processor.convert_sap_date(date_str)
            assert result == expected_date
    
    def test_convert_sap_date_none(self):
        """Testa conversão de datas SAP com valores None."""
        assert self.processor.convert_sap_date(None) is None
        assert self.processor.convert_sap_date('') is None
        assert self.processor.convert_sap_date(pd.NA) is None
        assert self.processor.convert_sap_date('   ') is None
    
    def test_convert_sap_date_invalid(self):
        """Testa conversão de datas SAP inválidas."""
        with patch('src.etl.processors.pmm_processor.logger') as mock_logger:
            result = self.processor.convert_sap_date('data_invalida')
            assert result is None
            mock_logger.warning.assert_called()
    
    def test_clean_pmm_2_data(self):
        """Testa limpeza de dados PMM_2."""
        # Cria DataFrame com dados problemáticos
        df = pd.DataFrame({
            'maintenance_plan_code': ['TBDPDTCH001A', '', 'TBDPDTCH002A', None],
            'work_center': ['TTABDPM', 'TTABDPM', '', 'TTABDPM'],
            'maintenance_item_text': ['Teste 1', 'Teste 2', 'Teste 3', ''],
            'installation_location': ['LOC1', 'LOC2', 'LOC3', 'LOC4']
        })
        
        result = self.processor.clean_pmm_2_data(df)
        
        # Verifica se removeu linhas inválidas
        assert len(result) == 1  # Apenas a primeira linha deve permanecer
        assert result.iloc[0]['maintenance_plan_code'] == 'TBDPDTCH001A'
    
    def test_clean_pmm_2_data_duplicates(self):
        """Testa remoção de duplicatas."""
        df = pd.DataFrame({
            'maintenance_plan_code': ['TBDPDTCH001A', 'TBDPDTCH001A', 'TBDPDTCH002A'],
            'work_center': ['TTABDPM', 'TTABDPM', 'TTABDPM'],
            'maintenance_item_text': ['Teste 1', 'Teste 1', 'Teste 2'],
            'installation_location': ['LOC1', 'LOC1', 'LOC2']
        })
        
        result = self.processor.clean_pmm_2_data(df)
        
        # Verifica se removeu duplicatas
        assert len(result) == 2
        assert result.iloc[0]['maintenance_plan_code'] == 'TBDPDTCH001A'
        assert result.iloc[1]['maintenance_plan_code'] == 'TBDPDTCH002A'
    
    def test_validate_pmm_2_record_valid(self):
        """Testa validação de registro PMM_2 válido."""
        record = {
            'maintenance_plan_code': 'TBDPDTCH001A',
            'work_center': 'TTABDPM',
            'maintenance_item_text': 'Teste operativo',
            'installation_location': 'MT-S-70113-FE01-CH-301F7T',
            'planned_date': datetime(2025, 1, 15)
        }
        
        is_valid, errors = self.processor.validate_pmm_2_record(record)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_pmm_2_record_invalid(self):
        """Testa validação de registro PMM_2 inválido."""
        record = {
            'maintenance_plan_code': '',  # Campo obrigatório vazio
            'work_center': 'A' * 25,  # Muito longo
            'maintenance_item_text': 'A' * 600,  # Muito longo
            'installation_location': '',  # Campo obrigatório vazio
            'planned_date': 'data_invalida'  # Data inválida
        }
        
        is_valid, errors = self.processor.validate_pmm_2_record(record)
        
        assert is_valid is False
        assert len(errors) > 0
        assert any('Campo obrigatório ausente' in error for error in errors)
        assert any('Centro de trabalho inválido' in error for error in errors)
        assert any('Texto de item muito longo' in error for error in errors)
        assert any('Data inválida' in error for error in errors)
    
    def test_get_processing_summary_empty(self):
        """Testa geração de resumo com lista vazia."""
        summary = self.processor.get_processing_summary([])
        
        assert summary['total_records'] == 0
        assert summary['work_centers'] == []
        assert summary['equipment_codes'] == []
        assert summary['date_range'] is None
    
    def test_get_processing_summary_with_data(self):
        """Testa geração de resumo com dados."""
        records = [
            {
                'maintenance_plan_code': 'TBDPDTCH001A',
                'work_center': 'TTABDPM',
                'equipment_code': 'CH-301F7T',
                'planned_date': datetime(2025, 1, 15)
            },
            {
                'maintenance_plan_code': 'TBDPDTCH002A',
                'work_center': 'TTABDPM',
                'equipment_code': 'CH-302F8_8T',
                'planned_date': datetime(2025, 2, 10)
            }
        ]
        
        summary = self.processor.get_processing_summary(records)
        
        assert summary['total_records'] == 2
        assert 'TTABDPM' in summary['work_centers']
        assert 'CH-301F7T' in summary['equipment_codes']
        assert 'CH-302F8_8T' in summary['equipment_codes']
        assert summary['unique_work_centers'] == 1
        assert summary['unique_equipment_codes'] == 2
        assert summary['date_range'] is not None
    
    def test_read_pmm_2_csv_success(self):
        """Testa leitura de CSV PMM_2 bem-sucedida."""
        # Cria arquivo temporário
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='latin-1') as f:
            f.write(self.sample_csv_content)
            temp_path = f.name
        
        try:
            # Mock dos métodos de detecção
            with patch.object(self.processor, 'detect_encoding', return_value='latin-1'):
                with patch.object(self.processor, 'detect_delimiter', return_value=';'):
                    result = self.processor.read_pmm_2_csv(Path(temp_path))
                    
                    assert isinstance(result, pd.DataFrame)
                    assert len(result) == 2
                    assert 'Plano manut.' in result.columns
                    assert 'CenTrab respon.' in result.columns
        finally:
            os.unlink(temp_path)
    
    def test_read_pmm_2_csv_error(self):
        """Testa leitura de CSV PMM_2 com erro."""
        with patch.object(self.processor, 'detect_encoding', side_effect=Exception("Encoding error")):
            with pytest.raises(DataProcessingError):
                self.processor.read_pmm_2_csv(Path("nonexistent.csv"))
    
    def test_process_pmm_2_csv_integration(self):
        """Teste de integração do processamento completo."""
        # Cria arquivo temporário
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='latin-1') as f:
            f.write(self.sample_csv_content)
            temp_path = f.name
        
        try:
            # Mock dos métodos de detecção
            with patch.object(self.processor, 'detect_encoding', return_value='latin-1'):
                with patch.object(self.processor, 'detect_delimiter', return_value=';'):
                    result = self.processor.process_pmm_2_csv(Path(temp_path))
                    
                    assert isinstance(result, list)
                    assert len(result) == 2
                    
                    # Verifica primeiro registro
                    first_record = result[0]
                    assert first_record['maintenance_plan_code'] == 'TBDPDTCH001A'
                    assert first_record['work_center'] == 'TTABDPM'
                    assert first_record['equipment_code'] == 'CH-301F7T'
                    assert first_record['data_source'] == 'SAP'
                    assert first_record['status'] == 'Active'
                    assert 'metadata_json' in first_record
                    
                    # Verifica metadados
                    metadata = first_record['metadata_json']
                    assert 'source_file' in metadata
                    assert 'processed_at' in metadata
                    assert 'original_location' in metadata
                    assert 'extracted_equipment_code' in metadata
                    
        finally:
            os.unlink(temp_path)
    
    def test_process_pmm_2_csv_error(self):
        """Testa processamento de CSV PMM_2 com erro."""
        with patch.object(self.processor, 'read_pmm_2_csv', side_effect=Exception("Read error")):
            with pytest.raises(DataProcessingError):
                self.processor.process_pmm_2_csv(Path("test.csv"))
    
    def test_column_mapping_completeness(self):
        """Testa se o mapeamento de colunas está completo."""
        # Verifica se todas as colunas do PMM_2 estão mapeadas
        expected_mappings = {
            'plano manut.': 'maintenance_plan_code',
            'centrab respon.': 'work_center',
            'texto item man.': 'maintenance_item_text',
            'loc.instalação': 'installation_location',
            'data planejada': 'planned_date',
            'dta.início.progr.': 'scheduled_start_date',
            'data encermto.': 'completion_date',
            'última ordem': 'last_order',
            'ordem': 'current_order'
        }
        
        for original, expected in expected_mappings.items():
            assert original in self.processor.column_mapping
            assert self.processor.column_mapping[original] == expected
    
    def test_encoding_priority(self):
        """Testa prioridade de encodings."""
        # Verifica se latin-1 e cp1252 estão no início da lista
        assert self.processor.supported_encodings[0] == 'latin-1'
        assert self.processor.supported_encodings[1] == 'cp1252'
    
    def test_equipment_code_patterns(self):
        """Testa padrões de código de equipamento."""
        test_cases = [
            ('MT-S-70113-FE01-CH-301F7T', 'CH-301F7T'),
            ('MT-S-70113-FE01-DJ-3U4', 'DJ-3U4'),
            ('MT-S-70113-INCA-GM-1', 'GM-1'),
            ('MT-S-70113-FE01-TR-001A', 'TR-001A'),
            ('MT-S-70113-FE01-BC-C1_F', 'BC-C1_F'),
            ('MT-S-70113-FE01-FH-FH3_F', 'FH-FH3_F'),
            ('MT-S-70113-FE01-BB-3', 'BB-3'),
            ('MT-S-70113-FE01-TC-4U4_VM', 'TC-4U4_VM'),
            ('MT-S-70113-FE01-PR-T8_F_BR', 'PR-T8_F_BR'),
        ]
        
        for location, expected_code in test_cases:
            result = self.processor.extract_equipment_code(location)
            assert result == expected_code, f"Failed for {location}, got {result}, expected {expected_code}" 