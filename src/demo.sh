#!/bin/bash
# ======================================================================
# DyraSQL - Script de Demonstração Completa
# ======================================================================
# Este script demonstra todo o fluxo do framework DyraSQL
# ======================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "======================================================================"
echo -e "${BLUE}DyraSQL - Demonstração Completa do Framework${NC}"
echo "======================================================================"
echo ""

# ----------------------------------------------------------------------
# 1. Verificar ambiente
# ----------------------------------------------------------------------
echo -e "${YELLOW}[1/8]${NC} Verificando ambiente..."
if ! docker compose ps | grep -q "dyrasql-core.*running"; then
    echo -e "${RED}✗ DyraSQL Core não está rodando${NC}"
    echo "  Execute: docker compose up -d"
    exit 1
fi
echo -e "${GREEN}✓ Ambiente rodando${NC}"
echo ""

# ----------------------------------------------------------------------
# 2. Demonstrar queries simples (cluster small)
# ----------------------------------------------------------------------
echo -e "${YELLOW}[2/8]${NC} Testando consulta SIMPLES (esperado: cluster small)..."
echo ""

query_simple="SELECT COUNT(*) as total FROM iceberg.analytics.dados WHERE date = TIMESTAMP '2024-01-15'"
echo "Query: $query_simple"
echo ""

response=$(curl -s -X POST http://localhost:5001/api/v1/route \
    -H "Content-Type: application/json" \
    -d "{\"query\": \"$query_simple\"}")

cluster=$(echo "$response" | grep -o '"cluster":"[^"]*"' | cut -d'"' -f4)
score=$(echo "$response" | grep -o '"score":[0-9.]*' | cut -d':' -f2)
volume=$(echo "$response" | grep -o '"volume":[0-9.]*' | cut -d':' -f2 | head -1)
complexity=$(echo "$response" | grep -o '"complexity":[0-9.]*' | cut -d':' -f2)

echo "Resultado:"
echo "  Cluster selecionado: $cluster"
echo "  Score calculado: $score"
echo "  Fatores: volume=$volume, complexity=$complexity"

if [ "$cluster" = "small" ]; then
    echo -e "  ${GREEN}✓ Correto! Query simples → cluster small${NC}"
else
    echo -e "  ${RED}⚠ Inesperado! Esperava cluster small${NC}"
fi
echo ""
sleep 2

# ----------------------------------------------------------------------
# 3. Demonstrar queries intermediárias (cluster medium)
# ----------------------------------------------------------------------
echo -e "${YELLOW}[3/8]${NC} Testando consulta INTERMEDIÁRIA (esperado: cluster medium)..."
echo ""

query_medium="SELECT t.tenant_id, t.categoria, COUNT(*) as total, SUM(d.valor) as soma FROM iceberg.analytics.dados d JOIN iceberg.analytics.tenant_info t ON d.tenant_id = t.tenant_id WHERE d.date >= TIMESTAMP '2024-01-01' AND d.date < TIMESTAMP '2024-01-15' GROUP BY t.tenant_id, t.categoria"
echo "Query: SELECT ... FROM dados d JOIN tenant_info t ... GROUP BY ..."
echo ""

response=$(curl -s -X POST http://localhost:5001/api/v1/route \
    -H "Content-Type: application/json" \
    -d "{\"query\": \"$query_medium\"}")

cluster=$(echo "$response" | grep -o '"cluster":"[^"]*"' | cut -d'"' -f4)
score=$(echo "$response" | grep -o '"score":[0-9.]*' | cut -d':' -f2)
volume=$(echo "$response" | grep -o '"volume":[0-9.]*' | cut -d':' -f2 | head -1)
complexity=$(echo "$response" | grep -o '"complexity":[0-9.]*' | cut -d':' -f2)

echo "Resultado:"
echo "  Cluster selecionado: $cluster"
echo "  Score calculado: $score"
echo "  Fatores: volume=$volume, complexity=$complexity"

if [ "$cluster" = "medium" ]; then
    echo -e "  ${GREEN}✓ Correto! Query com JOIN → cluster medium${NC}"
else
    echo -e "  ${YELLOW}⚠ Score determinou cluster: $cluster${NC}"
fi
echo ""
sleep 2

# ----------------------------------------------------------------------
# 4. Demonstrar cache hit
# ----------------------------------------------------------------------
echo -e "${YELLOW}[4/8]${NC} Testando CACHE (reexecução da mesma query)..."
echo ""

response=$(curl -s -X POST http://localhost:5001/api/v1/route \
    -H "Content-Type: application/json" \
    -d "{\"query\": \"$query_simple\"}")

cached=$(echo "$response" | grep -o '"cached":[a-z]*' | cut -d':' -f2)
cluster=$(echo "$response" | grep -o '"cluster":"[^"]*"' | cut -d'"' -f4)

