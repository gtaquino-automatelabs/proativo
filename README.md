# PROAtivo - Sistema Inteligente de Apoio à Decisão

Sistema conversacional inteligente para consultas em linguagem natural sobre dados de manutenção de ativos elétricos, utilizando Google Gemini 2.5 Flash com implementação RAG (Retrieval-Augmented Generation) e arquitetura avançada de serviços de IA.

## 📋 Visão Geral

O PROAtivo é um protótipo de pesquisa acadêmica que permite consultas em linguagem natural sobre dados semiestruturados de manutenção de equipamentos elétricos. O sistema processa arquivos CSV, XML e XLSX e fornece respostas inteligentes através de uma interface conversacional com cache inteligente, sistema de fallback e validação avançada.

### Características Principais

- 🤖 **IA Conversacional** com Google Gemini 2.5 Flash
- 📊 **Pipeline ETL** para processamento de dados (CSV, XML, XLSX)
- 🔍 **Sistema RAG** para recuperação contextual de informações
- 🧠 **Cache Inteligente** com detecção de similaridade
- 🛡️ **Sistema de Fallback** para respostas alternativas
- 🔒 **Validação SQL** avançada com prevenção de injection
- 📝 **Templates de Prompts** especializados por contexto
- 🌐 **API REST** com FastAPI (async/await)
- 🎨 **Interface Web** com Streamlit
- 🐘 **Banco PostgreSQL** para persistência
- 🐳 **Containerização** completa com Docker
- 📈 **Sistema de Feedback** e métricas de qualidade
- 🧪 **Suite de Testes** completa (unitários + integração)
- 🔧 **Scripts Utilitários** para validação e diagnóstico

## 🏗️ Arquitetura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │    Database     │
│   Streamlit     │◄──►│    FastAPI      │◄──►│   PostgreSQL    │
│   (Port 8501)   │    │   (Port 8000)   │    │   (Port 5432)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                       ┌─────────────────┐
                       │   Google        │
                       │   Gemini API    │
                       └─────────────────┘
```

### Arquitetura de Serviços de IA

```
┌──────────────────────────────────────────────────────────────┐
│                    CAMADA DE SERVIÇOS DE IA                  │
├──────────────────────────────────────────────────────────────┤
│  🧠 LLM Service     🔍 RAG Service     🧪 Query Processor    │
│  📦 Cache Service   🛡️ Fallback       🔒 SQL Validator      │
│  📝 Prompt Templates                                         │
└──────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Pré-requisitos

- Docker Desktop instalado e rodando
- Git para clonar o repositório
- (Opcional) Python 3.11+ para desenvolvimento local

### 1. Clone o Repositório

```bash
git clone https://github.com/gtaquino-automatelabs/proativo.git
cd proativo
```

### 2. Configurar Variáveis de Ambiente

```bash
# Navegar para o diretório principal da aplicação
cd proativo

# Copiar arquivo de exemplo
cp .env.example .env

# Editar .env e adicionar sua Google API Key
nano .env  # ou seu editor preferido
```

**Variáveis obrigatórias no .env:**
```bash
GOOGLE_API_KEY=your_google_gemini_api_key_here
```

### 3. Iniciar com Docker

```bash
# Iniciar todos os serviços
docker-compose up -d

# Ver logs em tempo real
docker-compose logs -f
```

### 4. Acessar as Aplicações

- **Frontend Streamlit:** http://localhost:8501
- **API FastAPI:** http://localhost:8000
- **PgAdmin:** http://localhost:5050
- **Documentação da API:** http://localhost:8000/docs

## 🔧 Configuração Detalhada

### Arquivo .env

Copie `.env.example` para `.env` e configure as seguintes variáveis:

```bash
# Obrigatório - API Google Gemini
GOOGLE_API_KEY=your_google_gemini_api_key_here

# Banco de Dados (padrões funcionam para Docker)
DATABASE_URL=postgresql+asyncpg://proativo_user:proativo_password@localhost:5432/proativo_db
POSTGRES_DB=proativo_db
POSTGRES_USER=proativo_user
POSTGRES_PASSWORD=proativo_password

# PgAdmin (opcional, só para mudança de credenciais)
PGADMIN_EMAIL=admin@proativo.com
PGADMIN_PASSWORD=admin123

# Configurações do Gemini (opcionais - têm valores padrão)
GEMINI_MODEL=gemini-2.5-flash
GEMINI_TEMPERATURE=0.1
GEMINI_MAX_TOKENS=2048
GEMINI_TIMEOUT=30
GEMINI_MAX_RETRIES=3

# Outras configurações têm valores padrão adequados
```

