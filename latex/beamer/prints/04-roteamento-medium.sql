SELECT t.tenant_id,
       t.categoria,
       COUNT(d.document) AS total,
       SUM(length(d.document)) AS bytes_documento,
       AVG(d.valor) AS media,
       MAX(d.valor) AS maximo,
       MIN(d.valor) AS minimo
FROM iceberg.analytics.dados d
JOIN iceberg.analytics.tenant_info t
  ON d.tenant_id = t.tenant_id
WHERE d.status = 'ATIVO'
GROUP BY t.tenant_id, t.categoria
HAVING COUNT(*) > 1000;
