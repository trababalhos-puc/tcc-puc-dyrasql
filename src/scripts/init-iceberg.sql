CREATE SCHEMA IF NOT EXISTS iceberg.analytics;

CREATE TABLE IF NOT EXISTS iceberg.analytics.tenant_info (
    tenant_id varchar,
    categoria varchar,
    nivel integer
);

CREATE TABLE IF NOT EXISTS iceberg.analytics.dados (
    tenant_id varchar,
    status varchar,
    valor double,
    date timestamp(6),
    created_at timestamp(6),
    updated_at timestamp(6),
    document varchar,
    surrogate_key varchar
)
WITH (
    partitioning = ARRAY['day(date)'],
    format = 'PARQUET'
);
