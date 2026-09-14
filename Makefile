# Makefile para Projeto TCC
# Suporte a múltiplos sistemas operacionais

# Nome do arquivo principal (em latex/)
MAIN = latex/principal

# Comandos de compilação
PDFLATEX = pdflatex
BIBTEX = bibtex

# Arquivo PDF de saída
PDF = $(MAIN).pdf

# Nome do PDF de entrega, conforme padrão do Regimento de TCC (Seção 8):
# "TCC_<nome completo do aluno>.pdf"
DELIVERY_PDF = TCC_Aristides Henrique Gonçalves da Cruz.pdf

# Arquivos auxiliares para limpeza
AUX_FILES = *.aux *.bbl *.blg *.log *.out *.toc *.fdb_latexmk *.fls *.synctex.gz

# Cores para output (compatíveis com a maioria dos terminais)
BLUE = \033[0;34m
GREEN = \033[0;32m
YELLOW = \033[1;33m
RED = \033[0;31m
NC = \033[0m

# Detecta o sistema operacional
OS := $(shell uname -s)
ifeq ($(OS),Darwin)
    # macOS
    PACKAGE_MANAGER = brew
    INSTALL_CMD = $(PACKAGE_MANAGER) install
    LATEX_PACKAGES = basictex
else ifeq ($(OS),Linux)
    # Detecta a distribuição Linux
    ifneq (,$(wildcard /etc/debian_version))
        # Debian/Ubuntu
        PACKAGE_MANAGER = sudo apt-get
        INSTALL_CMD = $(PACKAGE_MANAGER) install -y
        LATEX_PACKAGES = texlive-latex-base texlive-latex-extra texlive-bibtex-extra texlive-fonts-recommended texlive-fonts-extra texlive-lang-portuguese texlive-publishers texlive-science texlive-xetex texlive-luatex texlive-latex-recommended texlive-pictures texlive-plain-generic
    else ifneq (,$(wildcard /etc/redhat-release))
        # CentOS/RHEL/Fedora
        PACKAGE_MANAGER = sudo dnf
        INSTALL_CMD = $(PACKAGE_MANAGER) install -y
        LATEX_PACKAGES = texlive texlive-latex texlive-collection-fontsrecommended texlive-collection-langportuguese texlive-science
    else ifneq (,$(wildcard /etc/arch-release))
        # Arch Linux
        PACKAGE_MANAGER = sudo pacman
        INSTALL_CMD = $(PACKAGE_MANAGER) -S --noconfirm
        LATEX_PACKAGES = texlive-most
    else
        # Outros sistemas Linux
        PACKAGE_MANAGER = echo "Sistema não suportado automaticamente. Instale o LaTeX manualmente e execute 'make compile'."
        INSTALL_CMD = $(PACKAGE_MANAGER)
        LATEX_PACKAGES =
    endif
else
    # Windows/Outros
    PACKAGE_MANAGER = echo "Sistema não suportado automaticamente. Instale o LaTeX manualmente e execute 'make compile'."
    INSTALL_CMD = $(PACKAGE_MANAGER)
    LATEX_PACKAGES =
endif

.PHONY: all install convert compile beamer clean zip format lint help docker-build docker-compile docker-beamer docker-clean docker-shell c4-build c4-compile c4-clean

# Comando padrão
all: help

# 1. Instalar dependências de acordo com o sistema operacional
install:
	@echo "$(BLUE)[TCC]$(NC) Instalando dependências para $(OS)..."
	@echo "$(BLUE)[Sistema]$(NC) Atualizando repositórios..."
	@case "$(OS)" in \
		Linux) \
			if [ -f "/etc/debian_version" ]; then \
				sudo apt-get update || echo "$(YELLOW)[AVISO]$(NC) Erro ao atualizar repositórios, continuando..."; \
			elif [ -f "/etc/redhat-release" ]; then \
				sudo dnf check-update || echo "$(YELLOW)[AVISO]$(NC) Erro ao atualizar repositórios, continuando..."; \
			elif [ -f "/etc/arch-release" ]; then \
				sudo pacman -Sy || echo "$(YELLOW)[AVISO]$(NC) Erro ao atualizar repositórios, continuando..."; \
			fi; \
			;; \
		Darwin) \
			brew update || echo "$(YELLOW)[AVISO]$(NC) Erro ao atualizar repositórios, continuando..."; \
			;; \
		*) \
			echo "$(YELLOW)[AVISO]$(NC) Atualização de repositórios não suportada para este sistema."; \
			;; \
	esac
	@echo "$(BLUE)[LaTeX]$(NC) Instalando LaTeX..."
	@if [ ! -z "$(LATEX_PACKAGES)" ]; then \
		$(INSTALL_CMD) $(LATEX_PACKAGES) || { \
			echo "$(YELLOW)[AVISO]$(NC) Falha na instalação automática do LaTeX."; \
			echo "$(YELLOW)[AVISO]$(NC) Por favor, instale o LaTeX manualmente:"; \
			case "$(OS)" in \
				Linux) \
					if [ -f "/etc/debian_version" ]; then \
						echo "sudo apt-get install -y texlive-latex-base texlive-latex-extra texlive-bibtex-extra texlive-lang-portuguese"; \
					elif [ -f "/etc/redhat-release" ]; then \
						echo "sudo dnf install -y texlive texlive-latex texlive-collection-langportuguese"; \
					elif [ -f "/etc/arch-release" ]; then \
						echo "sudo pacman -S texlive-most"; \
					fi; \
					;; \
				Darwin) \
					echo "brew install basictex"; \
					echo "ou baixe e instale MacTeX: https://www.tug.org/mactex/"; \
					;; \
				*) \
					echo "Para Windows: baixe e instale MiKTeX: https://miktex.org/download"; \
					;; \
			esac; \
		}; \
	else \
		echo "$(YELLOW)[AVISO]$(NC) Instalação automática não disponível para seu sistema."; \
		echo "$(YELLOW)[AVISO]$(NC) Por favor, instale o LaTeX manualmente:"; \
		echo "- Windows: https://miktex.org/download"; \
		echo "- macOS: https://www.tug.org/mactex/"; \
		echo "- Linux: Use seu gerenciador de pacotes para instalar texlive"; \
	fi
	
	@if command -v $(PDFLATEX) >/dev/null 2>&1; then \
		echo "$(GREEN)[SUCESSO]$(NC) LaTeX instalado!"; \
	else \
		echo "$(YELLOW)[AVISO]$(NC) LaTeX não detectado após instalação. Verifique se está no PATH."; \
	fi
	
	@echo "$(BLUE)[Python]$(NC) Verificando dependências Python..."
	@if [ -f "requirements.txt" ]; then \
		if command -v pip3 >/dev/null 2>&1; then \
			pip3 install -r requirements.txt || echo "$(YELLOW)[AVISO]$(NC) Erro ao instalar dependências Python."; \
			echo "$(GREEN)[SUCESSO]$(NC) Dependências Python instaladas!"; \
		else \
			echo "$(YELLOW)[AVISO]$(NC) pip3 não encontrado. Instale o Python e pip manualmente."; \
		fi; \
	else \
		echo "$(YELLOW)[AVISO]$(NC) Arquivo requirements.txt não encontrado."; \
	fi
	
	@echo "$(BLUE)[TCC]$(NC) Verificando estrutura de diretórios..."
	@if [ ! -d "latex/figuras" ]; then \
		mkdir -p latex/figuras; \
		echo "$(BLUE)[INFO]$(NC) Diretório latex/figuras criado."; \
	fi
	@if [ ! -d "latex/modulos" ]; then \
		mkdir -p latex/modulos; \
		echo "$(BLUE)[INFO]$(NC) Diretório latex/modulos criado."; \
	fi
	@if [ ! -d "references" ]; then \
		mkdir -p references; \
		echo "$(BLUE)[INFO]$(NC) Diretório references criado."; \
	fi
	@echo "$(GREEN)[SUCESSO]$(NC) Estrutura de diretórios verificada!"

