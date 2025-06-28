"""
Componente de upload de arquivos para interface Streamlit.

Este módulo implementa a interface de usuário para upload de arquivos
de dados, incluindo validações, feedback visual e integração com a API.
"""

import streamlit as st
import pandas as pd
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
import time
import uuid
import asyncio
from datetime import datetime, timedelta

from services.api_client import APIClient
from api.models.upload import FileType


class FileUploadComponent:
    """Componente para upload de arquivos no Streamlit."""
    
    def __init__(self, api_client: APIClient):
        """
        Inicializa o componente de upload.
        
        Args:
            api_client: Cliente da API para comunicação
        """
        self.api_client = api_client
        self.allowed_extensions = ['.csv', '.xlsx', '.xls', '.xml']
        self.max_size_mb = 50
        
    def render(self) -> Optional[Dict[str, Any]]:
        """
        Renderiza a interface de upload de arquivos.
        
        Returns:
            Dict com informações do upload se realizado, None caso contrário
        """
        st.subheader("📁 Upload de Arquivos de Dados")
        
        # Informações sobre tipos aceitos
        with st.expander("ℹ️ Tipos de arquivo aceitos", expanded=False):
            st.markdown("""
            **Formatos suportados:**
            - **CSV** (.csv) - Dados separados por vírgula
            - **Excel** (.xlsx, .xls) - Planilhas do Microsoft Excel  
            - **XML** (.xml) - Dados estruturados em XML
            
            **Tipos de dados reconhecidos:**
            - **Equipamentos**: Arquivos contendo dados de ativos e equipamentos
            - **Manutenções**: Dados de ordens de serviço e histórico de manutenção
            
            **Limites:**
            - Tamanho máximo: 50 MB
            - O sistema detecta automaticamente o tipo de dados baseado no nome do arquivo
            """)
        
        # Interface de upload
        uploaded_file = st.file_uploader(
            "Escolha um arquivo",
            type=['csv', 'xlsx', 'xls', 'xml'],
            help=f"Formatos aceitos: {', '.join(self.allowed_extensions)} • Tamanho máximo: {self.max_size_mb}MB"
        )
        
        if uploaded_file is not None:
            return self._handle_uploaded_file(uploaded_file)
        
        return None
    
    def _handle_uploaded_file(self, uploaded_file) -> Optional[Dict[str, Any]]:
        """
        Processa arquivo enviado pelo usuário.
        
        Args:
            uploaded_file: Arquivo enviado via st.file_uploader
            
        Returns:
            Dict com resultado do upload
        """
        # Validações frontend
        validation_result = self._validate_file(uploaded_file)
        if not validation_result["valid"]:
            st.error(f"❌ {validation_result['message']}")
            return None
        
        # Exibir informações do arquivo
        file_info = self._display_file_info(uploaded_file)
        
        # Opções de upload
        col1, col2 = st.columns(2)
        
        with col1:
            file_type = st.selectbox(
                "Tipo de dados",
                options=[None, FileType.EQUIPMENT, FileType.MAINTENANCE],
                format_func=lambda x: {
                    None: "🔍 Auto-detectar",
                    FileType.EQUIPMENT: "⚙️ Equipamentos",
                    FileType.MAINTENANCE: "🔧 Manutenções"
                }.get(x, str(x)),
                help="Deixe em 'Auto-detectar' para identificação automática"
            )
        
        with col2:
            overwrite_existing = st.checkbox(
                "Sobrescrever dados existentes",
                value=False,
                help="Se marcado, dados existentes serão substituídos"
            )
        
        # Campo de descrição
        description = st.text_area(
            "Descrição (opcional)",
            placeholder="Ex: Arquivo de equipamentos da planta industrial - Janeiro 2024",
            max_chars=500,
            help="Descrição opcional para identificar o upload"
        )
        
        # Preview dos dados (se possível)
        preview_data = self._generate_preview(uploaded_file)
        if preview_data is not None:
            with st.expander("👀 Preview dos dados", expanded=False):
                st.dataframe(preview_data, use_container_width=True)
        
        # Botão de upload
        if st.button("🚀 Fazer Upload", type="primary", use_container_width=True):
            return self._perform_upload(
                uploaded_file, 
                file_type, 
                description, 
                overwrite_existing
            )
        
        return None
    
    def _validate_file(self, uploaded_file) -> Dict[str, Any]:
        """
        Valida arquivo antes do upload.
        
        Args:
            uploaded_file: Arquivo a ser validado
            
        Returns:
            Dict com resultado da validação
        """
        # Verificar extensão
        file_extension = Path(uploaded_file.name).suffix.lower()
        if file_extension not in self.allowed_extensions:
            return {
                "valid": False,
                "message": f"Extensão '{file_extension}' não permitida. Use: {', '.join(self.allowed_extensions)}"
            }
        
        # Verificar tamanho
        file_size_mb = uploaded_file.size / (1024 * 1024)
        if file_size_mb > self.max_size_mb:
            return {
                "valid": False,
                "message": f"Arquivo muito grande ({file_size_mb:.1f}MB). Tamanho máximo: {self.max_size_mb}MB"
            }
        
        return {"valid": True, "message": "Arquivo válido"}
    
    def _display_file_info(self, uploaded_file) -> Dict[str, Any]:
        """
        Exibe informações do arquivo carregado.
        
        Args:
            uploaded_file: Arquivo carregado
            
        Returns:
            Dict com informações do arquivo
        """
        file_size_mb = uploaded_file.size / (1024 * 1024)
        file_extension = Path(uploaded_file.name).suffix.lower()
        
        # Detectar tipo provável
        detected_type = self._detect_file_type(uploaded_file.name)
        
        info_data = {
            "Nome": uploaded_file.name,
            "Tamanho": f"{file_size_mb:.2f} MB",
            "Tipo": file_extension.upper(),
            "Tipo detectado": {
                FileType.EQUIPMENT: "⚙️ Equipamentos",
                FileType.MAINTENANCE: "🔧 Manutenções",
                FileType.UNKNOWN: "❓ Não identificado"
            }.get(detected_type, "❓ Desconhecido")
        }
        
        # Exibir em colunas
        cols = st.columns(4)
        for i, (key, value) in enumerate(info_data.items()):
            with cols[i]:
                st.metric(key, value)
        
        return info_data
    
    def _detect_file_type(self, filename: str) -> FileType:
        """
        Detecta tipo de arquivo baseado no nome.
        
        Args:
            filename: Nome do arquivo
            
        Returns:
            FileType detectado
        """
        filename_lower = filename.lower()
        
        # Palavras-chave para equipamentos
        equipment_keywords = ['equipment', 'equipamento', 'equip', 'asset', 'ativo']
        
        # Palavras-chave para manutenções
        maintenance_keywords = ['maintenance', 'manutencao', 'manutenção', 'maint', 'servico', 'serviço']
        
        # Verificar equipamentos
        for keyword in equipment_keywords:
            if keyword in filename_lower:
                return FileType.EQUIPMENT
        
        # Verificar manutenções
        for keyword in maintenance_keywords:
            if keyword in filename_lower:
                return FileType.MAINTENANCE
        
        return FileType.UNKNOWN
    
    def _generate_preview(self, uploaded_file) -> Optional[pd.DataFrame]:
        """
        Gera preview dos dados do arquivo.
        
        Args:
            uploaded_file: Arquivo para preview
            
        Returns:
            DataFrame com preview ou None se não possível
        """
        try:
            file_extension = Path(uploaded_file.name).suffix.lower()
            
            # Reset file pointer
            uploaded_file.seek(0)
            
            if file_extension == '.csv':
                # Tentar diferentes encodings
                for encoding in ['utf-8', 'latin-1', 'cp1252']:
                    try:
                        uploaded_file.seek(0)
                        df = pd.read_csv(uploaded_file, encoding=encoding, nrows=5)
                        return df
                    except UnicodeDecodeError:
                        continue
                    except Exception:
                        break
                        
            elif file_extension in ['.xlsx', '.xls']:
                uploaded_file.seek(0)
                df = pd.read_excel(uploaded_file, nrows=5)
                return df
                
            # XML é mais complexo, não implementar preview por agora
            
        except Exception as e:
            st.warning(f"⚠️ Não foi possível gerar preview: {str(e)}")
        
        return None
    
    def _perform_upload(self, uploaded_file, file_type: Optional[FileType], 
                       description: str, overwrite_existing: bool) -> Dict[str, Any]:
        """
        Executa o upload do arquivo.
        
        Args:
            uploaded_file: Arquivo para upload
            file_type: Tipo de dados
            description: Descrição do upload
            overwrite_existing: Se deve sobrescrever dados
            
        Returns:
            Dict com resultado do upload
        """
        progress_placeholder = st.empty()
        status_placeholder = st.empty()
        
        try:
            # Mostrar progresso
            with progress_placeholder.container():
                progress_bar = st.progress(0)
                status_text = st.text("🚀 Iniciando upload...")
            
            # Preparar dados do arquivo
            uploaded_file.seek(0)
            file_content = uploaded_file.read()
            
            # Simular progresso de upload
            for i in range(0, 101, 20):
                progress_bar.progress(i)
                if i == 20:
                    status_text.text("📤 Enviando arquivo...")
                elif i == 60:
                    status_text.text("🔍 Validando dados...")
                elif i == 80:
                    status_text.text("💾 Salvando arquivo...")
                time.sleep(0.3)
            
            # Fazer upload real via API
            api_result, success = self.api_client.upload_file(
                file_content=file_content,
                filename=uploaded_file.name,
                file_type=file_type.value if file_type else "",
                description=description,
                overwrite_existing=overwrite_existing
            )
            
            if success and api_result:
                upload_result = {
                    "success": True,
                    "upload_id": api_result.get("upload_id"),
                    "filename": api_result.get("filename"),
                    "file_size": api_result.get("file_size"),
                    "file_type": api_result.get("file_type"),
                    "message": api_result.get("message", "Arquivo enviado com sucesso!")
                }
            else:
                upload_result = {
                    "success": False,
                    "message": "Erro ao enviar arquivo para o servidor"
                }
            
            # Limpar progresso
            progress_placeholder.empty()
            
            # Exibir resultado
            if upload_result["success"]:
                status_placeholder.success(f"✅ {upload_result['message']}")
                
                # Exibir informações do upload
                st.info(f"""
                **Upload realizado com sucesso!**
                - 🆔 ID: `{upload_result['upload_id']}`
                - 📁 Arquivo: {upload_result['filename']}
                - 📊 Tipo: {upload_result['file_type']}
                - ⏰ Status: Aguardando processamento
                """)
                
                # Botão para processar imediatamente
                col1, col2 = st.columns([2, 1])
                with col1:
                    if st.button("🚀 Processar Agora", type="primary", use_container_width=True):
                        upload_id = upload_result.get('upload_id')
                        if upload_id:
                            with st.spinner("⚙️ Processando arquivo..."):
                                try:
                                    # Usar o mesmo método da UploadHistoryComponent
                                    result, success = self.api_client.process_single_upload(upload_id)
                                    
                                    if success and result and result.get("success", False):
                                        st.success(f"✅ **Processamento concluído!**")
                                        st.balloons()
                                        time.sleep(2)
                                        st.rerun()
                                    else:
                                        error_msg = result.get("error", "Erro desconhecido") if result else "Falha na comunicação"
                                        st.warning(f"⚠️ **Processamento pendente:** {error_msg}")
                                        st.info("💡 O arquivo ficará disponível para processamento na aba 'Histórico'.")
                                except Exception as e:
                                    st.warning(f"⚠️ **Processamento pendente:** {str(e)}")
                                    st.info("💡 O arquivo ficará disponível para processamento na aba 'Histórico'.")
                        
                with col2:
                    st.info("💡 Ou processe depois na aba **Histórico**")
                
                return upload_result
            else:
                status_placeholder.error(f"❌ Erro no upload: {upload_result.get('message', 'Erro desconhecido')}")
                
        except Exception as e:
            progress_placeholder.empty()
            status_placeholder.error(f"❌ Erro durante upload: {str(e)}")
            
        return {
            "success": False,
            "message": "Erro durante o upload"
        }


