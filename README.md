# PROAtivo - Sistema Conversacional para Manutenção de Ativos

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-20+-blue.svg)](https://www.docker.com/)

Sistema conversacional inteligente que permite consultas em **linguagem natural** sobre dados de manutenção de ativos elétricos, utilizando IA (Google Gemini) para transformar perguntas do usuário em consultas SQL e fornecer respostas contextualizadas.

## 🎯 Funcionalidade Principal

O **PROAtivo** permite que usuários façam perguntas como:
- *"Quantos transformadores foram mantidos este mês?"*
- *"Quais equipamentos tiveram falhas recorrentes?"*
- *"Mostre o histórico de manutenção do transformador TR001"*
- *"Qual a criticidade média dos equipamentos por tipo?"*

O sistema processa essas perguntas, gera consultas SQL seguras e retorna respostas em linguagem natural com dados contextualizados.

## 🏗️ Arquitetura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API FastAPI   │    │   PostgreSQL    │
│   Streamlit     │◄──►│   + IA Services │◄──►│   Database      │
│   (Port 8501)   │    │   (Port 8000)   │    │   (Port 5432)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                       ┌─────────────────┐
                       │  Google Gemini  │
                       │   LLM Service   │
                       └─────────────────┘
```

## 🚀 Como Executar

### 1. Pré-requisitos
- Docker Desktop instalado
- Git

### 2. Configuração Inicial

```bash
# Clone o repositório
git clone https://github.com/gtaquino-automatelabs/proativo.git
cd proativo/proativo

# Configure as variáveis de ambiente
cp .env.example .env
```

**⚠️ IMPORTANTE**: Edite o arquivo `.env` e configure:
```bash
GOOGLE_API_KEY=sua_chave_api_google_gemini_aqui
```

### 3. Executar a Aplicação

```bash
# Iniciar todos os serviços
docker-compose up -d

# Verificar se os containers estão rodando
docker-compose ps
```

### 4. Popular Dados Iniciais

```bash
# Popular banco com dados de exemplo (OBRIGATÓRIO na primeira execução)
docker-compose exec proativo-app python scripts/setup/populate_database.py
docker-compose exec proativo-app python scripts/setup/populate_data_history.py

# Verificar se dados foram carregados
docker-compose exec proativo-app python scripts/debugging/check_database.py
```

### 5. Acessar a Aplicação

- **Frontend (Interface do usuário)**: http://localhost:8501
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Database Admin (pgAdmin)**: http://localhost:5050
  - Email: `admin@example.com`
  - Senha: `your_admin_password_here`

## 🗂️ Estrutura do Projeto

```
proativo/
├── src/
│   ├── api/                    # FastAPI - Endpoints e serviços
│   ├── database/               # Modelos e repositórios de dados
│   ├── frontend/               # Interface Streamlit
│   └── etl/                    # Pipeline de processamento de dados
├── scripts/
│   ├── setup/                  # Scripts de configuração inicial
│   ├── debugging/              # Scripts de diagnóstico
│   └── testing/                # Scripts de validação
├── data/
│   ├── samples/                # Dados de exemplo
│   └── uploads/                # Arquivos enviados
├── docker-compose.yml          # Configuração dos containers
└── .env                        # Variáveis de ambiente
```

## 🛠️ Comandos Básicos

### Gerenciamento da Aplicação
```bash
# Iniciar aplicação
docker-compose up -d

# Parar aplicação
docker-compose down

# Reiniciar aplicação
docker-compose restart

# Ver logs
docker-compose logs -f proativo-app

# Ver status dos containers
docker-compose ps
```

### Scripts de Manutenção
```bash
# Verificar status do sistema
docker-compose exec proativo-app python scripts/testing/validate_system.py

# Verificar banco de dados
docker-compose exec proativo-app python scripts/debugging/check_database.py

# Limpar dados duplicados
docker-compose exec proativo-app python scripts/maintenance/clean_duplicate_equipment.py

# Testar pipeline ETL
docker-compose exec proativo-app python scripts/testing/test_etl_pipeline.py
```

### Upload de Dados
```bash
# Processar arquivo CSV de equipamentos
docker-compose exec proativo-app python -c "
from src.etl.data_processor import DataProcessor
processor = DataProcessor()
processor.process_file('data/samples/equipment.csv', 'equipment')
"

# Processar arquivo de ordens de manutenção
docker-compose exec proativo-app python -c "
from src.etl.data_processor import DataProcessor
processor = DataProcessor()
processor.process_file('data/samples/maintenance_orders.csv', 'maintenance_orders')
"
```

### Debugging
```bash
# Acessar container da aplicação
docker-compose exec proativo-app bash

# Verificar logs de erro
docker-compose exec proativo-app tail -f logs/proativo.log

# Conectar ao banco de dados
docker-compose exec postgres psql -U proativo_user -d proativo_db
```

## 🧪 Validação do Sistema

Após a instalação, execute este comando para verificar se tudo está funcionando:

```bash
docker-compose exec proativo-app python scripts/testing/validate_system.py
```

**Resultado esperado:**
- ✅ Conexão com banco de dados
- ✅ Dados carregados (equipamentos e manutenções)
- ✅ API respondendo
- ✅ Serviço de IA funcionando
- ✅ Frontend acessível

## 📋 Tipos de Dados Suportados

O sistema processa os seguintes tipos de dados:

### Equipamentos
- Transformadores, Disjuntores, Geradores
- Localização, tipo, criticidade
- Status operacional

### Manutenções
- Manutenções preventivas e corretivas
- Datas, responsáveis, observações
- Peças utilizadas e custos

### Incidentes
- Falhas e incidentes históricos
- Análise de causa raiz
- Impacto operacional

## 🔧 Solução de Problemas

### Problemas Comuns

**Sistema responde "dados não encontrados":**
```bash
docker-compose exec proativo-app python scripts/setup/populate_database.py
```

**Erro de conexão com API Gemini:**
- Verifique se `GOOGLE_API_KEY` está configurado no `.env`
- Teste: `docker-compose exec proativo-app python -c "from src.api.services.llm_service import LLMService; print('API OK')"`

**Container não inicia:**
```bash
docker-compose logs proativo-app
docker-compose down && docker-compose up -d
```

**Reset completo:**
```bash
docker-compose down -v
docker-compose up -d
docker-compose exec proativo-app python scripts/setup/populate_database.py
```

## 📞 Suporte

Para questões e suporte:
- **Issues**: [GitHub Issues](https://github.com/gtaquino-automatelabs/proativo/issues)
- **Logs**: Verifique `logs/proativo.log` dentro do container

---

**Versão**: 2.0 - Protótipo Funcional  
**Status**: ✅ Operacional com Docker 