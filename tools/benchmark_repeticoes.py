"""Experimentos com repeticoes para o DyraSQL (stack local).

Modos:
  execucao --cluster X   aquecimento (1 execucao descartada) + N repeticoes de cada
                         consulta no cluster X, que deve estar ativo sozinho.
  decisao                N medidas da decisao sem cache (cache limpo antes de cada uma)
                         e N com cache, para cada consulta.
  historico              ensaio sequencial: decisao -> falha informada -> nova decisao.
  cache                  mesma estrutura com intervalos distintos sobre a particao.

Resultados acumulados em results/benchmark/repeticoes.json.
Uso: python tools/benchmark_repeticoes.py <modo> [--cluster small] [--n 5]
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from benchmark_routing import CLUSTERS, CONSULTAS, decidir, executar, post_json  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "results" / "benchmark" / "repeticoes.json"
METRICS = "http://localhost:5001/api/v1/metrics"


def carregar():
    return json.loads(SAIDA.read_text(encoding="utf-8")) if SAIDA.exists() else {}


def salvar(dados):
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")


def limpar_cache():
    subprocess.run(
        ["docker", "compose", "-f", str(RAIZ / "src" / "docker-compose.yml"), "exec", "-T",
         "gateway-db", "psql", "-U", "gateway", "-d", "dyrasql", "-q", "-c",
         "DELETE FROM routing_decisions"],
        check=True, capture_output=True,
    )


def modo_execucao(cluster, n):
    dados = carregar()
    res = dados.setdefault("execucao", {}).setdefault(cluster, {})
    for qid, sql in CONSULTAS:
        executar(CLUSTERS[cluster], sql)  # aquecimento, descartado
        medidas = []
        for _ in range(n):
            ok, s, err = executar(CLUSTERS[cluster], sql)
            medidas.append({"ok": ok, "s": round(s, 3), "erro": err})
        res[qid] = medidas
        print(qid, cluster, [m["s"] if m["ok"] else m["erro"] for m in medidas], flush=True)
        salvar(dados)


def modo_decisao(n):
    dados = carregar()
    res = dados.setdefault("decisao", {})
    for qid, sql in CONSULTAS:
        miss, hit, decisoes = [], [], set()
        for _ in range(n):
            limpar_cache()
            r, ms = decidir(sql)
            miss.append(round(ms, 1))
            decisoes.add(r["cluster"])
        for _ in range(n):
            r, ms = decidir(sql)
            hit.append(round(ms, 1))
            assert r.get("cached") is True
        res[qid] = {"miss_ms": miss, "hit_ms": hit, "cluster": sorted(decisoes),
                    "score": round(r["score"], 3)}
        print(qid, sorted(decisoes), miss, hit, flush=True)
        salvar(dados)


def informar(fingerprint, sucesso):
    post_json(METRICS, {"fingerprint": fingerprint, "metrics": {"success": sucesso}})


def modo_historico():
    """Consulta leve (C09) com falhas sucessivas informadas a API."""
    sql = dict(CONSULTAS)["C09"]
    limpar_cache()
    passos = []
    r, _ = decidir(sql)
    passos.append({"etapa": "sem historico", "cluster": r["cluster"], "score": round(r["score"], 3),
                   "f_h": r["factors"]["historical"]})
    for _ in range(3):
        informar(r["fingerprint"], False)
        anterior = r["cluster"]
        r, _ = decidir(sql)
        passos.append({"etapa": f"apos falha no {anterior}", "cluster": r["cluster"],
                       "score": round(r["score"], 3), "f_h": r["factors"]["historical"],
                       "cached": r.get("cached")})
    informar(r["fingerprint"], True)
    r, _ = decidir(sql)
    passos.append({"etapa": "apos sucesso (cache valido)", "cluster": r["cluster"],
                   "score": round(r["score"], 3), "cached": r.get("cached")})
    dados = carregar()
    dados["historico"] = passos
    salvar(dados)
    print(json.dumps(passos, indent=2, ensure_ascii=False))


def modo_cache():
    base = ("SELECT sum(valor) FROM iceberg.analytics.dados "
            "WHERE date BETWEEN TIMESTAMP '{}' AND TIMESTAMP '{}'")
    casos = [("1 dia", "2024-01-01", "2024-01-01"), ("1 trimestre", "2024-01-01", "2024-03-31"),
             ("1 dia (outro)", "2024-02-10", "2024-02-10")]
    limpar_cache()
    linhas = []
    for nome, ini, fim in casos:
        r, ms = decidir(base.format(ini, fim))
        linhas.append({"caso": nome, "fingerprint": r["fingerprint"][:12], "cluster": r["cluster"],
                       "score": round(r["score"], 3), "f_v": round(r["factors"]["volume"], 3),
                       "cached": r.get("cached"), "ms": round(ms, 1)})
    dados = carregar()
    dados["cache"] = linhas
    salvar(dados)
    print(json.dumps(linhas, indent=2, ensure_ascii=False))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("modo", choices=["execucao", "decisao", "historico", "cache"])
    p.add_argument("--cluster", choices=list(CLUSTERS))
    p.add_argument("--n", type=int, default=5)
    a = p.parse_args()
    t0 = time.time()
    if a.modo == "execucao":
        modo_execucao(a.cluster, a.n)
    elif a.modo == "decisao":
        modo_decisao(a.n)
    elif a.modo == "historico":
        modo_historico()
    else:
        modo_cache()
    print(f"tempo total: {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