def render_upload_interface(api_client: APIClient) -> Optional[Dict[str, Any]]:
    """
    Função helper para renderizar interface de upload.
    
    Args:
        api_client: Cliente da API
        
    Returns:
        Resultado do upload se realizado
    """
    component = FileUploadComponent(api_client)
    return component.render()


class UploadHistoryComponent:
    """Componente para exibir histórico de uploads."""
    
    def __init__(self, api_client: APIClient):
        """
        Inicializa o componente de histórico.
        
        Args:
            api_client: Cliente da API para comunicação
        """
        self.api_client = api_client
    
    def render(self) -> None:
        """Renderiza o histórico de uploads."""
        st.subheader("📋 Histórico de Uploads")
        
        # Verificar uploads pendentes primeiro
        self._render_pending_uploads_section()
        
        st.markdown("---")
        
        # Controles de filtro
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            status_filter = st.selectbox(
                "Filtrar por status:",
                options=["Todos", "uploaded", "processing", "completed", "failed"],
                format_func=lambda x: {
                    "Todos": "🔍 Todos os status",
                    "uploaded": "📤 Aguardando processamento",
                    "processing": "⚙️ Processando",
                    "completed": "✅ Concluído",
                    "failed": "❌ Falhou"
                }.get(x, x)
            )
        
        with col2:
            limit = st.selectbox(
                "Número de registros:",
                options=[10, 25, 50, 100],
                index=1,
                help="Quantos uploads exibir"
            )
        
        with col3:
            if st.button("🔄 Atualizar", use_container_width=True):
                st.rerun()
        
        # Buscar histórico via API
        try:
            history_data, success = self.api_client.get_upload_history(limit=limit)
            
            if success and history_data:
                uploads = history_data.get("uploads", [])
                
                if uploads:
                    self._render_upload_table(uploads, status_filter)
                else:
                    st.info("📭 Nenhum upload encontrado.")
            else:
                st.error("❌ Erro ao carregar histórico de uploads.")
                
        except Exception as e:
            st.error(f"❌ Erro ao buscar histórico: {str(e)}")

    def _render_pending_uploads_section(self) -> None:
        """Renderiza seção específica para uploads pendentes com processamento automático."""
        st.subheader("⚡ Processamento Automático")
        
        try:
            # Buscar uploads pendentes
            pending_data, success = self.api_client.get_pending_uploads()
            
            if success and pending_data:
                total_pending = pending_data.get("total_pending", 0)
                uploads = pending_data.get("uploads", [])
                
                if total_pending > 0:
                    # Alerta de uploads pendentes
                    st.warning(f"⚠️ **{total_pending} upload(s) aguardando processamento**")
                    
                    # Botões de ação
                    col1, col2, col3 = st.columns([2, 2, 2])
                    
                    with col1:
                        if st.button("🚀 Processar Todos", 
                                   type="primary", 
                                   use_container_width=True,
                                   help="Processa todos os uploads pendentes"):
                            self._process_all_pending_uploads()
                    
                    with col2:
                        auto_process = st.checkbox("🔄 Processamento automático", 
                                                 help="Processa automaticamente novos uploads")
                        if auto_process and 'auto_process_enabled' not in st.session_state:
                            st.session_state.auto_process_enabled = True
                            st.rerun()
                    
                    with col3:
                        if st.button("📊 Ver Detalhes", 
                                   use_container_width=True,
                                   help="Ver detalhes dos uploads pendentes"):
                            st.session_state.show_pending_details = not st.session_state.get('show_pending_details', False)
                            st.rerun()
                    
                    # Exibir detalhes se solicitado
                    if st.session_state.get('show_pending_details', False):
                        st.markdown("**📋 Uploads Pendentes:**")
                        for upload in uploads:
                            with st.container():
                                col1, col2, col3 = st.columns([3, 2, 1])
                                
                                with col1:
                                    st.write(f"📁 **{upload.get('filename', 'Arquivo desconhecido')}**")
                                    st.caption(f"ID: {upload.get('upload_id', 'N/A')}")
                                
                                with col2:
                                    st.write(f"📊 Tipo: {upload.get('data_type', 'Desconhecido').title()}")
                                    st.caption(f"Formato: {upload.get('file_format', 'N/A').upper()}")
                                
                                with col3:
                                    if st.button("▶️", 
                                               key=f"process_{upload.get('upload_id')}",
                                               help="Processar este upload"):
                                        self._process_single_upload(upload.get('upload_id'))
                                
                                st.markdown("---")
                else:
                    st.success("✅ **Todos os uploads estão processados!**")
                    st.info("💡 Novos uploads aparecerão aqui automaticamente.")
            else:
                st.error("❌ Erro ao verificar uploads pendentes.")
        
        except Exception as e:
            st.error(f"❌ Erro ao buscar uploads pendentes: {str(e)}")

    def _process_all_pending_uploads(self) -> None:
        """Processa todos os uploads pendentes."""
        with st.spinner("⚙️ Processando todos os uploads pendentes..."):
            try:
                result, success = self.api_client.process_pending_uploads()
                
                if success and result:
                    if not result.get("error"):
                        processed_count = result.get("processed_count", 0)
                        error_count = result.get("error_count", 0)
                        
                        if processed_count > 0:
                            st.success(f"✅ **{processed_count} upload(s) processado(s) com sucesso!**")
                        
                        if error_count > 0:
                            st.warning(f"⚠️ **{error_count} upload(s) falharam no processamento.**")
                        
                        # Mostrar resultados detalhados
                        if result.get("results"):
                            st.markdown("**📊 Resultados do Processamento:**")
                            for res in result.get("results", []):
                                status_icon = "✅" if res.get("status") == "completed" else "❌"
                                st.write(f"{status_icon} {res.get('filename', 'Arquivo desconhecido')}")
                        
                        # Aguardar um pouco e atualizar
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(f"❌ Erro no processamento: {result.get('error')}")
                else:
                    st.error("❌ Falha na comunicação com o servidor.")
                    
            except Exception as e:
                st.error(f"❌ Erro inesperado: {str(e)}")

    def _process_single_upload(self, upload_id: str) -> None:
        """Processa um upload específico."""
        if not upload_id:
            st.error("❌ ID do upload inválido.")
            return
        
        with st.spinner(f"⚙️ Processando upload {upload_id[:8]}..."):
            try:
                result, success = self.api_client.process_single_upload(upload_id)
                
                if success and result:
                    if result.get("success", False):
                        st.success(f"✅ **Upload processado:** {result.get('filename', 'Arquivo desconhecido')}")
                        # Aguardar um pouco e atualizar
                        time.sleep(1)
                        st.rerun()
                    else:
                        error_msg = result.get("error", "Erro desconhecido")
                        st.error(f"❌ **Falha no processamento:** {error_msg}")
                else:
                    st.error("❌ Falha na comunicação com o servidor.")
                    
            except Exception as e:
                st.error(f"❌ Erro inesperado: {str(e)}")
    
    def _render_upload_table(self, uploads: List[Dict], status_filter: str) -> None:
        """
        Renderiza tabela com histórico de uploads.
        
        Args:
            uploads: Lista de uploads
            status_filter: Filtro de status aplicado
        """
        # Filtra por status se necessário
        if status_filter != "Todos":
            uploads = [u for u in uploads if u.get("status") == status_filter]
        
        if not uploads:
            st.info(f"📭 Nenhum upload encontrado com status '{status_filter}'.")
            return
        
        # Exibe estatísticas rápidas
        self._render_upload_stats(uploads)
        
        st.markdown("---")
        
        # Renderiza cada upload como um card
        for upload in uploads:
            self._render_upload_card(upload)
    
    def _render_upload_stats(self, uploads: List[Dict]) -> None:
        """
        Renderiza estatísticas rápidas dos uploads.
        
        Args:
            uploads: Lista de uploads
        """
        # Calcula estatísticas
        total = len(uploads)
        completed = len([u for u in uploads if u.get("status") == "completed"])
        failed = len([u for u in uploads if u.get("status") == "failed"])
        processing = len([u for u in uploads if u.get("status") == "processing"])
        
        # Exibe métricas
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total", total)
        
        with col2:
            st.metric("Concluídos", completed, delta=f"{(completed/total*100):.1f}%" if total > 0 else "0%")
        
        with col3:
            st.metric("Processando", processing)
        
        with col4:
            st.metric("Falhas", failed, delta=f"{(failed/total*100):.1f}%" if total > 0 else "0%")
    
    def _render_upload_card(self, upload: Dict) -> None:
        """
        Renderiza um card para um upload específico.
        
        Args:
            upload: Dados do upload
        """
        # Mapeamento de status para emojis e cores
        status_info = {
            "uploaded": {"emoji": "📤", "color": "blue", "label": "Aguardando"},
            "processing": {"emoji": "⚙️", "color": "orange", "label": "Processando"},
            "completed": {"emoji": "✅", "color": "green", "label": "Concluído"},
            "failed": {"emoji": "❌", "color": "red", "label": "Falhou"}
        }
        
        status = upload.get("status", "unknown")
        info = status_info.get(status, {"emoji": "❓", "color": "gray", "label": "Desconhecido"})
        
        # Container do card
        with st.container():
            # Header do card
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.markdown(f"**📁 {upload.get('filename', 'Arquivo desconhecido')}**")
                
            with col2:
                st.markdown(f"**{info['emoji']} {info['label']}**")
                
            with col3:
                upload_id = upload.get("upload_id", "")
                if upload_id:
                    # Se o upload está pendente, mostrar botão de processamento
                    if status == "uploaded":
                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            if st.button("▶️", key=f"process_card_{upload_id}", help="Processar agora"):
                                self._process_single_upload(upload_id)
                        with col_b:
                            if st.button("🔍", key=f"detail_{upload_id}", help="Ver detalhes rápidos"):
                                self._show_upload_details(upload)
                        with col_c:
                            if st.button("📋", key=f"full_detail_{upload_id}", help="Análise completa"):
                                st.session_state.page_mode = "upload_details"
                                st.session_state.selected_upload_id = upload_id
                                st.rerun()
                    else:
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("🔍", key=f"detail_{upload_id}", help="Ver detalhes rápidos"):
                                self._show_upload_details(upload)
                        with col_b:
                            if st.button("📋", key=f"full_detail_{upload_id}", help="Análise completa"):
                                st.session_state.page_mode = "upload_details"
                                st.session_state.selected_upload_id = upload_id
                                st.rerun()
            
            # Informações principais
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.caption(f"📅 {upload.get('created_at', 'Data desconhecida')}")
                
            with col2:
                file_size = upload.get("file_size", 0)
                if file_size:
                    size_mb = file_size / (1024 * 1024)
                    st.caption(f"📏 {size_mb:.2f} MB")
                else:
                    st.caption("📏 Tamanho desconhecido")
                    
            with col3:
                records_valid = upload.get("records_valid")
                if records_valid is not None:
                    st.caption(f"📊 {records_valid} registros")
                else:
                    st.caption("📊 Processamento pendente")
            
            # Barra de progresso para uploads em processamento
            if status == "processing":
                progress = upload.get("progress_percentage", 0)
                st.progress(progress / 100)
                st.caption(f"Progresso: {progress}%")
            
            # Mensagem de erro se houver
            if status == "failed" and upload.get("error_message"):
                st.error(f"💥 {upload.get('error_message')}")
            
            st.markdown("---")
    
    def _show_upload_details(self, upload: Dict) -> None:
        """
        Exibe detalhes completos de um upload.
        
        Args:
            upload: Dados do upload
        """
        upload_id = upload.get("upload_id")
        
        if not upload_id:
            st.error("❌ ID do upload não disponível")
            return
        
        # Busca detalhes atualizados via API
        try:
            details, success = self.api_client.get_upload_status(upload_id)
            
            if success and details:
                # Exibe detalhes em um modal (usando expander)
                with st.expander(f"📋 Detalhes do Upload {upload_id}", expanded=True):
                    
                    # Informações básicas
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**📄 Informações do Arquivo:**")
                        st.write(f"• Nome: {details.get('filename')}")
                        st.write(f"• Tamanho: {details.get('file_size', 0) / (1024*1024):.2f} MB")
                        st.write(f"• Tipo: {details.get('file_type', 'Não identificado')}")
                        
                    with col2:
                        st.markdown("**⏱️ Timestamps:**")
                        st.write(f"• Upload: {details.get('created_at', 'N/A')}")
                        st.write(f"• Início: {details.get('started_at', 'N/A')}")
                        st.write(f"• Conclusão: {details.get('completed_at', 'N/A')}")
                    
                    # Resultados do processamento
                    if details.get("records_processed"):
                        st.markdown("**📊 Resultados do Processamento:**")
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("Total Processado", details.get("records_processed", 0))
                        with col2:
                            st.metric("Registros Válidos", details.get("records_valid", 0))
                        with col3:
                            st.metric("Registros Inválidos", details.get("records_invalid", 0))
                    
                    # Tempo de processamento
                    processing_time = details.get("processing_time_seconds")
                    if processing_time:
                        st.metric("⏰ Tempo de Processamento", f"{processing_time:.2f}s")
                    
                    # Erro se houver
                    if details.get("error_message"):
                        st.error(f"💥 **Erro:** {details.get('error_message')}")
                        
            else:
                st.error("❌ Não foi possível carregar detalhes do upload")
                
        except Exception as e:
            st.error(f"❌ Erro ao buscar detalhes: {str(e)}")


