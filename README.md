# Dungeon Minus One

A conversational text-adventure game powered by Claude.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Local Development                                          │
│  Browser ↔ FastAPI :8000 ↔ SQLite                           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Production (DOKS)                                          │
│  Browser → DO Load Balancer :443 → App Pods → Postgres      │
│                                        ↓                    │
│                          Anthropic API (Claude)             │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start (Local)

```bash
make setup
cp .env.example .env  # Add ANTHROPIC_API_KEY
make dev-full
```

Access at `http://localhost:5173`. Runs backend + frontend with hot reload.

---

## Deployment

### GitHub Actions (Recommended)

Trigger from GitHub UI: **Actions → Build and Push Docker Image → Run workflow**

| Input | Description |
|-------|-------------|
| `tag` | Version tag (e.g., `v0.9.2`) |
| `asset_env` | `staging` or `prod` (selects CDN domain) |

The workflow:
1. Builds frontend with correct CDN URL
2. Publishes assets to DO Spaces
3. Verifies assets accessible on CDN
4. Builds and pushes Docker image
5. Commits `k8s/kustomization.yaml` with new tag

After workflow completes:
```bash
make k8s-deploy TAG=v0.9.2
```

### Manual Deployment (Alternative)

Requires `infra/.env.deploy` with Spaces credentials:

```bash
# Staging
make release-staging TAG=v0.9.2

# Production
make release-prod TAG=v0.9.2
```

---

## Infrastructure Setup (One-Time)

### Prerequisites

- [OpenTofu](https://opentofu.org/) installed
- [kubectl](https://kubernetes.io/docs/tasks/tools/) installed
- [Helm](https://helm.sh/) installed
- DigitalOcean API token
- SSL certificate uploaded to DO (name: `dungeon-cert`)

### 1. Create Environment File

```bash
cp infra/.env.deploy.example infra/.env.deploy
# Edit with DO_TOKEN, SPACES_ACCESS_KEY, SPACES_SECRET_KEY
```

### 2. Provision Infrastructure

```bash
make infra-init
make infra-plan
make infra-apply
make k8s-kubeconfig
export KUBECONFIG=~/.kube/doks-dungeon
```

### 3. Setup Doppler (Secrets)

1. Create Doppler project: `staging-deployment` with config `stg`
2. Add secrets: `ANTHROPIC_API_KEY`, `AUTH_SECRET_KEY`, `DATABASE_URL`, etc.
3. Generate service token for k8s operator

```bash
make k8s-setup  # Installs Doppler operator
kubectl create secret generic doppler-token -n dungeon --from-literal=serviceToken=YOUR_TOKEN
```

### 4. Setup CDN Assets

1. Create Space: `dungeon-minus-one-assets` in `nyc3`, enable CDN
2. Add CDN domains:
   - `assets-staging.dungeonminusone.com`
   - `assets.dungeonminusone.com`
3. Configure CORS for your app domains
4. Add GitHub secrets: `SPACES_ACCESS_KEY`, `SPACES_SECRET_KEY`, `DIGITALOCEAN_ACCESS_TOKEN`

---

## Cluster Management

| Command | Description |
|---------|-------------|
| `make k8s-status` | Show pods, services, secrets |
| `make k8s-logs` | Stream pod logs |
| `make k8s-restart` | Rolling restart deployment |
| `make k8s-rollback` | Rollback to previous revision |
| `make k8s-shell` | Open shell in running pod |

## Application Management

| Command | Description |
|---------|-------------|
| `make k8s-invite` | Generate invite code |
| `make k8s-seed` | Sync location fixtures |
| `make k8s-reset` | Reset game sessions |
| `make k8s-notify TITLE="..." MSG="..."` | Create notification |

## Local Commands

| Command | Description |
|---------|-------------|
| `make dev-full` | Start backend + frontend with hot reload |
| `make reset` | Clear game state (keep locations) |
| `make hard-reset` | Wipe DB and re-seed |
| `make invite` | Generate invite code |
| `make verify-movement` | Run movement regression test |
| `make validate-config` | Validate configuration |

---

## Debug Logging

| Variable | Description |
|----------|-------------|
| `DEBUG_LLM=true` | LLM context logging → `.cursor/llm_debug.log` |
| `DEBUG_GAME_TOOLS=true` | Tool handler logging → `.cursor/debug.log` |
| `DEBUG_SERVICE=true` | Service logging → `.cursor/service_debug.log` |