# 2. Converter PDFs em references
convert:
	@echo "$(BLUE)[TCC]$(NC) Convertendo PDFs da pasta references..."
	@if [ ! -d "references" ]; then \
		echo "$(YELLOW)[AVISO]$(NC) Pasta references não encontrada!"; \
		mkdir -p references; \
		echo "$(BLUE)[INFO]$(NC) Pasta references criada. Adicione seus PDFs e tente novamente."; \
		exit 0; \
	fi
	@if [ -z "$(shell find references -name '*.pdf' 2>/dev/null)" ]; then \
		echo "$(YELLOW)[AVISO]$(NC) Nenhum arquivo PDF encontrado na pasta references."; \
		exit 0; \
	fi
	@if command -v python3 >/dev/null 2>&1; then \
		if [ -d "tools" ] && [ -f "tools/pdf_to_markdown.py" ]; then \
			for pdf in references/*.pdf; do \
				if [ -f "$$pdf" ]; then \
					echo "$(BLUE)[INFO]$(NC) Convertendo: $$pdf"; \
					python3 tools/pdf_to_markdown.py --extract-images "$$pdf" || \
					echo "$(YELLOW)[AVISO]$(NC) Erro ao converter $$pdf"; \
				fi; \
			done; \
			echo "$(GREEN)[SUCESSO]$(NC) Conversão de referências concluída!"; \
		else \
			echo "$(YELLOW)[AVISO]$(NC) Script pdf_to_markdown.py não encontrado!"; \
			echo "$(BLUE)[INFO]$(NC) Verifique se o diretório tools contém o script de conversão."; \
		fi; \
	else \
		echo "$(YELLOW)[AVISO]$(NC) Python3 não encontrado!"; \
		echo "$(BLUE)[INFO]$(NC) Instale o Python 3 para usar esta funcionalidade."; \
	fi

# 3. Compilar o artigo para PDF
compile:
	@echo "$(BLUE)[TCC]$(NC) Compilando artigo LaTeX..."
	@if ! command -v $(PDFLATEX) >/dev/null 2>&1; then \
		echo "$(RED)[ERRO]$(NC) LaTeX não encontrado! Execute 'make install' primeiro."; \
		exit 1; \
	fi
	@cd latex && echo "$(BLUE)[LaTeX]$(NC) Compilando LaTeX (primeira passagem)..." && \
	$(PDFLATEX) -interaction=nonstopmode principal.tex > /dev/null 2>&1 || true
	@if [ -f "latex/bibliografia.bib" ]; then \
		cd latex && echo "$(BLUE)[LaTeX]$(NC) Processando bibliografia..." && \
		$(BIBTEX) principal > /dev/null 2>&1 || echo "$(YELLOW)[AVISO]$(NC) Erro no processamento da bibliografia."; \
	else \
		echo "$(YELLOW)[AVISO]$(NC) Arquivo bibliografia.bib não encontrado."; \
	fi
	@cd latex && echo "$(BLUE)[LaTeX]$(NC) Recompilando com referências (segunda passagem)..." && \
	$(PDFLATEX) -interaction=nonstopmode principal.tex > /dev/null 2>&1 || true
	@cd latex && echo "$(BLUE)[LaTeX]$(NC) Finalizando (terceira passagem)..." && \
	$(PDFLATEX) -interaction=nonstopmode principal.tex > /dev/null 2>&1 || true
	@if [ -f "latex/principal.pdf" ]; then \
		echo "$(GREEN)[SUCESSO]$(NC) Compilação concluída: latex/principal.pdf"; \
		echo "$(BLUE)[INFO]$(NC) Verifique latex/principal.log para warnings ou erros."; \
		cp "latex/principal.pdf" "doc/TCC_Aristides Henrique Gonçalves da Cruz.pdf"; \
		echo "$(GREEN)[SUCESSO]$(NC) Cópia de entrega gerada em doc/"; \
		if command -v xdg-open >/dev/null 2>&1; then \
			echo "$(BLUE)[INFO]$(NC) Para visualizar: xdg-open latex/principal.pdf"; \
		elif command -v open >/dev/null 2>&1; then \
			echo "$(BLUE)[INFO]$(NC) Para visualizar: open latex/principal.pdf"; \
		fi; \
	else \
		echo "$(RED)[ERRO]$(NC) Falha na compilação. Arquivo PDF não gerado."; \
		echo "$(RED)[ERRO]$(NC) Verifique o arquivo latex/principal.log para detalhes."; \
		exit 1; \
	fi

# Compilar apresentação beamer
beamer:
	@echo "$(BLUE)[TCC]$(NC) Compilando apresentação Beamer..."
	@if [ ! -d "latex/beamer" ]; then \
		echo "$(YELLOW)[AVISO]$(NC) Pasta latex/beamer não encontrada!"; \
		exit 0; \
	fi
	@if [ ! -f "latex/beamer/document.tex" ]; then \
		echo "$(YELLOW)[AVISO]$(NC) Arquivo latex/beamer/document.tex não encontrado!"; \
		exit 0; \
	fi
	@if ! command -v $(PDFLATEX) >/dev/null 2>&1; then \
		echo "$(RED)[ERRO]$(NC) LaTeX não encontrado! Execute 'make install' primeiro."; \
		exit 1; \
	fi
	@echo "$(BLUE)[LaTeX]$(NC) Compilando apresentação Beamer..."
	cd latex/beamer && $(PDFLATEX) -interaction=nonstopmode document.tex || \
		{ echo "$(RED)[ERRO]$(NC) Falha na compilação da apresentação."; exit 1; }
	@if [ -f "latex/beamer/document.pdf" ]; then \
		echo "$(GREEN)[SUCESSO]$(NC) Apresentação compilada: latex/beamer/document.pdf"; \
	else \
		echo "$(RED)[ERRO]$(NC) Falha na compilação da apresentação."; \
	fi

# 4. Formatação e Linting
format:
	@echo "$(BLUE)[TCC]$(NC) Formatando código Python..."
	@if [ ! -d "scripts" ]; then \
		echo "$(YELLOW)[AVISO]$(NC) Pasta scripts não encontrada!"; \
		exit 0; \
	fi
	@if [ -z "$(shell find scripts -name '*.py' 2>/dev/null)" ]; then \
		echo "$(YELLOW)[AVISO]$(NC) Nenhum arquivo Python encontrado na pasta scripts."; \
		exit 0; \
	fi
	@if command -v black >/dev/null 2>&1; then \
		black tools/*.py; \
		echo "$(GREEN)[SUCESSO]$(NC) Código formatado com black!"; \
	else \
		echo "$(YELLOW)[AVISO]$(NC) black não encontrado!"; \
		echo "$(BLUE)[INFO]$(NC) Instale com: pip install black"; \
	fi
	@if command -v isort >/dev/null 2>&1; then \
		isort tools/*.py; \
		echo "$(GREEN)[SUCESSO]$(NC) Imports organizados com isort!"; \
	else \
		echo "$(YELLOW)[AVISO]$(NC) isort não encontrado!"; \
		echo "$(BLUE)[INFO]$(NC) Instale com: pip install isort"; \
	fi

lint:
	@echo "$(BLUE)[TCC]$(NC) Verificando código Python..."
	@if [ ! -d "scripts" ]; then \
		echo "$(YELLOW)[AVISO]$(NC) Pasta scripts não encontrada!"; \
		exit 0; \
	fi
	@if [ -z "$(shell find scripts -name '*.py' 2>/dev/null)" ]; then \
		echo "$(YELLOW)[AVISO]$(NC) Nenhum arquivo Python encontrado na pasta scripts."; \
		exit 0; \
	fi
	@if command -v flake8 >/dev/null 2>&1; then \
		flake8 tools/*.py --max-line-length=100 --ignore=E203,W503; \
		echo "$(GREEN)[SUCESSO]$(NC) Linting concluído!"; \
	else \
		echo "$(YELLOW)[AVISO]$(NC) flake8 não encontrado!"; \
		echo "$(BLUE)[INFO]$(NC) Instale com: pip install flake8"; \
	fi

# Limpeza de arquivos auxiliares
clean:
	@echo "$(BLUE)[TCC]$(NC) Limpando arquivos auxiliares..."
	@cd latex && rm -f *.aux *.bbl *.blg *.log *.out *.toc *.fdb_latexmk *.fls *.synctex.gz 2>/dev/null || true
	@if [ -d "latex/beamer" ]; then \
		cd latex/beamer && rm -f *.aux *.log *.nav *.out *.snm *.toc *.vrb *.fdb_latexmk *.fls *.synctex.gz 2>/dev/null || true; \
	fi
	@rm -f embedding_system.log 2>/dev/null || true
	@echo "$(GREEN)[SUCESSO]$(NC) Limpeza concluída!"

# Criar arquivo ZIP do TCC (apenas arquivos essenciais)
zip:
	@echo "$(BLUE)[TCC]$(NC) Criando arquivo ZIP do TCC..."
	@ZIP_NAME="tcc-$$(date +%Y%m%d-%H%M%S).zip"; \
	files_exist=true; \
	for file in latex/principal.tex latex/principal.pdf latex/bibliografia.bib; do \
		if [ ! -f "$$file" ]; then \
			echo "$(YELLOW)[AVISO]$(NC) Arquivo $$file não encontrado."; \
			files_exist=false; \
		fi; \
	done; \
	if [ "$$files_exist" = true ]; then \
		if command -v zip >/dev/null 2>&1; then \
			zip -rq $$ZIP_NAME \
				latex/ \
				doc/ \
				README.md \
				LICENSE \
				CITATION.cff \
				-x "*.aux" "*.log" "*.bbl" "*.blg" "*.out" "*.toc" "*.synctex.gz" "*.nav" "*.snm" "*.vrb" \
				-x "*/.DS_Store" "*/Thumbs.db"; \
			echo "$(GREEN)[SUCESSO]$(NC) Arquivo ZIP do TCC criado: $$ZIP_NAME"; \
		else \
			echo "$(RED)[ERRO]$(NC) Comando 'zip' não encontrado. Instale o zip."; \
			exit 1; \
		fi; \
	else \
		echo "$(RED)[ERRO]$(NC) Arquivos essenciais não encontrados. Compile o TCC primeiro com 'make compile'."; \
		exit 1; \
	fi \
		else \
			echo "$(YELLOW)[AVISO]$(NC) Comando zip não encontrado."; \
		fi; \
	else \
		echo "$(RED)[ERRO]$(NC) Não foi possível criar o ZIP devido a arquivos faltantes."; \
		echo "$(BLUE)[INFO]$(NC) Execute 'make compile' primeiro."; \
	fi

