"""
Trino Gateway Proxy com Integração DyraSQL Core
Este proxy intercepta queries e roteia automaticamente baseado na decisão do DyraSQL Core
"""

from __future__ import annotations

import json
import logging
import os
import re
from urllib.parse import urljoin

import httpx
from fastapi import FastAPI, HTTPException, Request, Response

app = FastAPI(title="Trino Gateway Proxy", version="1.0.0")


logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


DYRASQL_CORE_URL = os.getenv("DYRASQL_CORE_URL", "http://dyrasql-core:5000")

TRINO_GATEWAY_URL = os.getenv("TRINO_GATEWAY_URL", "http://trino-gateway:8080")

CLUSTER_URLS = {
    "small": os.getenv("TRINO_SMALL_URL", "http://trino-small:8080"),
    "medium": os.getenv("TRINO_MEDIUM_URL", "http://trino-medium:8080"),
    "large": os.getenv("TRINO_LARGE_URL", "http://trino-large:8080"),
}

FALLBACK_CLUSTER = "small"

TIMEOUT = int(os.getenv("ROUTING_TIMEOUT", "5"))

QUERY_TIMEOUT = int(os.getenv("QUERY_TIMEOUT", "300"))

PUBLIC_BASE = os.getenv("PROXY_PUBLIC_URL", "http://localhost:8080").rstrip("/")

QUERY_ID_RE = re.compile(r"(\d{8}_\d{6}_\d{5}_[A-Za-z0-9]+)")

URI_KEYS = ("nextUri", "infoUri", "partialCancelUri")

query_cluster_map: dict[str, str] = {}

http_client = httpx.AsyncClient(timeout=TIMEOUT)


def sanitize_jdbc_metadata_query(query: str) -> str:
    """Remove aspas extras que o JDBC coloca em catalogo/schema (ex: '"iceberg"')."""
    return re.sub(r"'\"([^\"]+)\"'", r"'\1'", query)


def is_client_metadata_query(query: str) -> bool:
    normalized = query.strip().upper()
    normalized = re.sub(r"/\*.*?\*/", " ", normalized, flags=re.DOTALL)
    normalized = re.sub(r"--[^\n]*", " ", normalized)
    normalized = " ".join(normalized.rstrip(";").split())
    if normalized.startswith(
        ("SHOW ", "DESCRIBE ", "DESC ", "SELECT VERSION()", "SELECT CURRENT_")
    ):
        return True
    return "SYSTEM.JDBC." in normalized or "INFORMATION_SCHEMA." in normalized


def extract_query_id(text: str) -> str | None:
    match = QUERY_ID_RE.search(text)
    if match:
        return match.group(1)
    return None


def remember_query_cluster(content: str, cluster_name: str) -> None:
    query_id = None
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            query_id = data.get("id")
    except (json.JSONDecodeError, TypeError):
        query_id = None
    if not query_id:
        query_id = extract_query_id(content)
    if query_id:
        query_cluster_map[str(query_id)] = cluster_name
        logger.info("Mapeado query ID %s para cluster %s", query_id, cluster_name)


def rewrite_one_uri(uri: str) -> str:
    if not uri:
        return uri
    for prefix in list(CLUSTER_URLS.values()) + [
        "http://127.0.0.1:8080",
        "http://0.0.0.0:8080",
    ]:
        if uri.startswith(prefix):
            return PUBLIC_BASE + uri[len(prefix) :]
    return uri


def rewrite_trino_payload(content: str) -> str:
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            for key in URI_KEYS:
                value = data.get(key)
                if isinstance(value, str):
                    data[key] = rewrite_one_uri(value)
            return json.dumps(data)
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError):
        pass
    rewritten = content
    for cluster_url in CLUSTER_URLS.values():
        rewritten = re.sub(
            re.escape(cluster_url) + r"(/[^\"]+)",
            PUBLIC_BASE + r"\1",
            rewritten,
        )
    return rewritten


def clusters_to_try(path: str) -> list[str]:
    ordered = [FALLBACK_CLUSTER] + [name for name in CLUSTER_URLS if name != FALLBACK_CLUSTER]
    query_id = extract_query_id(path)
    if query_id and query_id in query_cluster_map:
        mapped = query_cluster_map[query_id]
        return [mapped] + [name for name in ordered if name != mapped]
    return ordered


