# Guia de Desenvolvimento

## Configurando Ambiente de Desenvolvimento

### Requisitos

- Python 3.9+
- Docker 20.10+
- Git 2.30+
- IDE recomendado: VS Code, PyCharm

### Setup Inicial

```bash
# Clone o repositório
git clone https://github.com/trababalhos-puc/tcc-puc-dyrasql.git
cd tcc-puc-dyrasql

# Crie ambiente virtual Python
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instale dependências de desenvolvimento
pip install -r src/dyrasql-core/requirements.txt
pip install pytest pytest-cov black flake8 mypy
```

## Estrutura do Código

### DyraSQL Core (`src/dyrasql-core/`)

```
dyrasql-core/
├── app.py                    # FastAPI application
├── decision_engine.py        # Algoritmo de decisão
├── query_analyzer.py         # Análise de queries
├── history_manager.py        # Gerenciamento de cache
├── requirements.txt          # Dependências
├── Dockerfile                # Build image
└── tests/                    # Testes unitários
```

#### app.py

Ponto de entrada FastAPI. Define rotas:

```python
@app.post("/api/v1/route")
async def route_query(query_request: QueryRequest):
    """Roteia query SQL para cluster apropriado"""
    ...

@app.get("/api/v1/metrics")
async def get_metrics():
    """Retorna métricas do sistema"""
    ...
```

#### decision_engine.py

Núcleo do algoritmo. Principais métodos:

```python
class DecisionEngine:
    def decide_cluster(self, query: str, fingerprint: str) -> RoutingDecision:
        """Decide cluster baseado em metadados e complexidade"""
        
    def _calculate_volume_factor(self, metadata: QueryMetadata) -> float:
        """Calcula fator de volume normalizado"""
        
    def _calculate_complexity_factor(self, ast: Dict) -> float:
        """Analisa AST e calcula complexidade"""
        
    def _calculate_historical_factor(self, fingerprint: str) -> float:
        """Obtém score histórico de decisões similares"""
```

#### query_analyzer.py

Extração de metadados e análise AST:

```python
class QueryAnalyzer:
    def extract_metadata(self, query: str, cluster_url: str) -> QueryMetadata:
        """Executa EXPLAIN (TYPE IO) e extrai metadados"""
        
    def analyze_complexity(self, query: str) -> Dict:
        """Analisa AST da query usando sqlglot"""
        
    def generate_fingerprint(self, query: str) -> str:
        """Gera hash SHA-256 da query normalizada"""
```

#### history_manager.py

Gerenciamento de cache PostgreSQL:

```python
class HistoryManager:
    def get_cached_decision(self, fingerprint: str) -> Optional[CachedDecision]:
        """Busca decisão no cache"""
        
    def save_decision(self, decision: RoutingDecision):
        """Armazena decisão com TTL"""
        
    def get_historical_score(self, fingerprint: str) -> float:
        """Calcula score médio de decisões similares"""
```

### Trino Gateway Proxy (`src/trino-gateway-proxy/`)

```
trino-gateway-proxy/
├── app.py                    # FastAPI proxy
├── requirements.txt          # Dependências
└── Dockerfile                # Build image
```

Proxy que intercepta queries e integra com DyraSQL Core:

```python
@app.post("/v1/statement")
async def proxy_statement(request: Request):
    """Intercepta statement, roteia, e encaminha"""
    query = await request.body()
    
    # Obter decisão de roteamento
    decision = await get_routing_decision(query)
    
    # Reescrever URL de destino
    target_url = f"{TRINO_GATEWAY_URL}/v1/statement"
    headers = dict(request.headers)
    headers["X-Trino-Routing-Group"] = decision["cluster"]
    
    # Encaminhar para Trino Gateway
    response = requests.post(target_url, data=query, headers=headers)
    return response.content
```

## Testes

### Executar Testes

```bash
# Testes unitários
cd src/dyrasql-core
pytest tests/

# Com cobertura
pytest --cov=. tests/

# Teste específico
pytest tests/test_decision_engine.py::test_volume_factor
```

### Estrutura de Testes

```python
# tests/test_decision_engine.py
import pytest
from decision_engine import DecisionEngine

@pytest.fixture
def engine():
    return DecisionEngine(database_url="sqlite:///:memory:")

def test_volume_factor_small(engine):
    metadata = {
        "effective_size_gb": 0.1,
        "effective_rows": 1000,
        "optimization_factor": 0.9
    }
    
    factor = engine._calculate_volume_factor(metadata)
    
    assert 0 <= factor <= 0.2, "Small volume should have low factor"

def test_complexity_factor_joins(engine):
    query = """
        SELECT a.*, b.*
        FROM table_a a
        JOIN table_b b ON a.id = b.id
    """
    
    ast = engine.analyzer.analyze_complexity(query)
    factor = engine._calculate_complexity_factor(ast)
    
    assert factor > 0.3, "Queries with JOINs should have higher complexity"
```