### Estrutura do Projeto

```
proativo/
├── src/                          # Código fonte
│   ├── api/                      # FastAPI backend
│   │   ├── endpoints/            # Endpoints da API
│   │   │   ├── chat.py           # Endpoint principal de chat
│   │   │   ├── health.py         # Health checks
│   │   │   ├── cache_demo.py     # Demo do sistema de cache
│   │   │   ├── fallback_demo.py  # Demo do sistema de fallback
│   │   │   └── feedback.py       # Sistema de feedback
│   │   ├── services/             # Serviços de IA e backend
│   │   │   ├── llm_service.py    # Integração Google Gemini
│   │   │   ├── rag_service.py    # Sistema RAG
│   │   │   ├── query_processor.py # Processamento de linguagem natural
│   │   │   ├── cache_service.py  # Cache inteligente
│   │   │   ├── fallback_service.py # Sistema de fallback
│   │   │   ├── sql_validator.py  # Validação e sanitização SQL
│   │   │   └── prompt_templates.py # Templates de prompts
│   │   ├── models/               # Modelos de dados da API
│   │   ├── config.py             # Configurações da aplicação
│   │   ├── dependencies.py       # Dependências FastAPI
│   │   └── main.py               # Aplicação principal FastAPI
│   ├── database/                 # Camada de dados
│   │   ├── connection.py         # Conexão com PostgreSQL
│   │   ├── models.py             # Modelos SQLAlchemy
│   │   └── repositories.py       # Repositories pattern
│   ├── etl/                      # Pipeline de processamento
│   │   ├── data_processor.py     # Processador principal
│   │   ├── data_ingestion.py     # Ingestão de dados
│   │   ├── exceptions.py         # Exceções específicas
│   │   └── processors/           # Processadores por formato
│   │       ├── csv_processor.py  # Processador CSV
│   │       ├── xml_processor.py  # Processador XML
│   │       └── xlsx_processor.py # Processador XLSX
│   ├── frontend/                 # Interface Streamlit
│   │   ├── app.py                # Aplicação principal
│   │   └── components/           # Componentes reutilizáveis
│   │       ├── chat_interface.py # Interface de chat
│   │       └── feedback.py       # Componente de feedback
│   └── utils/                    # Utilitários compartilhados
│       ├── validators.py         # Validadores
│       ├── error_handlers.py     # Tratamento de erros
│       └── logger.py             # Sistema de logging
├── tests/                        # Testes
│   ├── unit/                     # Testes unitários
│   │   ├── test_llm_service.py   # Testes do LLM Service
│   │   ├── test_rag_service.py   # Testes do RAG Service
│   │   ├── test_query_processor.py # Testes do Query Processor
│   │   ├── test_cache_service.py # Testes do Cache Service
│   │   └── test_fallback_service.py # Testes do Fallback Service
│   ├── integration/              # Testes de integração
│   │   └── test_complete_pipeline.py # Pipeline completo end-to-end
│   └── conftest.py               # Configurações compartilhadas
├── scripts/                      # Scripts utilitários
│   ├── validate_system.py        # Validação geral do sistema
│   ├── test_integration.py       # Testes de integração simulados
│   └── test_etl_pipeline.py      # Testes específicos do ETL
├── data/                         # Dados e uploads
│   ├── samples/                  # Dados de exemplo
│   │   ├── electrical_assets.xlsx
│   │   ├── equipment.csv
│   │   ├── equipment.xml
│   │   ├── maintenance_orders.csv
│   │   ├── maintenance_orders.xml
│   │   ├── failures_incidents.csv
│   │   └── spare_parts.csv
│   ├── SAP.csv                   # Dados SAP de exemplo
│   └── uploads/                  # Uploads do usuário
├── docs/                         # Documentação técnica
│   ├── arquitetura-camada-ia-proativo.md
│   ├── estrutura-banco-dados.md
│   ├── llm-service-detalhado.md
│   ├── pipeline-etl-explicacao-usuarios.md
│   ├── relatorio-camada-llm-proativo.md
│   └── sistema-tratamento-erros.md
├── logs/                         # Logs da aplicação
├── init-scripts/                 # Scripts de inicialização do DB
├── requirements.txt              # Dependências Python
├── pyproject.toml                # Configuração do projeto Python
├── uv.lock                       # Lock file do UV package manager
├── Dockerfile                    # Container da aplicação
├── docker-compose.yml            # Orquestração dos serviços
├── main.py                       # Ponto de entrada da aplicação
├── validate_system.py            # Script de validação do sistema
├── test_integration.py           # Script de testes de integração
├── test_etl_pipeline.py          # Script de testes do ETL
└── .env.example                  # Exemplo de configuração
```