# ========================================
# Comandos Docker
# ========================================

# Construir imagem Docker
docker-build:
	@echo "$(BLUE)[Docker]$(NC) Construindo imagem Docker para compilação LaTeX..."
	@if ! command -v docker >/dev/null 2>&1; then \
		echo "$(RED)[ERRO]$(NC) Docker não encontrado!"; \
		echo "$(BLUE)[INFO]$(NC) Instale o Docker: https://www.docker.com/get-started"; \
		exit 1; \
	fi
	cd latex && docker-compose build
	@echo "$(GREEN)[SUCESSO]$(NC) Imagem Docker construída com sucesso!"

# Compilar usando Docker
docker-compile:
	@echo "$(BLUE)[Docker]$(NC) Compilando artigo LaTeX usando Docker..."
	@if ! command -v docker >/dev/null 2>&1; then \
		echo "$(RED)[ERRO]$(NC) Docker não encontrado!"; \
		echo "$(BLUE)[INFO]$(NC) Instale o Docker: https://www.docker.com/get-started"; \
		exit 1; \
	fi
	@if ! docker images | grep -q "tcc-latex"; then \
		echo "$(BLUE)[Docker]$(NC) Imagem não encontrada. Construindo..."; \
		$(MAKE) docker-build; \
	fi
	cd latex && docker-compose run --rm latex
	@echo "$(GREEN)[SUCESSO]$(NC) Compilação via Docker concluída!"
	@if [ -f "latex/principal.pdf" ]; then \
		echo "$(GREEN)[SUCESSO]$(NC) PDF gerado: latex/principal.pdf"; \
		cp "latex/principal.pdf" "doc/principal.pdf"; \
		cp "latex/principal.pdf" "doc/$(DELIVERY_PDF)"; \
		echo "$(GREEN)[SUCESSO]$(NC) Cópia de entrega gerada: doc/$(DELIVERY_PDF)"; \
		if command -v open >/dev/null 2>&1; then \
			echo "$(BLUE)[INFO]$(NC) Para visualizar: open latex/principal.pdf"; \
			echo "$(BLUE)[INFO]$(NC) Arquivo de entrega: open doc/$(DELIVERY_PDF)"; \
		fi; \
	else \
		echo "$(RED)[ERRO]$(NC) Falha na compilação. Verifique latex/principal.log"; \
	fi

