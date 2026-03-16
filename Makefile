.DEFAULT_GOAL := help

# ── OS / shell detection ──────────────────────────────────────────────────────
ifeq ($(OS),Windows_NT)
    # Always use native Windows commands to avoid WSL/Git-Bash path translation issues.
    SETUP_CMD = scripts\setup.bat
    START_CMD  = scripts\start.bat
    PYTHON_CMD = .venv\Scripts\python.exe
    PYTHON_CMD_SUBDIR = ..\.venv\Scripts\python.exe
else
    SETUP_CMD = bash scripts/setup.sh
    START_CMD  = bash scripts/start.sh
    PYTHON_CMD = .venv/bin/python
    PYTHON_CMD_SUBDIR = ../.venv/bin/python
endif
PIP_CMD = "$(PYTHON_CMD)" -m pip

# ── Setup ─────────────────────────────────────────────────────────────────────
setup: ## Full first-time setup: download docs, start DB, embed + install all deps
	$(SETUP_CMD)
	$(PIP_CMD) install -r backend/requirements-dev.txt
	$(PIP_CMD) install -r benchmark/requirements.txt

# ── Development ───────────────────────────────────────────────────────────────
start: ## Start both frontend and backend
	$(START_CMD)

backend: ## Start FastAPI backend only (with hot reload)
	cd backend && uvicorn main:app --reload --port 8000

frontend: ## Start Next.js frontend only
	cd frontend && npm run dev

# ── Docker ────────────────────────────────────────────────────────────────────
db-up: ## Start PostgreSQL + pgvector via Docker
	docker compose -f backend/docker-compose.yml up -d

db-down: ## Stop PostgreSQL container
	docker compose -f backend/docker-compose.yml down

db-logs: ## Tail PostgreSQL container logs
	docker compose -f backend/docker-compose.yml logs -f

# ── Testing ───────────────────────────────────────────────────────────────────
test: ## Install dev deps and run all backend unit tests
	$(PIP_CMD) install -q -r backend/requirements-dev.txt
	cd backend && "$(PYTHON_CMD_SUBDIR)" -m pytest tests/ -v

test-quick: ## Install dev deps and run tests, stop on first failure
	$(PIP_CMD) install -q -r backend/requirements-dev.txt
	cd backend && "$(PYTHON_CMD_SUBDIR)" -m pytest tests/ -x -v

# ── Benchmarking ──────────────────────────────────────────────────────────────
dataset: ## Generate technical Q&A evaluation dataset (uses OpenAI API)
	$(PIP_CMD) install -q -r benchmark/requirements.txt
	cd benchmark && "$(PYTHON_CMD_SUBDIR)" generate_dataset.py

dataset-userstyle: ## Generate user-style Q&A evaluation dataset (uses OpenAI API)
	$(PIP_CMD) install -q -r benchmark/requirements.txt
	cd benchmark && "$(PYTHON_CMD_SUBDIR)" generate_dataset.py --style userstyle

eval-retrieval: ## Run retrieval-only evaluation on technical dataset (fast, free)
	$(PIP_CMD) install -q -r benchmark/requirements.txt
	cd benchmark && "$(PYTHON_CMD_SUBDIR)" evaluate.py --retrieval-only

eval-retrieval-userstyle: ## Run retrieval-only evaluation on user-style dataset (fast, free)
	$(PIP_CMD) install -q -r benchmark/requirements.txt
	cd benchmark && "$(PYTHON_CMD_SUBDIR)" evaluate.py --retrieval-only --dataset eval_dataset_userstyle.json

eval-full: ## Run full evaluation on technical dataset (retrieval + generation, uses OpenAI API)
	$(PIP_CMD) install -q -r benchmark/requirements.txt
	cd benchmark && "$(PYTHON_CMD_SUBDIR)" evaluate.py

eval-full-userstyle: ## Run full evaluation on user-style dataset (uses OpenAI API)
	$(PIP_CMD) install -q -r benchmark/requirements.txt
	cd benchmark && "$(PYTHON_CMD_SUBDIR)" evaluate.py --dataset eval_dataset_userstyle.json

# ── Utilities ─────────────────────────────────────────────────────────────────
health: ## Check backend health endpoint
	curl -s http://localhost:8000/health | "$(PYTHON_CMD)" -m json.tool

lint: ## Run ruff linter on backend code
	cd backend && "$(PYTHON_CMD_SUBDIR)" -m ruff check .

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

.PHONY: setup start backend frontend db-up db-down db-logs test test-quick \
        dataset dataset-userstyle \
        eval-retrieval eval-retrieval-userstyle eval-full eval-full-userstyle \
        health lint help
