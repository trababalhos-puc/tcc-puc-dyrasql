# Gerador de Dados Sintéticos

Este documento descreve o gerador de dados sintéticos do DyraSQL, usado para criar datasets de teste para tabelas Apache Iceberg.

## Visão Geral

O script `generate_data.py` gera consultas SQL INSERT para popular tabelas Iceberg com dados sintéticos de diferentes volumes, permitindo testar o comportamento do algoritmo de roteamento em diferentes cenários.

## Uso Básico

### 1. Gerar Dataset Padrão (180k registros)

```bash
cd src/scripts
./generate_data.py
```

Gera o arquivo `load-iceberg-generated.sql` com 180.000 registros distribuídos por 90 dias.

### 2. Gerar Dataset Customizado

```bash
./generate_data.py --records 500000 --days 180 --batch 2000 --output meu-dataset.sql
```

Parâmetros:
- `--records`: Número total de registros (padrão: 180000)
- `--start-date`: Data inicial (padrão: 2024-01-01)
- `--days`: Range de dias (padrão: 90)
- `--batch`: Registros por INSERT (padrão: 1000)
- `--output`: Arquivo de saída (padrão: load-iceberg-generated.sql)

### 3. Gerar Dataset Grande (por GB)

```bash
./generate_data.py --size-gb 10 --output load-10gb.sql
```

Gera um dataset de aproximadamente 10 GB (~52 milhões de registros).

### 4. Gerar Dataset de 1 Ano

```bash
./generate_data.py --records 1000000 --days 365 --start-date 2023-01-01
```

## Estrutura dos Dados

### Tabela: tenant_info

Sempre gera 50 registros fixos:

| Campo | Tipo | Descrição |
|-------|------|-----------|
| tenant_id | varchar | T1, T2, ..., T50 |
| categoria | varchar | A, B ou C (distribuído igualmente) |
| nivel | integer | 1 a 10 (cíclico) |

### Tabela: dados

Registros sintéticos com distribuição realista:

| Campo | Tipo | Geração |
|-------|------|---------|
| tenant_id | varchar | Aleatório entre T1-T50 |
| status | varchar | ATIVO (90%) ou INATIVO (10%) |
| valor | double | Entre 10.0 e 1000.0 |
| date | timestamp | Distribuído no range de dias |
| created_at | timestamp | localtimestamp |
| updated_at | timestamp | localtimestamp |
| document | varchar (JSON) | Documento sintético em JSON |
| surrogate_key | varchar | SK00000001, SK00000002, ... |

## Exemplos de Uso

### Cenário 1: Teste de Consultas Leves

Gerar dataset pequeno para consultas que devem ir para cluster small:

```bash
./generate_data.py --records 50000 --days 30 --output load-small-test.sql
```

**Uso esperado:** Queries que processam poucos dias (< 1 semana) resultarão em score < 0.3

### Cenário 2: Teste de Consultas Intermediárias

Gerar dataset médio para consultas que devem ir para cluster medium:

```bash
./generate_data.py --records 500000 --days 90 --output load-medium-test.sql
```

**Uso esperado:** Queries com JOINs e filtros por mês resultarão em 0.3 <= score <= 0.7

### Cenário 3: Teste de Consultas Pesadas

Gerar dataset grande para consultas que devem ir para cluster large:

```bash
./generate_data.py --size-gb 10 --output load-large-test.sql
```

**Uso esperado:** Queries com subconsultas e sem filtros de data resultarão em score > 0.7

### Cenário 4: Validação Temporal

Gerar dataset com 1 ano de histórico para testar filtros temporais:

```bash
./generate_data.py \
  --records 2000000 \
  --days 365 \
  --start-date 2023-01-01 \
  --batch 5000 \
  --output load-yearly.sql
```

## Carregar Dados Gerados

### Método 1: Via CLI do Trino

```bash
# Copiar arquivo para container
docker cp load-iceberg-generated.sql trino-small:/tmp/

# Executar no Trino
docker compose exec trino-small trino \
  --server http://localhost:8080 \
  --user admin \
  --file /tmp/load-iceberg-generated.sql
```

### Método 2: Via Trino CLI Externo

```bash
trino \
  --server http://localhost:8080 \
  --user admin \
  --catalog iceberg \
  --schema analytics \
  --file load-iceberg-generated.sql
```

### Método 3: Via Batch (para datasets grandes)

Para datasets muito grandes (> 5GB), é recomendado dividir em arquivos menores:

```bash
# Gerar dataset de 10 GB
./generate_data.py --size-gb 10 --batch 10000 --output load-10gb.sql

# Dividir em arquivos de 1 GB cada
split -l 250000 load-10gb.sql load-part-

# Carregar cada parte
for file in load-part-*; do
    echo "Carregando $file..."
    trino --server http://localhost:8080 --user admin --file $file
done
```

## Estimativas de Tamanho

| Registros | Tamanho SQL | Tempo Geração | Tempo Carga | Tamanho Iceberg |
|-----------|-------------|---------------|-------------|-----------------|
| 50.000 | ~10 MB | 5s | ~30s | ~100 MB |
| 180.000 | ~36 MB | 15s | ~2 min | ~400 MB |
| 500.000 | ~100 MB | 45s | ~5 min | ~1 GB |
| 1.000.000 | ~200 MB | 1.5 min | ~10 min | ~2 GB |
| 5.000.000 | ~1 GB | 8 min | ~50 min | ~10 GB |
| 10.000.000 | ~2 GB | 15 min | ~2h | ~20 GB |

**Nota:** Tempos são aproximados e dependem do hardware.