# Compilar apresentação Beamer usando Docker
docker-beamer:
	@echo "$(BLUE)[Docker]$(NC) Compilando apresentação Beamer usando Docker..."
	@if ! command -v docker >/dev/null 2>&1; then \
		echo "$(RED)[ERRO]$(NC) Docker não encontrado!"; \
		echo "$(BLUE)[INFO]$(NC) Instale o Docker: https://www.docker.com/get-started"; \
		exit 1; \
	fi
	@if ! docker images | grep -q "tcc-latex"; then \
		echo "$(BLUE)[Docker]$(NC) Imagem não encontrada. Construindo..."; \
		$(MAKE) docker-build; \
	fi
	docker-compose run --rm latex make beamer
	@if [ -f "beamer/document.pdf" ]; then \
		echo "$(GREEN)[SUCESSO]$(NC) Compilação concluída: beamer/document.pdf"; \
		if command -v open >/dev/null 2>&1; then \
			echo "$(BLUE)[INFO]$(NC) Para visualizar: open beamer/document.pdf"; \
		fi; \
	else \
		echo "$(RED)[ERRO]$(NC) Falha na compilação da apresentação."; \
	fi

# Limpar containers e volumes Docker
docker-clean:
	@echo "$(BLUE)[Docker]$(NC) Limpando containers e volumes Docker..."
	docker-compose down -v
	@echo "$(GREEN)[SUCESSO]$(NC) Limpeza Docker concluída!"

