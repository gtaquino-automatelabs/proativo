import streamlit as st
from typing import Dict, Any, Optional

class ThemeManager:
    """Gerenciador de tema e estilos para a aplicação Streamlit"""
    
    def __init__(self):
        """Inicializa o gerenciador de tema"""
        self.primary_color = "#1f77b4"
        self.secondary_color = "#ff7f0e" 
        self.background_color = "#ffffff"
        self.text_color = "#262730"
        self.sidebar_bg = "#f0f2f6"
        
    def apply_custom_css(self):
        """Aplica CSS customizado para melhorar a aparência"""
        
        custom_css = f"""
        <style>
        /* ==== TEMA GERAL ==== */
        .stApp {{
            background-color: {self.background_color};
            color: {self.text_color};
        }}
        
        .main {{
            padding-top: 2rem;
            padding-bottom: 2rem;
            background-color: {self.background_color};
            color: {self.text_color};
        }}
        
        .css-1kyxreq {{
            background-color: {self.background_color};
        }}
        
        .css-12oz5g7 {{
            background-color: {self.background_color};
        }}
        
        .block-container {{
            padding-top: 1rem;
            background-color: {self.background_color};
        }}
        
        /* ==== HEADER CUSTOMIZADO ==== */
        .main-header {{
            background: linear-gradient(90deg, {self.primary_color} 0%, {self.secondary_color} 100%);
            padding: 1rem 2rem;
            border-radius: 10px;
            margin-bottom: 2rem;
            color: white;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        .main-header h1 {{
            margin: 0;
            font-size: 2.5rem;
            font-weight: 700;
        }}
        
        .main-header p {{
            margin: 0.5rem 0 0 0;
            font-size: 1.1rem;
            opacity: 0.9;
        }}
        
        /* ==== SIDEBAR MELHORADA ==== */
        .css-1d391kg {{
            background-color: {self.sidebar_bg};
            border-right: 2px solid {self.primary_color};
        }}
        
        .sidebar-logo {{
            text-align: center;
            padding: 1rem;
            background: linear-gradient(135deg, {self.primary_color}, {self.secondary_color});
            color: white;
            border-radius: 10px;
            margin-bottom: 1rem;
        }}
        
        .sidebar-logo h2 {{
            margin: 0;
            font-size: 1.5rem;
        }}
        
        /* ==== BOTÕES CUSTOMIZADOS ==== */
        .stButton > button {{
            width: 100%;
            border-radius: 25px;
            border: none;
            padding: 0.5rem 1rem;
            font-weight: 600;
            transition: all 0.3s ease;
            background: linear-gradient(45deg, {self.primary_color}, {self.secondary_color});
            color: white;
        }}
        
        .stButton > button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
            background: linear-gradient(45deg, {self.secondary_color}, {self.primary_color});
        }}
        
        /* ==== BOTÕES DA SIDEBAR ==== */
        .sidebar-button {{
            margin: 0.2rem 0;
        }}
        
        .sidebar-button > button {{
            background: white !important;
            color: {self.text_color} !important;
            border: 1px solid {self.primary_color} !important;
            border-radius: 8px !important;
            font-weight: 500;
        }}
        
        .sidebar-button > button:hover {{
            background: {self.primary_color} !important;
            color: white !important;
        }}
        
        /* ==== CHAT INTERFACE ==== */
        .chat-container {{
            background: {self.background_color};
            border-radius: 15px;
            padding: 1.5rem;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            border: 1px solid {self.primary_color}33;
            color: {self.text_color};
        }}
        
        .chat-message {{
            padding: 1rem;
            margin: 0.5rem 0;
            border-radius: 15px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
        }}
        
        .chat-message.user {{
            background: linear-gradient(135deg, #e3f2fd, #bbdefb);
            margin-left: 20%;
        }}
        
        .chat-message.assistant {{
            background: linear-gradient(135deg, #f3e5f5, #e1bee7);
            margin-right: 20%;
        }}
        
        /* ==== MÉTRICAS ==== */
        .metric-card {{
            background: {self.background_color};
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            border-left: 4px solid {self.primary_color};
            border: 1px solid {self.primary_color}33;
            margin: 0.5rem 0;
            color: {self.text_color};
        }}
        
        .metric-value {{
            font-size: 2rem;
            font-weight: 700;
            color: {self.primary_color};
        }}
        
        .metric-label {{
            font-size: 0.9rem;
            color: #666;
            margin-top: 0.5rem;
        }}
        
        /* ==== STATUS INDICATORS ==== */
        .status-online {{
            color: #4caf50;
            font-weight: 600;
        }}
        
        .status-offline {{
            color: #f44336;
            font-weight: 600;
        }}
        
        .status-warning {{
            color: #ff9800;
            font-weight: 600;
        }}
        
        /* ==== FEEDBACK BUTTONS ==== */
        .feedback-container {{
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 10px;
            border: 1px solid #dee2e6;
            margin: 1rem 0;
        }}
        
        .feedback-buttons {{
            display: flex;
            gap: 0.5rem;
            justify-content: center;
        }}
        
        .feedback-button {{
            padding: 0.5rem 1rem;
            border-radius: 20px;
            border: none;
            font-size: 1.1rem;
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        
        .feedback-positive {{
            background: #d4edda;
            color: #155724;
        }}
        
        .feedback-positive:hover {{
            background: #c3e6cb;
            transform: scale(1.05);
        }}
        
        .feedback-negative {{
            background: #f8d7da;
            color: #721c24;
        }}
        
        .feedback-negative:hover {{
            background: #f5c6cb;
            transform: scale(1.05);
        }}
        
        /* ==== LOADING INDICATORS ==== */
        .loading-spinner {{
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 2rem;
            background: #f8f9fa;
            border-radius: 10px;
            margin: 1rem 0;
        }}
        
        .loading-text {{
            margin-left: 1rem;
            font-weight: 500;
            color: {self.primary_color};
        }}
        
        /* ==== PROGRESS BARS ==== */
        .stProgress > div > div {{
            background: linear-gradient(45deg, {self.primary_color}, {self.secondary_color});
            border-radius: 10px;
        }}
        
        /* ==== ALERTAS CUSTOMIZADOS ==== */
        .stAlert {{
            border-radius: 10px;
            border: none;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }}
        
        .stSuccess {{
            background: linear-gradient(135deg, #d4edda, #c3e6cb);
            color: #155724;
        }}
        
        .stError {{
            background: linear-gradient(135deg, #f8d7da, #f5c6cb);
            color: #721c24;
        }}
        
        .stWarning {{
            background: linear-gradient(135deg, #fff3cd, #ffeaa7);
            color: #856404;
        }}
        
        .stInfo {{
            background: linear-gradient(135deg, #cce7ff, #b3d9ff);
            color: #004085;
        }}
        
        /* ==== RESPONSIVIDADE ==== */
        @media (max-width: 768px) {{
            .main-header h1 {{
                font-size: 2rem;
            }}
            
            .chat-message.user,
            .chat-message.assistant {{
                margin-left: 5%;
                margin-right: 5%;
            }}
            
            .metric-card {{
                padding: 1rem;
            }}
            
            .metric-value {{
                font-size: 1.5rem;
            }}
        }}
        
        @media (max-width: 480px) {{
            .main-header {{
                padding: 0.5rem 1rem;
            }}
            
            .main-header h1 {{
                font-size: 1.5rem;
            }}
            
            .chat-container {{
                padding: 1rem;
            }}
        }}
        
        /* ==== ANIMAÇÕES ==== */
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .fade-in {{
            animation: fadeIn 0.5s ease-out;
        }}
        
        @keyframes pulse {{
            0% {{ transform: scale(1); }}
            50% {{ transform: scale(1.05); }}
            100% {{ transform: scale(1); }}
        }}
        
        .pulse {{
            animation: pulse 2s infinite;
        }}
        
        /* ==== SCROLLBAR CUSTOMIZADA ==== */
        ::-webkit-scrollbar {{
            width: 8px;
        }}
        
        ::-webkit-scrollbar-track {{
            background: #f1f1f1;
            border-radius: 10px;
        }}
        
        ::-webkit-scrollbar-thumb {{
            background: {self.primary_color};
            border-radius: 10px;
        }}
        
        ::-webkit-scrollbar-thumb:hover {{
            background: {self.secondary_color};
        }}
        
        /* ==== HIDE STREAMLIT BRANDING ==== */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        header {{visibility: hidden;}}
        
        /* ==== ADAPTAÇÃO COMPLETA PARA TEMAS ESCUROS ==== */
        .stSelectbox > div > div {{
            background-color: {self.background_color} !important;
            color: {self.text_color} !important;
        }}
        
        .stTextInput > div > div > input {{
            background-color: {self.background_color} !important;
            color: {self.text_color} !important;
            border-color: {self.primary_color}66 !important;
        }}
        
        .stTextArea > div > div > textarea {{
            background-color: {self.background_color} !important;
            color: {self.text_color} !important;
            border-color: {self.primary_color}66 !important;
        }}
        
        .element-container {{
            background-color: {self.background_color} !important;
        }}
        
        .stMarkdown {{
            color: {self.text_color} !important;
        }}
        
        .stText {{
            color: {self.text_color} !important;
        }}
        
        /* Ajustar labels e headers para temas escuros */
        .metric-label {{
            color: {self.text_color}CC !important;
        }}
        
        /* Ajustar containers filhos */
        div[data-testid="column"] {{
            background-color: {self.background_color} !important;
        }}
        
        div[data-testid="stVerticalBlock"] {{
            background-color: {self.background_color} !important;
        }}
        
        /* Forçar background em todos os elementos principais */
        .css-1v0mbdj {{
            background-color: {self.background_color} !important;
            color: {self.text_color} !important;
        }}
        
        .css-1lcbmhc {{
            background-color: {self.background_color} !important;
            color: {self.text_color} !important;
        }}
        
        /* Garantir que todos os divs herdem o background */
        div:not(.sidebar-logo):not(.main-header) {{
            background-color: inherit;
            color: inherit;
        }}
        
        /* ==== CORREÇÕES ESPECÍFICAS PARA ÁREAS CLARAS ==== */
        
        /* Status do Sistema - força background e texto visível */
        .css-1kyxreq .css-12oz5g7 {{
            background-color: {self.background_color} !important;
            color: {self.text_color} !important;
        }}
        
        /* Todos os containers de conteúdo */
        .css-1d391kg, .css-1lcbmhc, .css-1v0mbdj, .css-12oz5g7 {{
            background-color: {self.background_color} !important;
            color: {self.text_color} !important;
        }}
        
        /* Seções de cartões e métricas */
        .css-1r6slb0, .css-1wivap2, .css-1cpxqw2 {{
            background-color: {self.background_color} !important;
            color: {self.text_color} !important;
        }}
        
        /* Força todos os textos */
        p, h1, h2, h3, h4, h5, h6, span, label, div {{
            color: {self.text_color} !important;
        }}
        
        /* Específico para labels de métricas */
        .css-1wivap2 p, .css-1cpxqw2 p {{
            color: {self.text_color} !important;
        }}
        
        /* Container principal do Streamlit */
        .css-1d391kg {{
            background-color: {self.background_color} !important;
        }}
        
        /* Área de conteúdo principal */
        .css-1lcbmhc.e1fqkh3o4 {{
            background-color: {self.background_color} !important;
        }}
        
        /* Status badges e elementos pequenos */
        .css-1wivap2 {{
            background-color: {self.background_color} !important;
        }}
        
        /* Força background em elementos específicos do Streamlit */
        [data-testid="stSidebar"] {{
            background-color: {self.sidebar_bg} !important;
        }}
        
        [data-testid="stAppViewContainer"] {{
            background-color: {self.background_color} !important;
        }}
        
        [data-testid="stMain"] {{
            background-color: {self.background_color} !important;
        }}
        
        /* Cartões de status com fundo escuro */
        .element-container > div {{
            background-color: {self.background_color} !important;
            color: {self.text_color} !important;
        }}
        
        /* Correção para textos pequenos e labels */
        small, .small-text {{
            color: {self.text_color}BB !important;
        }}

        </style>
        """
        
        st.markdown(custom_css, unsafe_allow_html=True)
    
    def create_custom_header(self, title: str, subtitle: str = None):
        """Cria um header customizado profissional"""
        
        header_html = f"""
        <div class="main-header fade-in">
            <h1>🔌 {title}</h1>
            {f'<p>{subtitle}</p>' if subtitle else ''}
        </div>
        """
        
        st.markdown(header_html, unsafe_allow_html=True)
    
    def create_sidebar_logo(self):
        """Cria logo customizado na sidebar"""
        
        logo_html = """
        <div class="sidebar-logo pulse">
            <h2>🔌 PROAtivo</h2>
            <p style="margin: 0; font-size: 0.9rem; opacity: 0.8;">Sistema Inteligente</p>
        </div>
        """
        
        st.sidebar.markdown(logo_html, unsafe_allow_html=True)
    
    def create_metric_card(self, title: str, value: str, delta: str = None, help_text: str = None):
        """Cria cartão de métrica customizado"""
        
        delta_html = ""
        if delta:
            delta_color = "#4caf50" if not delta.startswith("-") else "#f44336"
            delta_html = f'<div style="color: {delta_color}; font-size: 0.8rem; margin-top: 0.2rem;">{delta}</div>'
        
        help_html = ""
        if help_text:
            help_html = f'<div style="font-size: 0.7rem; color: #888; margin-top: 0.5rem;">{help_text}</div>'
        
        card_html = f"""
        <div class="metric-card fade-in">
            <div class="metric-value">{value}</div>
            <div class="metric-label">{title}</div>
            {delta_html}
            {help_html}
        </div>
        """
        
        st.markdown(card_html, unsafe_allow_html=True)
    
    def create_status_badge(self, status: str, text: str):
        """Cria badge de status colorido"""
        
        colors = {
            "online": "#4caf50",
            "offline": "#f44336", 
            "warning": "#ff9800",
            "info": "#2196f3"
        }
        
        color = colors.get(status, "#666")
        
        badge_html = f"""
        <span style="
            background: {color};
            color: white;
            padding: 0.2rem 0.8rem;
            border-radius: 15px;
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
        ">{text}</span>
        """
        
        st.markdown(badge_html, unsafe_allow_html=True)
    
    def create_chat_bubble(self, message: str, role: str, timestamp: str = None):
        """Cria bubble de chat customizado"""
        
        role_class = "user" if role == "user" else "assistant"
        icon = "👤" if role == "user" else "🤖"
        
        timestamp_html = ""
        if timestamp:
            timestamp_html = f'<div style="font-size: 0.7rem; color: #888; margin-top: 0.5rem;">{timestamp}</div>'
        
        bubble_html = f"""
        <div class="chat-message {role_class} fade-in">
            <div style="display: flex; align-items: center; margin-bottom: 0.5rem;">
                <span style="font-size: 1.2rem; margin-right: 0.5rem;">{icon}</span>
                <strong>{role.title()}</strong>
            </div>
            <div>{message}</div>
            {timestamp_html}
        </div>
        """
        
        st.markdown(bubble_html, unsafe_allow_html=True)
    
    def create_loading_placeholder(self, message: str = "Carregando..."):
        """Cria placeholder de loading customizado"""
        
        loading_html = f"""
        <div class="loading-spinner">
            <div class="spinner-border text-primary" role="status">
                <span class="sr-only"></span>
            </div>
            <div class="loading-text">{message}</div>
        </div>
        """
        
        return st.markdown(loading_html, unsafe_allow_html=True)
    
    def apply_responsive_config(self):
        """Aplica configurações responsivas"""
        
        # Detecta o tamanho da tela via JavaScript (simulado)
        responsive_css = """
        <style>
        /* Configurações responsivas adicionais */
        .responsive-container {
            width: 100%;
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 1rem;
        }
        
        .responsive-grid {
            display: grid;
            gap: 1rem;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        }
        
        .responsive-flex {
            display: flex;
            flex-wrap: wrap;
            gap: 1rem;
        }
        
        .responsive-flex > * {
            flex: 1 1 300px;
        }
        </style>
        """
        
        st.markdown(responsive_css, unsafe_allow_html=True)
    
    def set_page_config(self):
        """Configura a página com tema personalizado"""
        
        # Essa função deve ser chamada antes de qualquer comando st.
        # Como st.set_page_config só pode ser chamado uma vez,
        # vamos deixar isso para ser feito na aplicação principal.
        pass
    
    def get_color_scheme(self) -> Dict[str, str]:
        """Retorna o esquema de cores atual"""
        
        return {
            "primary": self.primary_color,
            "secondary": self.secondary_color,
            "background": self.background_color,
            "text": self.text_color,
            "sidebar_bg": self.sidebar_bg
        }
    
    def set_color_scheme(self, colors: Dict[str, str]):
        """Define um novo esquema de cores"""
        
        if "primary" in colors:
            self.primary_color = colors["primary"]
        if "secondary" in colors:
            self.secondary_color = colors["secondary"]
        if "background" in colors:
            self.background_color = colors["background"]
        if "text" in colors:
            self.text_color = colors["text"]
        if "sidebar_bg" in colors:
            self.sidebar_bg = colors["sidebar_bg"]


