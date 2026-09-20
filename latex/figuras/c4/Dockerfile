FROM eclipse-temurin:17-jre

# Versão do Structurizr CLI
ARG STRUCTURIZR_CLI_VERSION=2025.11.09

# Diretório de trabalho
WORKDIR /workspace

# Dependências básicas
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    default-jre \
    graphviz \
    wget \
 && rm -rf /var/lib/apt/lists/*

# Instala PlantUML mais recente
RUN wget -O /opt/plantuml.jar https://github.com/plantuml/plantuml/releases/download/v1.2024.8/plantuml-1.2024.8.jar \
 && echo '#!/bin/bash\njava -Xmx2048m -DPLANTUML_LIMIT_SIZE=16384 -jar /opt/plantuml.jar "$@"' > /usr/local/bin/plantuml \
 && chmod +x /usr/local/bin/plantuml
ENV PLANTUML_LIMIT_SIZE=16384

# Baixa e instala o Structurizr CLI
RUN curl -L -f "https://github.com/structurizr/cli/releases/download/v${STRUCTURIZR_CLI_VERSION}/structurizr-cli.zip" \
    -o /tmp/structurizr-cli.zip \
 && test -s /tmp/structurizr-cli.zip \
 && unzip /tmp/structurizr-cli.zip -d /opt \
 && rm /tmp/structurizr-cli.zip \
 && chmod +x /opt/structurizr.sh

# Structurizr Lite pode ser usado separadamente para visualização interativa
# Para exportar PNG no formato nativo, use o site estático gerado (static/index.html)

# Deixa o script acessível no PATH
ENV PATH="/opt:${PATH}"

# Diretório padrão onde você vai montar seus arquivos DSL
VOLUME ["/workspace"]

# EntryPoint padrão para usar o CLI diretamente
ENTRYPOINT ["structurizr.sh"]
CMD ["--help"]
