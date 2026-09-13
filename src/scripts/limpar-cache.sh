#!/bin/bash
# Limpa o cache de decisoes de roteamento no PostgreSQL

echo "Limpando cache do DyraSQL Core..."
echo ""

if ! docker compose ps | grep -q dyrasql-core; then
    echo "ERROR: dyrasql-core nao esta em execucao"
    exit 1
fi

docker compose exec -T dyrasql-core python3 << 'EOF'
from history_manager import HistoryManager

try:
    hm = HistoryManager()
    deleted = hm.clear_cache()
    print(f"SUCCESS: {deleted} registros removidos do cache")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
EOF

echo ""
echo "Cache limpo"
