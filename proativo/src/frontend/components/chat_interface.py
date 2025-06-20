import streamlit as st
from datetime import datetime
from typing import List, Dict, Any, Optional
import uuid

class ChatInterface:
    """Componente modular para interface de chat no Streamlit"""
    
    def __init__(self, 
                 session_key: str = "chat_messages",
                 max_messages: int = 100,
                 welcome_message: str = None):
        """
        Inicializa o componente de chat
        
        Args:
            session_key: Chave para armazenar mensagens na sessão
            max_messages: Número máximo de mensagens no histórico
            welcome_message: Mensagem inicial do assistente
        """
        self.session_key = session_key
        self.max_messages = max_messages
        self.welcome_message = welcome_message or (
            "Olá! 👋 Eu sou o assistente do PROAtivo. "
            "Como posso ajudá-lo com informações sobre equipamentos e manutenções?"
        )
        
        self._initialize_session()
    
    def _initialize_session(self):
        """Inicializa as mensagens na sessão se ainda não existir"""
        if self.session_key not in st.session_state:
            st.session_state[self.session_key] = [
                {
                    "id": str(uuid.uuid4()),
                    "role": "assistant",
                    "content": self.welcome_message,
                    "timestamp": datetime.now()
                }
            ]
    
    def get_messages(self) -> List[Dict[str, Any]]:
        """Retorna todas as mensagens do chat"""
        return st.session_state[self.session_key]
    
    def add_message(self, role: str, content: str, metadata: Dict = None) -> str:
        """
        Adiciona uma nova mensagem ao chat
        
        Args:
            role: 'user' ou 'assistant'
            content: Conteúdo da mensagem
            metadata: Metadados adicionais (opcional)
            
        Returns:
            ID da mensagem criada
        """
        message_id = str(uuid.uuid4())
        
        message = {
            "id": message_id,
            "role": role,
            "content": content,
            "timestamp": datetime.now(),
            "metadata": metadata or {}
        }
        
        # Adiciona mensagem
        st.session_state[self.session_key].append(message)
        
        # Remove mensagens antigas se exceder o limite
        if len(st.session_state[self.session_key]) > self.max_messages:
            # Mantém sempre a mensagem de boas-vindas
            welcome_msg = st.session_state[self.session_key][0]
            recent_messages = st.session_state[self.session_key][-(self.max_messages-1):]
            st.session_state[self.session_key] = [welcome_msg] + recent_messages
        
        return message_id
    
    def clear_chat(self):
        """Limpa o histórico de chat, mantendo apenas a mensagem de boas-vindas"""
        st.session_state[self.session_key] = [
            {
                "id": str(uuid.uuid4()),
                "role": "assistant",
                "content": self.welcome_message,
                "timestamp": datetime.now()
            }
        ]
    
    def get_last_message(self) -> Optional[Dict[str, Any]]:
        """Retorna a última mensagem do chat"""
        messages = self.get_messages()
        return messages[-1] if messages else None
    
    def get_message_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Busca uma mensagem pelo ID"""
        for message in self.get_messages():
            if message.get("id") == message_id:
                return message
        return None
    
    def render_messages(self, 
                       show_timestamps: bool = False,
                       show_metadata: bool = False,
                       container_height: int = None):
        """
        Renderiza todas as mensagens do chat
        
        Args:
            show_timestamps: Se deve mostrar timestamps das mensagens
            show_metadata: Se deve mostrar metadados das mensagens
            container_height: Altura do container (se especificado, cria container com scroll)
        """
        messages = self.get_messages()
        
        if container_height:
            with st.container(height=container_height):
                self._render_message_list(messages, show_timestamps, show_metadata)
        else:
            self._render_message_list(messages, show_timestamps, show_metadata)
    
    def _render_message_list(self, 
                           messages: List[Dict[str, Any]], 
                           show_timestamps: bool,
                           show_metadata: bool):
        """Renderiza a lista de mensagens"""
        for message in messages:
            self._render_single_message(message, show_timestamps, show_metadata)
    
    def _render_single_message(self, 
                             message: Dict[str, Any],
                             show_timestamps: bool,
                             show_metadata: bool):
        """Renderiza uma única mensagem"""
        role = message.get("role", "user")
        content = message.get("content", "")
        timestamp = message.get("timestamp")
        metadata = message.get("metadata", {})
        
        # Escolhe o ícone e estilo baseado no role
        if role == "user":
            icon = "👤"
            message_type = "user"
            prefix = "**Você:**"
        else:
            icon = "🤖"
            message_type = "assistant"
            prefix = "**Assistente:**"
        
        # Renderiza a mensagem usando o chat_message do Streamlit
        with st.chat_message(message_type):
            st.write(f"{prefix} {content}")
            
            # Mostra timestamp se solicitado
            if show_timestamps and timestamp:
                st.caption(f"⏰ {timestamp.strftime('%H:%M:%S')}")
            
            # Mostra metadados se solicitado
            if show_metadata and metadata:
                with st.expander("ℹ️ Detalhes"):
                    for key, value in metadata.items():
                        st.text(f"{key}: {value}")
    
    def render_input_area(self, 
                         placeholder: str = "Digite sua pergunta...",
                         button_text: str = "📤 Enviar",
                         input_key: str = "chat_input",
                         button_key: str = "chat_button",
                         max_chars: int = 1000) -> tuple[str, bool]:
        """
        Renderiza a área de input do chat
        
        Args:
            placeholder: Placeholder do campo de texto
            button_text: Texto do botão de envio
            input_key: Chave única para o campo de input
            button_key: Chave única para o botão
            max_chars: Número máximo de caracteres
            
        Returns:
            Tupla (texto_digitado, botao_pressionado)
        """
        col1, col2 = st.columns([4, 1])
        
        with col1:
            user_input = st.text_input(
                "Digite sua pergunta:",
                placeholder=placeholder,
                key=input_key,
                max_chars=max_chars,
                label_visibility="collapsed"
            )
        
        with col2:
            button_pressed = st.button(
                button_text, 
                key=button_key,
                use_container_width=True
            )
        
        return user_input, button_pressed
    
    def render_chat_stats(self):
        """Renderiza estatísticas básicas do chat"""
        messages = self.get_messages()
        user_messages = [msg for msg in messages if msg.get("role") == "user"]
        assistant_messages = [msg for msg in messages if msg.get("role") == "assistant"]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total de Mensagens", len(messages))
        
        with col2:
            st.metric("Suas Perguntas", len(user_messages))
        
        with col3:
            st.metric("Respostas do Assistente", len(assistant_messages))
    
    def export_chat_history(self, format: str = "text") -> str:
        """
        Exporta o histórico do chat em diferentes formatos
        
        Args:
            format: 'text', 'json' ou 'markdown'
            
        Returns:
            String com o histórico formatado
        """
        messages = self.get_messages()
        
        if format == "json":
            import json
            return json.dumps(messages, indent=2, default=str)
        
        elif format == "markdown":
            lines = ["# Histórico do Chat PROAtivo\n"]
            for msg in messages:
                role_icon = "👤" if msg["role"] == "user" else "🤖"
                timestamp = msg["timestamp"].strftime("%H:%M:%S")
                lines.append(f"## {role_icon} {msg['role'].title()} - {timestamp}")
                lines.append(f"{msg['content']}\n")
            return "\n".join(lines)
        
        else:  # text format
            lines = ["=== Histórico do Chat PROAtivo ===\n"]
            for msg in messages:
                role_icon = "👤" if msg["role"] == "user" else "🤖"
                timestamp = msg["timestamp"].strftime("%H:%M:%S")
                lines.append(f"[{timestamp}] {role_icon} {msg['role'].upper()}: {msg['content']}\n")
            return "\n".join(lines)
    
    def get_conversation_context(self, max_messages: int = 5) -> List[Dict[str, str]]:
        """
        Retorna o contexto da conversa para enviar à API
        
        Args:
            max_messages: Número máximo de mensagens recentes para incluir
            
        Returns:
            Lista de mensagens formatadas para a API
        """
        messages = self.get_messages()
        recent_messages = messages[-max_messages:] if len(messages) > max_messages else messages
        
        # Remove a mensagem de boas-vindas do contexto se for muito antiga
        context = []
        for msg in recent_messages:
            if msg["role"] in ["user", "assistant"] and msg["content"] != self.welcome_message:
                context.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        return context


def create_chat_interface(session_key: str = "chat_messages", **kwargs) -> ChatInterface:
    """
    Factory function para criar uma instância do ChatInterface
    
    Args:
        session_key: Chave única para a sessão
        **kwargs: Argumentos adicionais para o ChatInterface
        
    Returns:
        Instância configurada do ChatInterface
    """
    return ChatInterface(session_key=session_key, **kwargs) 