EXPLAIN (TYPE IO)
SELECT t.tenant_id, t.categoria, COUNT(*) AS total_registros,
       SUM(d.valor) AS valor_total, AVG(d.valor) AS valor_medio
FROM iceberg.analytics.dados d
JOIN iceberg.analytics.tenant_info t ON d.tenant_id = t.tenant_id
WHERE d.date >= TIMESTAMP '2024-01-01'
  AND d.date < TIMESTAMP '2024-02-01'
  AND d.status = 'ATIVO'
  AND t.categoria IN (
      SELECT categoria FROM iceberg.analytics.tenant_info
      WHERE nivel > (SELECT AVG(nivel) FROM iceberg.analytics.tenant_info)
  )
GROUP BY t.tenant_id, t.categoria
HAVING COUNT(*) > 100
ORDER BY valor_total DESC
LIMIT 50
