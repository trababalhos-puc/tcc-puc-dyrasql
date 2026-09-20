# Guia de Uso

## Acesso ao Sistema

Após inicialização completa (`docker-compose up -d`), os seguintes serviços estarão disponíveis:

| Serviço | URL | Descrição |
|---------|-----|-----------|
| Gateway Proxy | http://localhost:8080 | Ponto de entrada principal |
| DyraSQL Core | http://localhost:8000 | API de roteamento |
| Trino Small | http://localhost:8082 | Cluster pequeno |
| Trino Medium | http://localhost:8083 | Cluster médio |
| Trino Large | http://localhost:8084 | Cluster grande |
| Trino Gateway | http://localhost:8081 | Gateway oficial |
| MinIO Console | http://localhost:9001 | Interface S3 |

## Executando Consultas

### Via Trino CLI (Recomendado)

#### 1. Conectar ao Gateway Proxy

```bash
docker run --rm -it --network host trinodb/trino:latest trino \
  --server http://localhost:8080 \
  --catalog iceberg \
  --schema db
```

#### 2. Executar Queries

```sql
-- Query simples (→ Small)
SELECT * FROM dados WHERE id = 123;

-- Query com agregação (→ Medium)
SELECT categoria, COUNT(*) as total
FROM dados
GROUP BY categoria;

-- Query complexa (→ Large)
SELECT 
    d.categoria,
    AVG(d.valor) as media,
    COUNT(DISTINCT d.tenant_id) as tenants
FROM dados d
JOIN tenant_info t ON d.tenant_id = t.tenant_id
GROUP BY d.categoria
HAVING COUNT(*) > 1000;
```

### Via Python

```python
import trino

# Conexão via Gateway Proxy
conn = trino.dbapi.connect(
    host='localhost',
    port=8080,
    user='admin',
    catalog='iceberg',
    schema='db'
)

cursor = conn.cursor()

# Query simples
cursor.execute("SELECT COUNT(*) FROM dados")
result = cursor.fetchone()
print(f"Total de registros: {result[0]}")

# Query com parâmetros
cursor.execute("""
    SELECT categoria, COUNT(*) as total
    FROM dados
    WHERE data >= DATE '2026-01-01'
    GROUP BY categoria
""")

for row in cursor.fetchall():
    print(f"{row[0]}: {row[1]}")

cursor.close()
conn.close()
```

### Via DBeaver / DataGrip

1. **Criar conexão Trino**:
   - Host: `localhost`
   - Port: `8080`
   - User: `admin`
   - Catalog: `iceberg`
   - Schema: `db`

2. **Testar conexão**

3. **Executar queries** normalmente

## Monitoramento de Decisões

### Logs do DyraSQL Core

```bash
docker-compose logs -f dyrasql-core
```

Você verá logs como:

```
INFO: Cache miss para query: SELECT * FROM dados WHERE id = 123
INFO: Executando EXPLAIN (TYPE IO)...
INFO: Metadados extraídos: size=0.05GB, rows=1000, opt_factor=0.95
INFO: Calculando score: fv=0.05, fc=0.10, fh=0.00
INFO: Score final: 0.08 → Roteando para SMALL
INFO: Decisão armazenada no cache (TTL: 24h)
```

### Script de Monitoramento

```bash
cd src/scripts
./monitor-routing.sh
```

Output:
```
🔍 Monitorando decisões de roteamento...
───────────────────────────────────────────────────
2026-09-13 11:30:15 | SELECT * FROM dados WHERE id = 123
  → Cluster: SMALL | Score: 0.08 | Cache: MISS

2026-09-13 11:30:20 | SELECT categoria, COUNT(*) FROM dados GROUP BY categoria
  → Cluster: MEDIUM | Score: 0.45 | Cache: MISS

2026-09-13 11:30:25 | SELECT * FROM dados WHERE id = 456
  → Cluster: SMALL | Score: 0.08 | Cache: HIT
───────────────────────────────────────────────────
Pressione Ctrl+C para parar
```