def render_upload_notifications_in_sidebar(api_client: APIClient) -> None:
    """
    Renderiza notificações de upload na sidebar da aplicação.
    
    Args:
        api_client: Cliente da API
    """
    notification_component = RealTimeNotificationComponent(api_client)
    notification_component.render_sidebar_notifications()


def render_file_upload_page() -> None:
    """
    Renderiza a página completa de upload de arquivos com histórico.
    """
    # Verifica se APIClient está disponível
    if not hasattr(st.session_state, 'api_client') or st.session_state.api_client is None:
        st.error("❌ Cliente da API não está disponível")
        return
    
    api_client = st.session_state.api_client
    
    # Verifica se deve mostrar página de detalhes
    if st.session_state.get("page_mode") == "upload_details":
        upload_id = st.session_state.get("selected_upload_id")
        if upload_id:
            render_upload_details_page(api_client, upload_id)
            return
        else:
            # Se não há upload_id, volta para página principal
            st.session_state.page_mode = "upload"
    
    # Inicializa componente de notificações
    notification_component = RealTimeNotificationComponent(api_client)
    notification_component.initialize_notifications()
    
    # Header customizado
    if hasattr(st.session_state, 'theme_manager'):
        theme = st.session_state.theme_manager
        theme.create_custom_header(
            "Upload de Arquivos",
            "Envie arquivos de dados e acompanhe o processamento"
        )
    else:
        st.title("📤 Upload de Arquivos")
    
    # Painel de notificações (sempre visível se houver notificações)
    notification_component.render_notification_panel()
    
    # Status de uploads ativos
    notification_component.render_active_uploads_status()
    
    # Tabs para organizar upload e histórico
    tab1, tab2 = st.tabs(["📤 Novo Upload", "📋 Histórico"])
    
    with tab1:
        # Interface de upload
        upload_component = FileUploadComponent(api_client)
        upload_result = upload_component.render()
        
        # Se houve upload bem-sucedido, adiciona ao monitoramento
        if upload_result and upload_result.get("success"):
            upload_id = upload_result.get("upload_id")
            if upload_id:
                notification_component.add_upload_to_monitoring(upload_id)
                st.success("🔔 Upload adicionado ao monitoramento em tempo real!")
            
            st.balloons()  # Celebração visual
            
            # Botão para ir ao histórico
            if st.button("📋 Ver no Histórico", type="secondary"):
                # Força atualização da página para mostrar no histórico
                st.rerun()
    
    with tab2:
        # Histórico de uploads
        history_component = UploadHistoryComponent(api_client)
        history_component.render()
    
    # Auto-refresh da página para polling (apenas se há uploads ativos)
    if st.session_state.get("active_uploads"):
        # Usa um placeholder invisível para forçar refresh periódico
        time.sleep(0.1)  # Pequena pausa para não sobrecarregar
        st.rerun()