## Formato do Documento JSON

Cada registro contém um campo `document` em formato JSON:

```json
{
  "origem": "sintetico",
  "versao": "1.0",
  "metadados": {
    "gerado_em": "2026-09-13T11:00:00",
    "tipo": "A"
  }
}
```

Este campo pode ser usado para:
- Testes de funções JSON do Trino
- Análise de dados semi-estruturados
- Simulação de dados de origem externa

## Distribuição dos Dados

### Distribuição Temporal

Os dados são distribuídos uniformemente ao longo do range de dias especificado.

Exemplo com 90 dias:
- **Dia 1:** ~2.000 registros
- **Dia 45:** ~2.000 registros
- **Dia 90:** ~2.000 registros

### Distribuição por Tenant

Distribuição uniforme entre 50 tenants:
- Cada tenant recebe aproximadamente 1/50 dos registros
- Para 180k registros: ~3.600 registros por tenant

### Distribuição de Status

- **ATIVO:** 90% dos registros
- **INATIVO:** 10% dos registros

### Distribuição de Valores

Valores monetários seguem distribuição uniforme entre 10.0 e 1000.0.

## Performance e Otimização

### Para Geração Rápida

```bash
# Use batch size maior para datasets grandes
./generate_data.py --records 5000000 --batch 10000
```

### Para Carga Rápida

1. **Aumentar paralelismo do Trino:**
   ```properties
   # config.properties
   task.max-worker-threads=16
   ```

2. **Usar múltiplas conexões:**
   ```bash
   # Dividir dataset e carregar em paralelo
   split -n 4 load-large.sql load-part-
   for file in load-part-*; do
       trino --server http://localhost:8080 --user admin --file $file &
   done
   wait
   ```

3. **Ajustar batch size:**
   ```bash
   # Batches maiores = menos INSERTs, mais memória
   ./generate_data.py --records 1000000 --batch 5000
   ```

## Validação dos Dados

Após carregar, validar com:

```sql
-- Contar registros
SELECT COUNT(*) FROM iceberg.analytics.dados;

-- Verificar range de datas
SELECT 
    MIN(date) as data_inicial,
    MAX(date) as data_final,
    COUNT(DISTINCT DATE(date)) as dias_unicos
FROM iceberg.analytics.dados;

-- Verificar distribuição de status
SELECT 
    status,
    COUNT(*) as total,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentual
FROM iceberg.analytics.dados
GROUP BY status;

-- Verificar distribuição por tenant
SELECT 
    COUNT(DISTINCT tenant_id) as tenants_unicos,
    AVG(registros_por_tenant) as media_por_tenant,
    MIN(registros_por_tenant) as minimo,
    MAX(registros_por_tenant) as maximo
FROM (
    SELECT tenant_id, COUNT(*) as registros_por_tenant
    FROM iceberg.analytics.dados
    GROUP BY tenant_id
);
```

## Troubleshooting

### Erro: "Out of Memory" durante geração

**Solução:** Usar batch size menor

```bash
./generate_data.py --records 5000000 --batch 500
```

### Erro: "Transaction timeout" durante carga

**Solução:** Dividir em arquivos menores ou aumentar timeout

```bash
# Dividir dataset
split -l 100000 load-large.sql load-chunk-

# Ajustar timeout do Trino (config.properties)
query.max-execution-time=30m
```

### Dataset muito lento para carregar

**Solução:** Verificar se o MinIO está lento ou usar batch maior

```bash
# Verificar status do MinIO
docker compose logs minio

# Usar batch maior
./generate_data.py --records 1000000 --batch 10000
```

## Scripts Úteis

### Limpar dados existentes

```sql
-- Limpar tabela dados
TRUNCATE TABLE iceberg.analytics.dados;

-- Verificar
SELECT COUNT(*) FROM iceberg.analytics.dados;
```

### Regenerar com seed para reprodutibilidade

Adicionar seed ao script Python:

```python
# No início do main()
import random
random.seed(42)
```

### Gerar múltiplos datasets

```bash
#!/bin/bash
# gerar-datasets-testes.sh

# Small test
./generate_data.py --records 50000 --days 7 --output load-small.sql

# Medium test
./generate_data.py --records 500000 --days 30 --output load-medium.sql

# Large test
./generate_data.py --size-gb 5 --output load-large.sql

echo "Todos os datasets gerados!"
```

## Integração com Testes

### Teste 1: Verificar Roteamento para Small

```bash
# Gerar dataset pequeno
./generate_data.py --records 10000 --days 1

# Carregar
trino --server http://localhost:8080 --user admin --file load-iceberg-generated.sql

# Testar query (esperado: score < 0.3, cluster small)
echo "SELECT COUNT(*) FROM iceberg.analytics.dados WHERE date = DATE '2024-01-01'" | \
  curl -X POST http://localhost:5001/api/v1/route \
    -H "Content-Type: application/json" \
    -d @-
```

### Teste 2: Verificar Roteamento para Medium

```bash
# Gerar dataset médio
./generate_data.py --records 500000 --days 90

# Query com JOIN (esperado: 0.3 <= score <= 0.7, cluster medium)
# Ver query.sql linha 49-67
```

### Teste 3: Verificar Roteamento para Large

```bash
# Gerar dataset grande
./generate_data.py --size-gb 5

# Query complexa (esperado: score > 0.7, cluster large)
# Ver query.sql linha 109-131
```

---

**Documentação completa:** [src/README.md](../README.md)  
**Scripts relacionados:** [scripts/](.)  
**Queries de teste:** [query.sql](../query.sql)
