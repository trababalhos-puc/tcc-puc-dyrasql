"""Benchmark de roteamento do DyraSQL na stack local.

Para cada consulta:
  1. pede a decisao ao DyraSQL Core duas vezes (cache miss e cache hit),
     medindo a latencia da decisao;
  2. executa a consulta diretamente nos clusters small, medium e large,
     medindo tempo e registrando falhas (ex.: limite de memoria);
  3. define o cluster de referencia de forma independente do DyraSQL:
     o menor cluster que executa sem falha em ate TOLERANCIA x o melhor tempo.

Uso (stack no ar): python tools/benchmark_routing.py [--saida results/benchmark]
Somente biblioteca padrao.
"""
import argparse
import csv
import json
import time
import urllib.request
from pathlib import Path

CORE = "http://localhost:5001/api/v1/route"
CLUSTERS = {"small": "http://localhost:8081", "medium": "http://localhost:8082",
            "large": "http://localhost:8083"}
ORDEM = ["small", "medium", "large"]
TOLERANCIA = 1.5
TIMEOUT_S = 600

D = "iceberg.analytics.dados"
T = "iceberg.analytics.tenant_info"
CONSULTAS = [
    ("C01", f"SELECT count(*) FROM {T}"),
    ("C02", f"SELECT tenant_id, categoria FROM {T} WHERE nivel > 5"),
    ("C03", f"SELECT sum(valor) FROM {D} WHERE date = TIMESTAMP '2024-01-05'"),
    ("C04", f"SELECT status, count(*) FROM {D} WHERE date BETWEEN TIMESTAMP '2024-01-01' AND TIMESTAMP '2024-01-03' GROUP BY status"),
    ("C05", f"SELECT d.tenant_id, COUNT(*), SUM(d.valor) FROM {D} d JOIN {T} t ON d.tenant_id = t.tenant_id WHERE d.date = TIMESTAMP '2024-01-10' AND t.nivel > 5 GROUP BY d.tenant_id"),
    ("C06", f"SELECT max(valor), min(valor) FROM {D} WHERE date BETWEEN TIMESTAMP '2024-01-01' AND TIMESTAMP '2024-01-07'"),
    ("C07", f"SELECT sum(valor) FROM {D}"),
    ("C08", f"SELECT status, count(*), avg(valor) FROM {D} GROUP BY status"),
    ("C09", f"SELECT d.tenant_id, COUNT(*), SUM(d.valor) FROM {D} d JOIN {T} t ON d.tenant_id = t.tenant_id WHERE d.date >= TIMESTAMP '2024-01-01' AND t.nivel > 5 GROUP BY d.tenant_id"),
    ("C10", f"SELECT tenant_id, date_trunc('day', date), sum(valor) FROM {D} WHERE date < TIMESTAMP '2024-02-01' GROUP BY 1, 2"),
    ("C11", f"SELECT t.categoria, d.status, count(*), sum(d.valor) FROM {D} d JOIN {T} t ON d.tenant_id = t.tenant_id GROUP BY t.categoria, d.status"),
    ("C12", f"SELECT tenant_id, sum(valor) FROM {D} WHERE valor > (SELECT avg(valor) FROM {D} WHERE date = TIMESTAMP '2024-01-05') GROUP BY tenant_id"),
    ("C13", f"SELECT count(DISTINCT surrogate_key) FROM {D} WHERE date < TIMESTAMP '2024-02-01'"),
    ("C14", f"SELECT count(DISTINCT surrogate_key) FROM {D}"),
    ("C15", f"SELECT max(rn) FROM (SELECT row_number() OVER (PARTITION BY tenant_id ORDER BY valor) AS rn FROM {D})"),
    ("C16", f"SELECT count(*) FROM (SELECT surrogate_key FROM {D} GROUP BY surrogate_key HAVING count(*) > 1)"),
    ("C17", f"SELECT count(*) FROM {D} a JOIN {D} b ON a.surrogate_key = b.surrogate_key WHERE a.date < TIMESTAMP '2024-01-15'"),
    ("C18", f"SELECT count(*) FROM {D} a JOIN {D} b ON a.surrogate_key = b.surrogate_key"),
]


def post_json(url, payload, headers=None):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
        return json.loads(r.read())


def decidir(sql):
    t0 = time.perf_counter()
    r = post_json(CORE, {"query": sql})
    return r, (time.perf_counter() - t0) * 1000