class RealTimeNotificationComponent:
    """Componente para notificações em tempo real de uploads."""
    
    def __init__(self, api_client: APIClient):
        """
        Inicializa o componente de notificações.
        
        Args:
            api_client: Cliente da API para comunicação
        """
        self.api_client = api_client
        self.polling_interval = 5  # segundos
        self.max_notifications = 10
    
    def initialize_notifications(self) -> None:
        """Inicializa o sistema de notificações na sessão."""
        if "notifications" not in st.session_state:
            st.session_state.notifications = []
        
        if "active_uploads" not in st.session_state:
            st.session_state.active_uploads = set()
        
        if "last_notification_check" not in st.session_state:
            st.session_state.last_notification_check = datetime.now()
    
    def add_upload_to_monitoring(self, upload_id: str) -> None:
        """
        Adiciona um upload para monitoramento em tempo real.
        
        Args:
            upload_id: ID do upload para monitorar
        """
        self.initialize_notifications()
        st.session_state.active_uploads.add(upload_id)
    
    def check_for_updates(self) -> None:
        """Verifica atualizações nos uploads ativos."""
        self.initialize_notifications()
        
        # Verifica se já passou tempo suficiente desde a última verificação
        now = datetime.now()
        if (now - st.session_state.last_notification_check).seconds < self.polling_interval:
            return
        
        st.session_state.last_notification_check = now
        
        # Verifica cada upload ativo
        completed_uploads = set()
        
        for upload_id in st.session_state.active_uploads.copy():
            try:
                status_data, success = self.api_client.get_upload_status(upload_id)
                
                if success and status_data:
                    status = status_data.get("status")
                    filename = status_data.get("filename", "Arquivo desconhecido")
                    
                    # Verifica se houve mudança de status
                    if status in ["completed", "failed"]:
                        self._add_notification(upload_id, status, filename, status_data)
                        completed_uploads.add(upload_id)
                    
                    elif status == "processing":
                        # Notificação de progresso se disponível
                        progress = status_data.get("progress_percentage", 0)
                        # Verificar se progress não é None antes da comparação
                        if progress is not None and progress > 0 and progress % 25 == 0:  # Notifica a cada 25%
                            self._add_progress_notification(upload_id, filename, progress)
                            
            except Exception as e:
                # Remove upload com erro do monitoramento
                completed_uploads.add(upload_id)
                self._add_error_notification(upload_id, str(e))
        
        # Remove uploads concluídos do monitoramento
        st.session_state.active_uploads -= completed_uploads
    
    def _add_notification(self, upload_id: str, status: str, filename: str, status_data: Dict) -> None:
        """
        Adiciona uma notificação de status.
        
        Args:
            upload_id: ID do upload
            status: Status atual
            filename: Nome do arquivo
            status_data: Dados completos do status
        """
        notification = {
            "id": f"notif_{upload_id}_{int(time.time())}",
            "upload_id": upload_id,
            "type": "status_change",
            "status": status,
            "filename": filename,
            "timestamp": datetime.now(),
            "message": self._get_status_message(status, filename, status_data),
            "icon": self._get_status_icon(status),
            "color": self._get_status_color(status)
        }
        
        st.session_state.notifications.insert(0, notification)
        self._trim_notifications()
    
    def _add_progress_notification(self, upload_id: str, filename: str, progress: int) -> None:
        """
        Adiciona notificação de progresso.
        
        Args:
            upload_id: ID do upload
            filename: Nome do arquivo
            progress: Percentual de progresso
        """
        notification = {
            "id": f"progress_{upload_id}_{progress}",
            "upload_id": upload_id,
            "type": "progress",
            "progress": progress,
            "filename": filename,
            "timestamp": datetime.now(),
            "message": f"📊 {filename} - {progress}% processado",
            "icon": "⚙️",
            "color": "orange"
        }
        
        st.session_state.notifications.insert(0, notification)
        self._trim_notifications()
    
    def _add_error_notification(self, upload_id: str, error_message: str) -> None:
        """
        Adiciona notificação de erro.
        
        Args:
            upload_id: ID do upload
            error_message: Mensagem de erro
        """
        notification = {
            "id": f"error_{upload_id}_{int(time.time())}",
            "upload_id": upload_id,
            "type": "error",
            "timestamp": datetime.now(),
            "message": f"❌ Erro ao monitorar upload: {error_message[:100]}",
            "icon": "⚠️",
            "color": "red"
        }
        
        st.session_state.notifications.insert(0, notification)
        self._trim_notifications()
    
    def _get_status_message(self, status: str, filename: str, status_data: Dict) -> str:
        """
        Gera mensagem baseada no status.
        
        Args:
            status: Status do upload
            filename: Nome do arquivo
            status_data: Dados do status
            
        Returns:
            Mensagem formatada
        """
        if status == "completed":
            records = status_data.get("records_valid", 0)
            return f"✅ {filename} processado com sucesso! {records} registros válidos."
        
        elif status == "failed":
            error = status_data.get("error_message", "Erro desconhecido")
            return f"❌ Falha no processamento de {filename}: {error[:100]}"
        
        return f"📤 Status de {filename} alterado para {status}"
    
    def _get_status_icon(self, status: str) -> str:
        """Retorna ícone para o status."""
        icons = {
            "completed": "✅",
            "failed": "❌",
            "processing": "⚙️",
            "uploaded": "📤"
        }
        return icons.get(status, "📋")
    
    def _get_status_color(self, status: str) -> str:
        """Retorna cor para o status."""
        colors = {
            "completed": "green",
            "failed": "red",
            "processing": "orange",
            "uploaded": "blue"
        }
        return colors.get(status, "gray")
    
    def _trim_notifications(self) -> None:
        """Limita o número de notificações armazenadas."""
        if len(st.session_state.notifications) > self.max_notifications:
            st.session_state.notifications = st.session_state.notifications[:self.max_notifications]
    
    def render_notification_panel(self) -> None:
        """Renderiza painel de notificações."""
        self.check_for_updates()
        
        if not st.session_state.get("notifications", []):
            return
        
        # Painel de notificações
        with st.container():
            st.markdown("### 🔔 Notificações Recentes")
            
            # Controles do painel
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                show_all = st.checkbox("Mostrar todas as notificações", value=False)
            
            with col2:
                if st.button("🔄 Verificar Agora", help="Força verificação de atualizações"):
                    st.session_state.last_notification_check = datetime.now() - timedelta(seconds=self.polling_interval)
                    st.rerun()
            
            with col3:
                if st.button("🗑️ Limpar", help="Remove todas as notificações"):
                    st.session_state.notifications = []
                    st.rerun()
            
            # Lista de notificações
            notifications_to_show = st.session_state.notifications if show_all else st.session_state.notifications[:5]
            
            for notification in notifications_to_show:
                self._render_notification_item(notification)
    
    def _render_notification_item(self, notification: Dict) -> None:
        """
        Renderiza um item de notificação.
        
        Args:
            notification: Dados da notificação
        """
        # Calcula tempo relativo
        time_diff = datetime.now() - notification["timestamp"]
        if time_diff.seconds < 60:
            time_str = f"{time_diff.seconds}s atrás"
        elif time_diff.seconds < 3600:
            time_str = f"{time_diff.seconds // 60}m atrás"
        else:
            time_str = notification["timestamp"].strftime("%H:%M")
        
        # Container da notificação
        with st.container():
            col1, col2 = st.columns([4, 1])
            
            with col1:
                # Mensagem principal
                st.markdown(f"**{notification['icon']} {notification['message']}**")
                
                # Barra de progresso para notificações de progresso
                if notification.get("type") == "progress":
                    progress = notification.get("progress", 0)
                    st.progress(progress / 100)
            
            with col2:
                st.caption(time_str)
            
            st.markdown("---")
    
    def render_active_uploads_status(self) -> None:
        """Renderiza status dos uploads ativos."""
        self.initialize_notifications()
        
        if not st.session_state.active_uploads:
            return
        
        st.markdown("### ⚙️ Uploads em Processamento")
        
        for upload_id in list(st.session_state.active_uploads):
            try:
                status_data, success = self.api_client.get_upload_status(upload_id)
                
                if success and status_data:
                    self._render_active_upload_card(upload_id, status_data)
                else:
                    # Remove upload que não conseguimos consultar
                    st.session_state.active_uploads.discard(upload_id)
                    
            except Exception:
                # Remove upload com erro
                st.session_state.active_uploads.discard(upload_id)
    
    def _render_active_upload_card(self, upload_id: str, status_data: Dict) -> None:
        """
        Renderiza card de upload ativo.
        
        Args:
            upload_id: ID do upload
            status_data: Dados do status
        """
        filename = status_data.get("filename", "Arquivo desconhecido")
        status = status_data.get("status", "unknown")
        progress = status_data.get("progress_percentage", 0)
        
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.markdown(f"**📁 {filename}**")
                if progress > 0:
                    st.progress(progress / 100)
                    st.caption(f"Progresso: {progress}%")
            
            with col2:
                status_icon = self._get_status_icon(status)
                st.markdown(f"**{status_icon} {status.title()}**")
            
            with col3:
                if st.button("❌", key=f"stop_{upload_id}", help="Parar monitoramento"):
                    st.session_state.active_uploads.discard(upload_id)
                    st.rerun()
            
            st.markdown("---")
    
    def render_sidebar_notifications(self) -> None:
        """Renderiza notificações compactas na sidebar."""
        self.check_for_updates()
        
        # Contador de uploads ativos
        active_count = len(st.session_state.get("active_uploads", set()))
        
        if active_count > 0:
            st.sidebar.markdown("---")
            st.sidebar.markdown(f"### ⚙️ Uploads Ativos ({active_count})")
            
            # Mostra apenas os uploads em processamento
            for upload_id in list(st.session_state.active_uploads):
                try:
                    status_data, success = self.api_client.get_upload_status(upload_id)
                    
                    if success and status_data:
                        filename = status_data.get("filename", "Arquivo")[:20] + "..."
                        progress = status_data.get("progress_percentage", 0)
                        status = status_data.get("status", "unknown")
                        
                        # Card compacto na sidebar
                        st.sidebar.markdown(f"**📁 {filename}**")
                        if progress > 0:
                            st.sidebar.progress(progress / 100)
                            st.sidebar.caption(f"{status.title()} - {progress}%")
                        else:
                            st.sidebar.caption(f"Status: {status.title()}")
                        
                except Exception:
                    continue
        
        # Notificações recentes (máximo 3 na sidebar)
        recent_notifications = st.session_state.get("notifications", [])[:3]
        
        if recent_notifications:
            st.sidebar.markdown("---")
            st.sidebar.markdown("### 🔔 Últimas Notificações")
            
            for notification in recent_notifications:
                # Versão compacta da notificação
                icon = notification.get("icon", "📋")
                message = notification.get("message", "")[:50] + "..."
                
                # Cor baseada no tipo
                if notification.get("type") == "error" or notification.get("status") == "failed":
                    st.sidebar.error(f"{icon} {message}")
                elif notification.get("status") == "completed":
                    st.sidebar.success(f"{icon} {message}")
                else:
                    st.sidebar.info(f"{icon} {message}")
    
    def get_notification_summary(self) -> Dict[str, int]:
        """
        Retorna resumo das notificações para exibição.
        
        Returns:
            Dict com contadores de notificações
        """
        notifications = st.session_state.get("notifications", [])
        
        summary = {
            "total": len(notifications),
            "completed": 0,
            "failed": 0,
            "progress": 0,
            "active_uploads": len(st.session_state.get("active_uploads", set()))
        }
        
        for notification in notifications:
            if notification.get("status") == "completed":
                summary["completed"] += 1
            elif notification.get("status") == "failed":
                summary["failed"] += 1
            elif notification.get("type") == "progress":
                summary["progress"] += 1
        
        return summary


