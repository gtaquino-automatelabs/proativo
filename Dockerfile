# Use Python 3.11 slim image para menor tamanho e compatibilidade
FROM python:3.11-slim

# Definir variáveis de ambiente para otimização Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Criar usuário não-root para segurança
RUN groupadd --gid 1000 proativo && \
    useradd --uid 1000 --gid proativo --shell /bin/bash --create-home proativo

# Instalar dependências do sistema necessárias
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    postgresql-client \
    dos2unix \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Definir diretório de trabalho
WORKDIR /app

# Copiar arquivos de configuração primeiro para aproveitar cache do Docker
COPY requirements.txt pyproject.toml ./

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Criar diretórios necessários
RUN mkdir -p logs data/uploads data/samples init-scripts scripts docs

# Copiar código da aplicação
COPY src/ ./src/
COPY tests/ ./tests/
COPY main.py ./
COPY scripts/ ./scripts/
COPY docs/ ./docs/

# Copiar e configurar scripts de inicialização
COPY scripts/setup/entrypoint.sh ./entrypoint.sh
RUN sed -i 's/\r$//' ./entrypoint.sh
COPY scripts/setup/wait-for-postgres.sh ./wait-for-postgres.sh
COPY scripts/setup/setup_complete_database.py ./scripts/setup/setup_complete_database.py
COPY scripts/setup/create_tables.py ./scripts/setup/create_tables.py
COPY scripts/setup/populate_database.py ./scripts/setup/populate_database.py
COPY scripts/setup/check_database.py ./scripts/setup/check_database.py

# Configurar permissões para scripts de inicialização e converter fim de linha
RUN chmod +x ./entrypoint.sh ./wait-for-postgres.sh && \
    dos2unix ./entrypoint.sh ./wait-for-postgres.sh 2>/dev/null || true

# Mudar ownership para usuário não-root
RUN chown -R proativo:proativo /app

# Trocar para usuário não-root
USER proativo

# Expor porta da aplicação FastAPI
EXPOSE 8000

# Health check para monitoramento
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Configurar entrypoint para automação completa
ENTRYPOINT ["./entrypoint.sh"]

# Comando padrão para iniciar a aplicação FastAPI (pode ser sobrescrito)
CMD ["api"]