# Abrir shell interativo no container Docker
docker-shell:
	@echo "$(BLUE)[Docker]$(NC) Abrindo shell interativo no container..."
	@if ! command -v docker >/dev/null 2>&1; then \
		echo "$(RED)[ERRO]$(NC) Docker não encontrado!"; \
		exit 1; \
	fi
	@if ! docker images | grep -q "tcc-latex"; then \
		echo "$(BLUE)[Docker]$(NC) Imagem não encontrada. Construindo..."; \
		$(MAKE) docker-build; \
	fi
	docker-compose run --rm latex /bin/bash

# ========================================
# Comandos C4/Structurizr
# ========================================

# Construir imagem Docker para Structurizr
c4-build:
	@echo "$(BLUE)[C4]$(NC) Construindo imagem Docker para Structurizr..."
	@if ! command -v docker >/dev/null 2>&1; then \
		echo "$(RED)[ERRO]$(NC) Docker não encontrado!"; \
		echo "$(BLUE)[INFO]$(NC) Instale o Docker: https://www.docker.com/get-started"; \
		exit 1; \
	fi
	@if [ ! -f "figuras/c4/Dockerfile" ]; then \
		echo "$(RED)[ERRO]$(NC) Dockerfile não encontrado em figuras/c4/"; \
		exit 1; \
	fi
	docker build -t structurizr-cli -f figuras/c4/Dockerfile figuras/c4/
	@echo "$(GREEN)[SUCESSO]$(NC) Imagem Docker Structurizr construída com sucesso!"