### Consultar Cache PostgreSQL

```bash
docker-compose exec postgres psql -U dyrasql -d dyrasql
```

```sql
-- Ver todas as decisões
SELECT 
    query_fingerprint,
    target_cluster,
    score,
    effective_size_gb,
    effective_rows,
    created_at
FROM routing_decisions
ORDER BY created_at DESC
LIMIT 10;

-- Estatísticas por cluster
SELECT 
    target_cluster,
    COUNT(*) as total_queries,
    AVG(score) as avg_score,
    AVG(effective_size_gb) as avg_size_gb
FROM routing_decisions
GROUP BY target_cluster;
```

## Gerenciamento de Cache

### Limpar Cache

```bash
cd src/scripts
./limpar-cache.sh
```

Ou manualmente:

```bash
docker-compose exec postgres psql -U dyrasql -d dyrasql \
  -c "TRUNCATE TABLE routing_decisions;"
```

### Ajustar TTL

Edite `src/.env`:

```bash
CACHE_TTL_HOURS=12  # Padrão: 24
```

Reinicie o Core:

```bash
docker-compose restart dyrasql-core
```

### Invalidar Query Específica

```sql
DELETE FROM routing_decisions 
WHERE query_fingerprint = '<fingerprint>';
```

## Configuração Avançada

### Ajustar Pesos do Algoritmo

Edite `src/dyrasql-core/decision_engine.py`:

```python
class DecisionEngine:
    def __init__(self, db_url: str):
        # Pesos configuráveis
        self.w1 = 0.5  # Peso do fator volume
        self.w2 = 0.3  # Peso do fator complexidade
        self.w3 = 0.2  # Peso do fator histórico
```

Valores recomendados por cenário:

#### Cenário 1: Priorizar Volume
```python
self.w1 = 0.6  # Volume alto
self.w2 = 0.2  # Complexidade média
self.w3 = 0.2  # Histórico médio
```
**Quando usar**: Dados com tamanhos muito variados, queries simples

#### Cenário 2: Priorizar Complexidade
```python
self.w1 = 0.3  # Volume baixo
self.w2 = 0.5  # Complexidade alta
self.w3 = 0.2  # Histórico médio
```
**Quando usar**: Dados uniformes, queries com JOINs e agregações complexas

#### Cenário 3: Priorizar Histórico
```python
self.w1 = 0.3  # Volume baixo
self.w2 = 0.2  # Complexidade baixa
self.w3 = 0.5  # Histórico alto
```
**Quando usar**: Workload repetitivo, otimizar decisões anteriores

### Ajustar Limites de Normalização

Edite `src/.env`:

```bash
# Tamanho máximo para normalização (padrão: 10 GB)
MAX_SIZE_GB=20.0

# Linhas máximas para normalização (padrão: 10M)
MAX_ROWS=50000000
```

### Customizar Thresholds de Decisão

Edite `src/dyrasql-core/decision_engine.py`:

```python
def _decide_cluster(self, score: float) -> str:
    # Thresholds configuráveis
    if score < 0.33:    # Padrão: 0.33
        return "small"
    elif score < 0.66:  # Padrão: 0.66
        return "medium"
    else:
        return "large"
```

Exemplo para decisões mais conservadoras:

```python
def _decide_cluster(self, score: float) -> str:
    if score < 0.40:    # Small mais restrito
        return "small"
    elif score < 0.70:  # Medium mais restrito
        return "medium"
    else:
        return "large"
```

## Exemplos de Uso

### Arquivo de Queries Exemplo

O projeto inclui `src/query.sql` com queries pré-configuradas:

```bash
# Executar todas as queries
docker run --rm -i --network host trinodb/trino:latest trino \
  --server http://localhost:8080 \
  --catalog iceberg \
  --schema db \
  --file src/query.sql
```

