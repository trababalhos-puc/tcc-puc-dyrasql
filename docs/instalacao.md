# Instalação

## Requisitos

### Hardware Mínimo
- **CPU**: 4 cores
- **RAM**: 16 GB
- **Disco**: 20 GB livres

### Software
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Git**: 2.30+

### Sistema Operacional
- Linux (Ubuntu 20.04+, CentOS 8+)
- macOS (11+)
- Windows 10/11 com WSL2

## Instalação Rápida

### 1. Clone o Repositório

```bash
git clone https://github.com/trababalhos-puc/tcc-puc-dyrasql.git
cd tcc-puc-dyrasql
```

### 2. Configure Variáveis de Ambiente

```bash
cd src
cp .env.example .env
```

Edite `.env` conforme necessário. As configurações padrão funcionam para ambiente de desenvolvimento.

### 3. Inicie os Serviços

```bash
docker-compose up -d
```

### 4. Aguarde Inicialização

Os serviços levam aproximadamente 2-3 minutos para inicializar completamente.

Monitore o status:

```bash
docker-compose ps
```

Todos os serviços devem estar com status `Up (healthy)`.

### 5. Valide a Instalação

```bash
./validar.sh
```

Este script executa 10 verificações automáticas:

1. ✅ Trino Small acessível
2. ✅ Trino Medium acessível
3. ✅ Trino Large acessível
4. ✅ DyraSQL Core respondendo
5. ✅ PostgreSQL funcional
6. ✅ Tabelas Iceberg criadas
7. ✅ Trino Gateway configurado
8. ✅ Gateway Proxy operacional
9. ✅ Metadados Iceberg disponíveis
10. ✅ Roteamento DyraSQL funcional

### 6. Execute Demonstração

```bash
./demo.sh
```

Este script demonstra o fluxo completo:
- Query simples → Small
- Query média → Medium
- Query complexa → Large
- Cache hit behavior

## Instalação Detalhada

### Estrutura do Projeto

```
tcc-puc-dyrasql/
├── src/                          # Código-fonte
│   ├── dyrasql-core/             # Motor de decisão
│   ├── trino-gateway-proxy/      # Proxy interceptador
│   ├── trino/                    # Configurações Trino
│   ├── postgres/                 # Scripts PostgreSQL
│   ├── trino-gateway/            # Gateway oficial
│   ├── scripts/                  # Scripts utilitários
│   ├── docker-compose.yml        # Orquestração
│   └── .env.example              # Variáveis exemplo
├── latex/                        # Monografia LaTeX
├── doc/                          # Documentação adicional
├── data/                         # Dados sintéticos
├── results/                      # Resultados de testes
├── references/                   # Referências acadêmicas
└── tools/                        # Ferramentas de build
```

### Serviços Docker

O `docker-compose.yml` define os seguintes serviços:

#### 1. PostgreSQL
```yaml
postgres:
  image: postgres:15-alpine
  ports:
    - "5432:5432"
  environment:
    POSTGRES_USER: dyrasql
    POSTGRES_PASSWORD: dyrasql123
    POSTGRES_DB: dyrasql
```

#### 2. MinIO
```yaml
minio:
  image: minio/minio:latest
  ports:
    - "9000:9000"
    - "9001:9001"
  command: server /data --console-address ":9001"
```

#### 3. Iceberg REST Catalog
```yaml
iceberg-rest:
  image: tabulario/iceberg-rest:latest
  ports:
    - "8181:8181"
  depends_on:
    - postgres
```

#### 4. Trino Clusters (Small, Medium, Large)
```yaml
trino-small:
  image: trinodb/trino:latest
  ports:
    - "8082:8082"
  volumes:
    - ./trino/config/small:/etc/trino
```

#### 5. DyraSQL Core
```yaml
dyrasql-core:
  build: ./dyrasql-core
  ports:
    - "8000:8000"
  depends_on:
    - postgres
    - trino-small
    - trino-medium
    - trino-large
```

#### 6. Trino Gateway
```yaml
trino-gateway:
  build: ./trino-gateway
  ports:
    - "8081:8081"
  depends_on:
    - postgres
```

