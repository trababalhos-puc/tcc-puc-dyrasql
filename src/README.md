# DyraSQL - ambiente local

Stack de experimentacao do DyraSQL em Docker Compose, com tabelas Apache Iceberg locais, tres clusters Trino de capacidades distintas e cache de decisoes no PostgreSQL.

## Componentes

- MinIO: armazenamento de objetos do warehouse Iceberg
- Catalogo Iceberg REST: metadados das tabelas
- PostgreSQL: persistencia do Trino Gateway e cache/historico do DyraSQL
- Trino small, medium e large: execucao das consultas
- DyraSQL Core: analise via EXPLAIN (TYPE IO) e decisao de roteamento
- Trino Gateway e proxy: interceptacao e encaminhamento

## Subida do ambiente

Na primeira execucao, volumes antigos da stack AWS devem ser removidos.

```
cd experimento
docker compose down -v
docker compose up -d
```

Aguarde o servico `iceberg-init` concluir a criacao do schema `iceberg.analytics` e a carga da tabela sintetica.

## Consulta de referencia

O arquivo `query.sql` consulta `iceberg.analytics.dados` e `iceberg.analytics.tenant_info`, particionadas por data.

Faixas de score:

- Score menor que 0,3: cluster small
- Score entre 0,3 e 0,7: cluster medium
- Score maior que 0,7: cluster large

## Portas

- Proxy: 8080
- DyraSQL Core: 5001
- Trino small: 8081
- Trino medium: 8082
- Trino large: 8083
- Trino Gateway: 8085
- Catalogo Iceberg REST: 8181
- MinIO API: 9000
- MinIO console: 9001

## Limpeza de cache

```
./scripts/limpar-cache.sh
```

## Observacao

Credenciais do MinIO e do PostgreSQL destinam-se apenas ao ambiente local. Nao reutilizar em producao.