def filter_response_headers(headers) -> dict[str, str]:
    skipped = {
        "connection",
        "transfer-encoding",
        "content-encoding",
        "content-length",
    }
    return {key: value for key, value in headers.items() if key.lower() not in skipped}


@app.get("/health")
async def health():
    """Health check endpoint"""

    return {
        "service": "trino-gateway-proxy",
        "status": "healthy",
        "dyrasql_core_url": DYRASQL_CORE_URL,
        "trino_gateway_url": TRINO_GATEWAY_URL,
    }


@app.post("/v1/statement")
async def route_statement(request: Request):
    """
    Intercepta queries SQL e roteia baseado na decisão do DyraSQL Core
    """

    try:
        query = (await request.body()).decode("utf-8")

        user = request.headers.get("X-Trino-User", "admin")

        if not query or not query.strip():
            raise HTTPException(status_code=400, detail="Query SQL é obrigatória")

        query_normalized = query.strip().upper().rstrip(";").strip()

        is_keepalive = (
            query_normalized in ["SELECT 1", "SELECT 1 AS KEEPALIVE", "SELECT 1 AS 1"]
            or query_normalized.startswith("SELECT 'KEEP ALIVE'")
            or query_normalized.startswith("SELECT 'KEEPALIVE'")
        )

        is_metadata = is_client_metadata_query(query)

        if is_keepalive:
            logger.debug(f"Query de keep-alive detectada: {query}")

            cluster_name = FALLBACK_CLUSTER

        elif is_metadata:
            sanitized = sanitize_jdbc_metadata_query(query)
            if sanitized != query:
                logger.info("METADATA: removendo aspas extras da consulta JDBC")
                query = sanitized
            logger.info("METADATA: consulta de catalogo JDBC no cluster small: %s", query[:180])

            cluster_name = FALLBACK_CLUSTER

        else:
            logger.info(f"Query recebida de {user}: {query[:100]}...")

            cluster_name = await get_routing_decision(query)

            if not cluster_name:
                logger.warning(
                    f"Não foi possível obter decisão do DyraSQL Core, usando fallback: {FALLBACK_CLUSTER}"
                )

                cluster_name = FALLBACK_CLUSTER

        cluster_url = CLUSTER_URLS.get(cluster_name)

        if not cluster_url:
            logger.error(
                f"Cluster '{cluster_name}' não encontrado, usando fallback: {FALLBACK_CLUSTER}"
            )

            cluster_url = CLUSTER_URLS[FALLBACK_CLUSTER]

        if not is_keepalive:
            logger.info(f"Roteando query para cluster: {cluster_name} ({cluster_url})")

        target_url = urljoin(cluster_url, "/v1/statement")

        headers = {"Content-Type": "text/plain", "X-Trino-User": user}

        for header in [
            "X-Trino-Catalog",
            "X-Trino-Schema",
            "X-Trino-Source",
            "X-Trino-Client-Info",
        ]:
            if header in request.headers:
                headers[header] = request.headers[header]

        request_headers = headers.copy()

        request_headers["Accept-Encoding"] = "identity"

        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
            response = await client.post(target_url, content=query, headers=request_headers)

            response_content = rewrite_trino_payload(response.content.decode("utf-8"))

            remember_query_cluster(response_content, cluster_name)

            response_headers = filter_response_headers(response.headers)

            content_type = response.headers.get("Content-Type", "application/json")

            response_headers["Content-Type"] = content_type

            return Response(
                content=response_content.encode("utf-8"),
                status_code=response.status_code,
                headers=response_headers,
            )

    except HTTPException:
        raise

    except httpx.TimeoutException:
        logger.error("Timeout ao rotear query")

        raise HTTPException(status_code=504, detail="Timeout ao executar query")

    except Exception as e:
        logger.error(f"Erro ao rotear query: {str(e)}", exc_info=True)

        raise HTTPException(status_code=500, detail=f"Erro ao rotear query: {str(e)}")


