# Arquitetura

## Visão Geral

O DyraSQL implementa uma arquitetura de microsserviços containerizados que intercepta, analisa e roteia consultas SQL de forma transparente.

## Componentes

### 1. Trino Gateway Proxy

**Responsabilidade**: Interceptação de consultas

```
Cliente → Gateway Proxy → DyraSQL Core → Trino Gateway → Cluster Trino
```

**Funcionalidades**:
- Recebe consultas SQL do cliente
- Gera fingerprint único da consulta
- Consulta DyraSQL Core para decisão de roteamento
- Reescreve URL de destino
- Encaminha para Trino Gateway oficial

**Porta**: 8080

### 2. DyraSQL Core

**Responsabilidade**: Motor de decisão e análise

**Funcionalidades**:
- Recebe requisições do Gateway Proxy
- Verifica cache de decisões anteriores
- Extrai metadados via `EXPLAIN (TYPE IO)`
- Analisa complexidade da query (AST)
- Calcula score de roteamento
- Armazena decisão no cache
- Retorna cluster de destino

**Porta**: 8000

**API Endpoints**:
- `POST /api/v1/route` - Decisão de roteamento
- `GET /api/v1/metrics` - Métricas do sistema
- `GET /health` - Status do serviço

### 3. PostgreSQL

**Responsabilidade**: Cache de decisões

**Schema**:
```sql
CREATE TABLE routing_decisions (
    id SERIAL PRIMARY KEY,
    query_fingerprint VARCHAR(64) UNIQUE NOT NULL,
    target_cluster VARCHAR(50) NOT NULL,
    score FLOAT NOT NULL,
    volume_factor FLOAT,
    complexity_factor FLOAT,
    historical_factor FLOAT,
    effective_size_gb FLOAT,
    effective_rows BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);
```

**TTL**: 24 horas (configurável)

### 4. Trino Gateway

**Responsabilidade**: Balanceamento entre clusters Trino

Gateway oficial do projeto Trino que gerencia:
- Health checks dos clusters
- Roteamento efetivo
- Failover automático

**Porta**: 8081

### 5. Clusters Trino

Três clusters com capacidades distintas:

#### Small
- **Memória**: 2GB heap
- **CPU**: Recursos limitados
- **Uso**: Queries simples e pontuais
- **Porta**: 8082

#### Medium
- **Memória**: 4GB heap
- **CPU**: Recursos moderados
- **Uso**: Queries com agregações e filtros
- **Porta**: 8083

#### Large
- **Memória**: 8GB heap
- **CPU**: Recursos amplos
- **Uso**: Queries complexas com JOINs
- **Porta**: 8084

### 6. Apache Iceberg REST Catalog

**Responsabilidade**: Catálogo de metadados Iceberg

- Gerencia esquemas de tabelas
- Armazena snapshots
- Controla versionamento

**Porta**: 8181

### 7. MinIO

**Responsabilidade**: Armazenamento S3-compatível

- Armazena dados das tabelas Iceberg
- Gerencia arquivos Parquet

**Porta**: 9000 (API), 9001 (Console)

## Fluxo de Dados

### Consulta Inicial (Cache Miss)

```mermaid
sequenceDiagram
    participant C as Cliente
    participant GP as Gateway Proxy
    participant DC as DyraSQL Core
    participant PG as PostgreSQL
    participant T as Trino Cluster
    
    C->>GP: SELECT ...
    GP->>DC: POST /route {query, fingerprint}
    DC->>PG: Busca cache
    PG-->>DC: Cache miss
    DC->>T: EXPLAIN (TYPE IO)
    T-->>DC: Metadados
    DC->>DC: Calcula score
    DC->>PG: Armazena decisão
    DC-->>GP: {cluster: "medium"}
    GP->>T: Executa query no cluster
    T-->>C: Resultado
```

### Consulta com Cache Hit

```mermaid
sequenceDiagram
    participant C as Cliente
    participant GP as Gateway Proxy
    participant DC as DyraSQL Core
    participant PG as PostgreSQL
    participant T as Trino Cluster
    
    C->>GP: SELECT ...
    GP->>DC: POST /route {query, fingerprint}
    DC->>PG: Busca cache
    PG-->>DC: Cache hit: medium
    DC-->>GP: {cluster: "medium"}
    GP->>T: Executa query no cluster
    T-->>C: Resultado
```

## Algoritmo de Decisão

### 1. Fator de Volume ($f_v$)

Normaliza tamanho e número de linhas:

$$T_n = \frac{T_e}{T_{max}}$$

$$R_n = \frac{R_e}{R_{max}}$$

$$f_v = (T_n \times 0.6 + R_n \times 0.4) \times (1 - F_o)$$

Onde:
- $T_e$: Tamanho efetivo (GB)
- $T_{max}$: Tamanho máximo esperado (10 GB)
- $R_e$: Linhas efetivas
- $R_{max}$: Linhas máximas esperadas (10M)
- $F_o$: Fator de otimização (0-1)

### 2. Fator de Complexidade ($f_c$)

Analisa AST da query:

```python
score = 0
score += count(JOINs) * 0.35
score += count(SUBQUERIEs) * 0.25
score += count(AGGREGATIONs) * 0.15
score += count(WINDOW_FUNCs) * 0.15
score += count(DISTINCT) * 0.10
```

### 3. Fator Histórico ($f_h$)

Baseado em decisões anteriores para queries similares:

$$f_h = \text{avg}(\text{scores históricos})$$

### Score Final

$$S = w_1 \cdot f_v + w_2 \cdot f_c + w_3 \cdot f_h$$

Pesos padrão: $w_1 = 0.5$, $w_2 = 0.3$, $w_3 = 0.2$

### Decisão

- $S < 0.33$: **Small**
- $0.33 \leq S < 0.66$: **Medium**
- $S \geq 0.66$: **Large**

## Configuração

### Variáveis de Ambiente

#### DyraSQL Core

```bash
DATABASE_URL=postgresql://dyrasql:senha@postgres:5432/dyrasql
TRINO_SMALL_URL=http://trino-small:8082
TRINO_MEDIUM_URL=http://trino-medium:8083
TRINO_LARGE_URL=http://trino-large:8084
TRINO_USER=admin
CACHE_TTL_HOURS=24
MAX_SIZE_GB=10.0
MAX_ROWS=10000000
```

#### Trino Clusters

```properties
# config.properties
coordinator=true
node-scheduler.include-coordinator=true
http-server.http.port=8082
discovery.uri=http://localhost:8082
query.max-memory=2GB
query.max-memory-per-node=512MB
```

## Limitações Conhecidas

1. **Cache Global**: Não há invalidação automática quando dados mudam
2. **Estimativas**: Metadados do Iceberg podem não refletir dados reais
3. **Complexidade**: Análise AST não captura todas as nuances
4. **Single Point**: DyraSQL Core é ponto único de falha
5. **Latência**: Overhead de análise em cache miss

## Melhorias Futuras

- [ ] Cache distribuído (Redis)
- [ ] Invalidação inteligente de cache
- [ ] Machine learning para ajuste de pesos
- [ ] Alta disponibilidade do Core
- [ ] Métricas em tempo real (Prometheus)
- [ ] Dashboard de monitoramento (Grafana)
- [ ] Suporte a múltiplos catálogos Iceberg
- [ ] Roteamento baseado em custo financeiro
