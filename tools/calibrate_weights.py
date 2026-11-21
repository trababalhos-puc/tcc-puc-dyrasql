"""Calibracao de pesos e limiares do DyraSQL sobre o benchmark medido.

Recalcula f_c com o elemento "memory_intensive" (coeficiente c_m) a partir do
SQL de cada consulta, reaproveita f_v e f_h medidos, e busca em grade
(w1, w2, w3, limiar small, limiar medium, c_m) que:
  1. nao subdimensiona nenhuma consulta (restricao: falha por memoria);
  2. maximiza o acerto do cluster de referencia;
  3. desempata pela configuracao mais proxima da original (0.5/0.3/0.2, 0.3/0.7).
Avalia generalizacao por leave-one-out.

Uso: python tools/calibrate_weights.py [--entrada results/benchmark/benchmark.json]
"""
import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "dyrasql-core"))
logging.disable(logging.CRITICAL)
from query_analyzer import QueryAnalyzer  # noqa: E402

ORDEM = ["small", "medium", "large"]
COEF = {"joins": 0.2, "aggregations": 0.15, "subqueries": 0.25,
        "partitioned_filters": 0.02, "non_partitioned_filters": 0.1}
LIMITE = 2.0
GRADE = [i / 20 for i in range(21)]
C_M = [0.25, 0.5, 1.0, 1.5, 2.0]
ORIGINAL = (0.5, 0.3, 0.2, 0.3, 0.7)


def f_c(cx, c_m):
    s = sum(cx[k] * v for k, v in COEF.items()) + cx.get("memory_intensive", 0) * c_m
    return min(1.0, s / LIMITE)


def classifica(s, a, b):
    return "small" if s < a else ("medium" if s <= b else "large")


def avalia(linhas, cfg):
    w1, w2, w3, a, b, c_m = cfg
    acertos = sub = 0
    for r in linhas:
        c = classifica(w1 * r["f_v"] + w2 * f_c(r["cx"], c_m) + w3 * r["f_h"], a, b)
        acertos += c == r["referencia"]
        sub += ORDEM.index(c) < ORDEM.index(r["referencia"])
    return acertos, sub


def distancia(cfg):
    return sum(abs(x - y) for x, y in zip(cfg[:5], ORIGINAL))


def configs():
    for c_m in C_M:
        for w1 in GRADE:
            for w2 in GRADE:
                w3 = round(1 - w1 - w2, 2)
                if w3 < 0:
                    continue
                for a in GRADE:
                    for b in GRADE:
                        if b > a:
                            yield (w1, w2, w3, a, b, c_m)


def melhor(linhas):
    best = None
    for cfg in configs():
        ac, sub = avalia(linhas, cfg)
        if sub:
            continue
        chave = (ac, -distancia(cfg))
        if best is None or chave > best[0]:
            best = (chave, cfg)
    return best[1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--entrada", default="results/benchmark/benchmark.json")
    a = p.parse_args()
    qa = QueryAnalyzer()
    linhas = [r for r in json.loads(Path(a.entrada).read_text(encoding="utf-8")) if r["referencia"]]
    for r in linhas:
        r["cx"] = qa.analyze_complexity(r["sql"])

    original = avalia(linhas, ORIGINAL + (0.0,))
    cfg = melhor(linhas)
    ac, sub = avalia(linhas, cfg)

    loo = 0
    for i, r in enumerate(linhas):
        treino = linhas[:i] + linhas[i + 1:]
        c = melhor(treino)
        loo += avalia([r], c)[0]

    res = {
        "n": len(linhas),
        "original_sem_memoria": {"acertos": original[0], "subdimensionadas": original[1]},
        "calibrado": {"w1": cfg[0], "w2": cfg[1], "w3": cfg[2], "limiar_small": cfg[3],
                      "limiar_medium": cfg[4], "c_m": cfg[5], "acertos": ac, "subdimensionadas": sub},
        "leave_one_out_acertos": loo,
    }
    print(json.dumps(res, indent=2))
    Path(a.entrada).with_name("calibracao.json").write_text(json.dumps(res, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
