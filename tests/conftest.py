"""Fixtures compartilhadas para testes do DyraSQL Core."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "src" / "dyrasql-core"
if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))

os.environ.setdefault("SAVE_EXPLAINS", "false")
os.environ.setdefault("EXPLAINS_DIR", "/tmp/dyrasql-explains-test")
os.environ.setdefault("LOG_LEVEL", "WARNING")


@pytest.fixture(scope="session", autouse=True)
def _patch_postgres_and_sleep():
    """Evita retries lentos ao importar HistoryManager/app durante a suite."""
    mock_conn = MagicMock()
    mock_conn.closed = 0
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_conn.cursor.return_value = mock_cursor
    with patch("psycopg2.connect", return_value=mock_conn):
        with patch("time.sleep"):
            yield


@pytest.fixture
def mock_history_manager():
    hm = MagicMock()
    hm.get_historical_factor.return_value = 0.5
    hm.get_cached_decision.return_value = None
    hm.save_decision.return_value = None
    hm.save_metrics.return_value = None
    hm.clear_cache.return_value = 0
    return hm


@pytest.fixture
def article_metadata():
    """Metadados do exemplo da monografia: Te=1.25 GB, Re=2_500_000."""
    size_bytes = int(1.25 * (1024**3))
    return {
        "iceberg.analytics.dados": {
            "total_size_bytes": size_bytes,
            "total_records": 2_500_000,
        }
    }


@pytest.fixture
def article_complexity():
    """Complexidade do exemplo da monografia."""
    return {
        "joins": 1,
        "aggregations": 3,
        "subqueries": 2,
        "partitioned_filters": 1,
        "non_partitioned_filters": 2,
    }


@pytest.fixture
def mock_pg_connection():
    """Conexao PostgreSQL mockada para HistoryManager."""
    conn = MagicMock()
    conn.closed = 0
    cursor = MagicMock()
    cursor.fetchone.return_value = None
    cursor.rowcount = 0
    conn.cursor.return_value = cursor
    return conn, cursor


@pytest.fixture
def history_manager_no_db(mock_pg_connection):
    """HistoryManager sem conexao real (conn=None)."""
    with patch("history_manager.psycopg2.connect", side_effect=Exception("no db")):
        with patch("history_manager.time.sleep"):
            from history_manager import HistoryManager

            hm = HistoryManager()
            hm.conn = None
            return hm


@pytest.fixture
def history_manager_with_cursor(mock_pg_connection):
    """HistoryManager com cursor mockado."""
    conn, cursor = mock_pg_connection
    with patch("history_manager.psycopg2.connect", return_value=conn):
        with patch("history_manager.time.sleep"):
            from history_manager import HistoryManager

            hm = HistoryManager()
            hm.conn = conn
            yield hm, cursor