# Compilar arquivo DSL para diagramas
c4-compile:
	@echo "$(BLUE)[C4]$(NC) Compilando diagramas C4..."
	@if ! command -v docker >/dev/null 2>&1; then \
		echo "$(RED)[ERRO]$(NC) Docker não encontrado!"; \
		echo "$(BLUE)[INFO]$(NC) Instale o Docker: https://www.docker.com/get-started"; \
		exit 1; \
	fi
	@if [ ! -f "figuras/c4/c4-completo.dsl" ]; then \
		echo "$(RED)[ERRO]$(NC) Arquivo c4-completo.dsl não encontrado em figuras/c4/"; \
		exit 1; \
	fi
	@if ! docker images | grep -q "structurizr-cli"; then \
		echo "$(BLUE)[C4]$(NC) Imagem não encontrada. Construindo..."; \
		$(MAKE) c4-build; \
	fi
	@echo "$(BLUE)[C4]$(NC) Validando arquivo DSL..."
	docker run --rm -v "$(PWD)/figuras/c4:/workspace" structurizr-cli \
		validate -workspace c4-completo.dsl || \
		{ echo "$(YELLOW)[AVISO]$(NC) Validação encontrou problemas, mas continuando..."; }
	@echo "$(BLUE)[C4]$(NC) Exportando diagramas PlantUML..."
	docker run --rm -v "$(PWD)/figuras/c4:/workspace" structurizr-cli \
		export -workspace c4-completo.dsl -format plantuml -output .
	@echo "$(BLUE)[C4]$(NC) Exportando site estático (formato Structurizr nativo)..."
	docker run --rm -v "$(PWD)/figuras/c4:/workspace" structurizr-cli \
		export -workspace c4-completo.dsl -format static -output .
	@echo "$(BLUE)[C4]$(NC) Exportando workspace JSON (formato nativo)..."
	docker run --rm -v "$(PWD)/figuras/c4:/workspace" structurizr-cli \
		export -workspace c4-completo.dsl -format json -output . 2>/dev/null || true
	@if [ -n "$$(find figuras/c4 -name '*.puml' -type f 2>/dev/null)" ]; then \
		echo "$(GREEN)[SUCESSO]$(NC) Arquivos PlantUML gerados!"; \
		if [ -d "figuras/c4/static" ]; then \
			echo "$(GREEN)[SUCESSO]$(NC) Site estático gerado em figuras/c4/static/"; \
			echo "$(BLUE)[INFO]$(NC) Site estático (formato Structurizr nativo):"; \
			echo "$(BLUE)[INFO]$(NC)   - Abra figuras/c4/static/index.html no navegador"; \
			echo "$(BLUE)[INFO]$(NC)   - Clique em cada diagrama e use o botão de exportar (ícone de download)"; \
			echo "$(BLUE)[INFO]$(NC)   - Exporte como PNG ou SVG no formato nativo do Structurizr"; \
		fi; \
		if [ -f "figuras/c4/workspace.json/c4-completo.json" ] || [ -f "figuras/c4/c4-completo.json" ]; then \
			echo "$(GREEN)[SUCESSO]$(NC) Workspace JSON gerado (formato nativo do Structurizr)."; \
		fi; \
		echo "$(BLUE)[C4]$(NC) Convertendo PlantUML para PNG (formato A4)..."; \
		docker run --rm --entrypoint /bin/bash -v "$(PWD)/figuras/c4:/workspace" structurizr-cli \
			-c "cd /workspace && \
				mkdir -p /tmp/png && \
				for file in structurizr-ContextoDoSistema.puml structurizr-ContainersDoSistema.puml structurizr-ComponentesRoteamento.puml; do \
					if [ -f \"/workspace/\$$file\" ]; then \
						sed 's/skinparam ranksep [0-9]*/skinparam ranksep 80/g; s/skinparam nodesep [0-9]*/skinparam nodesep 40/g' \"/workspace/\$$file\" > \"/tmp/png/\$$file\" 2>/dev/null; \
						if ! grep -q 'skinparam ranksep' \"/tmp/png/\$$file\"; then \
							sed -i '/set separator/a skinparam ranksep 80' \"/tmp/png/\$$file\" 2>/dev/null; \
						fi; \
						if ! grep -q 'skinparam nodesep' \"/tmp/png/\$$file\"; then \
							sed -i '/set separator/a skinparam nodesep 40' \"/tmp/png/\$$file\" 2>/dev/null; \
						fi; \
						if [[ \"\$$file\" =~ ContextoDoSistema ]]; then \
							sed -i '/@startuml/a skinparam pageSize A4 portrait' \"/tmp/png/\$$file\" 2>/dev/null; \
						else \
							sed -i '/@startuml/a skinparam pageSize A4 landscape' \"/tmp/png/\$$file\" 2>/dev/null; \
						fi; \
						cd /tmp/png && \
						PLANTUML_LIMIT_SIZE=16384 plantuml -tpng -SDPI=300 \$$file >/dev/null 2>&1 && \
						mv \$${file%.puml}.png /workspace/ 2>/dev/null || true; \
					fi; \
				done && \
				rm -rf /tmp/png"; \
		if [ -n "$$(find figuras/c4 -name '*.png' -type f 2>/dev/null)" ]; then \
			echo "$(GREEN)[SUCESSO]$(NC) Diagramas C4 compilados!"; \
			echo "$(BLUE)[INFO]$(NC) Arquivos gerados em figuras/c4/:"; \
			echo "$(BLUE)[INFO]$(NC) PlantUML:"; \
			find figuras/c4 -name 'structurizr-*.puml' -type f -exec basename {} \; | sed 's/^/  - /'; \
			echo "$(BLUE)[INFO]$(NC) PNG:"; \
			find figuras/c4 -name 'structurizr-*.png' -type f -exec basename {} \; | sed 's/^/  - /'; \
		else \
			echo "$(YELLOW)[AVISO]$(NC) Arquivos PlantUML gerados, mas conversão para PNG falhou."; \
			echo "$(BLUE)[INFO]$(NC) Arquivos PlantUML disponíveis:"; \
			find figuras/c4 -name 'structurizr-*.puml' -type f -exec basename {} \; | sed 's/^/  - /'; \
		fi; \
	else \
		echo "$(YELLOW)[AVISO]$(NC) Nenhum arquivo PlantUML foi gerado. Verifique os logs acima."; \
	fi

