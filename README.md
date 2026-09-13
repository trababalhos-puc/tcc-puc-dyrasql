# DyraSQL - Roteamento Dinâmico de Consultas SQL

**Trabalho de Conclusão de Curso**  
**Sistemas de Informação - PUC Minas São Gabriel**

**Autor:** Aristides Henrique Gonçalves da Cruz  
**Orientador:** Prof. Gustavo Luís Soares

---

## Sobre

Este repositório contém o Trabalho de Conclusão de Curso sobre roteamento dinâmico de consultas SQL baseado em metadados de tabelas Apache Iceberg.

O DyraSQL é um framework que direciona automaticamente consultas para clusters Trino de capacidades distintas (small, medium, large), otimizando o uso de recursos através da análise de metadados obtidos via comando EXPLAIN (TYPE IO).

## Estrutura

O trabalho completo está disponível na branch `developer`:

```bash
git checkout developer
```

Esta branch `main` contém apenas informações básicas do projeto. Todo o desenvolvimento, código-fonte, documentação e monografia estão organizados na branch `developer`.

## Como Usar

### Clonar o repositório completo

```bash
git clone -b developer https://github.com/trababalhos-puc/tcc-puc-dyrasql.git
cd tcc-puc-dyrasql
```

### Estrutura da branch developer

- `src/` - Código-fonte do DyraSQL
- `latex/` - Monografia e apresentação
- `doc/` - PDFs de entrega e documentação
- `references/` - Referências bibliográficas
- `data/` - Dados dos experimentos
- `results/` - Resultados e métricas
- `tools/` - Scripts auxiliares

## Compilar a Monografia

```bash
make compile
```

## Executar o Software

Consulte o README na branch `developer` para instruções detalhadas de execução do software.

## Licença

MIT License - Veja o arquivo LICENSE na branch `developer`

## Contato

- **Aristides Henrique Gonçalves da Cruz**
- Email: arihenriquedev@hotmail.com
- PUC Minas - Instituto de Ciências Exatas e de Informática
