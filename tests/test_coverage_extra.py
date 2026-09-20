"""Testes extras para elevar cobertura do HistoryManager e QueryAnalyzer."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from history_manager import HistoryManager
from query_analyzer import QueryAnalyzer


def test_history_save_metrics_no_connection():
    with patch("history_manager.psycopg2.connect", side_effect=Exception("x")):
        with patch("history_manager.time.sleep"):
            hm = HistoryManager()
    hm.conn = None
    hm.save_metrics({"fingerprint": "fp"})


def test_history_get_cached_invalid_json_factors():
    conn = MagicMock()
    conn.closed = 0
    cursor = MagicMock()
    cursor.fetchone.return_value = {
        "cluster": "small",
        "score": 0.1,
        "factors": "{not-json",
        "created_at": None,
    }
    conn.cursor.return_value = cursor
    with patch("history_manager.psycopg2.connect", return_value=conn):
        with patch("history_manager.time.sleep"):
            hm = HistoryManager()
    hm.conn = conn
    result = hm.get_cached_decision("fp")
    assert result["factors"] == {}


def test_history_query_errors():
    conn = MagicMock()
    conn.closed = 0
    cursor = MagicMock()
    cursor.execute.side_effect = Exception("db error")
    conn.cursor.return_value = cursor
    with patch("history_manager.psycopg2.connect", return_value=conn):
        with patch("history_manager.time.sleep"):
            hm = HistoryManager()
    hm.conn = conn
    assert hm.get_cached_decision("fp") is None
    hm.save_decision("fp", {"cluster": "small", "score": 0.1, "factors": {}})
    hm.save_metrics({"fingerprint": "fp"})
    assert hm.get_historical_factor("fp", "q") == 0.5
    assert hm.clear_cache() == 0


def test_execute_trino_with_next_uri(monkeypatch):
    monkeypatch.setenv("SAVE_EXPLAINS", "false")
    analyzer = QueryAnalyzer()

    first = MagicMock()
    first.status_code = 200
    first.json.return_value = {
        "columns": [],
        "data": [["a"]],
        "nextUri": "http://trino/next",
        "stats": {"state": "RUNNING"},
    }
    second = MagicMock()
    second.status_code = 200
    second.json.return_value = {
        "data": [["b"]],
        "stats": {"state": "FINISHED"},
        "nextUri": None,
    }
    with patch("query_analyzer.requests.post", return_value=first):
        with patch("query_analyzer.requests.get", return_value=second):
            result = analyzer._execute_trino_query("SELECT 1")
    assert result["data"] == [["a"], ["b"]]


def test_execute_trino_query_error_in_json(monkeypatch):
    monkeypatch.setenv("SAVE_EXPLAINS", "false")
    analyzer = QueryAnalyzer()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"error": {"message": "bad sql"}}
    with patch("query_analyzer.requests.post", return_value=resp):
        result = analyzer._execute_trino_query("SELECT bad")
    assert result["error"] == "bad sql"


def test_explain_io_json_decode_error(monkeypatch):
    monkeypatch.setenv("SAVE_EXPLAINS", "false")
    analyzer = QueryAnalyzer()
    with patch.object(
        analyzer,
        "_execute_trino_query",
        return_value={"data": [["not-json{"]]},
    ):
        with patch.object(analyzer, "_save_explain") as save:
            assert analyzer.explain_io("SELECT 1") is None
            save.assert_called()


def test_parse_explain_safe_float_nan(monkeypatch):
    monkeypatch.setenv("SAVE_EXPLAINS", "false")
    analyzer = QueryAnalyzer()
    parsed = analyzer._parse_explain_io(
        {
            "inputTableColumnInfos": [
                {
                    "table": {
                        "catalog": "iceberg",
                        "schemaTable": {"schema": "s", "table": "t"},
                    },
                    "constraint": {"columnConstraints": []},
                    "estimate": {
                        "outputRowCount": "NaN",
                        "outputSizeInBytes": None,
                        "cpuCost": "x",
                    },
                }
            ]
        }
    )
    assert parsed["total_rows"] == 0.0
