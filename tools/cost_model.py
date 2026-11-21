"""Modelo analitico de custo: cluster unico vs. roteamento DyraSQL.

Custo = horas de no no mes x preco por no-hora. Cada cluster tem 1 coordenador
alem dos workers (replicas).

Cenarios:
  A: um cluster grande ligado 24/7 (superdimensionado);
  B: um cluster pequeno ligado 24/7 (subdimensionado);
  C: DyraSQL
     - small : 24/7, com replicas;
     - medium: apenas no horario comercial (dias uteis), menos replicas;
     - large : desligado; sobe sob demanda quando chega uma consulta pesada
               e desliga ao terminar (tempo de inicializacao e cobrado).

Preco padrao: m5.xlarge us-east-1, AWS Price List API (publicacao 2026-11-13):
EC2 On-Demand 0.192 + EMR 0.048 = 0.240 USD/h.

Uso: python tools/cost_model.py [--help]
"""
import argparse
import json
from pathlib import Path

DIAS_MES = 30


def nos(workers: int, coord: int) -> int:
    return workers + coord


def custo_c(a, pesadas_dia: float, duracao_h: float) -> dict:
    small = nos(a.small, a.coord) * 24 * DIAS_MES
    medium = nos(a.medium, a.coord) * a.horas_comerciais * a.dias_uteis
    large = nos(a.large, a.coord) * pesadas_dia * (duracao_h + a.startup_min / 60) * DIAS_MES
    return {"small": small, "medium": medium, "large": large, "total": small + medium + large}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--preco", type=float, default=0.24, help="US$ por no-hora (EC2 + EMR)")
    p.add_argument("--coord", type=int, default=1, help="coordenadores por cluster")
    p.add_argument("--small", type=int, default=2, help="replicas (workers) do small")
    p.add_argument("--medium", type=int, default=3, help="replicas (workers) do medium")
    p.add_argument("--large", type=int, default=10, help="replicas (workers) do large")
    p.add_argument("--horas-comerciais", type=float, default=10)
    p.add_argument("--dias-uteis", type=int, default=22)
    p.add_argument("--pesadas-dia", type=float, default=3, help="consultas pesadas por dia")
    p.add_argument("--duracao-h", type=float, default=0.5, help="duracao de cada consulta pesada")
    p.add_argument("--startup-min", type=float, default=10, help="tempo de subida do large")
    p.add_argument("--saida", default="latex/tabelas")
    a = p.parse_args()

    horas_a = nos(a.large, a.coord) * 24 * DIAS_MES
    horas_b = nos(a.small, a.coord) * 24 * DIAS_MES
    c = custo_c(a, a.pesadas_dia, a.duracao_h)

    def linha(h):
        return {"horas_no": round(h, 1), "custo": round(h * a.preco, 2),
                "economia_vs_A": round(1 - h / horas_a, 4)}

    resultado = {
        "parametros": vars(a),
        "cenarios": {"A": linha(horas_a), "B": linha(horas_b), "C": linha(c["total"]),
                     # D: roteamento DyraSQL, mas large mantido 24/7
                     "D": linha(c["small"] + c["medium"] + horas_a)},
        "C_por_cluster": {k: linha(v) for k, v in c.items() if k != "total"},
        "sensibilidade": [
            {"pesadas_dia": n, "duracao_h": d, **linha(custo_c(a, n, d)["total"])}
            for n in (1, 3, 6, 12) for d in (0.25, 0.5, 1, 2)
        ],
    }

    out = Path(a.saida)
    out.mkdir(parents=True, exist_ok=True)
    (out / "modelo_custo.json").write_text(json.dumps(resultado, indent=2), encoding="utf-8")
    print(json.dumps(resultado, indent=2))


if __name__ == "__main__":
    main()
