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
    
    def run_upload_tests(self, test_type: str = "all") -> Tuple[bool, str, Dict[str, Any]]:
        """
        Executa testes específicos de upload.
        
        Args:
            test_type: Tipo de teste ("performance", "concurrency", "cleanup", "all")
        
        Returns:
            Tuple[bool, str, Dict]: (sucesso, output, detalhes)
        """
        try:
            # Mapear tipos de teste para arquivos
            test_files = {
                "performance": "tests/unit/test_upload_performance.py",
                "concurrency": "tests/unit/test_upload_concurrency.py", 
                "cleanup": "tests/unit/test_upload_cleanup.py",
                "integration": "tests/integration/test_upload_workflow.py"
            }
            
            if test_type == "all":
                # Executar todos os testes de upload
                scripts = list(test_files.values())
            else:
                scripts = [test_files.get(test_type)]
                if not scripts[0]:
                    return False, f"❌ Tipo de teste inválido: {test_type}", {"error": "invalid_test_type"}
            
            all_results = []
            total_success = True
            
            for script_path in scripts:
                if not script_path:
                    continue
                    
                # Executar teste específico
                result = subprocess.run(
                    [sys.executable, "-m", "pytest", script_path, "-v", "--tb=short"],
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minutos para testes de upload
                    cwd="/app" if os.path.exists("/app") else "."
                )
                
                script_success = result.returncode == 0
                total_success = total_success and script_success
                
                all_results.append({
                    "script": script_path,
                    "success": script_success,
                    "output": result.stdout if script_success else result.stderr,
                    "returncode": result.returncode
                })
            
            # Consolidar output
            consolidated_output = ""
            for res in all_results:
                script_name = Path(res["script"]).stem
                status = "✅ PASSOU" if res["success"] else "❌ FALHOU"
                consolidated_output += f"\n=== {script_name.upper()} - {status} ===\n"
                consolidated_output += res["output"]
                consolidated_output += "\n" + "="*50 + "\n"
            
            # Parse dos resultados
            details = self._parse_upload_test_output(all_results)
            
            self.test_results[f"upload_tests_{test_type}"] = {
                "success": total_success,
                "output": consolidated_output,
                "details": details,
                "timestamp": datetime.now().isoformat(),
                "test_type": test_type
            }
            
            self.last_test_time = datetime.now()
            
            return total_success, consolidated_output, details
            
        except subprocess.TimeoutExpired:
            error_msg = "⏰ Timeout: Testes de upload demoraram mais de 5 minutos"
            return False, error_msg, {"error": "timeout"}
            
        except Exception as e:
            error_msg = f"❌ Erro ao executar testes de upload: {str(e)}"
            return False, error_msg, {"error": str(e)}
    
    def _parse_upload_test_output(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Parse da saída dos testes de upload"""
        details = {
            "total_scripts": len(results),
            "scripts_passed": 0,
            "scripts_failed": 0,
            "total_tests": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "scripts_details": []
        }
        
        for result in results:
            script_name = Path(result["script"]).stem
            script_success = result["success"]
            
            if script_success:
                details["scripts_passed"] += 1
            else:
                details["scripts_failed"] += 1
            
            # Parse específico por tipo de teste
            script_details = {
                "name": script_name,
                "success": script_success,
                "tests_run": 0,
                "tests_passed": 0,
                "performance_metrics": {},
                "errors": []
            }
            
            output_lines = result["output"].split('\n')
            for line in output_lines:
                # Contar testes
                if "PASSED" in line:
                    script_details["tests_passed"] += 1
                    details["tests_passed"] += 1
                elif "FAILED" in line:
                    script_details["tests_run"] += 1
                    details["tests_failed"] += 1
                elif "ERROR" in line:
                    script_details["errors"].append(line.strip())
                
                # Extrair métricas de performance
                if "MÉTRICAS DE PERFORMANCE" in line:
                    # Próximas linhas podem conter métricas
                    continue
                elif "Tempo de upload:" in line:
                    try:
                        time_str = line.split(":")[-1].strip().replace("segundos", "").strip()
                        script_details["performance_metrics"]["upload_time"] = float(time_str)
                    except:
                        pass
                elif "Aumento de memória:" in line:
                    try:
                        mem_str = line.split(":")[-1].strip().replace("MB", "").strip()
                        script_details["performance_metrics"]["memory_increase"] = float(mem_str)
                    except:
                        pass
            
            script_details["tests_run"] = script_details["tests_passed"] + len(script_details["errors"])
            details["total_tests"] += script_details["tests_run"]
            details["scripts_details"].append(script_details)
        
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
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🧪 Testes de Feedback", 
        "✅ Validação Completa", 
        "📁 Testes de Upload",
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
        st.markdown("#### Testes de Upload de Arquivos")
        st.markdown("Execute testes específicos para validar a funcionalidade de upload de arquivos.")
        
        # Seletor de tipo de teste
        col1, col2 = st.columns([2, 1])
        
        with col1:
            test_type = st.selectbox(
                "Tipo de Teste:",
                options=["all", "performance", "concurrency", "cleanup", "integration"],
                format_func=lambda x: {
                    "all": "🎯 Todos os Testes",
                    "performance": "⚡ Performance (arquivos grandes)",
                    "concurrency": "🔄 Concorrência (uploads simultâneos)",
                    "cleanup": "🧹 Limpeza automática",
                    "integration": "🔗 Integração completa"
                }.get(x, x),
                help="Escolha o tipo específico de teste ou execute todos"
            )
        
        with col2:
            st.markdown("**Duração estimada:**")
            duration_map = {
                "all": "5-10 min",
                "performance": "2-3 min", 
                "concurrency": "1-2 min",
                "cleanup": "30-60 seg",
                "integration": "1-2 min"
            }
            st.info(f"⏱️ {duration_map.get(test_type, 'Variável')}")
        
        # Botão para executar testes
        if st.button("🚀 Executar Testes de Upload", type="primary", use_container_width=True):
            with st.spinner(f"Executando testes de upload ({test_type})..."):
                success, output, details = diagnostics.run_upload_tests(test_type)
                
                if success:
                    st.success("✅ Testes de upload executados com sucesso!")
                    
                    # Mostrar métricas dos testes
                    if details:
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric("Scripts", f"{details['scripts_passed']}/{details['total_scripts']}")
                        
                        with col2:
                            st.metric("Testes", f"{details['tests_passed']}/{details['total_tests']}")
                        
                        with col3:
                            success_rate = (details['tests_passed'] / max(details['total_tests'], 1)) * 100
                            st.metric("Taxa de Sucesso", f"{success_rate:.1f}%")
                        
                        with col4:
                            st.metric("Scripts com Falha", details['scripts_failed'])
                        
                        # Detalhes por script
                        if details.get('scripts_details'):
                            st.markdown("**Detalhes por Teste:**")
                            for script in details['scripts_details']:
                                icon = "✅" if script['success'] else "❌"
                                status = "PASSOU" if script['success'] else "FALHOU"
                                
                                with st.expander(f"{icon} {script['name']} - {status}"):
                                    col1, col2 = st.columns(2)
                                    
                                    with col1:
                                        st.write(f"**Testes executados:** {script['tests_run']}")
                                        st.write(f"**Testes aprovados:** {script['tests_passed']}")
                                        if script['errors']:
                                            st.write(f"**Erros:** {len(script['errors'])}")
                                    
                                    with col2:
                                        # Métricas de performance se disponíveis
                                        if script['performance_metrics']:
                                            st.write("**Métricas de Performance:**")
                                            for metric, value in script['performance_metrics'].items():
                                                if metric == "upload_time":
                                                    st.write(f"- Tempo: {value:.2f}s")
                                                elif metric == "memory_increase":
                                                    st.write(f"- Memória: {value:.1f}MB")
                                    
                                    # Mostrar erros se houver
                                    if script['errors']:
                                        st.error("**Erros encontrados:**")
                                        for error in script['errors'][:3]:  # Mostrar apenas os primeiros 3
                                            st.write(f"- {error}")
                                        if len(script['errors']) > 3:
                                            st.write(f"... e mais {len(script['errors']) - 3} erros")
                    
                    # Log completo em expander
                    with st.expander("📋 Log Completo dos Testes"):
                        st.text(output)
                        
                else:
                    st.error("❌ Testes de upload falharam!")
                    st.error(output)
                    
                    # Mostrar detalhes de falha se disponíveis
                    if details and details.get("error"):
                        if details["error"] == "timeout":
                            st.warning("⏰ Os testes demoraram mais que o esperado. Isso pode indicar problemas de performance.")
                        elif details["error"] == "invalid_test_type":
                            st.error("❌ Tipo de teste inválido selecionado.")
        
        # Informações sobre os testes
        with st.expander("ℹ️ Sobre os Testes de Upload"):
            st.markdown("""
            **Tipos de Teste Disponíveis:**
            
            - **Performance**: Testa upload de arquivos grandes (40-45MB) próximos ao limite de 50MB
            - **Concorrência**: Valida uploads simultâneos e thread safety
            - **Limpeza**: Verifica limpeza automática de arquivos processados
            - **Integração**: Testa o fluxo completo upload → processamento → banco
            - **Todos**: Executa todos os testes acima em sequência
            
            **O que é validado:**
            - ✅ Thread safety e integridade de dados
            - ✅ Performance com arquivos grandes
            - ✅ Limpeza automática de arquivos antigos
            - ✅ Concorrência de múltiplos uploads
            - ✅ Integração completa do pipeline
            """)

    with tab4:
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

    with tab5:
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