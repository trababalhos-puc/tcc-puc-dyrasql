# Prints da apresentação Beamer

Os cinco PNGs desta pasta entram nos slides de demonstração. Substitua cada arquivo pelo print real, mantendo o mesmo nome. Depois, compile a apresentação a partir de `latex/`:

```bash
docker-compose run --rm latex make beamer
```

Ordem sugerida: ambiente, dados, explain, roteamento, cache. Assim o Docker sobe uma vez e os dados Iceberg já existem antes dos prints de SQL.

## Pré-requisitos

- Docker e Docker Compose 2
- Portas livres: 8080, 8081 a 8085, 9000, 9001, 5001
- Cerca de 8 GB de RAM

Todos os comandos abaixo são executados no diretório `src/` do repositório, salvo indicação em contrário.

## 1. ambiente.png (stack Docker)

**O que o slide mostra.** Containers do laboratório (proxy, Core, três Trinos, PostgreSQL, MinIO, catálogo Iceberg).

**Quando tirar.** Depois que o `docker compose up -d` terminar e `docker compose ps` listar os serviços em `healthy` ou `running`. Não tire no meio da subida (status `starting` ou `health: starting`). Aguarde 2 a 3 minutos.

**Comandos.**

```bash
cd src
docker compose up -d
docker compose ps
```

**Como capturar.** Janela do terminal com a tabela do `ps` visível, ou o Docker Desktop com os mesmos containers. Recorte só a lista de serviços, sem outras abas.

**Arquivo.** `latex/beamer/prints/ambiente.png`

## 2. dados.png (tabela Iceberg)

**O que o slide mostra.** Consulta simples sobre `iceberg.analytics.dados`, comprovando que o *dataset* sintético está carregado.

**Quando tirar.** Depois do print do ambiente. O serviço `init-iceberg` já cria o *schema* e carrega as linhas na primeira subida. Confirme que a tabela não está vazia antes de capturar.

**Comandos.** Conecte direto no cluster small (não use o proxy). O objetivo aqui é o dado, não o roteamento.

```bash
cd src
docker compose exec trino-small trino \
  --server http://localhost:8080 \
  --user admin \
  --catalog iceberg \
  --schema analytics
```

No CLI do Trino (ou na IDE, arquivo `02-dados.sql`, conexão porta 8081):

```sql
SELECT COUNT(*) AS total_registros FROM iceberg.analytics.dados;
SELECT tenant_id, status, valor, date FROM iceberg.analytics.dados LIMIT 10;
```

**Como capturar.** Tela do CLI com o `COUNT(*)` (número maior que zero) e algumas linhas do `SELECT`. Se o count for 0, rode de novo `docker compose up -d` e espere o `init-iceberg` concluir, ou execute `src/scripts/init-iceberg.sh` no fluxo do compose.

**Arquivo.** `latex/beamer/prints/dados.png`

## 3. explain.png (EXPLAIN TYPE IO)

**O que o slide mostra.** Metadados de I/O usados no Fator volume (`outputSizeInBytes` e `outputRowCount`).

**Quando tirar.** Com a tabela já populada (print 2). Use a mesma sessão do Trino small, ou o JSON gravado em `src/explains/` se `SAVE_EXPLAINS=true` no Core.

**Opção A (CLI, mais visual para o slide).** Ainda no Trino small, arquivo `03-explain.sql` (porta 8081):

```sql
EXPLAIN (TYPE IO, FORMAT JSON)
SELECT t.tenant_id, t.categoria, COUNT(d.document) AS total,
       SUM(length(d.document)) AS bytes_documento, AVG(d.valor) AS media
FROM iceberg.analytics.dados d
JOIN iceberg.analytics.tenant_info t ON d.tenant_id = t.tenant_id
WHERE d.status = 'ATIVO'
GROUP BY t.tenant_id, t.categoria
HAVING COUNT(*) > 1000;
```

No JSON, destaque `outputSizeInBytes` e `outputRowCount`.

**Opção B (arquivo salvo pelo Core).** Depois de pelo menos uma consulta roteada pelo proxy:

```bash
ls -lt src/explains/
```

Abra o JSON mais recente (por exemplo no editor) e destaque os mesmos campos.

**Como capturar.** JSON visível, com os dois campos destacados (seleção, marca-texto ou recorte próximo dessas chaves). Evite capturar só o cabeçalho `EXPLAIN` sem o JSON.

**Arquivo.** `latex/beamer/prints/explain.png`

## 4. roteamento.png (decisão small / medium / large)

**O que o slide mostra.** O Core escolhendo cluster conforme o Score, com consultas de `src/query.sql`.

**Quando tirar.** Ambiente saudável, dados carregados, e o monitor de logs já aberto **antes** de disparar as queries. O melhor instante é quando o log mostra `ROUTING DECISION` e o cluster (`small`, `medium` ou `large`) na mesma tela em que a query rodou.

**Terminal 1 (monitor).**

```bash
cd src
./scripts/monitor-routing.sh
```

**Terminal 2 (consultas pelo proxy, não pelo Trino direto).**

```bash
cd src
docker compose exec trino-small trino \
  --server http://trino-gateway-proxy:8080 \
  --user admin \
  --catalog iceberg \
  --schema analytics
```

No CLI ou na IDE (conexão proxy, porta 8080), rode um arquivo por vez:

- `04-roteamento-small.sql` (esperado: cluster small)
- `04-roteamento-medium.sql` (esperado: cluster medium)
- `04-roteamento-large.sql` (esperado: cluster large)

