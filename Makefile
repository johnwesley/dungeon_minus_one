.PHONY: setup install run clean reset hard-reset sync-locations sync-locations-prune sync-locations-check help validate-config invite auth-reset frontend-install frontend-dev frontend-build dev-full notify test

VENV := venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
FRONTEND := frontend

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: $(VENV)/bin/activate  ## Create venv and install all dependencies
	@echo "Setup complete. Run 'make run' to start the server."
	@echo "Don't forget to copy .env.example to .env and add your ANTHROPIC_API_KEY"

$(VENV)/bin/activate: requirements.txt
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	touch $(VENV)/bin/activate

install:  ## Install dependencies (requires existing venv)
	$(PIP) install -r requirements.txt

db-up:  ## Start local Postgres via Docker
	docker-compose up -d db

db-down:  ## Stop local Postgres
	docker-compose down

db-migrate:  ## Run Alembic migrations against local Postgres
	DATABASE_URL=postgresql+asyncpg://dungeon:password@localhost:5432/dungeon $(PYTHON) -m alembic upgrade head

run:  ## Start the local development server (FastAPI only)
	@echo "Note: If using local Postgres, ensure 'make db-up' is running."
	$(PYTHON) scripts/compile_skills.py
	$(PYTHON) scripts/sync_locations.py
	$(PYTHON) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

clean:  ## Remove venv and cache files
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

reset:  ## Soft reset: clear game state but keep locations
	$(PYTHON) scripts/reset_game_state.py

hard-reset:  ## Hard reset: drop/recreate tables and re-seed locations
	$(PYTHON) scripts/reset_database.py --force
	$(PYTHON) scripts/sync_locations.py --prune
	@echo "Database reset and re-seeded."

sync-locations:  ## Sync static location fixtures into DB (non-destructive)
	$(PYTHON) scripts/sync_locations.py

sync-locations-prune:  ## Sync + prune static location fixtures (deletes missing locations/exits; repairs current_location)
	$(PYTHON) scripts/sync_locations.py --prune

sync-locations-check:  ## Check DB matches fixtures (no writes; expects exact match)
	$(PYTHON) scripts/sync_locations.py --dry-run --prune

verify-movement:  ## Verify narrator tool usage for movement
	$(PYTHON) scripts/verify_movement.py

test:  ## Run local test pipeline (pytest + walkthrough)
	$(PYTHON) -m pytest app/tests
	$(MAKE) verify-movement

validate-config:  ## Validate config (set DB_CHECK=true for DB connectivity)
	$(PYTHON) scripts/validate_config.py $(if $(DB_CHECK),--db-check,)

invite:  ## Generate a new invite token (usage: make invite EMAIL="user@example.com")
	$(PYTHON) scripts/generate_invite.py $(EMAIL)

auth-reset:  ## Reset auth-related tables (dangerous; add FORCE=true)
	$(PYTHON) scripts/reset_auth.py $(if $(FORCE),--force,)

create-admin:  ## Create a new admin user (usage: make create-admin USER=admin PASS=pass EMAIL=admin@example.com)
	$(PYTHON) scripts/create_admin.py $(USER) $(PASS) $(if $(EMAIL),--email $(EMAIL),)

notify:  ## Create a notification (usage: make notify TITLE="title" MSG="message")
	$(PYTHON) scripts/create_notification.py "$(TITLE)" "$(MSG)" $(if $(TTL),--ttl $(TTL),) $(if $(TYPE),--type $(TYPE),)

dev: setup run  ## Setup and run local dev in one command

# --- Frontend (Vite) ---

frontend-install:  ## Install frontend dependencies
	cd $(FRONTEND) && npm ci

frontend-dev:  ## Start Vite dev server (port 5173)
	cd $(FRONTEND) && npm run dev

frontend-build:  ## Build frontend for production
	cd $(FRONTEND) && npm run build

dev-full:  ## Start backend + frontend dev servers (access at localhost:5173)
	@./scripts/dev_full.sh $(PYTHON) $(FRONTEND)
