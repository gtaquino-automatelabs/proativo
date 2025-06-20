# Lista de Tarefas - PROAtivo: Sistema Inteligente de Apoio à Decisão

## Arquivos Relevantes

- `proativo/src/database/models.py` - Modelos SQLAlchemy para equipamentos, manutenções e histórico de dados
- `proativo/src/database/connection.py` - Configuração de conexão com PostgreSQL usando SQLAlchemy async
- `proativo/src/database/repositories.py` - Padrão Repository para acesso aos dados de equipamentos e manutenções
- `proativo/src/etl/exceptions.py` - Exceções customizadas para processamento ETL
- `proativo/src/etl/data_processor.py` - Classe principal do pipeline ETL para processamento de planilhas
- `proativo/src/etl/data_ingestion.py` - Orquestrador da ingestão automatizada de dados
- `proativo/src/etl/processors/csv_processor.py` - Processador específico para arquivos CSV usando Pandas
- `proativo/src/etl/processors/xml_processor.py` - Processador específico para arquivos XML
- `proativo/src/etl/processors/xlsx_processor.py` - Processador específico para arquivos Excel usando OpenPyXL
- `proativo/src/api/main.py` - Aplicação principal FastAPI com configuração de CORS e middleware
- `src/api/endpoints/chat.py` - Endpoint principal para processamento de consultas em linguagem natural com mock de LLM funcional
- `proativo/src/api/endpoints/health.py` - Endpoint de health check para monitoramento
- `proativo/src/api/services/llm_service.py` - Integração completa com Google Gemini 2.5 Flash API incluindo cache, retry, validação, prompts estruturados e sistema automático de fallback
- `proativo/src/api/services/rag_service.py` - Implementação da técnica RAG para recuperação de contexto
- `proativo/src/api/services/query_processor.py` - Processador avançado de linguagem natural para SQL com análise de intenção, extração de entidades, geração segura de queries e sistema avançado de validação/sanitização SQL
- `proativo/src/frontend/app.py` - Aplicação principal Streamlit com interface conversacional completa, sidebar de navegação e integração com API backend
- `proativo/src/frontend/components/chat_interface.py` - Componente modular de chat com gerenciamento de histórico, renderização de mensagens, estatísticas e exportação de dados
- `proativo/src/frontend/components/feedback.py` - Sistema completo de feedback com botões 👍/👎, comentários, histórico, estatísticas e integração com API
- `proativo/src/frontend/components/loading.py` - Sistema avançado de indicadores visuais de loading com spinners, progress bars, status de API, métricas de performance e histórico de eventos
- `proativo/src/frontend/components/theme.py` - Gerenciador profissional de tema e estilos com CSS customizado, layout responsivo, esquemas de cores, componentes visuais e animações
- `proativo/src/frontend/components/validation.py` - Sistema completo de validação de entrada com verificação de tamanho, SQL injection, XSS, caracteres especiais, feedback visual, estatísticas e configuração customizável
- `proativo/src/frontend/components/error_handler.py` - Sistema avançado de tratamento de erros com classificação automática, retry inteligente, fallbacks, mensagens amigáveis, log detalhado, dashboard de erros e integração completa
- `proativo/src/frontend/services/http_service.py` - Serviço HTTP base com sessões otimizadas, cache inteligente, retry automático, estatísticas de performance, gestão de headers e configurações de timeout
- `proativo/src/frontend/services/api_client.py` - Cliente da API PROAtivo que centraliza toda comunicação HTTP com endpoints específicos, cache, tratamento de erros, estatísticas por endpoint e testes de conectividade
- `proativo/src/frontend/services/__init__.py` - Módulo de serviços do frontend com factory functions para APIClient e HTTPService
- `proativo/src/utils/validators.py` - Validações de dados de entrada e queries SQL
- `proativo/src/utils/error_handlers.py` - Sistema completo de tratamento centralizado de erros com hierarquia de exceções customizadas e handlers FastAPI
- `proativo/src/utils/logger.py` - Configuração de logging estruturado
- `proativo/src/api/config.py` - Configuração centralizada com Pydantic BaseSettings para todas as configurações do sistema
- `proativo/src/api/dependencies.py` - Sistema de injeção de dependências com funções para criar e gerenciar services e repositories automaticamente
- `proativo/src/api/models/chat.py` - Modelos Pydantic V2 para chat, feedback e comunicação com IA incluindo validações e tipos de dados estruturados
- `proativo/src/api/endpoints/feedback.py` - Sistema completo de feedback com avaliações 👍/👎, comentários e análise de estatísticas
- `src/api/services/fallback_service.py` - Sistema completo de fallback com validação de respostas, múltiplas estratégias, detecção de triggers e métricas de uso
- `proativo/tests/unit/test_llm_service.py` - Testes unitários completos para o LLMService com 27 cenários de teste
- `tests/unit/test_query_processor.py` - Suite completa de 30+ testes para o QueryProcessor cobrindo análise NL, geração SQL, validação de segurança e sanitização avançada
- `src/api/services/prompt_templates.py` - Sistema especializado de templates de prompt com 7 tipos de consulta otimizados para equipamentos elétricos
- `proativo/requirements.txt` - Dependências Python com versões específicas
- `proativo/docker-compose.yml` - Configuração Docker para PostgreSQL e aplicação
- `proativo/Dockerfile` - Imagem Docker da aplicação Python
- `proativo/.env.example` - Exemplo de variáveis de ambiente necessárias
- `proativo/tests/unit/test_data_processor.py` - Testes unitários para processamento de dados
- `proativo/tests/unit/test_llm_service.py` - Testes unitários para integração com LLM
- `proativo/tests/integration/test_api_endpoints.py` - Testes de integração para endpoints da API
- `proativo/tests/integration/test_etl_pipeline.py` - Testes de integração para pipeline ETL
- `proativo/data/samples/` - Dados de exemplo para testes (CSV, XML, XLSX)
- `proativo/data/samples/equipment.xml` - Dados de exemplo de equipamentos em formato XML
- `proativo/data/samples/maintenance_orders.xml` - Dados de exemplo de ordens de manutenção em formato XML
- `proativo/data/samples/electrical_assets.xlsx` - Dados de exemplo de equipamentos e manutenções em formato XLSX
- `proativo/docs/sistema-tratamento-erros.md` - Documentação em linguagem simples sobre o sistema de tratamento de erros
- `proativo/docs/relatorio-camada-llm-proativo.md` - Relatório técnico completo sobre a arquitetura LLM com Google Gemini, sistema RAG, prompts e tools
- `proativo/docs/arquitetura-camada-ia-proativo.md` - Documentação completa da arquitetura de IA com diagramas, configurações e métricas
- `proativo/docs/llm-service-detalhado.md` - Documentação técnica detalhada do LLMService com implementação Google Gemini
- `tests/unit/test_fallback_service.py` - Suite completa de testes para o sistema de fallback com 25+ cenários incluindo validação, geração de respostas e integração
- `proativo/src/api/endpoints/metrics_export.py` - Sistema completo de exportação de métricas com suporte a JSON, CSV e XLSX para análise externa e integração com ferramentas de BI
- `proativo/src/database/models.py` - Modelo UserFeedback para armazenamento estruturado de feedback dos usuários com categorização, priorização e análise de sentimento
- `proativo/src/database/repositories.py` - UserFeedbackRepository com métodos especializados para consultas, estatísticas e análise de padrões de feedback