## 🧠 Serviços de IA Implementados

### LLM Service (`llm_service.py`)
**Integração com Google Gemini 2.5 Flash**
- ✅ Prompts estruturados por tipo de consulta
- ✅ Sistema de retry automático com backoff exponencial
- ✅ Validação e sanitização de respostas
- ✅ Cálculo de confiança automático
- ✅ Health checks e métricas detalhadas

### RAG Service (`rag_service.py`)
**Sistema de Recuperação de Contexto Relevante**
- ✅ Indexação automática de documentos e dados
- ✅ Busca semântica com embeddings simples
- ✅ Ranking de relevância por similaridade
- ✅ Suporte a múltiplas fontes de dados
- ✅ Cache de índices para performance

### Query Processor (`query_processor.py`)
**Análise de Linguagem Natural**
- ✅ Identificação automática de intenções
- ✅ Extração de entidades e parâmetros
- ✅ Geração de SQL seguro e validado
- ✅ Suporte a 6 tipos de consulta diferentes
- ✅ Normalização e sanitização de entrada

### Cache Service (`cache_service.py`)
**Cache Inteligente com Detecção de Similaridade**
- ✅ Normalização de queries para correspondência
- ✅ Detecção de consultas similares (threshold configurável)
- ✅ TTL dinâmico baseado na confiança
- ✅ Métricas detalhadas de hit/miss
- ✅ Limpeza automática de entradas expiradas

### Fallback Service (`fallback_service.py`)
**Sistema de Respostas Alternativas**
- ✅ Detecção automática de problemas no LLM
- ✅ Templates de resposta por tipo de problema
- ✅ Sugestões contextuais para o usuário
- ✅ Múltiplas estratégias de fallback
- ✅ Métricas de satisfação do usuário

### SQL Validator (`sql_validator.py`)
**Validação e Sanitização de SQL**
- ✅ Prevenção de SQL injection
- ✅ Validação de estrutura e sintaxe
- ✅ Whitelist de comandos e funções permitidas
- ✅ Análise de complexidade de queries
- ✅ Sanitização automática quando possível

### Prompt Templates (`prompt_templates.py`)
**Templates Especializados de Prompts**
- ✅ Templates por tipo de consulta
- ✅ Contextualização automática
- ✅ Exemplos específicos por domínio
- ✅ Optimização para o modelo Gemini
- ✅ Versionamento de templates

## 🔧 Scripts Utilitários

### Validação do Sistema (`scripts/validate_system.py`)
Script completo para validar a saúde do sistema:
```bash
cd proativo
python scripts/validate_system.py
```
**Funcionalidades:**
- ✅ Verificação de imports e dependências
- ✅ Testes básicos de todos os serviços
- ✅ Validação de integração entre componentes
- ✅ Relatório detalhado de status
- ✅ Códigos de saída para automação

### Testes de Integração (`scripts/test_integration.py`)
Simulação completa do pipeline sem dependência do LLM real:
```bash
cd proativo
python scripts/test_integration.py
```
**Funcionalidades:**
- ✅ Simulação end-to-end de consultas
- ✅ Métricas de performance e confiança
- ✅ Relatórios JSON detalhados
- ✅ Análise de saúde do sistema
- ✅ Distribuição de performance por categoria

