# Documentação DyraSQL (Sphinx)

Esta pasta contém a documentação técnica do projeto DyraSQL, construída com Sphinx e hospedada no GitHub Pages.

## Acesso Online

🌐 **Documentação publicada:** [https://trababalhos-puc.github.io/tcc-puc-dyrasql/](https://trababalhos-puc.github.io/tcc-puc-dyrasql/)

A documentação é automaticamente construída e publicada quando há push para as branches `developer` ou `main`.

## Compilar Localmente

### Requisitos

- Python 3.9+
- pip

### Instalação

```bash
# Instalar dependências
pip install -r requirements.txt
```

### Build

```bash
# Compilar documentação HTML
make html

# Ou diretamente com sphinx-build
sphinx-build -b html . _build/html
```

### Visualizar

Abra `_build/html/index.html` no navegador:

```bash
# Linux/Mac
open _build/html/index.html

# Ou com servidor local
python3 -m http.server 8000 -d _build/html
# Acesse http://localhost:8000
```

### Live Reload (Desenvolvimento)

```bash
# Instalar sphinx-autobuild
pip install sphinx-autobuild

# Iniciar servidor com reload automático
make livehtml

# Ou diretamente
sphinx-autobuild . _build/html
# Acesse http://localhost:8000
```

## Estrutura

```
docs/
├── conf.py                 # Configuração Sphinx
├── index.rst               # Página inicial
├── introducao.md           # Introdução
├── arquitetura.md          # Arquitetura detalhada
├── instalacao.md           # Guia de instalação
├── uso.md                  # Guia de uso
├── api.md                  # Referência da API
├── desenvolvimento.md      # Guia de desenvolvimento
├── contributing.md         # Como contribuir
├── license.md              # Licença
├── requirements.txt        # Dependências Python
├── Makefile                # Comandos make
├── .nojekyll               # GitHub Pages
├── _static/                # Arquivos estáticos
├── _templates/             # Templates customizados
└── _build/                 # Saída (não commitado)
```

## Atualizar Documentação

### 1. Editar Conteúdo

Arquivos Markdown (`.md`) ou reStructuredText (`.rst`) em `docs/`

### 2. Testar Localmente

```bash
make html
open _build/html/index.html
```

### 3. Commit e Push

```bash
git add docs/
git commit -m "docs: atualiza documentação X"
git push origin developer
```

### 4. GitHub Pages

O GitHub Actions automaticamente:
1. Compila a documentação
2. Publica em GitHub Pages
3. Disponibiliza em https://trababalhos-puc.github.io/tcc-puc-dyrasql/

## Formatação

### Markdown (MyST)

A maioria dos arquivos usa Markdown com extensão MyST:

```markdown
# Título

## Subtítulo

**Negrito** e *itálico*

- Lista
- Item

\`\`\`python
# Código
def example():
    pass
\`\`\`

[Link](https://example.com)
```

### reStructuredText

O arquivo `index.rst` usa RST para melhor controle:

```rst
Título
======

.. toctree::
   :maxdepth: 2

   pagina1
   pagina2
```

## Temas

Tema atual: **Read the Docs** (`sphinx_rtd_theme`)

Para trocar, edite `conf.py`:

```python
html_theme = 'alabaster'  # ou 'sphinx_book_theme', 'furo', etc.
```

## Extensões

Extensões habilitadas em `conf.py`:

- `sphinx.ext.autodoc` - Documentação automática de código
- `sphinx.ext.napoleon` - Suporte a docstrings Google/NumPy
- `sphinx.ext.viewcode` - Links para código-fonte
- `sphinx.ext.githubpages` - Suporte a GitHub Pages
- `myst_parser` - Suporte a Markdown

## Troubleshooting

### Erro: Module not found

```bash
pip install -r requirements.txt --upgrade
```

### Erro: Build failed

```bash
# Limpar build anterior
make clean

# Recompilar
make html
```

### GitHub Pages não atualiza

1. Verifique workflow: Actions → Deploy Sphinx Documentation
2. Certifique-se que GitHub Pages está configurado:
   - Settings → Pages → Source: GitHub Actions

## Contribuindo

Para contribuir com a documentação, veja [contributing.md](contributing.md).

---

**Projeto**: DyraSQL  
**Autor**: Aristides Henrique Gonçalves da Cruz  
**Instituição**: PUC Minas  
**Ano**: 2026
