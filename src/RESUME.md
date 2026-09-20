# Resumo do Projeto DyraSQL - Ambiente de Experimentos

**Data da última atualização:** 2025-11-16  
**Status:** ✅ Funcional e testado  
**Última melhoria:** Configuração automática de backends no Trino Gateway

Este documento resume todas as implementações, correções e melhorias realizadas no ambiente de experimentos do DyraSQL. Use este documento para retomar o trabalho e entender o estado atual do projeto.

## Visão Geral

O projeto DyraSQL implementa um sistema de roteamento dinâmico de consultas SQL para múltiplos clusters Trino, utilizando análise inteligente de queries para determinar o cluster mais adequado para execução.

## Arquitetura Implementada

### Componentes Principais

1. **Trino Gateway** (porta 8080)
   - Balanceador de carga e gateway de roteamento oficial
   - Compilado a partir do código-fonte oficial (Java 24)
   - Admin port: 8084 (porta interna 8081)
   - Persistência via PostgreSQL

2. **DyraSQL Core** (porta 5001)
   - Sistema de roteamento dinâmico
   - Análise de queries usando EXPLAIN (TYPE IO)
   - Cálculo de score baseado em volume, complexidade e histórico
   - Cache de decisões no PostgreSQL

3. **Clusters Trino Simulados**
   - **Trino ECS** (porta 8081): Consultas leves (Score < 0.3)
   - **Trino EMR Standard** (porta 8082): Consultas médias (Score 0.3-0.7)
   - **Trino EMR Optimized** (porta 8083): Consultas pesadas (Score > 0.7)

4. **Infraestrutura de Suporte**
   - PostgreSQL: Banco de dados para Trino Gateway
   - PostgreSQL: Cache de decisões de roteamento
   - AWS Glue Catalog: Metastore para tabelas Iceberg
   - S3: Armazenamento de dados Iceberg

## Implementações Realizadas

### 1. Configuração Docker Compose

**Arquivo:** `docker-compose.yml`

- Configuração completa de todos os serviços
- Uso de volumes para montar `~/.aws` (credenciais AWS)
- Configuração de redes Docker para comunicação entre serviços
- Health checks para todos os containers
- Dependências entre serviços configuradas
- **Serviço `gateway-setup`** para configuração automática de backends

**Principais características:**
- Credenciais AWS lidas de `~/.aws/credentials` (não passadas como variáveis de ambiente)
- Variáveis de ambiente configuráveis via `.env`
- Portas mapeadas para acesso externo
- **Configuração automática**: Backends do Trino Gateway são configurados automaticamente no startup

### 2. Trino Gateway Oficial

**Arquivos:** `trino-gateway/Dockerfile`, `trino-gateway/config.yaml`

- Compilação do Trino Gateway a partir do código-fonte oficial
- Multi-stage Docker build (builder + runtime)
- Configuração com PostgreSQL para persistência
- API REST para gerenciamento de backends
- **Configuração automática de backends** via serviço `gateway-setup` no docker-compose

**Scripts:**
- `scripts/setup-gateway-backends.sh`: Registra os três clusters Trino no Gateway (execução manual)
- `scripts/setup-gateway-backends-auto.sh`: Configuração automática executada no startup

### 3. Configuração dos Clusters Trino

**Arquivos:** `trino/Dockerfile`, `trino/scripts/configure-credentials.sh`, `trino/config/*/catalog/*.properties`

- Configuração automática de credenciais AWS
- Integração com AWS Glue Catalog
- Suporte a Apache Iceberg
- Configuração de S3 filesystem nativo (`fs.native-s3.enabled=true`)

**Configurações:**
- Hive connector: Fornece filesystem S3 para o Iceberg connector
- Iceberg connector: Configurado para usar Glue Catalog
- Credenciais lidas automaticamente de `~/.aws/credentials`

### 4. DyraSQL Core - Query Analyzer

**Arquivo:** `dyrasql-core/query_analyzer.py`

**Evolução da Implementação:**

#### Versão Inicial
- Análise básica de queries usando regex
- Extração de tabelas e análise de complexidade
- Geração de fingerprint para cache

#### Versão Final (Atual)
- **Uso exclusivo de EXPLAIN (TYPE IO)**
- Execução de `EXPLAIN (TYPE IO)` no Trino ECS
- Parse do JSON retornado com informações de I/O
- Extração de:
  - `outputSizeInBytes`: Tamanho estimado dos dados (já considera filtros)
  - `outputRowCount`: Número de linhas estimadas
  - `cpuCost`: Custo de CPU
  - `columnConstraints`: Filtros aplicados (ranges)

