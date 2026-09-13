#!/bin/bash

# Script de instalação do LaTeX para WSL - TCC
# Instala todos os pacotes necessários para compilação do TCC

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

# Verificar se está rodando no WSL
if ! grep -q Microsoft /proc/version 2>/dev/null; then
    print_warning "Este script foi otimizado para WSL, mas pode funcionar em outros sistemas Linux"
fi

print_message "Iniciando instalação do LaTeX para TCC..."

# Atualizar lista de pacotes
print_message "Atualizando lista de pacotes..."
sudo apt update

# Instalar dependências básicas
print_message "Instalando dependências básicas..."
sudo apt install -y \
    wget \
    curl \
    git \
    make \
    build-essential \
    software-properties-common

# Instalar LaTeX básico
print_message "Instalando LaTeX básico..."
sudo apt install -y \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-bibtex-extra \
    texlive-fonts-recommended \
    texlive-fonts-extra

# Instalar pacotes específicos para ABNT
print_message "Instalando pacotes ABNT..."
sudo apt install -y \
    texlive-publishers \
    texlive-science \
    texlive-lang-portuguese

# Instalar pacotes adicionais úteis
print_message "Instalando pacotes adicionais..."
sudo apt install -y \
    texlive-xetex \
    texlive-luatex \
    texlive-latex-recommended \
    texlive-pictures \
    texlive-plain-generic

# Verificar instalação
print_message "Verificando instalação..."
if command -v pdflatex &> /dev/null; then
    print_success "pdflatex instalado com sucesso!"
    pdflatex --version | head -1
else
    print_error "Falha na instalação do pdflatex"
    exit 1
fi

if command -v bibtex &> /dev/null; then
    print_success "bibtex instalado com sucesso!"
else
    print_error "Falha na instalação do bibtex"
    exit 1
fi

# Limpar cache
print_message "Limpando cache de pacotes..."
sudo apt autoremove -y
sudo apt autoclean

# Criar alias útil
print_message "Criando aliases úteis..."
cat >> ~/.bashrc << 'EOF'

# Aliases para TCC LaTeX
alias tcc-compile='make compile'
alias tcc-beamer='make beamer'
alias tcc-clean='make clean'
alias tcc-help='make help'

EOF

print_success "Instalação concluída com sucesso!"
print_message "Para usar os aliases, execute: source ~/.bashrc"
print_message "Comandos disponíveis:"
echo "  tcc-compile  - Compilação completa"
echo "  tcc-quick    - Compilação rápida"
echo "  tcc-clean    - Limpeza de arquivos"
echo "  tcc-help     - Ajuda do Makefile"

print_message "Testando compilação do TCC..."
if [ -f "latex/principal.tex" ]; then
    print_message "Arquivo latex/principal.tex encontrado. Testando compilação..."
    make compile
    if [ $? -eq 0 ]; then
        print_success "Compilação de teste bem-sucedida!"
        print_message "PDF gerado: latex/principal.pdf"
    else
        print_warning "Compilação de teste falhou. Verifique os erros acima."
    fi
else
    print_warning "Arquivo latex/principal.tex não encontrado. Execute 'make compile' quando estiver no diretório do projeto."
fi

print_success "Instalação do LaTeX para TCC concluída!"
print_message "Agora você pode compilar seu TCC usando: make compile"
