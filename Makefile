.PHONY: setup install run clean reset hard-reset sync-locations sync-locations-prune sync-locations-check help validate-config invite-api invite-staging staging-up staging-down staging-logs staging-restart staging-rebuild staging-seed staging-seed-prune staging-seed-check staging-invite staging-reset staging-notify frontend-install frontend-dev frontend-build dev-full notify docker-build docker-push docker-release deploy-staging scale-staging infra-init infra-plan infra-apply infra-destroy

VENV := venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
DOCKER_COMPOSE_STAGING := docker compose -f docker-compose.staging.yml
FRONTEND := frontend
DOPPLER_PROJECT ?= staging-deployment
DOPPLER_CONFIG ?= stg

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

invite:  ## Generate a new invite code (local DB)
	$(PYTHON) scripts/generate_invite.py

invite-staging:  ## Generate invite via API using Doppler (staging only)
	doppler run --project $(DOPPLER_PROJECT) --config $(DOPPLER_CONFIG) -- $(PYTHON) scripts/generate_invite_api.py

invite-api: invite-staging  ## Alias for invite-staging (staging only)

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

# Tag derivation: extract version from branch name (release/v0.5.0 -> v0.5.0)
GIT_BRANCH := $(shell git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
DEFAULT_TAG := $(shell echo $(GIT_BRANCH) | sed 's|.*/||')
TAG ?= $(DEFAULT_TAG)

# Deployment environment file
DEPLOY_ENV := infra/.env.deploy

docker-build:  ## Build Docker image for amd64 (usage: make docker-build TAG=v0.5.0)
	docker buildx build --platform linux/amd64 -t $(IMAGE_NAME):$(TAG) --load .

docker-push:  ## Push Docker image (usage: make docker-push TAG=v0.5.0)
	docker push $(IMAGE_NAME):$(TAG)

docker-release:  ## Build and push Docker image for amd64 (usage: make docker-release TAG=v0.5.0)
	docker buildx build --platform linux/amd64 -t $(IMAGE_NAME):$(TAG) --push .

deploy-staging:  ## Build, push, and deploy to staging (usage: make deploy-staging [TAG=v0.5.0])
	@if [ ! -f $(DEPLOY_ENV) ]; then \
		echo "Error: $(DEPLOY_ENV) not found."; \
		echo "Copy infra/.env.deploy.example to $(DEPLOY_ENV) and fill in values."; \
		exit 1; \
	fi
	@echo "==> Building and pushing image: $(IMAGE_NAME):$(TAG)"
	docker buildx build --platform linux/amd64 -t $(IMAGE_NAME):$(TAG) --push .
	@echo ""
	@echo "==> Planning infrastructure changes..."
	@set -a && . ./$(DEPLOY_ENV) && set +a && \
		cd infra && \
		TF_VAR_do_token=$$DO_TOKEN \
		TF_VAR_staging_app_image=$(IMAGE_NAME):$(TAG) \
		tofu plan $(if $(NODES),-var="staging_node_count=$(NODES)",)
	@echo ""
	@read -p "Apply these changes? [y/N] " confirm && \
		[ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ] || { echo "Aborted."; exit 1; }
	@set -a && . ./$(DEPLOY_ENV) && set +a && \
		cd infra && \
		TF_VAR_do_token=$$DO_TOKEN \
		TF_VAR_staging_app_image=$(IMAGE_NAME):$(TAG) \
		tofu apply -auto-approve $(if $(NODES),-var="staging_node_count=$(NODES)",)
	@echo ""
	@echo "==> Deployment complete: $(IMAGE_NAME):$(TAG)"

scale-staging:  ## Scale staging nodes without rebuilding (usage: make scale-staging NODES=2)
	@if [ ! -f $(DEPLOY_ENV) ]; then \
		echo "Error: $(DEPLOY_ENV) not found."; \
		echo "Copy infra/.env.deploy.example to $(DEPLOY_ENV) and fill in values."; \
		exit 1; \
	fi
	@if [ -z "$(NODES)" ]; then \
		echo "Error: NODES is required (e.g., make scale-staging NODES=2)"; \
		exit 1; \
	fi
	@echo "==> Getting current app image from state..."
	@set -a && . ./$(DEPLOY_ENV) && set +a && \
		CURRENT_IMAGE=$$(cd infra && TF_VAR_do_token=$$DO_TOKEN tofu output -raw staging_app_image 2>/dev/null) && \
		if [ -z "$$CURRENT_IMAGE" ]; then \
			echo "Error: Could not get current image from state. Run deploy-staging first."; \
			exit 1; \
		fi && \
		echo "Current image: $$CURRENT_IMAGE" && \
		echo "" && \
		echo "==> Planning scale to $(NODES) node(s)..." && \
		cd infra && \
		TF_VAR_do_token=$$DO_TOKEN \
		TF_VAR_staging_app_image=$$CURRENT_IMAGE \
		tofu plan -var="staging_node_count=$(NODES)" && \
		echo "" && \
		read -p "Apply these changes? [y/N] " confirm && \
		[ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ] || { echo "Aborted."; exit 1; } && \
		TF_VAR_do_token=$$DO_TOKEN \
		TF_VAR_staging_app_image=$$CURRENT_IMAGE \
		tofu apply -auto-approve -var="staging_node_count=$(NODES)" && \
		echo "" && \
		echo "==> Scaled to $(NODES) node(s)"

# --- Infrastructure (OpenTofu) ---

infra-init:  ## Initialize OpenTofu (auto-sources .env.deploy if present)
	@if [ -f $(DEPLOY_ENV) ]; then set -a && . ./$(DEPLOY_ENV) && set +a; fi && \
		cd infra && TF_VAR_do_token=$${DO_TOKEN:-$(DO_TOKEN)} tofu init

infra-plan:  ## Plan infrastructure changes (auto-sources .env.deploy if present)
	@if [ -f $(DEPLOY_ENV) ]; then set -a && . ./$(DEPLOY_ENV) && set +a; fi && \
		cd infra && \
		CURRENT_IMAGE=$$(TF_VAR_do_token=$${DO_TOKEN:-$(DO_TOKEN)} tofu output -raw staging_app_image 2>/dev/null) && \
		if [ -z "$$CURRENT_IMAGE" ]; then \
			echo "Error: Could not get current image from state. Run deploy-staging first."; \
			exit 1; \
		fi && \
		TF_VAR_do_token=$${DO_TOKEN:-$(DO_TOKEN)} \
		TF_VAR_staging_app_image=$$CURRENT_IMAGE \
		tofu plan $(if $(NODES),-var="staging_node_count=$(NODES)",)

infra-apply:  ## Apply infrastructure changes (auto-sources .env.deploy if present)
	@if [ -f $(DEPLOY_ENV) ]; then set -a && . ./$(DEPLOY_ENV) && set +a; fi && \
		cd infra && \
		CURRENT_IMAGE=$$(TF_VAR_do_token=$${DO_TOKEN:-$(DO_TOKEN)} tofu output -raw staging_app_image 2>/dev/null) && \
		if [ -z "$$CURRENT_IMAGE" ]; then \
			echo "Error: Could not get current image from state. Run deploy-staging first."; \
			exit 1; \
		fi && \
		TF_VAR_do_token=$${DO_TOKEN:-$(DO_TOKEN)} \
		TF_VAR_staging_app_image=$$CURRENT_IMAGE \
		tofu apply $(if $(NODES),-var="staging_node_count=$(NODES)",)

infra-destroy:  ## Destroy all infrastructure (auto-sources .env.deploy if present)
	@if [ -f $(DEPLOY_ENV) ]; then set -a && . ./$(DEPLOY_ENV) && set +a; fi && \
		cd infra && TF_VAR_do_token=$${DO_TOKEN:-$(DO_TOKEN)} tofu destroy
