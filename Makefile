.PHONY: setup install run clean reset hard-reset sync-locations sync-locations-prune sync-locations-check help validate-config staging-up staging-down staging-logs staging-restart staging-rebuild staging-seed staging-seed-prune staging-seed-check staging-invite staging-reset staging-notify frontend-install frontend-dev frontend-build dev-full notify docker-build docker-push docker-release infra-init infra-plan infra-apply infra-destroy

VENV := venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
DOCKER_COMPOSE_STAGING := docker compose -f docker-compose.staging.yml
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
	$(PYTHON) scripts/sync_locations.py
	DEV_AUTH_BYPASS=true $(PYTHON) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

clean:  ## Remove venv and cache files
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

reset:  ## Soft reset: clear game state but keep locations
	$(PYTHON) scripts/reset_game_state.py

hard-reset:  ## Hard reset: delete DB and re-seed locations
	rm -f chat.db
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

validate-config:  ## Validate config (set DB_CHECK=true for DB connectivity)
	$(PYTHON) scripts/validate_config.py $(if $(DB_CHECK),--db-check,)

invite:  ## Generate a new invite code
	$(PYTHON) scripts/generate_invite.py

notify:  ## Create a notification (usage: make notify TITLE="title" MSG="message")
	$(PYTHON) scripts/create_notification.py "$(TITLE)" "$(MSG)" $(if $(TTL),--ttl $(TTL),) $(if $(TYPE),--type $(TYPE),)

dev: setup run  ## Setup and run local dev in one command

# --- Staging (Docker Compose) ---

staging-up:  ## Start staging containers detached
	$(DOCKER_COMPOSE_STAGING) up -d

staging-down:  ## Stop and remove staging containers
	$(DOCKER_COMPOSE_STAGING) down

staging-logs:  ## Follow staging logs
	$(DOCKER_COMPOSE_STAGING) logs -f

staging-restart:  ## Restart staging containers
	$(DOCKER_COMPOSE_STAGING) restart

staging-rebuild:  ## Pull latest image and restart staging containers
	$(DOCKER_COMPOSE_STAGING) pull
	$(DOCKER_COMPOSE_STAGING) up -d

staging-seed:  ## Seed/Update staging database locations
	$(DOCKER_COMPOSE_STAGING) exec -T app python scripts/sync_locations.py

staging-seed-prune:  ## Seed/Update staging database locations and prune missing (use for staging/dev only)
	$(DOCKER_COMPOSE_STAGING) exec -T app python scripts/sync_locations.py --prune

staging-seed-check:  ## Check staging DB matches fixtures (no writes; expects exact match)
	$(DOCKER_COMPOSE_STAGING) exec -T app python scripts/sync_locations.py --dry-run --prune

staging-invite:  ## Generate invite code in staging
	$(DOCKER_COMPOSE_STAGING) exec app python scripts/generate_invite.py

staging-reset:  ## Reset game sessions in staging (keeps users)
	$(DOCKER_COMPOSE_STAGING) exec app python scripts/reset_game_state.py

staging-notify:  ## Create notification in staging (usage: make staging-notify TITLE="title" MSG="message")
	$(DOCKER_COMPOSE_STAGING) exec app python scripts/create_notification.py "$(TITLE)" "$(MSG)" $(if $(TTL),--ttl $(TTL),) $(if $(TYPE),--type $(TYPE),)

# --- Frontend (Vite) ---

frontend-install:  ## Install frontend dependencies
	cd $(FRONTEND) && npm ci

frontend-dev:  ## Start Vite dev server (port 5173)
	cd $(FRONTEND) && npm run dev

frontend-build:  ## Build frontend for staging/prod-style
	cd $(FRONTEND) && npm run build

dev-full:  ## Start backend + frontend dev servers (access at localhost:5173)
	$(PYTHON) scripts/sync_locations.py
	@echo "Starting backend on :8000 and frontend on :5173..."
	@echo "Access the app at http://localhost:5173"
	@DEV_AUTH_BYPASS=true $(PYTHON) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 & \
	cd $(FRONTEND) && npm run dev

# --- Docker Image ---

REGISTRY ?= registry.digitalocean.com
REPO ?= dungeon-minus-one
IMAGE_NAME = $(REGISTRY)/$(REPO)/dungeon-minus-one
TAG ?= latest

docker-build:  ## Build Docker image for amd64 (usage: make docker-build TAG=v0.5.0)
	docker buildx build --platform linux/amd64 -t $(IMAGE_NAME):$(TAG) --load .

docker-push:  ## Push Docker image (usage: make docker-push TAG=v0.5.0)
	docker push $(IMAGE_NAME):$(TAG)

docker-release:  ## Build and push Docker image for amd64 (usage: make docker-release TAG=v0.5.0)
	docker buildx build --platform linux/amd64 -t $(IMAGE_NAME):$(TAG) --push .

# --- Infrastructure (OpenTofu) ---

infra-init:  ## Initialize OpenTofu (usage: make infra-init DO_TOKEN=xxx)
	cd infra && TF_VAR_do_token=$(DO_TOKEN) tofu init

infra-plan:  ## Plan infrastructure changes (usage: make infra-plan DO_TOKEN=xxx)
	cd infra && TF_VAR_do_token=$(DO_TOKEN) tofu plan $(if $(NODES),-var="staging_node_count=$(NODES)",)

infra-apply:  ## Apply infrastructure changes (usage: make infra-apply DO_TOKEN=xxx)
	cd infra && TF_VAR_do_token=$(DO_TOKEN) tofu apply $(if $(NODES),-var="staging_node_count=$(NODES)",)

infra-destroy:  ## Destroy all infrastructure (usage: make infra-destroy DO_TOKEN=xxx)
	cd infra && TF_VAR_do_token=$(DO_TOKEN) tofu destroy
