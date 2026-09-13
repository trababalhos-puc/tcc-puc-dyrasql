# API Reference

## DyraSQL Core API

Base URL: `http://localhost:8000`

### Endpoints

#### 1. POST /api/v1/route

Solicita decisão de roteamento para uma query SQL.

**Request**

```http
POST /api/v1/route HTTP/1.1
Content-Type: application/json

{
    "query": "SELECT * FROM dados WHERE id = 123",
    "fingerprint": "abc123def456"
}
```

**Parameters**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| query | string | Sim | Consulta SQL a ser roteada |
| fingerprint | string | Sim | Identificador único da query (SHA-256) |

**Response 200 OK**

```json
{
    "cluster": "small",
    "score": 0.08,
    "factors": {
        "volume": 0.05,
        "complexity": 0.10,
        "historical": 0.00
    },
    "metadata": {
        "effective_size_gb": 0.05,
        "effective_rows": 1000,
        "optimization_factor": 0.95
    },
    "cache_hit": false
}
```

**Response Fields**

| Campo | Tipo | Descrição |
|-------|------|-----------|
| cluster | string | Cluster de destino: `small`, `medium` ou `large` |
| score | float | Score final calculado (0-1) |
| factors.volume | float | Fator de volume normalizado |
| factors.complexity | float | Fator de complexidade |
| factors.historical | float | Fator histórico |
| metadata.effective_size_gb | float | Tamanho efetivo em GB |
| metadata.effective_rows | integer | Número de linhas estimado |
| metadata.optimization_factor | float | Fator de otimização Iceberg (0-1) |
| cache_hit | boolean | Se decisão veio do cache |

**Response 400 Bad Request**

```json
{
    "detail": "Query parameter is required"
}
```

**Response 500 Internal Server Error**

```json
{
    "detail": "Failed to analyze query: connection timeout"
}
```

**Example (cURL)**

```bash
curl -X POST http://localhost:8000/api/v1/route \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT categoria, COUNT(*) FROM dados GROUP BY categoria",
    "fingerprint": "7f9a3b2c1d8e6f5a4b3c2d1e0f9a8b7c"
  }'
```

**Example (Python)**

```python
import requests
import hashlib

query = "SELECT * FROM dados WHERE id = 123"
fingerprint = hashlib.sha256(query.encode()).hexdigest()

response = requests.post(
    "http://localhost:8000/api/v1/route",
    json={
        "query": query,
        "fingerprint": fingerprint
    }
)

data = response.json()
print(f"Cluster: {data['cluster']}")
print(f"Score: {data['score']:.3f}")
```

---

#### 2. GET /api/v1/metrics

Retorna métricas do sistema de roteamento.

**Request**

```http
GET /api/v1/metrics HTTP/1.1
```

**Response 200 OK**

```json
{
    "total_decisions": 1250,
    "cache_hits": 450,
    "cache_miss": 800,
    "cache_hit_rate": 0.36,
    "cluster_distribution": {
        "small": 450,
        "medium": 520,
        "large": 280
    },
    "avg_scores": {
        "small": 0.15,
        "medium": 0.48,
        "large": 0.75
    },
    "avg_response_time_ms": 125.5
}
```

**Response Fields**

| Campo | Tipo | Descrição |
|-------|------|-----------|
| total_decisions | integer | Total de decisões realizadas |
| cache_hits | integer | Decisões servidas do cache |
| cache_miss | integer | Decisões que executaram análise |
| cache_hit_rate | float | Taxa de acerto do cache (0-1) |
| cluster_distribution | object | Distribuição de queries por cluster |
| avg_scores | object | Score médio por cluster |
| avg_response_time_ms | float | Tempo médio de resposta em ms |

**Example (cURL)**

```bash
curl http://localhost:8000/api/v1/metrics
```

**Example (Python)**

```python
import requests

response = requests.get("http://localhost:8000/api/v1/metrics")
metrics = response.json()

print(f"Cache Hit Rate: {metrics['cache_hit_rate'] * 100:.1f}%")
print(f"Distribuição:")
for cluster, count in metrics['cluster_distribution'].items():
    print(f"  {cluster}: {count} queries")
```

---

#### 3. GET /health

Verifica status do serviço DyraSQL Core.

**Request**

```http
GET /health HTTP/1.1
```

**Response 200 OK**

```json
{
    "status": "healthy",
    "database": "connected",
    "trino_clusters": {
        "small": "healthy",
        "medium": "healthy",
        "large": "healthy"
    },
    "version": "1.0.0"
}
```

**Response 503 Service Unavailable**

```json
{
    "status": "unhealthy",
    "database": "disconnected",
    "trino_clusters": {
        "small": "unhealthy",
        "medium": "healthy",
        "large": "healthy"
    }
}
```

---

#### 4. GET /v1/info (Proxy Trino)

Endpoint de compatibilidade Trino para informações do cluster.

**Request**

```http
GET /v1/info HTTP/1.1
```

**Response 200 OK**

```json
{
    "nodeVersion": {
        "version": "DyraSQL-Proxy-1.0.0"
    },
    "coordinator": true,
    "starting": false
}
```

---

#### 5. POST /v1/statement (Proxy Trino)

Endpoint de compatibilidade Trino para execução de statements.

**Request**

```http
POST /v1/statement HTTP/1.1
Content-Type: text/plain
X-Trino-User: admin
X-Trino-Catalog: iceberg
X-Trino-Schema: db

SELECT * FROM dados WHERE id = 123
```

**Headers**

