# Dungeon Minus One

A conversational text-adventure game powered by Claude.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Local Development                                          │
│  Browser ↔ FastAPI :8000 ↔ Postgres                         │
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
make db-up
cp .env.example .env  # Add ANTHROPIC_API_KEY
make dev-full
```

Access at `http://localhost:5173`. Runs backend + frontend with hot reload.

---

## Deployment

### Deployment Flow

This is the single source of truth for keeping the app and DB in sync with `data/`:

1. Build and push a unique image tag (GitHub Actions or manual release).
2. Deploy the new image: `make k8s-deploy TAG=vX.Y.Z` (rollout + `k8s-db-migrate`).
3. Sync location fixtures: `make k8s-seed`.
4. If you removed locations from `data/locations`, run `make k8s-seed-prune` (destructive to stale locations and may reset affected game states).
5. Smoke test (e.g., read the leaflet or move between rooms).

### GitHub Actions (Recommended)

Trigger from GitHub UI: **Actions → Build and Push Docker Image → Run workflow**

| Input | Description |
|-------|-------------|
| `tag` | Version tag (e.g., `v0.9.2`) |
| `asset_env` | `staging` or `prod` (selects CDN domain) |

After the workflow completes, follow the **Deployment Flow** above.

### Environments

| Environment | Namespace | Doppler Config | Domain |
|-------------|-----------|----------------|--------|
| Staging | `staging-dungeon` | `stg` | `staging.dungeonminusone.com` |
| Production | `prod-dungeon` | `prd` | `dungeonminusone.com` |

All k8s commands accept `K8S_ENV=staging` (default) or `K8S_ENV=prod`.

### Manual Deployment (Alternative)

Requires `infra/.env.deploy` with Spaces credentials:

```bash
make release-staging TAG=v0.9.2
make release-prod TAG=v0.9.2
```

Then follow the **Deployment Flow** above.

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

1. Create Doppler project `dungeon-minus-one` with configs `stg` and `prd`
2. Add secrets: `ANTHROPIC_API_KEY`, `AUTH_SECRET_KEY`, `DATABASE_URL`, etc.

```bash
make k8s-setup-staging  # Installs Doppler operator, creates namespace + secrets
make k8s-setup-prod     # Creates namespace + secrets (operator already installed)
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

All commands default to staging. Add `K8S_ENV=prod` for production.

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

## Staging Lifecycle

Staging is kept down when not in use. Bring it up for testing, tear it down when done.

**Bring up:**
```bash
make k8s-setup-staging
make k8s-deploy K8S_ENV=staging
make k8s-seed K8S_ENV=staging
```

**Tear down:**
```bash
kubectl delete ns staging-dungeon
```

The setup target is idempotent — it creates the namespace, Doppler service token, and registry pull secret. The Doppler operator syncs app secrets automatically once the token is in place.

## Production Lifecycle

Production stays up. Deployments go through GitHub Actions.

**Deploy a new version:**
1. Trigger workflow: **Actions → Build and Push Docker Image** with `tag` and `asset_env=prod`
2. After build completes:
   ```bash
   make k8s-deploy K8S_ENV=prod
   make k8s-seed K8S_ENV=prod        # if location data changed
   ```

**Rollback:**
```bash
make k8s-rollback K8S_ENV=prod
```

**First-time setup** (already done, for reference):
```bash
make k8s-setup-prod
make k8s-deploy K8S_ENV=prod
make k8s-seed K8S_ENV=prod
make k8s-create-admin K8S_ENV=prod USERNAME="admin" PASSWORD="..." EMAIL="..."
```

## Admin Pages

| URL | Description |
|-----|-------------|
| `/admin/invites` | Manage invite requests (approve/reject) |

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

---

## Observability

The application includes Prometheus metrics and a Grafana dashboard deployed via kube-prometheus-stack.

### Access Grafana

```bash
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
```

Open `http://localhost:3000` (credentials: `admin` / `prom-operator`)

Dashboard: **Dungeon Minus One - LLM Metrics**

### Metrics Reference

| Metric | Type | Description |
|--------|------|-------------|
| `llm_sessions_total` | Counter | Total game sessions started |
| `llm_session_active` | Gauge | Currently active SSE connections (mid-conversation) |
| `llm_api_requests_total` | Counter | Total Anthropic API calls |
| `llm_api_duration_seconds` | Histogram | API call latency (P50/P95/P99) |
| `llm_tokens_input_total` | Counter | Input tokens consumed (cost driver) |
| `llm_tokens_output_total` | Counter | Output tokens generated |
| `llm_tokens_cache_read_total` | Counter | Tokens served from prompt cache (savings) |
| `llm_tool_calls_total` | Counter | Tool executions by name and status |
| `llm_errors_total` | Counter | API errors by type |
| `llm_thinking_requests_total` | Counter | Requests using extended thinking |

### Dashboard Panels

| Panel | What It Shows |
|-------|---------------|
| **API Latency (P50/P95/P99)** | Response time distribution - high P95 = slow |
| **Request Rate** | API calls per minute |
| **Error Rate %** | Failures as percentage of requests |
| **Active Sessions** | Players currently mid-conversation |
| **Token Usage** | Input/output/cache tokens per minute |
| **Tool Calls by Status** | Game tool success/failure rates |
| **Total Registered Players** | All-time registered users (from PostgreSQL) |
| **Active Last 24h** | Unique players with activity in last 24 hours |
| **Thinking Usage** | Extended thinking feature usage over time |

### Interpreting the Data

**"Is the dungeon scary, or just slow and broken?"**

- **Slow** = High P95 latency in API Latency panel
- **Broken** = High Error Rate % or red bars in Tool Calls
- **Scary** = Low latency + low errors (working as intended)
