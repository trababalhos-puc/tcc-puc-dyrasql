-- ======================================================================
-- DyraSQL - Queries de Teste
-- ======================================================================
-- Este arquivo contém consultas de diferentes complexidades para testar
-- o sistema de roteamento dinâmico
-- ======================================================================

-- ======================================================================
-- 1. CONSULTAS SIMPLES (Esperado: cluster SMALL, score < 0.3)
-- ======================================================================

-- 1.1. Count simples
SELECT COUNT(*) as total_registros
FROM iceberg.analytics.dados;

-- 1.2. Select com filtro em coluna particionada (dia específico)
SELECT tenant_id, status, valor
FROM iceberg.analytics.dados
WHERE date = TIMESTAMP '2024-01-15'
LIMIT 10;

-- 1.3. Agregação simples
SELECT status, COUNT(*) as total
FROM iceberg.analytics.dados
WHERE date BETWEEN TIMESTAMP '2024-01-01' AND TIMESTAMP '2024-01-07'
GROUP BY status;

-- 1.4. Metadados (sempre vai para small)
SHOW SCHEMAS IN iceberg;
SHOW TABLES IN iceberg.analytics;
DESCRIBE iceberg.analytics.dados;


-- ======================================================================
-- 2. CONSULTAS INTERMEDIÁRIAS (Esperado: cluster MEDIUM, 0.3 <= score <= 0.7)
-- ======================================================================

-- 2.1. Join com agregação (exemplo do artigo)
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

-- 2.2. Join com múltiplas agregações
SELECT 
    t.tenant_id,
    t.categoria,
    COUNT(*) as total,
    SUM(d.valor) as soma,
    AVG(d.valor) as media
FROM iceberg.analytics.dados d
JOIN iceberg.analytics.tenant_info t ON d.tenant_id = t.tenant_id
WHERE d.date >= TIMESTAMP '2024-01-01'
  AND d.date < TIMESTAMP '2024-01-15'
GROUP BY t.tenant_id, t.categoria;

-- 2.3. Análise por período com join
SELECT 
    DATE_TRUNC('day', d.date) as dia,
    t.categoria,
    COUNT(*) as transacoes,
    SUM(d.valor) as valor_total
FROM iceberg.analytics.dados d
JOIN iceberg.analytics.tenant_info t ON d.tenant_id = t.tenant_id
WHERE d.date >= TIMESTAMP '2024-01-01'
  AND d.status = 'ATIVO'
GROUP BY DATE_TRUNC('day', d.date), t.categoria
ORDER BY dia, categoria;


-- ======================================================================
-- 3. CONSULTAS COMPLEXAS (Esperado: cluster LARGE, score > 0.7)
-- ======================================================================

-- 3.1. Query com subconsultas (exemplo do artigo)
SELECT 
    t.tenant_id,
    t.categoria,
    COUNT(*) as total_registros,
    SUM(d.valor) as valor_total,
    AVG(d.valor) as valor_medio
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
HAVING COUNT(*) > 100
ORDER BY valor_total DESC
LIMIT 50;

-- 3.2. Análise estatística completa
SELECT 
    t.tenant_id,
    t.categoria,
    COUNT(*) as total,
    SUM(d.valor) as valor_total,
    AVG(d.valor) as media,
    MAX(d.valor) as maximo,
    MIN(d.valor) as minimo,
    STDDEV(d.valor) as desvio_padrao,
    APPROX_PERCENTILE(d.valor, 0.5) as mediana
FROM iceberg.analytics.dados d
JOIN iceberg.analytics.tenant_info t ON d.tenant_id = t.tenant_id
WHERE d.date >= TIMESTAMP '2024-01-01'
  AND d.status = 'ATIVO'
GROUP BY t.tenant_id, t.categoria
HAVING COUNT(*) > 50
ORDER BY valor_total DESC;

-- 3.3. Window functions com múltiplas agregações
SELECT 
    t.tenant_id,
    t.categoria,
    DATE_TRUNC('day', d.date) as dia,
    SUM(d.valor) as valor_dia,
    SUM(SUM(d.valor)) OVER (PARTITION BY t.tenant_id ORDER BY DATE_TRUNC('day', d.date)) as acumulado,
    AVG(d.valor) OVER (PARTITION BY t.categoria) as media_categoria
FROM iceberg.analytics.dados d
JOIN iceberg.analytics.tenant_info t ON d.tenant_id = t.tenant_id
WHERE d.date >= TIMESTAMP '2024-01-01'
  AND d.date < TIMESTAMP '2024-02-01'
GROUP BY t.tenant_id, t.categoria, DATE_TRUNC('day', d.date), d.valor
ORDER BY t.tenant_id, dia;


-- ======================================================================
-- 4. TESTES DE CACHE
-- ======================================================================
-- Execute a mesma query duas vezes para verificar cache hit

-- 4.1. Primeira execução (cache miss - será analisada)
SELECT 
    t.tenant_id,
    COUNT(*) as total
FROM iceberg.analytics.dados d
JOIN iceberg.analytics.tenant_info t ON d.tenant_id = t.tenant_id
WHERE d.date >= TIMESTAMP '2024-01-01'
GROUP BY t.tenant_id;

-- 4.2. Segunda execução (cache hit - reutiliza decisão)
-- Execute a mesma query acima novamente e veja nos logs que foi cache hit


-- ======================================================================
-- 5. TESTES DE FILTROS PARTICIONADOS
-- ======================================================================

-- 5.1. Filtro em coluna particionada (day(date))
-- Deve ter factor de complexidade diferente por ser particionado
SELECT COUNT(*) as total
FROM iceberg.analytics.dados
WHERE date >= TIMESTAMP '2024-01-01'
  AND date < TIMESTAMP '2024-01-02';

-- 5.2. Filtro em coluna não-particionada
-- Fator de complexidade maior
SELECT COUNT(*) as total
FROM iceberg.analytics.dados
WHERE status = 'ATIVO'
  AND valor > 500;


-- ======================================================================
-- 6. ANÁLISE DE EXPLAIN (TYPE IO)
-- ======================================================================
-- Não use estas queries diretamente, elas servem apenas como referência
-- O DyraSQL executa automaticamente o EXPLAIN para cada query

-- Exemplo do que o sistema executa internamente:
-- EXPLAIN (TYPE IO)
-- SELECT * FROM iceberg.analytics.dados WHERE date = TIMESTAMP '2024-01-15';

-- Os resultados são salvos em: ./explains/*.json


-- ======================================================================
-- 7. VERIFICAR ROTEAMENTO
-- ======================================================================
-- Use os scripts de monitoramento em paralelo:
--
-- Terminal 1: Execute uma query acima
-- Terminal 2: ./scripts/monitor-routing.sh
--
-- Ou consulte diretamente o cache:

-- Query para ver decisões no cache
-- (execute no PostgreSQL do gateway-db)
-- SELECT 
--     fingerprint,
--     cluster,
--     score,
--     factors,
--     created_at,
--     expires_at
-- FROM routing_decisions
-- ORDER BY created_at DESC
-- LIMIT 10;


-- ======================================================================
-- FIM
-- ======================================================================
