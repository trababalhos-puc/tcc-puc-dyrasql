#!/bin/bash

# Script de instalação mínima do LaTeX para WSL - TCC
# Instala apenas os pacotes essenciais para compilação do TCC

set -e

# Cores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_message() {
    echo -e "${BLUE}[TCC LaTeX]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_message "Instalação mínima do LaTeX para TCC..."

# Atualizar e instalar pacotes essenciais
sudo apt update
sudo apt install -y texlive-latex-base texlive-latex-extra texlive-bibtex-extra texlive-fonts-recommended

# Verificar instalação
if command -v pdflatex &> /dev/null; then
    print_success "LaTeX instalado com sucesso!"
    print_message "Testando compilação..."
    make quick
    print_success "Pronto para usar! Execute 'make pdf' para compilação completa."
else
    echo "Erro na instalação"
    exit 1
fi
