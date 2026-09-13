# DyraSQL - Guia de Início Rápido

Este guia permite que você tenha o DyraSQL funcionando em **5 minutos**.

## Pré-requisitos

- Docker 20.10+
- Docker Compose 2.0+
- 8GB+ RAM disponível
- 20GB+ espaço em disco

## Passo a Passo

### 1. Clone o repositório

```bash
git clone -b developer https://github.com/trababalhos-puc/tcc-puc-dyrasql.git
cd tcc-puc-dyrasql/src
```

### 2. Suba o ambiente

```bash
docker compose up -d
```

**Aguarde 2-3 minutos** para todos os serviços ficarem prontos.

### 3. Valide a instalação

```bash
./validar.sh
```

Se todos os testes passarem, você verá:

```
✓ Todos os testes passaram!
```

### 4. Execute sua primeira consulta

```bash
docker compose exec trino-small trino \
  --server http://localhost:8080 \
  --user admin \
  --catalog iceberg \
  --schema analytics
```

No prompt do Trino, execute:

```sql
SELECT COUNT(*) FROM dados;
```

### 5. Monitore o roteamento

Em outro terminal:

```bash
./scripts/monitor-routing.sh
```

Você verá as decisões de roteamento em tempo real:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Query will be executed on cluster 'small'
  [DECISION] score=0.120, cluster=small
  Factors: volume=0.100, complexity=0.050, historical=0.500
```

## Consultas de Exemplo

### Consulta Simples → Cluster Small

```sql
SELECT COUNT(*) 
FROM iceberg.analytics.dados
WHERE date = TIMESTAMP '2024-01-15';
```

**Esperado:** Score < 0.3, cluster **small**

### Consulta Intermediária → Cluster Medium

```sql
SELECT 
    t.tenant_id,
    t.categoria,
    COUNT(*) as total,
    SUM(d.valor) as soma
FROM iceberg.analytics.dados d
JOIN iceberg.analytics.tenant_info t ON d.tenant_id = t.tenant_id
WHERE d.date >= TIMESTAMP '2024-01-01'
  AND d.date < TIMESTAMP '2024-01-15'
GROUP BY t.tenant_id, t.categoria;
```

**Esperado:** 0.3 <= Score <= 0.7, cluster **medium**

### Consulta Complexa → Cluster Large

```sql
SELECT 
    t.tenant_id,
    t.categoria,
    COUNT(*) as total,
    SUM(d.valor) as valor_total,
    AVG(d.valor) as media,
    STDDEV(d.valor) as desvio
FROM iceberg.analytics.dados d
JOIN iceberg.analytics.tenant_info t ON d.tenant_id = t.tenant_id
WHERE d.date >= TIMESTAMP '2024-01-01'
  AND t.categoria IN (
      SELECT categoria 
      FROM iceberg.analytics.tenant_info 
      WHERE nivel > (SELECT AVG(nivel) FROM iceberg.analytics.tenant_info)
  )
GROUP BY t.tenant_id, t.categoria
HAVING COUNT(*) > 50;
```

**Esperado:** Score > 0.7, cluster **large**

## Interfaces Web

| Serviço | URL | Descrição |
|---------|-----|-----------|
| DyraSQL Proxy | http://localhost:8080 | Acesso principal (use para conectar IDEs) |
| DyraSQL Core API | http://localhost:5001/health | API de decisão |
| Trino Gateway | http://localhost:8085 | Gateway oficial |
| MinIO Console | http://localhost:9001 | Storage (dyrasql/dyrasql1) |
| Trino Small | http://localhost:8081 | Cluster pequeno |
| Trino Medium | http://localhost:8082 | Cluster médio |
| Trino Large | http://localhost:8083 | Cluster grande |

## Comandos Úteis

### Ver logs em tempo real

```bash
docker compose logs -f dyrasql-core
```

### Limpar cache de decisões

```bash
./scripts/limpar-cache.sh
```

### Ver consultas no cache

```bash
docker compose exec gateway-db psql -U dyrasql -d dyrasql -c \
  "SELECT fingerprint, cluster, score, created_at FROM routing_decisions ORDER BY created_at DESC LIMIT 5;"
```

### Reiniciar um serviço

```bash
docker compose restart dyrasql-core
```

### Parar tudo

```bash
docker compose down
```

### Remover tudo (incluindo dados)

```bash
docker compose down -v
```

## Conectar IDEs

### DataGrip / DataSpell / IntelliJ

1. Novo Data Source → Trino
2. **Host:** `localhost`
3. **Port:** `8080`
4. **User:** `admin`
5. **Catalog:** `iceberg`
6. **Schema:** `analytics`
7. **JDBC URL:** `jdbc:trino://localhost:8080/iceberg/analytics`

### DBeaver

1. Nova Conexão → Presto/Trino
2. **Host:** `localhost`
3. **Port:** `8080`
4. **Database:** `iceberg/analytics`
5. **User:** `admin`

## Solução de Problemas

### Containers não ficam healthy

```bash
docker compose logs dyrasql-core
docker compose logs trino-gateway
```

### Tabelas Iceberg não foram criadas

```bash
docker compose logs iceberg-init
docker compose restart iceberg-init
```

### Cache não funciona

```bash
docker compose exec gateway-db psql -U dyrasql -d dyrasql -c \
  "SELECT COUNT(*) FROM routing_decisions;"
```

### Erro ao conectar IDE

1. Verifique se porta 8080 está liberada
2. Teste com curl: `curl http://localhost:8080/v1/info`
3. Veja logs: `docker compose logs trino-gateway-proxy`

## Próximos Passos

1. 📖 Leia o [README completo](README.md)
2. 🏗️ Entenda a [arquitetura](../doc/arquitetura.md)
3. 📊 Execute as [queries de teste](query.sql)
4. 📝 Leia a [monografia](../latex/principal.pdf)

## Suporte

- **Issues:** https://github.com/trababalhos-puc/tcc-puc-dyrasql/issues
- **Email:** arihenriquedev@hotmail.com

---

**Desenvolvido por:** Aristides Henrique Gonçalves da Cruz  
**PUC Minas - 2024**