### Observações

- Testes unitários devem estar na pasta `tests/unit/` e de integração em `tests/integration/`
- Use `pytest tests/` para executar todos os testes ou `pytest tests/unit/` para específicos
- Configure variáveis de ambiente no arquivo `.env` baseado no `.env.example`
- PostgreSQL deve estar rodando antes de iniciar a aplicação (via Docker Compose)
- O projeto segue padrões async/await do Python para melhor performance

## Tarefas

- [x] 1.0 Configurar Ambiente e Infraestrutura Base
  - [x] 1.1 Criar estrutura completa de diretórios do projeto conforme arquitetura (src/, tests/unit/, tests/integration/, docs/, data/samples/, etl/processors/)
  - [x] 1.2 Configurar arquivo requirements.txt com todas as dependências necessárias
  - [x] 1.3 Criar arquivo .env.example com variáveis de ambiente necessárias
  - [x] 1.4 Configurar Dockerfile para containerização da aplicação Python
  - [x] 1.5 Configurar docker-compose.yml com PostgreSQL e aplicação
  - [x] 1.6 Criar arquivo README.md com instruções de setup e execução
  - [x] 1.7 Configurar estrutura de logging básica (src/utils/logger.py)

- [x] 2.0 Implementar Camada de Dados e Pipeline ETL
  - [x] 2.1 Configurar conexão com PostgreSQL usando SQLAlchemy async (src/database/connection.py)
  - [x] 2.2 Definir modelos SQLAlchemy para equipamentos, manutenções e histórico (src/database/models.py)
  - [x] 2.3 Implementar repositories usando padrão Repository (src/database/repositories.py)
  - [x] 2.4 Criar processador para arquivos CSV usando Pandas (src/etl/processors/csv_processor.py)
  - [x] 2.5 Criar processador para arquivos XML (src/etl/processors/xml_processor.py)
  - [x] 2.6 Criar processador para arquivos XLSX usando OpenPyXL (src/etl/processors/xlsx_processor.py)
  - [x] 2.7 Implementar validações de integridade de dados (src/utils/validators.py)
  - [x] 2.8 Implementar classe principal do pipeline ETL (src/etl/data_processor.py)
  - [x] 2.9 Criar orquestrador de ingestão automatizada (src/etl/data_ingestion.py)
  - [x] 2.10 Criar dados de exemplo para testes (data/samples/)

