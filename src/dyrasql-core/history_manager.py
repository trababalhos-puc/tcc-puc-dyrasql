#!/usr/bin/env python3
"""
History Manager - cache e historico de consultas no PostgreSQL
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone

import psycopg2
from psycopg2.extras import Json, RealDictCursor

logger = logging.getLogger(__name__)


class HistoryManager:
    """Gerencia historico e cache de decisoes no PostgreSQL"""

    def __init__(self):
        self.cache_ttl_hours = 24
        self.conn = None
        self._connect_with_retry()

    def _connect_with_retry(self, attempts=10, delay_seconds=2):
        host = os.getenv("POSTGRES_HOST", "gateway-db")
        port = int(os.getenv("POSTGRES_PORT", "5432"))
        dbname = os.getenv("POSTGRES_DB", "dyrasql")
        user = os.getenv("POSTGRES_USER", "dyrasql")
        password = os.getenv("POSTGRES_PASSWORD", "dyrasql")

        last_error = None
        for attempt in range(1, attempts + 1):
            try:
                self.conn = psycopg2.connect(
                    host=host,
                    port=port,
                    dbname=dbname,
                    user=user,
                    password=password,
                )
                self.conn.autocommit = True
                logger.info("Conectado ao PostgreSQL: %s/%s", host, dbname)
                return
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Tentativa %s/%s de conexao ao PostgreSQL falhou: %s",
                    attempt,
                    attempts,
                    exc,
                )
                time.sleep(delay_seconds)

        logger.error("Erro ao conectar ao PostgreSQL: %s", last_error)
        self.conn = None

    def _cursor(self):
        if self.conn is None or self.conn.closed:
            self._connect_with_retry(attempts=3, delay_seconds=1)
        if self.conn is None:
            return None
        return self.conn.cursor(cursor_factory=RealDictCursor)

    def get_cached_decision(self, fingerprint):
        cursor = self._cursor()
        if cursor is None:
            return None

        try:
            cursor.execute(
                """
                SELECT cluster, score, factors, created_at
                FROM routing_decisions
                WHERE fingerprint = %s AND expires_at > NOW()
                  AND (success IS NULL OR success = TRUE)
                """,
                (fingerprint,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            factors = row["factors"] or {}
            if isinstance(factors, str):
                try:
                    factors = json.loads(factors)
                except (json.JSONDecodeError, TypeError):
                    factors = {}

            logger.debug("Cache hit para fingerprint: %s", fingerprint)
            timestamp = row["created_at"]
            return {
                "cluster": row["cluster"],
                "score": float(row["score"] or 0),
                "factors": factors,
                "timestamp": timestamp.isoformat() if timestamp else None,
            }
        except Exception as exc:
            logger.error("Erro ao consultar cache: %s", exc)
            return None
        finally:
            cursor.close()

    def save_decision(self, fingerprint, decision):
        cursor = self._cursor()
        if cursor is None:
            logger.warning("PostgreSQL nao disponivel, nao e possivel salvar decisao")
            return

        try:
            now = datetime.now(timezone.utc)
            expires_at = now + timedelta(hours=self.cache_ttl_hours)
            factors = Json(decision.get("factors", {}))
            cursor.execute(
                """
                INSERT INTO routing_decisions (
                    fingerprint, cluster, score, factors, created_at, expires_at
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (fingerprint) DO UPDATE SET
                    cluster = EXCLUDED.cluster,
                    score = EXCLUDED.score,
                    factors = EXCLUDED.factors,
                    created_at = EXCLUDED.created_at,
                    expires_at = EXCLUDED.expires_at
                """,
                (
                    fingerprint,
                    decision["cluster"],
                    float(decision["score"]),
                    factors,
                    now,
                    expires_at,
                ),
            )
            logger.debug("Decisao salva no cache: %s", fingerprint)
        except Exception as exc:
            logger.error("Erro ao salvar decisao: %s", exc)
        finally:
            cursor.close()

    def save_metrics(self, metrics_data):
        cursor = self._cursor()
        if cursor is None:
            logger.warning("PostgreSQL nao disponivel, nao e possivel salvar metricas")
            return

        try:
            fingerprint = metrics_data["fingerprint"]
            cursor.execute(
                """
                UPDATE routing_decisions
                SET execution_time = %s,
                    cost = %s,
                    success = %s,
                    updated_at = %s
                WHERE fingerprint = %s
                """,
                (
                    metrics_data.get("execution_time", 0),
                    metrics_data.get("cost", 0),
                    metrics_data.get("success", True),
                    datetime.now(timezone.utc),
                    fingerprint,
                ),
            )
            logger.debug("Metricas salvas: %s", fingerprint)
        except Exception as exc:
            logger.error("Erro ao salvar metricas: %s", exc)
        finally:
            cursor.close()

    def _previous_execution(self, fingerprint):
        """Retorna (cluster, score, success) da ultima decisao para o fingerprint."""
        cursor = self._cursor()
        if cursor is None:
            return None
        try:
            cursor.execute(
                """
                SELECT cluster, score, success
                FROM routing_decisions
                WHERE fingerprint = %s
                """,
                (fingerprint,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return row["cluster"], float(row["score"] or 0.5), row["success"]
        except Exception as exc:
            logger.warning("Erro ao consultar historico: %s", exc)
            return None
        finally:
            cursor.close()

    def get_historical_factor(self, fingerprint, query):
        """
        Fator historico:
          - sem historico ou sem resultado registrado: 0,5 (neutro);
          - execucao anterior bem-sucedida: score anterior (reforca a faixa);
          - falha no small ou medium: 1,0 (eleva o score; ver get_minimum_cluster);
          - falha no large: 0,5 (a causa tende a ser outra que nao a capacidade).
        """
        previous = self._previous_execution(fingerprint)
        if previous is None:
            return 0.5
        cluster, previous_score, success = previous
        if success is None:
            return 0.5
        if success:
            return previous_score
        if cluster in ("small", "medium"):
            return 1.0
        return 0.5

    def get_minimum_cluster(self, fingerprint):
        """
        Piso de capacidade apos falha: o novo destino deve ser ao menos o cluster
        imediatamente superior ao que falhou (ou o proprio large, se a falha
        ocorreu nele). Retorna None quando nao ha piso.
        """
        previous = self._previous_execution(fingerprint)
        if previous is None:
            return None
        cluster, _, success = previous
        if success is False:
            # falha no large: mantem o large, pois reduzir a capacidade nao corrige a falha
            return {"small": "medium", "medium": "large", "large": "large"}.get(cluster)
        return None

    def clear_cache(self):
        cursor = self._cursor()
        if cursor is None:
            return 0
        try:
            cursor.execute("DELETE FROM routing_decisions")
            deleted = cursor.rowcount
            logger.info("Cache limpo: %s registros", deleted)
            return deleted
        except Exception as exc:
            logger.error("Erro ao limpar cache: %s", exc)
            return 0
        finally:
            cursor.close()
