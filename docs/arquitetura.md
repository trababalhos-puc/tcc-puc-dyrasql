# Arquitetura Técnica - DyraSQL

## Visão Geral

O DyraSQL é um framework de roteamento dinâmico de consultas SQL que utiliza análise de metadados Apache Iceberg para direcionar automaticamente consultas para clusters Trino de capacidades distintas. O sistema foi desenvolvido como prova de conceito para validar a viabilidade de roteamento baseado em análise pré-execução.

## Componentes Principais

### 1. DyraSQL Core

**Tecnologia:** Python 3.11, FastAPI, uvicorn  
**Porta:** 5000 (interna), 5001 (exposta)  
**Responsabilidades:**
- Motor de decisão de roteamento
- Execução de EXPLAIN (TYPE IO) no Trino
- Cálculo de scores baseado em metadados
- Gerenciamento de cache e histórico
- API REST para integração

**Módulos:**

#### app.py
API principal com os endpoints:
- `POST /api/v1/route`: Analisa query e retorna decisão
- `POST /api/v1/metrics`: Salva métricas pós-execução
- `GET /health`: Health check
- `POST /v1/statement`: Proxy direto para execução
- `GET /v1/info`: Informações do Trino

#### decision_engine.py
Implementa o algoritmo de pontuação descrito no artigo:

```python
S = w1 * fv + w2 * fc + w3 * fh
```

Onde:
- `S`: Score final (0-1)
- `fv`: Fator volume (baseado em tamanho e número de linhas)
- `fc`: Fator complexidade (JOINs, agregações, subconsultas)
- `fh`: Fator histórico (execuções anteriores)
- `w1, w2, w3`: Pesos configuráveis (soma = 1.0)

**Roteamento:**
- `score < 0.3` → cluster small
- `0.3 <= score <= 0.7` → cluster medium
- `score > 0.7` → cluster large

#### query_analyzer.py
Responsável por:
- Geração de fingerprints (SHA-256 de query normalizada)
- Execução de EXPLAIN (TYPE IO) no Trino
- Parsing do JSON retornado pelo EXPLAIN
- Análise de complexidade estrutural via sqlglot
- Extração de metadados (tamanho, linhas, CPU cost)
- Salvamento de EXPLAIN para análise posterior

**Análise de Complexidade:**
Utiliza sqlglot para parsear a AST da query e contar:
- Número de JOINs
- Número de agregações (apenas no SELECT principal)
- Número de subconsultas
- Filtros particionados vs. não-particionados

#### history_manager.py
Gerencia cache e histórico no PostgreSQL:
- Cache de decisões com TTL de 24h
- Armazenamento de métricas pós-execução
- Cálculo do fator histórico baseado em sucesso/falha

**Tabela `routing_decisions`:**
```sql
CREATE TABLE routing_decisions (
    fingerprint VARCHAR(64) PRIMARY KEY,
    cluster VARCHAR(32) NOT NULL,
    score DOUBLE PRECISION NOT NULL,
    factors JSONB NOT NULL,
    success BOOLEAN,
    execution_time DOUBLE PRECISION,
    cost DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL
);
```

#### metadata_connector.py
Stub para integração futura com catálogo Iceberg REST.  
Atualmente, todos os metadados vêm do EXPLAIN (TYPE IO).

### 2. Trino Gateway Proxy

**Tecnologia:** Python 3.11, FastAPI, httpx  
**Porta:** 8080  
**Responsabilidades:**
- Interceptação de consultas SQL
- Integração com DyraSQL Core para decisão
- Reescrita de URLs nas respostas
- Proxy transparente para nextUri

**Fluxo:**
1. Cliente → Proxy (POST /v1/statement)
2. Proxy → DyraSQL Core (POST /api/v1/route)
3. DyraSQL Core retorna cluster recomendado
4. Proxy → Cluster Trino selecionado
5. Resposta → Cliente (com URLs reescritas)

**Otimizações:**
- Keep-alive queries vão direto para small
- Queries de metadados vão direto para small
- Cache de fingerprints para reuso

