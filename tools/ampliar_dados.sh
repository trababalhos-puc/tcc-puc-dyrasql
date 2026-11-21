#!/bin/sh
# Amplia iceberg.analytics.dados de 180.000 para 46.080.000 linhas por 8 duplicacoes.
# Cada duplicacao gera novo surrogate_key (uuid) e multiplica o valor por um fator
# aleatorio em [0,5; 1,5). A funcao random() do Trino nao aceita semente, portanto os
# valores numericos variam entre reproducoes; a contagem de linhas, a distribuicao entre
# as 90 particoes diarias, os tenants e os status sao preservados.
# Executar na raiz do repositorio, com a stack no ar e o cluster large ativo.
set -e
COMPOSE="docker compose -f src/docker-compose.yml"
for i in 1 2 3 4 5 6 7 8; do
  $COMPOSE exec -T trino-large trino --user admin --execute \
    "INSERT INTO iceberg.analytics.dados
     SELECT tenant_id, status, valor * (0.5 + random()), date, created_at, updated_at,
            document, cast(uuid() AS varchar)
     FROM iceberg.analytics.dados"
  echo "duplicacao $i concluida"
done
$COMPOSE exec -T trino-large trino --user admin --execute \
  "SELECT count(*) FROM iceberg.analytics.dados"