**Principais métodos:**
- `explain_io()`: Executa EXPLAIN (TYPE IO) e parseia o resultado
- `_parse_explain_io()`: Extrai informações de tabelas, tamanhos e filtros
- `analyze_query_io()`: Análise completa de I/O usando apenas EXPLAIN
- `generate_fingerprint()`: Gera hash único para cache

**Vantagens da abordagem final:**
- ✅ Mais rápido: Uma única chamada ao Trino
- ✅ Mais preciso: Trino já aplica filtros e otimizações
- ✅ Mais simples: Não precisa consultar tabela `$files` manualmente
- ✅ Informações completas: Tamanho, linhas, custos e filtros em uma resposta

### 5. DyraSQL Core - Decision Engine

**Arquivo:** `dyrasql-core/decision_engine.py`

**Algoritmo de Decisão:**
```
Score = w1 × fv + w2 × fc + w3 × fh
```

Onde:
- `w1 = 0.5`: Peso do fator volume
- `w2 = 0.3`: Peso do fator complexidade
- `w3 = 0.2`: Peso do fator histórico

**Fatores:**

1. **Fator Volume (fv)**
   - Baseado em `outputSizeInBytes` do EXPLAIN
   - Considera tamanho total em GB
   - Estima número de arquivos baseado no tamanho
   - Normalização usando logaritmo

2. **Fator Complexidade (fc)**
   - Número de JOINs
   - Número de agregações
   - Número de subconsultas
   - Filtros particionados vs não-particionados

3. **Fator Histórico (fh)**
   - Baseado em execuções anteriores
   - Consulta PostgreSQL para histórico
   - Valor padrão: 0.5

**Seleção de Cluster:**
- Score < 0.3 → ECS (consultas leves)
- 0.3 ≤ Score < 0.7 → EMR Standard (consultas médias)
- Score ≥ 0.7 → EMR Optimized (consultas pesadas)

### 6. DyraSQL Core - History Manager

**Arquivo:** `dyrasql-core/history_manager.py`

- Gerenciamento de cache no PostgreSQL
- TTL de 24 horas para decisões
- Salvamento de fatores junto com decisões
- Consulta de histórico para cálculo de fator histórico

**Funcionalidades:**
- `get_cached_decision()`: Retorna decisão do cache com fatores
- `save_decision()`: Salva decisão com score, cluster e fatores
- `save_metrics()`: Salva métricas pós-execução
- `get_historical_factor()`: Calcula fator histórico baseado em execuções anteriores

### 7. API REST do DyraSQL Core

**Arquivo:** `dyrasql-core/app.py`

**Endpoints:**

1. **GET /health**
   - Health check do serviço

2. **POST /api/v1/route**
   - Recebe: `{"query": "SELECT ..."}`
   - Retorna: Decisão de roteamento com cluster, score e fatores
   - Fluxo:
     1. Gera fingerprint da query
     2. Verifica cache no PostgreSQL
     3. Se não estiver em cache:
        - Executa EXPLAIN (TYPE IO)
        - Analisa I/O e complexidade
        - Calcula score e seleciona cluster
        - Salva no cache
     4. Retorna decisão

3. **POST /api/v1/metrics**
   - Salva métricas pós-execução
   - Recebe: fingerprint, cluster, execution_time, rows_processed, etc.

### 8. Scripts de Automação

**Scripts criados:**

1. **`scripts/setup-gateway-backends.sh`**
   - Registra os três clusters Trino no Trino Gateway (execução manual)
   - Usa API REST do Gateway: `POST /entity?entityType=GATEWAY_BACKEND`

2. **`scripts/setup-gateway-backends-auto.sh`** ⭐ **NOVO**
   - Configuração automática dos backends no Trino Gateway
   - Executado automaticamente pelo serviço `gateway-setup` no docker-compose
   - Aguarda o Gateway estar pronto antes de configurar
   - Verifica se backends já existem antes de adicionar (idempotente)
   - Lista backends configurados ao final

3. **`scripts/trino-query.sh`**
   - Executa queries no Trino via API REST
   - Suporta queries diretas ou arquivos `.sql`
   - Remove semicolons automaticamente
   - Lida com paginação (`nextUri`)

