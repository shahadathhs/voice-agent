.DEFAULT_GOAL := help

BACKEND_DIR := backend
WEB_DIR := web

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install: install-backend install-web ## Install all dependencies

.PHONY: install-backend
install-backend: ## Install backend dependencies (uv)
	cd $(BACKEND_DIR) && uv sync

.PHONY: install-web
install-web: ## Install web dependencies (npm)
	cd $(WEB_DIR) && npm install

.PHONY: dev-backend
dev-backend: ## Run backend dev server (port 8000)
	cd $(BACKEND_DIR) && uv run uvicorn app.main:app --reload

.PHONY: dev-web
dev-web: ## Run web dev server (port 3000)
	cd $(WEB_DIR) && npm run dev

.PHONY: dev run
dev: ## Run backend + web dev servers together
	$(MAKE) -j2 dev-backend dev-web

run: dev ## Alias for dev

.PHONY: up
up: ## Start full stack with Docker Compose
	docker compose up -d --build

.PHONY: down
down: ## Stop Docker Compose stack
	docker compose down

.PHONY: logs
logs: ## Tail Docker Compose logs
	docker compose logs -f

.PHONY: lint
lint: lint-backend lint-web ## Lint everything

.PHONY: lint-backend
lint-backend: ## Lint backend (ruff)
	cd $(BACKEND_DIR) && uv run ruff check . && uv run ruff format --check .

.PHONY: lint-web
lint-web: ## Lint web (eslint)
	cd $(WEB_DIR) && npm run lint

.PHONY: format
format: ## Format backend code (ruff)
	cd $(BACKEND_DIR) && uv run ruff check --fix . && uv run ruff format .

.PHONY: test
test: ## Run backend tests
	cd $(BACKEND_DIR) && uv run pytest

.PHONY: build
build: build-web ## Build everything
	docker compose build

.PHONY: build-web
build-web: ## Build web production bundle
	cd $(WEB_DIR) && npm run build

.PHONY: clean
clean: ## Remove build artifacts and caches
	rm -rf $(BACKEND_DIR)/.venv $(BACKEND_DIR)/.pytest_cache $(BACKEND_DIR)/.ruff_cache
	rm -rf $(WEB_DIR)/.next $(WEB_DIR)/node_modules
	find . -type d -name __pycache__ -exec rm -rf {} +