### Testes de Integração

```python
# tests/test_integration.py
import requests
import pytest

@pytest.fixture(scope="module")
def setup_services():
    """Inicia serviços Docker para testes"""
    # subprocess para docker-compose up
    yield
    # subprocess para docker-compose down

def test_end_to_end_routing(setup_services):
    query = "SELECT * FROM dados WHERE id = 123"
    
    # Enviar query via proxy
    response = requests.post(
        "http://localhost:8080/v1/statement",
        data=query,
        headers={"X-Trino-User": "admin"}
    )
    
    assert response.status_code == 200
    
    # Verificar que foi roteada corretamente
    metrics = requests.get("http://localhost:8000/api/v1/metrics").json()
    assert metrics["total_decisions"] > 0
```

## Depuração

### Logs Detalhados

Adicione logging em pontos críticos:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def decide_cluster(self, query: str) -> str:
    logger.debug(f"Analyzing query: {query[:100]}")
    
    metadata = self.analyzer.extract_metadata(query)
    logger.debug(f"Metadata: {metadata}")
    
    score = self._calculate_score(metadata)
    logger.debug(f"Final score: {score}")
    
    cluster = self._decide_cluster(score)
    logger.info(f"Routing to: {cluster}")
    
    return cluster
```

### Debug com VS Code

`.vscode/launch.json`:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: FastAPI",
            "type": "python",
            "request": "launch",
            "module": "uvicorn",
            "args": [
                "app:app",
                "--reload",
                "--host", "0.0.0.0",
                "--port", "8000"
            ],
            "jinja": true,
            "justMyCode": true,
            "env": {
                "DATABASE_URL": "postgresql://dyrasql:dyrasql123@localhost:5432/dyrasql"
            }
        }
    ]
}
```

### Profiling

```python
import cProfile
import pstats

def profile_decision_engine():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Código a ser analisado
    engine = DecisionEngine(...)
    for i in range(1000):
        engine.decide_cluster(f"SELECT * FROM table WHERE id = {i}")
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)
```

## Contribuindo

### Workflow de Desenvolvimento

1. **Fork** o repositório
2. **Clone** seu fork:
   ```bash
   git clone https://github.com/seu-usuario/tcc-puc-dyrasql.git
   cd tcc-puc-dyrasql
   ```

3. **Crie branch** para feature/fix:
   ```bash
   git checkout -b feature/nova-funcionalidade
   ```

4. **Desenvolva** com testes:
   ```bash
   # Faça alterações
   # Adicione testes
   pytest tests/
   ```

5. **Format** código:
   ```bash
   black src/dyrasql-core/*.py
   flake8 src/dyrasql-core/
   mypy src/dyrasql-core/
   ```

6. **Commit** seguindo convenção:
   ```bash
   git commit -m "feat: adiciona suporte a queries CTEs"
   ```

7. **Push** e abra **Pull Request**:
   ```bash
   git push origin feature/nova-funcionalidade
   ```

### Convenções de Código

#### Python Style Guide

- **PEP 8** para estilo geral
- **Black** para formatação automática
- **Type hints** obrigatórios:
  ```python
  def calculate_score(
      self,
      volume: float,
      complexity: float,
      historical: float
  ) -> float:
      return self.w1 * volume + self.w2 * complexity + self.w3 * historical
  ```

#### Docstrings

```python
def decide_cluster(self, query: str, fingerprint: str) -> RoutingDecision:
    """
    Decide qual cluster Trino deve executar a query.
    
    Args:
        query: Consulta SQL a ser analisada
        fingerprint: Hash SHA-256 da query para cache
    
    Returns:
        RoutingDecision contendo cluster de destino, score e fatores
    
    Raises:
        ConnectionError: Se não conseguir conectar ao Trino
        ValueError: Se query estiver malformada
    
    Example:
        >>> engine = DecisionEngine(db_url)
        >>> decision = engine.decide_cluster("SELECT * FROM dados", "abc123")
        >>> print(decision.cluster)
        'small'
    """
    ...
```

#### Commits Semânticos