### Testes do ETL (`scripts/test_etl_pipeline.py`)
Validação específica do pipeline de processamento de dados:
```bash
cd proativo
python scripts/test_etl_pipeline.py
```
**Funcionalidades:**
- ✅ Teste de todos os processadores (CSV, XML, XLSX)
- ✅ Validação de dados e formatação
- ✅ Tratamento de erros e casos extremos
- ✅ Processamento de diretórios completos
- ✅ Relatório de cobertura de testes

## 🐳 Comandos Docker

### Gerenciamento dos Serviços

```bash
# Navegar para o diretório da aplicação
cd proativo

# Iniciar todos os serviços
docker-compose up -d

# Iniciar apenas banco e PgAdmin
docker-compose up postgres pgadmin -d

# Ver logs
docker-compose logs -f [service_name]

# Parar todos os serviços
docker-compose down

# Rebuild da aplicação
docker-compose build proativo-app

# Remover volumes (CUIDADO: remove dados!)
docker-compose down -v
```

### Health Checks

```bash
# Verificar status dos containers
docker-compose ps

# Health check manual da API
curl http://localhost:8000/health

# Health check específico dos serviços de IA
curl http://localhost:8000/health/services

# Health check do PostgreSQL
docker exec proativo-postgres pg_isready -U proativo_user -d proativo_db
```

## 🗄️ Gerenciamento do Banco de Dados

### PgAdmin

1. Acesse http://localhost:5050
2. Login: `admin@proativo.com` / `admin123`
3. Adicionar servidor:
   - **Host:** `postgres` (nome do container)
   - **Port:** `5432`
   - **Database:** `proativo_db`
   - **Username:** `proativo_user`
   - **Password:** `proativo_password`

### Conexão Direta

```bash
# Conectar via psql
docker exec -it proativo-postgres psql -U proativo_user -d proativo_db

# Backup do banco
docker exec proativo-postgres pg_dump -U proativo_user proativo_db > backup.sql

# Restore do banco
docker exec -i proativo-postgres psql -U proativo_user -d proativo_db < backup.sql
```

## 📊 Uso da Aplicação

### 1. Upload de Dados