3. **`scripts/get-routing-decision.sh`**
   - Consulta o DyraSQL Core para obter decisão de roteamento
   - Exibe resultado formatado com cores
   - Mostra cluster recomendado, score e fatores
   - Fornece comandos prontos para executar a query

4. **`scripts/clear-cache.sh`**
   - Limpa o cache do PostgreSQL
   - Remove todas as entradas de decisões

5. **`scripts/test-routing.sh`**
   - Testa o sistema de roteamento com múltiplas queries


### 9. Documentação

**Arquivos criados:**

1. **`README.md`**
   - Documentação principal do projeto
   - Instruções de configuração e uso
   - Explicação da arquitetura

2. **`COMO_EXECUTAR.md`**
   - Guia detalhado de como executar scripts
   - Exemplos de uso
   - Troubleshooting

3. **`ROTEAMENTO_TRINO_GATEWAY.md`**
   - Explicação de como o roteamento funciona
   - Integração com DyraSQL Core
   - Próximos passos para routing provider customizado

4. **`GLUE_CATALOG_SETUP.md`**
   - Configuração do AWS Glue Catalog
   - Permissões IAM necessárias
   - Integração com Trino

5. **`COMO_FAZER_QUERIES.md`**
   - Diferentes formas de executar queries
   - Web UI, REST API, CLI, clientes gráficos
   - Exemplos práticos

## Correções e Melhorias Realizadas

### 1. Configuração de Credenciais AWS
- ✅ Migração de variáveis de ambiente para montagem de `~/.aws`
- ✅ Uso de `boto3.Session` com perfil AWS
- ✅ Suporte a múltiplos perfis AWS

### 2. Trino Gateway
- ✅ Compilação do código-fonte oficial (não mais imagem customizada Python)
- ✅ Configuração correta de `config.yaml`
- ✅ Integração com PostgreSQL
- ✅ Correção de portas (admin port: 8084)

### 3. Configuração do Trino
- ✅ Integração com AWS Glue Catalog
- ✅ Configuração de S3 filesystem nativo
- ✅ Hive connector para fornecer filesystem S3
- ✅ Script de configuração automática de credenciais

### 4. Query Analyzer
- ✅ Implementação inicial com consulta à tabela `$files`
- ✅ Refatoração para usar apenas EXPLAIN (TYPE IO)
- ✅ Parse correto do JSON do EXPLAIN
- ✅ Extração de filtros via `columnConstraints`
- ✅ Tratamento de valores "NaN" no JSON

### 5. Cache e Persistência
- ✅ Salvamento de fatores no PostgreSQL
- ✅ Retorno de fatores do cache
- ✅ Script para limpar cache

### 6. Scripts e Automação
- ✅ Scripts executáveis e documentados
- ✅ Tratamento de erros
- ✅ Output formatado e colorido

## Fluxo de Funcionamento

### Fluxo de Roteamento

```
1. Cliente envia query → DyraSQL Core (POST /api/v1/route)
   ↓
2. Gera fingerprint da query
   ↓
3. Verifica cache no PostgreSQL
   ↓
4a. Se em cache: Retorna decisão salva
   ↓
4b. Se não em cache:
   - Executa EXPLAIN (TYPE IO) no Trino ECS
   - Parse do JSON retornado
   - Extrai: tamanho, linhas, custos, filtros
   - Analisa complexidade da query
   - Calcula fatores (volume, complexidade, histórico)
   - Calcula score final
   - Seleciona cluster apropriado
   - Salva no cache
   ↓
5. Retorna decisão: {cluster, score, factors, cluster_url}
```

### Fluxo de Execução (Futuro - com Routing Provider)

```
1. Cliente envia query → Trino Gateway (porta 8080)
   ↓
2. Trino Gateway intercepta query
   ↓
3. Chama DyraSQL Core: POST /api/v1/route
   ↓
4. DyraSQL Core retorna decisão
   ↓
5. Trino Gateway roteia para cluster recomendado
   ↓
6. Query executada no cluster selecionado
   ↓
7. Resultado retornado ao cliente
   ↓
8. (Opcional) Métricas enviadas ao DyraSQL Core
```

## Estrutura de Arquivos

