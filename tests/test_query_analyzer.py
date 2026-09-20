"""Testes do QueryAnalyzer."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from query_analyzer import QueryAnalyzer


@pytest.fixture
def analyzer(tmp_path, monkeypatch):
    monkeypatch.setenv("SAVE_EXPLAINS", "false")
    monkeypatch.setenv("PARTITION_COLUMNS", "date")
    return QueryAnalyzer()


def test_fingerprint_stable_across_literals(analyzer):
    q1 = "SELECT * FROM dados WHERE id = 123 AND name = 'alice'"
    q2 = "SELECT * FROM dados WHERE id = 456 AND name = 'bob'"
    assert analyzer.generate_fingerprint(q1) == analyzer.generate_fingerprint(q2)


def test_fingerprint_differs_for_structure(analyzer):
    q1 = "SELECT * FROM dados WHERE id = 1"
    q2 = "SELECT * FROM dados JOIN other ON dados.id = other.id WHERE id = 1"
    assert analyzer.generate_fingerprint(q1) != analyzer.generate_fingerprint(q2)


def test_analyze_complexity_counts(analyzer):
    query = """
    SELECT d.categoria, COUNT(*), SUM(d.valor), AVG(d.valor)
    FROM iceberg.analytics.dados d
    JOIN iceberg.analytics.tenant_info t ON d.tenant_id = t.tenant_id
    WHERE d.date >= TIMESTAMP '2024-01-01'
      AND d.date < TIMESTAMP '2024-02-01'
      AND d.categoria = 'A'
      AND t.status = 'active'
      AND d.id IN (SELECT id FROM iceberg.analytics.filtro WHERE ativo = true)
      AND EXISTS (SELECT 1 FROM iceberg.analytics.extra e WHERE e.id = d.id)
    GROUP BY d.categoria
    """
    complexity = analyzer.analyze_complexity(query)
    assert complexity["joins"] >= 1
    assert complexity["aggregations"] >= 3
    assert complexity["subqueries"] >= 1
    assert complexity["partitioned_filters"] >= 1
    assert complexity["non_partitioned_filters"] >= 1


def test_analyze_complexity_invalid_sql(analyzer):
    result = analyzer.analyze_complexity("NOT A VALID SQL !!!")
    assert result["joins"] == 0
    assert result["aggregations"] == 0


def test_extract_where_clause(analyzer):
    where = analyzer._extract_where_clause("SELECT * FROM t WHERE a = 1 AND b = 2 GROUP BY a")
    assert where is not None
    assert "a = 1" in where.lower() or "a = 1" in where


def test_extract_where_clause_absent(analyzer):
    assert analyzer._extract_where_clause("SELECT * FROM t") is None


def test_normalize_query_adds_iceberg_catalog(analyzer):
    normalized = analyzer._normalize_query_with_catalog(
        "SELECT * FROM analytics.dados WHERE id = 1"
    )
    assert "iceberg.analytics.dados" in normalized.lower()


def test_parse_explain_io(analyzer):
    explain_json = {
        "inputTableColumnInfos": [
            {
                "table": {
                    "catalog": "iceberg",
                    "schemaTable": {"schema": "analytics", "table": "dados"},
                },
                "constraint": {
                    "columnConstraints": [
                        {
                            "columnName": "date",
                            "domain": {
                                "ranges": [
                                    {
                                        "low": {"value": "2024-01-01", "bound": "ABOVE"},
                                        "high": {"value": "2024-02-01", "bound": "BELOW"},
                                    }
                                ]
                            },
                        }
                    ]
                },
                "estimate": {
                    "outputRowCount": 2500000.0,
                    "outputSizeInBytes": 1.25 * (1024**3),
                    "cpuCost": 100.0,
                },
            }
        ]
    }
    parsed = analyzer._parse_explain_io(explain_json)
    assert parsed["total_rows"] == 2500000.0
    assert abs(parsed["total_size_bytes"] / (1024**3) - 1.25) < 0.01
    assert "iceberg.analytics.dados" in parsed["tables"]


def test_explain_io_success(analyzer):
    explain_payload = {
        "inputTableColumnInfos": [
            {
                "table": {
                    "catalog": "iceberg",
                    "schemaTable": {"schema": "db", "table": "t"},
                },
                "constraint": {"columnConstraints": []},
                "estimate": {
                    "outputRowCount": 100,
                    "outputSizeInBytes": 1024,
                    "cpuCost": 1,
                },
            }
        ]
    }
    trino_result = {
        "columns": [{"name": "Query Plan"}],
        "data": [[json.dumps(explain_payload)]],
        "stats": {"state": "FINISHED"},
    }
    with patch.object(analyzer, "_execute_trino_query", return_value=trino_result):
        with patch.object(analyzer, "_save_explain"):
            result = analyzer.explain_io("SELECT * FROM db.t")
    assert result is not None
    assert result["total_rows"] == 100


def test_explain_io_error(analyzer):
    with patch.object(analyzer, "_execute_trino_query", return_value={"error": "boom"}):
        with patch.object(analyzer, "_save_explain") as save:
            result = analyzer.explain_io("SELECT 1")
    assert result is None
    save.assert_called_once()


def test_explain_io_no_data(analyzer):
    with patch.object(analyzer, "_execute_trino_query", return_value={"data": []}):
        with patch.object(analyzer, "_save_explain"):
            assert analyzer.explain_io("SELECT 1") is None


def test_analyze_query_io_success(analyzer):
    parsed = {
        "tables": {
            "iceberg.db.t": {
                "estimated_size_bytes": 2048,
                "estimated_rows": 50,
                "cpu_cost": 1,
                "filters": [],
            }
        },
        "total_size_bytes": 2048,
        "total_rows": 50,
        "total_cpu_cost": 1,
    }
    with patch.object(analyzer, "explain_io", return_value=parsed):
        result = analyzer.analyze_query_io("SELECT * FROM db.t WHERE x = 1")
    assert result["total_rows"] == 50
    assert "iceberg.db.t" in result["tables"]
    assert result["tables"]["iceberg.db.t"]["total_records"] == 50


def test_analyze_query_io_failure(analyzer):
    with patch.object(analyzer, "explain_io", return_value=None):
        result = analyzer.analyze_query_io("SELECT 1")
    assert result["tables"] == {}
    assert result["total_size_bytes"] == 0


def test_extract_tables_fallback(analyzer):
    with patch.object(analyzer, "explain_io", return_value=None):
        tables = analyzer.extract_tables("SELECT * FROM analytics.dados JOIN other o ON 1=1")
    assert "analytics.dados" in tables or "dados" in tables or len(tables) >= 1


def test_extract_tables_from_explain(analyzer):
    with patch.object(
        analyzer,
        "explain_io",
        return_value={"tables": {"iceberg.db.t": {}}},
    ):
        assert analyzer.extract_tables("SELECT 1") == ["iceberg.db.t"]


def test_execute_trino_query_http_error(analyzer):
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "error"
    with patch("query_analyzer.requests.post", return_value=mock_resp):
        result = analyzer._execute_trino_query("SELECT 1")
    assert result["status_code"] == 500


def test_execute_trino_query_success(analyzer):
    first = MagicMock()
    first.status_code = 200
    first.json.return_value = {
        "columns": [],
        "data": [["row"]],
        "stats": {"state": "FINISHED"},
        "nextUri": None,
    }
    with patch("query_analyzer.requests.post", return_value=first):
        result = analyzer._execute_trino_query("SELECT 1")
    assert result["data"] == [["row"]]


def test_execute_trino_query_exception(analyzer):
    with patch("query_analyzer.requests.post", side_effect=Exception("network")):
        assert analyzer._execute_trino_query("SELECT 1") is None


def test_save_explain_writes_file(tmp_path, monkeypatch):
    monkeypatch.setenv("SAVE_EXPLAINS", "true")
    monkeypatch.setenv("EXPLAINS_DIR", str(tmp_path))
    analyzer = QueryAnalyzer()
    analyzer._save_explain(
        "SELECT 1",
        {"raw": {}, "error": None},
        {"tables": {}, "total_size_bytes": 0, "total_rows": 0, "total_cpu_cost": 0},
    )
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
