#!/bin/bash
set -euo pipefail

SERVER="${TRINO_URL:-http://trino-small:8080}"
USER_NAME="${TRINO_USER:-admin}"

echo "Aguardando Trino em ${SERVER}..."
ready=0
for i in $(seq 1 90); do
    if curl -sf "${SERVER}/v1/info" >/dev/null 2>&1; then
        ready=1
        echo "Trino pronto"
        break
    fi
    sleep 2
done

if [ "$ready" -ne 1 ]; then
    echo "ERROR: Trino nao ficou pronto"
    exit 1
fi

sleep 8

echo "Criando schema e tabelas Iceberg..."
trino --server "$SERVER" --user "$USER_NAME" --file /init-iceberg.sql

COUNT=$(trino --server "$SERVER" --user "$USER_NAME" --output-format TSV --execute "SELECT count(*) FROM iceberg.analytics.dados" | tr -d '[:space:]' || echo "0")

if [ "${COUNT:-0}" = "0" ]; then
    echo "Carregando dados sinteticos..."
    trino --server "$SERVER" --user "$USER_NAME" --file /load-iceberg.sql
    COUNT=$(trino --server "$SERVER" --user "$USER_NAME" --output-format TSV --execute "SELECT count(*) FROM iceberg.analytics.dados" | tr -d '[:space:]')
    echo "Carga concluida: ${COUNT} linhas"
else
    echo "Tabela ja possui ${COUNT} linhas"
fi
