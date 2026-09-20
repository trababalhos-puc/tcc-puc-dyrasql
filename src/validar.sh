#!/bin/bash
# ======================================================================
# DyraSQL - Script de Validação
# ======================================================================
# Este script valida que todos os componentes estão funcionando
# ======================================================================

set -e

RED='\033[0,31m'
GREEN='\033[0,32m'
YELLOW='\033[1,33m'
BLUE='\033[0,34m'
NC='\033[0m' # No Color

echo "======================================================================"
echo -e "${BLUE}DyraSQL - Script de Validação${NC}"
echo "======================================================================"
echo ""

# ----------------------------------------------------------------------
# 1. Verificar se Docker está rodando
# ----------------------------------------------------------------------
echo -e "${YELLOW}[1/10]${NC} Verificando Docker..."
if ! docker ps &> /dev/null; then
    echo -e "${RED}✗ Docker não está rodando${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker está rodando${NC}"
echo ""

# ----------------------------------------------------------------------
# 2. Verificar se containers estão rodando
# ----------------------------------------------------------------------
echo -e "${YELLOW}[2/10]${NC} Verificando containers..."
containers=(
    "dyrasql-core"
    "trino-gateway-proxy"
    "trino-gateway"
    "trino-small"
    "trino-medium"
    "trino-large"
    "gateway-db"
    "minio"
    "iceberg-rest"
)

for container in "${containers[@]}"; do
    if docker compose ps | grep -q "$container.*running"; then
        echo -e "  ${GREEN}✓${NC} $container"
    else
        echo -e "  ${RED}✗${NC} $container não está rodando"
        echo -e "     Execute: docker compose up -d"
        exit 1
    fi
done
echo ""

