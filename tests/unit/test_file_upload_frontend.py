"""
Testes unitários para componente frontend de upload de arquivos.

Este módulo testa todas as funcionalidades do componente Streamlit
de upload, incluindo validações, interface e integração com API.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional
import io

# Mock do streamlit antes de importar os componentes
with patch.dict('sys.modules', {'streamlit': MagicMock()}):
    from src.frontend.components.file_upload import (
        FileUploadComponent,
        UploadHistoryComponent,
        RealTimeNotificationComponent,
        UploadDetailsPage,
        render_upload_interface,
        render_file_upload_page,
        render_upload_notifications_in_sidebar
    )
    from src.frontend.services.api_client import APIClient
    from src.api.models.upload import FileType


class TestFileUploadComponent:
    """Testes para a classe FileUploadComponent."""
    
    @pytest.fixture
    def mock_api_client(self):
        """Mock do cliente da API."""
        client = Mock(spec=APIClient)
        return client
    
    @pytest.fixture
    def mock_streamlit(self):
        """Mock do streamlit."""
        with patch('src.frontend.components.file_upload.st') as mock_st:
            # Configurar mocks básicos
            mock_st.subheader = Mock()
            mock_st.expander = Mock()
            mock_st.file_uploader = Mock()
            mock_st.columns = Mock(return_value=[Mock(), Mock()])
            mock_st.selectbox = Mock()
            mock_st.checkbox = Mock()
            mock_st.text_area = Mock()
            mock_st.button = Mock()
            mock_st.error = Mock()
            mock_st.success = Mock()
            mock_st.warning = Mock()
            mock_st.info = Mock()
            mock_st.metric = Mock()
            mock_st.dataframe = Mock()
            mock_st.progress = Mock()
            
            yield mock_st
    
    @pytest.fixture
    def component(self, mock_api_client):
        """Instância do componente para testes."""
        return FileUploadComponent(mock_api_client)
    
    @pytest.fixture
    def mock_uploaded_file(self):
        """Mock de arquivo enviado."""
        mock_file = Mock()
        mock_file.name = "equipment_data.csv"
        mock_file.size = 1024 * 1024  # 1MB
        mock_file.read = Mock(return_value=b"id,name,type\n1,Motor A,Motor\n2,Pump B,Pump")
        return mock_file
    
    def test_init(self, mock_api_client):
        """Testa inicialização do componente."""
        component = FileUploadComponent(mock_api_client)
        
        assert component.api_client == mock_api_client
        assert component.allowed_extensions == ['.csv', '.xlsx', '.xls', '.xml']
        assert component.max_size_mb == 50
    
    def test_render_without_file(self, component, mock_streamlit):
        """Testa renderização sem arquivo enviado."""
        mock_streamlit.file_uploader.return_value = None
        
        result = component.render()
        
        assert result is None
        mock_streamlit.subheader.assert_called_once()
        mock_streamlit.file_uploader.assert_called_once()
    
    def test_render_with_file(self, component, mock_streamlit, mock_uploaded_file):
        """Testa renderização com arquivo enviado."""
        mock_streamlit.file_uploader.return_value = mock_uploaded_file
        
        with patch.object(component, '_handle_uploaded_file') as mock_handle:
            mock_handle.return_value = {"success": True}
            
            result = component.render()
            
            assert result == {"success": True}
            mock_handle.assert_called_once_with(mock_uploaded_file)
    
    def test_validate_file_success(self, component, mock_uploaded_file):
        """Testa validação de arquivo válido."""
        result = component._validate_file(mock_uploaded_file)
        
        assert result["valid"] is True
        assert result["message"] == "Arquivo válido"
    
    def test_validate_file_invalid_extension(self, component):
        """Testa validação de extensão inválida."""
        mock_file = Mock()
        mock_file.name = "document.txt"
        mock_file.size = 1024
        
        result = component._validate_file(mock_file)
        
        assert result["valid"] is False
        assert "não permitida" in result["message"]
    
    def test_validate_file_too_large(self, component):
        """Testa validação de arquivo muito grande."""
        mock_file = Mock()
        mock_file.name = "large_file.csv"
        mock_file.size = 60 * 1024 * 1024  # 60MB
        
        result = component._validate_file(mock_file)
        
        assert result["valid"] is False
        assert "muito grande" in result["message"]
    
    def test_detect_file_type_equipment(self, component):
        """Testa detecção de arquivo de equipamentos."""
        test_cases = [
            "equipamentos.csv",
            "equipment_data.xlsx",
            "assets.xml",
            "EQUIPMENT.CSV"
        ]
        
        for filename in test_cases:
            result = component._detect_file_type(filename)
            assert result == FileType.EQUIPMENT, f"Failed for {filename}"
    
    def test_detect_file_type_maintenance(self, component):
        """Testa detecção de arquivo de manutenções."""
        test_cases = [
            "manutencao.csv",
            "maintenance_orders.xlsx",
            "servicos.xml",
            "MAINTENANCE.CSV"
        ]
        
        for filename in test_cases:
            result = component._detect_file_type(filename)
            assert result == FileType.MAINTENANCE, f"Failed for {filename}"
    
    def test_detect_file_type_unknown(self, component):
        """Testa detecção de arquivo desconhecido."""
        test_cases = [
            "data.csv",
            "report.xlsx",
            "generic.xml"
        ]
        
        for filename in test_cases:
            result = component._detect_file_type(filename)
            assert result == FileType.UNKNOWN, f"Failed for {filename}"
    
    def test_generate_preview_csv(self, component, mock_uploaded_file):
        """Testa geração de preview para arquivo CSV."""
        csv_content = "id,name,type\n1,Motor A,Motor\n2,Pump B,Pump\n3,Valve C,Valve"
        mock_uploaded_file.read.return_value = csv_content.encode()
        mock_uploaded_file.name = "test.csv"
        
        with patch('pandas.read_csv') as mock_read_csv:
            mock_df = pd.DataFrame({'id': [1, 2, 3], 'name': ['Motor A', 'Pump B', 'Valve C']})
            mock_read_csv.return_value = mock_df
            
            result = component._generate_preview(mock_uploaded_file)
            
            assert result is not None
            assert isinstance(result, pd.DataFrame)
    
    def test_generate_preview_excel(self, component):
        """Testa geração de preview para arquivo Excel."""
        mock_file = Mock()
        mock_file.name = "test.xlsx"
        
        # Mock do pandas read_excel
        with patch('pandas.read_excel') as mock_read:
            mock_df = pd.DataFrame({'id': [1, 2], 'name': ['A', 'B']})
            mock_read.return_value = mock_df
            
            result = component._generate_preview(mock_file)
            
            assert result is not None
            assert isinstance(result, pd.DataFrame)
    
    def test_generate_preview_invalid_format(self, component):
        """Testa preview com formato inválido."""
        mock_file = Mock()
        mock_file.name = "test.txt"
        
        result = component._generate_preview(mock_file)
        
        assert result is None
    
    def test_display_file_info(self, component, mock_uploaded_file, mock_streamlit):
        """Testa exibição de informações do arquivo."""
        mock_streamlit.columns.return_value = [Mock(), Mock(), Mock(), Mock()]
        
        result = component._display_file_info(mock_uploaded_file)
        
        assert isinstance(result, dict)
        assert "Nome" in result
        assert "Tamanho" in result
        assert "Tipo" in result
        assert "Tipo detectado" in result
        
        mock_streamlit.columns.assert_called_once_with(4)
    
    def test_perform_upload_success(self, component, mock_uploaded_file, mock_streamlit):
        """Testa upload bem-sucedido."""
        # Mock da resposta da API
        mock_response = {
            "upload_id": "12345",
            "filename": "test.csv",
            "status": "uploaded",
            "message": "Sucesso"
        }
        component.api_client.upload_file.return_value = mock_response
        
        # Mock do progress bar
        mock_progress = Mock()
        mock_streamlit.progress.return_value = mock_progress
        
        result = component._perform_upload(
            mock_uploaded_file,
            FileType.EQUIPMENT,
            "Test description",
            False
        )
        
        assert result is not None
        assert result["success"] is True
        assert result["upload_id"] == "12345"
        
        component.api_client.upload_file.assert_called_once()
        mock_streamlit.success.assert_called()
    
    def test_perform_upload_failure(self, component, mock_uploaded_file, mock_streamlit):
        """Testa falha no upload."""
        # Mock de erro na API
        component.api_client.upload_file.side_effect = Exception("API Error")
        
        result = component._perform_upload(
            mock_uploaded_file,
            FileType.EQUIPMENT,
            "Test description",
            False
        )
        
        assert result is not None
        assert result["success"] is False
        
        mock_streamlit.error.assert_called()


class TestUploadHistoryComponent:
    """Testes para a classe UploadHistoryComponent."""
    
    @pytest.fixture
    def mock_api_client(self):
        """Mock do cliente da API."""
        client = Mock(spec=APIClient)
        return client
    
    @pytest.fixture
    def mock_streamlit(self):
        """Mock do streamlit."""
        with patch('src.frontend.components.file_upload.st') as mock_st:
            mock_st.subheader = Mock()
            mock_st.columns = Mock(return_value=[Mock(), Mock()])
            mock_st.selectbox = Mock()
            mock_st.number_input = Mock()
            mock_st.dataframe = Mock()
            mock_st.metric = Mock()
            mock_st.info = Mock()
            mock_st.warning = Mock()
            
            yield mock_st
    
    @pytest.fixture
    def component(self, mock_api_client):
        """Instância do componente para testes."""
        return UploadHistoryComponent(mock_api_client)
    
    @pytest.fixture
    def mock_upload_history(self):
        """Mock de histórico de uploads."""
        return {
            "uploads": [
                {
                    "upload_id": "1",
                    "filename": "test1.csv",
                    "status": "completed",
                    "uploaded_at": "2024-01-15T10:00:00",
                    "records_processed": 100
                },
                {
                    "upload_id": "2",
                    "filename": "test2.csv",
                    "status": "processing",
                    "uploaded_at": "2024-01-15T11:00:00",
                    "records_processed": 50
                }
            ],
            "total_count": 2
        }
    
    def test_init(self, mock_api_client):
        """Testa inicialização do componente."""
        component = UploadHistoryComponent(mock_api_client)
        
        assert component.api_client == mock_api_client
    
    def test_render_with_history(self, component, mock_streamlit, mock_upload_history):
        """Testa renderização com histórico."""
        component.api_client.get_upload_history.return_value = mock_upload_history
        
        component.render()
        
        component.api_client.get_upload_history.assert_called_once()
        mock_streamlit.subheader.assert_called()
    
    def test_render_empty_history(self, component, mock_streamlit):
        """Testa renderização com histórico vazio."""
        component.api_client.get_upload_history.return_value = {
            "uploads": [],
            "total_count": 0
        }
        
        component.render()
        
        mock_streamlit.info.assert_called()
    
    def test_render_api_error(self, component, mock_streamlit):
        """Testa renderização com erro da API."""
        component.api_client.get_upload_history.side_effect = Exception("API Error")
        
        component.render()
        
        mock_streamlit.warning.assert_called()


class TestRealTimeNotificationComponent:
    """Testes para a classe RealTimeNotificationComponent."""
    
    @pytest.fixture
    def mock_api_client(self):
        """Mock do cliente da API."""
        client = Mock(spec=APIClient)
        return client
    
    @pytest.fixture
    def mock_streamlit(self):
        """Mock do streamlit."""
        with patch('src.frontend.components.file_upload.st') as mock_st:
            # Mock do session_state
            mock_st.session_state = {}
            mock_st.sidebar = Mock()
            mock_st.empty = Mock()
            mock_st.container = Mock()
            mock_st.success = Mock()
            mock_st.info = Mock()
            mock_st.warning = Mock()
            mock_st.error = Mock()
            
            yield mock_st
    
    @pytest.fixture
    def component(self, mock_api_client):
        """Instância do componente para testes."""
        return RealTimeNotificationComponent(mock_api_client)
    
    def test_init(self, mock_api_client):
        """Testa inicialização do componente."""
        component = RealTimeNotificationComponent(mock_api_client)
        
        assert component.api_client == mock_api_client
        assert component.monitored_uploads == set()
        assert component.notifications == []
    
    def test_initialize_notifications(self, component, mock_streamlit):
        """Testa inicialização de notificações."""
        component.initialize_notifications()
        
        assert "upload_notifications" in mock_streamlit.session_state
        assert "monitored_uploads" in mock_streamlit.session_state
    
    def test_add_upload_to_monitoring(self, component, mock_streamlit):
        """Testa adição de upload ao monitoramento."""
        upload_id = "test-123"
        
        component.add_upload_to_monitoring(upload_id)
        
        assert upload_id in component.monitored_uploads
    
    def test_check_for_updates(self, component, mock_streamlit):
        """Testa verificação de atualizações."""
        upload_id = "test-123"
        component.monitored_uploads.add(upload_id)
        
        # Mock da resposta da API
        component.api_client.get_upload_status.return_value = {
            "upload_id": upload_id,
            "filename": "test.csv",
            "status": "completed",
            "progress_percentage": 100
        }
        
        component.check_for_updates()
        
        component.api_client.get_upload_status.assert_called_with(upload_id)
    
    def test_get_notification_summary(self, component):
        """Testa obtenção de resumo de notificações."""
        # Adicionar algumas notificações mock
        component.notifications = [
            {"status": "completed", "timestamp": "2024-01-15T10:00:00"},
            {"status": "failed", "timestamp": "2024-01-15T11:00:00"},
            {"status": "processing", "timestamp": "2024-01-15T12:00:00"}
        ]
        
        summary = component.get_notification_summary()
        
        assert isinstance(summary, dict)
        assert "total" in summary
        assert summary["total"] == 3


class TestUploadDetailsPage:
    """Testes para a classe UploadDetailsPage."""
    
    @pytest.fixture
    def mock_api_client(self):
        """Mock do cliente da API."""
        client = Mock(spec=APIClient)
        return client
    
    @pytest.fixture
    def mock_streamlit(self):
        """Mock do streamlit."""
        with patch('src.frontend.components.file_upload.st') as mock_st:
            mock_st.title = Mock()
            mock_st.columns = Mock(return_value=[Mock(), Mock(), Mock()])
            mock_st.metric = Mock()
            mock_st.progress = Mock()
            mock_st.dataframe = Mock()
            mock_st.expander = Mock()
            mock_st.code = Mock()
            mock_st.warning = Mock()
            mock_st.error = Mock()
            
            yield mock_st
    
    @pytest.fixture
    def component(self, mock_api_client):
        """Instância do componente para testes."""
        return UploadDetailsPage(mock_api_client)
    
    @pytest.fixture
    def mock_upload_details(self):
        """Mock de detalhes do upload."""
        return {
            "upload_id": "test-123",
            "filename": "equipment.csv",
            "status": "completed",
            "progress_percentage": 100,
            "records_processed": 150,
            "records_valid": 145,
            "records_invalid": 5,
            "processing_time_seconds": 30.5,
            "started_at": "2024-01-15T10:00:00",
            "completed_at": "2024-01-15T10:00:30"
        }
    
    def test_init(self, mock_api_client):
        """Testa inicialização do componente."""
        component = UploadDetailsPage(mock_api_client)
        
        assert component.api_client == mock_api_client
    
    def test_render_with_details(self, component, mock_streamlit, mock_upload_details):
        """Testa renderização com detalhes."""
        upload_id = "test-123"
        component.api_client.get_upload_status.return_value = mock_upload_details
        
        component.render(upload_id)
        
        component.api_client.get_upload_status.assert_called_once_with(upload_id)
        mock_streamlit.title.assert_called()
    
    def test_render_upload_not_found(self, component, mock_streamlit):
        """Testa renderização quando upload não é encontrado."""
        upload_id = "nonexistent"
        component.api_client.get_upload_status.side_effect = Exception("Not found")
        
        component.render(upload_id)
        
        mock_streamlit.error.assert_called()
    
    def test_calculate_efficiency(self, component, mock_upload_details):
        """Testa cálculo de eficiência."""
        result = component._calculate_efficiency(mock_upload_details)
        
        assert isinstance(result, str)
        assert "%" in result


class TestHelperFunctions:
    """Testes para funções auxiliares."""
    
    @pytest.fixture
    def mock_streamlit(self):
        """Mock do streamlit."""
        with patch('src.frontend.components.file_upload.st') as mock_st:
            mock_st.title = Mock()
            mock_st.tabs = Mock(return_value=[Mock(), Mock()])
            mock_st.sidebar = Mock()
            
            yield mock_st
    
    @pytest.fixture
    def mock_api_client(self):
        """Mock do cliente da API."""
        return Mock(spec=APIClient)
    
    def test_render_upload_interface(self, mock_streamlit, mock_api_client):
        """Testa função de renderização da interface."""
        with patch('src.frontend.components.file_upload.FileUploadComponent') as mock_component:
            mock_instance = Mock()
            mock_component.return_value = mock_instance
            mock_instance.render.return_value = None
            
            result = render_upload_interface(mock_api_client)
            
            assert result is None
            mock_component.assert_called_once_with(mock_api_client)
            mock_instance.render.assert_called_once()
    
    def test_render_file_upload_page(self, mock_streamlit):
        """Testa função de renderização da página principal."""
        with patch('src.frontend.components.file_upload.APIClient') as mock_client_class, \
             patch('src.frontend.components.file_upload.FileUploadComponent') as mock_component_class, \
             patch('src.frontend.components.file_upload.UploadHistoryComponent') as mock_history_class:
            
            # Configurar mocks
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            mock_component = Mock()
            mock_component_class.return_value = mock_component
            mock_component.render.return_value = None
            
            mock_history = Mock()
            mock_history_class.return_value = mock_history
            
            render_file_upload_page()
            
            mock_streamlit.title.assert_called()
            mock_streamlit.tabs.assert_called()
    
    def test_render_upload_notifications_in_sidebar(self, mock_streamlit, mock_api_client):
        """Testa renderização de notificações na sidebar."""
        with patch('src.frontend.components.file_upload.RealTimeNotificationComponent') as mock_component:
            mock_instance = Mock()
            mock_component.return_value = mock_instance
            
            render_upload_notifications_in_sidebar(mock_api_client)
            
            mock_component.assert_called_once_with(mock_api_client)
            mock_instance.render_sidebar_notifications.assert_called_once()


class TestIntegrationScenarios:
    """Testes de cenários integrados."""
    
    @pytest.fixture
    def mock_streamlit_full(self):
        """Mock completo do streamlit."""
        with patch('src.frontend.components.file_upload.st') as mock_st:
            # Configurar todos os mocks necessários
            mock_st.session_state = {}
            mock_st.subheader = Mock()
            mock_st.file_uploader = Mock()
            mock_st.button = Mock()
            mock_st.success = Mock()
            mock_st.error = Mock()
            mock_st.columns = Mock(return_value=[Mock(), Mock()])
            mock_st.selectbox = Mock()
            mock_st.checkbox = Mock()
            mock_st.text_area = Mock()
            mock_st.expander = Mock()
            mock_st.dataframe = Mock()
            mock_st.metric = Mock()
            mock_st.progress = Mock()
            
            yield mock_st
    
    def test_complete_upload_workflow(self, mock_streamlit_full):
        """Testa fluxo completo de upload."""
        # Mock do cliente API
        mock_api_client = Mock(spec=APIClient)
        
        # Mock do arquivo
        mock_file = Mock()
        mock_file.name = "test_equipment.csv"
        mock_file.size = 1024
        mock_file.read.return_value = b"id,name\n1,Motor"
        
        # Mock da resposta de upload
        mock_api_client.upload_file.return_value = {
            "upload_id": "test-123",
            "status": "uploaded",
            "message": "Success"
        }
        
        # Configurar streamlit mocks
        mock_streamlit_full.file_uploader.return_value = mock_file
        mock_streamlit_full.button.return_value = True
        mock_streamlit_full.selectbox.return_value = FileType.EQUIPMENT
        mock_streamlit_full.checkbox.return_value = False
        mock_streamlit_full.text_area.return_value = "Test description"
        
        # Executar componente
        component = FileUploadComponent(mock_api_client)
        result = component.render()
        
        # Verificar resultado
        assert result is not None
        mock_api_client.upload_file.assert_called_once()
        mock_streamlit_full.success.assert_called()