@app.get("/v1/info")
async def info():
    """Endpoint de info do Trino - retorna exatamente o que o Trino retorna"""

    try:
        async with httpx.AsyncClient(timeout=2, headers={"Accept-Encoding": "identity"}) as client:
            response = await client.get(f"{CLUSTER_URLS[FALLBACK_CLUSTER]}/v1/info")

            response_headers = {}

            for key, value in response.headers.items():
                if key.lower() not in ["connection", "transfer-encoding", "content-encoding"]:
                    response_headers[key] = value

            response_content = response.content.decode("utf-8")

            for _cluster_name_sub, cluster_url in CLUSTER_URLS.items():
                pattern = re.escape(cluster_url) + r"(/[^\"]+)"

                replacement = r"http://localhost:8080\1"

                response_content = re.sub(pattern, replacement, response_content)

            return Response(
                content=response_content.encode("utf-8"),
                status_code=response.status_code,
                headers=response_headers,
            )

    except Exception as e:
        logger.warning(f"Erro ao obter info do cluster, retornando fallback: {e}")

        import json

        fallback_data = {"nodeId": "proxy", "state": "ACTIVE", "environment": "production"}

        return Response(
            content=json.dumps(fallback_data).encode("utf-8"),
            status_code=200,
            headers={"Content-Type": "application/json"},
        )


@app.post("/loginType")
async def login_type_post():
    """Endpoint de tipo de login - retorna que não há autenticação necessária"""

    return Response(
        content=json.dumps({"supportedTypes": []}).encode("utf-8"),
        status_code=200,
        headers={"Content-Type": "application/json"},
    )


@app.get("/loginType")
async def login_type_get():
    """Endpoint de tipo de login - retorna que não há autenticação necessária"""

    return Response(
        content=json.dumps({"supportedTypes": []}).encode("utf-8"),
        status_code=200,
        headers={"Content-Type": "application/json"},
    )