- [x] 3.0 Desenvolver API Backend com FastAPI
  - [x] 3.1 Configurar aplicação FastAPI principal com CORS e middleware (src/api/main.py)
  - [x] 3.2 Criar endpoint de health check (src/api/endpoints/health.py)
  - [x] 3.3 Implementar tratamento centralizado de erros (src/utils/error_handlers.py)
  - [x] 3.4 Configurar injeção de dependência para services e repositories
  - [x] 3.5 Criar modelos Pydantic para request/response de chat
  - [x] 3.6 Implementar endpoint principal de chat (src/api/endpoints/chat.py)
  - [x] 3.7 Configurar logging estruturado e middleware de tempo de resposta
  - [x] 3.8 Criar endpoint para feedback de usuários

- [x] 4.0 Integrar Serviços de IA (LLM + RAG)
  - [x] 4.1 Implementar service para integração com Google Gemini API
  - [x] 4.2 Implementar RAG service para recuperação de contexto
  - [x] 4.3 Criar sistema de prompts dinâmicos
  - [x] 4.4 Implementar query processor avançado
  - [x] 4.5 Sistema de validação e sanitização SQL
  - [x] 4.6 Sistema de fallback para LLM
  - [x] 4.7 Implementar cache básico para respostas similares
  - [x] 4.8 Testar integração completa com dados reais
  - [x] 4.9 Documentar arquitetura da camada de IA

- [x] 5.0 Criar Interface Frontend com Streamlit
  - [x] 5.1 Configurar aplicação Streamlit principal (src/frontend/app.py)
  - [x] 5.2 Criar componente de interface de chat (src/frontend/components/chat_interface.py)
  - [x] 5.3 Implementar sistema de feedback com botões 👍/👎 (src/frontend/components/feedback.py)
  - [x] 5.4 Adicionar indicador visual de loading durante processamento
  - [x] 5.5 Configurar layout responsivo e tema profissional
  - [x] 5.6 Implementar validação de entrada do usuário (não vazio, tamanho máximo)
  - [x] 5.7 Configurar tratamento de erros na interface com mensagens amigáveis
  - [x] 5.8 Integrar frontend com API backend via requests HTTP

- [x] 6.0 Implementar Sistema de Feedback e Métricas
  - [x] 6.1 Criar modelos de dados para armazenar feedback dos usuários
  - [x] 6.2 Implementar endpoint POST /feedback para coletar avaliações 👍/👎
  - [x] 6.3 Configurar logging automático de tempo de resposta e métricas
  - [x] 6.4 Implementar coleta de métricas de satisfação do usuário
  - [x] 6.5 Criar sistema de logging para consultas que resultaram em "não sei"
  - [x] 6.6 Implementar dashboard básico para visualização de métricas
  - [x] 6.7 Configurar exportação de métricas para análise externa
  - [x] 6.8 Criar testes para validar coleta e armazenamento de métricas 