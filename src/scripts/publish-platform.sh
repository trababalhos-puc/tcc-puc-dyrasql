#!/bin/bash
# Publica a imagem dyrasql/platform (MinIO + Trino Gateway) no GitHub Container Registry.
# Sem argumentos. Ajuste as variaveis abaixo se necessario.
# Requer docker e gh autenticados (o token precisa do escopo write:packages,
# para adicionar rode: gh auth refresh -s write:packages).

set -euo pipefail

REGISTRY="ghcr.io"
OWNER="trababalhos-puc"
IMAGE_NAME="dyrasql-platform"
VERSION="1.0.0"
PLATFORMS="linux/amd64,linux/arm64"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$(dirname "$SCRIPT_DIR")"
TARGET="${REGISTRY}/${OWNER}/${IMAGE_NAME}:${VERSION}"

GH_USER="$(gh api user --jq .login)"
gh auth token | docker login "$REGISTRY" -u "$GH_USER" --password-stdin

docker buildx inspect dyrasql-builder >/dev/null 2>&1 || docker buildx create --name dyrasql-builder --use >/dev/null
docker buildx use dyrasql-builder

docker buildx build \
    --platform "$PLATFORMS" \
    -f "$SRC_DIR/platform/Dockerfile" \
    -t "$TARGET" \
    --push \
    "$SRC_DIR"

echo "Imagem publicada em $TARGET"
echo "Para usar, no docker-compose.yml troque o bloco build por image: $TARGET"