### 3. Trino Gateway (Oficial)

**Tecnologia:** Java, Maven  
**Porta:** 8080 (interna), 8085 (exposta)  
**Responsabilidades:**
- Balanceamento de carga entre backends
- Health check dos clusters
- Interface administrativa
- Armazenamento de histórico de queries

**Configuração:**
```yaml
serverConfig:
  node.environment: production
  http-server.http.port: 8080

dataStore:
  jdbcUrl: jdbc:postgresql://gateway-db:5432/trino_gateway
  driver: org.postgresql.Driver
  
clusterStatsConfiguration:
  monitorType: INFO_API
```

**Backends:**
- small: http://trino-small:8080
- medium: http://trino-medium:8080
- large: http://trino-large:8080

### 4. Clusters Trino

**Tecnologia:** Trino (trinodb/trino:latest)  
**Configuração:** 3 clusters com capacidades distintas

#### Cluster Small
**Porta:** 8081  
**Capacidade:** query.max-memory=1GB  
**Uso:** Queries simples, metadados, keep-alive

#### Cluster Medium
**Porta:** 8082  
**Capacidade:** query.max-memory=2GB  
**Uso:** Queries intermediárias com JOINs e agregações

#### Cluster Large
**Porta:** 8083  
**Capacidade:** query.max-memory=4GB  
**Uso:** Queries complexas com subconsultas e window functions

**Catálogo Iceberg (compartilhado):**
```properties
connector.name=iceberg
iceberg.catalog.type=rest
iceberg.rest-catalog.uri=http://iceberg-rest:8181
iceberg.file-format=PARQUET
fs.native-s3.enabled=true
s3.endpoint=http://minio:9000
s3.path-style-access=true
```

### 5. PostgreSQL

**Tecnologia:** PostgreSQL 16 Alpine  
**Databases:**
- `trino_gateway`: usado pelo Trino Gateway oficial
- `dyrasql`: cache e histórico do DyraSQL Core

**Inicialização:**
- Script `init-dyrasql.sh` cria user, database e table
- Índice em `expires_at` para queries rápidas

### 6. MinIO

**Tecnologia:** MinIO (S3-compatible)  
**Portas:** 9000 (API), 9001 (Console)  
**Bucket:** warehouse  
**Uso:** Armazenamento das tabelas Iceberg

**Credentials:**
- Access Key: dyrasql
- Secret Key: dyrasql1

### 7. Iceberg REST Catalog

**Tecnologia:** tabulario/iceberg-rest:1.6.0  
**Porta:** 8181  
**Responsabilidades:**
- Catálogo de metadados Iceberg
- Integração com MinIO
- Compartilhado por todos os clusters Trino

## Fluxo de Dados

### Primeira Execução (Cache Miss)

```
┌─────────┐
│ Cliente │
└────┬────┘
     │ 1. POST /v1/statement (SQL query)
     │
     ▼
┌──────────────────────┐
│ Trino Gateway Proxy  │
└──────────┬───────────┘
           │ 2. POST /api/v1/route
           │
           ▼
┌─────────────────────────────┐
│ DyraSQL Core                │
│ ┌─────────────────────────┐ │
│ │ Query Analyzer          │ │
│ │ - Generate fingerprint  │ │
│ │ - Check cache (MISS)    │ │
│ │ - Execute EXPLAIN       │ │
│ │ - Parse metadata        │ │
│ │ - Analyze complexity    │ │
│ └────────┬────────────────┘ │
│          │                  │
│          ▼                  │
│ ┌─────────────────────────┐ │
│ │ Decision Engine         │ │
│ │ - Calculate fv          │ │
│ │ - Calculate fc          │ │
│ │ - Get fh from history   │ │
│ │ - Calculate score       │ │
│ │ - Select cluster        │ │
│ └────────┬────────────────┘ │
│          │                  │
│          ▼                  │
│ ┌─────────────────────────┐ │
│ │ History Manager         │ │
│ │ - Save decision         │ │
│ │ - Set TTL (24h)         │ │
│ └─────────────────────────┘ │
└──────────┬──────────────────┘
           │ 3. Return {cluster, score, factors}
           │
           ▼
┌──────────────────────┐
│ Trino Gateway Proxy  │
└──────────┬───────────┘
           │ 4. POST to selected cluster
           │
           ▼
┌──────────────────────┐
│ Trino Cluster        │
│ (small/medium/large) │
└──────────┬───────────┘
           │ 5. Execute query on Iceberg
           │
           ▼
┌──────────────────────┐
│ Iceberg REST + MinIO │
└──────────┬───────────┘
           │ 6. Query result
           │
           ▼
┌─────────┐
│ Cliente │
└─────────┘
```

