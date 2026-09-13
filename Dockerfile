# Dockerfile para compilação de documentos LaTeX
# Usa imagem oficial do TeX Live com suporte completo

FROM texlive/texlive:latest

# Metadados
LABEL maintainer="TCC Project"
LABEL description="Ambiente Docker para compilação de documentos LaTeX"

# Instala dependências adicionais úteis
RUN apt-get update && apt-get install -y \
    make \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Define o diretório de trabalho
WORKDIR /tcc

# Copia arquivos do projeto
COPY . .

# Comando padrão: compilar o documento
CMD ["make", "compile"]
