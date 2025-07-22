"""
Testes de integração para o sistema PMM_2 completo.

Testa a integração entre o PMM_2Processor, DataProcessor, PMM_2Repository
e o processamento completo de arquivos PMM_2.
"""

import asyncio
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
import tempfile
import os

from src.etl.processors.pmm_processor import PMM_2Processor
from src.etl.data_processor import DataProcessor, DataType, FileFormat
from src.database.repositories import PMM_2Repository
from src.etl.exceptions import DataProcessingError


class TestPMM2Integration:
    """Testes de integração para o sistema PMM_2."""
    
    def setup_method(self):
        """Configuração inicial para cada teste."""
        self.sample_pmm_2_content = """Plano manut.;CenTrab respon.;Texto item man.;Loc.instalação;Data planejada;Dta.início.progr.;Data encermto.;Última ordem;Ordem
TBDPDTCH001A;TTABDPM;Teste operativo (BDP) CH-301F7T;MT-S-70113-FE01-CH-301F7T;15/01/2028;11/03/2025;11/03/2025;2200264285;2200264285
TBDPDTCH002A;TTABDPM;Teste operativo (BDP) CH-302F8_8T;MT-S-70113-FE01-CH-302F8_8T;12/01/2025;13/01/2025;15/02/2022;2200264286;2200188699
TBDPDTDJ001A;TTABDPM;Teste operativo (BDP) DJ-3U4;MT-S-70113-FE01-DJ-3U4;21/03/2025;11/03/2025;11/03/2025;2200253515;2200253515"""
    
    def test_pmm_2_processor_integration(self):
        """Testa integração completa do PMM_2Processor."""
        processor = PMM_2Processor()
        
        # Cria arquivo temporário
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='latin-1') as f:
            f.write(self.sample_pmm_2_content)
            temp_path = f.name
        
        try:
            # Processa o arquivo
            records = processor.process_pmm_2_csv(Path(temp_path))
            
            # Verifica resultados
            assert len(records) == 3
            
            # Verifica primeiro registro
            first_record = records[0]
            assert first_record['maintenance_plan_code'] == 'TBDPDTCH001A'
            assert first_record['work_center'] == 'TTABDPM'
            assert first_record['equipment_code'] == 'CH-301F7T'
            assert first_record['data_source'] == 'SAP'
            assert first_record['status'] == 'Active'
            
            # Verifica tipos de dados
            assert isinstance(first_record['planned_date'], datetime)
            assert isinstance(first_record['scheduled_start_date'], datetime)
            assert isinstance(first_record['completion_date'], datetime)
            
            # Verifica metadados
            assert 'metadata_json' in first_record
            metadata = first_record['metadata_json']
            assert 'source_file' in metadata
            assert 'processed_at' in metadata
            assert 'original_location' in metadata
            assert 'extracted_equipment_code' in metadata
            
        finally:
            os.unlink(temp_path)
    
    def test_data_processor_pmm_2_detection(self):
        """Testa detecção de arquivos PMM_2 no DataProcessor."""
        # Mock do repository manager
        mock_repo_manager = Mock()
        data_processor = DataProcessor(mock_repo_manager)
        
        # Testa detecção por nome de arquivo
        test_cases = [
            ('PMM_2.csv', DataType.PMM_2),
            ('pmm2_data.csv', DataType.PMM_2),
            ('plano_manut.csv', DataType.PMM_2),
            ('equipments.csv', DataType.EQUIPMENT),
            ('maintenance.csv', DataType.MAINTENANCE),
        ]
        
        for filename, expected_type in test_cases:
            file_path = Path(filename)
            detected_type = data_processor.detect_data_type(file_path, FileFormat.CSV)
            assert detected_type == expected_type
    
    def test_data_processor_pmm_2_processing(self):
        """Testa processamento de PMM_2 no DataProcessor."""
        # Mock do repository manager
        mock_repo_manager = Mock()
        data_processor = DataProcessor(mock_repo_manager)
        
        # Cria arquivo temporário
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='latin-1') as f:
            f.write(self.sample_pmm_2_content)
            temp_path = f.name
        
        try:
            # Mock do validador
            with patch.object(data_processor.validator, 'validate_batch') as mock_validate:
                mock_validate.return_value = ([], [])  # Sem registros válidos para este teste
                
                # Processa o arquivo
                records, errors = data_processor.process_file(
                    Path(temp_path),
                    data_type=DataType.PMM_2,
                    file_format=FileFormat.CSV
                )
                
                # Verifica que o processamento foi chamado
                assert mock_validate.called
                assert isinstance(records, list)
                assert isinstance(errors, list)
                
        finally:
            os.unlink(temp_path)
    
    async def test_pmm_2_repository_integration(self):
        """Testa integração com PMM_2Repository."""
        # Mock da sessão do banco
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result
        
        repo = PMM_2Repository(mock_session)
        
        # Testa upsert
        test_data = {
            'work_center': 'TTABDPM',
            'maintenance_item_text': 'Teste de integração',
            'installation_location': 'MT-S-70113-FE01-CH-001',
            'equipment_code': 'CH-001',
            'planned_date': datetime(2025, 1, 15),
            'status': 'Active'
        }
        
        # Mock do método create
        with patch.object(repo, 'create') as mock_create:
            mock_create.return_value = Mock(id='test-id')
            
            # Executa upsert
            result = await repo.upsert('TEST001A', **test_data)
            
            # Verifica que create foi chamado
            mock_create.assert_called_once()
            assert result.id == 'test-id'
    
    def test_pmm_2_data_flow_integration(self):
        """Testa fluxo completo de dados PMM_2."""
        # 1. Processamento de arquivo
        processor = PMM_2Processor()
        
        # Cria arquivo temporário
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='latin-1') as f:
            f.write(self.sample_pmm_2_content)
            temp_path = f.name
        
        try:
            # Processa arquivo
            records = processor.process_pmm_2_csv(Path(temp_path))
            assert len(records) == 3
            
            # 2. Validação de registros
            for record in records:
                is_valid, errors = processor.validate_pmm_2_record(record)
                assert is_valid, f"Record invalid: {errors}"
            
            # 3. Geração de resumo
            summary = processor.get_processing_summary(records)
            assert summary['total_records'] == 3
            assert summary['unique_work_centers'] == 1
            assert summary['unique_equipment_codes'] == 3
            assert 'TTABDPM' in summary['work_centers']
            assert 'CH-301F7T' in summary['equipment_codes']
            assert 'CH-302F8_8T' in summary['equipment_codes']
            assert 'DJ-3U4' in summary['equipment_codes']
            
        finally:
            os.unlink(temp_path)
    
    async def test_data_processor_save_pmm_2(self):
        """Testa salvamento de dados PMM_2 no DataProcessor."""
        # Mock do repository manager
        mock_repo_manager = Mock()
        mock_pmm_2_repo = AsyncMock()
        mock_repo_manager.pmm_2 = mock_pmm_2_repo
        
        data_processor = DataProcessor(mock_repo_manager)
        
        # Dados de teste
        test_records = [
            {
                'maintenance_plan_code': 'TBDPDTCH001A',
                'work_center': 'TTABDPM',
                'maintenance_item_text': 'Teste operativo',
                'installation_location': 'MT-S-70113-FE01-CH-301F7T',
                'equipment_code': 'CH-301F7T',
                'planned_date': datetime(2025, 1, 15),
                'status': 'Active',
                'metadata_json': {'source': 'test'}
            }
        ]
        
        # Mock do método upsert
        mock_pmm_2_repo.upsert.return_value = Mock()
        
        # Executa salvamento
        result = await data_processor.save_to_database(test_records, DataType.PMM_2)
        
        # Verifica que upsert foi chamado
        mock_pmm_2_repo.upsert.assert_called_once()
        assert result == 1  # Um registro processado
    
    def test_pmm_2_error_handling(self):
        """Testa tratamento de erros na integração PMM_2."""
        processor = PMM_2Processor()
        
        # Teste com arquivo inexistente
        with pytest.raises(DataProcessingError):
            processor.process_pmm_2_csv(Path('nonexistent.csv'))
        
        # Teste com dados inválidos
        invalid_record = {
            'maintenance_plan_code': '',  # Campo obrigatório vazio
            'work_center': '',  # Campo obrigatório vazio
        }
        
        is_valid, errors = processor.validate_pmm_2_record(invalid_record)
        assert not is_valid
        assert len(errors) > 0
    
    def test_pmm_2_encoding_integration(self):
        """Testa integração com diferentes encodings."""
        processor = PMM_2Processor()
        
        # Teste com encoding latin-1
        content_latin1 = """Plano manut.;CenTrab respon.;Texto item man.;Loc.instalação;Data planejada
TBDPDTCH001A;TTABDPM;Teste operativo (BDP) CH-301F7T;MT-S-70113-FE01-CH-301F7T;15/01/2028"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='latin-1') as f:
            f.write(content_latin1)
            temp_path = f.name
        
        try:
            # Verifica detecção de encoding
            detected_encoding = processor.detect_encoding(Path(temp_path))
            assert detected_encoding in ['latin-1', 'cp1252']
            
            # Verifica processamento
            records = processor.process_pmm_2_csv(Path(temp_path))
            assert len(records) == 1
            assert records[0]['maintenance_plan_code'] == 'TBDPDTCH001A'
            
        finally:
            os.unlink(temp_path)
    
    def test_pmm_2_equipment_code_extraction_integration(self):
        """Testa integração da extração de códigos de equipamento."""
        processor = PMM_2Processor()
        
        # Conteúdo com diferentes tipos de equipamento
        content = """Plano manut.;CenTrab respon.;Texto item man.;Loc.instalação;Data planejada
