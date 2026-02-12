.PHONY: setup install run clean reset hard-reset sync-locations sync-locations-prune sync-locations-check help validate-config invite auth-reset frontend-install frontend-dev frontend-build dev-full notify docker-build docker-push docker-release assets-publish release-staging release-prod infra-init infra-plan infra-apply infra-destroy k8s-kubeconfig k8s-setup-staging k8s-setup-prod k8s-deploy k8s-status k8s-logs k8s-restart k8s-shell k8s-db-migrate k8s-seed k8s-seed-prune k8s-invite k8s-reset k8s-auth-reset k8s-create-admin k8s-notify k8s-dns-upsert k8s-dns-delete k8s-teardown-staging test

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

frontend-build:  ## Build frontend for staging/prod-style
	cd $(FRONTEND) && ASSET_BASE_URL="$(ASSET_BASE_URL)" npm run build

dev-full:  ## Start backend + frontend dev servers (access at localhost:5173)
	@./scripts/dev_full.sh $(PYTHON) $(FRONTEND)

# --- Docker Image ---

REGISTRY ?= registry.digitalocean.com
REPO ?= dungeon-minus-one
IMAGE_NAME = $(REGISTRY)/$(REPO)/dungeon-minus-one

# Tag derivation: extract version from branch name (release/v0.5.0 -> v0.5.0)
GIT_BRANCH := $(shell git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
DEFAULT_TAG := $(shell echo $(GIT_BRANCH) | sed 's|.*/||')
TAG ?= $(DEFAULT_TAG)

# --- Frontend Assets (Spaces) ---

ASSET_REGION ?= nyc3
ASSET_SPACE ?= dungeon-minus-one-assets
ASSET_ENV ?= staging
ASSET_PREFIX ?= $(ASSET_ENV)/$(TAG)
ASSET_CDN_DOMAIN ?=
ASSET_BASE_URL ?= $(if $(ASSET_CDN_DOMAIN),https://$(ASSET_CDN_DOMAIN)/$(ASSET_PREFIX)/,)
ASSET_CACHE_CONTROL ?= public, max-age=31536000, immutable

# Default CDN hostnames (override via env or .env.deploy)
ASSET_CDN_DOMAIN_STAGING ?= assets-staging.dungeonminusone.com
ASSET_CDN_DOMAIN_PROD ?= assets.dungeonminusone.com

# Deployment environment file
DEPLOY_ENV := infra/.env.deploy

docker-build:  ## Build Docker image for amd64 (usage: make docker-build TAG=v0.5.0)
	docker buildx build --platform linux/amd64 -t $(IMAGE_NAME):$(TAG) --build-arg ASSET_BASE_URL=$(ASSET_BASE_URL) --load .

docker-push:  ## Push Docker image (usage: make docker-push TAG=v0.5.0)
	docker push $(IMAGE_NAME):$(TAG)

docker-release:  ## Build and push Docker image for amd64 (usage: make docker-release TAG=v0.5.0)
	@if [ -n "$(ASSET_BASE_URL)" ]; then $(MAKE) assets-publish TAG=$(TAG) ASSET_BASE_URL="$(ASSET_BASE_URL)"; fi
	docker buildx build --platform linux/amd64 -t $(IMAGE_NAME):$(TAG) --build-arg ASSET_BASE_URL=$(ASSET_BASE_URL) --no-cache --push .

# --- Asset Publishing (Spaces) ---

assets-publish:  ## Build and upload frontend assets to Spaces
	@set -a; [ -f $(DEPLOY_ENV) ] && . ./$(DEPLOY_ENV); set +a; \
	if [ -z "$(ASSET_BASE_URL)" ]; then echo "ASSET_BASE_URL is required (set ASSET_CDN_DOMAIN or ASSET_BASE_URL)."; exit 1; fi; \
	if [ -z "$$SPACES_ACCESS_KEY" ] && [ -z "$$AWS_ACCESS_KEY_ID" ]; then echo "SPACES_ACCESS_KEY or AWS_ACCESS_KEY_ID must be set."; exit 1; fi; \
	if [ -z "$$SPACES_SECRET_KEY" ] && [ -z "$$AWS_SECRET_ACCESS_KEY" ]; then echo "SPACES_SECRET_KEY or AWS_SECRET_ACCESS_KEY must be set."; exit 1; fi; \
	$(MAKE) frontend-build ASSET_BASE_URL="$(ASSET_BASE_URL)"; \
	$(PYTHON) scripts/publish_frontend_assets.py --dist $(FRONTEND)/dist --space $(ASSET_SPACE) --region $(ASSET_REGION) --prefix $(ASSET_PREFIX) --cache-control "$(ASSET_CACHE_CONTROL)"

# --- One-command release helpers ---

release-staging:  ## Build+publish assets, push image, and deploy to staging
	@set -a; [ -f $(DEPLOY_ENV) ] && . ./$(DEPLOY_ENV); set +a; \
	ASSET_ENV=staging \
	ASSET_CDN_DOMAIN=$${ASSET_CDN_DOMAIN:-$${ASSET_CDN_DOMAIN_STAGING:-$(ASSET_CDN_DOMAIN_STAGING)}} \
	$(MAKE) docker-release TAG=$(TAG) ASSET_ENV=staging ASSET_CDN_DOMAIN=$${ASSET_CDN_DOMAIN:-$${ASSET_CDN_DOMAIN_STAGING:-$(ASSET_CDN_DOMAIN_STAGING)}}; \
	$(MAKE) k8s-deploy K8S_ENV=staging TAG=$(TAG)

release-prod:  ## Build+publish assets, push image, and deploy to production
	@set -a; [ -f $(DEPLOY_ENV) ] && . ./$(DEPLOY_ENV); set +a; \
	ASSET_ENV=prod \
	ASSET_CDN_DOMAIN=$${ASSET_CDN_DOMAIN:-$${ASSET_CDN_DOMAIN_PROD:-$(ASSET_CDN_DOMAIN_PROD)}} \
	$(MAKE) docker-release TAG=$(TAG) ASSET_ENV=prod ASSET_CDN_DOMAIN=$${ASSET_CDN_DOMAIN:-$${ASSET_CDN_DOMAIN_PROD:-$(ASSET_CDN_DOMAIN_PROD)}}; \
	$(MAKE) k8s-deploy K8S_ENV=prod TAG=$(TAG)

# --- Infrastructure (OpenTofu) ---

infra-init:  ## Initialize OpenTofu (auto-sources .env.deploy if present)
	@if [ -f $(DEPLOY_ENV) ]; then set -a && . ./$(DEPLOY_ENV) && set +a; fi && \
		cd infra && \
		TF_VAR_do_token=$${DO_TOKEN:-$(DO_TOKEN)} \
		TF_VAR_spaces_access_id=$${SPACES_ACCESS_KEY:-$${SPACES_ACCESS_ID:-$${AWS_ACCESS_KEY_ID}}} \
		TF_VAR_spaces_secret_key=$${SPACES_SECRET_KEY:-$${AWS_SECRET_ACCESS_KEY}} \
		tofu init

infra-plan:  ## Plan infrastructure changes
	@if [ ! -f $(DEPLOY_ENV) ]; then \
		echo "Error: $(DEPLOY_ENV) not found."; \
		exit 1; \
	fi
	@set -a && . ./$(DEPLOY_ENV) && set +a && \
		cd infra && \
		TF_VAR_do_token=$$DO_TOKEN \
		TF_VAR_spaces_access_id=$${SPACES_ACCESS_KEY:-$${SPACES_ACCESS_ID:-$${AWS_ACCESS_KEY_ID}}} \
		TF_VAR_spaces_secret_key=$${SPACES_SECRET_KEY:-$${AWS_SECRET_ACCESS_KEY}} \
		tofu plan

infra-apply:  ## Apply infrastructure changes
	@if [ ! -f $(DEPLOY_ENV) ]; then \
		echo "Error: $(DEPLOY_ENV) not found."; \
		exit 1; \
	fi
	@set -a && . ./$(DEPLOY_ENV) && set +a && \
		cd infra && \
		TF_VAR_do_token=$$DO_TOKEN \
		TF_VAR_spaces_access_id=$${SPACES_ACCESS_KEY:-$${SPACES_ACCESS_ID:-$${AWS_ACCESS_KEY_ID}}} \
		TF_VAR_spaces_secret_key=$${SPACES_SECRET_KEY:-$${AWS_SECRET_ACCESS_KEY}} \
		tofu apply

infra-destroy:  ## Destroy all infrastructure (DANGEROUS)
	@if [ ! -f $(DEPLOY_ENV) ]; then \
		echo "Error: $(DEPLOY_ENV) not found."; \
		exit 1; \
	fi
	@set -a && . ./$(DEPLOY_ENV) && set +a && \
		cd infra && \
		TF_VAR_do_token=$$DO_TOKEN \
		TF_VAR_spaces_access_id=$${SPACES_ACCESS_KEY:-$${SPACES_ACCESS_ID:-$${AWS_ACCESS_KEY_ID}}} \
		TF_VAR_spaces_secret_key=$${SPACES_SECRET_KEY:-$${AWS_SECRET_ACCESS_KEY}} \
		tofu destroy

# --- Kubernetes (DOKS) ---

# Environment selection: staging (default) or prod
K8S_ENV ?= staging
K8S_NAMESPACE := $(if $(filter prod,$(K8S_ENV)),prod-dungeon,staging-dungeon)
K8S_DIR := k8s/$(K8S_ENV)
KUBECONFIG_FILE := ~/.kube/doks-dungeon

k8s-kubeconfig:  ## Refresh kubeconfig for DOKS cluster via doctl
	@doctl kubernetes cluster kubeconfig save dungeon-k8s
	@echo "Kubeconfig refreshed for dungeon-k8s cluster"

k8s-setup-staging:  ## One-time staging setup (Doppler, namespace, secrets, manifests, DNS)
	@echo "==> Installing Doppler Kubernetes Operator..."
	helm repo add doppler https://helm.doppler.com || true
	helm repo update
	helm upgrade --install doppler-operator doppler/doppler-kubernetes-operator \
		-n doppler-operator --create-namespace
	@echo ""
	$(MAKE) _k8s-setup-env K8S_ENV=staging
	@echo ""
	@echo "==> Applying staging manifests..."
	kubectl apply -k k8s/staging/
	@echo ""
	@echo "==> Waiting for Load Balancer external IP (up to 5 min)..."
	@IP=""; \
	for i in $$(seq 1 30); do \
		IP=$$(kubectl get svc dungeon-app-lb -n staging-dungeon -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null); \
		if [ -n "$$IP" ]; then break; fi; \
		echo "    Attempt $$i/30: waiting for external IP..."; \
		sleep 10; \
	done; \
	if [ -z "$$IP" ]; then \
		echo "ERROR: Timed out waiting for Load Balancer IP."; \
		kubectl get svc dungeon-app-lb -n staging-dungeon; \
		exit 1; \
	fi; \
	echo "==> Load Balancer IP: $$IP"; \
	echo ""; \
	echo "==> Creating DNS record..."; \
	set -a; [ -f $(DEPLOY_ENV) ] && . ./$(DEPLOY_ENV); set +a; \
	$(PYTHON) scripts/manage_dns.py upsert --ip $$IP

k8s-setup-prod:  ## One-time production setup (namespace, secrets)
	$(MAKE) _k8s-setup-env K8S_ENV=prod

DOPPLER_PROJECT := dungeon-minus-one
DOPPLER_CONFIG = $(if $(filter prod,$(K8S_ENV)),prd,stg)
DOPPLER_TOKEN_NAME = k8s-operator-$(K8S_ENV)

_k8s-setup-env:  ## Internal: setup namespace, doppler token, and registry secret for K8S_ENV
	@echo "==> Creating $(K8S_ENV) namespace..."
	kubectl apply -f k8s/$(K8S_ENV)/namespace.yaml
	@echo ""
	@echo "==> Setting up doppler-token in $(K8S_NAMESPACE)..."
	@if kubectl get secret doppler-token -n $(K8S_NAMESPACE) >/dev/null 2>&1; then \
		echo "    doppler-token already exists, skipping"; \
	elif kubectl get secret doppler-token -n dungeon >/dev/null 2>&1; then \
		echo "    Copying doppler-token from dungeon namespace..."; \
		kubectl get secret doppler-token -n dungeon -o json \
			| jq 'del(.metadata.namespace, .metadata.resourceVersion, .metadata.uid, .metadata.creationTimestamp, .metadata.managedFields)' \
			| kubectl apply -n $(K8S_NAMESPACE) -f -; \
	else \
		echo "    Creating new Doppler service token ($(DOPPLER_CONFIG))..."; \
		TOKEN=$$(doppler configs tokens create \
			--project $(DOPPLER_PROJECT) --config $(DOPPLER_CONFIG) \
			--name $(DOPPLER_TOKEN_NAME) \
			--max-age 0 --plain) || \
			{ echo "ERROR: Failed to create Doppler token."; exit 1; }; \
		kubectl create secret generic doppler-token \
			-n $(K8S_NAMESPACE) \
			--from-literal=serviceToken=$$TOKEN; \
	fi
	@echo ""
	@echo "==> Setting up registry pull secret in $(K8S_NAMESPACE)..."
	@if kubectl get secret registry-dungeon-minus-one -n $(K8S_NAMESPACE) >/dev/null 2>&1; then \
		echo "    registry-dungeon-minus-one already exists, skipping"; \
	else \
		DOCKER_CONFIG=$$(doppler secrets get REGISTRY_DOCKER_CONFIG_B64 \
			--project $(DOPPLER_PROJECT) --config $(DOPPLER_CONFIG) --plain | base64 -d); \
		kubectl create secret generic registry-dungeon-minus-one \
			-n $(K8S_NAMESPACE) \
			--type=kubernetes.io/dockerconfigjson \
			--from-literal=.dockerconfigjson="$$DOCKER_CONFIG"; \
	fi
	@echo ""
	@echo "==> $(K8S_ENV) setup complete. Deploy with: make k8s-deploy K8S_ENV=$(K8S_ENV)"

k8s-deploy:  ## Deploy/update app to DOKS (K8S_ENV=staging|prod, optional: TAG=v1.0.0)
	@echo "==> Deploying to $(K8S_ENV) (namespace: $(K8S_NAMESPACE))"
	@if [ -n "$(TAG)" ]; then \
		CURRENT_TAG=$$(grep 'newTag:' k8s/base/kustomization.yaml | awk '{print $$2}'); \
		if [ "$$CURRENT_TAG" = "$(TAG)" ]; then \
			echo "==> Tag already set to $(TAG)"; \
		else \
			echo "==> Updating image tag: $$CURRENT_TAG -> $(TAG)"; \
			sed -i.bak 's/newTag: .*/newTag: $(TAG)/' k8s/base/kustomization.yaml && rm -f k8s/base/kustomization.yaml.bak; \
		fi; \
	fi
	kubectl apply -k $(K8S_DIR)/
	@echo ""
	@echo "==> Waiting for rollout to complete..."
	kubectl rollout status deployment/dungeon-app -n $(K8S_NAMESPACE) --timeout=300s
	$(MAKE) k8s-db-migrate K8S_ENV=$(K8S_ENV)

k8s-status:  ## Show pods, services, and secrets (K8S_ENV=staging|prod)
	@echo "==> Environment: $(K8S_ENV) (namespace: $(K8S_NAMESPACE))"
	@echo ""
	@echo "==> Pods:"
	kubectl get pods -n $(K8S_NAMESPACE) -o wide
	@echo ""
	@echo "==> Services:"
	kubectl get svc -n $(K8S_NAMESPACE)
	@echo ""
	@echo "==> Doppler Secrets:"
	kubectl get dopplersecret -n $(K8S_NAMESPACE) 2>/dev/null || echo "(none)"

k8s-logs:  ## Stream pod logs (K8S_ENV=staging|prod)
	kubectl logs -f -l app=dungeon-app -n $(K8S_NAMESPACE) --all-containers

k8s-restart:  ## Restart deployment (K8S_ENV=staging|prod)
	kubectl rollout restart deployment/dungeon-app -n $(K8S_NAMESPACE)
	kubectl rollout status deployment/dungeon-app -n $(K8S_NAMESPACE)

k8s-rollback:  ## Rollback to previous deployment revision (K8S_ENV=staging|prod)
	kubectl rollout undo deployment/dungeon-app -n $(K8S_NAMESPACE)
	kubectl rollout status deployment/dungeon-app -n $(K8S_NAMESPACE)

k8s-shell:  ## Open shell in running pod (K8S_ENV=staging|prod)
	kubectl exec -it $$(kubectl get pod -n $(K8S_NAMESPACE) -l app=dungeon-app -o jsonpath='{.items[0].metadata.name}') -n $(K8S_NAMESPACE) -- /bin/bash

k8s-db-migrate:  ## Run Alembic DB schema migrations (K8S_ENV=staging|prod)
	@IMAGE_TAG=$${TAG:-$$(grep 'newTag:' k8s/base/kustomization.yaml | awk '{print $$2}')}; \
	POD=""; \
	for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do \
		POD=$$(kubectl get pod -n $(K8S_NAMESPACE) -l app=dungeon-app \
			-o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[?(@.name=="app")].image}{"\t"}{.status.phase}{"\n"}{end}' \
			| awk -v tag=":$$IMAGE_TAG" '$$3=="Running" && $$2 ~ tag {print $$1; exit}'); \
		if [ -n "$$POD" ]; then break; fi; \
		sleep 3; \
	done; \
	if [ -z "$$POD" ]; then \
		echo "No running dungeon-app pod found with image tag $$IMAGE_TAG"; \
		kubectl get pods -n $(K8S_NAMESPACE) -l app=dungeon-app -o wide; \
		exit 1; \
	fi; \
	echo "==> Running migrations in $$POD (tag $$IMAGE_TAG)"; \
	kubectl exec -it $$POD -n $(K8S_NAMESPACE) -c app -- alembic upgrade head

k8s-seed:  ## Sync location fixtures to k8s database (K8S_ENV=staging|prod)
	kubectl exec -it $$(kubectl get pod -n $(K8S_NAMESPACE) -l app=dungeon-app -o jsonpath='{.items[0].metadata.name}') -n $(K8S_NAMESPACE) -- python scripts/sync_locations.py

k8s-seed-prune:  ## Sync + prune location fixtures (K8S_ENV=staging|prod)
	kubectl exec -it $$(kubectl get pod -n $(K8S_NAMESPACE) -l app=dungeon-app -o jsonpath='{.items[0].metadata.name}') -n $(K8S_NAMESPACE) -- python scripts/sync_locations.py --prune

k8s-invite:  ## Generate invite token (K8S_ENV=staging|prod, EMAIL="user@example.com")
	kubectl exec -it $$(kubectl get pod -n $(K8S_NAMESPACE) -l app=dungeon-app -o jsonpath='{.items[0].metadata.name}') -n $(K8S_NAMESPACE) -- python scripts/generate_invite.py $(EMAIL)

k8s-reset:  ## Reset game sessions (K8S_ENV=staging|prod)
	kubectl exec -it $$(kubectl get pod -n $(K8S_NAMESPACE) -l app=dungeon-app -o jsonpath='{.items[0].metadata.name}') -n $(K8S_NAMESPACE) -- python scripts/reset_game_state.py

k8s-auth-reset:  ## Reset auth tables (K8S_ENV=staging|prod, dangerous; add FORCE=true)
	kubectl exec -it $$(kubectl get pod -n $(K8S_NAMESPACE) -l app=dungeon-app -o jsonpath='{.items[0].metadata.name}') -n $(K8S_NAMESPACE) -- python scripts/reset_auth.py $(if $(FORCE),--force,)

k8s-create-admin:  ## Create admin user (K8S_ENV=staging|prod, USERNAME="admin" PASSWORD="pass" EMAIL="admin@example.com")
	kubectl exec -it $$(kubectl get pod -n $(K8S_NAMESPACE) -l app=dungeon-app -o jsonpath='{.items[0].metadata.name}') -n $(K8S_NAMESPACE) -- python scripts/create_admin.py $(USERNAME) $(PASSWORD) $(if $(EMAIL),--email $(EMAIL),)

k8s-notify:  ## Create notification (K8S_ENV=staging|prod, TITLE="title" MSG="message")
	kubectl exec -it $$(kubectl get pod -n $(K8S_NAMESPACE) -l app=dungeon-app -o jsonpath='{.items[0].metadata.name}') -n $(K8S_NAMESPACE) -- python scripts/create_notification.py "$(TITLE)" "$(MSG)" $(if $(TTL),--ttl $(TTL),) $(if $(TYPE),--type $(TYPE),)

# --- DNS ---

k8s-dns-upsert:  ## Create/update staging DNS A record from current LB IP
	@echo "==> Resolving Load Balancer IP..."
	@IP=""; \
	for i in $$(seq 1 30); do \
		IP=$$(kubectl get svc dungeon-app-lb -n staging-dungeon -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null); \
		if [ -n "$$IP" ]; then break; fi; \
		echo "    Attempt $$i/30: waiting for external IP..."; \
		sleep 10; \
	done; \
	if [ -z "$$IP" ]; then \
		echo "ERROR: Timed out waiting for Load Balancer IP."; \
		kubectl get svc dungeon-app-lb -n staging-dungeon; \
		exit 1; \
	fi; \
	echo "==> Load Balancer IP: $$IP"; \
	set -a; [ -f $(DEPLOY_ENV) ] && . ./$(DEPLOY_ENV); set +a; \
	$(PYTHON) scripts/manage_dns.py upsert --ip $$IP

k8s-dns-delete:  ## Delete staging DNS A record
	@set -a; [ -f $(DEPLOY_ENV) ] && . ./$(DEPLOY_ENV); set +a; \
	$(PYTHON) scripts/manage_dns.py delete

k8s-teardown-staging:  ## Tear down staging environment (DNS + namespace)
	@echo "==> Deleting staging DNS record..."
	$(MAKE) k8s-dns-delete
	@echo ""
	@echo "==> Deleting staging namespace..."
	kubectl delete namespace staging-dungeon --ignore-not-found
	@echo "==> Staging teardown complete."
