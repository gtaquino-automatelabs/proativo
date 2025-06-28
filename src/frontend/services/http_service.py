import streamlit as st
import requests
import time
import json
from typing import Dict, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import hashlib

class HTTPService:
    """Serviço HTTP base para gerenciar requisições com sessões, cache e configurações"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Inicializa o serviço HTTP
        
        Args:
            base_url: URL base da API
        """
        self.base_url = base_url.rstrip('/')
        self.session = self._create_session()
        self.default_timeout = 30
        self.default_headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'PROAtivo-Frontend/1.0'
        }
        
        self._initialize_cache()
    
    def _create_session(self) -> requests.Session:
        """Cria sessão HTTP com configurações otimizadas"""
        session = requests.Session()
        
        # Estratégia de retry
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            backoff_factor=1
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _initialize_cache(self):
        """Inicializa sistema de cache na sessão"""
        if "http_cache" not in st.session_state:
            st.session_state.http_cache = {}
        
        if "http_stats" not in st.session_state:
            st.session_state.http_stats = {
                "total_requests": 0,
                "cached_requests": 0,
                "failed_requests": 0,
                "average_response_time": 0,
                "last_request_time": None
            }
    
    def _generate_cache_key(self, method: str, url: str, data: Dict = None, params: Dict = None) -> str:
        """Gera chave única para cache baseada na requisição"""
        cache_data = {
            "method": method,
            "url": url,
            "data": data,
            "params": params
        }
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str, max_age_minutes: int = 5) -> Optional[Dict]:
        """Recupera dados do cache se ainda válidos"""
        cache = st.session_state.http_cache
        
        if cache_key in cache:
            cache_entry = cache[cache_key]
            cache_time = cache_entry["timestamp"]
            max_age = timedelta(minutes=max_age_minutes)
            
            if datetime.now() - cache_time < max_age:
                return cache_entry["data"]
            else:
                # Remove entrada expirada
                del cache[cache_key]
        
        return None
    
    def _save_to_cache(self, cache_key: str, data: Dict):
        """Salva dados no cache"""
        cache = st.session_state.http_cache
        
        cache[cache_key] = {
            "data": data,
            "timestamp": datetime.now()
        }
        
        # Limita cache a 100 entradas
        if len(cache) > 100:
            # Remove a entrada mais antiga
            oldest_key = min(cache.keys(), key=lambda k: cache[k]["timestamp"])
            del cache[oldest_key]
    
    def _update_stats(self, response_time: float, cached: bool = False, failed: bool = False):
        """Atualiza estatísticas de requisições"""
        stats = st.session_state.http_stats
        
        stats["total_requests"] += 1
        stats["last_request_time"] = datetime.now()
        
        if cached:
            stats["cached_requests"] += 1
        
        if failed:
            stats["failed_requests"] += 1
        
        # Atualiza tempo médio de resposta
        if not cached and not failed:
            current_avg = stats["average_response_time"]
            total_requests = stats["total_requests"] - stats["cached_requests"]
            
            if total_requests > 1:
                stats["average_response_time"] = (
                    (current_avg * (total_requests - 1) + response_time) / total_requests
                )
            else:
                stats["average_response_time"] = response_time
    
    def request(self,
                method: str,
                endpoint: str,
                data: Dict = None,
                params: Dict = None,
                headers: Dict = None,
                timeout: int = None,
                use_cache: bool = False,
                cache_duration: int = 5) -> Tuple[Dict, bool]:
        """
        Executa requisição HTTP
        
        Args:
            method: Método HTTP (GET, POST, etc.)
            endpoint: Endpoint da API (sem base_url)
            data: Dados para enviar no body
            params: Parâmetros de query string
            headers: Headers adicionais
            timeout: Timeout específico
            use_cache: Se deve usar cache para esta requisição
            cache_duration: Duração do cache em minutos
            
        Returns:
            Tupla (response_data, success)
        """
        start_time = time.time()
        
        # Prepara URL completa
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Prepara headers
        request_headers = self.default_headers.copy()
        if headers:
            request_headers.update(headers)
        
        # Verifica cache se habilitado
        if use_cache and method.upper() == "GET":
            cache_key = self._generate_cache_key(method, url, data, params)
            cached_response = self._get_from_cache(cache_key, cache_duration)
            
            if cached_response:
                self._update_stats(0, cached=True)
                return cached_response, True
        
        try:
            # Executa requisição
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=request_headers,
                timeout=timeout or self.default_timeout
            )
            
            response_time = time.time() - start_time
            
            # Verifica se a requisição foi bem-sucedida
            response.raise_for_status()
            
            # Processa resposta
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = {"message": response.text}
            
            # Salva no cache se aplicável
            if use_cache and method.upper() == "GET":
                cache_key = self._generate_cache_key(method, url, data, params)
                self._save_to_cache(cache_key, response_data)
            
            # Atualiza estatísticas
            self._update_stats(response_time)
            
            return response_data, True
            
        except requests.exceptions.RequestException as e:
            response_time = time.time() - start_time
            self._update_stats(response_time, failed=True)
            
            # Re-levanta a exceção para o error handler processar
            raise e
    
    def get(self, endpoint: str, params: Dict = None, use_cache: bool = True, **kwargs) -> Tuple[Dict, bool]:
        """Requisição GET com cache habilitado por padrão"""
        return self.request("GET", endpoint, params=params, use_cache=use_cache, **kwargs)
    
    def post(self, endpoint: str, data: Dict = None, **kwargs) -> Tuple[Dict, bool]:
        """Requisição POST"""
        return self.request("POST", endpoint, data=data, **kwargs)
    
    def put(self, endpoint: str, data: Dict = None, **kwargs) -> Tuple[Dict, bool]:
        """Requisição PUT"""
        return self.request("PUT", endpoint, data=data, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> Tuple[Dict, bool]:
        """Requisição DELETE"""
        return self.request("DELETE", endpoint, **kwargs)
    
    def patch(self, endpoint: str, data: Dict = None, **kwargs) -> Tuple[Dict, bool]:
        """Requisição PATCH"""
        return self.request("PATCH", endpoint, data=data, **kwargs)
    
    def post_file(self, endpoint: str, file_content: bytes, filename: str, 
                  form_data: Dict = None, **kwargs) -> Tuple[Dict, bool]:
        """
        Requisição POST para upload de arquivo
        
        Args:
            endpoint: Endpoint da API
            file_content: Conteúdo do arquivo em bytes
            filename: Nome do arquivo
            form_data: Dados adicionais do formulário
            
        Returns:
            Tupla (response_data, success)
        """
        start_time = time.time()
        
        # Prepara URL completa
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Prepara headers (sem Content-Type para multipart)
        request_headers = {k: v for k, v in self.default_headers.items() if k != "Content-Type"}
        
        try:
            # Prepara dados do formulário multipart
            files = {"file": (filename, file_content)}
            data = form_data or {}
            
            # Executa requisição
            response = self.session.post(
                url=url,
                files=files,
                data=data,
                headers=request_headers,
                timeout=kwargs.get("timeout", self.default_timeout)
            )
            
            response_time = time.time() - start_time
            
            # Verifica se a requisição foi bem-sucedida
            response.raise_for_status()
            
            # Processa resposta
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = {"message": response.text}
            
            # Atualiza estatísticas
            self._update_stats(response_time)
            
            return response_data, True
            
        except requests.exceptions.RequestException as e:
            response_time = time.time() - start_time
            self._update_stats(response_time, failed=True)
            
            # Re-levanta a exceção para o error handler processar
            raise e
    
    def health_check(self) -> Tuple[Dict, bool]:
        """Verifica saúde da API"""
        try:
            return self.get("/api/v1/health/", timeout=5, use_cache=False)
        except Exception:
            return {"status": "offline", "message": "API não disponível"}, False
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas de uso do serviço HTTP"""
        stats = st.session_state.http_stats.copy()
        
        # Calcula taxa de cache
        if stats["total_requests"] > 0:
            stats["cache_hit_rate"] = (stats["cached_requests"] / stats["total_requests"]) * 100
            stats["failure_rate"] = (stats["failed_requests"] / stats["total_requests"]) * 100
            stats["success_rate"] = 100 - stats["failure_rate"]
        else:
            stats["cache_hit_rate"] = 0
            stats["failure_rate"] = 0
            stats["success_rate"] = 0
        
        return stats
    
    def clear_cache(self):
        """Limpa cache de requisições"""
        st.session_state.http_cache.clear()
    
    def set_auth_token(self, token: str):
        """Define token de autenticação"""
        self.default_headers["Authorization"] = f"Bearer {token}"
    
    def remove_auth_token(self):
        """Remove token de autenticação"""
        self.default_headers.pop("Authorization", None)
    
    def set_timeout(self, timeout: int):
        """Define timeout padrão"""
        self.default_timeout = timeout
    
    def add_default_header(self, key: str, value: str):
        """Adiciona header padrão"""
        self.default_headers[key] = value
    
    def remove_default_header(self, key: str):
        """Remove header padrão"""
        self.default_headers.pop(key, None)


def create_http_service(base_url: str = "http://localhost:8000") -> HTTPService:
    """
    Factory function para criar instância do HTTPService
    
    Args:
        base_url: URL base da API
        
    Returns:
        Instância configurada do HTTPService
    """
    return HTTPService(base_url) 