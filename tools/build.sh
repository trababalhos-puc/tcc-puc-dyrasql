#!/bin/bash

# Script para build e compilação do TCC usando Docker

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para imprimir mensagens coloridas
print_message() {
    echo -e "${BLUE}[TCC LaTeX]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar se Docker está instalado
if ! command -v docker &> /dev/null; then
    print_error "Docker não está instalado. Por favor, instale o Docker primeiro."
    exit 1
fi

# Verificar se docker-compose está instalado
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose não está instalado. Por favor, instale o Docker Compose primeiro."
    exit 1
fi

# Função para build da imagem
build_image() {
    print_message "Construindo imagem Docker do LaTeX..."
    docker-compose build latex
    print_success "Imagem construída com sucesso!"
}

# Função para compilação completa
compile_full() {
    print_message "Iniciando compilação completa do TCC..."
    docker-compose run --rm latex
    print_success "Compilação completa finalizada!"
}

# Função para compilação rápida
compile_quick() {
    print_message "Iniciando compilação rápida do TCC..."
    docker-compose run --rm latex-quick
    print_success "Compilação rápida finalizada!"
}

# Função para limpeza
clean_files() {
    print_message "Limpando arquivos auxiliares..."
    docker-compose run --rm latex-clean
    print_success "Limpeza concluída!"
}

# Função para mostrar ajuda
show_help() {
    echo "Uso: $0 [COMANDO]"
    echo ""
    echo "Comandos disponíveis:"
    echo "  build    - Construir a imagem Docker"
    echo "  compile  - Compilação completa (com bibliografia)"
    echo "  quick    - Compilação rápida (sem bibliografia)"
    echo "  clean    - Limpar arquivos auxiliares"
    echo "  all      - Build + compilação completa"
    echo "  help     - Mostrar esta ajuda"
    echo ""
    echo "Exemplos:"
    echo "  $0 build"
    echo "  $0 compile"
    echo "  $0 all"
}

# Processar argumentos
case "${1:-help}" in
    "build")
        build_image
        ;;
    "compile")
        compile_full
        ;;
    "quick")
        compile_quick
        ;;
    "clean")
        clean_files
        ;;
    "all")
        build_image
        compile_full
        ;;
    "help"|*)
        show_help
        ;;
esac
