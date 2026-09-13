# Como Contribuir

Este projeto foi desenvolvido como Trabalho de Conclusão de Curso (TCC) da Pontifícia Universidade Católica de Minas Gerais (PUC Minas).

Contribuições que expandam e melhorem o framework DyraSQL são bem-vindas!

## Estrutura do Repositório

- `src/` - Código-fonte do framework (aceita contribuições)
- `latex/` - Monografia acadêmica (apenas correções)
- `doc/` - Documentação técnica
- `references/` - Referências bibliográficas
- `data/` - Dados de teste
- `results/` - Resultados experimentais
- `tools/` - Scripts auxiliares

## Como Contribuir

### 1. Reportar Bugs

Se encontrar um bug:

1. Verifique se já não existe uma [Issue](https://github.com/trababalhos-puc/tcc-puc-dyrasql/issues) aberta
2. Abra uma nova Issue com:
   - Título descritivo
   - Passos para reproduzir
   - Comportamento esperado vs atual
   - Logs relevantes
   - Versão do Docker/Sistema Operacional

**Exemplo**:
```
Título: Query com JOIN não roteia para cluster correto

Descrição:
Ao executar query com JOIN, o sistema roteia para Small quando deveria ir para Large.

Passos para reproduzir:
1. docker-compose up -d
2. Execute query: SELECT a.*, b.* FROM dados a JOIN tenant_info b ON a.tenant_id = b.tenant_id
3. Verificar logs: docker-compose logs dyrasql-core

Esperado: Roteamento para Large (score > 0.66)
Atual: Roteamento para Small (score = 0.15)

Logs:
INFO: Score final: 0.15 → Roteando para SMALL
```

### 2. Propor Melhorias

Para sugerir novas funcionalidades:

1. Abra uma Issue com label `enhancement`
2. Descreva:
   - Problema que resolve
   - Solução proposta
   - Alternativas consideradas
   - Impacto na arquitetura

**Exemplo**:
```
Título: Adicionar suporte a queries CTEs (Common Table Expressions)

Descrição:
Queries CTEs não são analisadas corretamente no fator de complexidade.

Solução proposta:
- Estender QueryAnalyzer para detectar CTEs no AST
- Adicionar peso 0.20 para CTEs no cálculo de complexidade
- Adicionar testes para queries com CTEs

Alternativas:
- Tratar CTEs como subqueries (peso 0.25)
- Ignorar CTEs (não recomendado)

Impacto:
- Mudança em query_analyzer.py
- Mudança em decision_engine.py
- Adicionar testes em tests/test_decision_engine.py
```

### 3. Contribuir com Código

#### Setup Inicial

```bash
# Fork o repositório no GitHub

# Clone seu fork
git clone https://github.com/seu-usuario/tcc-puc-dyrasql.git
cd tcc-puc-dyrasql

# Adicione remote upstream
git remote add upstream https://github.com/trababalhos-puc/tcc-puc-dyrasql.git

# Crie ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instale dependências
pip install -r src/dyrasql-core/requirements.txt
pip install pytest black flake8 mypy
```

#### Workflow de Desenvolvimento

```bash
# Certifique-se de estar na branch developer
git checkout developer
git pull upstream developer

# Crie branch para sua feature/fix
git checkout -b feature/nome-descritivo
# ou
git checkout -b fix/corrige-problema

# Faça suas alterações
# ... código ...

# Execute testes
cd src/dyrasql-core
pytest tests/

# Formate código
black *.py
flake8 *.py
mypy *.py

# Commit com mensagem semântica
git add .
git commit -m "feat: adiciona suporte a queries CTEs"

# Push para seu fork
git push origin feature/nome-descritivo

# Abra Pull Request no GitHub para branch developer
```

#### Convenções de Commits

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: nova funcionalidade
fix: correção de bug
docs: atualização de documentação
test: adiciona ou modifica testes
refactor: refatora código sem mudar comportamento
perf: melhoria de performance
chore: tarefas de manutenção
```

**Exemplos**:
```bash
git commit -m "feat: adiciona fator de custo ao algoritmo de decisão"
git commit -m "fix: corrige cálculo de fator histórico com cache vazio"
git commit -m "docs: atualiza README com instruções de instalação"
git commit -m "test: adiciona testes para queries com subqueries"
git commit -m "refactor: extrai cálculo de score para método separado"
git commit -m "perf: otimiza consulta ao cache PostgreSQL"
```

#### Padrões de Código

**Python Style**:
- Seguir PEP 8
- Usar Black para formatação automática
- Type hints obrigatórios para funções públicas

**Exemplo**:
```python
def calculate_score(
    self,
    volume: float,
    complexity: float,
    historical: float
) -> float:
    """
    Calcula score final baseado em fatores normalizados.
    
    Args:
        volume: Fator de volume (0-1)
        complexity: Fator de complexidade (0-1)
        historical: Fator histórico (0-1)
    
    Returns:
        Score final (0-1)
    """
    score = self.w1 * volume + self.w2 * complexity + self.w3 * historical
    return min(score, 1.0)
```

#### Testes

- Toda nova funcionalidade deve ter testes
- Cobertura mínima: 80%
- Use pytest

**Exemplo**:
```python
# tests/test_decision_engine.py
def test_calculate_score_with_high_volume():
    engine = DecisionEngine(db_url="sqlite:///:memory:")
    
    score = engine.calculate_score(
        volume=0.9,
        complexity=0.2,
        historical=0.1
    )
    
    # w1=0.5, w2=0.3, w3=0.2
    # esperado = 0.5*0.9 + 0.3*0.2 + 0.2*0.1 = 0.53
    assert abs(score - 0.53) < 0.01
```

#### Pull Request

Ao abrir um PR:

**Título**: Descrição clara e concisa

**Descrição**:
```markdown
## Problema
Descreva o problema que este PR resolve.

## Solução
Descreva a solução implementada.

## Testes
- [ ] Testes unitários adicionados
- [ ] Testes de integração passam
- [ ] Testado manualmente

## Checklist
- [ ] Código segue style guide (Black + Flake8)
- [ ] Type hints adicionados
- [ ] Documentação atualizada
- [ ] Testes com cobertura > 80%
- [ ] Commit messages seguem Conventional Commits
- [ ] Testado localmente com docker-compose

## Screenshots (se aplicável)
```

**Revisão**:
- PRs serão revisados por maintainers
- Feedback será fornecido
- Mudanças podem ser solicitadas
- Após aprovação, será merged para `developer`

### 4. Documentação

Contribuições para documentação são sempre bem-vindas:

- Corrigir erros
- Melhorar clareza
- Adicionar exemplos
- Traduzir documentos

Documentação está em:
- `README.md` (visão geral)
- `doc/` (documentação técnica)
- `docs/` (Sphinx - GitHub Pages)
- Docstrings no código

### 5. Monografia (LaTeX)

A monografia em `latex/` é um documento acadêmico finalizado. 

Apenas correções **críticas** são aceitas:
- Erros de digitação evidentes
- Referências quebradas
- Erros em equações

Abra uma Issue primeiro antes de fazer alterações no LaTeX.

## Branches

- **`main`** - Versão estável, releases oficiais
- **`developer`** - Desenvolvimento ativo (use para PRs)

**Nunca faça PR direto para `main`**. Sempre use `developer`.

## Issues e Labels

Labels disponíveis:
- `bug` - Algo não funciona
- `enhancement` - Nova funcionalidade
- `documentation` - Documentação
- `good first issue` - Bom para iniciantes
- `help wanted` - Procurando contribuidores
- `question` - Pergunta sobre o projeto

## Código de Conduta

- **Respeito**: Trate todos com respeito
- **Construção**: Críticas construtivas
- **Colaboração**: Trabalhe em equipe
- **Inclusão**: Todos são bem-vindos

## Suporte

Para dúvidas:

1. Consulte a [documentação](https://trababalhos-puc.github.io/tcc-puc-dyrasql/)
2. Busque em [Issues fechadas](https://github.com/trababalhos-puc/tcc-puc-dyrasql/issues?q=is%3Aissue+is%3Aclosed)
3. Abra uma nova Issue com tag `question`
4. Entre em contato: arihenriquedev@hotmail.com

## Licença

Ao contribuir, você concorda que suas contribuições serão licenciadas sob a [MIT License](LICENSE).

---

**Obrigado por contribuir com o DyraSQL!** 🚀

Seu apoio ajuda a evoluir este projeto além do escopo acadêmico original.
