# PROAtivo - Sistema Inteligente de Apoio à Decisão

Sistema conversacional inteligente para consultas em linguagem natural sobre dados de manutenção de ativos elétricos, utilizando Google Gemini 2.5 Flash com implementação RAG (Retrieval-Augmented Generation).

## 📋 Visão Geral

O PROAtivo é um protótipo de pesquisa acadêmica que permite consultas em linguagem natural sobre dados semiestruturados de manutenção de equipamentos elétricos. O sistema processa arquivos CSV, XML e XLSX e fornece respostas inteligentes através de uma interface conversacional.

### Características Principais

- 🤖 **IA Conversacional** com Google Gemini 2.5 Flash
- 📊 **Pipeline ETL** para processamento de dados (CSV, XML, XLSX)
- 🔍 **Sistema RAG** para recuperação contextual de informações
- 🌐 **API REST** com FastAPI (async/await)
- 🎨 **Interface Web** com Streamlit
- 🐘 **Banco PostgreSQL** para persistência
- 🐳 **Containerização** completa com Docker
- 📈 **Sistema de Feedback** e métricas de qualidade

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

## 🚀 Quick Start

### Pré-requisitos

- Docker Desktop instalado e rodando
- Git para clonar o repositório
- (Opcional) Python 3.11+ para desenvolvimento local

### 1. Clone o Repositório

```bash
git clone <repository-url>
cd proativo
```

### 2. Configurar Variáveis de Ambiente

```bash
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

# Outras configurações têm valores padrão adequados
```

### Estrutura do Projeto

```
proativo/
├── src/                          # Código fonte
│   ├── api/                      # FastAPI backend
│   │   ├── endpoints/            # Endpoints da API
│   │   └── services/             # Serviços (LLM, RAG, etc.)
│   ├── database/                 # Modelos e repositories
│   ├── etl/                      # Pipeline de processamento
│   │   └── processors/           # Processadores por formato
│   ├── frontend/                 # Interface Streamlit
│   │   └── components/           # Componentes reutilizáveis
│   └── utils/                    # Utilitários compartilhados
├── tests/                        # Testes unitários e integração
├── data/                         # Dados e uploads
│   └── samples/                  # Dados de exemplo
├── docs/                         # Documentação
├── logs/                         # Logs da aplicação
├── requirements.txt              # Dependências Python
├── Dockerfile                    # Container da aplicação
├── docker-compose.yml            # Orquestração dos serviços
└── .env.example                  # Exemplo de configuração
```

## 🐳 Comandos Docker

### Gerenciamento dos Serviços

```bash
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

- Acesse o frontend Streamlit
- Faça upload de arquivos CSV, XML ou XLSX
- O sistema processará automaticamente os dados

### 2. Consultas em Linguagem Natural

Exemplos de consultas que você pode fazer:

```
"Quantos equipamentos tiveram manutenção preventiva este mês?"
"Mostre os equipamentos com maior número de falhas"
"Qual a média de tempo entre manutenções do equipamento X?"
"Liste os equipamentos que precisam de manutenção urgente"
```

### 3. Sistema de Feedback

- Use os botões 👍/👎 para avaliar as respostas
- O feedback ajuda a melhorar o sistema

## 🧪 Desenvolvimento e Testes

### Ambiente de Desenvolvimento Local

```bash
# Instalar dependências
pip install -r requirements.txt

# Executar testes
pytest tests/

# Executar apenas testes unitários
pytest tests/unit/

# Executar com cobertura
pytest tests/ --cov=src/
```

### Estrutura de Testes

```bash
tests/
├── unit/                         # Testes unitários
│   ├── test_data_processor.py    # Processamento de dados
│   └── test_llm_service.py       # Integração LLM
└── integration/                  # Testes de integração
    ├── test_api_endpoints.py     # Endpoints da API
    └── test_etl_pipeline.py      # Pipeline ETL
```

## 📝 Logs e Monitoramento

### Visualizar Logs

```bash
# Logs da aplicação
docker-compose logs -f proativo-app

# Logs do banco
docker-compose logs -f postgres

# Logs de todos os serviços
docker-compose logs -f
```

### Arquivos de Log

- **Container:** `/app/logs/proativo.log`
- **Host:** `./logs/proativo.log`

## 🔒 Segurança

### Boas Práticas Implementadas

- ✅ Container roda com usuário não-root
- ✅ Validação de entrada em todos os endpoints
- ✅ Sanitização de queries SQL geradas
- ✅ Não exposição de informações sensíveis em logs
- ✅ CORS configurado adequadamente

### Para Produção

- 🔄 Altere todas as senhas padrão
- 🔄 Use secrets management (Docker Secrets, etc.)
- 🔄 Configure HTTPS/TLS
- 🔄 Implemente rate limiting
- 🔄 Configure backup automatizado

## 🐛 Solução de Problemas

### Problemas Comuns

**Container não inicia:**
```bash
# Verificar logs
docker-compose logs [service_name]

# Rebuild forçado
docker-compose build --no-cache
```

**Banco não conecta:**
```bash
# Verificar se PostgreSQL está rodando
docker-compose ps postgres

# Testar conexão
docker exec proativo-postgres pg_isready -U proativo_user
```

**API não responde:**
```bash
# Verificar health check
curl http://localhost:8000/health

# Verificar se a porta está livre
netstat -an | grep 8000
```

## 📚 Recursos Adicionais

### Documentação da API

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Referências Técnicas

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Google Gemini API](https://ai.google.dev/docs)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

## 🤝 Contribuição

Este é um protótipo de pesquisa acadêmica. Para contribuições:

1. Fork o projeto
2. Crie uma branch para sua feature
3. Implemente testes para novas funcionalidades
4. Submeta um Pull Request

## 📄 Licença

[Incluir informações de licença aqui]

## 📞 Suporte

Para questões e suporte:
- Abra uma Issue no repositório
- Consulte a documentação da API
- Verifique os logs para debugging

---

**Status do Projeto:** 🚧 Protótipo em Desenvolvimento

**Última Atualização:** Junho 2025 