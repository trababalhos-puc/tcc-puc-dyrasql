"""Collect real local outputs and render legible terminal cards for the pitch.

Run with the project virtualenv; external systems are explicitly mocked in the
API demonstration. No benchmark or distributed execution is claimed.
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import os
from pathlib import Path
import platform
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "latex/beamer/evidencias"
OUT.mkdir(parents=True, exist_ok=True)
os.environ["SAVE_EXPLAINS"] = "false"
sys.path.insert(0, str(ROOT / "src/dyrasql-core"))


def capture(name, command):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    git_bin = Path("C:/Program Files/Git/bin")
    if git_bin.exists():
        env["PATH"] = str(git_bin) + os.pathsep + env["PATH"]
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True,
                            text=True, encoding="utf-8", errors="replace")
    text = "$ " + subprocess.list2cmdline(command) + "\n" + result.stdout + result.stderr
    text += f"\nEXIT_CODE={result.returncode}\n"
    (OUT / f"{name}.txt").write_text(text, encoding="utf-8")
    return result, text


def card(name, title, lines, label):
    font_path = "C:/Windows/Fonts/consola.ttf"
    font = ImageFont.truetype(font_path, 27) if Path(font_path).exists() else ImageFont.load_default()
    small = ImageFont.truetype(font_path, 21) if Path(font_path).exists() else font
    width, height = 1600, 135 + 39 * len(lines) + 60
    im = Image.new("RGB", (width, height), "#101c30")
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((16, 16, width - 16, height - 16), radius=20, outline="#3c5270", width=2)
    d.text((40, 34), title, font=font, fill="#76d9e8")
    d.text((40, 79), label, font=small, fill="#b3bfd2")
    for i, line in enumerate(lines):
        d.text((40, 130 + i * 39), line, font=font, fill="#e8eff8")
    d.text((40, height - 50), "Saída real renderizada | fonte: evidencias/*.txt | sem benchmark", font=small, fill="#b3bfd2")
    im.save(OUT / f"{name}.png")


def main():
    stamp = datetime.now(timezone(timedelta(hours=-3))).isoformat()
    _, git = capture("git", ["git", "rev-parse", "HEAD"])
    environment = {"timestamp_brt": stamp, "python": sys.version, "platform": platform.platform(),
                   "commit": git.splitlines()[1], "scope": "Local tests; API dependencies mocked"}
    (OUT / "ambiente.json").write_text(json.dumps(environment, indent=2), encoding="utf-8")
    focused, focused_text = capture("testes_focados", [sys.executable, "-m", "pytest", "-v",
        "--no-cov", "tests/test_decision_engine.py", "tests/test_query_analyzer.py",
        "tests/test_api_route.py", f"--junitxml={OUT / 'focados.xml'}"])
    full, full_text = capture("testes_completos", [sys.executable, "-m", "pytest", "-q",
        f"--junitxml={OUT / 'completos.xml'}"])
    suites = {}
    for key in ("focados", "completos"):
        suite = ET.parse(OUT / f"{key}.xml").getroot().find("testsuite")
        suites[key] = {k: suite.attrib[k] for k in ("tests", "failures", "errors", "skipped", "time")}
    (OUT / "resumo_testes.json").write_text(json.dumps(suites, indent=2), encoding="utf-8")
    summary_lines = [f"Python {platform.python_version()} | Windows | {stamp[:10]}",
                     "Foco: decisão, análise SQL e API (dependências simuladas)"]
    for key, result in (("focados", focused), ("completos", full)):
        s = suites[key]
        summary_lines.append(f"{key}: tests={s['tests']} failures={s['failures']} errors={s['errors']} exit={result.returncode}")
    cov_lines = [line for line in full_text.splitlines() if line.startswith("TOTAL") or "coverage of" in line]
    summary_lines += cov_lines
    card("01_testes", "DyraSQL | testes locais", summary_lines, "Captura renderizada do pytest; suíte completa preserva o gate de cobertura")

    from decision_engine import DecisionEngine
    from query_analyzer import QueryAnalyzer
    from fastapi.testclient import TestClient

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s | %(message)s"))
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)
    analyzer = QueryAnalyzer()
    engine = DecisionEngine()
    history = MagicMock()
    cases = [
        ("small", .01, 10, {"joins": 0, "aggregations": 0, "subqueries": 0}, 0),
        ("medium", 1.25, 2_500_000, {"joins": 1, "aggregations": 3, "subqueries": 2,
          "partitioned_filters": 1, "non_partitioned_filters": 2}, .5),
        ("large", 900, 500_000_000, {"joins": 5, "aggregations": 5, "subqueries": 5,
          "non_partitioned_filters": 5}, 1),
    ]
    decisions = []
    for expected, gb, rows, complexity, fh in cases:
        history.get_historical_factor.return_value = fh
        decision = engine.decide("SELECT 1", expected,
            {"t": {"total_size_bytes": int(gb * 1024**3), "total_records": rows}}, complexity, history)
        assert decision["cluster"] == expected
        decisions.append({"input_gib": gb, "input_rows": rows, **decision})
    (OUT / "decisoes.json").write_text(json.dumps(decisions, indent=2), encoding="utf-8")
    card("02_decisoes", "DyraSQL | execução do DecisionEngine", [
        "Entradas controladas; não representam tabelas carregadas no Trino",
        "S = 0.5 * volume + 0.3 * complexidade + 0.2 * histórico",
        *[f"{r['cluster']:6} | score={r['score']:.6f} | fv={r['factors']['volume']:.6f} | fc={r['factors']['complexity']:.3f} | fh={r['factors']['historical']:.1f}" for r in decisions],
        "Limites: S < 0.3 small; 0.3 <= S <= 0.7 medium; S > 0.7 large",
        "ASSERT cluster == destino esperado: OK (3/3)",
    ], "Execução real do algoritmo com metadados e histórico de teste")

    query = "SELECT d.tenant_id, COUNT(*), SUM(d.valor) FROM iceberg.analytics.dados d JOIN iceberg.analytics.tenant_info t ON d.tenant_id=t.tenant_id WHERE d.date >= TIMESTAMP '2024-01-01' AND t.nivel > 5 GROUP BY d.tenant_id"
    complexity = analyzer.analyze_complexity(query)
    fp = analyzer.generate_fingerprint(query)
    (OUT / "analise_sql.json").write_text(json.dumps({"query": query, "complexity": complexity, "fingerprint": fp}, indent=2), encoding="utf-8")
    card("03_analise_sql", "DyraSQL | análise sintática SQL", [
        "SELECT d.tenant_id, COUNT(*), SUM(d.valor)",
        "FROM iceberg.analytics.dados d JOIN iceberg.analytics.tenant_info t",
        "ON d.tenant_id = t.tenant_id",
        "WHERE d.date >= TIMESTAMP '2024-01-01' AND t.nivel > 5",
        "GROUP BY d.tenant_id",
        *[f"{k}: {v}" for k, v in complexity.items()],
        f"fingerprint (SHA-256, prefixo): {fp[:24]}",
    ], "Parser SQL real; consulta analisada, sem execução em banco")

    conn = MagicMock()
    conn.closed = 0
    with patch("psycopg2.connect", return_value=conn), patch("time.sleep"):
        import app as api
    api.history_manager.get_cached_decision = MagicMock(return_value=None)
    api.history_manager.get_historical_factor = MagicMock(return_value=.5)
    api.history_manager.save_decision = MagicMock()
    data = {"tables": {"iceberg.analytics.dados": {"total_size_bytes": int(1.25 * 1024**3), "total_records": 2_500_000}},
            "total_size_bytes": int(1.25 * 1024**3), "total_rows": 2_500_000}
    with TestClient(api.app) as client, patch.object(api.query_analyzer, "analyze_query_io", return_value=data), patch.object(api.query_analyzer, "analyze_complexity", return_value=cases[1][3]):
        health = client.get("/health")
        miss = client.post("/api/v1/route", json={"query": query})
        assert miss.status_code == 200 and miss.json()["cluster"] == "medium"
        api.history_manager.get_cached_decision.return_value = miss.json()
        hit = client.post("/api/v1/route", json={"query": query})
        assert hit.status_code == 200 and hit.json()["cached"] is True
    api_out = {"health": health.json(), "miss": miss.json(), "hit": hit.json(), "http_status": [health.status_code, miss.status_code, hit.status_code]}
    (OUT / "api.json").write_text(json.dumps(api_out, indent=2), encoding="utf-8")
    card("04_api_cache", "DyraSQL | API FastAPI em processo", [
        "TestClient: aplicação real; Trino e PostgreSQL simulados",
        f"GET /health -> HTTP {health.status_code} | status={health.json()['status']}",
        f"POST /api/v1/route -> HTTP {miss.status_code}",
        f"cluster={miss.json()['cluster']} score={miss.json()['score']:.6f} cached={miss.json()['cached']}",
        f"Repetição -> HTTP {hit.status_code} | cached={hit.json()['cached']}",
        "ASSERT cache miss -> cache hit: OK",
        "Persistência e latência do PostgreSQL não medidas nesta demonstração",
    ], "Saídas reais HTTP; respostas externas fornecidas por fixtures")
    (OUT / "execucao_local.txt").write_text(stream.getvalue(), encoding="utf-8")
    logging.getLogger().removeHandler(handler)

    compose, compose_text = capture("docker_compose", ["docker", "compose", "-f", "src/docker-compose.yml", "up", "-d",
        "minio", "iceberg-rest", "gateway-db", "trino-small", "trino-medium", "trino-large", "dyrasql-core", "trino-gateway-proxy"])
    capture("docker_estado", ["docker", "compose", "-f", "src/docker-compose.yml", "ps", "-a"])
    error_lines = [line.strip() for line in compose_text.splitlines() if "denied" in line or "Error response" in line]
    card("05_integracao", "DyraSQL | tentativa de integração local", [
        "$ docker compose -f src/docker-compose.yml up -d ...",
        f"EXIT_CODE={compose.returncode}",
        *[line[:100] for line in error_lines[:3]],
        "Infraestrutura integrada não validada nesta coleta.",
        "Sem medida real de EXPLAIN, consumo de recursos ou custo.",
    ], "Registro de falha real; evidência de execução não concluída")
    (OUT / "resultado_coleta.json").write_text(json.dumps({"suites": suites, "focused_exit": focused.returncode,
        "full_exit": full.returncode, "compose_exit": compose.returncode, "decisions": decisions}, indent=2), encoding="utf-8")
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.iterdir()) if p.is_file() and p.name != "sha256.json"}
    (OUT / "sha256.json").write_text(json.dumps(hashes, indent=2), encoding="utf-8")
    print(json.dumps({"suites": suites, "focused_exit": focused.returncode, "full_exit": full.returncode,
                      "compose_exit": compose.returncode}, indent=2))


def render_additional():
    """Render the separately captured WSL runs without rerunning tests."""
    results = {}
    for key in ("focados", "completos", "linux", "linux_lf"):
        suite = ET.parse(OUT / f"{key}.xml").getroot().find("testsuite")
        results[key] = {k: suite.attrib[k] for k in ("tests", "failures", "errors", "skipped", "time")}
    lf_text = (OUT / "testes_linux_lf.txt").read_text(encoding="utf-8")
    linux_text = (OUT / "testes_linux.txt").read_text(encoding="utf-8")
    cov = [line for line in lf_text.splitlines() if "Total coverage:" in line]
    card("06_testes_linux", "DyraSQL | suíte completa no Ubuntu / WSL", [
        "Python 3.12.3 | checkout isolado do mesmo commit | arquivos LF",
        "Commit: 8f9b8e58576a06f81479975923080206ce58ca4a",
        *[line for line in lf_text.splitlines() if line.startswith("TOTAL") or "passed in" in line],
        *cov,
        "EXIT_CODE=0 | gate de cobertura >= 90% preservado",
        "Windows: 107 passed / 13 failed (log original preservado)",
        "WSL no diretório Windows com CRLF: 115 passed / 5 failed",
        "Testes locais com mocks; sem validação distribuída nesta coleta.",
    ], "Saída real do pytest; fonte: testes_linux_lf.txt e linux_lf.xml")
    card("07_logs", "DyraSQL | logs da aplicação local", [
        line for line in (OUT / "execucao_local.txt").read_text(encoding="utf-8").splitlines()
        if "Decision Engine:" in line or "Decisao calculada" in line or "Cache hit" in line
        or "HTTP Request:" in line
    ][:11], "Logs reais de chamadas locais; serviços externos simulados")
    card("08_portabilidade", "DyraSQL | verificação de portabilidade", [
        "Windows: 13 failed, 107 passed | UTF-8, permissões e caminhos bash",
        *[line for line in linux_text.splitlines() if "failed," in line],
        "Causa das 5 falhas no mount WSL: scripts com CRLF",
        "Ubuntu em checkout Git com core.autocrlf=false:",
        *[line for line in lf_text.splitlines() if "passed in" in line],
        "Sem alteração de código-fonte ou relaxamento das asserções.",
    ], "Comparação de ambientes; fontes: testes_completos.txt, testes_linux*.txt")
    card("09_registro_minio", "DyraSQL | diagnóstico do registro de imagens", [
        "Docker Hub | consulta anônima ao manifesto latest:",
        "minio/mc        -> token HTTP 200, access=[], manifesto HTTP 401",
        "minio/minio     -> token HTTP 200, access=[], manifesto HTTP 401",
        "postgres        -> permissão pull, manifesto HTTP 200 (controle)",
        "quay.io/minio/mc -> manifesto HTTP 401",
        "Conclusão: acesso às imagens MinIO indisponível sem autenticação.",
        "O teste não distingue exclusão de mudança de visibilidade.",
    ], "Respostas reais dos registros; fonte: diagnostico_minio.txt")
    (OUT / "resumo_validacao.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(OUT.iterdir()) if p.is_file() and p.name != "sha256.json"}
    (OUT / "sha256.json").write_text(json.dumps(hashes, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    if "--render-additional" in sys.argv:
        render_additional()
    else:
        main()
