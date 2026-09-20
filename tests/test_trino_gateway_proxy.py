"""Testes do Trino Gateway Proxy (import por caminho absoluto)."""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

PROXY_APP_PATH = Path(__file__).resolve().parents[1] / "src" / "trino-gateway-proxy" / "app.py"


def _load_proxy_app():
    spec = importlib.util.spec_from_file_location("trino_gateway_proxy_app", PROXY_APP_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


proxy_app = _load_proxy_app()


@pytest.fixture
def client():
    return TestClient(proxy_app.app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "trino-gateway-proxy"


def test_login_type_get(client):
    response = client.get("/loginType")
    assert response.status_code == 200
    assert response.json()["supportedTypes"] == []


def test_login_type_post(client):
    response = client.post("/loginType")
    assert response.status_code == 200


def test_get_statement_not_allowed(client):
    response = client.get("/v1/statement")
    assert response.status_code == 405


def test_info_fallback(client):
    with patch.object(proxy_app.httpx, "AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.side_effect = Exception("down")
        mock_client_cls.return_value = mock_client
        response = client.get("/v1/info")
    assert response.status_code == 200
    assert b"ACTIVE" in response.content


def test_info_success(client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b'{"nodeId":"trino"}'
    mock_response.headers = {"Content-Type": "application/json"}

    with patch.object(proxy_app.httpx, "AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client
        response = client.get("/v1/info")
    assert response.status_code == 200


def test_statement_empty(client):
    response = client.post("/v1/statement", content=b"  ")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_routing_decision_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "cluster": "medium",
        "score": 0.5,
        "cached": False,
        "factors": {"volume": 0.2, "complexity": 0.3, "historical": 0.5},
    }

    with patch.object(proxy_app.httpx, "AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client
        cluster = await proxy_app.get_routing_decision("SELECT 1")
    assert cluster == "medium"


@pytest.mark.asyncio
async def test_get_routing_decision_cached():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "cluster": "small",
        "score": 0.1,
        "cached": True,
        "factors": {},
    }
    with patch.object(proxy_app.httpx, "AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client
        cluster = await proxy_app.get_routing_decision("SELECT 1")
    assert cluster == "small"


@pytest.mark.asyncio
async def test_get_routing_decision_error_status():
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "err"
    with patch.object(proxy_app.httpx, "AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client
        assert await proxy_app.get_routing_decision("SELECT 1") is None


@pytest.mark.asyncio
async def test_get_routing_decision_timeout():
    with patch.object(proxy_app.httpx, "AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.side_effect = proxy_app.httpx.TimeoutException("t")
        mock_client_cls.return_value = mock_client
        assert await proxy_app.get_routing_decision("SELECT 1") is None


@pytest.mark.asyncio
async def test_get_routing_decision_exception():
    with patch.object(proxy_app.httpx, "AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.side_effect = Exception("x")
        mock_client_cls.return_value = mock_client
        assert await proxy_app.get_routing_decision("SELECT 1") is None


def test_statement_keepalive(client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b'{"id":"1","nextUri":"http://trino-small:8080/v1/statement/q"}'
    mock_response.headers = {"Content-Type": "application/json"}

    with patch.object(proxy_app.httpx, "AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client
        response = client.post(
            "/v1/statement",
            content=b"SELECT 1",
            headers={"X-Trino-User": "admin"},
        )
    assert response.status_code == 200


def test_statement_with_routing(client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b'{"id":"2"}'
    mock_response.headers = {"Content-Type": "application/json"}

    with patch.object(proxy_app, "get_routing_decision", new=AsyncMock(return_value="large")):
        with patch.object(proxy_app.httpx, "AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client
            response = client.post(
                "/v1/statement",
                content=b"SELECT * FROM t",
                headers={"X-Trino-User": "admin", "X-Trino-Catalog": "iceberg"},
            )
    assert response.status_code == 200


def test_statement_fallback_when_no_decision(client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b'{"id":"3"}'
    mock_response.headers = {"Content-Type": "application/json"}

    with patch.object(proxy_app, "get_routing_decision", new=AsyncMock(return_value=None)):
        with patch.object(proxy_app.httpx, "AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client
            response = client.post("/v1/statement", content=b"SELECT * FROM t")
    assert response.status_code == 200


def test_statement_timeout(client):
    with patch.object(proxy_app, "get_routing_decision", new=AsyncMock(return_value="small")):
        with patch.object(proxy_app.httpx, "AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.side_effect = proxy_app.httpx.TimeoutException("t")
            mock_client_cls.return_value = mock_client
            response = client.post("/v1/statement", content=b"SELECT * FROM t")
    assert response.status_code == 504


def test_proxy_login_type_path(client):
    response = client.get("/loginType/")
    assert response.status_code == 200


def test_proxy_ui_get(client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"<html></html>"
    mock_response.headers = {"Content-Type": "text/html"}

    with patch.object(proxy_app.httpx, "AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client
        response = client.get("/ui/")
    assert response.status_code == 200


def test_proxy_ui_fallback_then_cluster(client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b'{"ok":true}'
    mock_response.headers = {"Content-Type": "application/json"}

    call_count = {"n": 0}

    async def get_side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise Exception("gateway down")
        return mock_response

    with patch.object(proxy_app.httpx, "AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.side_effect = get_side_effect
        mock_client_cls.return_value = mock_client
        response = client.get("/ui/index.html")
    assert response.status_code == 200


def test_proxy_other_post(client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b'{"ok":true}'
    mock_response.headers = {"Content-Type": "application/json"}

    with patch.object(proxy_app.httpx, "AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client
        response = client.post("/v1/status", content=b"{}")
    assert response.status_code == 200


def test_proxy_other_get(client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b'{"ok":true}'
    mock_response.headers = {"Content-Type": "application/json"}

    with patch.object(proxy_app.httpx, "AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client
        response = client.get("/v1/status")
    assert response.status_code == 200


@pytest.mark.parametrize(
    "method,attr",
    [
        ("put", "put"),
        ("delete", "delete"),
        ("head", "head"),
        ("options", "options"),
    ],
)
def test_proxy_other_methods(client, method, attr):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b'{"ok":true}'
    mock_response.headers = {"Content-Type": "application/json"}

    with patch.object(proxy_app.httpx, "AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        getattr(mock_client, attr).return_value = mock_response
        mock_client_cls.return_value = mock_client
        response = getattr(client, method)("/v1/status")
    assert response.status_code == 200


def test_proxy_other_error(client):
    with patch.object(proxy_app.httpx, "AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.side_effect = Exception("fail")
        mock_client_cls.return_value = mock_client
        response = client.get("/v1/status")
    assert response.status_code == 500


def test_startup_shutdown():
    asyncio.get_event_loop().run_until_complete(proxy_app.startup_event())
    with patch.object(proxy_app.http_client, "aclose", new=AsyncMock()):
        asyncio.get_event_loop().run_until_complete(proxy_app.shutdown_event())