TBDPDTCH001A;TTABDPM;Teste CH;MT-S-70113-FE01-CH-301F7T;15/01/2028
TBDPDTDJ001A;TTABDPM;Teste DJ;MT-S-70113-FE01-DJ-3U4;16/01/2028
TBDPDTGM001A;TTABDPM;Teste GM;MT-S-70113-INCA-GM-1;17/01/2028"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='latin-1') as f:
            f.write(content)
            temp_path = f.name
        
        try:
            records = processor.process_pmm_2_csv(Path(temp_path))
            
            # Verifica códigos extraídos
            assert len(records) == 3
            assert records[0]['equipment_code'] == 'CH-301F7T'
            assert records[1]['equipment_code'] == 'DJ-3U4'
            assert records[2]['equipment_code'] == 'GM-1'
            
        finally:
            os.unlink(temp_path)
    
    def test_pmm_2_date_conversion_integration(self):
        """Testa integração da conversão de datas."""
        processor = PMM_2Processor()
        
        # Conteúdo com diferentes formatos de data
        content = """Plano manut.;CenTrab respon.;Texto item man.;Loc.instalação;Data planejada;Dta.início.progr.;Data encermto.
TBDPDTCH001A;TTABDPM;Teste 1;MT-S-70113-FE01-CH-301F7T;15/01/2028;11/03/2025;11/03/2025
TBDPDTCH002A;TTABDPM;Teste 2;MT-S-70113-FE01-CH-302F8_8T;12.01.2025;13.01.2025;15.02.2022"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='latin-1') as f:
            f.write(content)
            temp_path = f.name
        
        try:
            records = processor.process_pmm_2_csv(Path(temp_path))
            
            # Verifica conversão de datas
            assert len(records) == 2
            
            # Primeiro registro (formato dd/mm/yyyy)
            assert records[0]['planned_date'] == datetime(2028, 1, 15)
            assert records[0]['scheduled_start_date'] == datetime(2025, 3, 11)
            assert records[0]['completion_date'] == datetime(2025, 3, 11)
            
            # Segundo registro (formato dd.mm.yyyy)
            assert records[1]['planned_date'] == datetime(2025, 1, 12)
            assert records[1]['scheduled_start_date'] == datetime(2025, 1, 13)
            assert records[1]['completion_date'] == datetime(2022, 2, 15)
            
        finally:
            os.unlink(temp_path) 