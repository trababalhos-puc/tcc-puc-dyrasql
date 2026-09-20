# Introdução

## Visão Geral

DyraSQL é um framework acadêmico desenvolvido como Trabalho de Conclusão de Curso (TCC) que implementa roteamento dinâmico de consultas SQL para múltiplos clusters Trino.

## Motivação

Com o crescimento exponencial de dados em ambientes de data lake, surge a necessidade de otimizar o processamento de consultas SQL. O DyraSQL propõe uma abordagem que:

- **Analisa metadados** previamente disponíveis em tabelas Apache Iceberg
- **Classifica consultas** automaticamente por complexidade e volume
- **Roteia inteligentemente** para clusters apropriados
- **Otimiza recursos** sem necessidade de execução prévia

## Características Principais

### Análise de Metadados
Utiliza o comando `EXPLAIN (TYPE IO)` do Trino para extrair:
- Tamanho efetivo dos dados (`outputSizeInBytes`)
- Número de linhas (`outputRowCount`)
- Estatísticas de otimização de leitura

### Algoritmo de Decisão
Implementa um score baseado em três fatores:

$$S = w_1 \cdot f_v + w_2 \cdot f_c + w_3 \cdot f_h$$

Onde:
- $f_v$: Fator de volume (tamanho e linhas)
- $f_c$: Fator de complexidade (análise AST da query)
- $f_h$: Fator histórico (decisões anteriores)
- $w_1, w_2, w_3$: Pesos configuráveis

### Cache Inteligente
- Armazena decisões de roteamento por fingerprint de consulta
- TTL configurável para evitar obsolescência
- Reutiliza decisões para consultas similares

## Arquitetura

O sistema é composto por:

1. **DyraSQL Core**: Motor de decisão e análise
2. **Trino Gateway Proxy**: Interceptador de consultas
3. **PostgreSQL**: Cache de decisões
4. **Múltiplos Clusters Trino**: Small, Medium, Large

## Tecnologias

- **Apache Iceberg**: Formato de tabela para data lakes
- **Trino**: Engine de consultas SQL distribuído
- **FastAPI**: Framework web Python
- **PostgreSQL**: Banco de dados para cache
- **Docker**: Containerização
- **MinIO**: Armazenamento S3-compatível

## Casos de Uso

### Query Simples
```sql
SELECT * FROM dados WHERE id = 123;
```
→ Roteada para cluster **Small**

### Query Média
```sql
SELECT categoria, COUNT(*) as total
FROM dados
WHERE data BETWEEN '2026-01-01' AND '2026-12-31'
GROUP BY categoria;
```
→ Roteada para cluster **Medium**

### Query Complexa
```sql
SELECT 
    d1.categoria,
    AVG(d1.valor) as media_valor,
    COUNT(DISTINCT d2.tenant_id) as total_tenants
FROM dados d1
JOIN tenant_info d2 ON d1.tenant_id = d2.tenant_id
WHERE d1.data >= DATE '2025-01-01'
GROUP BY d1.categoria
HAVING COUNT(*) > 1000
ORDER BY media_valor DESC;
```
→ Roteada para cluster **Large**

## Referências

Este projeto foi desenvolvido como TCC do curso de Sistemas de Informação da PUC Minas.

**Autor**: Aristides Henrique Gonçalves da Cruz  
**Orientador**: Prof. Gustavo Luís Soares  
**Instituição**: Pontifícia Universidade Católica de Minas Gerais  
**Ano**: 2026

## Citação

Se você utilizar este software, por favor cite:

```bibtex
@misc{dyrasql2026,
    author = {Cruz, Aristides Henrique Gonçalves da},
    title = {DyraSQL: Framework para roteamento dinâmico de consultas SQL baseado em metadados de tabelas Apache Iceberg},
    year = {2026},
    howpublished = {GitHub},
    note = {Disponível em: https://github.com/trababalhos-puc/tcc-puc-dyrasql}
}
```
