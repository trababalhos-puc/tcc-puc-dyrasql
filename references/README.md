# Referências - Artigos de Base para o TCC

Esta pasta contém todos os artigos científicos e documentos que servem como base teórica e metodológica para o desenvolvimento do TCC sobre **"Roteamento Dinâmico de Consultas SQL em Ambientes AWS Baseado em Metadados de Tabelas Iceberg"**.

## 📚 Artigos Disponíveis

### 1. Optimizing Cloud Data Lake Queries With a Balanced Coverage Plan
- **Foco**: Otimização de consultas em data lakes na nuvem
- **Relevância**: Base para estratégias de roteamento dinâmico
- **Páginas**: 16
- **Imagens**: 20 (gráficos, diagramas, tabelas de performance)

### 2. A Learned Cost Model-based Cross-engine Optimizer for SQL
- **Foco**: Otimizador baseado em modelo de custo aprendido
- **Relevância**: Metodologia para seleção de engines de processamento
- **Páginas**: 8
- **Imagens**: 8 (modelos de custo, algoritmos)

### 3. Adaptive and Robust Query Execution for Lakehouses at Scale
- **Foco**: Execução adaptativa de consultas em lakehouses
- **Relevância**: Técnicas de adaptação e robustez em ambientes distribuídos
- **Páginas**: 13
- **Imagens**: 12 (arquiteturas, fluxos de execução)

### 4. Intra-Query Runtime Elasticity for Cloud-Native Data Analysis
- **Foco**: Elasticidade em tempo de execução para análise de dados
- **Relevância**: Conceitos de escalabilidade dinâmica
- **Páginas**: 15
- **Imagens**: 33 (diagramas de elasticidade, métricas)

### 5. Automated Multidimensional Data Layouts in Amazon Redshift
- **Foco**: Layouts de dados multidimensionais automatizados
- **Relevância**: Otimização de estruturas de dados em AWS
- **Páginas**: 13
- **Imagens**: 18 (layouts, estruturas de dados)

## 🔄 Processamento Automático

Todos os PDFs são automaticamente processados para:

- **Conversão para Markdown**: Texto extraído e formatado
- **Extração de imagens**: Gráficos, diagramas e tabelas preservados
- **Organização**: Estrutura limpa com referências funcionais

### Comandos Úteis

```bash
# Converter todos os PDFs
make convert-referencias

# Limpar arquivos gerados
make clean-referencias

# Converter PDF específico
make pdf-to-md-images referencias/arquivo.pdf
```

## 📁 Estrutura dos Arquivos

Para cada artigo:
```
[nome_do_artigo].pdf                    # PDF original
[nome_do_artigo].md                     # Versão Markdown
[nome_do_artigo]_imagens/               # Pasta com imagens
├── imagem_p1_1.png                     # Imagens extraídas
├── pagina_2.png                        # Páginas renderizadas
└── ...
```

## 🎯 Aplicação no TCC

Estes artigos fornecem:

- **Base teórica** para roteamento dinâmico de consultas SQL
- **Metodologias** para otimização em ambientes AWS
- **Técnicas** de análise de metadados de tabelas Iceberg
- **Referências** para comparação de performance e custos
- **Exemplos práticos** de implementação em ambientes de nuvem

## 📝 Como Usar

1. **Consulta rápida**: Use os arquivos `.md` para leitura
2. **Referência visual**: Acesse as imagens nas pastas `_imagens/`
3. **Citação**: Use os PDFs originais para referências bibliográficas
4. **Análise**: Compare metodologias entre diferentes artigos

---

*Última atualização: $(date)*
*Total de artigos: 5*
*Total de imagens extraídas: 91*
