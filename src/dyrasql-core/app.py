#!/usr/bin/env python3
"""
DyraSQL Core - Sistema de Roteamento Dinâmico de Consultas SQL
API principal que coordena o processo de decisão de roteamento
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, Optional

import requests
from decision_engine import DecisionEngine
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from history_manager import HistoryManager
from metadata_connector import MetadataConnector
from pydantic import BaseModel
from query_analyzer import QueryAnalyzer

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


app = FastAPI(title="DyraSQL Core", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


query_analyzer = QueryAnalyzer()
decision_engine = DecisionEngine()
metadata_connector = MetadataConnector()
history_manager = HistoryManager()


query_cluster_map = {}


class RouteRequest(BaseModel):
    query: str


class MetricsRequest(BaseModel):
    fingerprint: str
    metrics: Optional[Dict[str, Any]] = None


@app.get("/health")
async def health():
    """Endpoint de health check"""
    return {"status": "healthy", "service": "dyrasql-core"}


@app.post("/api/v1/route")
async def route_query(request_data: RouteRequest):
    """
    Endpoint principal para roteamento de consultas
    Recebe uma consulta SQL e retorna a decisão de roteamento
    """
    try:
        query = request_data.query

        logger.info(f"Processando consulta: {query[:100]}...")

        fingerprint = query_analyzer.generate_fingerprint(query)
        logger.debug(f"Fingerprint gerado: {fingerprint}")

        cached_decision = history_manager.get_cached_decision(fingerprint)

        if cached_decision:
            logger.info(f"Cache hit para fingerprint: {fingerprint}")
            return {
                "fingerprint": fingerprint,
                "cluster": cached_decision["cluster"],
                "score": cached_decision.get("score"),
                "factors": cached_decision.get("factors", {}),
                "cached": True,
                "cluster_url": get_cluster_url(cached_decision["cluster"]),
            }

        logger.info("Analisando I/O da query com EXPLAIN (TYPE IO)...")
        io_analysis = query_analyzer.analyze_query_io(query)

        metadata = {}
        if io_analysis and io_analysis.get("tables"):
            for table_name, table_io in io_analysis["tables"].items():
                metadata[table_name] = {
                    "total_size_bytes": table_io.get("total_size_bytes", 0),
                    "total_records": table_io.get("total_records", 0),
                    "cpu_cost": table_io.get("cpu_cost", 0),
                    "filters": table_io.get("filters", []),
                    "io_analysis": table_io,
                }

        total_size_gb = io_analysis.get("total_size_bytes", 0) / (1024**3) if io_analysis else 0
        logger.info(
            f"Metadados de I/O obtidos: {len(metadata)} tabelas, {io_analysis.get('total_size_bytes', 0):,.0f} bytes ({total_size_gb:.2f} GB) totais"
        )

        complexity = query_analyzer.analyze_complexity(query)
        logger.debug(f"Complexidade: {complexity}")

        decision = decision_engine.decide(
            query=query,
            fingerprint=fingerprint,
            metadata=metadata,
            complexity=complexity,
            history_manager=history_manager,
        )

        logger.info(f"Decisão: cluster={decision['cluster']}, score={decision['score']:.3f}")

        history_manager.save_decision(fingerprint, decision)

        return {
            "fingerprint": fingerprint,
            "cluster": decision["cluster"],
            "score": decision["score"],
            "factors": decision.get("factors", {}),
            "cached": False,
            "cluster_url": get_cluster_url(decision["cluster"]),
        }

    except Exception as e:
        logger.error(f"Erro ao processar consulta: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "Erro interno ao processar consulta", "message": str(e)},
        )


@app.post("/api/v1/metrics")
async def save_metrics(request_data: MetricsRequest):
    """
    Endpoint para salvar métricas pós-execução
    """
    try:
        data = request_data.dict()
        history_manager.save_metrics(data)
        logger.info(f"Métricas salvas para fingerprint: {data['fingerprint']}")

        return {"status": "success", "message": "Métricas salvas com sucesso"}

    except Exception as e:
        logger.error(f"Erro ao salvar métricas: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail={"error": "Erro ao salvar métricas", "message": str(e)}
        )


def get_cluster_url(cluster_name):
    """Retorna a URL do cluster baseado no nome"""
    cluster_urls = {
        "small": os.getenv("TRINO_SMALL_URL", "http://trino-small:8080"),
        "medium": os.getenv("TRINO_MEDIUM_URL", "http://trino-medium:8080"),
        "large": os.getenv("TRINO_LARGE_URL", "http://trino-large:8080"),
    }
    return cluster_urls.get(cluster_name, cluster_urls["small"])


@app.get("/v1/info")
async def trino_info():
    """
    Endpoint /v1/info do Trino - necessário para conexão JDBC
    Retorna informações do cluster padrão (ECS)
    """
    try:
        cluster_url = get_cluster_url("small")
        response = requests.get(
            f"{cluster_url}/v1/info", headers={"Accept-Encoding": "identity"}, timeout=5
        )

        response_headers = {}
        for key, value in response.headers.items():
            if key.lower() not in [
                "content-encoding",
                "transfer-encoding",
                "connection",
                "content-length",
            ]:
                response_headers[key] = value

        content_type = response.headers.get("Content-Type", "application/json")
        response_headers["Content-Type"] = content_type

        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=response_headers,
            media_type=content_type,
        )

    except Exception as e:
        logger.error(f"Erro ao obter info do Trino: {str(e)}")
        return JSONResponse(
            content={
                "nodeId": "dyrasql-core",
                "state": "ACTIVE",
                "nodeVersion": {"version": "478"},
                "environment": "production",
                "coordinator": True,
            },
            status_code=200,
        )


@app.post("/v1/statement")
async def trino_statement(request: Request):
    """
    Endpoint /v1/statement do Trino - executa queries com roteamento inteligente
    O DyraSQL Core decide qual cluster usar e executa a query lá
    """
    try:
        logger.info("=" * 80)
        logger.info("REQUEST RECEIVED FROM IDE:")
        logger.info(f"   Method: {request.method}")
        logger.info(f"   Path: {request.url.path}")
        logger.info(f"   Headers: {dict(request.headers)}")
        logger.info(f"   Content-Type: {request.headers.get('content-type')}")

        body = await request.body()
        query = body.decode("utf-8")
        user = request.headers.get("X-Trino-User", "admin")

        logger.info(f"   Query received: {query[:200]}{'...' if len(query) > 200 else ''}")
        logger.info(f"   User: {user}")
        logger.info("=" * 80)

        if not query or not query.strip():
            logger.error("ERROR: Empty query received")
            raise HTTPException(status_code=400, detail={"error": "Query SQL é obrigatória"})

        query_normalized = query.strip().upper().rstrip(";").strip()
        is_keepalive = (
            query_normalized in ["SELECT 1", "SELECT 1 AS KEEPALIVE", "SELECT 1 AS 1"]
            or query_normalized.startswith("SELECT 'KEEP ALIVE'")
            or query_normalized.startswith("SELECT 'KEEPALIVE'")
        )

        if is_keepalive:
            cluster_name = "small"
            logger.info("KEEP-ALIVE: Keep-alive query detected, using default cluster (small)")
            logger.info(f"   Cluster: {cluster_name}")
        else:
            logger.info(f"Query recebida de {user}: {query[:100]}...")

            fingerprint = query_analyzer.generate_fingerprint(query)

            cached_decision = history_manager.get_cached_decision(fingerprint)

            if cached_decision:
                cluster_name = cached_decision["cluster"]
                score = cached_decision.get("score", 0.0)
                factors = cached_decision.get("factors", {})
                logger.info(f"CACHE: Using cached decision for fingerprint: {fingerprint[:16]}...")
                logger.info(
                    f"   Score: {score:.3f} | Factors: volume={factors.get('volume', 0):.3f}, complexity={factors.get('complexity', 0):.3f}, historical={factors.get('historical', 0):.3f}"
                )
                logger.info(f"   Cluster selected (cache): {cluster_name}")
            else:
                is_metadata_query = (
                    query_normalized.startswith("SHOW ")
                    or query_normalized.startswith("DESCRIBE ")
                    or query_normalized.startswith("DESC ")
                    or query_normalized.startswith("SELECT VERSION()")
                    or query_normalized.startswith("SELECT CURRENT_")
                )

                if is_metadata_query:
                    cluster_name = "small"
                    logger.info(
                        "METADATA: Metadata query detected, using default cluster (small) without full analysis"
                    )
                    logger.info(f"   Cluster: {cluster_name}")

                    history_manager.save_decision(
                        fingerprint,
                        {
                            "cluster": cluster_name,
                            "score": 0.0,
                            "factors": {"volume": 0, "complexity": 0, "historical": 0},
                        },
                    )
                else:
                    logger.info("Analisando I/O da query com EXPLAIN (TYPE IO) no cluster small...")
                    io_analysis = query_analyzer.analyze_query_io(query)

                    metadata = {}
                    if io_analysis and io_analysis.get("tables"):
                        for table_name, table_io in io_analysis["tables"].items():
                            metadata[table_name] = {
                                "total_size_bytes": table_io.get("total_size_bytes", 0),
                                "total_records": table_io.get("total_records", 0),
                                "cpu_cost": table_io.get("cpu_cost", 0),
                                "filters": table_io.get("filters", []),
                                "io_analysis": table_io,
                            }

                    complexity = query_analyzer.analyze_complexity(query)

                    decision = decision_engine.decide(
                        query=query,
                        fingerprint=fingerprint,
                        metadata=metadata,
                        complexity=complexity,
                        history_manager=history_manager,
                    )

                    cluster_name = decision["cluster"]
                    score = decision["score"]
                    factors = decision.get("factors", {})

                    logger.info("NEW ANALYSIS: Query analyzed from scratch (not in cache)")
                    logger.info(f"   Calculated score: {score:.3f}")
                    logger.info(
                        f"   Factors: volume={factors.get('volume', 0):.3f}, complexity={factors.get('complexity', 0):.3f}, historical={factors.get('historical', 0):.3f}"
                    )
                    logger.info(
                        f"   Cluster selected: {cluster_name} (analysis on small, execution on {cluster_name})"
                    )

                    history_manager.save_decision(fingerprint, decision)

        cluster_url = get_cluster_url(cluster_name)

        logger.info("=" * 80)
        logger.info(f"ROUTING DECISION: Query will be executed on cluster '{cluster_name}'")
        logger.info(f"   Cluster URL: {cluster_url}")
        logger.info(f"   Full query: {query}")
        logger.info("=" * 80)

        headers = {"Content-Type": "text/plain", "X-Trino-User": user}

        for header in [
            "X-Trino-Catalog",
            "X-Trino-Schema",
            "X-Trino-Source",
            "X-Trino-Client-Info",
        ]:
            if header in request.headers:
                headers[header] = request.headers[header]

        headers["Accept-Encoding"] = "identity"

        timeout = 5 if is_keepalive else 300

        logger.info(
            f"EXECUTING: Executing query on cluster {cluster_name} with timeout of {timeout}s"
        )
        logger.info(f"   Target URL: {cluster_url}/v1/statement")
        logger.info(f"   Request headers: {headers}")

        response = requests.post(
            f"{cluster_url}/v1/statement", data=query, headers=headers, timeout=timeout
        )

        logger.info(f"RESPONSE: Response received from cluster {cluster_name}:")
        logger.info(f"   Status Code: {response.status_code}")
        logger.info(f"   Headers: {dict(response.headers)}")
        logger.info(f"   Content (first 500 chars): {response.content[:500]}")

        response_content = response.content.decode("utf-8")

        try:
            response_json = json.loads(response_content)
            query_id = response_json.get("id")
            if query_id:
                query_cluster_map[query_id] = cluster_name
                logger.debug(f"Mapeado query ID {query_id} para cluster {cluster_name}")
        except:
            pass

        for _cluster_name_sub, cluster_url in [
            ("small", get_cluster_url("small")),
            ("medium", get_cluster_url("medium")),
            ("large", get_cluster_url("large")),
        ]:
            pattern_next = re.escape(cluster_url) + r"(/v1/statement/[^\"]+)"
            replacement_next = r"http://localhost:5001\1"
            response_content = re.sub(pattern_next, replacement_next, response_content)

            pattern_info = re.escape(cluster_url) + r"(/ui/[^\"]+)"
            replacement_info = r"http://localhost:5001\1"
            response_content = re.sub(pattern_info, replacement_info, response_content)

        response_headers = {}
        for key, value in response.headers.items():
            if key.lower() not in [
                "content-encoding",
                "transfer-encoding",
                "connection",
                "content-length",
            ]:
                response_headers[key] = value

        content_type = response.headers.get("Content-Type", "application/json")
        response_headers["Content-Type"] = content_type

        return Response(
            content=response_content.encode("utf-8"),
            status_code=response.status_code,
            headers=response_headers,
            media_type=content_type,
        )

    except requests.exceptions.Timeout:
        logger.error("Timeout ao executar query no cluster Trino")
        raise HTTPException(status_code=504, detail={"error": "Timeout ao executar query"})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao executar query: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail={"error": "Erro ao executar query", "message": str(e)}
        )


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"])
async def proxy_other(path: str, request: Request):
    """
    Proxy para outros endpoints do Trino (nextUri, etc)
    Detecta qual cluster usar baseado no query ID no path
    """
    try:
        cluster_name = "small"

        query_id_match = re.search(r"/(\d{8}_\d{6}_\d{5}_[^/]+)/", path)
        if query_id_match:
            query_id = query_id_match.group(1)

            if query_id in query_cluster_map:
                cluster_name = query_cluster_map[query_id]
                logger.info(
                    f"PROXY: Using cluster '{cluster_name}' for query ID {query_id} (nextUri)"
                )
            else:
                logger.warning(
                    f"WARNING: Query ID {query_id} not found in mapping, using default cluster (small)"
                )

        cluster_url = get_cluster_url(cluster_name)
        target_url = f"{cluster_url}/{path}"

        logger.debug(f"PROXY: {request.method} {path} → {cluster_name} ({target_url})")

        headers = {}
        for key, value in request.headers.items():
            if key.lower() not in ["host", "content-length", "connection"]:
                headers[key] = value

        headers["Accept-Encoding"] = "identity"

        body = await request.body() if request.method in ["POST", "PUT"] else None

        if request.method == "GET":
            response = requests.get(
                target_url, headers=headers, params=dict(request.query_params), timeout=300
            )
        elif request.method == "POST":
            response = requests.post(target_url, data=body, headers=headers, timeout=300)
        elif request.method == "PUT":
            response = requests.put(target_url, data=body, headers=headers, timeout=300)
        elif request.method == "DELETE":
            response = requests.delete(target_url, headers=headers, timeout=300)
        elif request.method == "HEAD":
            response = requests.head(target_url, headers=headers, timeout=300)
        elif request.method == "OPTIONS":
            response = requests.options(target_url, headers=headers, timeout=300)
        else:
            raise HTTPException(status_code=405, detail={"error": "Method not allowed"})

        response_content = response.content.decode("utf-8")

        for _cluster_name_sub, rewrite_url in [
            ("small", get_cluster_url("small")),
            ("medium", get_cluster_url("medium")),
            ("large", get_cluster_url("large")),
        ]:
            pattern_next = re.escape(rewrite_url) + r"(/v1/statement/[^\"]+)"
            replacement_next = r"http://localhost:5001\1"
            response_content = re.sub(pattern_next, replacement_next, response_content)

            pattern_info = re.escape(rewrite_url) + r"(/ui/[^\"]+)"
            replacement_info = r"http://localhost:5001\1"
            response_content = re.sub(pattern_info, replacement_info, response_content)

        response_headers = {}
        for key, value in response.headers.items():
            if key.lower() not in [
                "content-encoding",
                "transfer-encoding",
                "connection",
                "content-length",
            ]:
                response_headers[key] = value

        content_type = response.headers.get("Content-Type", "application/json")
        response_headers["Content-Type"] = content_type

        return Response(
            content=response_content.encode("utf-8"),
            status_code=response.status_code,
            headers=response_headers,
            media_type=content_type,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao fazer proxy para {path}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail={"error": "Erro ao fazer proxy", "message": str(e)}
        )


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
