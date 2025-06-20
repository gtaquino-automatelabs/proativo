import streamlit as st
import requests
from datetime import datetime
from typing import Dict, Any, Optional, Callable
import uuid
import os

class FeedbackSystem:
    """Componente modular para sistema de feedback no Streamlit"""
    
    def __init__(self, 
                 api_base_url: str = None,
                 session_key: str = "feedback_history",
                 user_id: str = "streamlit_user"):
        """
        Inicializa o sistema de feedback
        
        Args:
            api_base_url: URL base da API para envio de feedback
            session_key: Chave para armazenar histórico na sessão
            user_id: ID do usuário para identificação
        """
        self.api_base_url = api_base_url or os.getenv("API_BASE_URL", "http://localhost:8000")
        self.session_key = session_key
        self.user_id = user_id
        
        self._initialize_session()
    
    def _initialize_session(self):
        """Inicializa o histórico de feedback na sessão"""
        if self.session_key not in st.session_state:
            st.session_state[self.session_key] = []
    
    def render_feedback_buttons(self, 
                              response_id: str,
                              layout: str = "horizontal",
                              show_labels: bool = True,
                              button_size: str = "medium",
                              key_prefix: str = "feedback") -> Optional[str]:
        """
        Renderiza os botões de feedback 👍/👎
        
        Args:
            response_id: ID da resposta para qual o feedback está sendo dado
            layout: 'horizontal' ou 'vertical'
            show_labels: Se deve mostrar os rótulos dos botões
            button_size: 'small', 'medium' ou 'large'
            key_prefix: Prefixo para as chaves dos botões
            
        Returns:
            String com o tipo de feedback ('positive', 'negative') ou None
        """
        feedback_given = None
        
        # Configurações do botão baseado no tamanho
        use_container_width = button_size == "large"
        
        # Labels dos botões
        positive_label = "👍 Bom" if show_labels else "👍"
        negative_label = "👎 Ruim" if show_labels else "👎"
        
        if layout == "horizontal":
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button(positive_label, 
                           key=f"{key_prefix}_positive_{response_id}",
                           use_container_width=use_container_width):
                    feedback_given = "positive"
            
            with col2:
                if st.button(negative_label,
                           key=f"{key_prefix}_negative_{response_id}",
                           use_container_width=use_container_width):
                    feedback_given = "negative"
        
        else:  # vertical
            if st.button(positive_label,
                       key=f"{key_prefix}_positive_{response_id}",
                       use_container_width=use_container_width):
                feedback_given = "positive"
            
            if st.button(negative_label,
                       key=f"{key_prefix}_negative_{response_id}",
                       use_container_width=use_container_width):
                feedback_given = "negative"
        
        return feedback_given
    
    def render_comment_area(self, 
                          response_id: str,
                          placeholder: str = "Conte-nos como podemos melhorar...",
                          height: int = 60,
                          max_chars: int = 500,
                          key_prefix: str = "comment") -> str:
        """
        Renderiza área para comentários adicionais
        
        Args:
            response_id: ID da resposta
            placeholder: Texto do placeholder
            height: Altura da área de texto
            max_chars: Número máximo de caracteres
            key_prefix: Prefixo para a chave do componente
            
        Returns:
            Texto do comentário
        """
        return st.text_area(
            "Comentário adicional (opcional):",
            placeholder=placeholder,
            height=height,
            max_chars=max_chars,
            key=f"{key_prefix}_{response_id}",
            help=f"Máximo {max_chars} caracteres"
        )
    
    def render_feedback_form(self,
                           response_id: str,
                           title: str = "Como você avalia esta resposta?",
                           show_comment: bool = True,
                           show_send_button: bool = True,
                           layout: str = "horizontal",
                           key_prefix: str = "form") -> Dict[str, Any]:
        """
        Renderiza um formulário completo de feedback
        
        Args:
            response_id: ID da resposta
            title: Título do formulário
            show_comment: Se deve mostrar área de comentário
            show_send_button: Se deve mostrar botão de envio
            layout: Layout dos botões ('horizontal' ou 'vertical')
            key_prefix: Prefixo para as chaves dos componentes
            
        Returns:
            Dict com feedback_type, comment e send_pressed
        """
        result = {
            "feedback_type": None,
            "comment": "",
            "send_pressed": False
        }
        
        # Título
        if title:
            st.markdown(f"**{title}**")
        
        # Botões de feedback
        feedback_type = self.render_feedback_buttons(
            response_id=response_id,
            layout=layout,
            key_prefix=f"{key_prefix}_btn"
        )
        
        result["feedback_type"] = feedback_type
        
        # Área de comentário
        if show_comment:
            comment = self.render_comment_area(
                response_id=response_id,
                key_prefix=f"{key_prefix}_comment"
            )
            result["comment"] = comment.strip()
        
        # Botão de envio (se comentário foi digitado)
        if show_send_button and result["comment"]:
            if st.button("📝 Enviar comentário", 
                       key=f"{key_prefix}_send_{response_id}"):
                result["send_pressed"] = True
                result["feedback_type"] = result["feedback_type"] or "neutral"
        
        return result
    
    def send_feedback(self,
                     rating: str,
                     response_id: str,
                     comment: str = "",
                     metadata: Dict = None) -> bool:
        """
        Envia feedback para a API
        
        Args:
            rating: 'positive', 'negative' ou 'neutral'
            response_id: ID da resposta
            comment: Comentário adicional
            metadata: Metadados adicionais
            
        Returns:
            True se enviado com sucesso, False caso contrário
        """
        try:
            payload = {
                "rating": rating,
                "comment": comment,
                "user_id": self.user_id,
                "response_id": response_id,
                "metadata": metadata or {}
            }
            
            response = requests.post(
                f"{self.api_base_url}/feedback",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                # Salva no histórico local
                self._save_to_history(rating, response_id, comment, metadata)
                return True
            else:
                st.error(f"❌ Erro ao enviar feedback: Status {response.status_code}")
                return False
                
        except requests.exceptions.Timeout:
            st.error("❌ Tempo limite excedido ao enviar feedback")
            return False
        except requests.exceptions.ConnectionError:
            st.error("❌ Erro de conexão. Verifique se a API está funcionando.")
            return False
        except Exception as e:
            st.error(f"❌ Erro inesperado: {str(e)}")
            return False
    
    def _save_to_history(self, rating: str, response_id: str, comment: str, metadata: Dict):
        """Salva feedback no histórico local"""
        feedback_entry = {
            "id": str(uuid.uuid4()),
            "rating": rating,
            "response_id": response_id,
            "comment": comment,
            "metadata": metadata or {},
            "timestamp": datetime.now(),
            "user_id": self.user_id
        }
        
        st.session_state[self.session_key].append(feedback_entry)
    
    def get_feedback_history(self) -> list:
        """Retorna o histórico de feedbacks"""
        return st.session_state[self.session_key]
    
    def get_feedback_stats(self) -> Dict[str, int]:
        """Retorna estatísticas do feedback"""
        history = self.get_feedback_history()
        
        stats = {
            "total": len(history),
            "positive": len([f for f in history if f["rating"] == "positive"]),
            "negative": len([f for f in history if f["rating"] == "negative"]),
            "neutral": len([f for f in history if f["rating"] == "neutral"]),
            "with_comments": len([f for f in history if f["comment"]])
        }
        
        return stats
    
    def render_feedback_stats(self):
        """Renderiza estatísticas de feedback"""
        stats = self.get_feedback_stats()
        
        if stats["total"] > 0:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("👍 Positivos", stats["positive"])
            
            with col2:
                st.metric("👎 Negativos", stats["negative"])
            
            with col3:
                st.metric("💬 Com Comentário", stats["with_comments"])
            
            # Percentual de satisfação
            if stats["positive"] + stats["negative"] > 0:
                satisfaction = (stats["positive"] / (stats["positive"] + stats["negative"])) * 100
                st.metric("😊 Satisfação", f"{satisfaction:.1f}%")
        else:
            st.info("📊 Ainda não há feedbacks registrados")
    
    def clear_feedback_history(self):
        """Limpa o histórico de feedbacks"""
        st.session_state[self.session_key] = []
    
    def render_quick_feedback(self,
                            response_id: str,
                            on_feedback: Callable[[str, str, str], None] = None,
                            key_prefix: str = "quick") -> bool:
        """
        Renderiza um feedback rápido inline
        
        Args:
            response_id: ID da resposta
            on_feedback: Callback chamado quando feedback é dado
            key_prefix: Prefixo para as chaves
            
        Returns:
            True se feedback foi dado
        """
        col1, col2, col3 = st.columns([1, 1, 4])
        
        feedback_given = False
        
        with col1:
            if st.button("👍", key=f"{key_prefix}_quick_pos_{response_id}"):
                success = self.send_feedback("positive", response_id)
                if success:
                    st.success("✅ Obrigado pelo feedback!")
                    if on_feedback:
                        on_feedback("positive", response_id, "")
                    feedback_given = True
        
        with col2:
            if st.button("👎", key=f"{key_prefix}_quick_neg_{response_id}"):
                success = self.send_feedback("negative", response_id)
                if success:
                    st.success("✅ Obrigado pelo feedback!")
                    if on_feedback:
                        on_feedback("negative", response_id, "")
                    feedback_given = True
        
        return feedback_given


def create_feedback_system(api_base_url: str = None, **kwargs) -> FeedbackSystem:
    """
    Factory function para criar uma instância do FeedbackSystem
    
    Args:
        api_base_url: URL base da API
        **kwargs: Argumentos adicionais para o FeedbackSystem
        
    Returns:
        Instância configurada do FeedbackSystem
    """
    return FeedbackSystem(api_base_url=api_base_url, **kwargs)


# Função de conveniência para feedback rápido
def quick_feedback_buttons(response_id: str, 
                         api_base_url: str = None,
                         key_prefix: str = "quick") -> bool:
    """
    Função de conveniência para renderizar botões de feedback rápido
    
    Args:
        response_id: ID da resposta
        api_base_url: URL da API
        key_prefix: Prefixo para as chaves
        
    Returns:
        True se feedback foi dado
    """
    feedback_system = create_feedback_system(api_base_url=api_base_url)
    return feedback_system.render_quick_feedback(response_id, key_prefix=key_prefix) 