#### 7. Gateway Proxy
```yaml
trino-gateway-proxy:
  build: ./trino-gateway-proxy
  ports:
    - "8080:8080"
  depends_on:
    - dyrasql-core
    - trino-gateway
```

### Configuração dos Clusters Trino

#### Small (8082)
```properties
query.max-memory=2GB
query.max-memory-per-node=512MB
query.max-total-memory-per-node=768MB
```

#### Medium (8083)
```properties
query.max-memory=4GB
query.max-memory-per-node=1GB
query.max-total-memory-per-node=1536MB
```

#### Large (8084)
```properties
query.max-memory=8GB
query.max-memory-per-node=2GB
query.max-total-memory-per-node=3GB
```

## Geração de Dados Sintéticos

Para testes com volumes maiores de dados:

### Exemplo Básico
```bash
cd src/scripts
./generate_data.py --records 1000000
```

### Com Tamanho Específico
```bash
./generate_data.py --target-size-gb 5.0
```

### Range de Datas Customizado
```bash
./generate_data.py \
  --records 500000 \
  --start-date 2025-01-01 \
  --end-date 2025-12-31
```

### Cenários Pré-configurados

#### Desenvolvimento
```bash
./generate_data.py --records 10000
```
~50 MB, ideal para testes locais

#### Staging
```bash
./generate_data.py --records 1000000
```
~5 GB, testes de carga moderada

#### Produção (simulação)
```bash
./generate_data.py --target-size-gb 20.0
```
20 GB, validação completa

Veja `src/scripts/README_GENERATOR.md` para detalhes completos.

## Troubleshooting

### Problema: Containers não inicializam

**Solução**:
```bash
docker-compose down -v
docker-compose up -d
```

### Problema: Porta em uso

**Erro**: `Error starting userland proxy: listen tcp4 0.0.0.0:8080: bind: address already in use`

**Solução**: Identifique o processo usando a porta:
```bash
lsof -i :8080
kill -9 <PID>
```

Ou altere a porta no `docker-compose.yml`.

### Problema: Memória insuficiente

**Erro**: `java.lang.OutOfMemoryError: Java heap space`

**Solução**: Aumente recursos Docker:
- Docker Desktop → Settings → Resources
- Memória: Mínimo 8 GB, Recomendado 16 GB

### Problema: Tabelas Iceberg não criadas

**Solução**: Execute manualmente:
```bash
docker-compose exec trino-small trino --catalog iceberg \
  --execute "CREATE SCHEMA IF NOT EXISTS db"

docker-compose exec trino-small trino --catalog iceberg \
  --file /docker-entrypoint-initdb.d/init-iceberg.sql
```

### Problema: Cache PostgreSQL não funciona

**Solução**: Verifique conexão:
```bash
docker-compose exec postgres psql -U dyrasql -d dyrasql \
  -c "SELECT * FROM routing_decisions LIMIT 5;"
```

Se tabela não existe, recrie:
```bash
docker-compose exec postgres psql -U dyrasql -d dyrasql \
  -f /docker-entrypoint-initdb.d/init-dyrasql.sh
```

### Logs Detalhados

Para depuração avançada:

```bash
# Logs de um serviço específico
docker-compose logs -f dyrasql-core

# Logs de todos os serviços
docker-compose logs -f

# Últimas 100 linhas
docker-compose logs --tail=100 dyrasql-core
```

## Desinstalação

### Remover containers e volumes
```bash
docker-compose down -v
```

### Remover imagens
```bash
docker-compose down --rmi all -v
```

### Limpeza completa
```bash
docker system prune -a --volumes
```

## Próximos Passos

Após instalação bem-sucedida:

1. Leia a [documentação de uso](uso.md)
2. Explore a [API](api.md)
3. Execute queries de exemplo em `src/query.sql`
4. Configure pesos do algoritmo conforme seu cenário

## Suporte

Em caso de problemas:

1. Consulte a [documentação de arquitetura](arquitetura.md)
2. Verifique [issues conhecidos](https://github.com/trababalhos-puc/tcc-puc-dyrasql/issues)
3. Abra uma nova issue com:
   - Output de `docker-compose ps`
   - Logs relevantes
   - Versões de Docker e SO
