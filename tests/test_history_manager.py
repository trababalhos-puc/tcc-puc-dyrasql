"""Testes do HistoryManager com mocks de PostgreSQL."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from history_manager import HistoryManager


def _make_hm(conn=None):
    with patch("history_manager.psycopg2.connect", side_effect=Exception("skip")):
        with patch("history_manager.time.sleep"):
            hm = HistoryManager()
    hm.conn = conn
    if conn is None:
        hm._cursor = lambda: None
    return hm


def test_historical_factor_default_without_connection():
    hm = _make_hm(conn=None)
    assert hm.get_historical_factor("fp", "SELECT 1") == 0.5


def test_historical_factor_miss(history_manager_with_cursor):
    hm, cursor = history_manager_with_cursor
    cursor.fetchone.return_value = None
    assert hm.get_historical_factor("fp", "q") == 0.5


def test_historical_factor_success(history_manager_with_cursor):
    hm, cursor = history_manager_with_cursor
    cursor.fetchone.return_value = {"score": 0.44, "success": True}
    assert hm.get_historical_factor("fp", "q") == 0.44


def test_historical_factor_failure(history_manager_with_cursor):
    hm, cursor = history_manager_with_cursor
    cursor.fetchone.return_value = {"score": 0.44, "success": False}
    assert abs(hm.get_historical_factor("fp", "q") - (1.0 - 0.44)) < 1e-9


def test_get_cached_decision_hit(history_manager_with_cursor):
    hm, cursor = history_manager_with_cursor
    ts = datetime.now(timezone.utc)
    cursor.fetchone.return_value = {
        "cluster": "medium",
        "score": 0.44,
        "factors": {"volume": 0.27},
        "created_at": ts,
    }
    result = hm.get_cached_decision("fp")
    assert result["cluster"] == "medium"
    assert result["score"] == 0.44
    assert result["factors"]["volume"] == 0.27


def test_get_cached_decision_miss(history_manager_with_cursor):
    hm, cursor = history_manager_with_cursor
    cursor.fetchone.return_value = None
    assert hm.get_cached_decision("fp") is None


def test_get_cached_decision_no_connection():
    hm = _make_hm(conn=None)
    assert hm.get_cached_decision("fp") is None


def test_save_decision(history_manager_with_cursor):
    hm, cursor = history_manager_with_cursor
    hm.save_decision("fp", {"cluster": "small", "score": 0.1, "factors": {}})
    cursor.execute.assert_called()


def test_save_decision_no_connection():
    hm = _make_hm(conn=None)
    hm.save_decision("fp", {"cluster": "small", "score": 0.1, "factors": {}})


def test_save_metrics(history_manager_with_cursor):
    hm, cursor = history_manager_with_cursor
    hm.save_metrics(
        {
            "fingerprint": "fp",
            "execution_time": 1.2,
            "cost": 0.5,
            "success": True,
        }
    )
    cursor.execute.assert_called()


def test_clear_cache(history_manager_with_cursor):
    hm, cursor = history_manager_with_cursor
    cursor.rowcount = 3
    assert hm.clear_cache() == 3


def test_clear_cache_no_connection():
    hm = _make_hm(conn=None)
    assert hm.clear_cache() == 0


def test_get_cached_decision_factors_as_string(history_manager_with_cursor):
    hm, cursor = history_manager_with_cursor
    cursor.fetchone.return_value = {
        "cluster": "large",
        "score": 0.8,
        "factors": '{"volume": 0.9}',
        "created_at": None,
    }
    result = hm.get_cached_decision("fp")
    assert result["factors"]["volume"] == 0.9


def test_cursor_reconnects_when_closed():
    conn = MagicMock()
    conn.closed = 1
    new_conn = MagicMock()
    new_conn.closed = 0
    cursor = MagicMock()
    new_conn.cursor.return_value = cursor

    with patch("history_manager.psycopg2.connect", return_value=new_conn):
        with patch("history_manager.time.sleep"):
            hm = HistoryManager()
            hm.conn = conn
            result = hm._cursor()
    assert result is cursor
