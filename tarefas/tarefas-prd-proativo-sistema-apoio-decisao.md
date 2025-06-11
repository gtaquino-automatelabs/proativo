# Lista de Tarefas - PROAtivo: Sistema Inteligente de Apoio à Decisão

## Arquivos Relevantes

- `proativo/src/database/models.py` - Modelos SQLAlchemy para equipamentos, manutenções e histórico de dados
- `proativo/src/database/connection.py` - Configuração de conexão com PostgreSQL usando SQLAlchemy async
- `proativo/src/database/repositories.py` - Padrão Repository para acesso aos dados de equipamentos e manutenções
- `proativo/src/etl/data_processor.py` - Classe principal do pipeline ETL para processamento de planilhas
- `proativo/src/etl/data_ingestion.py` - Orquestrador da ingestão automatizada de dados
- `proativo/src/etl/processors/csv_processor.py` - Processador específico para arquivos CSV usando Pandas
- `proativo/src/etl/processors/xml_processor.py` - Processador específico para arquivos XML
- `proativo/src/etl/processors/xlsx_processor.py` - Processador específico para arquivos Excel usando OpenPyXL
- `proativo/src/api/main.py` - Aplicação principal FastAPI com configuração de CORS e middleware
- `proativo/src/api/endpoints/chat.py` - Endpoint principal para processamento de consultas em linguagem natural
- `proativo/src/api/endpoints/health.py` - Endpoint de health check para monitoramento
- `proativo/src/api/services/llm_service.py` - Integração com Google Gemini 2.5 Flash API
- `proativo/src/api/services/rag_service.py` - Implementação da técnica RAG para recuperação de contexto
- `proativo/src/api/services/query_processor.py` - Conversão de linguagem natural para SQL e validação
- `proativo/src/frontend/app.py` - Aplicação principal Streamlit para interface conversacional
- `proativo/src/frontend/components/chat_interface.py` - Componente de interface de chat com histórico de sessão
- `proativo/src/frontend/components/feedback.py` - Sistema de avaliação com botões 👍/👎
- `proativo/src/utils/validators.py` - Validações de dados de entrada e queries SQL
- `proativo/src/utils/error_handlers.py` - Tratamento centralizado de erros e exceções
- `proativo/src/utils/logger.py` - Configuração de logging estruturado
- `proativo/requirements.txt` - Dependências Python com versões específicas
- `proativo/docker-compose.yml` - Configuração Docker para PostgreSQL e aplicação
- `proativo/Dockerfile` - Imagem Docker da aplicação Python
- `proativo/.env.example` - Exemplo de variáveis de ambiente necessárias
- `proativo/tests/unit/test_data_processor.py` - Testes unitários para processamento de dados
- `proativo/tests/unit/test_llm_service.py` - Testes unitários para integração com LLM
- `proativo/tests/integration/test_api_endpoints.py` - Testes de integração para endpoints da API
- `proativo/tests/integration/test_etl_pipeline.py` - Testes de integração para pipeline ETL
- `proativo/data/samples/` - Dados de exemplo para testes (CSV, XML, XLSX)

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
  - [x] 2.7 Implementar classe principal do pipeline ETL (src/etl/data_processor.py)
  - [x] 2.8 Criar orquestrador de ingestão automatizada (src/etl/data_ingestion.py)
  - [x] 2.9 Implementar validações de integridade de dados (src/utils/validators.py)
  - [x] 2.10 Criar dados de exemplo para testes (data/samples/)

- [ ] 3.0 Desenvolver API Backend com FastAPI
  - [ ] 3.1 Configurar aplicação FastAPI principal com CORS e middleware (src/api/main.py)
  - [ ] 3.2 Criar endpoint de health check (src/api/endpoints/health.py)
  - [ ] 3.3 Implementar tratamento centralizado de erros (src/utils/error_handlers.py)
  - [ ] 3.4 Configurar injeção de dependência para services e repositories
  - [ ] 3.5 Criar modelos Pydantic para request/response de chat
  - [ ] 3.6 Implementar endpoint principal de chat (src/api/endpoints/chat.py)
  - [ ] 3.7 Configurar logging estruturado e middleware de tempo de resposta
  - [ ] 3.8 Criar endpoint para feedback de usuários

- [ ] 4.0 Integrar Serviços de IA (LLM + RAG)
  - [ ] 4.1 Implementar service para integração com Google Gemini API (src/api/services/llm_service.py)
  - [ ] 4.2 Criar processador que converte linguagem natural em SQL (src/api/services/query_processor.py)
  - [ ] 4.3 Implementar sistema RAG para recuperação de contexto (src/api/services/rag_service.py)
  - [ ] 4.4 Criar templates de prompt para diferentes tipos de consulta
  - [ ] 4.5 Implementar validação e sanitização de queries SQL geradas
  - [ ] 4.6 Criar sistema de fallback para quando LLM não consegue responder
  - [ ] 4.7 Implementar cache básico para respostas similares
  - [ ] 4.8 Configurar tratamento de timeout e retry para API externa

- [ ] 5.0 Criar Interface Frontend com Streamlit
  - [ ] 5.1 Configurar aplicação Streamlit principal (src/frontend/app.py)
  - [ ] 5.2 Criar componente de interface de chat (src/frontend/components/chat_interface.py)
  - [ ] 5.3 Implementar sistema de feedback com botões 👍/👎 (src/frontend/components/feedback.py)
  - [ ] 5.4 Adicionar indicador visual de loading durante processamento
  - [ ] 5.5 Configurar layout responsivo e tema profissional
  - [ ] 5.6 Implementar validação de entrada do usuário (não vazio, tamanho máximo)
  - [ ] 5.7 Configurar tratamento de erros na interface com mensagens amigáveis
  - [ ] 5.8 Integrar frontend com API backend via requests HTTP

- [ ] 6.0 Implementar Sistema de Feedback e Métricas
  - [ ] 6.1 Criar modelos de dados para armazenar feedback dos usuários
  - [ ] 6.2 Implementar endpoint POST /feedback para coletar avaliações 👍/👎
  - [ ] 6.3 Configurar logging automático de tempo de resposta e métricas
  - [ ] 6.4 Implementar coleta de métricas de satisfação do usuário
  - [ ] 6.5 Criar sistema de logging para consultas que resultaram em "não sei"
  - [ ] 6.6 Implementar dashboard básico para visualização de métricas
  - [ ] 6.7 Configurar exportação de métricas para análise externa
  - [ ] 6.8 Criar testes para validar coleta e armazenamento de métricas 