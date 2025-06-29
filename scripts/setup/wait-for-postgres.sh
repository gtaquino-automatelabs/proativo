#!/bin/bash
# wait-for-postgres.sh
# Script para aguardar PostgreSQL estar pronto para conexões

set -e

host="$1"
shift
cmd="$@"

until pg_isready -h "$host" -p 5432 -U "${POSTGRES_USER:-proativo_user}"; do
  echo "⏳ Aguardando PostgreSQL estar pronto em $host..."
  sleep 2
done

echo "✅ PostgreSQL está pronto!"
exec $cmd 