**Como capturar.** Duas janelas lado a lado (CLI + `monitor-routing.sh`) ou só o monitor se `ROUTING`, Score e cluster estiverem nítidos. Três decisões diferentes (small, medium, large) no mesmo recorte deixam o slide mais claro.

Se o monitor filtrar demais, use o log bruto:

```bash
docker compose logs -f dyrasql-core
```

Procure a linha `ROUTING DECISION: Query will be executed on cluster`.

**Arquivo.** `latex/beamer/prints/roteamento.png`

## 5. cache.png (miss e depois hit)

**O que o slide mostra.** Primeira execução analisa a query (`NEW ANALYSIS`); a segunda reusa a decisão (`CACHE`).

**Quando tirar.** Depois do print de roteamento. Limpe o cache **antes** da primeira execução da query escolhida. Capture no momento em que as duas linhas aparecem no log: a primeira com `NEW ANALYSIS` e a segunda com `CACHE: Using cached decision`.

**Limpar o cache.**

```bash
cd src
./scripts/limpar-cache.sh
```

**Terminal 1.**

```bash
docker compose logs -f dyrasql-core
```

**Terminal 2.** Mesmo CLI pelo proxy do print 4. Rode **duas vezes** o arquivo `05-cache.sql`, sem alterar o texto (o *fingerprint* é SHA-256 da consulta):

Na primeira vez o log deve trazer `NEW ANALYSIS: Query analyzed from scratch (not in cache)`. Na segunda, `CACHE: Using cached decision for fingerprint`.

**Como capturar.** Recorte com as duas linhas visíveis (miss e hit). Se só aparecer hit, o cache não foi limpo. Se só aparecer miss, a segunda query diferiu da primeira ou o TTL não chegou a gravar.

**Arquivo.** `latex/beamer/prints/cache.png`

## Checklist rápido

1. `docker compose up -d` e `docker compose ps` saudável → `ambiente.png`
2. Trino small direto, `COUNT(*)` e amostra de linhas → `dados.png`
3. `EXPLAIN (TYPE IO, FORMAT JSON)` ou JSON em `src/explains/` → `explain.png`
4. Proxy + `monitor-routing.sh` + queries de `src/query.sql` → `roteamento.png`
5. `limpar-cache.sh`, mesma query duas vezes, log Core miss e hit → `cache.png`
6. `docker-compose run --rm latex make beamer` em `latex/`

## Conexão pela IDE (DataGrip, DataSpell, DBeaver, Cursor)

Com o `docker compose up -d` saudável, crie duas fontes JDBC. Não há senha. SSL desligado. Usuário `admin`. Catálogo `iceberg`, schema `analytics`.

### Proxy (roteamento e cache)

Use esta conexão para os prints `roteamento.png` e `cache.png`. A IDE fala com o host na porta 8080, que é o `trino-gateway-proxy`.

- Host: `localhost`
- Porta: `8080`
- User: `admin`
- Password: vazio
- Catalog / Database: `iceberg`
- Schema: `analytics`
- JDBC URL: `jdbc:trino://localhost:8080/iceberg/analytics`
- SSL: desligado

No DataGrip ou DataSpell: Data Source, Trino, preencha host, porta, user, catalog e schema, teste a conexão. No DBeaver: Nova conexão, Presto/Trino, Database `iceberg/analytics`. Deixe a senha **vazia** (se o campo mostrar `<hidden>`, apague). Aba SSH/SSL: SSL desligado. No Cursor, use o cliente de banco (Database / SQLTools) com o mesmo JDBC.

Se o Test Connection falhar em `/v1/statement/queued/...` com 404, o proxy precisa do mapeamento query-cluster. Suba de novo o proxy (`docker compose up -d --build trino-gateway-proxy`) e teste outra vez. Alternativa imediata: porta `5001` (DyraSQL Core) ou `8081` (Trino small, sem roteamento).

### Cluster small direto (dados e EXPLAIN)

Use esta conexão para `dados.png` e `explain.png`. A porta 8081 é o `trino-small`, sem passar pelo DyraSQL.

- Host: `localhost`
- Porta: `8081`
- JDBC URL: `jdbc:trino://localhost:8081/iceberg/analytics`

Os demais campos são iguais (user `admin`, sem senha, catalog `iceberg`, schema `analytics`).

Opcional: medium em `8082` e large em `8083` se quiser inspecionar um cluster específico.

### O que executar na IDE

Arquivos SQL desta pasta. Rode um statement por vez. Deixe `./scripts/monitor-routing.sh` ou `docker compose logs -f dyrasql-core` aberto em outro terminal.

- `02-dados.sql` e `03-explain.sql`: conexão **small** (`localhost:8081`)
- `04-roteamento-small.sql`, `04-roteamento-medium.sql`, `04-roteamento-large.sql` e `05-cache.sql`: conexão **proxy** (`localhost:8080`)

No cache, limpe com `src/scripts/limpar-cache.sh` e execute `05-cache.sql` duas vezes.

O `SELECT 1` de keep-alive da IDE não entra no roteamento. `SHOW` e `DESCRIBE` vão sempre para o small.

## Observações

- Consultas de metadados (`SHOW`, `DESCRIBE`) vão sempre para o cluster small e não ilustram bem o Score.
- O CLI em `http://localhost:8080` **dentro** do container `trino-small` fala com o próprio cluster. Roteamento e cache exigem `http://trino-gateway-proxy:8080`.
- Do host, o proxy também responde em `http://localhost:8080` (útil para `curl` na API do Core em `http://localhost:5001`).
- Resolução sugerida: recorte largo, texto legível em projeção, fundo do terminal com contraste.
