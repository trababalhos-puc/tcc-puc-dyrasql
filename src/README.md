# DyraSQL - Software

Framework de roteamento dinâmico de consultas SQL baseado em análise de metadados Apache Iceberg.

## Arquitetura

O sistema é composto por:

- **DyraSQL Core**: Motor de decisão que analisa consultas e calcula scores
- **Trino Gateway Proxy**: Intercepta queries e consulta o Core para roteamento
- **Trino Gateway**: Balanceador oficial do Trino
- **3 Clusters Trino**: small, medium, large (capacidades distintas)
- **PostgreSQL**: Cache de decisões e histórico
- **MinIO**: Storage S3-compatible para tabelas Iceberg
- **Iceberg REST Catalog**: Catálogo de metadados compartilhado

## Pré-requisitos

- Docker 20.10+
- Docker Compose 2.0+
- 8GB+ RAM disponível
- Portas livres: 8080, 8081-8085, 9000-9001, 5001

## Início Rápido

### 1. Subir o ambiente

```bash
cd src
docker compose up -d
```

Aguarde todos os serviços ficarem saudáveis (2-3 minutos).

### 2. Verificar status

```bash
docker compose ps
```

Todos os containers devem estar com status `healthy` ou `running`.

### 3. Acessar interfaces

- **DyraSQL Proxy** (acesso principal): http://localhost:8080
- **DyraSQL Core** (API): http://localhost:5001/health
- **Trino Gateway**: http://localhost:8085
- **MinIO Console**: http://localhost:9001 (dyrasql / dyrasql1)

### 4. Executar consultas de teste

#### Via CLI do Trino

```bash
docker compose exec trino-small trino \
  --server http://localhost:8080 \
  --user admin \
  --catalog iceberg \
  --schema analytics
```

#### Consultas de exemplo

```sql
-- Consulta simples (esperado: cluster small)
SELECT COUNT(*) FROM iceberg.analytics.dados;

-- Consulta intermediária (esperado: cluster medium)
SELECT 
    t.tenant_id,
    t.categoria,
    COUNT(*) as total_registros,
    SUM(d.valor) as valor_total,
    AVG(d.valor) as valor_medio
FROM iceberg.analytics.dados d
JOIN iceberg.analytics.tenant_info t ON d.tenant_id = t.tenant_id
WHERE d.date >= TIMESTAMP '2024-01-01' 
  AND d.date < TIMESTAMP '2024-02-01'
  AND d.status = 'ATIVO'
GROUP BY t.tenant_id, t.categoria
HAVING COUNT(*) > 100
ORDER BY valor_total DESC
LIMIT 50;

-- Consulta complexa (esperado: cluster large)
SELECT 
    t.tenant_id,
    t.categoria,
    COUNT(*) as total,
    SUM(d.valor) as valor_total,
    AVG(d.valor) as media,
    MAX(d.valor) as maximo,
    MIN(d.valor) as minimo,
    STDDEV(d.valor) as desvio_padrao
FROM iceberg.analytics.dados d
JOIN iceberg.analytics.tenant_info t ON d.tenant_id = t.tenant_id
WHERE d.date >= TIMESTAMP '2024-01-01'
  AND d.status = 'ATIVO'
  AND t.categoria IN (
      SELECT categoria 
      FROM iceberg.analytics.tenant_info 
      WHERE nivel > (SELECT AVG(nivel) FROM iceberg.analytics.tenant_info)
  )
GROUP BY t.tenant_id, t.categoria
HAVING COUNT(*) > 50
ORDER BY valor_total DESC;
```

### 5. Monitorar roteamento

```bash
# Monitorar decisões em tempo real
./scripts/monitor-routing.sh

# Ver logs brutos do Core
./scripts/debug-ide-raw.sh
```

## Configuração

### Variáveis de ambiente do DyraSQL Core

Edite o arquivo `docker-compose.yml` na seção `dyrasql-core`:

```yaml
environment:
  # Pesos do algoritmo (soma deve ser 1.0)
  DYRASQL_WEIGHT_VOLUME: "0.5"      # Peso do fator volume
  DYRASQL_WEIGHT_COMPLEXITY: "0.3"  # Peso do fator complexidade
  DYRASQL_WEIGHT_HISTORICAL: "0.2"  # Peso do fator histórico
  
  # Thresholds de roteamento
  DYRASQL_SMALL_THRESHOLD: "0.3"    # Score < 0.3 = small
  DYRASQL_MEDIUM_THRESHOLD: "0.7"   # 0.3 <= Score <= 0.7 = medium
                                     # Score > 0.7 = large
  
  # Cache
  CACHE_TTL_HOURS: "24"             # TTL do cache em horas
  
  # Logging
  SAVE_EXPLAINS: "true"             # Salvar EXPLAIN em JSON
  EXPLAINS_DIR: /app/explains       # Diretório dos EXPLAIN
```

