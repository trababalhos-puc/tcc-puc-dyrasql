# Changelog

Todas as mudancas relevantes deste projeto sao documentadas neste arquivo.

O formato e baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Versionamento Semantico](https://semver.org/lang/pt-BR/).

## [Unreleased]

### Added
- Workflow de Release no GitHub Actions (tag `v*.*.*`)
- Release Drafter para rascunho automatico de notas
- Alvo `make release` para publicar tag e acionar a release

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
