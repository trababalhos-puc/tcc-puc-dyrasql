INSERT INTO iceberg.analytics.tenant_info
SELECT
    'T' || CAST(n AS varchar),
    CASE
        WHEN n % 3 = 0 THEN 'A'
        WHEN n % 3 = 1 THEN 'B'
        ELSE 'C'
    END,
    1 + (n % 10)
FROM UNNEST(SEQUENCE(1, 50)) AS t(n);

INSERT INTO iceberg.analytics.dados
SELECT
    'T' || CAST(1 + (n % 50) AS varchar),
    CASE WHEN n % 10 = 0 THEN 'INATIVO' ELSE 'ATIVO' END,
    10.0 + (n % 1000),
    CAST(date '2024-01-01' + INTERVAL '1' DAY * (n % 90) AS timestamp(6)),
    localtimestamp,
    localtimestamp,
    '{"origem":"sintetico"}',
    CAST(n AS varchar)
FROM UNNEST(SEQUENCE(1, 180000)) AS t(n);
