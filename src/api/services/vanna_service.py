"""
Serviço Vanna.ai para geração inteligente de SQL.

Este módulo integra o Vanna.ai ao sistema PROAtivo para converter
consultas em linguagem natural para SQL usando RAG.
"""

import os
import logging
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from datetime import datetime

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

try:
    # Importações corretas do Vanna.ai conforme documentação oficial
    from vanna.base import VannaBase
    from vanna.chromadb import ChromaDB_VectorStore
    from vanna.google import GoogleGeminiChat
    
    VANNA_AVAILABLE = True
    
except ImportError as e:
    VANNA_AVAILABLE = False
    logging.warning(f"Vanna.ai dependencies not available: {e}. Text-to-SQL will use fallback mode.")
    
    # Classes mock quando dependências não estão disponíveis
    class VannaBase:
        def __init__(self, config=None):
            raise RuntimeError("Vanna.ai not available - please install: pip install 'vanna>=0.7.9' 'chromadb>=0.4.0,<0.5.0' 'numpy>=1.21.0,<2.0.0' 'google-generativeai'")
    
    class ChromaDB_VectorStore:
        def __init__(self, config=None):
            pass
    
    class GoogleGeminiChat:
        def __init__(self, config=None):
            pass
            
except Exception as e:
    VANNA_AVAILABLE = False
    logging.error(f"Error importing Vanna.ai dependencies: {e}. Text-to-SQL will use fallback mode.")
    
    # Classes mock quando há erro de compatibilidade
    class VannaBase:
        def __init__(self, config=None):
            raise RuntimeError(f"Vanna.ai compatibility error: {e}")
    
    class ChromaDB_VectorStore:
        def __init__(self, config=None):
            pass
    
    class GoogleGeminiChat:
        def __init__(self, config=None):
            pass

from ..config import get_settings

logger = logging.getLogger(__name__)

@dataclass
class VannaResponse:
    """Resposta do Vanna.ai com metadata."""
    sql: Optional[str]
    confidence: float
    explanation: Optional[str]
    related_data: Optional[List[Dict[str, Any]]]
    processing_time: float
    model_used: str
    error: Optional[str] = None

@dataclass
class VannaCompleteResponse:
    """Resposta completa do Vanna.ai (método ask)."""
    sql: Optional[str]
    dataframe: Optional[Any]  # pandas DataFrame
    figure: Optional[Any]     # plotly Figure
    followup_questions: Optional[List[str]]
    natural_language_response: Optional[str]
    confidence: float
    processing_time: float
    model_used: str
    error: Optional[str] = None

