import streamlit as st
import time
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
import threading

class LoadingIndicator:
    """Componente modular para indicadores de loading no Streamlit"""
    
    def __init__(self):
        """Inicializa o componente de loading"""
        self._initialize_session()
    
    def _initialize_session(self):
        """Inicializa variáveis da sessão para controle de loading"""
        if "loading_states" not in st.session_state:
            st.session_state.loading_states = {}
        
        if "loading_history" not in st.session_state:
            st.session_state.loading_history = []
    
    @contextmanager
    def spinner(self, 
                message: str = "Processando...",
                icon: str = "🤔",
                show_time: bool = True):
        """
        Context manager para spinner com tempo
        
        Args:
            message: Mensagem a ser exibida
            icon: Ícone a ser usado
            show_time: Se deve mostrar tempo decorrido
        """
        start_time = time.time()
        
        display_message = f"{icon} {message}"
        if show_time:
            placeholder = st.empty()
            
            def update_timer():
                elapsed = time.time() - start_time
                placeholder.markdown(f"⏱️ **{display_message}** (⏳ {elapsed:.1f}s)")
            
            # Atualiza o timer inicial
            update_timer()
            
            try:
                with st.spinner(display_message):
                    yield
            finally:
                elapsed = time.time() - start_time
                placeholder.markdown(f"✅ **Concluído!** (⏳ {elapsed:.1f}s)")
                time.sleep(1)  # Mostra por 1 segundo
                placeholder.empty()
        else:
            with st.spinner(display_message):
                yield
    
    def progress_bar(self, 
                    steps: List[str],
                    current_step: int = 0,
                    title: str = "Progresso",
                    show_percentage: bool = True) -> st.delta_generator.DeltaGenerator:
        """
        Cria uma barra de progresso com etapas
        
        Args:
            steps: Lista de etapas do processo
            current_step: Etapa atual (0-based)
            title: Título da barra de progresso
            show_percentage: Se deve mostrar percentual
            
        Returns:
            Container da barra de progresso para atualizações
        """
        total_steps = len(steps)
        progress_value = current_step / total_steps if total_steps > 0 else 0
        
        container = st.container()
        
        with container:
            if title:
                st.markdown(f"**{title}**")
            
            # Barra de progresso
            progress_bar = st.progress(progress_value)
            
            # Informações da etapa atual
            if current_step < total_steps:
                current_step_name = steps[current_step]
                st.markdown(f"📍 **Etapa atual:** {current_step_name}")
            
            # Percentual e contagem
            if show_percentage:
                percentage = progress_value * 100
                st.caption(f"⚡ {percentage:.0f}% completo ({current_step}/{total_steps} etapas)")
            
            # Lista de etapas com status
            with st.expander("📋 Detalhes das etapas"):
                for i, step in enumerate(steps):
                    if i < current_step:
                        st.markdown(f"✅ {step}")
                    elif i == current_step:
                        st.markdown(f"⏳ **{step}** (atual)")
                    else:
                        st.markdown(f"⏸️ {step}")
        
        return container
    
    def status_indicator(self, 
                        status: str,
                        message: str,
                        details: str = None,
                        show_time: bool = True) -> None:
        """
        Mostra um indicador de status
        
        Args:
            status: 'loading', 'success', 'error', 'warning', 'info'
            message: Mensagem principal
            details: Detalhes adicionais (opcional)
            show_time: Se deve mostrar timestamp
        """
        timestamp = time.strftime("%H:%M:%S") if show_time else ""
        
        status_config = {
            "loading": {"icon": "⏳", "color": "blue", "method": st.info},
            "success": {"icon": "✅", "color": "green", "method": st.success},
            "error": {"icon": "❌", "color": "red", "method": st.error},
            "warning": {"icon": "⚠️", "color": "orange", "method": st.warning},
            "info": {"icon": "ℹ️", "color": "blue", "method": st.info}
        }
        
        config = status_config.get(status, status_config["info"])
        
        display_message = f"{config['icon']} {message}"
        if timestamp:
            display_message += f" ({timestamp})"
        
        if details:
            display_message += f"\n\n📝 {details}"
        
        config["method"](display_message)
    
    def api_connection_status(self, 
                            api_url: str,
                            timeout: int = 3,
                            show_details: bool = True) -> bool:
        """
        Mostra status de conexão com API em tempo real
        
        Args:
            api_url: URL da API para testar
            timeout: Timeout para o teste
            show_details: Se deve mostrar detalhes da conexão
            
        Returns:
            True se conectado, False caso contrário
        """
        import requests
        
        status_placeholder = st.empty()
        
        try:
            status_placeholder.markdown("⏳ **Testando conexão com API...**")
            
            start_time = time.time()
            response = requests.get(f"{api_url}/health", timeout=timeout)
            response_time = (time.time() - start_time) * 1000  # em ms
            
            if response.status_code == 200:
                if show_details:
                    status_placeholder.success(
                        f"✅ **API Online** \n"
                        f"📡 Tempo de resposta: {response_time:.0f}ms \n"
                        f"🔗 Status: {response.status_code}"
                    )
                else:
                    status_placeholder.success("✅ API Online")
                return True
            else:
                status_placeholder.error(f"❌ **API com problemas** \nStatus: {response.status_code}")
                return False
                
        except requests.exceptions.Timeout:
            status_placeholder.error("❌ **Timeout** - API demorou para responder")
            return False
        except requests.exceptions.ConnectionError:
            status_placeholder.error("❌ **Sem conexão** - API offline ou inacessível")
            return False
        except Exception as e:
            status_placeholder.error(f"❌ **Erro inesperado:** {str(e)}")
            return False
    
    def chat_typing_indicator(self, duration: float = 2.0) -> None:
        """
        Simula indicador de "digitando..." para chat
        
        Args:
            duration: Duração do efeito em segundos
        """
        placeholder = st.empty()
        
        # Animação de pontos
        for i in range(int(duration * 2)):  # 2 frames por segundo
            dots = "." * ((i % 3) + 1)
            placeholder.markdown(f"🤖 **Assistente está digitando{dots}**")
            time.sleep(0.5)
        
        placeholder.empty()
    
    def processing_steps(self, 
                        steps: List[Dict[str, Any]],
                        auto_advance: bool = False,
                        delay_between_steps: float = 1.0) -> None:
        """
        Executa uma sequência de etapas com indicadores visuais
        
        Args:
            steps: Lista de etapas com {'name', 'description', 'duration'?}
            auto_advance: Se deve avançar automaticamente
            delay_between_steps: Delay entre etapas
        """
        container = st.container()
        
        for i, step in enumerate(steps):
            with container:
                st.markdown(f"### Etapa {i+1}/{len(steps)}: {step['name']}")
                
                if step.get('description'):
                    st.markdown(step['description'])
                
                # Barra de progresso da etapa atual
                step_progress = st.progress(0)
                
                # Simula progresso da etapa
                duration = step.get('duration', 2.0)
                steps_count = 20  # 20 incrementos
                
                for j in range(steps_count + 1):
                    progress = j / steps_count
                    step_progress.progress(progress)
                    
                    if auto_advance:
                        time.sleep(duration / steps_count)
                
                # Marca como concluído
                st.success(f"✅ {step['name']} concluído!")
                
                if i < len(steps) - 1 and auto_advance:
                    time.sleep(delay_between_steps)
                elif i < len(steps) - 1 and not auto_advance:
                    st.button(f"➡️ Próxima etapa", key=f"next_step_{i}")
    
    def realtime_metrics(self, 
                        metrics: Dict[str, Any],
                        update_interval: float = 1.0,
                        auto_refresh: bool = True) -> None:
        """
        Mostra métricas em tempo real
        
        Args:
            metrics: Dicionário com métricas {nome: valor}
            update_interval: Intervalo de atualização em segundos
            auto_refresh: Se deve atualizar automaticamente
        """
        placeholder = st.empty()
        
        def update_metrics():
            with placeholder.container():
                cols = st.columns(len(metrics))
                
                for i, (name, value) in enumerate(metrics.items()):
                    with cols[i]:
                        # Simula variação nos valores (para demo)
                        import random
                        if isinstance(value, (int, float)):
                            display_value = value + random.uniform(-0.1, 0.1) * value
                            st.metric(name, f"{display_value:.1f}")
                        else:
                            st.metric(name, str(value))
        
        if auto_refresh:
            for _ in range(10):  # Atualiza 10 vezes
                update_metrics()
                time.sleep(update_interval)
        else:
            update_metrics()
    
    def save_loading_event(self, 
                          event_type: str,
                          duration: float,
                          success: bool = True,
                          details: str = None) -> None:
        """
        Salva evento de loading no histórico
        
        Args:
            event_type: Tipo do evento ('api_call', 'processing', etc.)
            duration: Duração em segundos
            success: Se foi bem-sucedido
            details: Detalhes adicionais
        """
        event = {
            "timestamp": time.time(),
            "type": event_type,
            "duration": duration,
            "success": success,
            "details": details or ""
        }
        
        st.session_state.loading_history.append(event)
        
        # Mantém apenas os últimos 50 eventos
        if len(st.session_state.loading_history) > 50:
            st.session_state.loading_history = st.session_state.loading_history[-50:]
    
    def get_loading_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas dos eventos de loading"""
        history = st.session_state.loading_history
        
        if not history:
            return {"total_events": 0}
        
        total_events = len(history)
        successful_events = len([e for e in history if e["success"]])
        avg_duration = sum(e["duration"] for e in history) / total_events
        
        return {
            "total_events": total_events,
            "successful_events": successful_events,
            "success_rate": (successful_events / total_events) * 100,
            "avg_duration": avg_duration,
            "last_event": history[-1] if history else None
        }


def create_loading_indicator() -> LoadingIndicator:
    """
    Factory function para criar uma instância do LoadingIndicator
    
    Returns:
        Instância configurada do LoadingIndicator
    """
    return LoadingIndicator()


# Funções de conveniência
def show_api_status(api_url: str, **kwargs) -> bool:
    """Função de conveniência para mostrar status da API"""
    loader = create_loading_indicator()
    return loader.api_connection_status(api_url, **kwargs)


def processing_spinner(message: str = "Processando...", **kwargs):
    """Função de conveniência para spinner de processamento"""
    loader = create_loading_indicator()
    return loader.spinner(message, **kwargs) 