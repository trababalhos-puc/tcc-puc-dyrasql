"""Analise das medidas repetidas (results/benchmark/repeticoes.json).

Gera results/benchmark/analise.json com:
  - mediana, minimo, maximo e coeficiente de variacao por consulta e cluster;
  - cluster de referencia para tolerancias de 1,25x, 1,5x e 2x;
  - calibracao (busca em grade) e leave-one-out com resultado por fold;
  - percentis da latencia de decisao com e sem cache.

Pipeline do leave-one-out: para cada consulta i, a busca em grade completa
(pesos, limiares e c_m) e refeita apenas com as demais; a configuracao obtida
classifica a consulta i. A escolha do elemento M e do conjunto de valores de c_m
foi feita antes, sobre todas as consultas (ver Secao 5), e nao e refeita por fold.

Uso: python tools/analise_repeticoes.py
"""

import json
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from calibrate_weights import ORDEM, ORIGINAL, QueryAnalyzer, avalia, melhor  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
BENCH = RAIZ / "results" / "benchmark"
TOLERANCIAS = (1.25, 1.5, 2.0)


def percentil(valores, p):
    v = sorted(valores)
    k = (len(v) - 1) * p / 100
    i, f = int(k), k - int(k)
    return v[i] + (v[min(i + 1, len(v) - 1)] - v[i]) * f


def resumo_tempos(medidas):
    oks = [m["s"] for m in medidas if m["ok"]]
    if len(oks) < len(medidas):
        return {"ok": False, "falhas": len(medidas) - len(oks), "n": len(medidas)}
    med = st.median(oks)
    cv = st.pstdev(oks) / st.mean(oks) if len(oks) > 1 else 0.0
    return {"ok": True, "n": len(oks), "mediana": round(med, 3), "min": min(oks),
            "max": max(oks), "cv": round(cv, 3)}


def referencia(tempos, tol):
    ok = {c: t["mediana"] for c, t in tempos.items() if t["ok"]}
    if not ok:
        return None
    melhor_t = min(ok.values())
    for c in ORDEM:
        if c in ok and ok[c] <= tol * melhor_t:
            return c
    return None


def main():
    rep = json.loads((BENCH / "repeticoes.json").read_text(encoding="utf-8"))
    base = {r["id"]: r for r in json.loads((BENCH / "benchmark.json").read_text(encoding="utf-8"))}
    qa = QueryAnalyzer()

    consultas = {}
    for qid, r in base.items():
        tempos = {c: resumo_tempos(rep["execucao"][c][qid]) for c in ORDEM}
        consultas[qid] = {"tempos": tempos,
                          "referencia": {str(t): referencia(tempos, t) for t in TOLERANCIAS}}

    # calibracao e leave-one-out com a referencia de 1,5x (medianas)
    linhas = []
    for qid, r in base.items():
        ref = consultas[qid]["referencia"]["1.5"]
        if ref is None:
            continue
        linhas.append({"id": qid, "f_v": r["f_v"], "f_h": r["f_h"], "referencia": ref,
                       "cx": qa.analyze_complexity(r["sql"])})
    cfg = melhor(linhas)
    acertos, sub = avalia(linhas, cfg)
    original = avalia(linhas, ORIGINAL + (0.0,))
    folds = []
    for i, r in enumerate(linhas):
        c = melhor(linhas[:i] + linhas[i + 1:])
        ac, sb = avalia([r], c)
        folds.append({"fora": r["id"], "referencia": r["referencia"],
                      "w": c[:3], "limiares": c[3:5], "c_m": c[5], "acerto": bool(ac),
                      "subdimensionou": bool(sb)})

    # sensibilidade: acerto da configuracao calibrada sob outras tolerancias
    sens = {}
    for t in TOLERANCIAS:
        ls = []
        for l in linhas:
            ref = consultas[l["id"]]["referencia"][str(t)]
            if ref is not None:
                ls.append({**l, "referencia": ref})
        a, s = avalia(ls, cfg)
        sens[str(t)] = {"elegiveis": len(ls), "acertos": a, "subdimensionadas": s}

    miss = [v for d in rep["decisao"].values() for v in d["miss_ms"]]
    hit = [v for d in rep["decisao"].values() for v in d["hit_ms"]]
    lat = {nome: {"n": len(v), "p50": round(percentil(v, 50), 1), "p90": round(percentil(v, 90), 1),
                  "p95": round(percentil(v, 95), 1), "max": max(v)}
           for nome, v in (("sem_cache", miss), ("com_cache", hit))}

    saida = {
        "consultas": consultas,
        "elegiveis": [l["id"] for l in linhas],
        "original": {"acertos": original[0], "subdimensionadas": original[1]},
        "calibrada": {"w": cfg[:3], "limiares": cfg[3:5], "c_m": cfg[5], "acertos": acertos,
                      "subdimensionadas": sub},
        "leave_one_out": {"acertos": sum(f["acerto"] for f in folds),
                          "subdimensionadas": sum(f["subdimensionou"] for f in folds),
                          "folds": folds},
        "sensibilidade_tolerancia": sens,
        "latencia_decisao_ms": lat,
    }
    (BENCH / "analise.json").write_text(json.dumps(saida, indent=2, ensure_ascii=False),
                                        encoding="utf-8")
    print(json.dumps({k: v for k, v in saida.items() if k != "consultas"}, indent=1,
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
