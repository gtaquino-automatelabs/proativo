import streamlit as st
import re
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

class InputValidator:
    """Componente modular para validação de entradas do usuário"""
    
    def __init__(self):
        """Inicializa o validador com configurações padrão"""
        self.min_length = 1
        self.max_length = 1000
        self.allowed_chars = None
        self.forbidden_patterns = []
        self.required_patterns = []
        
        # Configurações padrão
        self.default_rules = {
            "min_length": 1,
            "max_length": 1000,
            "trim_whitespace": True,
            "allow_empty": False,
            "sanitize_html": True,
            "check_sql_injection": True,
            "check_xss": True
        }
        
        self._initialize_session()
    
    def _initialize_session(self):
        """Inicializa dados de validação na sessão"""
        if "validation_errors" not in st.session_state:
            st.session_state.validation_errors = {}
        
        if "validation_stats" not in st.session_state:
            st.session_state.validation_stats = {
                "total_validations": 0,
                "failed_validations": 0,
                "common_errors": {}
            }
    
    def validate_text_input(self, 
                           text: str,
                           field_name: str = "input",
                           rules: Dict[str, Any] = None) -> Tuple[bool, List[str]]:
        """
        Valida entrada de texto
        
        Args:
            text: Texto a ser validado
            field_name: Nome do campo para identificação
            rules: Regras específicas de validação
            
        Returns:
            Tupla (is_valid, error_messages)
        """
        if rules is None:
            rules = self.default_rules.copy()
        
        errors = []
        original_text = text
        
        # Incrementa contador de validações
        st.session_state.validation_stats["total_validations"] += 1
        
        # Remove espaços se configurado
        if rules.get("trim_whitespace", True):
            text = text.strip()
        
        # Verifica se está vazio
        if not text:
            if not rules.get("allow_empty", False):
                errors.append("⚠️ Este campo não pode estar vazio")
        
        # Verifica tamanho mínimo
        min_len = rules.get("min_length", self.min_length)
        if len(text) < min_len and text:
            errors.append(f"⚠️ Mínimo de {min_len} caracteres (atual: {len(text)})")
        
        # Verifica tamanho máximo
        max_len = rules.get("max_length", self.max_length)
        if len(text) > max_len:
            errors.append(f"⚠️ Máximo de {max_len} caracteres (atual: {len(text)})")
        
        # Verifica caracteres permitidos
        if rules.get("allowed_chars") and text:
            allowed_pattern = f"^[{re.escape(rules['allowed_chars'])}]*$"
            if not re.match(allowed_pattern, text):
                errors.append("⚠️ Contém caracteres não permitidos")
        
        # Verifica injeção SQL
        if rules.get("check_sql_injection", True) and text:
            sql_patterns = [
                r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
                r"(--|;|\*|'|\"|=|<|>)",
                r"(\bOR\b|\bAND\b).*(\b=\b|\bLIKE\b)"
            ]
            
            for pattern in sql_patterns:
                if re.search(pattern, text.upper()):
                    errors.append("🛡️ Detectados caracteres suspeitos (possível SQL injection)")
                    break
        
        # Verifica XSS
        if rules.get("check_xss", True) and text:
            xss_patterns = [
                r"<script[^>]*>.*?</script>",
                r"javascript:",
                r"on\w+\s*=",
                r"<iframe[^>]*>",
                r"<object[^>]*>",
                r"<embed[^>]*>"
            ]
            
            for pattern in xss_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    errors.append("🛡️ Detectado código suspeito (possível XSS)")
                    break
        
        # Verifica padrões obrigatórios
        for pattern_name, pattern in rules.get("required_patterns", {}).items():
            if not re.search(pattern, text):
                errors.append(f"⚠️ Deve conter {pattern_name}")
        
        # Verifica padrões proibidos
        for pattern_name, pattern in rules.get("forbidden_patterns", {}).items():
            if re.search(pattern, text):
                errors.append(f"⚠️ Não pode conter {pattern_name}")
        
        # Salva erros se houver
        is_valid = len(errors) == 0
        
        if not is_valid:
            st.session_state.validation_errors[field_name] = {
                "errors": errors,
                "timestamp": datetime.now(),
                "original_text": original_text
            }
            
            # Atualiza estatísticas
            st.session_state.validation_stats["failed_validations"] += 1
            
            for error in errors:
                error_type = error.split("⚠️")[-1].split("🛡️")[-1].strip()
                if error_type in st.session_state.validation_stats["common_errors"]:
                    st.session_state.validation_stats["common_errors"][error_type] += 1
                else:
                    st.session_state.validation_stats["common_errors"][error_type] = 1
        else:
            # Remove erros anteriores se validação passou
            if field_name in st.session_state.validation_errors:
                del st.session_state.validation_errors[field_name]
        
        return is_valid, errors
    
    def create_validated_text_input(self,
                                   label: str,
                                   key: str,
                                   placeholder: str = "",
                                   rules: Dict[str, Any] = None,
                                   help_text: str = None,
                                   show_counter: bool = True) -> Tuple[str, bool]:
        """
        Cria input de texto com validação em tempo real
        
        Args:
            label: Label do input
            key: Chave única do input
            placeholder: Texto placeholder
            rules: Regras de validação
            help_text: Texto de ajuda
            show_counter: Se deve mostrar contador de caracteres
            
        Returns:
            Tupla (text_value, is_valid)
        """
        if rules is None:
            rules = self.default_rules.copy()
        
        # Container para o input
        input_container = st.container()
        
        with input_container:
            # Input principal
            user_input = st.text_input(
                label,
                key=key,
                placeholder=placeholder,
                help=help_text,
                max_chars=rules.get("max_length", self.max_length)
            )
            
            # Validação em tempo real
            is_valid, errors = self.validate_text_input(user_input, key, rules)
            
            # Container para feedback
            feedback_container = st.container()
            
            with feedback_container:
                # Mostra contador de caracteres
                if show_counter and user_input:
                    char_count = len(user_input)
                    max_chars = rules.get("max_length", self.max_length)
                    
                    if char_count > max_chars * 0.8:  # Aviso quando próximo do limite
                        color = "🟡" if char_count <= max_chars else "🔴"
                    else:
                        color = "🟢"
                    
                    st.caption(f"{color} {char_count}/{max_chars} caracteres")
                
                # Mostra erros de validação
                if errors:
                    for error in errors:
                        st.error(error)
                elif user_input:  # Mostra sucesso apenas se há texto
                    st.success("✅ Entrada válida")
        
        return user_input, is_valid
    
    def create_validated_text_area(self,
                                  label: str,
                                  key: str,
                                  height: int = 100,
                                  placeholder: str = "",
                                  rules: Dict[str, Any] = None,
                                  help_text: str = None) -> Tuple[str, bool]:
        """
        Cria text area com validação
        
        Args:
            label: Label do text area
            key: Chave única
            height: Altura em pixels
            placeholder: Texto placeholder
            rules: Regras de validação
            help_text: Texto de ajuda
            
        Returns:
            Tupla (text_value, is_valid)
        """
        if rules is None:
            rules = self.default_rules.copy()
        
        # Input principal
        user_input = st.text_area(
            label,
            key=key,
            height=height,
            placeholder=placeholder,
            help=help_text,
            max_chars=rules.get("max_length", self.max_length)
        )
        
        # Validação
        is_valid, errors = self.validate_text_input(user_input, key, rules)
        
        # Feedback visual
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if errors:
                for error in errors:
                    st.error(error)
            elif user_input:
                st.success("✅ Entrada válida")
        
        with col2:
            if user_input:
                char_count = len(user_input)
                max_chars = rules.get("max_length", self.max_length)
                progress = min(char_count / max_chars, 1.0)
                
                st.metric("Caracteres", f"{char_count}/{max_chars}")
                st.progress(progress)
        
        return user_input, is_valid
    
    def create_chat_input_with_validation(self,
                                        placeholder: str = "Digite sua pergunta...",
                                        key: str = "chat_input_validated",
                                        max_length: int = 1000) -> Tuple[str, bool, bool]:
        """
        Cria input de chat com validação e botão
        
        Args:
            placeholder: Placeholder do input
            key: Chave única
            max_length: Tamanho máximo
            
        Returns:
            Tupla (user_input, is_valid, button_pressed)
        """
        rules = {
            "min_length": 1,
            "max_length": max_length,
            "trim_whitespace": True,
            "allow_empty": False,
            "check_sql_injection": True,
            "check_xss": True
        }
        
        # Layout em colunas
        col1, col2 = st.columns([4, 1])
        
        with col1:
            user_input, is_valid = self.create_validated_text_input(
                label="",
                key=key,
                placeholder=placeholder,
                rules=rules,
                show_counter=True
            )
        
        with col2:
            # Botão só fica habilitado se input é válido
            button_pressed = st.button(
                "📤 Enviar",
                key=f"{key}_button",
                disabled=not is_valid or not user_input.strip(),
                use_container_width=True,
                help="Enviar mensagem" if is_valid else "Corrija os erros antes de enviar"
            )
        
        return user_input, is_valid, button_pressed
    
    def show_validation_summary(self):
        """Mostra resumo das validações"""
        stats = st.session_state.validation_stats
        
        if stats["total_validations"] == 0:
            st.info("📊 Nenhuma validação realizada ainda")
            return
        
        success_rate = ((stats["total_validations"] - stats["failed_validations"]) / 
                       stats["total_validations"]) * 100
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total de Validações", stats["total_validations"])
        
        with col2:
            st.metric("Taxa de Sucesso", f"{success_rate:.1f}%")
        
        with col3:
            st.metric("Falhas", stats["failed_validations"])
        
        # Erros mais comuns
        if stats["common_errors"]:
            st.markdown("### 📋 Erros Mais Comuns")
            
            sorted_errors = sorted(
                stats["common_errors"].items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            for error_type, count in sorted_errors[:5]:
                st.markdown(f"- **{error_type}**: {count} ocorrências")
    
    def clear_validation_errors(self, field_name: str = None):
        """Limpa erros de validação"""
        if field_name:
            if field_name in st.session_state.validation_errors:
                del st.session_state.validation_errors[field_name]
        else:
            st.session_state.validation_errors.clear()
    
    def get_validation_errors(self, field_name: str = None) -> Dict:
        """Retorna erros de validação"""
        if field_name:
            return st.session_state.validation_errors.get(field_name, {})
        return st.session_state.validation_errors
    
    def create_validation_rules_ui(self) -> Dict[str, Any]:
        """Cria interface para configurar regras de validação"""
        st.markdown("### ⚙️ Configurar Regras de Validação")
        
        col1, col2 = st.columns(2)
        
        with col1:
            min_length = st.number_input(
                "Tamanho mínimo:",
                min_value=0,
                max_value=100,
                value=1,
                help="Número mínimo de caracteres"
            )
            
            max_length = st.number_input(
                "Tamanho máximo:",
                min_value=1,
                max_value=5000,
                value=1000,
                help="Número máximo de caracteres"
            )
            
            trim_whitespace = st.checkbox(
                "Remover espaços em branco",
                value=True,
                help="Remove espaços no início e fim"
            )
        
        with col2:
            allow_empty = st.checkbox(
                "Permitir entrada vazia",
                value=False,
                help="Permite campos vazios"
            )
            
            check_sql_injection = st.checkbox(
                "Verificar SQL injection",
                value=True,
                help="Detecta tentativas de injeção SQL"
            )
            
            check_xss = st.checkbox(
                "Verificar XSS",
                value=True,
                help="Detecta tentativas de Cross-Site Scripting"
            )
        
        return {
            "min_length": min_length,
            "max_length": max_length,
            "trim_whitespace": trim_whitespace,
            "allow_empty": allow_empty,
            "check_sql_injection": check_sql_injection,
            "check_xss": check_xss
        }
    
    def sanitize_input(self, text: str, aggressive: bool = False) -> str:
        """
        Sanitiza entrada do usuário
        
        Args:
            text: Texto a ser sanitizado
            aggressive: Se deve usar sanitização agressiva
            
        Returns:
            Texto sanitizado
        """
        if not text:
            return text
        
        # Remove tags HTML básicas
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove caracteres de controle
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        
        if aggressive:
            # Remove caracteres especiais perigosos
            text = re.sub(r'[<>&"\'%;()+=]', '', text)
            
            # Remove múltiplos espaços
            text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas de validação"""
        return st.session_state.validation_stats.copy()


def create_input_validator() -> InputValidator:
    """
    Factory function para criar uma instância do InputValidator
    
    Returns:
        Instância configurada do InputValidator
    """
    return InputValidator()


# Funções de conveniência
def validate_chat_input(text: str) -> Tuple[bool, List[str]]:
    """Função de conveniência para validar input de chat"""
    validator = create_input_validator()
    return validator.validate_text_input(text, "chat", {
        "min_length": 1,
        "max_length": 1000,
        "check_sql_injection": True,
        "check_xss": True
    })


def safe_chat_input(placeholder: str = "Digite sua mensagem...", key: str = "safe_chat") -> Tuple[str, bool, bool]:
    """Função de conveniência para input de chat seguro"""
    validator = create_input_validator()
    return validator.create_chat_input_with_validation(placeholder, key) 