class VannaGeminiService(ChromaDB_VectorStore, GoogleGeminiChat):
    """
    Serviço Vanna.ai integrado seguindo o padrão oficial.
    
    Herda de VannaBase e usa composição interna para ChromaDB + GoogleGeminiChat.
    """
    
    def __init__(self, config=None):
        """Inicializa o serviço seguindo padrão oficial do Vanna.ai."""
        settings = get_settings()
        
        # Configuração base do Vanna.ai
        if config is None:
            config = {
                'api_key': settings.google_api_key,
                'model_name': settings.vanna_gemini_model,
                'path': settings.vanna_vector_db_path
            }
        
        # Inicializar VannaBase primeiro (padrão oficial)
        #VannaBase.__init__(self, config=config)
        
        # Configurar componentes internos (composição)
        self._setup_components(config)
        
        self.model_name = settings.vanna_gemini_model
        self.is_initialized = False
        
        self._initialize_vanna()
    
    def _setup_components(self, config):
        """Configura componentes internos conforme padrão oficial."""
        try:
            # Configuração do LLM (GoogleGeminiChat)
            llm_config = {
                'api_key': config.get('api_key'),
                'model_name': config.get('model_name'),
                'temperature': config.get('temperature', 0.7)
            }
            
            # Configuração do Vector Store (ChromaDB_VectorStore)  
            vector_config = {
                'path': config.get('path')
            }
            
            # Inicializar componentes internos
            GoogleGeminiChat.__init__(self, config=llm_config)
            ChromaDB_VectorStore.__init__(self, config=vector_config)
            
            logger.info(f"🔧 Components configured: LLM={type(GoogleGeminiChat).__name__}, VectorStore={type(ChromaDB_VectorStore).__name__}")
            
        except Exception as e:
            logger.error(f"Error setting up Vanna components: {e}")
            raise
    
    def _initialize_vanna(self):
        """Inicializa a instância Vanna com configurações adequadas."""
        if not VANNA_AVAILABLE:
            logger.warning("⚠️ Vanna.ai not available. Verifique as dependências no requirements.txt")
            logger.info("🔄 System will operate in fallback mode using traditional query processor")
            return
        
        try:
            logger.info("🤖 Initializing Vanna.ai with official pattern (VannaBase + internal composition)...")
            
            # Validar componentes com logs detalhados
            if hasattr(GoogleGeminiChat, 'system_message' ) and hasattr(ChromaDB_VectorStore, 'generate_embedding'):
                logger.info(f"✓ Components found: LLM={GoogleGeminiChat}, Vector={ChromaDB_VectorStore}")
                
                # Verificar se os componentes têm os métodos necessários
                required_llm_methods = ['submit_prompt', 'system_message', 'user_message', 'assistant_message']
                required_vector_methods = ['add_ddl', 'add_documentation', 'get_related_ddl']
                required_service_methods = ['generate_sql', 'add_question_sql', 'generate_embedding', 'get_similar_question_sql', 'get_training_data', 'remove_training_data']
                
                llm_ok = all(hasattr(GoogleGeminiChat, method) for method in required_llm_methods)
                vector_ok = all(hasattr(ChromaDB_VectorStore, method) for method in required_vector_methods)                
                # Verificar se o próprio serviço tem todos os métodos necessários
                service_ok = all(hasattr(GoogleGeminiChat, method) for method in required_service_methods)
                
                logger.info(f"✓ Method validation: LLM={llm_ok}, Vector={vector_ok}, Service={service_ok}")
                
                if llm_ok and vector_ok and service_ok:
                    self.is_initialized = True
                    logger.info("✅ Vanna.ai initialized successfully with official pattern (VannaBase + GoogleGeminiChat + ChromaDB)")
                    
                    # Log de debug sobre configurações
                    logger.debug(f"Final configuration: model={self.model_name}, initialized={self.is_initialized}")
                else:
                    missing_llm = [m for m in required_llm_methods if not hasattr(GoogleGeminiChat, m)]
                    missing_vector = [m for m in required_vector_methods if not hasattr(ChromaDB_VectorStore, m)]
                    missing_service = [m for m in required_service_methods if not hasattr(GoogleGeminiChat, m)]
                    raise Exception(f"Components missing methods - LLM: {missing_llm}, Vector: {missing_vector}, Service: {missing_service}")
            else:
                raise Exception(f"Components not properly initialized: missing_components")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Vanna.ai: {e}")
            logger.info("🔄 System will operate in fallback mode using traditional query processor")
            self.is_initialized = False
    
    # ================================================================
    # MÉTODOS DO VANNA.AI (SEGUINDO PADRÃO OFICIAL)
    # ================================================================
    '''
    def system_message(self, message: str) -> str:
        """Delegar para o componente LLM."""
        return self.system_message(message)
    
    def user_message(self, message: str) -> str:
        """Delegar para o componente LLM."""
        return self.user_message(message) 
    
    def assistant_message(self, message: str) -> str:
        """Delegar para o componente LLM."""
        return self.assistant_message(message) 
    
    def submit_prompt(self, prompt: str, **kwargs) -> str:
        """Delegar para o componente LLM."""
        if hasattr(GoogleGeminiChat, 'submit_prompt'):
            return self.submit_prompt(prompt, **kwargs)
        else:
            logger.error("LLM component missing submit_prompt method")
            return ""
    
    def add_ddl(self, ddl: str, **kwargs) -> str:
        """Delegar para o componente Vector Store."""
        if hasattr(self.vector_store, 'add_ddl'):
            return self.vector_store.add_ddl(ddl, **kwargs)
        else:
            logger.error("Vector store component missing add_ddl method")
            return ""
    
    def add_documentation(self, documentation: str, **kwargs) -> str:
        """Delegar para o componente Vector Store."""
        if hasattr(self.vector_store, 'add_documentation'):
            return self.vector_store.add_documentation(documentation, **kwargs)
        else:
            logger.error("Vector store component missing add_documentation method")
            return ""
    
    def get_related_ddl(self, question: str, **kwargs) -> list:
        """Delegar para o componente Vector Store."""
        if hasattr(self.vector_store, 'get_related_ddl'):
            return self.vector_store.get_related_ddl(question, **kwargs)
        else:
            logger.error("Vector store component missing get_related_ddl method")
            return []
    
    def get_related_documentation(self, question: str, **kwargs) -> list:
        """Delegar para o componente Vector Store."""
        if hasattr(self.vector_store, 'get_related_documentation'):
            return self.vector_store.get_related_documentation(question, **kwargs)
        else:
            logger.error("Vector store component missing get_related_documentation method")
            return []
    
    # ================================================================
    # MÉTODOS ABSTRATOS ADICIONAIS DO VANNA BASE
    # ================================================================
    
    def add_question_sql(self, question: str, sql: str, **kwargs) -> str:
        """Adiciona par pergunta-SQL ao treinamento."""
        if hasattr(self.vector_store, 'add_question_sql'):
            return self.vector_store.add_question_sql(question, sql, **kwargs)
        else:
            # Implementação alternativa usando add_documentation
            training_data = f"Question: {question}\nSQL: {sql}"
            return self.add_documentation(training_data, **kwargs)
    
    def generate_embedding(self, text: str, **kwargs) -> list:
        """Gera embedding para o texto."""
        if hasattr(self.vector_store, 'generate_embedding'):
            return self.vector_store.generate_embedding(text, **kwargs)
        else:
            logger.warning("Vector store missing generate_embedding method, returning empty list")
            return []
    
    def get_similar_question_sql(self, question: str, **kwargs) -> list:
        """Busca pares pergunta-SQL similares."""
        if hasattr(self.vector_store, 'get_similar_question_sql'):
            return self.vector_store.get_similar_question_sql(question, **kwargs)
        else:
            # Implementação alternativa usando get_related_documentation
            return self.get_related_documentation(question, **kwargs)
    
    def get_training_data(self, **kwargs) -> list:
        """Obtém dados de treinamento."""
        if hasattr(self.vector_store, 'get_training_data'):
            return self.vector_store.get_training_data(**kwargs)
        else:
            logger.warning("Vector store missing get_training_data method, returning empty list")
            return []
    
    def remove_training_data(self, id: str, **kwargs) -> bool:
        """Remove dados de treinamento por ID."""
        if hasattr(self.vector_store, 'remove_training_data'):
            return self.vector_store.remove_training_data(id, **kwargs)
        else:
            logger.warning("Vector store missing remove_training_data method, returning False")
            return False
    '''
    def generate_sql(self, question: str, **kwargs) -> str:
        """
        Gera SQL usando a orquestração padrão do Vanna.ai (LLM + Vector Store).
        
        Este é o método principal que combina:
        1. Busca de DDL/documentação relevante no Vector Store
        2. Criação de prompt com contexto
        3. Chamada ao LLM para gerar SQL
        """
        try:
            logger.debug(f"Generating SQL for question: {question}")
            
            # 1. Obter DDL e documentação relacionados com limite de resultados
            settings = get_settings()
            max_results = settings.vanna_max_results
            related_ddl = self.get_related_ddl(question, n_results=max_results)
            related_docs = self.get_related_documentation(question, n_results=max_results)
            
            # 2. Construir prompt com contexto (seguindo padrão Vanna.ai)
            context_parts = []
            
            if related_ddl:
                context_parts.append("-- Database Schema:")
                context_parts.extend(related_ddl)
            
            if related_docs:
                context_parts.append("-- Business Context:")  
                context_parts.extend(related_docs)
            
            # 3. Criar prompt final
            context = "\n".join(context_parts)
            
            prompt = f"""You are a PostgreSQL expert. Generate a SQL query based on the following context and question.

{context}

Question: {question}

Generate ONLY the SQL query without explanations or markdown formatting.
Use only SELECT statements.
Do not include dangerous commands (DROP, DELETE, INSERT, UPDATE, ALTER, CREATE).

SQL:"""
            
            # 4. Enviar para o LLM
            sql_response = self.submit_prompt(prompt)
            
            # 5. Limpar resposta
            if sql_response:
                sql_response = sql_response.strip()
                # Remover markdown se presente
                if sql_response.startswith('```sql'):
                    sql_response = sql_response[6:]
                if sql_response.endswith('```'):
                    sql_response = sql_response[:-3]
                return sql_response.strip()
            logger.info(f"SQL response: {sql_response}")
            return None
              
            

        except Exception as e:
            logger.error(f"Error in VannaGeminiService.generate_sql: {e}")
            return None    
    