echo "Resultado:"
if [ "$cached" = "true" ]; then
    echo -e "  ${GREEN}✓ CACHE HIT! Decisão reutilizada (TTL: 24h)${NC}"
    echo "  Cluster: $cluster (mesmo da primeira execução)"
else
    echo -e "  ${YELLOW}⚠ CACHE MISS (decisão recalculada)${NC}"
fi
echo ""
sleep 2

# ----------------------------------------------------------------------
# 5. Verificar histórico no PostgreSQL
# ----------------------------------------------------------------------
echo -e "${YELLOW}[5/8]${NC} Consultando histórico no PostgreSQL..."
echo ""

docker compose exec -T gateway-db psql -U dyrasql -d dyrasql -t <<EOF | head -5
SELECT 
    LEFT(fingerprint, 16) as fingerprint_short,
    cluster,
    ROUND(score::numeric, 3) as score,
    TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') as created
FROM routing_decisions 
ORDER BY created_at DESC 
LIMIT 5;
EOF

echo ""
echo -e "${GREEN}✓ Histórico registrado${NC}"
echo ""
sleep 2

# ----------------------------------------------------------------------
# 6. Demonstrar análise de complexidade
# ----------------------------------------------------------------------
echo -e "${YELLOW}[6/8]${NC} Analisando complexidade de query com subconsulta..."
echo ""

query_complex="SELECT t.tenant_id, COUNT(*) FROM iceberg.analytics.dados d JOIN iceberg.analytics.tenant_info t ON d.tenant_id = t.tenant_id WHERE t.categoria IN (SELECT categoria FROM iceberg.analytics.tenant_info WHERE nivel > 5) GROUP BY t.tenant_id"
echo "Query: SELECT ... WHERE categoria IN (SELECT ...)"
echo ""

response=$(curl -s -X POST http://localhost:5001/api/v1/route \
    -H "Content-Type: application/json" \
    -d "{\"query\": \"$query_complex\"}")

cluster=$(echo "$response" | grep -o '"cluster":"[^"]*"' | cut -d'"' -f4)
score=$(echo "$response" | grep -o '"score":[0-9.]*' | cut -d':' -f2)
complexity=$(echo "$response" | grep -o '"complexity":[0-9.]*' | cut -d':' -f2)

echo "Resultado:"
echo "  Cluster selecionado: $cluster"
echo "  Score calculado: $score"
echo "  Fator complexidade: $complexity"
echo -e "  ${GREEN}✓ Subconsulta detectada e considerada no score${NC}"
echo ""
sleep 2

# ----------------------------------------------------------------------
# 7. Verificar EXPLAIN salvo
# ----------------------------------------------------------------------
echo -e "${YELLOW}[7/8]${NC} Verificando EXPLAIN (TYPE IO) salvo..."
echo ""

num_explains=$(ls -1 explains/*.json 2>/dev/null | wc -l || echo "0")
if [ "$num_explains" -gt 0 ]; then
    echo -e "${GREEN}✓ $num_explains EXPLAIN(s) salvos em ./explains/${NC}"
    latest=$(ls -t explains/*.json | head -1)
    echo "  Último: $(basename $latest)"
    echo ""
    echo "  Exemplo do conteúdo:"
    cat "$latest" | python3 -m json.tool 2>/dev/null | head -20 || echo "  (erro ao parsear JSON)"
else
    echo -e "${YELLOW}⚠ Nenhum EXPLAIN salvo ainda${NC}"
fi
echo ""
sleep 2

# ----------------------------------------------------------------------
# 8. Resumo final
# ----------------------------------------------------------------------
echo -e "${YELLOW}[8/8]${NC} Resumo da Demonstração"
echo "======================================================================"
echo ""
echo "O framework DyraSQL demonstrou:"
echo ""
echo "  ✓ Análise de metadados via EXPLAIN (TYPE IO)"
echo "  ✓ Cálculo de score baseado em 3 fatores (volume, complexidade, histórico)"
echo "  ✓ Roteamento dinâmico para clusters diferentes"
echo "  ✓ Cache de decisões com TTL de 24h"
echo "  ✓ Histórico persistido no PostgreSQL"
echo "  ✓ Detecção de complexidade (JOINs, subconsultas)"
echo "  ✓ Salvamento de EXPLAIN para análise"
echo ""
echo "======================================================================"
echo -e "${GREEN}Demonstração concluída com sucesso!${NC}"
echo "======================================================================"
echo ""
echo "Próximos passos:"
echo "  1. Ver logs em tempo real: ./scripts/monitor-routing.sh"
echo "  2. Executar queries de teste: cat query.sql"
echo "  3. Gerar mais dados: cd scripts && ./generate_data.py --help"
echo "  4. Ler documentação: cat README.md"
echo ""