- Acesse o frontend Streamlit (http://localhost:8501)
- Faça upload de arquivos CSV, XML ou XLSX
- O sistema processará automaticamente os dados
- Use os dados de exemplo em `data/samples/` para testes

### 2. Consultas em Linguagem Natural

Exemplos de consultas que você pode fazer:

**Consultas sobre Equipamentos:**
```
"Quantos transformadores estão operacionais?"
"Liste todos os geradores em manutenção"
"Status do equipamento TR001"
"Equipamentos instalados em São Paulo"
```

**Consultas sobre Manutenções:**
```
"Manutenções programadas para esta semana"
"Qual foi a última manutenção do transformador X?"
"Quantas manutenções preventivas foram feitas este mês?"
"Técnicos com mais manutenções realizadas"
```

**Análises de Custos:**
```
"Custo total de manutenções este ano"
"Equipamento com maior custo de manutenção"
"Média de custo por tipo de equipamento"
"Comparar custos entre manutenção preventiva e corretiva"
```

**Análises de Falhas:**
```
"Equipamentos com mais falhas este ano"
"Falhas críticas nos últimos 30 dias"
"Tempo médio de resolução de falhas"
"Padrões de falhas por tipo de equipamento"
```

### 3. Sistema de Feedback

- Use os botões 👍/👎 para avaliar as respostas
- O feedback ajuda a melhorar o sistema
- Deixe comentários para sugestões específicas

### 4. Funcionalidades Avançadas

**Cache Inteligente:**
- Consultas similares são automaticamente detectadas
- Respostas em cache são servidas instantaneamente
- TTL dinâmico baseado na confiança da resposta

**Sistema de Fallback:**
- Respostas alternativas quando o LLM falha
- Sugestões contextuais para reformulação
- Detecção de consultas fora do domínio

## 🧪 Desenvolvimento e Testes

### Ambiente de Desenvolvimento Local

```bash
# Navegar para o diretório da aplicação
cd proativo

# Instalar dependências (usando UV - recomendado)
uv sync

# Ou usar pip
pip install -r requirements.txt

# Executar testes completos
pytest tests/

# Executar apenas testes unitários
pytest tests/unit/

# Executar com cobertura
pytest tests/ --cov=src/ --cov-report=html

# Executar scripts de validação
python scripts/validate_system.py
python scripts/test_integration.py
python scripts/test_etl_pipeline.py
```

### Estrutura de Testes

```bash
tests/
├── unit/                         # Testes unitários (5 arquivos)
│   ├── test_llm_service.py       # Integração Gemini + Cache + Fallback
│   ├── test_rag_service.py       # Sistema RAG e indexação
│   ├── test_query_processor.py   # Processamento linguagem natural
│   ├── test_cache_service.py     # Cache inteligente
│   └── test_fallback_service.py  # Sistema de fallback
├── integration/                  # Testes de integração
│   └── test_complete_pipeline.py # Pipeline completo end-to-end
└── conftest.py                   # Configurações compartilhadas

scripts/                          # Scripts utilitários
├── validate_system.py            # Validação geral (245 linhas)
├── test_integration.py           # Simulação completa (480 linhas)
└── test_etl_pipeline.py          # Testes ETL específicos (334 linhas)
```

### Métricas de Cobertura

- **Serviços de IA:** ~90% de cobertura de testes
- **Pipeline ETL:** ~85% de cobertura de testes
- **API Endpoints:** ~80% de cobertura de testes
- **Utilitários:** ~75% de cobertura de testes

## 📝 Logs e Monitoramento

### Visualizar Logs

```bash
# Logs da aplicação
docker-compose logs -f proativo-app

# Logs do banco
docker-compose logs -f postgres

# Logs de todos os serviços
docker-compose logs -f

# Logs específicos dos serviços de IA
docker-compose logs -f proativo-app | grep -E "(LLM|RAG|Cache|Fallback)"
```

### Arquivos de Log

- **Container:** `/app/logs/proativo.log`
- **Host:** `./logs/proativo.log`
- **Rotação:** Automática por tamanho (10MB) e tempo (7 dias)

### Métricas Disponíveis

**Via API REST:**
- `GET /health` - Status geral do sistema
- `GET /health/services` - Status detalhado dos serviços de IA
- `GET /metrics/cache` - Métricas do sistema de cache
- `GET /metrics/llm` - Métricas do LLM service
- `GET /metrics/fallback` - Métricas do sistema de fallback

## 🔒 Segurança

### Boas Práticas Implementadas

- ✅ Container roda com usuário não-root
- ✅ Validação rigorosa de entrada em todos os endpoints
- ✅ Sanitização completa de queries SQL geradas
- ✅ Prevenção de SQL injection com whitelist
- ✅ Não exposição de informações sensíveis em logs
- ✅ CORS configurado adequadamente
- ✅ Rate limiting nos endpoints críticos
- ✅ Validação de schemas com Pydantic
- ✅ Timeout em todas as operações externas

### Níveis de Segurança SQL

- **STRICT:** Apenas SELECT básico, máximo 2 JOINs
- **MODERATE:** JOINs múltiplos, funções agregadas
- **PERMISSIVE:** Funções analíticas, subconsultas complexas

### Para Produção

- 🔄 Altere todas as senhas padrão
- 🔄 Use secrets management (Docker Secrets, Kubernetes, etc.)
- 🔄 Configure HTTPS/TLS com certificados válidos
- 🔄 Implemente rate limiting mais restritivo
- 🔄 Configure backup automatizado do banco
- 🔄 Monitore métricas de segurança
- 🔄 Configure alertas de anomalias

## 🐛 Solução de Problemas

### Problemas Comuns

**Container não inicia:**
```bash
# Verificar logs
docker-compose logs [service_name]

# Rebuild forçado
docker-compose build --no-cache

# Verificar recursos do sistema
docker system df
```

**Banco não conecta:**
```bash
# Verificar se PostgreSQL está rodando
docker-compose ps postgres

# Testar conexão
docker exec proativo-postgres pg_isready -U proativo_user

# Verificar logs do banco
docker-compose logs postgres
```

**API não responde:**
```bash
# Verificar health check
curl http://localhost:8000/health

# Verificar se a porta está livre
netstat -an | grep 8000

# Verificar logs da aplicação
docker-compose logs proativo-app
```

**Serviços de IA com problemas:**
```bash
# Validar sistema completo
cd proativo && python scripts/validate_system.py

# Verificar status específico dos serviços
curl http://localhost:8000/health/services

# Executar testes de integração
python scripts/test_integration.py
```

**Google Gemini API com erro:**
```bash
# Verificar configuração da API key
grep GOOGLE_API_KEY .env

# Testar conexão manual
curl -H "Authorization: Bearer $GOOGLE_API_KEY" \
     https://generativelanguage.googleapis.com/v1beta/models
```

### Debug Mode

Para habilitar logs mais detalhados:
```bash
# No arquivo .env, adicionar:
LOG_LEVEL=DEBUG
ENABLE_DEBUG_MODE=true

# Reiniciar containers
docker-compose restart
```

## 📚 Recursos Adicionais

### Documentação da API

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Health Checks:** http://localhost:8000/health
- **Métricas:** http://localhost:8000/metrics

### Documentação Técnica

Localizada em `docs/`:
- **Arquitetura da Camada de IA:** `arquitetura-camada-ia-proativo.md`
- **Estrutura do Banco de Dados:** `estrutura-banco-dados.md`
- **LLM Service Detalhado:** `llm-service-detalhado.md`
- **Pipeline ETL para Usuários:** `pipeline-etl-explicacao-usuarios.md`
- **Relatório da Camada LLM:** `relatorio-camada-llm-proativo.md`
- **Sistema de Tratamento de Erros:** `sistema-tratamento-erros.md`

### Referências Técnicas

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Google Gemini API](https://ai.google.dev/docs)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

### Exemplos de Uso

Exemplos práticos estão disponíveis em:
- `data/samples/` - Dados de exemplo
- `tests/unit/` - Exemplos de testes
- `scripts/` - Scripts de exemplo e validação

## 🤝 Contribuição

Este é um protótipo de pesquisa acadêmica. Para contribuições:

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/nova-feature`)
3. Implemente testes para novas funcionalidades
4. Execute a suite completa de testes
5. Valide com os scripts utilitários
6. Submeta um Pull Request

### Diretrizes de Contribuição

- ✅ Código deve passar em todos os testes
- ✅ Cobertura de testes deve ser mantida acima de 80%
- ✅ Documentação deve ser atualizada
- ✅ Commits devem seguir padrão convencional
- ✅ Code review é obrigatório

## 📊 Status do Projeto

### Tarefas Concluídas ✅

- **Tarefa 1.0:** Ambiente e Infraestrutura
- **Tarefa 2.0:** Camada de Dados e Pipeline ETL
- **Tarefa 3.0:** API Backend FastAPI
- **Tarefa 4.0:** Serviços de IA Completos
  - 4.1-4.8: Todos os serviços implementados
  - 4.9: Documentação técnica completa

### Métricas de Desenvolvimento

- **Linhas de Código:** ~15.000 linhas
- **Arquivos de Código:** ~50 arquivos
- **Testes Implementados:** ~30 testes
- **Cobertura de Testes:** ~85%
- **Documentação:** 6 documentos técnicos
- **Scripts Utilitários:** 3 scripts completos

### Próximas Funcionalidades (Roadmap)

- 🔄 Interface web mais avançada
- 🔄 Suporte a mais formatos de arquivo
- 🔄 Dashboard de métricas em tempo real
- 🔄 Sistema de autenticação e autorização
- 🔄 Deployment para produção
- 🔄 Integração com mais LLMs

## 📄 Licença

[Licença específica será definida]

## 📞 Suporte

Para questões e suporte:
- **Issues:** Abra uma Issue no repositório GitHub
- **Documentação:** Consulte os docs técnicos em `docs/`
- **API Docs:** http://localhost:8000/docs (quando rodando)
- **Scripts de Debug:** Use os scripts em `scripts/` para diagnóstico

### Contatos

- **Repositório:** https://github.com/gtaquino-automatelabs/proativo
- **Documentação Técnica:** `docs/` no repositório
- **Logs de Debug:** `logs/proativo.log`

---

**Status do Projeto:** 🚀 Protótipo Funcional e Validado

**Última Atualização:** Janeiro 2025

**Versão:** 2.0 - Sistema de IA Completo 