def executar(base, sql):
    """Executa via REST do Trino seguindo nextUri. Retorna (ok, segundos, erro)."""
    t0 = time.perf_counter()
    req = urllib.request.Request(f"{base}/v1/statement", data=sql.encode(),
                                 headers={"X-Trino-User": "bench"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
            res = json.loads(r.read())
        while True:
            if "error" in res:
                return False, time.perf_counter() - t0, res["error"].get("errorName", "ERRO")
            nxt = res.get("nextUri")
            if not nxt:
                return True, time.perf_counter() - t0, None
            if time.perf_counter() - t0 > TIMEOUT_S:
                return False, time.perf_counter() - t0, "TIMEOUT"
            with urllib.request.urlopen(nxt, timeout=TIMEOUT_S) as r:
                res = json.loads(r.read())
    except Exception as e:  # noqa: BLE001
        return False, time.perf_counter() - t0, type(e).__name__


def referencia(execs):
    ok = {c: e["s"] for c, e in execs.items() if e["ok"]}
    if not ok:
        return None
    melhor = min(ok.values())
    for c in ORDEM:
        if c in ok and ok[c] <= TOLERANCIA * melhor:
            return c
    return None


def salvar(out, linhas):
    out.mkdir(parents=True, exist_ok=True)
    (out / "benchmark.json").write_text(json.dumps(linhas, indent=2), encoding="utf-8")
    with open(out / "benchmark.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(linhas[0]))
        w.writeheader()
        w.writerows(linhas)
    print(f"Acerto: {sum(x['acerto'] for x in linhas)}/{len(linhas)}")


def completar(out, cluster):
    linhas = json.loads((out / "benchmark.json").read_text(encoding="utf-8"))
    for linha in linhas:
        ok, s, err = executar(CLUSTERS[cluster], linha["sql"])
        linha[f"{cluster}_s"] = round(s, 2) if ok else None
        linha[f"{cluster}_erro"] = err
        execs = {c: {"ok": linha[f"{c}_s"] is not None, "s": linha[f"{c}_s"]} for c in ORDEM}
        ref = referencia(execs)
        linha["referencia"] = ref
        linha["acerto"] = linha["dyrasql"] == ref
        linha["subdimensionou"] = ref is not None and ORDEM.index(linha["dyrasql"]) < ORDEM.index(ref)
        print(linha["id"], cluster, linha[f"{cluster}_s"], err, flush=True)
    salvar(out, linhas)


def redecidir(out):
    linhas = json.loads((out / "benchmark.json").read_text(encoding="utf-8"))
    for linha in linhas:
        miss, ms_miss = decidir(linha["sql"])
        hit, ms_hit = decidir(linha["sql"])
        f = miss["factors"]
        ref = linha["referencia"]
        linha.update({
            "score": round(miss["score"], 3), "f_v": round(f["volume"], 3),
            "f_c": round(f["complexity"], 3), "f_h": round(f["historical"], 3),
            "dyrasql": miss["cluster"], "acerto": miss["cluster"] == ref,
            "subdimensionou": ref is not None and ORDEM.index(miss["cluster"]) < ORDEM.index(ref),
            "ms_decisao_miss": round(ms_miss, 1), "ms_decisao_hit": round(ms_hit, 1),
            "cache_hit": hit.get("cached"),
        })
        print(linha["id"], linha["score"], linha["dyrasql"], ref, flush=True)
    salvar(out, linhas)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--saida", default="results/benchmark")
    p.add_argument("--completar", choices=ORDEM,
                   help="reexecuta apenas este cluster sobre um benchmark.json existente "
                        "(util quando a maquina nao comporta os tres clusters ao mesmo tempo)")
    p.add_argument("--somente-decisao", action="store_true",
                   help="refaz apenas as decisoes do DyraSQL sobre um benchmark.json existente, "
                        "mantendo os tempos de execucao (ex.: apos recalibrar o algoritmo)")
    a = p.parse_args()
    if a.somente_decisao:
        redecidir(Path(a.saida))
        return
    if a.completar:
        completar(Path(a.saida), a.completar)
        return
    linhas = []
    for qid, sql in CONSULTAS:
        miss, ms_miss = decidir(sql)
        hit, ms_hit = decidir(sql)
        execs = {}
        for c in ORDEM:
            ok, s, err = executar(CLUSTERS[c], sql)
            execs[c] = {"ok": ok, "s": round(s, 2), "erro": err}
        ref = referencia(execs)
        f = miss["factors"]
        linha = {
            "id": qid, "score": round(miss["score"], 3), "f_v": round(f["volume"], 3),
            "f_c": round(f["complexity"], 3), "f_h": round(f["historical"], 3),
            "dyrasql": miss["cluster"], "referencia": ref,
            "acerto": miss["cluster"] == ref,
            "subdimensionou": ref is not None and ORDEM.index(miss["cluster"]) < ORDEM.index(ref),
            "ms_decisao_miss": round(ms_miss, 1), "ms_decisao_hit": round(ms_hit, 1),
            "cache_hit": hit.get("cached"),
            **{f"{c}_s": execs[c]["s"] if execs[c]["ok"] else None for c in ORDEM},
            **{f"{c}_erro": execs[c]["erro"] for c in ORDEM},
            "sql": sql,
        }
        linhas.append(linha)
        print(json.dumps({k: v for k, v in linha.items() if k != "sql"}), flush=True)

    out = Path(a.saida)
    out.mkdir(parents=True, exist_ok=True)
    (out / "benchmark.json").write_text(json.dumps(linhas, indent=2), encoding="utf-8")
    with open(out / "benchmark.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(linhas[0]))
        w.writeheader()
        w.writerows(linhas)
    acertos = sum(x["acerto"] for x in linhas)
    print(f"Acerto: {acertos}/{len(linhas)}")


if __name__ == "__main__":
    main()