def create_theme_manager() -> ThemeManager:
    """
    Factory function para criar uma instância do ThemeManager
    
    Returns:
        Instância configurada do ThemeManager
    """
    return ThemeManager()


def apply_professional_theme():
    """Função de conveniência para aplicar tema profissional"""
    theme = create_theme_manager()
    theme.apply_custom_css()
    theme.apply_responsive_config()
    return theme


# Esquemas de cores pré-definidos
COLOR_SCHEMES = {
    "default": {
        "primary": "#1f77b4",
        "secondary": "#ff7f0e",
        "background": "#ffffff",
        "text": "#262730",
        "sidebar_bg": "#f0f2f6"
    },
    "dark": {
        "primary": "#00d4aa",
        "secondary": "#ff6b6b", 
        "background": "#2c2c2c",  # ← MESMO CINZA ESCURO DO ENERGY
        "text": "#ffffff",
        "sidebar_bg": "#383838"   # ← MESMA COR DA SIDEBAR DO ENERGY
    },
    "corporate": {
        "primary": "#2c3e50",
        "secondary": "#3498db",
        "background": "#ffffff", 
        "text": "#2c3e50",
        "sidebar_bg": "#ecf0f1"
    },
    "energy": {
        "primary": "#ff6b35",   # ← Laranja mais vibrante para melhor contraste
        "secondary": "#f7931e", # ← Amarelo mais vibrante  
        "background": "#2c2c2c", # ← FUNDO CINZA ESCURO/CHUMBO
        "text": "#ffffff",       # ← Texto branco para contraste
        "sidebar_bg": "#383838" # ← Sidebar cinza escuro
    }
} 