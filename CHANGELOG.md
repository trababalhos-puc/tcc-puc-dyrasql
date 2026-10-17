# Changelog

Todas as mudancas relevantes deste projeto sao documentadas neste arquivo.

O formato e baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Versionamento Semantico](https://semver.org/lang/pt-BR/).

## [Unreleased]

### Added
- Workflow de Release no GitHub Actions (tag `v*.*.*`)
- Release Drafter para rascunho automatico de notas
- Alvo `make release` para publicar tag e acionar a release
- Imagem unica `dyrasql-platform` (MinIO e Trino Gateway) em `src/platform/`, publicada em `ghcr.io/trababalhos-puc/dyrasql-platform` para amd64 e arm64
- Codigo-fonte do MinIO (RELEASE.2025-10-15T17-29-55Z) e do Trino Gateway (21) em `src/vendor/`, com versoes e commits em `src/vendor/VERSIONS.md`
- Script `src/scripts/publish-platform.sh` para publicar a imagem da plataforma
- Secao "Imagens e Dependencias" no `src/README.md`

### Changed
- Imagens base fixadas por digest (Trino 484, PostgreSQL 16.15, AWS CLI 2.38.1, Alpine 3.24.2, Iceberg REST 1.6.0, Python 3.11, Temurin 25 e Go 1.24)
- Servicos `minio` e `trino-gateway` passam a usar a imagem `dyrasql-platform` no lugar de imagens e builds separados
- Bucket `warehouse` criado com `amazon/aws-cli` em vez de `minio/mc`, que saiu do Docker Hub
- Diretorio de dados dos clusters Trino movido para `/tmp/trino-data`, sem volumes persistentes
- Badge de versao do README passa a ler tags em vez de releases publicadas

### Fixed
- Carga de dados sinteticos compativel com o limite de 10.000 entradas de `SEQUENCE` do Trino atual
- Script `validar.sh` reconhece o status dos containers no Docker Compose atual
- Execucao do ambiente apos a descontinuacao do MinIO (repositorio arquivado em 25/04/2026)

### Removed
- Dockerfiles separados de `src/minio/` e `src/trino-gateway/`

## [1.0.0] - 2026-09-20

### Added
- Suite pytest com cobertura minima de 90% em `src/`
- Workflow CI de test e lint (Ruff + pytest)
- Configuracao Poetry (`package-mode = false`) e `pyproject.toml`

### Changed
- Padronizacao de lint/format com Ruff no codigo Python
- Renomeacao de `add-h2-dependency.py` para `add_h2_dependency.py`

### Removed
- Codigo Terraform legado em `src/terraform/`

[Unreleased]: https://github.com/trababalhos-puc/tcc-puc-dyrasql/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/trababalhos-puc/tcc-puc-dyrasql/releases/tag/v1.0.0
