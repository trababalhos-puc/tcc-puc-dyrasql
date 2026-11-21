"""Gera latex/modulos/apendice_d.tex a partir de results/benchmark/analise.json."""

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
a = json.loads((RAIZ / "results" / "benchmark" / "analise.json").read_text(encoding="utf-8"))
ABR = {"small": "S", "medium": "M", "large": "L", None: "--"}


def num(x, casas=2):
    return f"{x:.{casas}f}".replace(".", ",")


def celula(t):
    if not t["ok"]:
        return f"falha ({t['falhas']}/{t['n']})"
    return f"{num(t['mediana'])} ({num(t['cv'])})"


linhas_disp = []
for qid, c in a["consultas"].items():
    t = c["tempos"]
    r = c["referencia"]
    linhas_disp.append(
        f"\t{qid} & {celula(t['small'])} & {celula(t['medium'])} & {celula(t['large'])} & "
        f"{ABR[r['1.25']]} / {ABR[r['1.5']]} / {ABR[r['2.0']]} \\\\"
    )

linhas_fold = []
for f in a["leave_one_out"]["folds"]:
    w = " / ".join(num(x) for x in f["w"])
    lim = " / ".join(num(x) for x in f["limiares"])
    res = "acerto" if f["acerto"] else ("subdimensionou" if f["subdimensionou"] else "superdimensionou")
    linhas_fold.append(f"\t{f['fora']} & {ABR[f['referencia']]} & {w} & {lim} & {num(f['c_m'], 2)} & {res} \\\\")

lat = a["latencia_decisao_ms"]
tex = r"""\newpage

\begin{center}
\textbf{APÊNDICE D - PROTOCOLO, DISPERSÃO E VALIDAÇÃO CRUZADA}
\end{center}

\vspace{0.5cm}

\textbf{Protocolo.} Cada \textit{cluster} foi medido sozinho. Para cada consulta, executou-se uma rodada de aquecimento, descartada, seguida de 5 repetições, na ordem C01 a C18. O tempo de referência é a mediana das 5 repetições, e uma consulta é viável em um \textit{cluster} somente se não falhou em nenhuma delas. A decisão foi medida 5 vezes com \textit{cache} vazio, apagando as decisões antes de cada medida, e 5 vezes com \textit{cache}. Os \textit{scripts} utilizados são \texttt{tools/\allowbreak benchmark\_\allowbreak repeticoes.py} e \texttt{tools/\allowbreak analise\_\allowbreak repeticoes.py}.

\textbf{Dataset.} A tabela \textit{dados} tem 46.080.000 linhas em 90 partições diárias (1 de janeiro a 30 de março de 2024), com exatamente 512.000 linhas por partição, 50 \textit{tenants} com 921.600 linhas cada, 90\% dos registros com \textit{status} ATIVO e 10\% INATIVO, valores entre 0,38 e 11.058,74 (média de 509,66) e cerca de 44,7 milhões de chaves \textit{surrogate\_key} distintas (estimativa aproximada). A tabela \textit{tenant\_info} tem 50 linhas, 3 categorias e níveis de 1 a 10.

\textbf{Latência da decisão.} Sem \textit{cache} ($n = """ + str(lat["sem_cache"]["n"]) + r"""$): p50 de """ + num(lat["sem_cache"]["p50"], 1) + r""" ms, p90 de """ + num(lat["sem_cache"]["p90"], 1) + r""" ms, p95 de """ + num(lat["sem_cache"]["p95"], 1) + r""" ms e máximo de """ + num(lat["sem_cache"]["max"], 1) + r""" ms. Com \textit{cache} ($n = """ + str(lat["com_cache"]["n"]) + r"""$): p50 de """ + num(lat["com_cache"]["p50"], 1) + r""" ms, p90 de """ + num(lat["com_cache"]["p90"], 1) + r""" ms, p95 de """ + num(lat["com_cache"]["p95"], 1) + r""" ms e máximo de """ + num(lat["com_cache"]["max"], 1) + r""" ms.

\begin{center}
\textbf{Quadro 5 - Mediana do tempo (s), coeficiente de variação e referência por tolerância}
\end{center}

\begin{center}
\footnotesize
\begin{tabular}{lcccc}
\hline
\textbf{ID} & \textbf{Small} & \textbf{Medium} & \textbf{Large} & \textbf{Ref. (1,25 / 1,5 / 2,0)} \\
\hline
""" + "\n".join(linhas_disp) + r"""
\hline
\end{tabular}
\end{center}

\fonte{Elaborado pelo autor. Entre parênteses, o coeficiente de variação das 5 repetições ou o número de falhas.}

\textbf{Validação cruzada.} Em cada \textit{fold}, uma consulta elegível foi excluída, a busca em grade completa (pesos, limiares e $c_m$) foi refeita com as outras 14, e a configuração resultante classificou a consulta excluída. A escolha do elemento $M$ e do conjunto de valores de $c_m$ foi feita antes, sobre todas as consultas, e não é refeita por \textit{fold}.

\begin{center}
\textbf{Quadro 6 - Resultado de cada \textit{fold} do \textit{leave-one-out}}
\end{center}

\begin{center}
\footnotesize
\begin{tabular}{lccccl}
\hline
\textbf{Excluída} & \textbf{Ref.} & \textbf{Pesos} & \textbf{Limiares} & $c_m$ & \textbf{Resultado} \\
\hline
""" + "\n".join(linhas_fold) + r"""
\hline
\end{tabular}
\end{center}

\fonte{Elaborado pelo autor.}

\begin{center}
\textbf{Quadro 7 - Suítes de testes automatizados}
\end{center}

\begin{center}
\footnotesize
\begin{tabular}{lrl}
\hline
\textbf{Arquivo} & \textbf{Testes} & \textbf{Escopo} \\
\hline
\texttt{test\_query\_analyzer.py} & 24 & análise SQL, \textit{fingerprint} e \textit{EXPLAIN} \\
\texttt{test\_decision\_engine.py} & 11 & fatores, faixas e piso após falha \\
\texttt{test\_history\_manager.py} & 17 & \textit{cache} e fator histórico \\
\texttt{test\_api\_route.py} & 19 & API de roteamento e métricas \\
\texttt{test\_trino\_gateway\_proxy.py} & 34 & \textit{proxy} do \textit{Trino Gateway} \\
\texttt{test\_scripts\_shell.py} & 13 & sintaxe dos \textit{scripts} do ambiente \\
demais arquivos & 23 & geração de dados e casos auxiliares \\
\hline
\textbf{Total} & \textbf{141} & executados com \texttt{python -m pytest tests} \\
\hline
\end{tabular}
\end{center}

\fonte{Elaborado pelo autor. Testes unitários e de integração com dependências simuladas; não substituem os ensaios de desempenho.}
"""
(RAIZ / "latex" / "modulos" / "apendice_d.tex").write_text(tex, encoding="utf-8")
print("ok")
