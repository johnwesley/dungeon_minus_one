.PHONY: setup install run clean reset hard-reset help prod-up prod-down prod-logs prod-restart prod-rebuild prod-invite frontend-install frontend-dev frontend-build dev-full

VENV := venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
DOCKER_COMPOSE_PROD := docker compose -f docker-compose.prod.yml
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

run:  ## Start the local development server (FastAPI only)
	DEV_AUTH_BYPASS=true $(PYTHON) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

clean:  ## Remove venv and cache files
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

reset:  ## Soft reset: clear game state but keep locations
	$(PYTHON) scripts/reset_game_state.py

hard-reset:  ## Hard reset: delete DB and re-seed locations
	rm -f chat.db
	$(PYTHON) scripts/seed_locations.py
	@echo "Database reset and re-seeded."

invite:  ## Generate a new invite code
	$(PYTHON) scripts/generate_invite.py

dev: setup run  ## Setup and run local dev in one command

# --- Production / Staging (Docker Compose) ---

prod-up:  ## Start production containers detached
	$(DOCKER_COMPOSE_PROD) up -d

prod-down:  ## Stop and remove production containers
	$(DOCKER_COMPOSE_PROD) down

prod-logs:  ## Follow production logs
	$(DOCKER_COMPOSE_PROD) logs -f

prod-restart:  ## Restart production containers
	$(DOCKER_COMPOSE_PROD) restart

prod-rebuild:  ## Rebuild and restart production containers
	$(DOCKER_COMPOSE_PROD) up -d --build

prod-invite:  ## Generate invite code in production
	$(DOCKER_COMPOSE_PROD) exec app python scripts/generate_invite.py

# --- Frontend (Vite) ---

frontend-install:  ## Install frontend dependencies
	cd $(FRONTEND) && npm ci

frontend-dev:  ## Start Vite dev server (port 5173)
	cd $(FRONTEND) && npm run dev

frontend-build:  ## Build frontend for production
	cd $(FRONTEND) && npm run build

dev-full:  ## Start backend + frontend dev servers (access at localhost:5173)
	@echo "Starting backend on :8000 and frontend on :5173..."
	@echo "Access the app at http://localhost:5173"
	@DEV_AUTH_BYPASS=true $(PYTHON) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 & \
	cd $(FRONTEND) && npm run dev
