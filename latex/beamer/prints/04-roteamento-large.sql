SELECT t.tenant_id,
       t.categoria,
       COUNT(d.document) AS total,
       SUM(length(d.document)) AS bytes_documento,
       AVG(d.valor) AS media,
       MAX(d.valor) AS maximo,
       MIN(d.valor) AS minimo,
       STDDEV(d.valor) AS desvio
FROM iceberg.analytics.dados d
JOIN iceberg.analytics.tenant_info t
  ON d.tenant_id = t.tenant_id
WHERE d.status = 'ATIVO'
  AND t.categoria IN (
      SELECT categoria
      FROM iceberg.analytics.tenant_info
      WHERE nivel > (
          SELECT AVG(nivel)
          FROM iceberg.analytics.tenant_info
      )
  )
GROUP BY t.tenant_id, t.categoria
HAVING COUNT(*) > 1000;
