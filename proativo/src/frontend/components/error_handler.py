import streamlit as st
import requests
import time
import traceback
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import json

class ErrorType(Enum):
    """Tipos de erro do sistema"""
    CONNECTION_ERROR = "connection_error"
    TIMEOUT_ERROR = "timeout_error"
    API_ERROR = "api_error"
    VALIDATION_ERROR = "validation_error"
    AUTHENTICATION_ERROR = "auth_error"
    SERVER_ERROR = "server_error"
    UNKNOWN_ERROR = "unknown_error"

class ErrorSeverity(Enum):
    """Níveis de severidade dos erros"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorHandler:
    """Sistema completo de tratamento de erros para frontend Streamlit"""
    
    def __init__(self):
        """Inicializa o tratador de erros"""
        self.max_retry_attempts = 3
        self.retry_delay = 1.0
        self.error_messages = self._initialize_error_messages()
        self.fallback_responses = self._initialize_fallback_responses()
        
        self._initialize_session()
    
    def _initialize_session(self):
        """Inicializa dados de erro na sessão"""
        if "error_log" not in st.session_state:
            st.session_state.error_log = []
        
        if "error_stats" not in st.session_state:
            st.session_state.error_stats = {
                "total_errors": 0,
                "errors_by_type": {},
                "errors_by_severity": {},
                "last_error": None,
                "recovery_attempts": 0,
                "successful_recoveries": 0
            }
        
        if "system_status" not in st.session_state:
            st.session_state.system_status = {
                "api_available": True,
                "last_check": None,
                "consecutive_failures": 0,
                "maintenance_mode": False
            }
    
    def _initialize_error_messages(self) -> Dict[ErrorType, Dict[str, str]]:
        """Inicializa mensagens amigáveis para cada tipo de erro"""
        return {
            ErrorType.CONNECTION_ERROR: {
                "title": "🌐 Problemas de Conexão",
                "message": "Não conseguimos conectar com o servidor. Verifique sua conexão com a internet.",
                "suggestion": "Tente novamente em alguns segundos ou verifique sua conexão.",
                "user_action": "Verificar conexão e tentar novamente"
            },
            ErrorType.TIMEOUT_ERROR: {
                "title": "⏱️ Tempo Limite Excedido",
                "message": "O servidor está demorando mais do que o esperado para responder.",
                "suggestion": "O sistema pode estar sobrecarregado. Tente uma consulta mais simples.",
                "user_action": "Aguardar e tentar novamente"
            },
            ErrorType.API_ERROR: {
                "title": "🔧 Erro no Processamento",
                "message": "Houve um problema ao processar sua solicitação.",
                "suggestion": "Tente reformular sua pergunta ou consulte a ajuda.",
                "user_action": "Reformular pergunta"
            },
            ErrorType.VALIDATION_ERROR: {
                "title": "✏️ Erro de Validação",
                "message": "Os dados enviados não atendem aos requisitos do sistema.",
                "suggestion": "Verifique se todos os campos estão preenchidos corretamente.",
                "user_action": "Corrigir dados e tentar novamente"
            },
            ErrorType.AUTHENTICATION_ERROR: {
                "title": "🔐 Erro de Autenticação",
                "message": "Problema com as credenciais de acesso ao sistema.",
                "suggestion": "Entre em contato com o administrador do sistema.",
                "user_action": "Contatar administrador"
            },
            ErrorType.SERVER_ERROR: {
                "title": "🚨 Erro do Servidor",
                "message": "O servidor encontrou um problema interno.",
                "suggestion": "Nossa equipe foi notificada. Tente novamente em alguns minutos.",
                "user_action": "Aguardar e tentar mais tarde"
            },
            ErrorType.UNKNOWN_ERROR: {
                "title": "❓ Erro Desconhecido",
                "message": "Ocorreu um erro inesperado no sistema.",
                "suggestion": "Se o problema persistir, entre em contato com o suporte.",
                "user_action": "Contatar suporte se persistir"
            }
        }
    
    def _initialize_fallback_responses(self) -> Dict[str, str]:
        """Inicializa respostas de fallback quando a API está indisponível"""
        return {
            "equipment_status": "🔧 **Sistema Offline**: Não posso consultar o status dos equipamentos no momento. Tente novamente em alguns minutos.",
            "maintenance_query": "📋 **Sistema Offline**: As informações de manutenção não estão disponíveis temporariamente. Consulte os registros físicos se necessário.",
            "general_query": "🤖 **Sistema Offline**: O assistente de IA está temporariamente indisponível. Você pode:\n\n• Tentar novamente em alguns minutos\n• Consultar a documentação na seção 'Ajuda'\n• Entrar em contato com o suporte técnico",
            "data_analysis": "📊 **Sistema Offline**: A análise de dados não está disponível no momento. Os relatórios podem ser acessados diretamente no banco de dados."
        }
    
    def classify_error(self, error: Exception, response: Optional[requests.Response] = None) -> tuple[ErrorType, ErrorSeverity]:
        """
        Classifica o tipo e severidade do erro
        
        Args:
            error: Exceção capturada
            response: Resposta HTTP se disponível
            
        Returns:
            Tupla (ErrorType, ErrorSeverity)
        """
        if isinstance(error, requests.exceptions.ConnectionError):
            return ErrorType.CONNECTION_ERROR, ErrorSeverity.HIGH
        
        elif isinstance(error, requests.exceptions.Timeout):
            return ErrorType.TIMEOUT_ERROR, ErrorSeverity.MEDIUM
        
        elif isinstance(error, requests.exceptions.HTTPError):
            if response:
                if response.status_code == 401:
                    return ErrorType.AUTHENTICATION_ERROR, ErrorSeverity.HIGH
                elif response.status_code >= 500:
                    return ErrorType.SERVER_ERROR, ErrorSeverity.HIGH
                elif response.status_code >= 400:
                    return ErrorType.API_ERROR, ErrorSeverity.MEDIUM
            
            return ErrorType.API_ERROR, ErrorSeverity.MEDIUM
        
        elif "validation" in str(error).lower():
            return ErrorType.VALIDATION_ERROR, ErrorSeverity.LOW
        
        else:
            return ErrorType.UNKNOWN_ERROR, ErrorSeverity.MEDIUM
    
    def log_error(self, 
                  error: Exception,
                  error_type: ErrorType,
                  severity: ErrorSeverity,
                  context: Dict[str, Any] = None,
                  user_action: str = None):
        """
        Registra erro no log da sessão
        
        Args:
            error: Exceção capturada
            error_type: Tipo do erro
            severity: Severidade do erro
            context: Contexto adicional
            user_action: Ação que o usuário estava tentando realizar
        """
        error_entry = {
            "timestamp": datetime.now(),
            "type": error_type.value,
            "severity": severity.value,
            "message": str(error),
            "traceback": traceback.format_exc(),
            "context": context or {},
            "user_action": user_action,
            "resolved": False
        }
        
        # Adiciona ao log
        st.session_state.error_log.append(error_entry)
        
        # Mantém apenas os últimos 100 erros
        if len(st.session_state.error_log) > 100:
            st.session_state.error_log = st.session_state.error_log[-100:]
        
        # Atualiza estatísticas
        stats = st.session_state.error_stats
        stats["total_errors"] += 1
        stats["last_error"] = error_entry
        
        # Contabiliza por tipo
        if error_type.value in stats["errors_by_type"]:
            stats["errors_by_type"][error_type.value] += 1
        else:
            stats["errors_by_type"][error_type.value] = 1
        
        # Contabiliza por severidade
        if severity.value in stats["errors_by_severity"]:
            stats["errors_by_severity"][severity.value] += 1
        else:
            stats["errors_by_severity"][severity.value] = 1
    
    def display_error(self, 
                      error_type: ErrorType,
                      severity: ErrorSeverity,
                      additional_context: str = None,
                      show_retry_button: bool = True,
                      retry_callback: Callable = None) -> bool:
        """
        Exibe erro com interface amigável
        
        Args:
            error_type: Tipo do erro
            severity: Severidade do erro
            additional_context: Contexto adicional
            show_retry_button: Se deve mostrar botão de retry
            retry_callback: Função para retry
            
        Returns:
            True se usuário clicou em retry
        """
        error_info = self.error_messages[error_type]
        
        # Escolhe o tipo de alerta baseado na severidade
        if severity == ErrorSeverity.CRITICAL:
            alert_func = st.error
            icon = "🚨"
        elif severity == ErrorSeverity.HIGH:
            alert_func = st.error
            icon = "❌"
        elif severity == ErrorSeverity.MEDIUM:
            alert_func = st.warning
            icon = "⚠️"
        else:
            alert_func = st.info
            icon = "ℹ️"
        
        # Container para o erro
        error_container = st.container()
        
        with error_container:
            # Título do erro
            st.markdown(f"### {icon} {error_info['title']}")
            
            # Mensagem principal
            alert_func(error_info['message'])
            
            # Contexto adicional se fornecido
            if additional_context:
                st.markdown(f"**Detalhes:** {additional_context}")
            
            # Sugestão
            st.info(f"💡 **Sugestão:** {error_info['suggestion']}")
            
            # Ações recomendadas
            st.markdown(f"🎯 **Ação recomendada:** {error_info['user_action']}")
            
            # Botões de ação
            col1, col2, col3 = st.columns([1, 1, 2])
            
            retry_clicked = False
            
            if show_retry_button:
                with col1:
                    if st.button("🔄 Tentar Novamente", key=f"retry_{time.time()}"):
                        retry_clicked = True
                        if retry_callback:
                            retry_callback()
            
            with col2:
                if st.button("📋 Ver Detalhes", key=f"details_{time.time()}"):
                    self._show_error_details()
            
            with col3:
                if st.button("❓ Precisa de Ajuda?", key=f"help_{time.time()}"):
                    self._show_help_options(error_type)
        
        return retry_clicked
    
    def handle_api_request(self,
                          request_func: Callable,
                          *args,
                          fallback_response: str = None,
                          user_action: str = "fazer requisição",
                          **kwargs) -> tuple[Any, bool]:
        """
        Executa requisição com tratamento automático de erros e retry
        
        Args:
            request_func: Função que faz a requisição
            fallback_response: Resposta de fallback se tudo falhar
            user_action: Descrição da ação do usuário
            *args, **kwargs: Argumentos para a função
            
        Returns:
            Tupla (resultado, sucesso)
        """
        last_error = None
        
        for attempt in range(self.max_retry_attempts):
            try:
                # Atualiza status da tentativa se for retry
                if attempt > 0:
                    st.session_state.error_stats["recovery_attempts"] += 1
                    
                    with st.spinner(f"⏳ Tentativa {attempt + 1}/{self.max_retry_attempts}..."):
                        time.sleep(self.retry_delay * attempt)  # Backoff exponencial
                
                # Executa a requisição
                result = request_func(*args, **kwargs)
                
                # Se chegou aqui, foi sucesso
                if attempt > 0:
                    st.session_state.error_stats["successful_recoveries"] += 1
                    st.success(f"✅ Recuperação bem-sucedida na tentativa {attempt + 1}!")
                
                self._update_system_status(True)
                return result, True
                
            except Exception as error:
                last_error = error
                error_type, severity = self.classify_error(error)
                
                # Registra o erro
                self.log_error(
                    error=error,
                    error_type=error_type,
                    severity=severity,
                    context={
                        "attempt": attempt + 1,
                        "max_attempts": self.max_retry_attempts,
                        "function": request_func.__name__ if hasattr(request_func, '__name__') else str(request_func)
                    },
                    user_action=user_action
                )
                
                # Se é o último attempt ou erro crítico, para
                if attempt == self.max_retry_attempts - 1 or severity == ErrorSeverity.CRITICAL:
                    break
                
                # Mostra aviso para tentativas intermediárias
                if attempt < self.max_retry_attempts - 1:
                    st.warning(f"⚠️ Tentativa {attempt + 1} falhou. Tentando novamente...")
        
        # Todas as tentativas falharam
        self._update_system_status(False)
        
        if last_error:
            error_type, severity = self.classify_error(last_error)
            
            # Exibe erro final
            self.display_error(
                error_type=error_type,
                severity=severity,
                additional_context=f"Falha após {self.max_retry_attempts} tentativas",
                show_retry_button=False
            )
        
        # Retorna fallback se disponível
        if fallback_response:
            st.info("🔄 **Modo Offline**: Usando resposta alternativa")
            return fallback_response, False
        
        return None, False
    
    def _update_system_status(self, success: bool):
        """Atualiza status do sistema baseado no sucesso/falha"""
        status = st.session_state.system_status
        status["last_check"] = datetime.now()
        
        if success:
            status["api_available"] = True
            status["consecutive_failures"] = 0
        else:
            status["consecutive_failures"] += 1
            
            # Considera API indisponível após 3 falhas consecutivas
            if status["consecutive_failures"] >= 3:
                status["api_available"] = False
    
    def show_system_status(self):
        """Mostra status atual do sistema"""
        status = st.session_state.system_status
        
        if status["api_available"]:
            st.success("🟢 **Sistema Online** - Todos os serviços funcionando normalmente")
        else:
            st.error("🔴 **Sistema com Problemas** - Alguns serviços podem estar indisponíveis")
        
        if status["last_check"]:
            time_ago = datetime.now() - status["last_check"]
            st.caption(f"🕒 Última verificação: {time_ago.seconds}s atrás")
        
        # Mostra falhas consecutivas se houver
        if status["consecutive_failures"] > 0:
            st.warning(f"⚠️ {status['consecutive_failures']} falhas consecutivas detectadas")
    
    def show_error_statistics(self):
        """Exibe estatísticas de erro"""
        stats = st.session_state.error_stats
        
        if stats["total_errors"] == 0:
            st.info("📊 Nenhum erro registrado ainda")
            return
        
        st.markdown("### 📊 Estatísticas de Erros")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total de Erros", stats["total_errors"])
        
        with col2:
            if stats["recovery_attempts"] > 0:
                recovery_rate = (stats["successful_recoveries"] / stats["recovery_attempts"]) * 100
                st.metric("Taxa de Recuperação", f"{recovery_rate:.1f}%")
            else:
                st.metric("Taxa de Recuperação", "N/A")
        
        with col3:
            if stats["last_error"]:
                last_time = stats["last_error"]["timestamp"].strftime("%H:%M:%S")
                st.metric("Último Erro", last_time)
        
        # Gráfico de erros por tipo
        if stats["errors_by_type"]:
            st.markdown("#### 📈 Erros por Tipo")
            
            for error_type, count in stats["errors_by_type"].items():
                percentage = (count / stats["total_errors"]) * 100
                st.markdown(f"- **{error_type.replace('_', ' ').title()}**: {count} ({percentage:.1f}%)")
    
    def _show_error_details(self):
        """Mostra detalhes do último erro"""
        stats = st.session_state.error_stats
        
        if not stats["last_error"]:
            st.info("Nenhum erro registrado")
            return
        
        error = stats["last_error"]
        
        with st.expander("🔍 Detalhes Técnicos do Erro", expanded=True):
            st.markdown(f"**Tipo:** {error['type']}")
            st.markdown(f"**Severidade:** {error['severity']}")
            st.markdown(f"**Timestamp:** {error['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
            st.markdown(f"**Ação do Usuário:** {error['user_action']}")
            
            if error['context']:
                st.markdown("**Contexto:**")
                st.json(error['context'])
            
            st.markdown("**Stack Trace:**")
            st.code(error['traceback'], language='python')
    
    def _show_help_options(self, error_type: ErrorType):
        """Mostra opções de ajuda baseadas no tipo de erro"""
        st.markdown("### 🆘 Opções de Ajuda")
        
        help_options = {
            ErrorType.CONNECTION_ERROR: [
                "Verificar conexão com a internet",
                "Tentar usar uma rede diferente",
                "Verificar se não há bloqueios de firewall",
                "Contatar administrador de rede"
            ],
            ErrorType.TIMEOUT_ERROR: [
                "Tentar uma consulta mais simples",
                "Aguardar alguns minutos e tentar novamente",
                "Verificar se há manutenção programada",
                "Reportar problema se persistir"
            ],
            ErrorType.API_ERROR: [
                "Reformular a pergunta de forma diferente",
                "Verificar se os dados estão corretos",
                "Consultar a documentação de API",
                "Contatar suporte técnico"
            ]
        }
        
        options = help_options.get(error_type, [
            "Consultar a documentação do sistema",
            "Entrar em contato com suporte técnico",
            "Verificar fóruns da comunidade",
            "Reportar o problema"
        ])
        
        for option in options:
            st.markdown(f"• {option}")
    
    def clear_error_log(self):
        """Limpa o log de erros"""
        st.session_state.error_log.clear()
        st.session_state.error_stats = {
            "total_errors": 0,
            "errors_by_type": {},
            "errors_by_severity": {},
            "last_error": None,
            "recovery_attempts": 0,
            "successful_recoveries": 0
        }
    
    def export_error_log(self) -> str:
        """Exporta log de erros como JSON"""
        # Converte datetime para string para serialização
        export_data = []
        for error in st.session_state.error_log:
            error_copy = error.copy()
            error_copy["timestamp"] = error["timestamp"].isoformat()
            export_data.append(error_copy)
        
        return json.dumps(export_data, indent=2, ensure_ascii=False)
    
    def get_fallback_response(self, query_type: str = "general_query") -> str:
        """Retorna resposta de fallback para quando a API está indisponível"""
        return self.fallback_responses.get(query_type, self.fallback_responses["general_query"])


def create_error_handler() -> ErrorHandler:
    """
    Factory function para criar instância do ErrorHandler
    
    Returns:
        Instância configurada do ErrorHandler
    """
    return ErrorHandler()


# Decorador para tratamento automático de erros
def handle_errors(fallback_response: str = None, user_action: str = "executar ação"):
    """
    Decorador para tratamento automático de erros em funções
    
    Args:
        fallback_response: Resposta de fallback
        user_action: Descrição da ação do usuário
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            if "error_handler" not in st.session_state:
                st.session_state.error_handler = create_error_handler()
            
            handler = st.session_state.error_handler
            
            try:
                return func(*args, **kwargs)
            except Exception as error:
                error_type, severity = handler.classify_error(error)
                
                handler.log_error(
                    error=error,
                    error_type=error_type,
                    severity=severity,
                    user_action=user_action
                )
                
                handler.display_error(
                    error_type=error_type,
                    severity=severity,
                    show_retry_button=False
                )
                
                if fallback_response:
                    st.info("🔄 Usando resposta alternativa:")
                    st.write(fallback_response)
                    return fallback_response
                
                return None
        
        return wrapper
    return decorator


# Funções de conveniência
def safe_api_call(request_func: Callable, *args, **kwargs):
    """Função de conveniência para chamadas de API seguras"""
    if "error_handler" not in st.session_state:
        st.session_state.error_handler = create_error_handler()
    
    handler = st.session_state.error_handler
    return handler.handle_api_request(request_func, *args, **kwargs)


def show_error_dashboard():
    """Mostra dashboard completo de erros"""
    if "error_handler" not in st.session_state:
        st.session_state.error_handler = create_error_handler()
    
    handler = st.session_state.error_handler
    
    st.markdown("## 🚨 Dashboard de Erros")
    
    # Status do sistema
    handler.show_system_status()
    st.markdown("---")
    
    # Estatísticas
    handler.show_error_statistics()
    st.markdown("---")
    
    # Ações de gerenciamento
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🧹 Limpar Log de Erros"):
            handler.clear_error_log()
            st.success("Log de erros limpo!")
    
    with col2:
        if st.button("📥 Exportar Log"):
            log_data = handler.export_error_log()
            st.download_button(
                label="💾 Download JSON",
                data=log_data,
                file_name=f"error_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