### Ajustar capacidade dos clusters

Edite os arquivos em `trino/config/{small,medium,large}/config.properties`:

```properties
# Exemplo para cluster medium
query.max-memory=2GB
query.max-execution-time=10m
```

## Estrutura de Diretórios

```
src/
├── dyrasql-core/           # Motor de decisão
│   ├── app.py             # API principal
│   ├── decision_engine.py # Algoritmo de pontuação
│   ├── query_analyzer.py  # Análise de consultas
│   ├── history_manager.py # Cache e histórico
│   └── Dockerfile
├── trino-gateway-proxy/    # Proxy de interceptação
│   ├── app.py
│   └── Dockerfile
├── trino-gateway/          # Gateway oficial
│   ├── config.yaml
│   └── Dockerfile
├── trino/config/           # Configurações dos clusters
│   ├── small/
│   ├── medium/
│   └── large/
├── scripts/                # Scripts auxiliares
│   ├── init-iceberg.sh
│   ├── setup-gateway-backends-auto.sh
│   ├── monitor-routing.sh
│   └── limpar-cache.sh
├── postgres/               # Inicialização do DB
│   └── init-dyrasql.sh
└── docker-compose.yml      # Orquestração completa
```

## API do DyraSQL Core

### POST /api/v1/route

Analisa uma consulta e retorna decisão de roteamento.

**Request:**
```json
{
  "query": "SELECT * FROM iceberg.analytics.dados WHERE date = DATE '2024-01-01'"
}
```

**Response:**
```json
{
  "fingerprint": "a1b2c3d4...",
  "cluster": "medium",
  "score": 0.44,
  "factors": {
    "volume": 0.27,
    "complexity": 0.69,
    "historical": 0.50
  },
  "cached": false,
  "cluster_url": "http://trino-medium:8080"
}
```

### POST /api/v1/metrics

Salva métricas pós-execução para aprendizado.

**Request:**
```json
{
  "fingerprint": "a1b2c3d4...",
  "metrics": {
    "execution_time": 1.23,
    "cost": 0.05,
    "success": true
  }
}
```

## Troubleshooting

### Containers não ficam healthy

```bash
# Verificar logs
docker compose logs dyrasql-core
docker compose logs trino-gateway

# Reiniciar serviços problemáticos
docker compose restart dyrasql-core
```

### Trino não conecta ao Iceberg

```bash
# Verificar MinIO
docker compose logs minio
docker compose exec minio mc ls local/

# Verificar catálogo REST
docker compose logs iceberg-rest
```

### Cache não funciona

```bash
# Verificar PostgreSQL
docker compose exec gateway-db psql -U dyrasql -d dyrasql \
  -c "SELECT * FROM routing_decisions ORDER BY created_at DESC LIMIT 5;"

# Limpar cache
./scripts/limpar-cache.sh
```

### Queries não roteiam corretamente

```bash
# Ver decisões em tempo real
./scripts/monitor-routing.sh

# Verificar logs detalhados
docker compose logs -f dyrasql-core | grep -E "(score|cluster|Decision)"
```

## Manutenção

### Backup do cache

```bash
docker compose exec gateway-db pg_dump -U dyrasql dyrasql > backup_dyrasql.sql
```

### Limpar dados antigos

```bash
# Limpar cache expirado
docker compose exec gateway-db psql -U dyrasql -d dyrasql \
  -c "DELETE FROM routing_decisions WHERE expires_at < NOW();"

# Limpar explains antigos (> 7 dias)
find ./explains -name "*.json" -mtime +7 -delete
```

### Parar e limpar ambiente

```bash
# Parar containers
docker compose down

# Remover volumes (CUIDADO: perde dados!)
docker compose down -v
```

## Desenvolvimento

### Modificar código do Core

1. Edite os arquivos em `dyrasql-core/`
2. Reconstrua a imagem: `docker compose build dyrasql-core`
3. Reinicie: `docker compose restart dyrasql-core`

### Testar localmente sem Docker

```bash
cd dyrasql-core
pip install -r requirements.txt

# Configure variáveis
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export TRINO_URL=http://localhost:8081

# Execute
python app.py
```

## Referências

- [Trino Documentation](https://trino.io/docs/current/)
- [Apache Iceberg](https://iceberg.apache.org/)
- [Trino Gateway](https://github.com/trinodb/trino-gateway)
- [Artigo completo: ../latex/principal.pdf](../latex/principal.pdf)