| Header | Obrigatório | Descrição |
|--------|-------------|-----------|
| X-Trino-User | Sim | Usuário Trino |
| X-Trino-Catalog | Não | Catálogo padrão |
| X-Trino-Schema | Não | Schema padrão |

**Response**

Redireciona transparentemente para o cluster Trino apropriado após decisão de roteamento.

---

## Trino Gateway API

Base URL: `http://localhost:8081`

### Endpoints

#### GET /v1/gateway

Retorna informações sobre backends configurados.

```bash
curl http://localhost:8081/v1/gateway
```

Response:
```json
[
    {
        "name": "trino-small",
        "proxyTo": "http://trino-small:8082",
        "active": true,
        "routingGroup": "adhoc"
    },
    {
        "name": "trino-medium",
        "proxyTo": "http://trino-medium:8083",
        "active": true,
        "routingGroup": "adhoc"
    },
    {
        "name": "trino-large",
        "proxyTo": "http://trino-large:8084",
        "active": true,
        "routingGroup": "adhoc"
    }
]
```

---

## Exemplos de Integração

### Cliente Python Completo

```python
import requests
import hashlib
import trino
from typing import Dict, Any

class DyraSQLClient:
    def __init__(self, proxy_url: str = "http://localhost:8080"):
        self.proxy_url = proxy_url
        self.core_url = "http://localhost:8000"
    
    def _generate_fingerprint(self, query: str) -> str:
        """Gera fingerprint SHA-256 da query"""
        return hashlib.sha256(query.encode()).hexdigest()
    
    def get_routing_decision(self, query: str) -> Dict[str, Any]:
        """Obtém decisão de roteamento sem executar query"""
        fingerprint = self._generate_fingerprint(query)
        
        response = requests.post(
            f"{self.core_url}/api/v1/route",
            json={"query": query, "fingerprint": fingerprint}
        )
        
        return response.json()
    
    def execute_query(self, query: str, catalog: str = "iceberg", schema: str = "db"):
        """Executa query via proxy com roteamento automático"""
        conn = trino.dbapi.connect(
            host=self.proxy_url.split("://")[1].split(":")[0],
            port=int(self.proxy_url.split(":")[-1]),
            user='admin',
            catalog=catalog,
            schema=schema
        )
        
        cursor = conn.cursor()
        cursor.execute(query)
        
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        cursor.close()
        conn.close()
        
        return columns, results

# Uso
client = DyraSQLClient()

# Ver decisão sem executar
query = "SELECT categoria, COUNT(*) FROM dados GROUP BY categoria"
decision = client.get_routing_decision(query)
print(f"Query será roteada para: {decision['cluster']}")
print(f"Score: {decision['score']:.3f}")

# Executar query com roteamento automático
columns, rows = client.execute_query(query)
for row in rows:
    print(dict(zip(columns, row)))
```

### Integração com Apache Airflow

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import requests

def route_and_execute_query(**context):
    query = context['params']['query']
    fingerprint = hashlib.sha256(query.encode()).hexdigest()
    
    # Obter decisão de roteamento
    routing_response = requests.post(
        "http://dyrasql-core:8000/api/v1/route",
        json={"query": query, "fingerprint": fingerprint}
    )
    
    routing_data = routing_response.json()
    cluster = routing_data['cluster']
    
    # Executar no cluster apropriado
    cluster_urls = {
        "small": "http://trino-small:8082",
        "medium": "http://trino-medium:8083",
        "large": "http://trino-large:8084"
    }
    
    # Executar query...
    
    return {
        "cluster": cluster,
        "score": routing_data['score']
    }

with DAG(
    'dyrasql_data_pipeline',
    start_date=datetime(2026, 1, 1),
    schedule_interval='@daily'
) as dag:
    
    task = PythonOperator(
        task_id='execute_with_routing',
        python_callable=route_and_execute_query,
        params={'query': 'SELECT * FROM dados WHERE data = CURRENT_DATE'}
    )
```

### Monitoring com Prometheus

```python
# metrics_exporter.py
from prometheus_client import start_http_server, Gauge, Counter
import requests
import time

# Métricas
routing_decisions = Counter('dyrasql_routing_decisions_total', 'Total routing decisions', ['cluster'])
cache_hit_rate = Gauge('dyrasql_cache_hit_rate', 'Cache hit rate')
avg_score = Gauge('dyrasql_avg_score', 'Average score', ['cluster'])

def collect_metrics():
    while True:
        try:
            response = requests.get('http://dyrasql-core:8000/api/v1/metrics')
            data = response.json()
            
            # Atualizar métricas
            cache_hit_rate.set(data['cache_hit_rate'])
            
            for cluster, count in data['cluster_distribution'].items():
                routing_decisions.labels(cluster=cluster).inc(count)
                avg_score.labels(cluster=cluster).set(data['avg_scores'][cluster])
            
        except Exception as e:
            print(f"Error collecting metrics: {e}")
        
        time.sleep(60)  # Coletar a cada 1 minuto

if __name__ == '__main__':
    start_http_server(9090)
    collect_metrics()
```

---

## Rate Limiting

Atualmente não implementado. Para ambientes de produção, considere adicionar rate limiting no nível do proxy:

```python
# Exemplo com FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/v1/route")
@limiter.limit("100/minute")
async def route_query(request: Request, ...):
    ...
```

---

## Autenticação

Atualmente não implementado. Para ambientes de produção, considere adicionar autenticação JWT:

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    # Verificar token JWT...
    if not valid_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    return token

@app.post("/api/v1/route")
async def route_query(query_request: QueryRequest, token: str = Depends(verify_token)):
    ...
```