```
feat: adiciona nova funcionalidade
fix: corrige bug
docs: atualiza documentação
test: adiciona/modifica testes
refactor: refatora código sem mudar comportamento
perf: melhora performance
chore: tarefas de manutenção
```

### Code Review

Pull requests devem:

- [ ] Passar em todos os testes
- [ ] Ter cobertura de testes > 80%
- [ ] Seguir style guide (Black + Flake8)
- [ ] Incluir documentação atualizada
- [ ] Ter commits semânticos
- [ ] Ser revisado por pelo menos 1 maintainer

## Extensões

### Adicionando Novo Fator ao Algoritmo

```python
# decision_engine.py

def _calculate_cost_factor(self, metadata: QueryMetadata) -> float:
    """
    Calcula fator de custo financeiro baseado em pricing AWS/Cloud.
    
    Args:
        metadata: Metadados da query (size, rows, etc.)
    
    Returns:
        Fator de custo normalizado (0-1)
    """
    # Exemplo: custo por GB processado
    cost_per_gb = 0.005  # $0.005/GB
    
    estimated_cost = metadata.effective_size_gb * cost_per_gb
    max_acceptable_cost = 0.10  # $0.10
    
    normalized_cost = min(estimated_cost / max_acceptable_cost, 1.0)
    
    return normalized_cost

def _calculate_score(self, metadata: QueryMetadata, ast: Dict, fingerprint: str) -> float:
    """Adiciona novo fator ao cálculo"""
    fv = self._calculate_volume_factor(metadata)
    fc = self._calculate_complexity_factor(ast)
    fh = self._calculate_historical_factor(fingerprint)
    fcost = self._calculate_cost_factor(metadata)  # Novo fator
    
    # Ajustar pesos
    score = (
        self.w1 * fv +
        self.w2 * fc +
        self.w3 * fh +
        self.w4 * fcost  # Novo peso
    )
    
    return min(score, 1.0)
```

### Adicionando Novo Cluster

1. **Adicionar configuração Trino** em `src/trino/config/xlarge/`:

```properties
# config.properties
coordinator=true
node-scheduler.include-coordinator=true
http-server.http.port=8085
discovery.uri=http://localhost:8085
query.max-memory=16GB
query.max-memory-per-node=4GB
```

2. **Atualizar docker-compose.yml**:

```yaml
trino-xlarge:
  image: trinodb/trino:latest
  ports:
    - "8085:8085"
  volumes:
    - ./trino/config/xlarge:/etc/trino
```

3. **Atualizar decision_engine.py**:

```python
def _decide_cluster(self, score: float) -> str:
    if score < 0.25:
        return "small"
    elif score < 0.50:
        return "medium"
    elif score < 0.75:
        return "large"
    else:
        return "xlarge"  # Novo cluster
```

4. **Registrar no Trino Gateway**:

```bash
./scripts/setup-gateway-backends-auto.sh
```

## Monitoramento e Observabilidade

### Adicionando Métricas Prometheus

```python
# metrics.py
from prometheus_client import Counter, Histogram, Gauge

routing_decisions_total = Counter(
    'dyrasql_routing_decisions_total',
    'Total de decisões de roteamento',
    ['cluster', 'cache_status']
)

routing_duration_seconds = Histogram(
    'dyrasql_routing_duration_seconds',
    'Tempo de decisão de roteamento',
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)

# Em decision_engine.py
def decide_cluster(self, query: str, fingerprint: str) -> RoutingDecision:
    with routing_duration_seconds.time():
        decision = self._make_decision(query, fingerprint)
    
    routing_decisions_total.labels(
        cluster=decision.cluster,
        cache_status='hit' if decision.cache_hit else 'miss'
    ).inc()
    
    return decision
```

### Logs Estruturados

```python
import structlog

logger = structlog.get_logger()

def decide_cluster(self, query: str, fingerprint: str) -> RoutingDecision:
    logger.info(
        "routing_decision_started",
        fingerprint=fingerprint,
        query_preview=query[:50]
    )
    
    decision = self._make_decision(query, fingerprint)
    
    logger.info(
        "routing_decision_completed",
        fingerprint=fingerprint,
        cluster=decision.cluster,
        score=decision.score,
        cache_hit=decision.cache_hit,
        duration_ms=decision.duration_ms
    )
    
    return decision
```

## Recursos Adicionais

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Trino Documentation](https://trino.io/docs/current/)
- [Apache Iceberg](https://iceberg.apache.org/)
- [SQLGlot](https://github.com/tobymao/sqlglot)
- [PostgreSQL](https://www.postgresql.org/docs/)
