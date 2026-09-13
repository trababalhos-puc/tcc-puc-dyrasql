#!/bin/bash
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE USER dyrasql WITH PASSWORD 'dyrasql';
    CREATE DATABASE dyrasql OWNER dyrasql;
EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname dyrasql <<-EOSQL
    CREATE TABLE routing_decisions (
        fingerprint VARCHAR(64) PRIMARY KEY,
        cluster VARCHAR(32) NOT NULL,
        score DOUBLE PRECISION NOT NULL,
        factors JSONB NOT NULL DEFAULT '{}'::jsonb,
        success BOOLEAN,
        execution_time DOUBLE PRECISION,
        cost DOUBLE PRECISION,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ,
        expires_at TIMESTAMPTZ NOT NULL
    );
    CREATE INDEX idx_routing_expires_at ON routing_decisions (expires_at);
    GRANT ALL PRIVILEGES ON TABLE routing_decisions TO dyrasql;
    GRANT USAGE ON SCHEMA public TO dyrasql;
EOSQL
