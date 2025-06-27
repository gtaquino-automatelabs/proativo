"""
Componente de Diagnóstico do Sistema PROAtivo.

Este módulo fornece funcionalidades de diagnóstico e teste
diretamente pela interface Streamlit, incluindo:
- Teste do sistema de feedback
- Validação de componentes
- Verificação de conectividade
- Execução de scripts de teste
"""

import streamlit as st
import subprocess
import sys
import time
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime
import os

class SystemDiagnostics:
    """Classe para gerenciar diagnósticos do sistema"""
    
    def __init__(self):
        self.test_results = {}
        self.last_test_time = None
        
    def run_feedback_test(self) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Executa o teste de feedback do sistema.
        
        Returns:
            Tuple[bool, str, Dict]: (sucesso, output, detalhes)
        """
        try:
            # Caminho para o script de teste
            script_path = "scripts/testing/test_frontend_feedback.py"
            
            # Executa o script de teste
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=30,
                cwd="/app" if os.path.exists("/app") else "."
            )
            
            success = result.returncode == 0
            output = result.stdout if success else result.stderr
            
            # Parse dos resultados se possível
            details = self._parse_test_output(output)
            
            self.test_results["feedback_test"] = {
                "success": success,
                "output": output,
                "details": details,
                "timestamp": datetime.now().isoformat()
            }
            
            self.last_test_time = datetime.now()
            
            return success, output, details
            
        except subprocess.TimeoutExpired:
            error_msg = "⏰ Timeout: Teste demorou mais de 30 segundos"
            return False, error_msg, {"error": "timeout"}
            
        except Exception as e:
            error_msg = f"❌ Erro ao executar teste: {str(e)}"
            return False, error_msg, {"error": str(e)}
    
    def run_system_validation(self) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Executa validação completa do sistema.
        
        Returns:
            Tuple[bool, str, Dict]: (sucesso, output, detalhes)
        """
        try:
            script_path = "scripts/testing/validate_system.py"
            
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=60,
                cwd="/app" if os.path.exists("/app") else "."
            )
            
            success = result.returncode == 0
            output = result.stdout if success else result.stderr
            details = self._parse_validation_output(output)
            
            self.test_results["system_validation"] = {
                "success": success,
                "output": output,
                "details": details,
                "timestamp": datetime.now().isoformat()
            }
            
            return success, output, details
            
        except Exception as e:
            error_msg = f"❌ Erro na validação: {str(e)}"
            return False, error_msg, {"error": str(e)}
    
    def check_frontend_components(self) -> Dict[str, bool]:
        """
        Verifica se os componentes do frontend estão funcionando.
        
        Returns:
            Dict[str, bool]: Status de cada componente
        """
        components_status = {}
        
        try:
            # Testa import do sistema de feedback
            from components.feedback import FeedbackSystem, create_feedback_system
            components_status["feedback_system"] = True
        except Exception:
            components_status["feedback_system"] = False
        
        try:
            # Testa import do chat interface
            from components.chat_interface import create_chat_interface
            components_status["chat_interface"] = True
        except Exception:
            components_status["chat_interface"] = False
        
        try:
            # Testa import dos serviços de API
            from services.api_client import create_api_client
            components_status["api_client"] = True
        except Exception:
            components_status["api_client"] = False
        
        try:
            # Testa import do tema
            from components.theme import apply_professional_theme
            components_status["theme"] = True
        except Exception:
            components_status["theme"] = False
        
        return components_status
    
    def _parse_test_output(self, output: str) -> Dict[str, Any]:
        """Parse da saída do teste de feedback"""
        details = {
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "components_tested": []
        }
        
        lines = output.split('\n')
        for line in lines:
            if "✅" in line and "bem-sucedido" in line:
                details["tests_passed"] += 1
                if "FeedbackSystem" in line:
                    details["components_tested"].append("FeedbackSystem")
                elif "create_feedback_system" in line:
                    details["components_tested"].append("create_feedback_system")
            elif "❌" in line and "Erro" in line:
                details["tests_failed"] += 1
            elif "Testando" in line:
                details["tests_run"] += 1
        
        return details
    
    def _parse_validation_output(self, output: str) -> Dict[str, Any]:
        """Parse da saída da validação do sistema"""
        details = {
            "database_ok": False,
            "api_ok": False,
            "components_ok": False,
            "errors": []
        }
        
        lines = output.split('\n')
        for line in lines:
            if "Database" in line and "OK" in line:
                details["database_ok"] = True
            elif "API" in line and "OK" in line:
                details["api_ok"] = True
            elif "Components" in line and "OK" in line:
                details["components_ok"] = True
            elif "ERROR" in line or "Failed" in line:
                details["errors"].append(line.strip())
        
        return details
    
    def get_test_history(self) -> Dict[str, Any]:
        """Retorna histórico de testes executados"""
        return {
            "results": self.test_results,
            "last_test": self.last_test_time.isoformat() if self.last_test_time else None,
            "total_tests": len(self.test_results)
        }

def create_diagnostics_interface() -> SystemDiagnostics:
    """
    Cria interface de diagnóstico do sistema.
    
    Returns:
        SystemDiagnostics: Instância do sistema de diagnósticos
    """
    return SystemDiagnostics()