### Execução com Cache Hit

```
┌─────────┐
│ Cliente │
└────┬────┘
     │ 1. POST /v1/statement (SQL query)
     │
     ▼
┌──────────────────────┐
│ Trino Gateway Proxy  │
└──────────┬───────────┘
           │ 2. POST /api/v1/route
           │
           ▼
┌─────────────────────────────┐
│ DyraSQL Core                │
│ ┌─────────────────────────┐ │
│ │ Query Analyzer          │ │
│ │ - Generate fingerprint  │ │
│ │ - Check cache (HIT!)    │ │
│ │ - Return cached result  │ │
│ └─────────────────────────┘ │
└──────────┬──────────────────┘
           │ 3. Return {cluster, score} (cached)
           │
           ▼
     (continua como acima)
```

## Algoritmo de Decisão Detalhado

### Fator Volume (fv)

Calcula a normalização logarítmica do tamanho e número de linhas:

```python
# Valores obtidos do EXPLAIN (TYPE IO)
size_gb = outputSizeInBytes / (1024^3)
rows = outputRowCount

# Normalização logarítmica
norm_size = log(size_gb) / log(max_size_gb)
norm_rows = log(rows) / log(max_rows)

# Combinação com pesos e fator de otimização
fv = (norm_size * 0.7 + norm_rows * 0.3) * (1 - optimization_factor)

# Limites: 0 <= fv <= 1
```

**Parâmetros padrão:**
- `max_size_gb = 1000`
- `max_rows = 1e9`
- `optimization_factor = 0.1`

### Fator Complexidade (fc)

Analisa a estrutura da query via AST (sqlglot):

```python
# Contagem de elementos estruturais
joins = count(JOIN nodes in AST)
aggs = count(AggFunc in SELECT projections)
subq = count(Subquery nodes)
filt_p = count(partitioned column filters in WHERE)
filt_np = count(non-partitioned filters in WHERE)

# Cálculo com coeficientes
fc = (
    joins * 0.2 +
    aggs * 0.15 +
    subq * 0.25 +
    filt_p * 0.02 +
    filt_np * 0.1
) / complexity_limit

# Limites: 0 <= fc <= 1
```

**Coeficientes:**
- JOIN: 0.2 (alto impacto)
- Subconsulta: 0.25 (maior impacto)
- Agregação: 0.15
- Filtro não-particionado: 0.1
- Filtro particionado: 0.02 (baixo impacto)

### Fator Histórico (fh)

Baseado em execuções anteriores:

```python
# Consulta histórico por fingerprint
prev_exec = SELECT score, success FROM routing_decisions
            WHERE fingerprint = ? AND expires_at > NOW()

if not prev_exec:
    fh = 0.5  # Neutro
elif prev_exec.success:
    fh = prev_exec.score  # Repetir sucesso
else:
    fh = 1.0 - prev_exec.score  # Inverter falha
```

### Score Final

```python
S = w1 * fv + w2 * fc + w3 * fh

if S < 0.3:
    cluster = 'small'
elif S <= 0.7:
    cluster = 'medium'
else:
    cluster = 'large'
```

**Pesos padrão:**
- `w1 = 0.5` (volume - maior peso)
- `w2 = 0.3` (complexidade)
- `w3 = 0.2` (histórico)

## EXPLAIN (TYPE IO)