```
experimento/
├── docker-compose.yml              # Orquestração de todos os serviços
├── Makefile                        # Automação de comandos
├── env.example                     # Exemplo de variáveis de ambiente
├── README.md                       # Documentação principal
├── COMO_EXECUTAR.md               # Guia de execução
├── ROTEAMENTO_TRINO_GATEWAY.md    # Documentação de roteamento
├── GLUE_CATALOG_SETUP.md          # Setup do Glue Catalog
├── COMO_FAZER_QUERIES.md          # Guia de queries
├── RESUME.md                      # Este arquivo
│
├── scripts/
│   ├── setup-gateway-backends.sh  # Configura backends no Gateway
│   ├── trino-query.sh             # Executa queries no Trino
│   ├── get-routing-decision.sh    # Obtém decisão de roteamento
│   ├── clear-cache.sh             # Limpa cache do PostgreSQL
│   ├── test-routing.sh            # Testa roteamento
│   ├── exemplo.sql                # Exemplo de query SQL
│   ├── show-catalogs.sql          # Query para listar catálogos
│   └── show-schemas.sql           # Query para listar schemas
│
├── dyrasql-core/
│   ├── Dockerfile                 # Imagem Docker do DyraSQL Core
│   ├── app.py                     # API REST principal
│   ├── query_analyzer.py          # Análise de queries (EXPLAIN)
│   ├── decision_engine.py         # Algoritmo de decisão
│   ├── history_manager.py         # Gerenciamento de cache/histórico
│   ├── metadata_connector.py      # Conectores de metadados (legado)
│   └── requirements.txt           # Dependências Python
│
├── trino/
│   ├── Dockerfile                 # Imagem base para clusters Trino
│   ├── scripts/
│   │   └── configure-credentials.sh  # Configura credenciais AWS
│   └── config/
│       ├── ecs/
│       │   ├── config.properties
│       │   └── catalog/
│       │       ├── iceberg.properties
│       │       └── hive.properties
│       ├── emr-standard/
│       │   └── catalog/
│       │       ├── iceberg.properties
│       │       └── hive.properties
│       └── emr-optimized/
│           └── catalog/
│               ├── iceberg.properties
│               └── hive.properties
│
├── trino-gateway/
│   ├── Dockerfile                 # Compila Trino Gateway oficial
│   ├── config.yaml                # Configuração do Gateway
│   └── README.md                  # Documentação do Gateway
│
```

## Tecnologias Utilizadas

- **Docker & Docker Compose**: Orquestração de containers
- **Trino**: Engine SQL distribuído
- **Trino Gateway**: Balanceador de carga oficial
- **Python 3.11**: DyraSQL Core (Flask)
- **PostgreSQL**: Persistência do Trino Gateway
- **PostgreSQL**: Cache de decisões
- **AWS Glue Catalog**: Metastore para Iceberg
- **Apache Iceberg**: Formato de tabela
- **boto3**: SDK AWS para Python

## Configurações Importantes

### Variáveis de Ambiente

```bash
AWS_REGION=us-east-1
AWS_PROFILE=default
S3_BUCKET=prod-cafdatalakehouse--ref
S3_PREFIX=dbt/prod_db_transient_ref/
TRINO_URL=http://trino-ecs:8080
TRINO_USER=admin
```

### Portas Expostas

- **8080**: Trino Gateway (aplicação)
- **8081**: Trino ECS
- **8082**: Trino EMR Standard
- **8083**: Trino EMR Optimized
- **8084**: Trino Gateway (admin)
- **5001**: DyraSQL Core
- **5432**: PostgreSQL

## Algoritmo de Decisão

### Fórmula do Score

```
Score = 0.5 × fv + 0.3 × fc + 0.2 × fh
```

### Cálculo dos Fatores

#### Fator Volume (fv)
- Baseado em `outputSizeInBytes` do EXPLAIN (TYPE IO)
- Considera tamanho total em GB
- Estima número de arquivos
- Normalização usando logaritmo
- Limite máximo: 1TB

#### Fator Complexidade (fc)
- JOINs: 0.2 por JOIN
- Agregações: 0.15 por agregação
- Subconsultas: 0.25 por subconsulta
- Filtros particionados: 0.02 por filtro
- Filtros não-particionados: 0.1 por filtro

#### Fator Histórico (fh)
- Baseado em execuções anteriores no PostgreSQL
- Valor padrão: 0.5
- Pode ser ajustado baseado em métricas históricas

### Seleção de Cluster

