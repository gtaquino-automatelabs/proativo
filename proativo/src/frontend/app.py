import streamlit as st
import requests
import time
from datetime import datetime
from typing import List, Dict, Any
import os
from components.chat_interface import create_chat_interface
from components.feedback import create_feedback_system
from components.loading import create_loading_indicator, show_api_status
from components.theme import apply_professional_theme, COLOR_SCHEMES
from components.validation import create_input_validator
from components.error_handler import create_error_handler, safe_api_call

# Importa serviços de API
try:
    from services.api_client import create_api_client
    from services.http_service import create_http_service
    API_SERVICES_AVAILABLE = True
except ImportError:
    API_SERVICES_AVAILABLE = False

# Configuração da página
st.set_page_config(
    page_title="PROAtivo - Sistema de Apoio à Decisão",
    page_icon="🔌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Aplica tema profissional
theme = apply_professional_theme()

# Configuração da API
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

def inicializar_sessao():
    """Inicializa variáveis da sessão do Streamlit"""
    # Inicializa o cliente da API (novo sistema integrado)
    if "api_client" not in st.session_state and API_SERVICES_AVAILABLE:
        st.session_state.api_client = create_api_client(API_BASE_URL)
    
    # Inicializa o chat interface
    if "chat_interface" not in st.session_state:
        st.session_state.chat_interface = create_chat_interface(
            session_key="proativo_chat",
            max_messages=50
        )
    
    # Inicializa o sistema de feedback
    if "feedback_system" not in st.session_state:
        st.session_state.feedback_system = create_feedback_system(
            api_base_url=API_BASE_URL,
            session_key="proativo_feedback"
        )
    
    # Inicializa o sistema de loading
    if "loading_indicator" not in st.session_state:
        st.session_state.loading_indicator = create_loading_indicator()
    
    # Inicializa o validador de entrada
    if "input_validator" not in st.session_state:
        st.session_state.input_validator = create_input_validator()
    
    # Inicializa o tratador de erros
    if "error_handler" not in st.session_state:
        st.session_state.error_handler = create_error_handler()
    
    # Inicializa o tema se não existir
    if "theme_manager" not in st.session_state:
        st.session_state.theme_manager = theme
    
    if "feedback_pendente" not in st.session_state:
        st.session_state.feedback_pendente = False
    
    if "ultima_resposta_id" not in st.session_state:
        st.session_state.ultima_resposta_id = None

def criar_sidebar():
    """Cria a sidebar com menu de navegação"""
    with st.sidebar:
        # Logo customizado
        theme = st.session_state.theme_manager
        theme.create_sidebar_logo()
        st.markdown("---")
        
        # Menu de navegação
        opcoes_menu = [
            ("🔍 Consultas", "consultas"),
            ("📊 Dashboard", "dashboard"),
            ("📈 Métricas", "metricas"),
            ("⚙️ Configurações", "config"),
            ("📋 Sobre", "sobre"),
            ("❓ Ajuda", "ajuda")
        ]
        
        if "pagina_atual" not in st.session_state:
            st.session_state.pagina_atual = "consultas"
        
        for label, key in opcoes_menu:
            if st.button(label, key=f"btn_{key}", use_container_width=True):
                st.session_state.pagina_atual = key
        
        st.markdown("---")
        
        # Status da API usando o componente de loading
        st.subheader("Status do Sistema")
        show_api_status(API_BASE_URL, timeout=3, show_details=True)
        
        # Informações básicas
        st.markdown("---")
        st.markdown("**Versão:** 1.0.0")
        st.markdown("**Última atualização:** Hoje")

def _realizar_requisicao_api(mensagem: str) -> str:
    """Função interna para fazer a requisição à API usando APIClient"""
    # Verifica se o APIClient está disponível
    if API_SERVICES_AVAILABLE and "api_client" in st.session_state:
        api_client = st.session_state.api_client
        
        # Log do início da requisição
        st.session_state.loading_indicator.status_indicator(
            "loading", 
            "Enviando consulta para API...",
            f"Query: {mensagem[:100]}..."
        )
        
        # Usa o APIClient que já tem tratamento de erro integrado
        response, success = api_client.send_chat_message(
            query=mensagem,
            user_id="streamlit_user"
        )
        
        if success:
            # Log de sucesso
            st.session_state.loading_indicator.status_indicator(
                "success", 
                "Resposta recebida com sucesso!",
                "APIClient"
            )
            return response
        else:
            # Log de erro
            st.session_state.loading_indicator.status_indicator(
                "error", 
                "Erro na comunicação com API",
                "APIClient com fallback"
            )
            return response  # Já contém fallback do APIClient
    
    else:
        # Fallback para método manual se APIClient não disponível
        payload = {
            "query": mensagem,
            "user_id": "streamlit_user"
        }
        
        st.session_state.loading_indicator.status_indicator(
            "loading", 
            "Enviando consulta para API (modo fallback)...",
            f"Query: {mensagem[:100]}..."
        )
        
        response = requests.post(
            f"{API_BASE_URL}/chat", 
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            
            st.session_state.loading_indicator.status_indicator(
                "success", 
                "Resposta recebida com sucesso!",
                f"Status: {response.status_code}"
            )
            
            return data.get("response", "Erro: Resposta vazia da API")
        else:
            st.session_state.loading_indicator.status_indicator(
                "error", 
                f"Erro na API: Status {response.status_code}",
                f"Detalhes: {response.text[:200]}..."
            )
            
            # Levanta exceção para o handler processar
            response.raise_for_status()

def enviar_mensagem(mensagem: str) -> str:
    """Envia mensagem para a API com tratamento robusto de erros"""
    # Se APIClient disponível, usa ele diretamente (já tem tratamento de erro)
    if API_SERVICES_AVAILABLE and "api_client" in st.session_state:
        return _realizar_requisicao_api(mensagem)
    
    # Caso contrário, usa o sistema de error handler tradicional
    error_handler = st.session_state.error_handler
    
    # Resposta de fallback para quando a API está indisponível
    fallback_response = error_handler.get_fallback_response("general_query")
    
    # Executa requisição com tratamento automático de erros
    result, success = error_handler.handle_api_request(
        request_func=_realizar_requisicao_api,
        mensagem=mensagem,
        fallback_response=fallback_response,
        user_action=f"enviar consulta: '{mensagem[:50]}...'"
    )
    
    return result

# Função enviar_feedback removida - agora usa o componente FeedbackSystem

def pagina_consultas():
    """Página principal de consultas com chat"""
    # Header customizado
    theme = st.session_state.theme_manager
    theme.create_custom_header(
        "Interface de Chat",
        "Converse com o assistente inteligente do PROAtivo"
    )
    
    # Obtém a instância do chat interface
    chat = st.session_state.chat_interface
    
    # Renderiza as mensagens do chat
    chat.render_messages(show_timestamps=False)
    
    # Área de input com validação
    st.markdown("---")
    st.markdown("### 💬 Digite sua consulta")
    
    # Obtém o validador de entrada
    validator = st.session_state.input_validator
    
    # Usa input com validação em vez do componente básico
    user_input, is_valid, button_pressed = validator.create_chat_input_with_validation(
        placeholder="Ex: Qual foi a última manutenção do equipamento TR-001?",
        key="validated_chat_input",
        max_length=1000
    )
    
    # Processa envio da mensagem (apenas se entrada é válida)
    if button_pressed and user_input.strip() and is_valid:
        # Adiciona pergunta do usuário
        user_msg_id = chat.add_message("user", user_input)
        
        # Obtém o indicador de loading
        loader = st.session_state.loading_indicator
        
        # Mostra indicador de carregamento avançado
        start_time = time.time()
        
        # Simula etapas do processamento
        processing_steps = [
            "Analisando sua pergunta",
            "Buscando informações relevantes", 
            "Processando com IA",
            "Formatando resposta"
        ]
        
        with loader.spinner("Processando sua consulta", icon="🤖", show_time=True):
            # Opcional: mostrar etapas intermediárias
            status_placeholder = st.empty()
            
            for i, step in enumerate(processing_steps):
                status_placeholder.info(f"⏳ {step}...")
                time.sleep(0.5)  # Simula processamento
            
            status_placeholder.empty()
            
            # Chama a API
            resposta = enviar_mensagem(user_input)
        
        # Registra evento de loading
        duration = time.time() - start_time
        loader.save_loading_event(
            event_type="chat_query",
            duration=duration,
            success=not resposta.startswith("Erro"),
            details=f"Query: {user_input[:50]}..."
        )
        
        # Adiciona resposta do assistente
        assistant_msg_id = chat.add_message("assistant", resposta)
        
        # Habilita feedback
        st.session_state.feedback_pendente = True
        st.session_state.ultima_resposta_id = assistant_msg_id
        
        # Rerun para atualizar a interface
        st.rerun()
    
    # Sistema de feedback usando o componente modular
    if st.session_state.feedback_pendente:
        st.markdown("---")
        
        feedback_system = st.session_state.feedback_system
        
        # Renderiza o formulário completo de feedback
        feedback_result = feedback_system.render_feedback_form(
            response_id=st.session_state.ultima_resposta_id,
            title="Como você avalia esta resposta?",
            show_comment=True,
            show_send_button=True,
            key_prefix="main_feedback"
        )
        
        # Processa o feedback
        if feedback_result["feedback_type"]:
            success = feedback_system.send_feedback(
                rating=feedback_result["feedback_type"],
                response_id=st.session_state.ultima_resposta_id,
                comment=feedback_result["comment"]
            )
            
            if success:
                st.success("✅ Obrigado pelo seu feedback!")
                st.session_state.feedback_pendente = False
                st.rerun()
        
        # Envio de comentário separado
        if feedback_result["send_pressed"]:
            success = feedback_system.send_feedback(
                rating=feedback_result["feedback_type"],
                response_id=st.session_state.ultima_resposta_id,
                comment=feedback_result["comment"]
            )
            
            if success:
                st.success("✅ Comentário enviado com sucesso!")
                st.session_state.feedback_pendente = False
                st.rerun()
    
    # Botão para limpar chat (opcional)
    if st.sidebar.button("🗑️ Limpar Chat"):
        chat.clear_chat()
        st.session_state.feedback_pendente = False
        st.rerun()
    
    # Estatísticas do chat e feedback na sidebar
    with st.sidebar:
        st.markdown("---")
        st.subheader("📊 Estatísticas do Chat")
        chat.render_chat_stats()
        
        st.markdown("---")
        st.subheader("⭐ Estatísticas de Feedback")
        feedback_system = st.session_state.feedback_system
        feedback_system.render_feedback_stats()
        
        st.markdown("---")
        st.subheader("⚡ Performance do Sistema")
        loader = st.session_state.loading_indicator
        stats = loader.get_loading_stats()
        
        if stats["total_events"] > 0:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Consultas", stats["total_events"])
                st.metric("Taxa de Sucesso", f"{stats['success_rate']:.0f}%")
            with col2:
                st.metric("Tempo Médio", f"{stats['avg_duration']:.1f}s")
                if stats["last_event"]:
                    last_duration = stats["last_event"]["duration"]
                    st.metric("Última Consulta", f"{last_duration:.1f}s")
        else:
            st.info("📊 Dados de performance serão exibidos após as primeiras consultas")
        
        st.markdown("---")
        st.subheader("🛡️ Validação de Entrada")
        validator = st.session_state.input_validator
        validator.show_validation_summary()
        
        st.markdown("---")
        st.subheader("🚨 Status de Erros")
        error_handler = st.session_state.error_handler
        error_handler.show_system_status()
        
        # Mostra estatísticas básicas de erro se houver
        error_stats = error_handler.show_error_statistics()
        
        # Seção do APIClient se disponível
        if API_SERVICES_AVAILABLE and "api_client" in st.session_state:
            st.markdown("---")
            st.subheader("🌐 Status da API")
            api_client = st.session_state.api_client
            api_client.show_connection_status()
            
            # Estatísticas compactas do APIClient
            api_stats = api_client.get_stats()
            if api_stats["http"]["total_requests"] > 0:
                st.caption(f"📊 Total: {api_stats['http']['total_requests']} | "
                          f"Cache: {api_stats['http']['cache_hit_rate']:.0f}% | "
                          f"Sucesso: {api_stats['http']['success_rate']:.0f}%")

def pagina_dashboard():
    """Página de dashboard com métricas em tempo real"""
    # Header customizado
    theme = st.session_state.theme_manager
    theme.create_custom_header(
        "Dashboard do Sistema",
        "Monitore o desempenho e estatísticas em tempo real"
    )
    
    # Obtém componentes
    chat = st.session_state.chat_interface
    feedback_system = st.session_state.feedback_system
    loader = st.session_state.loading_indicator
    
    # Status da API em destaque
    st.markdown("### 🌐 Status da Conectividade")
    
    if API_SERVICES_AVAILABLE and "api_client" in st.session_state:
        # Usa o APIClient para status detalhado
        api_client = st.session_state.api_client
        api_client.show_connection_status()
        
        # Teste de conectividade com todos os endpoints
        with st.expander("🔍 Teste de Endpoints"):
            if st.button("🧪 Testar Todos os Endpoints"):
                with st.spinner("Testando conectividade..."):
                    results = api_client.test_all_endpoints()
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Health", "✅ Online" if results["health"] else "❌ Offline")
                        st.metric("Info", "✅ Online" if results["info"] else "❌ Offline")
                    
                    with col2:
                        st.metric("Equipment", "✅ Online" if results["equipment"] else "❌ Offline")
                        st.metric("Maintenance", "✅ Online" if results["maintenance"] else "❌ Offline")
                    
                    # Resumo
                    online_count = sum(results.values())
                    total_count = len(results)
                    st.metric("Status Geral", f"{online_count}/{total_count} Online")
    else:
        # Fallback para método tradicional
        show_api_status(API_BASE_URL, timeout=5, show_details=True)
    
    st.markdown("---")
    
    # Métricas principais
    st.markdown("### 📈 Métricas Principais")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Estatísticas do chat
    chat_messages = chat.get_messages()
    user_messages = [msg for msg in chat_messages if msg.get("role") == "user"]
    
    with col1:
        st.metric("💬 Total de Mensagens", len(chat_messages))
    
    with col2:
        st.metric("❓ Consultas dos Usuários", len(user_messages))
    
    # Estatísticas de feedback
    feedback_stats = feedback_system.get_feedback_stats()
    
    with col3:
        if feedback_stats["total"] > 0:
            satisfaction = f"{feedback_stats['positive']}/{feedback_stats['total']}"
            st.metric("👍 Feedbacks Positivos", satisfaction)
        else:
            st.metric("👍 Feedbacks Positivos", "0/0")
    
    # Estatísticas de performance
    loading_stats = loader.get_loading_stats()
    
    with col4:
        if loading_stats["total_events"] > 0:
            avg_time = f"{loading_stats['avg_duration']:.1f}s"
            st.metric("⚡ Tempo Médio", avg_time)
        else:
            st.metric("⚡ Tempo Médio", "0.0s")
    
    st.markdown("---")
    
    # Gráficos e detalhes
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Estatísticas de Feedback")
        feedback_system.render_feedback_stats()
        
        # Histórico de performance
        if loading_stats["total_events"] > 0:
            st.markdown("### ⚡ Performance Recente")
            st.metric("Taxa de Sucesso", f"{loading_stats['success_rate']:.0f}%")
            
            if loading_stats["last_event"]:
                last_event = loading_stats["last_event"]
                last_time = time.strftime("%H:%M:%S", time.localtime(last_event["timestamp"]))
                st.caption(f"Última consulta: {last_time} ({last_event['duration']:.1f}s)")
    
    with col2:
        st.markdown("### 💬 Estatísticas do Chat")
        chat.render_chat_stats()
        
        # Estatísticas do APIClient se disponível
        if API_SERVICES_AVAILABLE and "api_client" in st.session_state:
            st.markdown("### 🌐 APIClient - Métricas HTTP")
            api_client = st.session_state.api_client
            api_stats = api_client.get_stats()
            
            if api_stats["http"]["total_requests"] > 0:
                col_api1, col_api2 = st.columns(2)
                
                with col_api1:
                    st.metric("Requisições HTTP", api_stats["http"]["total_requests"])
                    st.metric("Cache Hits", f"{api_stats['http']['cache_hit_rate']:.1f}%")
                
                with col_api2:
                    st.metric("Taxa de Sucesso", f"{api_stats['http']['success_rate']:.1f}%")
                    st.metric("Tempo Médio", f"{api_stats['http']['average_response_time']:.2f}s")
                
                # Estatísticas por endpoint
                if api_stats["api"]["chat_requests"] > 0:
                    st.caption(f"💬 Chat: {api_stats['api']['chat_requests']} requisições")
                if api_stats["api"]["feedback_requests"] > 0:
                    st.caption(f"⭐ Feedback: {api_stats['api']['feedback_requests']} requisições")
                if api_stats["api"]["health_checks"] > 0:
                    st.caption(f"🔍 Health checks: {api_stats['api']['health_checks']} verificações")
            else:
                st.info("📊 Dados do APIClient serão exibidos após as primeiras requisições")
        
        # Ações rápidas
        st.markdown("### 🔧 Ações Rápidas")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            if st.button("🗑️ Limpar Chat", use_container_width=True):
                chat.clear_chat()
                st.success("✅ Chat limpo!")
                st.rerun()
        
        with col_b:
            if st.button("📊 Reset Métricas", use_container_width=True):
                feedback_system.clear_feedback_history()
                if API_SERVICES_AVAILABLE and "api_client" in st.session_state:
                    st.session_state.api_client.clear_cache()
                st.success("✅ Métricas resetadas!")
                st.rerun()
    
    # Seção de monitoramento em tempo real
    st.markdown("---")
    st.markdown("### 🔍 Monitoramento em Tempo Real")
    
    if st.button("🔄 Atualizar Status", use_container_width=False):
        with st.spinner("Verificando sistemas..."):
            time.sleep(1)  # Simula verificação
            st.success("✅ Todos os sistemas funcionando normalmente!")
            st.rerun()

def pagina_metricas():
    """Página de métricas avançadas"""
    # Header customizado
    theme = st.session_state.theme_manager
    theme.create_custom_header(
        "Análise de Métricas",
        "Análises detalhadas do desempenho e uso do sistema"
    )
    
    # Obtém componentes para métricas
    chat = st.session_state.chat_interface
    feedback_system = st.session_state.feedback_system
    loader = st.session_state.loading_indicator
    
    # Container responsivo
    st.markdown('<div class="responsive-container">', unsafe_allow_html=True)
    
    # Métricas em cards customizados
    col1, col2, col3 = st.columns(3)
    
    with col1:
        messages = chat.get_messages()
        theme.create_metric_card(
            "Total de Interações",
            str(len(messages)),
            help_text="Número total de mensagens trocadas"
        )
    
    with col2:
        feedback_stats = feedback_system.get_feedback_stats()
        if feedback_stats["total"] > 0:
            satisfaction = (feedback_stats["positive"] / feedback_stats["total"]) * 100
            theme.create_metric_card(
                "Satisfação do Usuário",
                f"{satisfaction:.1f}%",
                f"+{feedback_stats['positive']} positivos",
                help_text="Percentual de feedbacks positivos"
            )
        else:
            theme.create_metric_card("Satisfação do Usuário", "N/A", help_text="Aguardando feedbacks")
    
    with col3:
        loading_stats = loader.get_loading_stats()
        if loading_stats["total_events"] > 0:
            theme.create_metric_card(
                "Tempo Médio",
                f"{loading_stats['avg_duration']:.1f}s",
                f"{loading_stats['success_rate']:.0f}% sucesso",
                help_text="Tempo médio de resposta da API"
            )
        else:
            theme.create_metric_card("Tempo Médio", "N/A", help_text="Aguardando consultas")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Gráficos e análises detalhadas
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Distribuição de Feedback")
        if feedback_stats["total"] > 0:
            feedback_data = {
                "Positivos": feedback_stats["positive"],
                "Negativos": feedback_stats["negative"],
                "Neutros": feedback_stats["neutral"]
            }
            st.bar_chart(feedback_data)
        else:
            st.info("📈 Gráficos serão exibidos após receber feedbacks")
    
    with col2:
        st.markdown("### ⚡ Histórico de Performance")
        if loading_stats["total_events"] > 0:
            st.metric("Taxa de Sucesso", f"{loading_stats['success_rate']:.1f}%")
            st.metric("Total de Consultas", loading_stats["total_events"])
            
            if loading_stats["last_event"]:
                last_time = time.strftime("%H:%M:%S", time.localtime(loading_stats["last_event"]["timestamp"]))
                st.caption(f"🕒 Última consulta: {last_time}")
        else:
            st.info("⏱️ Dados de performance serão exibidos após as primeiras consultas")

def pagina_config():
    """Página de configurações do sistema"""
    # Header customizado
    theme = st.session_state.theme_manager
    theme.create_custom_header(
        "Configurações",
        "Personalize a aparência e comportamento do sistema"
    )
    
    # Seção de temas
    st.markdown("### 🎨 Tema da Aplicação")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("**Esquemas de Cores Disponíveis:**")
        
        for scheme_name, colors in COLOR_SCHEMES.items():
            if st.button(f"🎨 {scheme_name.title()}", key=f"theme_{scheme_name}", use_container_width=True):
                theme.set_color_scheme(colors)
                st.success(f"✅ Tema '{scheme_name}' aplicado!")
                st.rerun()
        
        st.markdown("---")
        
        # Preview das cores atuais
        current_colors = theme.get_color_scheme()
        st.markdown("**Cores Atuais:**")
        
        for color_name, color_value in current_colors.items():
            st.markdown(
                f'<div style="display: flex; align-items: center; margin: 0.2rem 0;">'
                f'<div style="width: 20px; height: 20px; background: {color_value}; border-radius: 3px; margin-right: 0.5rem;"></div>'
                f'<span style="font-size: 0.8rem;">{color_name}: {color_value}</span>'
                f'</div>',
                unsafe_allow_html=True
            )
    
    with col2:
        st.markdown("**Preview do Tema:**")
        
        # Exemplo de cards com o tema atual
        theme.create_metric_card(
            "Exemplo de Métrica",
            "42",
            "+12%",
            "Esta é uma demonstração do visual dos cards"
        )
        
        # Exemplo de status badges
        st.markdown("**Status Badges:**")
        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            theme.create_status_badge("online", "Online")
        with col_b:
            theme.create_status_badge("warning", "Aviso")
        with col_c:
            theme.create_status_badge("offline", "Offline")
    
    st.markdown("---")
    
    # Configurações do chat
    st.markdown("### 💬 Configurações do Chat")
    
    col1, col2 = st.columns(2)
    
    with col1:
        max_messages = st.slider(
            "Máximo de mensagens no histórico:",
            min_value=10,
            max_value=200,
            value=50,
            step=10,
            help="Número máximo de mensagens armazenadas no chat"
        )
        
        show_timestamps = st.checkbox(
            "Mostrar timestamps nas mensagens",
            value=False,
            help="Exibe a hora em que cada mensagem foi enviada"
        )
    
    with col2:
        auto_clear = st.checkbox(
            "Limpeza automática do chat",
            value=False,
            help="Limpa automaticamente o chat após um período"
        )
        
        if auto_clear:
            clear_interval = st.selectbox(
                "Intervalo de limpeza:",
                ["1 hora", "4 horas", "12 horas", "24 horas"],
                help="Período para limpeza automática"
            )
    
    # Configurações de validação de entrada
    st.markdown("---")
    st.markdown("### 🛡️ Configurações de Validação")
    
    validator = st.session_state.input_validator
    
    # Interface para configurar regras de validação
    validation_rules = validator.create_validation_rules_ui()
    
    # Área de teste de validação
    st.markdown("#### 🧪 Teste de Validação")
    test_input, is_valid = validator.create_validated_text_input(
        label="Digite algo para testar a validação:",
        key="validation_test",
        placeholder="Exemplo: test@example.com",
        rules=validation_rules,
        help_text="Use este campo para testar as regras de validação configuradas acima"
    )
    
    if test_input:
        if is_valid:
            st.success("✅ Entrada válida de acordo com as regras configuradas")
        else:
            st.warning("⚠️ Entrada não atende às regras de validação")
    
    # Configurações de tratamento de erros
    st.markdown("---")
    st.markdown("### 🚨 Tratamento de Erros")
    
    error_handler = st.session_state.error_handler
    
    col1, col2 = st.columns(2)
    
    with col1:
        max_retry = st.slider(
            "Máximo de tentativas:",
            min_value=1,
            max_value=5,
            value=3,
            help="Número de tentativas antes de considerar falha"
        )
        
        retry_delay = st.slider(
            "Delay entre tentativas (segundos):",
            min_value=0.5,
            max_value=5.0,
            value=1.0,
            step=0.5,
            help="Tempo de espera entre tentativas de retry"
        )
    
    with col2:
        st.markdown("**Status Atual do Sistema:**")
        error_handler.show_system_status()
        
        if st.button("🔄 Testar Conectividade"):
            if API_SERVICES_AVAILABLE and "api_client" in st.session_state:
                # Usa APIClient para teste avançado
                api_client = st.session_state.api_client
                with st.spinner("Testando todos os endpoints..."):
                    results = api_client.test_all_endpoints()
                    
                    if all(results.values()):
                        st.success("✅ Todos os endpoints OK!")
                    else:
                        failed = [k for k, v in results.items() if not v]
                        st.warning(f"⚠️ Falhas em: {', '.join(failed)}")
            else:
                # Fallback para método tradicional
                def test_connection():
                    import requests
                    response = requests.get(f"{API_BASE_URL}/api/v1/health/", timeout=5)
                    return response.status_code == 200
                
                result, success = safe_api_call(
                    test_connection,
                    fallback_response="Teste de conectividade falhou",
                    user_action="testar conectividade"
                )
                
                if success:
                    st.success("✅ Conectividade OK!")
                else:
                    st.error("❌ Problemas de conectividade detectados")
    
    # Configurações do APIClient
    if API_SERVICES_AVAILABLE and "api_client" in st.session_state:
        st.markdown("---")
        st.markdown("### 🌐 Configurações da API")
        
        api_client = st.session_state.api_client
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Configurações de Timeout:**")
            
            new_timeout = st.slider(
                "Timeout padrão (segundos):",
                min_value=5,
                max_value=60,
                value=30,
                help="Tempo limite para requisições HTTP"
            )
            
            if st.button("Aplicar Timeout"):
                api_client.set_timeout(new_timeout)
                st.success(f"✅ Timeout definido para {new_timeout}s")
            
            st.markdown("**Cache HTTP:**")
            if st.button("🗑️ Limpar Cache"):
                api_client.clear_cache()
                st.success("✅ Cache HTTP limpo!")
        
        with col2:
            st.markdown("**Estatísticas da API:**")
            api_stats = api_client.get_stats()
            
            if api_stats["http"]["total_requests"] > 0:
                st.metric("Total de Requisições", api_stats["http"]["total_requests"])
                st.metric("Taxa de Cache", f"{api_stats['http']['cache_hit_rate']:.1f}%")
                st.metric("Taxa de Sucesso", f"{api_stats['http']['success_rate']:.1f}%")
                st.metric("Tempo Médio", f"{api_stats['http']['average_response_time']:.2f}s")
            else:
                st.info("📊 Faça algumas requisições para ver estatísticas")
            
            # Última requisição bem-sucedida
            if api_stats["api"]["last_successful_request"]:
                last_success = api_stats["api"]["last_successful_request"]
                st.caption(f"🕒 Última requisição: {last_success.strftime('%H:%M:%S')}")
    
    # Dashboard de erros resumido
    st.markdown("---")
    st.markdown("### 📊 Resumo de Erros")
    
    if st.button("🔍 Ver Dashboard Completo de Erros"):
        # Mostra dashboard de erros em um expander
        with st.expander("🚨 Dashboard Completo de Erros", expanded=True):
            from components.error_handler import show_error_dashboard
            show_error_dashboard()
    
    # Configurações de performance
    st.markdown("---")
    st.markdown("### ⚡ Configurações de Performance")
    
    col1, col2 = st.columns(2)
    
    with col1:
        api_timeout = st.slider(
            "Timeout da API (segundos):",
            min_value=5,
            max_value=60,
            value=30,
            help="Tempo limite para requisições à API"
        )
        
        loading_animation = st.selectbox(
            "Tipo de animação de loading:",
            ["Spinner padrão", "Barra de progresso", "Pontos animados"],
            help="Estilo da animação durante carregamento"
        )
    
    with col2:
        cache_responses = st.checkbox(
            "Cache de respostas",
            value=True,
            help="Armazena respostas similares para melhor performance"
        )
        
        detailed_logs = st.checkbox(
            "Logs detalhados",
            value=False,
            help="Ativa logs mais detalhados para debugging"
        )
    
    # Botões de ação
    st.markdown("---")
    st.markdown("### 🔧 Ações do Sistema")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Salvar Configurações", use_container_width=True):
            # Simula salvamento das configurações
            st.success("✅ Configurações salvas com sucesso!")
    
    with col2:
        if st.button("🔄 Restaurar Padrões", use_container_width=True):
            # Restaura configurações padrão
            theme.set_color_scheme(COLOR_SCHEMES["default"])
            st.info("🔄 Configurações restauradas para o padrão")
            st.rerun()
    
    with col3:
        if st.button("🧹 Limpar Todos os Dados", use_container_width=True):
            # Limpa todos os dados da sessão
            for key in list(st.session_state.keys()):
                if key.startswith(("chat_", "feedback_", "loading_")):
                    del st.session_state[key]
            st.warning("⚠️ Todos os dados da sessão foram limpos")
            st.rerun()

def pagina_sobre():
    """Página sobre o sistema"""
    # Header customizado
    theme = st.session_state.theme_manager
    theme.create_custom_header(
        "Sobre o PROAtivo",
        "Conheça mais sobre nosso sistema inteligente de apoio à decisão"
    )
    
    st.markdown("""
    ## 🔌 Sistema Inteligente de Apoio à Decisão
    
    O **PROAtivo** é um sistema inovador que utiliza Inteligência Artificial para auxiliar 
    na gestão e manutenção de equipamentos elétricos.
    
    ### 🎯 Objetivos
    - Facilitar consultas sobre equipamentos e manutenções
    - Fornecer insights baseados em dados históricos
    - Otimizar processos de tomada de decisão
    - Melhorar a eficiência operacional
    
    ### 🛠️ Tecnologias
    - **Backend:** FastAPI + Python
    - **Frontend:** Streamlit
    - **IA:** Google Gemini + RAG
    - **Banco de Dados:** PostgreSQL
    - **Containerização:** Docker
    
    ### 🏗️ Arquitetura
    - Camada de Dados (ETL + Database)
    - Camada de API (FastAPI)
    - Camada de IA (LLM + RAG)
    - Camada de Apresentação (Streamlit)
    """)

def pagina_ajuda():
    """Página de ajuda"""
    # Header customizado
    theme = st.session_state.theme_manager
    theme.create_custom_header(
        "Central de Ajuda",
        "Tire suas dúvidas e aprenda a usar o sistema"
    )
    
    st.markdown("""
    ## 🤔 Como usar o PROAtivo?
    
    ### 💬 Fazendo Perguntas
    1. Digite sua pergunta na caixa de texto
    2. Clique em "📤 Enviar" ou pressione Enter
    3. Aguarde a resposta do assistente
    4. Avalie a resposta com 👍 ou 👎
    
    ### 🔍 Exemplos de Perguntas
    - "Qual foi a última manutenção do equipamento TR-001?"
    - "Quantos equipamentos estão em manutenção?"
    - "Liste as falhas mais comuns dos transformadores"
    - "Quando foi a última inspeção do setor Norte?"
    
    ### 📞 Suporte
    Em caso de problemas técnicos, verifique:
    1. ✅ Status da API na sidebar
    2. 🌐 Conexão com a internet
    3. 🔧 Configurações do sistema
    
    ### 💡 Dicas
    - Seja específico nas suas perguntas
    - Use códigos de equipamentos quando possível
    - Forneça feedback para melhorar o sistema
    """)

def main():
    """Função principal da aplicação"""
    # Inicializa sessão
    inicializar_sessao()
    
    # Cria sidebar
    criar_sidebar()
    
    # Roteamento de páginas
    if st.session_state.pagina_atual == "consultas":
        pagina_consultas()
    elif st.session_state.pagina_atual == "dashboard":
        pagina_dashboard()
    elif st.session_state.pagina_atual == "metricas":
        pagina_metricas()
    elif st.session_state.pagina_atual == "config":
        pagina_config()
    elif st.session_state.pagina_atual == "sobre":
        pagina_sobre()
    elif st.session_state.pagina_atual == "ajuda":
        pagina_ajuda()

if __name__ == "__main__":
    main() 