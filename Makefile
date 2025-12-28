.PHONY: setup install run clean reset hard-reset sync-locations sync-locations-prune sync-locations-check help validate-config invite frontend-install frontend-dev frontend-build dev-full notify docker-build docker-push docker-release infra-init infra-plan infra-apply infra-destroy k8s-kubeconfig k8s-setup k8s-deploy k8s-status k8s-logs k8s-restart k8s-shell k8s-seed k8s-seed-prune k8s-invite k8s-reset k8s-notify

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

notify:  ## Create a notification (usage: make notify TITLE="title" MSG="message")
	$(PYTHON) scripts/create_notification.py "$(TITLE)" "$(MSG)" $(if $(TTL),--ttl $(TTL),) $(if $(TYPE),--type $(TYPE),)

dev: setup run  ## Setup and run local dev in one command

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

# --- Infrastructure (OpenTofu) ---

infra-init:  ## Initialize OpenTofu (auto-sources .env.deploy if present)
	@if [ -f $(DEPLOY_ENV) ]; then set -a && . ./$(DEPLOY_ENV) && set +a; fi && \
		cd infra && TF_VAR_do_token=$${DO_TOKEN:-$(DO_TOKEN)} tofu init

infra-plan:  ## Plan infrastructure changes
	@if [ ! -f $(DEPLOY_ENV) ]; then \
		echo "Error: $(DEPLOY_ENV) not found."; \
		exit 1; \
	fi
	@set -a && . ./$(DEPLOY_ENV) && set +a && \
		cd infra && TF_VAR_do_token=$$DO_TOKEN tofu plan

infra-apply:  ## Apply infrastructure changes
	@if [ ! -f $(DEPLOY_ENV) ]; then \
		echo "Error: $(DEPLOY_ENV) not found."; \
		exit 1; \
	fi
	@set -a && . ./$(DEPLOY_ENV) && set +a && \
		cd infra && TF_VAR_do_token=$$DO_TOKEN tofu apply

infra-destroy:  ## Destroy all infrastructure (DANGEROUS)
	@if [ ! -f $(DEPLOY_ENV) ]; then \
		echo "Error: $(DEPLOY_ENV) not found."; \
		exit 1; \
	fi
	@set -a && . ./$(DEPLOY_ENV) && set +a && \
		cd infra && TF_VAR_do_token=$$DO_TOKEN tofu destroy

# --- Kubernetes (DOKS) ---

K8S_NAMESPACE := dungeon
KUBECONFIG_FILE := ~/.kube/doks-dungeon

k8s-kubeconfig:  ## Export kubeconfig for DOKS cluster
	@if [ ! -f $(DEPLOY_ENV) ]; then \
		echo "Error: $(DEPLOY_ENV) not found."; \
		exit 1; \
	fi
	@mkdir -p ~/.kube
	@set -a && . ./$(DEPLOY_ENV) && set +a && \
		cd infra && \
		TF_VAR_do_token=$$DO_TOKEN tofu output -raw k8s_kubeconfig > $(KUBECONFIG_FILE) && \
		chmod 600 $(KUBECONFIG_FILE) && \
		echo "Kubeconfig written to $(KUBECONFIG_FILE)" && \
		echo "Run: export KUBECONFIG=$(KUBECONFIG_FILE)"

k8s-setup:  ## One-time cluster setup (Doppler operator + namespace)
	@echo "==> Installing Doppler Kubernetes Operator..."
	helm repo add doppler https://helm.doppler.com || true
	helm repo update
	helm upgrade --install doppler-operator doppler/doppler-kubernetes-operator \
		-n doppler-operator --create-namespace
	@echo ""
	@echo "==> Creating namespace..."
	kubectl apply -f k8s/namespace.yaml
	@echo ""
	@echo "==> Next steps:"
	@echo "  1. Create a Doppler service token: doppler configs tokens create stg --name k8s-operator"
	@echo "  2. Create the secret: kubectl create secret generic doppler-token -n $(K8S_NAMESPACE) --from-literal=serviceToken=YOUR_TOKEN"
	@echo "  3. Deploy the app: make k8s-deploy"