- **Score < 0.3** → ECS (consultas leves)
- **0.3 ≤ Score < 0.7** → EMR Standard (consultas médias)
- **Score ≥ 0.7** → EMR Optimized (consultas pesadas)

## Exemplos de Uso

### 1. Configurar Ambiente

```bash
# Copiar variáveis de ambiente
cp env.example .env

# Editar .env com suas configurações
# (credenciais AWS já estão em ~/.aws)

# Construir e iniciar containers
make build
make up

# Configurar backends no Gateway
./scripts/setup-gateway-backends.sh
```

### 2. Obter Decisão de Roteamento

```bash
# Com query direta
./scripts/get-routing-decision.sh "SELECT * FROM iceberg.default.vendas LIMIT 10"

# Com arquivo .sql
./scripts/get-routing-decision.sh scripts/exemplo.sql
```

### 3. Executar Query

```bash
# Via Gateway (roteamento automático)
./scripts/trino-query.sh "SELECT 1" http://localhost:8080 admin

# Direto no cluster específico
./scripts/trino-query.sh "SELECT 1" http://localhost:8081 admin  # ECS
./scripts/trino-query.sh "SELECT 1" http://localhost:8082 admin  # EMR Standard
./scripts/trino-query.sh "SELECT 1" http://localhost:8083 admin  # EMR Optimized
```

### 4. Limpar Cache

```bash
./scripts/clear-cache.sh
```

## Problemas Resolvidos

### 1. Configuração de Credenciais AWS
- **Problema**: Credenciais passadas como variáveis de ambiente
- **Solução**: Montagem de `~/.aws` como volume read-only

### 2. Trino Gateway
- **Problema**: Tentativa de usar imagem inexistente
- **Solução**: Compilação do código-fonte oficial via Dockerfile multi-stage

### 3. Parsing do EXPLAIN (TYPE IO)
- **Problema**: Estrutura JSON aninhada não era parseada corretamente
- **Solução**: Parse correto de `table.catalog` e `table.schemaTable.schema/table`

### 4. Consulta à Tabela $files
- **Problema**: Consulta manual à tabela `$files` era lenta e complexa
- **Solução**: Uso exclusivo de EXPLAIN (TYPE IO) que já fornece todas as informações

### 5. Cache sem Fatores
- **Problema**: Fatores zerados quando decisão vinha do cache
- **Solução**: Salvamento e retorno de fatores no cache

### 6. Cálculo de Volume
- **Problema**: Volume calculado incorretamente (valores zerados)
- **Solução**: Uso direto de `outputSizeInBytes` do EXPLAIN

## Próximos Passos

### 1. Routing Provider Customizado para Trino Gateway
- Desenvolver provider em Java que integra com DyraSQL Core
- Implementar interface `RouterProvider` do Trino Gateway
- Compilar e empacotar como JAR
- Adicionar ao classpath do Trino Gateway

### 2. Coleta de Métricas Pós-Execução
- Implementar callback após execução de queries
- Enviar métricas reais (tempo de execução, linhas processadas) ao DyraSQL Core
- Usar métricas para ajustar fator histórico

### 3. Melhorias no Algoritmo de Decisão
- Ajustar pesos dos fatores baseado em métricas reais
- Implementar aprendizado adaptativo
- Considerar carga atual dos clusters

### 4. Interface Web
- Dashboard para visualizar decisões
- Gráficos de distribuição de queries por cluster
- Métricas de performance

## Comandos Úteis

### Docker Compose
```bash
make build          # Constrói imagens
make up             # Inicia serviços
make down           # Para serviços
make logs           # Ver logs
make clean          # Limpa tudo
```


### Scripts
```bash
./scripts/setup-gateway-backends.sh    # Configura backends
./scripts/get-routing-decision.sh      # Obtém decisão
./scripts/trino-query.sh               # Executa query
./scripts/clear-cache.sh               # Limpa cache
```

## Referências

