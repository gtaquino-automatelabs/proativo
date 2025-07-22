#!/bin/bash
# entrypoint.sh
# Script principal para inicialização automática do container PROAtivo

set -e

echo "🚀 INICIANDO PROATIVO - AUTOMAÇÃO COMPLETA"
echo "=========================================="

# Configurações
POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
PYTHON_PATH="/app"
POPULATE_TIMEOUT=300  # 5 minutos timeout para população

# Função para log com timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Função para executar com timeout
run_with_timeout() {
    local timeout=$1
    local command=$2
    local description=$3
    
    log "⏳ Executando: $description"
    timeout $timeout bash -c "$command" || {
        log "❌ TIMEOUT ou ERRO em: $description"
        return 1
    }
    log "✅ Concluído: $description"
}

# Determinar comando antes das etapas de setup
if [ "$1" = "streamlit" ]; then
    log "🎨 MODO STREAMLIT - Pulando configuração de banco"
    log "Streamlit se conectará via API em: $API_BASE_URL"
    cd $PYTHON_PATH
else
    # ETAPA 1: Aguardar PostgreSQL estar pronto (apenas para API)
    log "ETAPA 1: Aguardando PostgreSQL..."
    echo "Host: $POSTGRES_HOST"
    echo "Usuário: $POSTGRES_USER"
    echo "Banco: $POSTGRES_DB"

    run_with_timeout 60 "
        until pg_isready -h $POSTGRES_HOST -p 5432 -U $POSTGRES_USER; do
            echo '⏳ PostgreSQL não está pronto, aguardando...'
            sleep 2
        done
    " "Verificação PostgreSQL" || {
        log "❌ FALHA: PostgreSQL não respondeu a tempo"
        exit 1
    }

    # ETAPA 2: Verificar se banco precisa ser populado
    log "ETAPA 2: Verificando necessidade de população..."

    cd $PYTHON_PATH

    # ETAPA 3: Configuração completa do banco (master script)
    log "ETAPA 3: Configuração automática do banco..."

    # Força a string de conexão correta para os scripts Python
    export database_url="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:5432/${POSTGRES_DB}"
    export DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:5432/${POSTGRES_DB}"

    log "🔗 Usando conexão: $database_url"

    run_with_timeout $POPULATE_TIMEOUT "
        python3 scripts/setup/setup_complete_database.py
    " "Configuração completa do banco" || {
        log "❌ FALHA na configuração do banco"
        exit 1
    }
fi

# ETAPA 4: Iniciar aplicação
log "ETAPA 4: Iniciando aplicação PROAtivo..."
echo "=========================================="
log "🎉 SISTEMA PRONTO - Iniciando serviços"
echo "API: http://localhost:8000"
echo "Streamlit: http://localhost:8501"
echo "=========================================="

# Determinar comando a executar baseado no argumento
if [ "$1" = "api" ] || [ "$1" = "" ]; then
    log "🚀 Iniciando API FastAPI..."
    exec uvicorn main:app --host 0.0.0.0 --port 8000
elif [ "$1" = "streamlit" ]; then
    log "🚀 Iniciando Streamlit..."
    cd src/frontend
    exec streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true
else
    log "🚀 Executando comando customizado: $@"
    exec "$@"
fi 