### Teste de Carga

```python
import trino
import time
from concurrent.futures import ThreadPoolExecutor

def execute_query(query_id):
    conn = trino.dbapi.connect(
        host='localhost',
        port=8080,
        user='admin',
        catalog='iceberg',
        schema='db'
    )
    
    cursor = conn.cursor()
    start = time.time()
    
    cursor.execute(f"""
        SELECT categoria, COUNT(*) 
        FROM dados 
        WHERE id > {query_id * 1000}
        GROUP BY categoria
    """)
    
    result = cursor.fetchall()
    elapsed = time.time() - start
    
    cursor.close()
    conn.close()
    
    return elapsed

# Executar 10 queries em paralelo
with ThreadPoolExecutor(max_workers=10) as executor:
    results = list(executor.map(execute_query, range(10)))

print(f"Tempo médio: {sum(results) / len(results):.2f}s")
```

### Benchmark de Roteamento

```bash
cd src/scripts
./benchmark.sh
```

Gera relatório com:
- Total de queries executadas
- Distribuição por cluster
- Tempo médio por cluster
- Taxa de cache hit

## Análise de Resultados

### Verificar Distribuição de Clusters

```sql
SELECT 
    target_cluster,
    COUNT(*) as queries,
    ROUND(AVG(score), 3) as avg_score,
    ROUND(AVG(effective_size_gb), 2) as avg_size_gb,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as percentage
FROM routing_decisions
GROUP BY target_cluster
ORDER BY queries DESC;
```

Output esperado:
```
 target_cluster | queries | avg_score | avg_size_gb | percentage 
----------------+---------+-----------+-------------+------------
 medium         |     450 |     0.485 |        2.30 |      45.00
 small          |     350 |     0.158 |        0.15 |      35.00
 large          |     200 |     0.752 |        5.80 |      20.00
```

### Taxa de Cache Hit

```sql
SELECT 
    DATE(created_at) as date,
    COUNT(*) as total_decisions,
    COUNT(DISTINCT query_fingerprint) as unique_queries,
    ROUND((COUNT(*) - COUNT(DISTINCT query_fingerprint)) * 100.0 / COUNT(*), 2) as cache_hit_rate
FROM routing_decisions
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

## Troubleshooting

### Query roteada incorretamente

**Problema**: Query simples vai para cluster Large

**Debug**:
```bash
# Ver logs detalhados
docker-compose logs dyrasql-core | grep "Score final"

# Verificar metadados extraídos
docker-compose logs dyrasql-core | grep "Metadados extraídos"
```

**Soluções**:
1. Ajustar pesos (reduzir `w1` se volume está superestimado)
2. Ajustar `MAX_SIZE_GB` se normalização está incorreta
3. Limpar cache se decisão histórica está incorreta

### Cache não funciona

**Problema**: Todas as queries resultam em cache miss

**Debug**:
```bash
# Verificar conexão PostgreSQL
docker-compose exec dyrasql-core python -c "
from sqlalchemy import create_engine
import os
engine = create_engine(os.getenv('DATABASE_URL'))
print(engine.connect())
"
```

**Soluções**:
1. Verificar `DATABASE_URL` em `.env`
2. Reiniciar container PostgreSQL
3. Verificar se tabela existe

### Performance degradada

**Problema**: Queries lentas mesmo com roteamento

**Debug**:
```bash
# Verificar uso de recursos
docker stats

# Verificar health dos clusters
curl http://localhost:8082/v1/info
curl http://localhost:8083/v1/info
curl http://localhost:8084/v1/info
```

**Soluções**:
1. Aumentar recursos Docker
2. Distribuir queries de forma mais equilibrada
3. Adicionar mais workers aos clusters

## Próximos Passos

- Explore a [API completa](api.md)
- Entenda a [arquitetura](arquitetura.md)
- Contribua para o projeto seguindo [CONTRIBUTING.md](../CONTRIBUTING.md)