k8s-deploy:  ## Deploy/update app to DOKS (usage: make k8s-deploy [TAG=v0.5.0])
	@if [ -n "$(TAG)" ]; then \
		echo "==> Deploying with image tag: $(TAG)"; \
		sed -i.bak 's/newTag: .*/newTag: $(TAG)/' k8s/kustomization.yaml && rm -f k8s/kustomization.yaml.bak; \
	fi
	kubectl apply -k k8s/
	@echo ""
	kubectl rollout status deployment/dungeon-app -n $(K8S_NAMESPACE)

k8s-commit-version:  ## Commit and push updated k8s manifests (usage: make k8s-commit-version [TAG=v0.6.0])
	git add k8s/kustomization.yaml
	git commit -m "chore: bump k8s deployment version to $(TAG)"
	git push origin $(GIT_BRANCH)

k8s-status:  ## Show pods, services, and secrets
	@echo "==> Pods:"
	kubectl get pods -n $(K8S_NAMESPACE) -o wide
	@echo ""
	@echo "==> Services:"
	kubectl get svc -n $(K8S_NAMESPACE)
	@echo ""
	@echo "==> Doppler Secrets:"
	kubectl get dopplersecret -n $(K8S_NAMESPACE) 2>/dev/null || echo "(none)"

k8s-logs:  ## Stream pod logs
	kubectl logs -f -l app=dungeon-app -n $(K8S_NAMESPACE) --all-containers

k8s-restart:  ## Restart deployment (rolling)
	kubectl rollout restart deployment/dungeon-app -n $(K8S_NAMESPACE)
	kubectl rollout status deployment/dungeon-app -n $(K8S_NAMESPACE)

k8s-shell:  ## Open shell in running pod
	kubectl exec -it $$(kubectl get pod -n $(K8S_NAMESPACE) -l app=dungeon-app -o jsonpath='{.items[0].metadata.name}') -n $(K8S_NAMESPACE) -- /bin/bash

k8s-seed:  ## Sync location fixtures to k8s database
	kubectl exec -it $$(kubectl get pod -n $(K8S_NAMESPACE) -l app=dungeon-app -o jsonpath='{.items[0].metadata.name}') -n $(K8S_NAMESPACE) -- python scripts/sync_locations.py

k8s-seed-prune:  ## Sync + prune location fixtures in k8s database
	kubectl exec -it $$(kubectl get pod -n $(K8S_NAMESPACE) -l app=dungeon-app -o jsonpath='{.items[0].metadata.name}') -n $(K8S_NAMESPACE) -- python scripts/sync_locations.py --prune

k8s-invite:  ## Generate invite code in k8s
	kubectl exec -it $$(kubectl get pod -n $(K8S_NAMESPACE) -l app=dungeon-app -o jsonpath='{.items[0].metadata.name}') -n $(K8S_NAMESPACE) -- python scripts/generate_invite.py

k8s-reset:  ## Reset game sessions in k8s (keeps users)
	kubectl exec -it $$(kubectl get pod -n $(K8S_NAMESPACE) -l app=dungeon-app -o jsonpath='{.items[0].metadata.name}') -n $(K8S_NAMESPACE) -- python scripts/reset_game_state.py

k8s-notify:  ## Create notification in k8s (usage: make k8s-notify TITLE="title" MSG="message")
	kubectl exec -it $$(kubectl get pod -n $(K8S_NAMESPACE) -l app=dungeon-app -o jsonpath='{.items[0].metadata.name}') -n $(K8S_NAMESPACE) -- python scripts/create_notification.py "$(TITLE)" "$(MSG)" $(if $(TTL),--ttl $(TTL),) $(if $(TYPE),--type $(TYPE),)