@app.get("/v1/statement")
async def get_statement():
    """Endpoint GET /v1/statement - alguns clientes JDBC fazem GET antes de POST"""

    raise HTTPException(
        status_code=405, detail="Method not allowed. Use POST /v1/statement to execute queries."
    )


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"])
async def proxy_other(path: str, request: Request):
    """
    Proxy para outros endpoints do Trino (nextUri, queries de keep-alive, etc)
    Para UI do Trino, redireciona para o Trino Gateway
    """

    logger.info(f"Proxy other - path: '{path}', method: {request.method}, path type: {type(path)}")

    normalized_path = path.strip("/")

    if normalized_path == "loginType":
        logger.info("Tratando /loginType - retornando resposta vazia")

        import json

        return Response(
            content=json.dumps({"supportedTypes": []}).encode("utf-8"),
            status_code=200,
            headers={"Content-Type": "application/json"},
        )

    is_ui_request = (
        path == ""
        or path == "/"
        or path.startswith("ui/")
        or path.startswith("assets/")
        or path.startswith("vendor/")
        or path.endswith(".html")
        or path.endswith(".css")
        or path.endswith(".js")
        or path.endswith(".ico")
    )

    if is_ui_request and request.method == "GET":
        gateway_ui_url = f"{TRINO_GATEWAY_URL}/{path}" if path else f"{TRINO_GATEWAY_URL}/"

        logger.debug(f"Redirecionando requisição de UI para: {gateway_ui_url}")

        try:
            async with httpx.AsyncClient(
                timeout=5, follow_redirects=True, headers={"Accept-Encoding": "identity"}
            ) as client:
                response = await client.get(gateway_ui_url, params=request.query_params)

                response_headers = {}

                for key, value in response.headers.items():
                    if key.lower() not in ["connection", "transfer-encoding", "content-encoding"]:
                        response_headers[key] = value

                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=response_headers,
                )

        except Exception as e:
            logger.warning(f"Erro ao redirecionar UI para gateway, tentando cluster padrão: {e}")

    try:
        relative_path = path if path.startswith("/") else f"/{path}" if path else "/"

        headers = {}

        for key, value in request.headers.items():
            if key.lower() not in ["host", "content-length", "connection", "transfer-encoding"]:
                headers[key] = value

        body = await request.body() if request.method in ["POST", "PUT"] else None

        is_statement_poll = relative_path.startswith("/v1/statement/")

        timeout = QUERY_TIMEOUT if is_statement_poll else TIMEOUT

        last_response = None

        async with httpx.AsyncClient(
            timeout=timeout, follow_redirects=True, headers={"Accept-Encoding": "identity"}
        ) as client:
            for cluster_name in clusters_to_try(relative_path):
                target_url = f"{CLUSTER_URLS[cluster_name]}{relative_path}"
                if is_statement_poll:
                    logger.info("PROXY: %s %s -> %s", request.method, relative_path, cluster_name)

                if request.method == "GET":
                    response = await client.get(
                        target_url, headers=headers, params=request.query_params
                    )

                elif request.method == "POST":
                    response = await client.post(target_url, content=body, headers=headers)

                elif request.method == "PUT":
                    response = await client.put(target_url, content=body, headers=headers)

                elif request.method == "DELETE":
                    response = await client.delete(target_url, headers=headers)

                elif request.method == "HEAD":
                    response = await client.head(target_url, headers=headers)

                elif request.method == "OPTIONS":
                    response = await client.options(target_url, headers=headers)

                else:
                    raise HTTPException(status_code=405, detail="Method not allowed")

                last_response = response

                if is_statement_poll and response.status_code == 404:
                    logger.warning(
                        "Query nao encontrada em %s, tentando outro cluster: %s",
                        cluster_name,
                        relative_path,
                    )
                    continue

                break

            response = last_response

            if response is None:
                raise HTTPException(status_code=502, detail="Nenhum cluster Trino disponivel")

            response_headers = filter_response_headers(response.headers)

            try:
                response_content = rewrite_trino_payload(response.content.decode("utf-8"))
                payload = response_content.encode("utf-8")
            except UnicodeDecodeError:
                payload = response.content

            return Response(
                content=payload,
                status_code=response.status_code,
                headers=response_headers,
            )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Erro ao fazer proxy para {path}: {str(e)}", exc_info=True)

        raise HTTPException(status_code=500, detail=f"Erro ao fazer proxy: {str(e)}")


async def get_routing_decision(query: str) -> str | None:
    """
    Chama o DyraSQL Core para obter decisão de roteamento
    """

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(f"{DYRASQL_CORE_URL}/api/v1/route", json={"query": query})

            if response.status_code == 200:
                data = response.json()

                cluster = data.get("cluster")

                score = data.get("score", 0)

                cached = data.get("cached", False)

                factors = data.get("factors", {})

                if cached:
                    logger.info(
                        f"CACHE: DyraSQL Core decision (cached): cluster={cluster}, score={score:.3f}"
                    )

                else:
                    logger.info(
                        f"NEW ANALYSIS: DyraSQL Core decision: cluster={cluster}, score={score:.3f}"
                    )

                    logger.info(
                        f"   Factors: volume={factors.get('volume', 0):.3f}, complexity={factors.get('complexity', 0):.3f}, historical={factors.get('historical', 0):.3f}"
                    )

                logger.info(f"ROUTING: Query will be executed on cluster '{cluster}'")

                return cluster

            else:
                logger.warning(
                    f"DyraSQL Core retornou status {response.status_code}: {response.text}"
                )

                return None

    except httpx.TimeoutException:
        logger.warning("Timeout ao chamar DyraSQL Core")

        return None

    except Exception as e:
        logger.error(f"Erro ao chamar DyraSQL Core: {str(e)}", exc_info=True)

        return None


@app.on_event("startup")
async def startup_event():
    """Evento de inicialização"""

    logger.info("Iniciando Trino Gateway Proxy")

    logger.info(f"DyraSQL Core URL: {DYRASQL_CORE_URL}")

    logger.info(f"Trino Gateway URL: {TRINO_GATEWAY_URL}")


@app.on_event("shutdown")
async def shutdown_event():
    """Evento de encerramento"""

    await http_client.aclose()


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8080"))

    uvicorn.run(app, host="0.0.0.0", port=port)