- [Trino Gateway GitHub](https://github.com/trinodb/trino-gateway)
- [Trino Gateway Documentation](https://trinodb.github.io/trino-gateway/)
- [Trino Documentation](https://trino.io/docs/)
- [Apache Iceberg](https://iceberg.apache.org/)
- [AWS Glue Catalog](https://docs.aws.amazon.com/glue/latest/dg/catalog-and-crawler.html)

## Estado Atual do Projeto

### ✅ Funcionalidades Implementadas e Testadas

1. **Ambiente Docker Compose completo**
   - Todos os serviços configurados e funcionando
   - Credenciais AWS via `~/.aws`
   - Health checks funcionando

2. **Trino Gateway oficial**
   - Compilado a partir do código-fonte
   - Backends registrados (ECS, EMR Standard, EMR Optimized)
   - PostgreSQL configurado

3. **DyraSQL Core**
   - Análise de queries usando EXPLAIN (TYPE IO) ✅
   - Cálculo de score baseado em volume, complexidade e histórico ✅
   - Cache no PostgreSQL funcionando
   - API REST respondendo corretamente ✅

4. **Clusters Trino**
   - Configurados com AWS Glue Catalog ✅
   - S3 filesystem nativo habilitado ✅
   - Credenciais AWS funcionando ✅

5. **Scripts de automação**
   - Todos os scripts funcionando ✅
   - Documentação completa ✅

### ⚠️ Limitações Conhecidas

1. **Roteamento no Trino Gateway**
   - Atualmente usa round-robin básico
   - Não há integração automática com DyraSQL Core
   - Requer routing provider customizado em Java (não implementado)

2. **Coleta de Métricas**
   - Endpoint `/api/v1/metrics` existe mas não é chamado automaticamente
   - Métricas reais de execução não são coletadas ainda

### 🔄 Próximas Implementações Necessárias

1. **Routing Provider Customizado (Java)**
   - Implementar `RouterProvider` que chama DyraSQL Core
   - Compilar e integrar no Trino Gateway
   - Testar roteamento automático

2. **Coleta Automática de Métricas**
   - Integrar callback após execução de queries
   - Enviar métricas ao DyraSQL Core
   - Usar métricas para ajustar fator histórico

3. **Melhorias no Algoritmo**
   - Ajustar pesos baseado em métricas reais
   - Implementar aprendizado adaptativo

## Como Retomar o Trabalho

### 1. Verificar Status do Ambiente

```bash
cd experimento
docker compose ps
```

### 2. Verificar Logs

```bash
# Ver se há erros
docker compose logs --tail=50

# Ver logs específicos
docker compose logs -f dyrasql-core
docker compose logs -f trino-gateway
```

### 3. Testar Funcionalidades

```bash
# Testar roteamento
./scripts/get-routing-decision.sh "SELECT * FROM iceberg.prod_db_transient_ref.transient_caf_executions LIMIT 1"

# Verificar se está funcionando corretamente
# Deve retornar: Volume > 0, Score calculado, Cluster recomendado
```

### 4. Continuar Desenvolvimento

**Próxima tarefa principal:** Implementar routing provider customizado em Java para integração completa do Trino Gateway com DyraSQL Core.

## Informações Importantes para Continuidade

### Estrutura do EXPLAIN (TYPE IO)

O EXPLAIN retorna JSON com esta estrutura:
```json
{
  "inputTableColumnInfos": [{
    "table": {
      "catalog": "iceberg",
      "schemaTable": {
        "schema": "prod_db_transient_ref",
        "table": "transient_caf_executions"
      }
    },
    "constraint": {
      "columnConstraints": [{
        "columnName": "date",
        "domain": {
          "ranges": [...]
        }
      }]
    },
    "estimate": {
      "outputRowCount": 298277285.0,
      "outputSizeInBytes": 727777655682.0,
      "cpuCost": 727777655682.0
    }
  }]
}
```

### Endpoints do DyraSQL Core

- **POST /api/v1/route**: Recebe query, retorna decisão
- **POST /api/v1/metrics**: Salva métricas pós-execução
- **GET /health**: Health check

### Endpoints do Trino Gateway

- **POST /entity?entityType=GATEWAY_BACKEND**: Adiciona/atualiza backend
- **GET /entity?entityType=GATEWAY_BACKEND**: Lista backends
- **POST /v1/statement**: Executa query (roteia para backends)

## Conclusão

O ambiente de experimentos do DyraSQL está completamente funcional, utilizando EXPLAIN (TYPE IO) do Trino para análise precisa de queries e cálculo de scores para roteamento inteligente. O sistema está pronto para testes e pode ser expandido com um routing provider customizado para integração completa com o Trino Gateway.

**Última verificação:** Sistema testado e funcionando corretamente com tabela de 677GB, retornando score 0.532 e recomendando EMR Standard.