O comando `EXPLAIN (TYPE IO)` do Trino retorna JSON com:

```json
{
  "inputTableColumnInfos": [{
    "table": {
      "catalog": "iceberg",
      "schemaTable": {
        "schema": "analytics",
        "table": "dados"
      }
    },
    "constraint": {
      "columnConstraints": [{
        "columnName": "date",
        "type": "timestamp(6)",
        "domain": {
          "ranges": [{"low": {...}, "high": {...}}]
        }
      }]
    },
    "estimate": {
      "outputRowCount": 2500000.0,
      "outputSizeInBytes": 1342177280.0,
      "cpuCost": 1342177280.0
    }
  }]
}
```

**Informações extraídas:**
- `outputSizeInBytes`: Tamanho estimado pós-filtros
- `outputRowCount`: Número de linhas estimado
- `cpuCost`: Custo de CPU estimado
- `columnConstraints`: Filtros aplicados

## Cache e TTL

**Estratégia:**
- Fingerprint único (SHA-256) de query normalizada
- TTL de 24 horas
- Expira automaticamente via campo `expires_at`
- Índice em `expires_at` para performance

**Normalização de Query:**
```python
# Remove espaços extras
normalized = re.sub(r'\s+', ' ', query.lower())

# Substitui literais por placeholder
normalized = re.sub(r"'[^']*'", "'?'", normalized)
normalized = re.sub(r'\d+', '?', normalized)

# Gera hash
fingerprint = sha256(normalized).hexdigest()
```

## Monitoramento e Debugging

### Logs Estruturados

O DyraSQL Core emite logs estruturados:
```
INFO - ROUTING DECISION: Query will be executed on cluster 'medium'
INFO - NEW ANALYSIS: Query analyzed from scratch (not in cache)
INFO -   Calculated score: 0.440
INFO -   Factors: volume=0.270, complexity=0.690, historical=0.500
INFO - CACHE: Using cached decision for fingerprint: abc123...
```

### EXPLAIN Salvos

Quando `SAVE_EXPLAINS=true`:
- Cada EXPLAIN é salvo em `/app/explains/`
- Formato: `{timestamp}_{fingerprint}.json`
- Inclui query original, normalizada, metadata extraída

### Scripts de Monitoramento

**monitor-routing.sh:**
```bash
docker compose logs -f dyrasql-core | grep -E "(ROUTING|Decision|cluster)"
```

**limpar-cache.sh:**
```bash
docker compose exec dyrasql-core python3 -c "from history_manager import HistoryManager; HistoryManager().clear_cache()"
```

## Limitações Conhecidas

1. **Volume de dados:** Dataset sintético limitado (< 10 GB)
2. **Histórico:** Fator histórico depende de execuções prévias
3. **EXPLAIN latency:** EXPLAIN pode ser lento em queries complexas
4. **Metadados desatualizados:** Iceberg stats podem estar desatualizados
5. **Elasticidade:** Ambiente local não simula escala de nuvem
6. **Fallback:** Sem estratégia formal para falha do EXPLAIN

## Trabalhos Futuros

1. **Ajuste automático de pesos:** ML para calibrar w1, w2, w3
2. **Elasticidade:** Integração com Kubernetes para scaling
3. **Métricas em tempo real:** Prometheus + Grafana
4. **Otimização de custos:** Integração com billing APIs
5. **Fallback robusto:** Cluster padrão quando EXPLAIN falha
6. **A/B testing:** Comparação de algoritmos em produção

## Referências Técnicas

- [Trino Documentation](https://trino.io/docs/current/)
- [Apache Iceberg Table Spec](https://iceberg.apache.org/spec/)
- [Trino Gateway](https://github.com/trinodb/trino-gateway)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [sqlglot AST Parser](https://github.com/tobymao/sqlglot)

---

**Desenvolvido por:** Aristides Henrique Gonçalves da Cruz  
**Orientador:** Prof. Gustavo Luís Soares  
**Instituição:** PUC Minas - ICEI  
**Ano:** 2026
