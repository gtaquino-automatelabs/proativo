# PROAtivo - Guia do Desenvolvedor

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)](https://www.postgresql.org/)
[![pytest](https://img.shields.io/badge/pytest-7.4+-yellow.svg)](https://pytest.org/)

> **📖 Para usuários finais:** Consulte o [README principal](../README.md) para instruções de instalação e uso.

Este é o **guia técnico completo** para desenvolvedores do sistema PROAtivo - um sistema conversacional inteligente para consultas em linguagem natural sobre dados de manutenção de ativos elétricos.

## 🎯 Público-Alvo

Este README é destinado a:
- **Desenvolvedores** que vão trabalhar no código
- **Arquitetos** que precisam entender a estrutura técnica
- **DevOps** que vão configurar ambientes e deployment
- **QA Engineers** que vão trabalhar com testes

## 🏗️ Arquitetura Técnica Detalhada

### Stack Tecnológico Completo

```mermaid
graph TB
    subgraph "Frontend Layer"
        A1[Streamlit 1.28+]
        A2[Components Architecture]
        A3[State Management]
    end
    
    subgraph "API Layer"
        B1[FastAPI 0.100+]
        B2[Pydantic Models]
        B3[Async/Await]
        B4[Dependency Injection]
    end
    
    subgraph "Service Layer"
        C1[LLM Service]
        C2[RAG Service]
        C3[Cache Service]
        C4[Fallback Service]
        C5[Query Processor]
        C6[SQL Validator]
    end
    
    subgraph "Data Layer"
        D1[SQLAlchemy ORM]
        D2[Repository Pattern]
        D3[PostgreSQL 13+]
        D4[ETL Pipeline]
    end
    
    subgraph "External Services"
        E1[Google Gemini 2.5]
        E2[API Rate Limiting]
    end
    
    A1 --> B1
    B1 --> C1
    C1 --> E1
    B1 --> D1
    D1 --> D3
```

### Camada de Serviços de IA

```python
# Hierarquia de Serviços
┌─────────────────────────────────────────────────────────────┐
│                    AI SERVICES LAYER                        │
├─────────────────────────────────────────────────────────────┤
│  LLMService           │  RAGService          │  CacheService │
│  - Google Gemini      │  - Document Index    │  - Smart Cache│
│  - Retry Logic        │  - Semantic Search   │  - TTL Dynamic│
│  - Response Validate  │  - Context Ranking   │  - Similarity │
├─────────────────────────────────────────────────────────────┤
│  QueryProcessor       │  FallbackService     │  SQLValidator │
│  - Intent Detection   │  - Error Handling    │  - Injection  │
│  - Entity Extraction  │  - Alternative Resp  │  - Sanitize   │
│  - SQL Generation     │  - Degradation       │  - Whitelist  │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Setup de Desenvolvimento

### 1. Pré-requisitos de Desenvolvimento

```bash
# Ferramentas obrigatórias
- Python 3.11+ (recomendado: 3.12)
- UV package manager (recomendado) ou pip
- Docker Desktop
- Git
- PostgreSQL Client (psql)

# Ferramentas opcionais mas recomendadas
- VS Code com extensões Python
- pgAdmin ou DBeaver
- Postman ou Insomnia para testes de API
```

### 2. Configuração do Ambiente Local

```bash
# Clone e navegue para o diretório da aplicação
git clone https://github.com/gtaquino-automatelabs/proativo.git
cd proativo/proativo

# Instalar UV (recomendado)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Criar e ativar ambiente virtual
uv venv
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate     # Windows

# Instalar dependências de desenvolvimento
uv sync --dev

# Alternativamente, com pip
pip install -r requirements.txt
pip install -r requirements-dev.txt  # se existir
```

### 3. Variáveis de Ambiente para Desenvolvimento

```bash
# Copiar arquivo de configuração
cp .env.example .env

# Configurar variáveis essenciais
cat > .env << EOF
# === OBRIGATÓRIAS ===
GOOGLE_API_KEY=your_google_gemini_api_key_here

# === DESENVOLVIMENTO ===
LOG_LEVEL=DEBUG
ENABLE_DEBUG_MODE=true
DEVELOPMENT_MODE=true

# === BANCO DE DADOS ===
DATABASE_URL=postgresql+asyncpg://proativo_user:proativo_password@localhost:5432/proativo_db
POSTGRES_DB=proativo_db
POSTGRES_USER=proativo_user
POSTGRES_PASSWORD=proativo_password

# === GEMINI CONFIGURAÇÕES ===
GEMINI_MODEL=gemini-2.5-flash
GEMINI_TEMPERATURE=0.1
GEMINI_MAX_TOKENS=2048
GEMINI_TIMEOUT=30
GEMINI_MAX_RETRIES=3

# === CACHE E PERFORMANCE ===
CACHE_TTL_DEFAULT=3600
CACHE_SIMILARITY_THRESHOLD=0.85
ENABLE_QUERY_CACHE=true

# === SEGURANÇA ===
SQL_SECURITY_LEVEL=MODERATE
ENABLE_SQL_VALIDATION=true
CORS_ORIGINS=["http://localhost:3000","http://localhost:8501"]
EOF
```

## 🗂️ Estrutura Detalhada do Código

```
src/
├── api/                                    # 🌐 FastAPI Application
│   ├── endpoints/                          # 🎯 API Endpoints
│   │   ├── __init__.py
│   │   ├── chat.py                         # 💬 Main chat endpoint
│   │   ├── health.py                       # ❤️ Health checks
│   │   ├── cache_demo.py                   # 📦 Cache system demo
│   │   ├── fallback_demo.py                # 🛡️ Fallback system demo
│   │   ├── feedback.py                     # 📝 User feedback system
│   │   └── metrics_export.py               # 📊 Metrics and monitoring
│   ├── models/                             # 📋 Pydantic Models
│   │   ├── __init__.py
│   │   ├── chat.py                         # Chat request/response models
│   │   ├── feedback.py                     # Feedback models
│   │   └── metrics.py                      # Metrics models
│   ├── services/                           # 🧠 Business Logic Layer
│   │   ├── __init__.py
│   │   ├── llm_service.py                  # 🤖 Google Gemini integration
│   │   ├── rag_service.py                  # 🔍 Retrieval-Augmented Generation
│   │   ├── query_processor.py              # 🔄 Natural language processing
│   │   ├── cache_service.py                # 📦 Intelligent caching system
│   │   ├── fallback_service.py             # 🛡️ Fallback response system
│   │   ├── sql_validator.py                # 🔒 SQL validation and sanitization
│   │   └── prompt_templates.py             # 📝 Prompt engineering templates
│   ├── config.py                           # ⚙️ Application configuration
│   ├── dependencies.py                     # 🔗 FastAPI dependencies
│   └── main.py                             # 🚀 FastAPI app initialization

├── database/                               # 🗄️ Data Access Layer
│   ├── __init__.py
│   ├── connection.py                       # 🔌 Database connection management
│   ├── models.py                           # 📊 SQLAlchemy ORM models
│   └── repositories.py                     # 🏛️ Repository pattern implementation

├── etl/                                    # 📊 Data Processing Pipeline
│   ├── __init__.py
│   ├── data_processor.py                   # 🔄 Main data processing orchestrator
│   ├── data_ingestion.py                   # 📥 Data ingestion controller
│   ├── exceptions.py                       # ⚠️ ETL-specific exceptions
│   └── processors/                         # 📁 Format-specific processors
│       ├── __init__.py
│       ├── csv_processor.py                # 📄 CSV file processor
│       ├── xml_processor.py                # 🏷️ XML file processor
│       └── xlsx_processor.py               # 📊 Excel file processor

├── frontend/                               # 🎨 Streamlit UI Layer
│   ├── __init__.py
│   ├── app.py                              # 🏠 Main Streamlit application
│   ├── components/                         # 🧩 Reusable UI components
│   │   ├── __init__.py
│   │   ├── chat_interface.py               # 💬 Chat UI component
│   │   ├── error_handler.py                # ⚠️ Error display component
│   │   ├── feedback.py                     # 📝 Feedback UI component
│   │   ├── loading.py                      # ⏳ Loading states component
│   │   ├── theme.py                        # 🎨 UI theme configuration
│   │   └── validation.py                   # ✅ Input validation component
│   └── services/                           # 🌐 Frontend service layer
│       ├── __init__.py
│       ├── api_client.py                   # 🔌 API client for backend calls
│       └── http_service.py                 # 🌐 HTTP utilities

└── utils/                                  # 🛠️ Shared Utilities
    ├── __init__.py
    ├── error_handlers.py                   # ⚠️ Global error handling
    ├── logger.py                           # 📝 Logging configuration
    └── validators.py                       # ✅ Data validation utilities
```

## 🛠️ Comandos de Desenvolvimento

### Comandos Básicos

```bash
# Ativar ambiente virtual (se não estiver ativo)
source .venv/bin/activate

# Instalar novas dependências
uv add package_name
uv add --dev package_name  # Para dependências de desenvolvimento

# Atualizar dependências
uv sync

# Executar aplicação principal
python main.py

# Executar apenas a API
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Executar apenas o frontend
streamlit run src/frontend/app.py --server.port 8501
```

### Comandos de Teste

```bash
# Executar todos os testes
pytest

# Testes com cobertura
pytest --cov=src --cov-report=html --cov-report=term

# Testes específicos
pytest tests/unit/                          # Apenas testes unitários
pytest tests/integration/                   # Apenas testes de integração
pytest tests/unit/test_llm_service.py       # Arquivo específico
pytest -k "test_cache"                      # Testes que contenham "cache"

# Executar testes com verbosidade
pytest -v -s

# Executar testes em paralelo (se tiver pytest-xdist)
pytest -n auto

# Executar scripts de validação
python scripts/validate_system.py           # Validação completa do sistema
python scripts/test_integration.py          # Testes de integração simulados
python scripts/test_etl_pipeline.py         # Validação específica do ETL
```

### Comandos de Qualidade de Código

```bash
# Formatação de código (se tiver ruff)
ruff format src/ tests/

# Linting
ruff check src/ tests/

# Type checking (se tiver mypy)
mypy src/

# Verificar imports não utilizados
ruff check --select F401 src/

# Verificar complexidade de código
ruff check --select C901 src/
```

### Comandos de Banco de Dados

```bash
# Conectar ao banco local
psql -h localhost -U proativo_user -d proativo_db

# Executar migrations (se implementado)
alembic upgrade head

# Criar nova migration
alembic revision --autogenerate -m "Description"

# Resetar banco de desenvolvimento
docker-compose down -v
docker-compose up postgres -d
```

## 🧪 Testes e Qualidade

### Estrutura de Testes Detalhada

```
tests/
├── conftest.py                             # 🔧 Configurações compartilhadas e fixtures
├── unit/                                   # 🔬 Testes Unitários (85%+ cobertura)
│   ├── test_llm_service.py                 # 🤖 LLM Service + integração Gemini
│   ├── test_rag_service.py                 # 🔍 RAG Service + busca semântica
│   ├── test_query_processor.py             # 🔄 Processamento de linguagem natural
│   ├── test_cache_service.py               # 📦 Sistema de cache inteligente
│   ├── test_fallback_service.py            # 🛡️ Sistema de fallback
│   ├── test_sql_validator.py               # 🔒 Validação SQL
│   ├── test_data_processors.py             # 📊 Processadores ETL
│   └── test_repositories.py                # 🏛️ Camada de dados
├── integration/                            # 🔗 Testes de Integração
│   ├── test_complete_pipeline.py           # 🚀 Pipeline completo end-to-end
│   ├── test_api_endpoints.py               # 🌐 Endpoints da API
│   └── test_database_operations.py         # 🗄️ Operações de banco
└── fixtures/                               # 📁 Dados de teste
    ├── sample_data.json
    ├── mock_responses.json
    └── test_files/
        ├── sample.csv
        ├── sample.xml
        └── sample.xlsx
```

### Executar Testes por Categoria

```bash
# Testes de serviços de IA
pytest tests/unit/test_*service*.py -v

# Testes de API
pytest tests/integration/test_api_endpoints.py -v

# Testes de ETL
pytest tests/unit/test_data_processors.py -v

# Testes com mock (sem chamadas externas)
pytest -m "not integration" -v

# Testes que requerem API externa
pytest -m "integration" -v
```

### Métricas e Cobertura

```bash
# Relatório de cobertura detalhado
pytest --cov=src --cov-report=html
# Abrir htmlcov/index.html no browser

# Verificar cobertura específica
pytest --cov=src.api.services --cov-report=term-missing

# Benchmark de performance (se implementado)
pytest --benchmark-only -v
```

## 🔧 Desenvolvimento de Funcionalidades

### Padrões de Código

```python
# Exemplo de Service Pattern
class LLMService:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.model = model
        self.client = self._initialize_client()
    
    async def process_query(
        self, 
        query: str, 
        context: List[str] = None
    ) -> LLMResponse:
        """
        Process natural language query with LLM.
        
        Args:
            query: User query in natural language
            context: Optional context for RAG
            
        Returns:
            LLMResponse with generated answer and metadata
            
        Raises:
            LLMServiceError: If API call fails
        """
        try:
            # Implementation
            pass
        except Exception as e:
            logger.error(f"LLM processing failed: {e}")
            raise LLMServiceError(f"Failed to process query: {e}")

# Exemplo de Repository Pattern
class EquipmentRepository:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def get_by_id(self, equipment_id: str) -> Optional[Equipment]:
        """Get equipment by ID with error handling."""
        result = await self.db.execute(
            select(Equipment).where(Equipment.id == equipment_id)
        )
        return result.scalar_one_or_none()
    
    async def get_maintenance_history(
        self, 
        equipment_id: str, 
        limit: int = 10
    ) -> List[MaintenanceRecord]:
        """Get maintenance history for equipment."""
        # Implementation
        pass
```

### Adicionando Novos Endpoints

```python
# src/api/endpoints/new_feature.py
from fastapi import APIRouter, Depends, HTTPException
from src.api.dependencies import get_current_user, get_db_session
from src.api.models.new_feature import NewFeatureRequest, NewFeatureResponse

router = APIRouter(prefix="/new-feature", tags=["new-feature"])

@router.post("/", response_model=NewFeatureResponse)
async def create_new_feature(
    request: NewFeatureRequest,
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_current_user)  # Se autenticação implementada
):
    """
    Create new feature endpoint.
    
    - **request**: New feature data
    - **returns**: Created feature with ID
    """
    try:
        # Implementation
        pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Adicionando Novos Processadores ETL

```python
# src/etl/processors/new_format_processor.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from src.etl.exceptions import ProcessingError

class BaseProcessor(ABC):
    @abstractmethod
    async def process(self, file_path: str) -> List[Dict[str, Any]]:
        pass

class NewFormatProcessor(BaseProcessor):
    """Processor for new file format."""
    
    async def process(self, file_path: str) -> List[Dict[str, Any]]:
        """Process new format file."""
        try:
            # Implementation
            pass
        except Exception as e:
            raise ProcessingError(f"Failed to process {file_path}: {e}")
    
    def _validate_format(self, data: Any) -> bool:
        """Validate file format."""
        # Implementation
        pass
```

## 🐛 Debug e Troubleshooting

### Logs de Desenvolvimento

```bash
# Tail logs em tempo real
tail -f logs/proativo.log

# Filtrar logs por nível
grep "ERROR" logs/proativo.log
grep "DEBUG" logs/proativo.log | tail -50

# Logs específicos de serviços
grep "LLMService" logs/proativo.log
grep "CacheService" logs/proativo.log
```

### Debug com Python Debugger

```python
# Adicionar breakpoint no código
import pdb; pdb.set_trace()

# Ou usar breakpoint() (Python 3.7+)
breakpoint()

# Debug específico de async
import asyncio
import pdb

async def debug_async_function():
    pdb.set_trace()
    # Seu código async aqui
```

### Problemas Comuns e Soluções

```bash
# 1. Problemas de dependências
uv sync --reinstall

# 2. Problemas de importação
python -c "import src.api.main; print('OK')"

# 3. Problemas de banco de dados
python -c "from src.database.connection import test_connection; test_connection()"

# 4. Problemas com Gemini API
python -c "from src.api.services.llm_service import test_api_connection; test_api_connection()"

# 5. Limpar cache Python
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +

# 6. Verificar configuração
python -c "from src.api.config import settings; print(settings.dict())"
```

## 📈 Performance e Monitoramento

### Profiling de Performance

```bash
# Profile de CPU
python -m cProfile -o profile_output.prof main.py

# Análise de profile
python -c "import pstats; p = pstats.Stats('profile_output.prof'); p.sort_stats('cumulative').print_stats(10)"

# Memory profiling (se tiver memory_profiler)
python -m memory_profiler main.py

# Line profiling (se tiver line_profiler)
kernprof -l -v main.py
```

### Métricas de Desenvolvimento

```python
# Adicionar métricas customizadas
from src.utils.logger import logger
import time

def measure_execution_time(func):
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        execution_time = time.time() - start_time
        logger.info(f"{func.__name__} executed in {execution_time:.2f}s")
        return result
    return wrapper

@measure_execution_time
async def slow_function():
    # Sua função aqui
    pass
```

## 🚀 Deploy e DevOps

### Build e Containerização

```bash
# Build local da aplicação
docker build -t proativo:dev .

# Build com cache disabled
docker build --no-cache -t proativo:dev .

# Multi-stage build para produção
docker build --target production -t proativo:prod .

# Verificar imagem
docker images proativo:*
docker history proativo:dev
```

### Environment Management

```bash
# Desenvolvimento
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Testes
docker-compose -f docker-compose.test.yml up --abort-on-container-exit

# Produção (se implementado)
docker-compose -f docker-compose.prod.yml up -d
```

## 🤝 Contribuição para Desenvolvedores

### Workflow de Desenvolvimento

```bash
# 1. Criar branch para feature
git checkout -b feature/nova-funcionalidade

# 2. Fazer mudanças e testar
# ... código ...
pytest tests/
python scripts/validate_system.py

# 3. Commit com mensagem descritiva
git add .
git commit -m "feat: adiciona nova funcionalidade X

- Implementa endpoint /api/nova-funcionalidade
- Adiciona validação de entrada
- Inclui testes unitários
- Atualiza documentação"

# 4. Push e Pull Request
git push origin feature/nova-funcionalidade
```

### Code Review Checklist

- [ ] **Testes**: Novos testes adicionados e todos passando
- [ ] **Documentação**: Docstrings e comentários atualizados
- [ ] **Type Hints**: Todas as funções têm type hints
- [ ] **Error Handling**: Tratamento adequado de erros
- [ ] **Logging**: Logs apropriados adicionados
- [ ] **Performance**: Considerações de performance avaliadas
- [ ] **Security**: Sem vulnerabilidades introduzidas
- [ ] **Backward Compatibility**: Compatibilidade mantida

## 📚 Recursos para Desenvolvedores

### Documentação Técnica Avançada
- [Arquitetura da Camada de IA](docs/arquitetura-camada-ia-proativo.md)
- [Sistema de Tratamento de Erros](docs/sistema-tratamento-erros.md)
- [LLM Service - Implementação Detalhada](docs/llm-service-detalhado.md)

### APIs e Ferramentas
- **Local API Docs**: http://localhost:8000/docs
- **Health Checks**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics
- **Database Admin**: http://localhost:5050

### Referências Técnicas
- [FastAPI Advanced Features](https://fastapi.tiangolo.com/advanced/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Pydantic Advanced Usage](https://docs.pydantic.dev/usage/models/)
- [Google Gemini API Reference](https://ai.google.dev/api/rest)

## ⚡ Performance Tips

### Otimizações de Código
```python
# Use async/await consistentemente
async def fetch_data():
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

# Cache expensive operations
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_function(param):
    # Operação custosa
    return result

# Use generators para grandes datasets
def process_large_dataset():
    for item in large_dataset:
        yield process_item(item)
```

### Database Performance
```python
# Use select_related para evitar N+1 queries
from sqlalchemy.orm import selectinload

result = await session.execute(
    select(Equipment).options(selectinload(Equipment.maintenance_records))
)

# Use batch operations
await session.execute(
    insert(Equipment).values([
        {"name": "Equip1", "type": "Transformer"},
        {"name": "Equip2", "type": "Generator"},
    ])
)
```

---

## 📞 Suporte para Desenvolvedores

**🐛 Issues**: [GitHub Issues](https://github.com/gtaquino-automatelabs/proativo/issues)  
**💬 Discussões**: [GitHub Discussions](https://github.com/gtaquino-automatelabs/proativo/discussions)  
**📖 Wiki**: [Project Wiki](https://github.com/gtaquino-automatelabs/proativo/wiki)  

**🚀 Status**: Protótipo Funcional - Versão 2.0  
**🧪 Cobertura**: 85%+ testes  
**📊 Métricas**: Disponíveis via `/metrics`  

---
*Para informações de uso e instalação, consulte o [README principal](../README.md).* 