def render_diagnostics_page():
    """Renderiza a página completa de diagnósticos"""
    
    # Header
    st.markdown("### 🔧 Diagnóstico do Sistema")
    st.markdown("Execute testes e validações do sistema diretamente pela interface.")
    
    # Inicializa o sistema de diagnósticos
    if "diagnostics" not in st.session_state:
        st.session_state.diagnostics = create_diagnostics_interface()
    
    diagnostics = st.session_state.diagnostics
    
    # Tabs para organizar as funcionalidades
    tab1, tab2, tab3, tab4 = st.tabs([
        "🧪 Testes de Feedback", 
        "✅ Validação Completa", 
        "🔍 Componentes", 
        "📊 Histórico"
    ])
    
    with tab1:
        st.markdown("#### Teste do Sistema de Feedback")
        st.markdown("Executa o script de teste específico para validar o sistema de feedback.")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if st.button("🚀 Executar Teste de Feedback", type="primary", use_container_width=True):
                with st.spinner("Executando teste de feedback..."):
                    success, output, details = diagnostics.run_feedback_test()
                    
                    if success:
                        st.success("✅ Teste de feedback executado com sucesso!")
                        
                        # Mostra detalhes do teste
                        if details.get("tests_passed", 0) > 0:
                            st.metric("Testes Aprovados", details["tests_passed"])
                            
                        if details.get("components_tested"):
                            st.write("**Componentes testados:**")
                            for component in details["components_tested"]:
                                st.write(f"- ✅ {component}")
                        
                        # Mostra output completo em expander
                        with st.expander("📋 Log Completo do Teste"):
                            st.text(output)
                    else:
                        st.error("❌ Teste de feedback falhou!")
                        st.error(output)
        
        with col2:
            st.markdown("**Informações:**")
            st.info("Este teste verifica se o sistema de feedback está funcionando corretamente após as correções implementadas.")
    
    with tab2:
        st.markdown("#### Validação Completa do Sistema")
        st.markdown("Executa validação abrangente de todos os componentes.")
        
        if st.button("🔍 Executar Validação Completa", type="primary", use_container_width=True):
            with st.spinner("Executando validação completa do sistema..."):
                success, output, details = diagnostics.run_system_validation()
                
                if success:
                    st.success("✅ Validação completa executada com sucesso!")
                    
                    # Mostra status dos componentes
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        db_status = "✅ OK" if details.get("database_ok") else "❌ Erro"
                        st.metric("Database", db_status)
                    
                    with col2:
                        api_status = "✅ OK" if details.get("api_ok") else "❌ Erro"
                        st.metric("API", api_status)
                    
                    with col3:
                        comp_status = "✅ OK" if details.get("components_ok") else "❌ Erro"
                        st.metric("Componentes", comp_status)
                    
                    # Mostra erros se houver
                    if details.get("errors"):
                        st.warning("⚠️ Erros encontrados:")
                        for error in details["errors"]:
                            st.write(f"- {error}")
                    
                    # Log completo
                    with st.expander("📋 Log Completo da Validação"):
                        st.text(output)
                else:
                    st.error("❌ Validação falhou!")
                    st.error(output)
    
    with tab3:
        st.markdown("#### Status dos Componentes Frontend")
        st.markdown("Verifica se todos os componentes do frontend estão funcionando.")
        
        if st.button("🔄 Verificar Componentes", use_container_width=True):
            with st.spinner("Verificando componentes..."):
                components_status = diagnostics.check_frontend_components()
                
                st.markdown("**Status dos Componentes:**")
                
                for component, status in components_status.items():
                    icon = "✅" if status else "❌"
                    status_text = "OK" if status else "Erro"
                    st.write(f"{icon} **{component}**: {status_text}")
                
                # Resumo
                total_components = len(components_status)
                working_components = sum(components_status.values())
                
                if working_components == total_components:
                    st.success(f"✅ Todos os {total_components} componentes estão funcionando!")
                else:
                    st.warning(f"⚠️ {working_components}/{total_components} componentes funcionando")
    
    with tab4:
        st.markdown("#### Histórico de Testes")
        st.markdown("Visualize os resultados dos testes executados anteriormente.")
        
        history = diagnostics.get_test_history()
        
        if history["total_tests"] > 0:
            st.metric("Total de Testes", history["total_tests"])
            
            if history["last_test"]:
                st.write(f"**Último teste:** {history['last_test']}")
            
            # Mostra resultados dos testes
            for test_name, test_data in history["results"].items():
                with st.expander(f"📋 {test_name.replace('_', ' ').title()}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        status = "✅ Sucesso" if test_data["success"] else "❌ Falha"
                        st.write(f"**Status:** {status}")
                        st.write(f"**Data:** {test_data['timestamp']}")
                    
                    with col2:
                        if "details" in test_data and test_data["details"]:
                            st.write("**Detalhes:**")
                            for key, value in test_data["details"].items():
                                if isinstance(value, (list, dict)):
                                    st.write(f"- {key}: {len(value) if isinstance(value, list) else 'objeto'}")
                                else:
                                    st.write(f"- {key}: {value}")
                    
                    # Output do teste
                    if test_data.get("output"):
                        st.text_area("Output:", test_data["output"], height=150, disabled=True)
        else:
            st.info("📊 Nenhum teste foi executado ainda. Execute um teste para ver o histórico.")
        
        # Botão para limpar histórico
        if history["total_tests"] > 0:
            if st.button("🗑️ Limpar Histórico", type="secondary"):
                diagnostics.test_results = {}
                diagnostics.last_test_time = None
                st.success("✅ Histórico limpo!")
                st.rerun() 