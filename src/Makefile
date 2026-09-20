.PHONY: help build up up-detached down logs logs-file logs-stop clean clean-logs

LOGS_DIR := logs
TIMESTAMP := $(shell date +%Y%m%d_%H%M%S)
LOG_FILE := $(LOGS_DIR)/docker-compose_$(TIMESTAMP).log

help:
	@echo "Comandos disponiveis:"
	@echo ""
	@echo "  make build          - Constroi as imagens Docker"
	@echo "  make up             - Inicia os servicos (salva logs em logs/)"
	@echo "  make up-detached    - Inicia os servicos em background"
	@echo "  make down           - Para os servicos"
	@echo "  make logs           - Mostra os logs em tempo real"
	@echo "  make logs-file      - Mostra o ultimo arquivo de log salvo"
	@echo "  make logs-stop      - Para a captura de logs em background"
	@echo "  make clean          - Remove containers e volumes"
	@echo "  make clean-logs     - Remove arquivos de log antigos"

build:
	docker compose build

build-no-cache:
	docker compose build --no-cache

up:
	@mkdir -p $(LOGS_DIR)
	@echo "Iniciando servicos e salvando logs em $(LOG_FILE)..."
	@docker compose up 2>&1 | tee $(LOG_FILE)

up-detached:
	@mkdir -p $(LOGS_DIR)
	@echo "Iniciando servicos em background..."
	@docker compose up -d
	@sleep 2
	@docker compose logs --tail=100 > $(LOG_FILE) 2>&1
	@(docker compose logs -f >> $(LOG_FILE) 2>&1 &) && echo $$! > $(LOGS_DIR)/.log_pid
	@echo "Servicos iniciados. Logs em $(LOG_FILE)"

down:
	@$(MAKE) logs-stop 2>/dev/null || true
	docker compose down

logs:
	docker compose logs -f

logs-file:
	@if [ -d $(LOGS_DIR) ] && [ -n "$$(ls -A $(LOGS_DIR)/docker-compose_*.log 2>/dev/null)" ]; then \
		LATEST_LOG=$$(ls -t $(LOGS_DIR)/docker-compose_*.log 2>/dev/null | head -1); \
		echo "Mostrando ultimo log: $$LATEST_LOG"; \
		tail -100 $$LATEST_LOG; \
	else \
		echo "Nenhum arquivo de log encontrado"; \
	fi

logs-stop:
	@if [ -f $(LOGS_DIR)/.log_pid ]; then \
		PID=$$(cat $(LOGS_DIR)/.log_pid); \
		kill $$PID 2>/dev/null || true; \
		rm -f $(LOGS_DIR)/.log_pid; \
	else \
		pkill -f 'docker compose logs' 2>/dev/null || true; \
	fi

clean:
	docker compose down -v
	docker system prune -f

clean-logs:
	@rm -f $(LOGS_DIR)/docker-compose_*.log $(LOGS_DIR)/.log_pid
