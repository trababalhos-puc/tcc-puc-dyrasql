# Reprodução dos experimentos do TCC

Este roteiro reproduz os resultados da Seção 5 (Experimentos e Resultados) do artigo
"Roteamento Dinâmico de Consultas SQL Baseado em Metadados de Tabelas Apache Iceberg".
A versão do código usada no artigo está marcada pela tag `tcc-v1.0`.

## Requisitos

- Docker com pelo menos 8 GB de memória disponíveis para os containers.
- Python 3.11 (os scripts de `tools/` usam apenas a biblioteca padrão, exceto a
  calibração, que importa o `query_analyzer` do DyraSQL e requer `sqlglot`).

## 1. Subir a stack e carregar os dados

```sh
git checkout tcc-v1.0
cd src && docker compose up -d --build && cd ..
# a carga inicial (180.000 linhas) e feita pelo container iceberg-init
sh tools/ampliar_dados.sh          # 8 duplicacoes -> 46.080.000 linhas
```

A configuração calibrada (limiares 0,6/0,7, `T_max` = 3 GB, `R_max` = 46.080.000,
`c_m` = 1,5) está em `src/docker-compose.yml` e nos valores padrão do código.

## 2. Decisões e execuções (benchmark de 18 consultas)

As consultas C01 a C18 estão em `tools/benchmark_routing.py`. Como a máquina de 8 GB
não comporta os três clusters ao mesmo tempo, cada cluster é medido sozinho:

```sh
# com apenas trino-small ativo (necessario para o EXPLAIN do DyraSQL)
python tools/benchmark_repeticoes.py decisao --n 5
python tools/benchmark_repeticoes.py historico
python tools/benchmark_repeticoes.py cache
python tools/benchmark_repeticoes.py execucao --cluster small --n 5
# parar trino-small e subir apenas trino-medium
python tools/benchmark_repeticoes.py execucao --cluster medium --n 5
# parar trino-medium e subir apenas trino-large
python tools/benchmark_repeticoes.py execucao --cluster large --n 5
```

Cada execução de cluster faz 1 rodada de aquecimento (descartada) seguida de 5
repetições, na ordem C01 a C18.

## 3. Análise, calibração e validação cruzada

```sh
python tools/analise_repeticoes.py
```

Gera `results/benchmark/analise.json` com medianas e dispersão por consulta e cluster,
clusters de referência para tolerâncias de 1,25x, 1,5x e 2x, a calibração por busca em
grade e o leave-one-out com o resultado de cada fold.

## 4. Testes automatizados

```sh
pip install -r requirements-dev.txt -r src/dyrasql-core/requirements.txt
python -m pytest tests
```

Os testes de sintaxe dos scripts shell exigem ambiente Linux.
