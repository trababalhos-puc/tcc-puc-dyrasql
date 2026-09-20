"""Testes da API FastAPI do DyraSQL Core."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "src" / "dyrasql-core"
if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))


@pytest.fixture
def api_client():
    mock_conn = MagicMock()
    mock_conn.closed = 0
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_conn.cursor.return_value = mock_cursor

    with patch("psycopg2.connect", return_value=mock_conn):
        with patch("time.sleep"):
            import app as app_module

            app_module.history_manager.conn = mock_conn
            app_module.history_manager.get_cached_decision = MagicMock(return_value=None)
            app_module.history_manager.save_decision = MagicMock()
            app_module.history_manager.save_metrics = MagicMock()
            app_module.history_manager.get_historical_factor = MagicMock(return_value=0.5)

            client = TestClient(app_module.app)
            yield client, app_module


def test_health(api_client):
    client, _ = api_client
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_route_cache_hit(api_client):
    client, app_module = api_client
    app_module.history_manager.get_cached_decision.return_value = {
        "cluster": "medium",
        "score": 0.44,
        "factors": {"volume": 0.27, "complexity": 0.69, "historical": 0.5},
    }
    response = client.post("/api/v1/route", json={"query": "SELECT 1"})
    assert response.status_code == 200
    data = response.json()
    assert data["cached"] is True
    assert data["cluster"] == "medium"


def test_route_cache_miss(api_client, article_metadata, article_complexity):
    client, app_module = api_client
    app_module.history_manager.get_cached_decision.return_value = None

    with patch.object(
        app_module.query_analyzer,
        "analyze_query_io",
        return_value={
            "tables": {
                "iceberg.analytics.dados": {
                    "total_size_bytes": article_metadata["iceberg.analytics.dados"][
                        "total_size_bytes"
                    ],
                    "total_records": 2_500_000,
                    "cpu_cost": 1,
                    "filters": [],
                }
            },
            "total_size_bytes": article_metadata["iceberg.analytics.dados"]["total_size_bytes"],
            "total_rows": 2_500_000,
        },
    ):
        with patch.object(
            app_module.query_analyzer,
            "analyze_complexity",
            return_value=article_complexity,
        ):
            response = client.post(
                "/api/v1/route",
                json={"query": "SELECT * FROM iceberg.analytics.dados"},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["cached"] is False
    assert data["cluster"] == "medium"
    assert abs(data["score"] - 0.44) < 0.03
    app_module.history_manager.save_decision.assert_called()


def test_route_error(api_client):
    client, app_module = api_client
    app_module.history_manager.get_cached_decision.side_effect = Exception("boom")
    response = client.post("/api/v1/route", json={"query": "SELECT 1"})
    assert response.status_code == 500


def test_save_metrics(api_client):
    client, app_module = api_client
    response = client.post(
        "/api/v1/metrics",
        json={"fingerprint": "abc", "metrics": {"execution_time": 1.0}},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    app_module.history_manager.save_metrics.assert_called()


def test_save_metrics_error(api_client):
    client, app_module = api_client
    app_module.history_manager.save_metrics.side_effect = Exception("fail")
    response = client.post(
        "/api/v1/metrics",
        json={"fingerprint": "abc", "metrics": {}},
    )
    assert response.status_code == 500


def test_get_cluster_url(api_client):
    _, app_module = api_client
    assert "trino-small" in app_module.get_cluster_url("small")
    assert "trino-medium" in app_module.get_cluster_url("medium")
    assert "trino-large" in app_module.get_cluster_url("large")
    assert "trino-small" in app_module.get_cluster_url("unknown")


def test_trino_info_fallback(api_client):
    client, _ = api_client
    with patch("app.requests.get", side_effect=Exception("down")):
        response = client.get("/v1/info")
    assert response.status_code == 200
    assert response.json()["coordinator"] is True


def test_trino_info_proxy(api_client):
    client, _ = api_client
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b'{"nodeId":"x"}'
    mock_resp.headers = {"Content-Type": "application/json"}
    with patch("app.requests.get", return_value=mock_resp):
        response = client.get("/v1/info")
    assert response.status_code == 200


def test_statement_empty_query(api_client):
    client, _ = api_client
    response = client.post("/v1/statement", content=b"   ")
    assert response.status_code == 400


def test_statement_keepalive(api_client):
    client, _ = api_client
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b'{"id":"20260101_000000_00001_abc","nextUri":"http://trino-small:8080/v1/statement/queued"}'
    mock_resp.headers = {"Content-Type": "application/json"}
    with patch("app.requests.post", return_value=mock_resp):
        response = client.post(
            "/v1/statement",
            content=b"SELECT 1",
            headers={"X-Trino-User": "admin"},
        )
    assert response.status_code == 200


def test_statement_metadata_query(api_client):
    client, app_module = api_client
    app_module.history_manager.get_cached_decision.return_value = None
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b'{"id":"q1"}'
    mock_resp.headers = {"Content-Type": "application/json"}
    with patch("app.requests.post", return_value=mock_resp):
        response = client.post(
            "/v1/statement",
            content=b"SHOW TABLES",
            headers={"X-Trino-User": "admin"},
        )
    assert response.status_code == 200
    app_module.history_manager.save_decision.assert_called()


def test_statement_with_analysis(api_client, article_complexity):
    client, app_module = api_client
    app_module.history_manager.get_cached_decision.return_value = None
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b'{"id":"20260101_000000_00002_xyz"}'
    mock_resp.headers = {"Content-Type": "application/json"}

    with patch.object(
        app_module.query_analyzer,
        "analyze_query_io",
        return_value={"tables": {}, "total_size_bytes": 0, "total_rows": 0},
    ):
        with patch.object(
            app_module.query_analyzer,
            "analyze_complexity",
            return_value=article_complexity,
        ):
            with patch("app.requests.post", return_value=mock_resp):
                response = client.post(
                    "/v1/statement",
                    content=b"SELECT * FROM iceberg.analytics.dados WHERE id = 1",
                    headers={"X-Trino-User": "admin"},
                )
    assert response.status_code == 200


def test_statement_cache_hit(api_client):
    client, app_module = api_client
    app_module.history_manager.get_cached_decision.return_value = {
        "cluster": "large",
        "score": 0.8,
        "factors": {},
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b'{"id":"cached1"}'
    mock_resp.headers = {"Content-Type": "application/json"}
    with patch("app.requests.post", return_value=mock_resp):
        response = client.post(
            "/v1/statement",
            content=b"SELECT * FROM t",
            headers={"X-Trino-User": "admin"},
        )
    assert response.status_code == 200


def test_statement_timeout(api_client):
    client, _ = api_client
    import requests as req

    with patch("app.requests.post", side_effect=req.exceptions.Timeout()):
        response = client.post(
            "/v1/statement",
            content=b"SELECT 1",
            headers={"X-Trino-User": "admin"},
        )
    assert response.status_code == 504


def test_proxy_other_get(api_client):
    client, app_module = api_client
    app_module.query_cluster_map["20260101_000000_00001_abc"] = "medium"
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b'{"stats":{"state":"FINISHED"}}'
    mock_resp.headers = {"Content-Type": "application/json"}
    with patch("app.requests.get", return_value=mock_resp):
        response = client.get("/v1/statement/queued/20260101_000000_00001_abc/xx")
    assert response.status_code == 200


def test_proxy_other_error(api_client):
    client, _ = api_client
    with patch("app.requests.get", side_effect=Exception("proxy fail")):
        response = client.get("/v1/statement/queued/unknown/xx")
    assert response.status_code == 500
