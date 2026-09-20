# DyraSQL - Roteamento Dinâmico de Consultas SQL

[![Compile LaTeX](https://github.com/trababalhos-puc/tcc-puc-dyrasql/actions/workflows/compile-latex.yml/badge.svg)](https://github.com/trababalhos-puc/tcc-puc-dyrasql/actions/workflows/compile-latex.yml)
[![Test and Lint](https://github.com/trababalhos-puc/tcc-puc-dyrasql/actions/workflows/test-lint.yml/badge.svg)](https://github.com/trababalhos-puc/tcc-puc-dyrasql/actions/workflows/test-lint.yml)
[![Release](https://img.shields.io/github/v/release/trababalhos-puc/tcc-puc-dyrasql?display_name=release)](https://github.com/trababalhos-puc/tcc-puc-dyrasql/releases)

**Trabalho de Conclusão de Curso**  
**Sistemas de Informação - PUC Minas São Gabriel**

**Autor:** Aristides Henrique Gonçalves da Cruz  
**Orientador:** Prof. Gustavo Luís Soares

---

## Sobre o Projeto

O DyraSQL é um framework para roteamento dinâmico de consultas SQL baseado em metadados de tabelas Apache Iceberg. O sistema analisa características das consultas antes da execução e as direciona automaticamente para clusters Trino de capacidades distintas (small, medium, large), otimizando o uso de recursos computacionais.

### Características Principais

- **Análise de Metadados**: Utiliza o comando `EXPLAIN (TYPE IO)` do Trino para obter informações sobre volume de dados e complexidade
- **Roteamento Inteligente**: Algoritmo de pontuação que combina volume de dados, complexidade da consulta e histórico de execuções
- **Cache de Decisões**: PostgreSQL para armazenar e reutilizar decisões de roteamento
- **Arquitetura Modular**: Componentes independentes (Gateway, Core, Proxy) facilitam manutenção e evolução

### Documentação

📚 **Documentação completa disponível em:** [https://trababalhos-puc.github.io/tcc-puc-dyrasql/](https://trababalhos-puc.github.io/tcc-puc-dyrasql/)

A documentação inclui:
- 🚀 Guia de instalação e configuração
- 🏗️ Arquitetura detalhada do sistema
- 📖 Referência completa da API
- 💻 Exemplos de uso e integração
- 🛠️ Guia de desenvolvimento e contribuição

## Estrutura do Repositório

```
├── src/                # Código-fonte do DyraSQL
│   ├── dyrasql-core/          # Motor de decisão
│   ├── trino-gateway/         # Gateway Trino
│   ├── trino-gateway-proxy/   # Proxy de interceptação
│   ├── trino/config/          # Configurações dos clusters
│   ├── scripts/               # Scripts auxiliares
│   └── docker-compose.yml     # Orquestração do ambiente
├── latex/              # Monografia e apresentação
│   ├── principal.tex          # Documento principal
│   ├── modulos/               # Capítulos da monografia
│   ├── figuras/               # Imagens e diagramas
│   ├── beamer/                # Apresentação de defesa
│   ├── bibliografia.bib       # Referências bibliográficas
│   ├── Dockerfile             # Build Docker para LaTeX
│   └── docker-compose.yml     # Orquestração da compilação LaTeX
├── docs/               # Documentação Sphinx + PDFs de entrega
│   ├── TCC_Aristides Henrique Gonçalves da Cruz.pdf
│   ├── principal.pdf          # PDF da monografia
│   └── arquitetura.md         # Documentação técnica
├── references/         # Papers e referências
├── data/               # Dados dos experimentos
├── results/            # Resultados e métricas
├── tools/              # Scripts utilitários
├── Makefile            # Automação de compilação
├── LICENSE             # Licença MIT
├── CITATION.cff        # Metadados de citação
└── CONTRIBUTING.md     # Guia de contribuição
```

## Como Usar

### Pré-requisitos

- **Para o Software**: Docker e Docker Compose
- **Para o LaTeX**: TeX Live completo ou MiKTeX

### Clonar o Repositório

```bash
git clone -b developer https://github.com/trababalhos-puc/tcc-puc-dyrasql.git
cd tcc-puc-dyrasql
```

### Executar o Software

#### 1. Subir o ambiente local

```bash
cd src
docker compose up -d
```

Aguarde o serviço `iceberg-init` concluir a inicialização.

#### 2. Acessar as interfaces

- **Proxy DyraSQL**: http://localhost:8080
- **DyraSQL Core**: http://localhost:5001
- **Trino Gateway**: http://localhost:8085
- **MinIO Console**: http://localhost:9001

#### 3. Executar consultas de teste

```bash
cd src
# Ver query.sql para exemplos
```

Detalhes completos em [`src/README.md`](src/README.md).

### Compilar a Monografia

#### Usando Make

```bash
make compile
```

#### Usando Docker

```bash
cd latex
docker-compose up
```

O PDF será gerado em `principal.pdf` e copiado para `../docs/`.

#### Compilar apresentação

```bash
make beamer
```

### Documentacao Tecnica

Consulte a [documentacao de arquitetura](docs/arquitetura.md) para detalhes tecnicos do projeto.

## Releases

As versoes do projeto sao publicadas em [GitHub Releases](https://github.com/trababalhos-puc/tcc-puc-dyrasql/releases).

1. Atualize `version` em `pyproject.toml` e `CITATION.cff`
2. Documente a versao em `CHANGELOG.md`
3. Ajuste `RELEASE_VERSION` no `Makefile` (padrao `1.0.0`)
4. Publique a tag:

```bash
make release
```

O workflow `Release` valida lint/testes e cria a release automaticamente a partir da tag `vX.Y.Z`.
O Release Drafter mantem um rascunho de notas a cada merge em `developer`/`main`.

## Resultados

O framework demonstrou eficácia na classificação e direcionamento de consultas através da análise sistemática de metadados. Os experimentos validaram que:

- O comando `EXPLAIN (TYPE IO)` fornece informações precisas sobre volume de dados
- O algoritmo de pontuação reflete adequadamente as características das consultas
- O cache de decisões reduz overhead de análise em consultas recorrentes

Resultados detalhados estão disponíveis na monografia em `docs/`.

## Tecnologias Utilizadas

### Software

- **Apache Iceberg**: Formato de tabela para data lake
- **Trino**: Engine de consultas SQL distribuído
- **PostgreSQL**: Armazenamento de cache e histórico
- **MinIO**: Armazenamento de objetos compatível com S3
- **Python + FastAPI**: API do DyraSQL Core
- **Docker**: Containerização e orquestração

### Monografia

- **LaTeX**: Sistema de tipografia
- **abntex2**: Formatação ABNT
- **Beamer**: Apresentação de defesa
- **GitHub Actions**: Compilação automatizada

## Contribuindo

Contribuições são bem-vindas! Consulte o [guia de contribuição](CONTRIBUTING.md) para detalhes sobre como colaborar com o projeto.

## Citação

Se você utilizar este trabalho em sua pesquisa, por favor cite:

```bibtex
@software{cruz2026dyrasql,
  author = {Cruz, Aristides Henrique Gonçalves da and Soares, Gustavo Luís},
  title = {DyraSQL: Roteamento Dinâmico de Consultas SQL Baseado em Metadados de Tabelas Apache Iceberg},
  year = {2026},
  url = {https://github.com/trababalhos-puc/tcc-puc-dyrasql},
  institution = {Pontifícia Universidade Católica de Minas Gerais}
}
```

Ou utilize o botão "Cite this repository" no GitHub (gerado automaticamente pelo `CITATION.cff`).

## Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

Os estilos e pacotes abntex2/Abakos seguem suas respectivas licenças (LPPL 1.3c).

## Contato

**Aristides Henrique Gonçalves da Cruz**
- Email: arihenriquedev@hotmail.com
- LinkedIn: [linkedin.com/in/aristides-cruz](https://linkedin.com/in/aristides-cruz)
- PUC Minas - Instituto de Ciências Exatas e de Informática

**Orientador: Prof. Gustavo Luís Soares**
- Email: gsoares@pucminas.br
- PUC Minas - ICEI

## Agradecimentos

- Prof. Gustavo Luís Soares pela orientação
- PUC Minas e ICEI pela infraestrutura e suporte acadêmico
- Comunidades Trino, Iceberg e de código aberto

---

**Desenvolvido como Trabalho de Conclusão de Curso**  
**PUC Minas - 2026**
