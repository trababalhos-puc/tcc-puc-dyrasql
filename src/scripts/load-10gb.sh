#!/bin/bash
# Carrega iceberg.analytics.dados ate cerca de 10 GB no MinIO.
# Executar em src/: ./scripts/load-10gb.sh

set -euo pipefail

TARGET_GB=10
BATCH_ROWS=40000
SEQ_INNER=10000
DAYS=90
START_N=0

TARGET_BYTES=$((TARGET_GB * 1024 * 1024 * 1024))

warehouse_bytes() {
    docker compose exec -T minio du -sb /data | awk '{print $1}'
}

run_sql() {
    docker compose exec -T trino-small trino \
        --server http://localhost:8080 \
        --user admin \
        --catalog iceberg \
        --schema analytics \
        --output-format TSV \
        --execute "$1"
}

echo "Alvo: ${TARGET_GB} GB no volume MinIO"
echo "Lote: ${BATCH_ROWS} linhas"
echo "Este script nao e chamado pelo docker compose. Rode so quando quiser os 10 GB."

atual=$(warehouse_bytes)
gb_atual=$(awk -v b="${atual}" 'BEGIN { printf "%.2f", b/1024/1024/1024 }')
echo "Tamanho atual: ${gb_atual} GB"

if [ "${atual}" -ge "${TARGET_BYTES}" ]; then
    echo "Ja existem cerca de ${TARGET_GB} GB no MinIO. Nada a carregar."
    exit 0
fi

if [ "${START_N}" -eq 0 ]; then
    START_N=$(run_sql "SELECT COALESCE(MAX(TRY_CAST(surrogate_key AS bigint)), 0) + 1 FROM iceberg.analytics.dados" | tr -d '[:space:]')
fi
n=${START_N}
lote=0
echo "Proximo n: ${n}"

while [ "${atual}" -lt "${TARGET_BYTES}" ]; do
    lote=$((lote + 1))
    fim=$((n + BATCH_ROWS - 1))
    echo "Lote ${lote}: linhas ${n} a ${fim} (warehouse=${atual} bytes)"

    outer_max=$((BATCH_ROWS / SEQ_INNER - 1))
    run_sql "
INSERT INTO iceberg.analytics.dados
SELECT
    CAST('T' || CAST(1 + (n % 50) AS varchar) AS varchar),
    CAST(CASE WHEN n % 10 = 0 THEN 'INATIVO' ELSE 'ATIVO' END AS varchar),
    CAST(10.0 + (n % 1000) AS double),
    CAST(date '2024-01-01' + INTERVAL '1' DAY * (n % ${DAYS}) AS timestamp(6)),
    CAST(current_timestamp AS timestamp(6)),
    CAST(current_timestamp AS timestamp(6)),
    array_join(TRANSFORM(SEQUENCE(1, 64), k -> to_hex(md5(to_utf8(CAST(n AS varchar) || '-' || CAST(k AS varchar))))), ''),
    CAST(n AS varchar)
FROM (
    SELECT ${n} + a * ${SEQ_INNER} + (b - 1) AS n
    FROM UNNEST(SEQUENCE(0, ${outer_max})) AS ta(a)
    CROSS JOIN UNNEST(SEQUENCE(1, ${SEQ_INNER})) AS tb(b)
) t
"

    n=$((fim + 1))
    atual=$(warehouse_bytes)
    gb=$(awk -v b="${atual}" 'BEGIN { printf "%.2f", b/1024/1024/1024 }')
    echo "Warehouse apos lote ${lote}: ${gb} GB"
done

linhas=$(run_sql "SELECT count(*) FROM iceberg.analytics.dados" | tr -d '[:space:]')
gb=$(awk -v b="${atual}" 'BEGIN { printf "%.2f", b/1024/1024/1024 }')
echo "Carga concluida: ${linhas} linhas, ${gb} GB no MinIO"
