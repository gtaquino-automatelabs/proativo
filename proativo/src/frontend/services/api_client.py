import streamlit as st
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import os
from .http_service import HTTPService, create_http_service
from components.error_handler import safe_api_call

class APIClient:
    """Cliente da API PROAtivo que centraliza toda comunicação com o backend"""
    
    def __init__(self, base_url: str = None):
        """
        Inicializa o cliente da API
        
        Args:
            base_url: URL base da API (usa variável de ambiente se não fornecida)
        """
        self.base_url = base_url or os.getenv("API_BASE_URL", "http://localhost:8000")
        self.http_service = create_http_service(self.base_url)
        self._initialize_session()
    
    def _initialize_session(self):
        """Inicializa dados específicos da API na sessão"""
        if "api_client_stats" not in st.session_state:
            st.session_state.api_client_stats = {
                "chat_requests": 0,
                "feedback_requests": 0,
                "health_checks": 0,
                "last_successful_request": None,
                "api_version": None
            }
    
    def _update_endpoint_stats(self, endpoint_type: str, success: bool = True):
        """Atualiza estatísticas específicas por endpoint"""
        stats = st.session_state.api_client_stats
        
        if endpoint_type in stats:
            stats[endpoint_type] += 1
        
        if success:
            stats["last_successful_request"] = datetime.now()
    
    # =============================================================================
    # ENDPOINTS DE CHAT
    # =============================================================================
    
    def send_chat_message(self, 
                         query: str, 
                         user_id: str = "streamlit_user",
                         context: Dict = None) -> Tuple[str, bool]:
        """
        Envia mensagem para o chat da API
        
        Args:
            query: Pergunta do usuário
            user_id: ID do usuário
            context: Contexto adicional
            
        Returns:
            Tupla (resposta, sucesso)
        """
        payload = {
            "message": query
            # Note: session_id removido - será None (opcional)
        }
        
        if context:
            payload["context"] = context
        
        def _make_chat_request():
            response, success = self.http_service.post("/api/v1/chat/", data=payload)
            if success:
                self._update_endpoint_stats("chat_requests")
                return response.get("response", "Erro: Resposta vazia da API")
            return None
        
        # Usa safe_api_call com fallback
        fallback_response = ("🤖 **Sistema Offline**: O assistente de IA está temporariamente "
                           "indisponível. Tente novamente em alguns minutos ou consulte a "
                           "documentação na seção 'Ajuda'.")
        
        result, success = safe_api_call(
            _make_chat_request,
            fallback_response=fallback_response,
            user_action=f"enviar mensagem de chat: '{query[:50]}...'"
        )
        
        return result, success
    
    def get_chat_history(self, 
                        user_id: str = "streamlit_user",
                        limit: int = 50) -> Tuple[List[Dict], bool]:
        """
        Recupera histórico de chat do usuário
        
        Args:
            user_id: ID do usuário
            limit: Número máximo de mensagens
            
        Returns:
            Tupla (lista_mensagens, sucesso)
        """
        params = {
            "user_id": user_id,
            "limit": limit
        }
        
        def _get_history():
            response, success = self.http_service.get("/api/v1/chat/history", params=params, use_cache=True)
            if success:
                return response.get("messages", [])
            return []
        
        result, success = safe_api_call(
            _get_history,
            fallback_response=[],
            user_action="recuperar histórico de chat"
        )
        
        return result, success
    
    # =============================================================================
    # ENDPOINTS DE FEEDBACK
    # =============================================================================
    
    def send_feedback(self,
                     response_id: str,
                     rating: str,
                     comment: str = None,
                     user_id: str = "streamlit_user") -> Tuple[bool, str]:
        """
        Envia feedback sobre uma resposta
        
        Args:
            response_id: ID da resposta avaliada
            rating: Avaliação (positive/negative)
            comment: Comentário opcional
            user_id: ID do usuário
            
        Returns:
            Tupla (sucesso, mensagem)
        """
        payload = {
            "response_id": response_id,
            "rating": rating,
            "user_id": user_id
        }
        
        if comment:
            payload["comment"] = comment
        
        def _send_feedback():
            response, success = self.http_service.post("/api/v1/feedback/", data=payload)
            if success:
                self._update_endpoint_stats("feedback_requests")
                return True, "Feedback enviado com sucesso!"
            return False, "Erro ao enviar feedback"
        
        result, success = safe_api_call(
            _send_feedback,
            fallback_response=(False, "Sistema offline - feedback será enviado quando possível"),
            user_action="enviar feedback"
        )
        
        return result if success else (False, "Erro na comunicação")
    
    def get_feedback_stats(self, user_id: str = None) -> Tuple[Dict, bool]:
        """
        Recupera estatísticas de feedback
        
        Args:
            user_id: ID do usuário (opcional, retorna stats globais se None)
            
        Returns:
            Tupla (estatísticas, sucesso)
        """
        params = {}
        if user_id:
            params["user_id"] = user_id
        
        def _get_stats():
            response, success = self.http_service.get("/api/v1/feedback/stats", params=params, use_cache=True)
            if success:
                return response
            return {}
        
        result, success = safe_api_call(
            _get_stats,
            fallback_response={"total": 0, "positive": 0, "negative": 0},
            user_action="recuperar estatísticas de feedback"
        )
        
        return result, success
    
    # =============================================================================
    # ENDPOINTS DE SISTEMA
    # =============================================================================
    
    def health_check(self) -> Tuple[Dict, bool]:
        """
        Verifica saúde da API
        
        Returns:
            Tupla (status, sucesso)
        """
        def _health_check():
            response, success = self.http_service.health_check()
            if success:
                self._update_endpoint_stats("health_checks")
            return response
        
        result, success = safe_api_call(
            _health_check,
            fallback_response={"status": "offline", "message": "API indisponível"},
            user_action="verificar saúde da API"
        )
        
        return result, success
    
    def get_api_info(self) -> Tuple[Dict, bool]:
        """
        Recupera informações da API
        
        Returns:
            Tupla (informações, sucesso)
        """
        def _get_info():
            response, success = self.http_service.get("/", use_cache=True, cache_duration=30)
            if success and "version" in response:
                st.session_state.api_client_stats["api_version"] = response.get("version")
            return response
        
        result, success = safe_api_call(
            _get_info,
            fallback_response={"name": "PROAtivo API", "status": "unknown"},
            user_action="recuperar informações da API"
        )
        
        return result, success
    
    # =============================================================================
    # ENDPOINTS DE DADOS
    # =============================================================================
    
    def search_equipment(self, 
                        query: str = None,
                        equipment_id: str = None,
                        limit: int = 10) -> Tuple[List[Dict], bool]:
        """
        Busca equipamentos
        
        Args:
            query: Termo de busca
            equipment_id: ID específico do equipamento
            limit: Número máximo de resultados
            
        Returns:
            Tupla (lista_equipamentos, sucesso)
        """
        params = {"limit": limit}
        
        if query:
            params["query"] = query
        
        if equipment_id:
            params["equipment_id"] = equipment_id
        
        def _search():
            response, success = self.http_service.get("/api/v1/equipment/", params=params, use_cache=True)
            if success:
                return response.get("equipment", [])
            return []
        
        result, success = safe_api_call(
            _search,
            fallback_response=[],
            user_action=f"buscar equipamentos: '{query or equipment_id}'"
        )
        
        return result, success
    
    def get_maintenance_history(self, 
                               equipment_id: str = None,
                               limit: int = 20) -> Tuple[List[Dict], bool]:
        """
        Recupera histórico de manutenções
        
        Args:
            equipment_id: ID do equipamento (opcional)
            limit: Número máximo de registros
            
        Returns:
            Tupla (lista_manutencoes, sucesso)
        """
        params = {"limit": limit}
        
        if equipment_id:
            params["equipment_id"] = equipment_id
        
        def _get_maintenance():
            response, success = self.http_service.get("/api/v1/maintenance/", params=params, use_cache=True)
            if success:
                return response.get("maintenance", [])
            return []
        
        result, success = safe_api_call(
            _get_maintenance,
            fallback_response=[],
            user_action=f"recuperar histórico de manutenção: '{equipment_id or 'todos'}'"
        )
        
        return result, success
    
    # =============================================================================
    # MÉTODOS DE CONFIGURAÇÃO
    # =============================================================================
    
    def set_auth_token(self, token: str):
        """Define token de autenticação"""
        self.http_service.set_auth_token(token)
    
    def remove_auth_token(self):
        """Remove token de autenticação"""
        self.http_service.remove_auth_token()
    
    def set_timeout(self, timeout: int):
        """Define timeout padrão"""
        self.http_service.set_timeout(timeout)
    
    def clear_cache(self):
        """Limpa cache de requisições"""
        self.http_service.clear_cache()
    
    # =============================================================================
    # ESTATÍSTICAS E MONITORAMENTO
    # =============================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas completas do cliente API"""
        http_stats = self.http_service.get_stats()
        api_stats = st.session_state.api_client_stats.copy()
        
        return {
            "http": http_stats,
            "api": api_stats,
            "combined": {
                "total_api_calls": api_stats["chat_requests"] + api_stats["feedback_requests"],
                "health_checks": api_stats["health_checks"],
                "last_success": api_stats["last_successful_request"],
                "cache_efficiency": http_stats["cache_hit_rate"],
                "reliability": http_stats["success_rate"]
            }
        }
    
    def show_connection_status(self):
        """Mostra status da conexão em formato amigável"""
        health, success = self.health_check()
        
        if success and health.get("status") == "healthy":
            st.success("🟢 **API Online** - Conectado com sucesso")
            
            # Mostra informações da API se disponível
            if st.session_state.api_client_stats["api_version"]:
                st.caption(f"Versão: {st.session_state.api_client_stats['api_version']}")
                
        elif success and health.get("status") != "healthy":
            st.warning("🟡 **API com Problemas** - Conexão instável")
            
        else:
            st.error("🔴 **API Offline** - Sem conexão")
        
        # Mostra estatísticas básicas
        stats = self.get_stats()
        if stats["http"]["total_requests"] > 0:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Requisições", stats["http"]["total_requests"])
            
            with col2:
                st.metric("Cache Hit", f"{stats['http']['cache_hit_rate']:.1f}%")
            
            with col3:
                st.metric("Sucesso", f"{stats['http']['success_rate']:.1f}%")
    
    def test_all_endpoints(self) -> Dict[str, bool]:
        """Testa conectividade com todos os endpoints principais"""
        results = {}
        
        # Testa health check
        _, success = self.health_check()
        results["health"] = success
        
        # Testa endpoint de informações da API
        _, success = self.get_api_info()
        results["info"] = success
        
        # Testa busca de equipamentos (sem parâmetros)
        _, success = self.search_equipment(limit=1)
        results["equipment"] = success
        
        # Testa histórico de manutenção (sem parâmetros)
        _, success = self.get_maintenance_history(limit=1)
        results["maintenance"] = success
        
        return results


def create_api_client(base_url: str = None) -> APIClient:
    """
    Factory function para criar instância do APIClient
    
    Args:
        base_url: URL base da API
        
    Returns:
        Instância configurada do APIClient
    """
    return APIClient(base_url) 