# Limpar arquivos gerados pelo Structurizr
c4-clean:
	@echo "$(BLUE)[C4]$(NC) Limpando arquivos gerados pelo Structurizr..."
	@cd figuras/c4 && rm -f *.png *.svg *.html *.json 2>/dev/null || true
	@cd figuras/c4 && rm -rf static css js img 2>/dev/null || true
	@echo "$(GREEN)[SUCESSO]$(NC) Limpeza concluída!"

# Ajuda
help:
	@echo "$(BLUE)[TCC]$(NC) Comandos disponíveis:"
	@echo ""
	@echo "$(GREEN)1. Instalação e Configuração:$(NC)"
	@echo "  make install    - Instalar dependências (LaTeX + Python)"
	@echo ""
	@echo "$(GREEN)2. Conversão:$(NC)"
	@echo "  make convert    - Converter PDFs da pasta referencias para Markdown"
	@echo ""
	@echo "$(GREEN)3. Compilação:$(NC)"
	@echo "  make compile    - Compilar artigo LaTeX para PDF"
	@echo "  make beamer     - Compilar apresentação Beamer"
	@echo ""
	@echo "$(GREEN)4. Formatação e Linting:$(NC)"
	@echo "  make format     - Formatar código Python (black + isort)"
	@echo "  make lint       - Verificar código Python (flake8)"
	@echo ""
	@echo "$(GREEN)5. Utilitários:$(NC)"
	@echo "  make clean      - Limpar arquivos auxiliares"
	@echo "  make zip        - Criar arquivo ZIP do TCC (arquivos essenciais)"
	@echo "  make help       - Mostrar esta ajuda"
	@echo ""
	@echo "$(GREEN)6. Docker (recomendado para macOS):$(NC)"
	@echo "  make docker-build   - Construir imagem Docker"
	@echo "  make docker-compile - Compilar artigo usando Docker (sem instalar LaTeX)"
	@echo "  make docker-beamer - Compilar apresentação Beamer usando Docker"
	@echo "  make docker-clean   - Limpar containers e volumes Docker"
	@echo "  make docker-shell   - Abrir shell interativo no container"
	@echo ""
	@echo "$(GREEN)7. Diagramas C4 (Structurizr):$(NC)"
	@echo "  make c4-build   - Construir imagem Docker Structurizr"
	@echo "  make c4-compile - Compilar arquivo DSL para diagramas PlantUML"
	@echo "  make c4-clean   - Limpar arquivos gerados pelo Structurizr"
	@echo ""
	@echo "$(YELLOW)Fluxo recomendado (sem LaTeX instalado):$(NC)"
	@echo "  1. make docker-compile  # Compila artigo usando Docker"
	@echo "  2. make docker-beamer   # Compila apresentação usando Docker"
	@echo ""
	@echo "$(YELLOW)Fluxo recomendado (com LaTeX instalado):$(NC)"
	@echo "  1. make install         # Configuração inicial"
	@echo "  2. make convert         # Converter referências"
	@echo "  3. make compile         # Compilar artigo"
	@echo ""
	@echo "$(YELLOW)Fluxo para diagramas C4:$(NC)"
	@echo "  1. make c4-compile      # Compila diagramas DSL"
	@echo ""
	@echo "$(YELLOW)Sistema detectado: $(OS)$(NC)"
	@echo "  Gerenciador de pacotes: $(PACKAGE_MANAGER)"