class UploadDetailsPage:
    """Página dedicada para detalhes avançados de upload com logs e estatísticas."""
    
    def __init__(self, api_client: APIClient):
        """
        Inicializa a página de detalhes.
        
        Args:
            api_client: Cliente da API para comunicação
        """
        self.api_client = api_client
    
    def render(self, upload_id: str) -> None:
        """
        Renderiza página completa de detalhes do upload.
        
        Args:
            upload_id: ID do upload para exibir detalhes
        """
        # Header customizado
        if hasattr(st.session_state, 'theme_manager'):
            theme = st.session_state.theme_manager
            theme.create_custom_header(
                f"Detalhes do Upload",
                f"Análise completa do processamento • ID: {upload_id}"
            )
        else:
            st.title(f"📋 Detalhes do Upload")
            st.caption(f"ID: {upload_id}")
        
        # Busca dados do upload
        try:
            details, success = self.api_client.get_upload_status(upload_id)
            
            if not success or not details:
                st.error("❌ Upload não encontrado ou erro ao carregar dados")
                if st.button("⬅️ Voltar ao Histórico"):
                    st.session_state.page_mode = "upload"
                    st.rerun()
                return
            
            # Botão voltar
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("⬅️ Voltar", type="secondary"):
                    st.session_state.page_mode = "upload"
                    st.rerun()
            
            # Tabs para organizar informações
            tab1, tab2, tab3, tab4 = st.tabs([
                "📊 Visão Geral", 
                "📈 Métricas Detalhadas", 
                "📝 Logs de Processamento",
                "🔍 Análise Técnica"
            ])
            
            with tab1:
                self._render_overview(details)
            
            with tab2:
                self._render_detailed_metrics(details)
            
            with tab3:
                self._render_processing_logs(upload_id, details)
            
            with tab4:
                self._render_technical_analysis(details)
                
        except Exception as e:
            st.error(f"❌ Erro ao carregar detalhes: {str(e)}")
    
    def _render_overview(self, details: Dict) -> None:
        """Renderiza visão geral do upload."""
        st.subheader("📋 Informações Gerais")
        
        # Status principal
        status = details.get("status", "unknown")
        status_icons = {
            "uploaded": "📤",
            "processing": "⚙️", 
            "completed": "✅",
            "failed": "❌"
        }
        
        status_colors = {
            "uploaded": "blue",
            "processing": "orange",
            "completed": "green", 
            "failed": "red"
        }
        
        icon = status_icons.get(status, "❓")
        color = status_colors.get(status, "gray")
        
        st.markdown(f"### {icon} Status: **{status.title()}**")
        
        # Informações principais em cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "📁 Arquivo",
                details.get("filename", "N/A"),
                help="Nome do arquivo original"
            )
        
        with col2:
            file_size = details.get("file_size", 0)
            size_mb = file_size / (1024 * 1024) if file_size else 0
            st.metric(
                "📏 Tamanho", 
                f"{size_mb:.2f} MB",
                help="Tamanho do arquivo em megabytes"
            )
        
        with col3:
            progress = details.get("progress_percentage", 0)
            st.metric(
                "📊 Progresso",
                f"{progress}%",
                help="Percentual de conclusão do processamento"
            )
        
        with col4:
            processing_time = details.get("processing_time_seconds")
            if processing_time:
                st.metric(
                    "⏱️ Tempo",
                    f"{processing_time:.2f}s",
                    help="Tempo total de processamento"
                )
            else:
                st.metric("⏱️ Tempo", "N/A", help="Processamento não iniciado ou em andamento")
        
        # Timeline do processamento
        st.subheader("⏰ Timeline do Processamento")
        
        timeline_data = []
        
        # Upload
        created_at = details.get("created_at")
        if created_at:
            timeline_data.append(("📤 Upload", created_at, "Arquivo enviado com sucesso"))
        
        # Início do processamento
        started_at = details.get("started_at")
        if started_at:
            timeline_data.append(("⚙️ Início", started_at, "Processamento iniciado"))
        
        # Conclusão
        completed_at = details.get("completed_at")
        if completed_at:
            if status == "completed":
                timeline_data.append(("✅ Conclusão", completed_at, "Processamento concluído com sucesso"))
            elif status == "failed":
                timeline_data.append(("❌ Falha", completed_at, "Processamento falhou"))
        
        # Renderizar timeline
        for i, (event, timestamp, description) in enumerate(timeline_data):
            col1, col2, col3 = st.columns([1, 2, 3])
            with col1:
                st.write(event)
            with col2:
                st.write(timestamp)
            with col3:
                st.write(description)
            
            if i < len(timeline_data) - 1:
                st.write("↓")
        
        # Erro se houver
        error_message = details.get("error_message")
        if error_message:
            st.subheader("💥 Erro Encontrado")
            st.error(error_message)
    
    def _render_detailed_metrics(self, details: Dict) -> None:
        """Renderiza métricas detalhadas."""
        st.subheader("📈 Métricas de Processamento")
        
        # Métricas de registros
        records_processed = details.get("records_processed", 0)
        records_valid = details.get("records_valid", 0)
        records_invalid = details.get("records_invalid", 0)
        
        if records_processed > 0:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "📊 Total Processado",
                    f"{records_processed:,}",
                    help="Número total de registros processados"
                )
            
            with col2:
                valid_percentage = (records_valid / records_processed * 100) if records_processed > 0 else 0
                st.metric(
                    "✅ Registros Válidos",
                    f"{records_valid:,}",
                    delta=f"{valid_percentage:.1f}%",
                    help="Registros que passaram na validação"
                )
            
            with col3:
                invalid_percentage = (records_invalid / records_processed * 100) if records_processed > 0 else 0
                st.metric(
                    "❌ Registros Inválidos",
                    f"{records_invalid:,}",
                    delta=f"{invalid_percentage:.1f}%",
                    delta_color="inverse",
                    help="Registros que falharam na validação"
                )
            
            # Gráfico de distribuição
            st.subheader("📊 Distribuição de Registros")
            
            if records_valid > 0 or records_invalid > 0:
                import pandas as pd
                
                chart_data = pd.DataFrame({
                    'Tipo': ['Válidos', 'Inválidos'],
                    'Quantidade': [records_valid, records_invalid],
                    'Percentual': [valid_percentage, invalid_percentage]
                })
                
                st.bar_chart(chart_data.set_index('Tipo')['Quantidade'])
                
                # Tabela detalhada
                st.dataframe(
                    chart_data,
                    use_container_width=True,
                    hide_index=True
                )
        else:
            st.info("📭 Nenhum registro foi processado ainda")
        
        # Métricas de performance
        st.subheader("⚡ Métricas de Performance")
        
        processing_time = details.get("processing_time_seconds")
        if processing_time and records_processed > 0:
            records_per_second = records_processed / processing_time
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    "🚀 Registros/segundo",
                    f"{records_per_second:.2f}",
                    help="Taxa de processamento"
                )
            
            with col2:
                file_size = details.get("file_size", 0)
                if file_size > 0:
                    mb_per_second = (file_size / (1024 * 1024)) / processing_time
                    st.metric(
                        "📈 MB/segundo",
                        f"{mb_per_second:.2f}",
                        help="Taxa de processamento de dados"
                    )
    
    def _render_processing_logs(self, upload_id: str, details: Dict) -> None:
        """Renderiza logs de processamento."""
        st.subheader("📝 Logs de Processamento")
        
        # Simulação de logs (em implementação real, buscaria do sistema de logs)
        logs = self._get_upload_logs(upload_id, details)
        
        # Filtros de logs
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            log_level = st.selectbox(
                "Nível de Log:",
                ["TODOS", "INFO", "WARNING", "ERROR", "DEBUG"],
                help="Filtrar logs por nível"
            )
        
        with col2:
            show_timestamps = st.checkbox("Mostrar timestamps", value=True)
        
        with col3:
            if st.button("🔄 Atualizar"):
                st.rerun()
        
        # Exibir logs
        if logs:
            log_container = st.container()
            
            with log_container:
                for log_entry in logs:
                    if log_level != "TODOS" and log_entry["level"] != log_level:
                        continue
                    
                    # Cor baseada no nível
                    if log_entry["level"] == "ERROR":
                        st.error(self._format_log_entry(log_entry, show_timestamps))
                    elif log_entry["level"] == "WARNING":
                        st.warning(self._format_log_entry(log_entry, show_timestamps))
                    elif log_entry["level"] == "INFO":
                        st.info(self._format_log_entry(log_entry, show_timestamps))
                    else:
                        st.text(self._format_log_entry(log_entry, show_timestamps))
        else:
            st.info("📭 Nenhum log disponível para este upload")
    
    def _render_technical_analysis(self, details: Dict) -> None:
        """Renderiza análise técnica avançada."""
        st.subheader("🔍 Análise Técnica")
        
        # Informações do arquivo
        st.markdown("**📄 Detalhes do Arquivo:**")
        
        file_info = {
            "Nome Original": details.get("filename", "N/A"),
            "Tamanho": f"{details.get('file_size', 0) / (1024*1024):.2f} MB",
            "Tipo Detectado": details.get("file_type", "N/A"),
            "Status": details.get("status", "N/A")
        }
        
        for key, value in file_info.items():
            st.write(f"• **{key}:** {value}")
        
        # Timestamps detalhados
        st.markdown("**⏰ Timestamps Detalhados:**")
        
        timestamps = {
            "Upload": details.get("created_at", "N/A"),
            "Início do Processamento": details.get("started_at", "N/A"),
            "Conclusão": details.get("completed_at", "N/A")
        }
        
        for key, value in timestamps.items():
            st.write(f"• **{key}:** {value}")
        
        # Cálculos de performance
        processing_time = details.get("processing_time_seconds")
        if processing_time:
            st.markdown("**⚡ Análise de Performance:**")
            
            records_processed = details.get("records_processed", 0)
            file_size = details.get("file_size", 0)
            
            performance_metrics = {
                "Tempo Total": f"{processing_time:.3f} segundos",
                "Taxa de Registros": f"{records_processed / processing_time:.2f} registros/segundo" if records_processed > 0 else "N/A",
                "Taxa de Dados": f"{(file_size / (1024*1024)) / processing_time:.2f} MB/segundo" if file_size > 0 else "N/A",
                "Eficiência": self._calculate_efficiency(details)
            }
            
            for key, value in performance_metrics.items():
                st.write(f"• **{key}:** {value}")
        
        # Dados brutos (JSON)
        with st.expander("🔧 Dados Brutos (JSON)", expanded=False):
            st.json(details)
    
    def _get_upload_logs(self, upload_id: str, details: Dict) -> List[Dict]:
        """
        Simula busca de logs de upload.
        Em implementação real, buscaria do sistema de logs.
        """
        # Simulação de logs baseada no status
        logs = []
        
        status = details.get("status", "unknown")
        filename = details.get("filename", "arquivo.csv")
        
        # Log de upload
        logs.append({
            "timestamp": details.get("created_at", "2024-01-01T00:00:00"),
            "level": "INFO",
            "message": f"Upload iniciado para arquivo: {filename}",
            "module": "upload_endpoint"
        })
        
        # Log de validação
        logs.append({
            "timestamp": details.get("created_at", "2024-01-01T00:00:01"),
            "level": "INFO", 
            "message": f"Arquivo validado com sucesso: {filename}",
            "module": "data_processor"
        })
        
        if details.get("started_at"):
            # Log de início de processamento
            logs.append({
                "timestamp": details.get("started_at"),
                "level": "INFO",
                "message": f"Iniciando processamento: {upload_id}",
                "module": "upload_monitor"
            })
            
            # Logs de progresso
            records_processed = details.get("records_processed", 0)
            if records_processed > 0:
                logs.append({
                    "timestamp": details.get("started_at"),
                    "level": "INFO",
                    "message": f"Processando registros... Total encontrado: {records_processed}",
                    "module": "data_processor"
                })
        
        if status == "completed":
            logs.append({
                "timestamp": details.get("completed_at"),
                "level": "INFO",
                "message": f"Upload processado com sucesso: {upload_id} - {details.get('records_valid', 0)} registros válidos",
                "module": "upload_monitor"
            })
        elif status == "failed":
            logs.append({
                "timestamp": details.get("completed_at"),
                "level": "ERROR", 
                "message": f"Erro ao processar upload {upload_id}: {details.get('error_message', 'Erro desconhecido')}",
                "module": "upload_monitor"
            })
        
        return logs
    
    def _format_log_entry(self, log_entry: Dict, show_timestamps: bool) -> str:
        """Formata entrada de log para exibição."""
        timestamp = log_entry.get("timestamp", "")
        level = log_entry.get("level", "INFO")
        message = log_entry.get("message", "")
        module = log_entry.get("module", "")
        
        if show_timestamps:
            return f"[{timestamp}] {level} - {module} - {message}"
        else:
            return f"{level} - {module} - {message}"
    
    def _calculate_efficiency(self, details: Dict) -> str:
        """Calcula eficiência do processamento."""
        records_processed = details.get("records_processed", 0)
        records_valid = details.get("records_valid", 0)
        processing_time = details.get("processing_time_seconds", 0)
        
        if records_processed == 0 or processing_time == 0:
            return "N/A"
        
        # Eficiência baseada em registros válidos por segundo
        efficiency = records_valid / processing_time
        
        if efficiency > 100:
            return "Excelente"
        elif efficiency > 50:
            return "Boa"
        elif efficiency > 20:
            return "Regular"
        else:
            return "Baixa"


def render_upload_details_page(api_client: APIClient, upload_id: str) -> None:
    """
    Renderiza página dedicada de detalhes de upload.
    
    Args:
        api_client: Cliente da API
        upload_id: ID do upload para exibir
    """
    details_page = UploadDetailsPage(api_client)
    details_page.render(upload_id) 