class VannaService:
    """
    Wrapper service para integração com o sistema PROAtivo.
    
    Mantém a interface original mas usa o VannaGeminiService internamente.
    """
    
    def __init__(self):
        """Inicializa o serviço Vanna."""
        self.settings = get_settings()
        self.vanna = None
        self.model_name = self.settings.vanna_gemini_model
        self.is_initialized = False
        
        self._initialize_vanna()
    
    def _initialize_vanna(self):
        """Inicializa a instância Vanna com configurações adequadas."""
        try:
            logger.info("🚀 Starting VannaService initialization...")
            
            # Criar instância do VannaGeminiService (padrão oficial)
            self.vanna = VannaGeminiService()
            
            if self.vanna.is_initialized:
                # Configurar conexão com banco para método ask() completo
                self._setup_database_connection()
                
                self.is_initialized = True
                logger.info("✅ VannaService initialized successfully")
            else:
                logger.warning("⚠️ VannaGeminiService not properly initialized")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize VannaService: {e}")
            self.is_initialized = False
    
    async def generate_sql(self, question: str, context: Optional[Dict[str, Any]] = None) -> VannaResponse:
        """
        Gera SQL a partir de uma pergunta em linguagem natural.
        
        Args:
            question: Pergunta do usuário
            context: Contexto adicional (filtros, preferências, etc.)
            
        Returns:
            VannaResponse com SQL gerado e metadata
        """
        start_time = datetime.now()
        
        if not self.is_initialized:
            return VannaResponse(
                sql=None,
                confidence=0.0,
                explanation="Vanna.ai não inicializado",
                related_data=None,
                processing_time=0.0,
                model_used="none",
                error="Service not initialized"
            )
        
        try:
            enhanced_question = self._enhance_question_with_context(question, context)
            
            # Usar a API oficial do Vanna.ai para gerar SQL
            sql = self.vanna.generate_sql(enhanced_question)
            
            # Obter dados relacionados (DDL + documentação) com limite de resultados
            settings = get_settings()
            max_results = settings.vanna_max_results
            related_ddl = self.vanna.get_related_ddl(enhanced_question, n_results=max_results)
            related_docs = self.vanna.get_related_documentation(enhanced_question, n_results=max_results)
            related_data = {"ddl": related_ddl, "documentation": related_docs}
            
            # Calcular confiança baseado na qualidade da resposta
            confidence = self._calculate_confidence(sql, related_data) 
            
            # Gerar explicação básica
            explanation = f"SQL gerado para: {enhanced_question}"
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return VannaResponse(
                sql=sql,
                confidence=confidence,
                explanation=explanation,
                related_data=related_data,
                processing_time=processing_time,
                model_used=self.model_name
            )
            
        except Exception as e:
            logger.error(f"Error generating SQL with Vanna: {e}")
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return VannaResponse(
                sql=None,
                confidence=0.0,
                explanation=None,
                related_data=None,
                processing_time=processing_time,
                model_used=self.model_name,
                error=str(e)
            )
    
    async def ask_complete(self, question: str, context: Optional[Dict[str, Any]] = None) -> VannaCompleteResponse:
        """
        Usa o método ask() completo do Vanna.ai que faz tudo internamente:
        - Gera SQL usando RAG próprio
        - Executa SQL no banco conectado
        - Formata resposta em linguagem natural
        - Gera perguntas de seguimento
        
        Args:
            question: Pergunta do usuário
            context: Contexto adicional (não usado pelo ask() nativo)
            
        Returns:
            VannaCompleteResponse com resposta completa
        """
        start_time = datetime.now()
        
        if not self.is_initialized:
            return VannaCompleteResponse(
                sql=None,
                dataframe=None,
                figure=None,
                followup_questions=None,
                natural_language_response="Vanna.ai não inicializado",
                confidence=0.0,
                processing_time=0.0,
                model_used="none",
                error="Service not initialized"
            )
        
        try:
            enhanced_question = self._enhance_question_with_context(question, context)
            
            # Usar o método ask() completo do Vanna.ai
            # ask() retorna: (sql, dataframe, figure, visualize)
            logger.info(f"Using Vanna.ai complete workflow for: {enhanced_question}")
            
            # Usar parâmetros básicos que sabemos que funcionam
            result = self.vanna.ask(
                question=enhanced_question,
                print_results=False,  # Não imprimir resultados
                auto_train=False      # Não treinar automaticamente
            )
            
            if result:
                # Extrair componentes do resultado baseando-se no que está disponível
                sql = None
                dataframe = None
                figure = None
                followup_questions = []
                
                if isinstance(result, tuple):
                    if len(result) >= 1:
                        sql = result[0]
                    if len(result) >= 2:
                        dataframe = result[1]
                    if len(result) >= 3:
                        figure = result[2]
                    if len(result) >= 4:
                        followup_questions = result[3] or []
                elif isinstance(result, dict):
                    # Caso o resultado seja um dicionário
                    sql = result.get('sql')
                    dataframe = result.get('dataframe') 
                    figure = result.get('figure')
                    
                else:
                    # Caso seja apenas a SQL string
                    sql = str(result) if result else None
                
                # Gerar resposta em linguagem natural baseada nos dados
                natural_response = self._generate_natural_response(enhanced_question, sql, dataframe)
                
                # Calcular confiança baseada na qualidade da resposta
                confidence = self._calculate_ask_confidence(sql, dataframe)
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                logger.info(f"Vanna.ai complete workflow successful. SQL: {sql[:100] if sql else 'None'}...")
                
                return VannaCompleteResponse(
                    sql=sql,
                    dataframe=dataframe,
                    figure=figure,
                    followup_questions=followup_questions,
                    natural_language_response=natural_response,
                    confidence=confidence,
                    processing_time=processing_time,
                    model_used=self.model_name
                )
            else:
                logger.warning("Vanna.ai ask() returned incomplete result")
                return VannaCompleteResponse(
                    sql=None,
                    dataframe=None,
                    figure=None,
                    followup_questions=None,
                    natural_language_response="Não foi possível gerar resposta completa",
                    confidence=0.0,
                    processing_time=(datetime.now() - start_time).total_seconds(),
                    model_used=self.model_name,
                    error="Incomplete result from Vanna ask()"
                )
                
        except Exception as e:
            logger.error(f"Error in Vanna.ai complete workflow: {e}")
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return VannaCompleteResponse(
                sql=None,
                dataframe=None,
                figure=None,
                followup_questions=None,
                natural_language_response=f"Erro ao processar consulta: {str(e)}",
                confidence=0.0,
                processing_time=processing_time,
                model_used=self.model_name,
                error=str(e)
            )
    
    def _enhance_question_with_context(self, question: str, context: Optional[Dict[str, Any]]) -> str:
        """Melhora a pergunta com contexto adicional."""
        if not context:
            return question
        
        enhanced = question
        
        if 'user_location' in context:
            enhanced += f" na localidade {context['user_location']}"
        
        if 'time_filter' in context:
            enhanced += f" {context['time_filter']}"
        
        if 'equipment_type' in context:
            enhanced += f" para equipamentos do tipo {context['equipment_type']}"
        
        return enhanced
    
    def _calculate_confidence(self, sql: Optional[str], related_data: Any) -> float:
        """Calcula score de confiança baseado na qualidade da resposta."""
        if not sql:
            return 0.0
        
        confidence = 0.5 
        
        if self._is_valid_sql_structure(sql):
            confidence += 0.2
        
        # Bonus por dados relacionados encontrados
        if related_data and isinstance(related_data, dict):
            if related_data.get('ddl') or related_data.get('documentation'):
                confidence += 0.1
        
        known_tables = ['equipments', 'maintenances', 'failures', 'pmm_2', 'sap_locations']
        if any(table in sql.lower() for table in known_tables):
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _generate_natural_response(self, question: str, sql: Optional[str], dataframe: Optional[Any]) -> str:
        """
        Gera resposta em linguagem natural usando os prompts estruturados do LLMService
        e os métodos nativos do Vanna GoogleGeminiChat.
        
        Args:
            question: Pergunta original
            sql: SQL gerada
            dataframe: DataFrame com resultados
            
        Returns:
            str: Resposta em linguagem natural gerada pelo LLM
        """
        # Debug logging detalhado (mantido para compatibilidade)
        logger.info(f"🔍 Natural Response Debug - Question: {question}")
        logger.info(f"🔍 Natural Response Debug - SQL: {sql}")
        logger.info(f"🔍 Natural Response Debug - DataFrame type: {type(dataframe)}")
        
        if dataframe is not None:
            logger.info(f"🔍 Natural Response Debug - DataFrame shape: {getattr(dataframe, 'shape', 'No shape')}")
            logger.info(f"🔍 Natural Response Debug - DataFrame empty: {getattr(dataframe, 'empty', 'No empty attr')}")
            logger.info(f"🔍 Natural Response Debug - DataFrame content: {str(dataframe)[:200]}")
        else:
            logger.info(f"🔍 Natural Response Debug - DataFrame is None")
        
        # Validações básicas mantidas para robustez
        if not sql:
            logger.warning("❌ SQL is None")
            return "Não foi possível gerar o SQL para sua pergunta."
        
        if dataframe is None:
            logger.warning("❌ DataFrame is None")
            return "Não foi possível executar a consulta no banco de dados."
        
        try:
            # Usar os prompts estruturados do LLMService (reutilizando lógica testada)
            logger.info("🤖 Gerando resposta natural usando prompts do LLMService e métodos nativos do Vanna")
            
            # Preparar contexto estruturado para o LLM
            context = self._prepare_context_for_llm(dataframe, question, sql)
            
            # Criar prompts reutilizando a lógica do LLMService
            system_prompt = self._create_system_prompt_for_natural_response()
            user_prompt = self._create_user_prompt_for_natural_response(question, context)
            
            # Construir prompt completo
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            # Usar método nativo do Vanna GoogleGeminiChat
            logger.info("📤 Enviando prompt para GoogleGeminiChat via submit_prompt()")
            response = self.vanna.submit_prompt(full_prompt)
            
            if response and response.strip():
                logger.info("✅ Resposta natural gerada com sucesso usando arquitetura Vanna")
                return response.strip()
            else:
                logger.warning("⚠️ Resposta vazia do LLM, usando fallback")
                return self._generate_fallback_response(dataframe, question)
                
        except Exception as e:
            logger.error(f"❌ Erro ao gerar resposta natural com Vanna: {e}")
            logger.info("🔄 Usando fallback para resposta natural")
            return self._generate_fallback_response(dataframe, question)
    
    def _prepare_context_for_llm(self, dataframe: Any, question: str, sql: str) -> Dict[str, Any]:
        """
        Prepara contexto estruturado para o LLM baseado no DataFrame.
        
        Args:
            dataframe: DataFrame com resultados
            question: Pergunta original
            sql: SQL executada
            
        Returns:
            Dict: Contexto estruturado para o LLM
        """
        context = {
            'sql_query': sql,
            'structured_data': [],
            'query_analysis': {'intent': 'general_query'}
        }
        
        try:
            # Verificar se dataframe tem dados
            if hasattr(dataframe, 'empty') and dataframe.empty:
                if hasattr(dataframe, 'shape') and dataframe.shape == (0, 0):
                    context['data_status'] = 'execution_error'
                else:
                    context['data_status'] = 'no_matching_data'
                return context
            
            context['data_status'] = 'has_data'
            
            # Converter DataFrame para formato estruturado
            if hasattr(dataframe, 'to_dict'):
                records = dataframe.to_dict('records')
                context['structured_data'] = records
                
                # Análise específica para diferentes tipos de consulta
                if hasattr(dataframe, 'shape'):
                    if dataframe.shape == (1, 1):
                        # Consulta de agregação/COUNT
                        context['query_analysis']['intent'] = 'count_query'
                        value = dataframe.iloc[0, 0]
                        context['count_value'] = value
                        logger.info(f"📊 COUNT query detected - Value: {value}")
                    elif dataframe.shape[0] > 1:
                        # Múltiplos registros
                        context['query_analysis']['intent'] = 'list_query'
                        context['record_count'] = dataframe.shape[0]
                        logger.info(f"📊 List query detected - {dataframe.shape[0]} records")
            
            return context
            
        except Exception as e:
            logger.error(f"❌ Erro ao preparar contexto: {e}")
            context['data_status'] = 'context_error'
            return context
    
    def _create_system_prompt_for_natural_response(self) -> str:
        """
        Cria prompt de sistema especializado para respostas naturais baseado no LLMService.
        
        Returns:
            str: Prompt de sistema otimizado
        """
        return """Você é um especialista técnico em equipamentos elétricos. Responda como um engenheiro experiente.

REGRAS OBRIGATÓRIAS:
1. NUNCA mencione "sistema", "banco de dados", "registros encontrados" ou "sua consulta"
2. NUNCA use frases como "Com base nos dados" ou "Encontrei X registros"
3. Seja DIRETO - responda como se soubesse a informação naturalmente
4. Use linguagem técnica profissional, mas clara
5. Foque na RESPOSTA, não no processo de busca

PARA CONSULTAS DE CONTAGEM:
6. Use APENAS os números fornecidos nos dados estruturados
7. Forneça contexto sobre os equipamentos contados (localização, tipo, etc.)
8. Seja específico sobre o que está sendo contado

PARA LISTAS DE DADOS:
9. Destaque os pontos mais relevantes
10. Organize informações de forma clara e hierárquica
11. Mencione detalhes técnicos importantes

EXEMPLOS CORRETOS:
✅ "No parque elétrico temos 8 transformadores e 12 disjuntores."
✅ "O transformador T001 teve manutenção preventiva em 15/12/2024."
✅ "Os disjuntores críticos são: DJ-001, DJ-005 e DJ-012."

RESPONDA SEMPRE como um especialista que conhece os dados, nunca como um sistema fazendo busca."""

    def _create_user_prompt_for_natural_response(self, question: str, context: Dict[str, Any]) -> str:
        """
        Cria prompt do usuário para resposta natural baseado no contexto.
        
        Args:
            question: Pergunta original
            context: Contexto preparado com dados estruturados
            
        Returns:
            str: Prompt formatado para o usuário
        """
        data_status = context.get('data_status', 'unknown')
        
        # Tratar casos sem dados
        if data_status == 'execution_error':
            return f"""PERGUNTA: {question}

STATUS: Erro na execução da consulta

Responda que houve um problema técnico e sugira tentar novamente."""

        elif data_status == 'no_matching_data':
            return f"""PERGUNTA: {question}

STATUS: Consulta executada com sucesso, mas sem dados correspondentes

Responda que a consulta foi executada mas não retornou dados."""

        elif data_status != 'has_data':
            return f"""PERGUNTA: {question}

STATUS: Erro no processamento dos dados

Responda que houve erro ao processar os dados."""

        # Processar dados estruturados
        structured_data = context.get('structured_data', [])
        query_intent = context.get('query_analysis', {}).get('intent', 'general_query')
        
        # Construir contexto baseado no tipo de consulta
        data_section = ""
        
        if query_intent == 'count_query':
            count_value = context.get('count_value', 0)
            data_section = f"**TOTAL DE EQUIPAMENTOS**: {count_value}"
            
            # Adicionar contexto adicional se disponível nos dados
            if structured_data and len(structured_data) > 0:
                first_record = structured_data[0]
                for key, value in first_record.items():
                    if key != 'count' and value is not None:
                        data_section += f"\n- {key}: {value}"
        
        elif query_intent == 'list_query':
            record_count = context.get('record_count', 0)
            data_section = f"**DADOS ENCONTRADOS**: {record_count} registros\n\n"
            
            # Mostrar primeiros registros estruturados
            for i, record in enumerate(structured_data[:5]):  # Máximo 5 registros
                data_section += f"**Registro {i+1}:**\n"
                for key, value in record.items():
                    if value is not None:
                        data_section += f"- {key}: {value}\n"
                data_section += "\n"
                
            if len(structured_data) > 5:
                data_section += f"... e mais {len(structured_data) - 5} registros"
        
        else:
            # Formato genérico para outros tipos
            if structured_data:
                data_section = "**DADOS:**\n"
                for record in structured_data[:3]:  # Máximo 3 registros
                    for key, value in record.items():
                        if value is not None:
                            data_section += f"- {key}: {value}\n"
                    data_section += "\n"

        return f"""PERGUNTA: {question}

{data_section}

Responda diretamente baseado nas informações disponíveis. Use APENAS os números e dados mostrados acima."""

    def _generate_fallback_response(self, dataframe: Any, question: str) -> str:
        """
        Gera resposta de fallback quando o LLM falha.
        
        Args:
            dataframe: DataFrame com resultados  
            question: Pergunta original
            
        Returns:
            str: Resposta de fallback
        """
        try:
            # Verificar se dataframe tem dados básicos para fallback
            if hasattr(dataframe, 'empty') and dataframe.empty:
                return "A consulta foi executada com sucesso, mas não retornou dados."
            
            # Para consultas de COUNT (fallback simples)
            if hasattr(dataframe, 'shape') and dataframe.shape == (1, 1):
                value = dataframe.iloc[0, 0]
                if isinstance(value, (int, float)):
                    if "quantos" in question.lower() or "count" in question.lower():
                        return f"Encontrei {int(value)} equipamentos que atendem aos critérios da consulta."
                    else:
                        return f"O resultado da consulta é: {value}"
            
            # Para múltiplas linhas
            elif hasattr(dataframe, 'shape') and dataframe.shape[0] > 1:
                count = dataframe.shape[0]
                return f"Encontrei {count} registros que atendem aos critérios da sua consulta."
            
            # Fallback genérico
            return "Consulta executada com sucesso. Verifique os dados retornados."
            
        except Exception as e:
            logger.error(f"❌ Erro no fallback: {e}")
            return "Consulta executada, mas houve erro ao formatar a resposta."
    
    def _calculate_ask_confidence(self, sql: Optional[str], dataframe: Optional[Any]) -> float:
        """
        Calcula confiança baseada na qualidade da resposta completa.
        
        Args:
            sql: SQL gerada
            dataframe: DataFrame com resultados
            
        Returns:
            float: Confiança entre 0.0 e 1.0
        """
        confidence = 0.5  # Base
        
        if sql:
            confidence += 0.2  # SQL foi gerada
            
            # SQL parece válida
            if "SELECT" in sql.upper() and "FROM" in sql.upper():
                confidence += 0.1
        
        if dataframe is not None:
            confidence += 0.2  # DataFrame foi retornado
            
            # DataFrame tem dados
            if hasattr(dataframe, 'empty') and not dataframe.empty:
                confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _is_valid_sql_structure(self, sql: str) -> bool:
        """Verifica se o SQL tem estrutura básica válida."""
        sql_lower = sql.lower().strip()
        
        if not sql_lower.startswith('select'):
            return False
        
        if 'from' not in sql_lower:
            return False
        
        dangerous_keywords = ['drop', 'delete', 'insert', 'update', 'alter', 'create']
        if any(keyword in sql_lower for keyword in dangerous_keywords):
            return False
        
        return True
    
    async def train_on_database_schema(self, db_session: AsyncSession) -> bool:
        """
        Treina o modelo Vanna no schema do banco de dados.
        
        Args:
            db_session: Sessão do banco de dados
            
        Returns:
            True se treinamento foi bem-sucedido
        """
        if not self.is_initialized:
            logger.error("Cannot train: Vanna not initialized")
            return False
        
        try:
            logger.info("🤖 Starting Vanna.ai training using official API...")
            
            # Treinar schemas usando a API oficial do Vanna.ai
            table_schemas = [
                self._get_equipment_schema(),
                self._get_maintenance_schema(),
                self._get_failure_schema(),
                self._get_pmm2_schema(),
                self._get_sap_location_schema()
            ]
            
            for schema_ddl in table_schemas:
                self.vanna.add_ddl(schema_ddl)
                logger.info(f"Added schema DDL to Vanna training: {schema_ddl[:50]}...")
            
            # Treinar documentação de negócio
            business_docs = self._get_business_documentation()
            for doc in business_docs:
                self.vanna.add_documentation(doc)
                logger.info(f"Added business documentation to Vanna training: {doc[:50]}...")
            
            logger.info("✅ Vanna.ai training completed successfully using official API")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error during Vanna.ai training: {e}")
            return False
    
    def _get_equipment_schema(self) -> str:
        """Retorna o schema da tabela equipments."""
        return """
        CREATE TABLE equipments (
            id UUID PRIMARY KEY,
            code VARCHAR(50) UNIQUE NOT NULL,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            equipment_type VARCHAR(50) NOT NULL,
            criticality VARCHAR(20) NOT NULL DEFAULT 'Medium',
            location VARCHAR(200),
            substation VARCHAR(100),
            sap_location_id UUID,
            manufacturer VARCHAR(100),
            model VARCHAR(100),
            serial_number VARCHAR(100),
            manufacturing_year INTEGER,
            installation_date TIMESTAMP WITH TIME ZONE,
            rated_voltage NUMERIC(10,2),
            rated_power NUMERIC(10,2),
            rated_current NUMERIC(10,2),
            status VARCHAR(20) NOT NULL DEFAULT 'Active',
            is_critical BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
    
    def _get_maintenance_schema(self) -> str:
        """Retorna o schema da tabela maintenances."""
        return """
        CREATE TABLE maintenances (
            id UUID PRIMARY KEY,
            equipment_id UUID NOT NULL,
            maintenance_code VARCHAR(50),
            maintenance_type VARCHAR(50) NOT NULL,
            priority VARCHAR(20) NOT NULL DEFAULT 'Medium',
            title VARCHAR(200) NOT NULL,
            description TEXT,
            work_performed TEXT,
            scheduled_date TIMESTAMP WITH TIME ZONE,
            start_date TIMESTAMP WITH TIME ZONE,
            completion_date TIMESTAMP WITH TIME ZONE,
            duration_hours NUMERIC(8,2),
            status VARCHAR(20) NOT NULL DEFAULT 'Planned',
            result VARCHAR(50),
            technician VARCHAR(100),
            team VARCHAR(200),
            contractor VARCHAR(100),
            estimated_cost NUMERIC(12,2),
            actual_cost NUMERIC(12,2),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
    
    def _get_failure_schema(self) -> str:
        """Retorna o schema da tabela failures."""
        return """
        CREATE TABLE failures (
            id UUID PRIMARY KEY,
            equipment_id UUID NOT NULL,
            incident_id VARCHAR(50),
            incident_number VARCHAR(50),
            failure_date TIMESTAMP WITH TIME ZONE NOT NULL,
            failure_type VARCHAR(100) NOT NULL,
            description TEXT,
            root_cause TEXT,
            severity VARCHAR(20) NOT NULL DEFAULT 'Medium',
            impact_level VARCHAR(20),
            downtime_hours NUMERIC(8,2),
            resolution_time INTEGER,
            cost NUMERIC(12,2),
            affected_customers INTEGER,
            resolution_description TEXT,
            lessons_learned TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'Reported',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
    
    def _get_pmm2_schema(self) -> str:
        """Retorna o schema da tabela PMM_2."""
        return """
        CREATE TABLE pmm_2 (
            id UUID PRIMARY KEY,
            maintenance_plan_code VARCHAR(20) NOT NULL,
            work_center VARCHAR(20) NOT NULL,
            maintenance_item_text VARCHAR(500) NOT NULL,
            installation_location VARCHAR(100) NOT NULL,
            equipment_id UUID,
            equipment_code VARCHAR(50),
            sap_location_id UUID,
            planned_date TIMESTAMP WITH TIME ZONE,
            scheduled_start_date TIMESTAMP WITH TIME ZONE,
            completion_date TIMESTAMP WITH TIME ZONE,
            last_order VARCHAR(20),
            current_order VARCHAR(20),
            maintenance_id UUID,
            status VARCHAR(20) NOT NULL DEFAULT 'Active',
            import_batch_id VARCHAR(100),
            import_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            data_source VARCHAR(50) NOT NULL DEFAULT 'SAP',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
    
    def _get_sap_location_schema(self) -> str:
        """Retorna o schema da tabela sap_locations."""
        return """
        CREATE TABLE sap_locations (
            id UUID PRIMARY KEY,
            location_code VARCHAR(50) UNIQUE NOT NULL,
            denomination VARCHAR(200) NOT NULL,
            abbreviation VARCHAR(20),
            region VARCHAR(10),
            type_code VARCHAR(10),
            status VARCHAR(20) NOT NULL DEFAULT 'Active',
            import_batch_id VARCHAR(100),
            import_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            data_source VARCHAR(50) NOT NULL DEFAULT 'SAP',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
    
    def _get_business_documentation(self) -> List[str]:
        """Retorna documentação de negócio para treinamento."""
        return [
            """
            O sistema PROAtivo gerencia manutenção de equipamentos elétricos.
            Equipamentos incluem transformadores, disjuntores, seccionadoras, motores e geradores.
            Criticidade pode ser High, Medium ou Low.
            Status de equipamentos: Active, Inactive, Maintenance, Retired.
            """,
            """
            Tipos de manutenção: Preventive (planejada), Corrective (reparo), 
            Predictive (baseada em condição), Emergency (urgente).
            Status de manutenção: Planned, InProgress, Completed, Cancelled.
            Prioridade: High, Medium, Low.
            """,
            """
            PMM_2 contém planos de manutenção do SAP com datas planejadas.
            Cada plano tem maintenance_plan_code único e installation_location.
            Status dos planos: Active, Completed, Cancelled, Suspended.
            """,
            """
            Falhas são registradas com severity (Critical, High, Medium, Low).
            Incluem downtime_hours, cost e affected_customers.
            Status de falhas: Reported, InProgress, Resolved, Closed.
            """,
            """
            Localidades SAP têm location_code único e denomination.
            Regiões são extraídas do código (ex: MT-S-74399).
            Equipamentos são associados a localidades via sap_location_id.
            """
        ]
    
    def test_functionality(self) -> Dict[str, Any]:
        """
        Testa funcionalidade do VannaService.
        
        Returns:
            Dict com resultados dos testes do serviço e componentes internos
        """
        service_results = {
            'service_initialized': self.is_initialized,
            'vanna_instance_available': hasattr(self, 'vanna') and self.vanna is not None,
        }
        
        # Se a instância Vanna estiver disponível, testar componentes internos
        if service_results['vanna_instance_available'] and hasattr(self.vanna, 'test_basic_functionality'):
            service_results['vanna_components'] = self.vanna.test_basic_functionality()
        
        return service_results
    
    def _setup_database_connection(self):
        """
        Configura conexão com banco para o método ask() completo do Vanna.
        """
        try:
            from ...database.connection import get_async_session
            import asyncio
            import pandas as pd
            
            async def run_sql_async(sql: str) -> pd.DataFrame:
                """Executa SQL de forma assíncrona e retorna DataFrame."""
                logger.info(f"🔍 Vanna SQL Execution - Query: {sql}")
                try:
                    # get_async_session é um async generator, usar diretamente
                    async with get_async_session() as session:
                        from sqlalchemy import text
                        result = await session.execute(text(sql))
                        rows = result.fetchall()
                        
                        logger.info(f"🔍 Vanna SQL Execution - Rows returned: {len(rows) if rows else 0}")
                        
                        columns = result.keys()
                        logger.info(f"🔍 Vanna SQL Execution - Columns: {list(columns) if columns else 'None'}")
                        logger.info(f"🔍 Vanna SQL Execution - Raw rows: {rows}")
                        
                        if rows:
                            data = [dict(zip(columns, row)) for row in rows]
                            df = pd.DataFrame(data)
                            
                            # Debug detalhado do DataFrame
                            logger.info(f"🔍 Vanna SQL Execution - DataFrame created: {df.shape}")
                            logger.info(f"🔍 Vanna SQL Execution - DataFrame dtypes: {df.dtypes.to_dict() if not df.empty else 'Empty'}")
                            logger.info(f"🔍 Vanna SQL Execution - DataFrame empty check: {df.empty}")
                            logger.info(f"🔍 Vanna SQL Execution - DataFrame values: {df.values.tolist() if not df.empty else 'Empty'}")
                            logger.info(f"🔍 Vanna SQL Execution - DataFrame content: {df.to_dict()}")
                            
                            # Debug específico para COUNT queries
                            if df.shape == (1, 1):
                                first_value = df.iloc[0, 0]
                                logger.info(f"🔍 Vanna SQL Execution - COUNT detected - Value: {first_value} (Type: {type(first_value)})")
                            
                            return df
                        else:
                            logger.warning("🔍 Vanna SQL Execution - No rows returned, creating empty DataFrame")
                            empty_df = pd.DataFrame()
                            logger.info(f"🔍 Vanna SQL Execution - Empty DataFrame check: {empty_df.empty}")
                            return empty_df
                            
                except Exception as e:
                    logger.error(f"❌ Error executing SQL in Vanna: {e}")
                    import traceback
                    logger.error(f"❌ SQL Execution Stack trace: {traceback.format_exc()}")
                    return pd.DataFrame()
            
            def run_sql_sync(sql: str) -> pd.DataFrame:
                """Executa SQL de forma síncrona usando conexão direta ao PostgreSQL."""
                logger.info(f"🔍 Vanna SQL Direct Execution - Query: {sql[:100]}...")
                try:
                    import pandas as pd
                    import psycopg2
                    from ...api.config import get_settings
                    
                    settings = get_settings()
                    
                    # Criar conexão síncrona direta - evita problemas de asyncio
                    logger.info("🔗 Creating direct PostgreSQL connection")
                    conn = psycopg2.connect(
                        host=settings.database_host,
                        port=settings.database_port,
                        database=settings.database_name,
                        user=settings.database_user,
                        password=settings.database_password
                    )
                    
                    # Executar query diretamente com pandas
                    logger.info("📊 Executing SQL with pandas.read_sql_query")
                    df = pd.read_sql_query(sql, conn)
                    conn.close()
                    
                    logger.info(f"✅ Direct SQL execution successful - DataFrame shape: {df.shape}")
                    logger.info(f"📊 DataFrame content: {df.to_dict()}")
                    
                    # Debug específico para COUNT queries
                    if df.shape == (1, 1):
                        first_value = df.iloc[0, 0]
                        logger.info(f"🔢 COUNT query detected - Value: {first_value} (Type: {type(first_value)})")
                    
                    return df
                    
                except ImportError as e:
                    logger.error(f"❌ Missing psycopg2 dependency: {e}")
                    logger.info("💡 Trying fallback with SQLAlchemy sync engine")
                    return fallback_sync_execution(sql)
                except Exception as e:
                    logger.error(f"❌ Error in direct SQL execution: {e}")
                    import traceback
                    logger.error(f"❌ Direct SQL Stack trace: {traceback.format_exc()}")
                    return pd.DataFrame()
            
            def fallback_sync_execution(sql_query: str) -> pd.DataFrame:
                """Fallback usando SQLAlchemy engine síncrono."""
                try:
                    import pandas as pd
                    from sqlalchemy import create_engine, text
                    from ...api.config import get_settings
                    
                    settings = get_settings()
                    
                    # Criar engine síncrono
                    database_url = f"postgresql://{settings.database_user}:{settings.database_password}@{settings.database_host}:{settings.database_port}/{settings.database_name}"
                    engine = create_engine(database_url)
                    
                    logger.info("🔄 Using SQLAlchemy sync engine fallback")
                    df = pd.read_sql_query(text(sql_query), engine)
                    engine.dispose()
                    
                    logger.info(f"✅ Fallback execution successful - DataFrame shape: {df.shape}")
                    return df
                    
                except Exception as e:
                    logger.error(f"❌ Error in fallback execution: {e}")
                    return pd.DataFrame()
            
            # Configurar o método run_sql do Vanna
            self.vanna.run_sql = run_sql_sync
            self.vanna.run_sql_is_set = True
            
            logger.info("✅ Database connection configured for Vanna ask() method")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to setup database connection for Vanna: {e}")
            logger.info("Vanna will work in SQL-generation-only mode")


# Instância global do VannaService
_vanna_service = None

def get_vanna_service() -> VannaService:
    """Retorna instância singleton do VannaService."""
    global _vanna_service
    if _vanna_service is None:
        _vanna_service = VannaService()
    return _vanna_service