# ----------------------------------------------------------------------
# 3. Health check do DyraSQL Core
# ----------------------------------------------------------------------
echo -e "${YELLOW}[3/10]${NC} Health check - DyraSQL Core..."
if curl -sf http://localhost:5001/health > /dev/null 2>&1; then
    response=$(curl -s http://localhost:5001/health)
    echo -e "${GREEN}✓ DyraSQL Core está saudável${NC}"
    echo "  Response: $response"
else
    echo -e "${RED}✗ DyraSQL Core não está respondendo${NC}"
    echo "  Logs: docker compose logs dyrasql-core"
    exit 1
fi
echo ""

# ----------------------------------------------------------------------
# 4. Health check do Trino Gateway Proxy
# ----------------------------------------------------------------------
echo -e "${YELLOW}[4/10]${NC} Health check - Trino Gateway Proxy..."
if curl -sf http://localhost:8080/health > /dev/null 2>&1; then
    response=$(curl -s http://localhost:8080/health)
    echo -e "${GREEN}✓ Trino Gateway Proxy está saudável${NC}"
    echo "  Response: $response"
else
    echo -e "${RED}✗ Trino Gateway Proxy não está respondendo${NC}"
    exit 1
fi
echo ""

# ----------------------------------------------------------------------
# 5. Health check dos clusters Trino
# ----------------------------------------------------------------------
echo -e "${YELLOW}[5/10]${NC} Health check - Clusters Trino..."
for port in 8081 8082 8083; do
    cluster=$([ $port -eq 8081 ] && echo "small" || [ $port -eq 8082 ] && echo "medium" || echo "large")
    if curl -sf http://localhost:$port/v1/info > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} Trino $cluster (porta $port)"
    else
        echo -e "  ${RED}✗${NC} Trino $cluster não está respondendo"
        exit 1
    fi
done
echo ""

# ----------------------------------------------------------------------
# 6. Verificar PostgreSQL
# ----------------------------------------------------------------------
echo -e "${YELLOW}[6/10]${NC} Verificando PostgreSQL..."
if docker compose exec -T gateway-db pg_isready -U dyrasql -d dyrasql > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL está acessível${NC}"
    
    # Verificar tabela routing_decisions
    count=$(docker compose exec -T gateway-db psql -U dyrasql -d dyrasql -t -c "SELECT COUNT(*) FROM routing_decisions;" 2>/dev/null | tr -d ' ')
    echo "  Registros no cache: $count"
else
    echo -e "${RED}✗ PostgreSQL não está acessível${NC}"
    exit 1
fi
echo ""

# ----------------------------------------------------------------------
# 7. Verificar MinIO
# ----------------------------------------------------------------------
echo -e "${YELLOW}[7/10]${NC} Verificando MinIO..."
if curl -sf http://localhost:9000/minio/health/live > /dev/null 2>&1; then
    echo -e "${GREEN}✓ MinIO está acessível${NC}"
else
    echo -e "${RED}✗ MinIO não está acessível${NC}"
    exit 1
fi
echo ""

# ----------------------------------------------------------------------
# 8. Verificar Iceberg REST Catalog
# ----------------------------------------------------------------------
echo -e "${YELLOW}[8/10]${NC} Verificando Iceberg REST Catalog..."
if curl -sf http://localhost:8181/v1/config > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Iceberg REST Catalog está acessível${NC}"
else
    echo -e "${RED}✗ Iceberg REST Catalog não está acessível${NC}"
    exit 1
fi
echo ""

# ----------------------------------------------------------------------
# 9. Verificar tabelas Iceberg
# ----------------------------------------------------------------------
echo -e "${YELLOW}[9/10]${NC} Verificando tabelas Iceberg..."
tables=$(docker compose exec -T trino-small trino --server http://localhost:8080 --user admin --output-format TSV --execute "SHOW TABLES IN iceberg.analytics" 2>/dev/null || echo "")
if echo "$tables" | grep -q "dados"; then
    echo -e "${GREEN}✓ Tabela 'dados' existe${NC}"
    
    count=$(docker compose exec -T trino-small trino --server http://localhost:8080 --user admin --output-format TSV --execute "SELECT COUNT(*) FROM iceberg.analytics.dados" 2>/dev/null | tr -d '[:space:]')
    echo "  Registros na tabela dados: $count"
else
    echo -e "${YELLOW}⚠ Tabela 'dados' não encontrada${NC}"
    echo "  Execute: docker compose logs iceberg-init"
fi

if echo "$tables" | grep -q "tenant_info"; then
    echo -e "${GREEN}✓ Tabela 'tenant_info' existe${NC}"
else
    echo -e "${YELLOW}⚠ Tabela 'tenant_info' não encontrada${NC}"
fi
echo ""

# ----------------------------------------------------------------------
# 10. Teste de roteamento básico
# ----------------------------------------------------------------------
echo -e "${YELLOW}[10/10]${NC} Teste de roteamento básico..."

# Query simples (esperado: small)
query_simple="SELECT COUNT(*) FROM iceberg.analytics.dados WHERE date = TIMESTAMP '2024-01-01'"
response=$(curl -s -X POST http://localhost:5001/api/v1/route \
    -H "Content-Type: application/json" \
    -d "{\"query\": \"$query_simple\"}")

if echo "$response" | grep -q '"cluster"'; then
    cluster=$(echo "$response" | grep -o '"cluster":"[^"]*"' | cut -d'"' -f4)
    score=$(echo "$response" | grep -o '"score":[0-9.]*' | cut -d':' -f2)
    echo -e "${GREEN}✓ Roteamento funcionando${NC}"
    echo "  Cluster selecionado: $cluster"
    echo "  Score calculado: $score"
else
    echo -e "${RED}✗ Erro no roteamento${NC}"
    echo "  Response: $response"
    exit 1
fi
echo ""

# ----------------------------------------------------------------------
# Resumo
# ----------------------------------------------------------------------
echo "======================================================================"
echo -e "${GREEN}✓ Todos os testes passaram!${NC}"
echo "======================================================================"
echo ""
echo "Próximos passos:"
echo "  1. Executar consultas de teste: cat query.sql"
echo "  2. Monitorar roteamento: ./scripts/monitor-routing.sh"
echo "  3. Ver logs do Core: docker compose logs -f dyrasql-core"
echo "  4. Acessar MinIO Console: http://localhost:9001"
echo ""
echo "Documentação completa: README.md"
echo "======================================================================"
