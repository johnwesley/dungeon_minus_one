# Deployment Infrastructure

> Part of the [project documentation](../CLAUDE.md). This file covers Kubernetes manifests, deployment workflows, and infrastructure.

## Manifest Structure

Multi-environment structure using Kustomize overlays:

```
k8s/
├── base/                    # Shared resources
│   ├── deployment.yaml      # App deployment (probes, graceful shutdown)
│   └── kustomization.yaml   # Base config (image tag set here)
├── staging/                 # Staging overlay
│   ├── namespace.yaml       # staging-dungeon namespace
│   ├── doppler-secret.yaml  # DopplerSecret (config: stg)
│   ├── service.yaml         # DO LoadBalancer with TLS
│   ├── podmonitor.yaml      # Prometheus monitoring
│   ├── dashboards/          # Grafana dashboard JSON
│   └── kustomization.yaml
├── prod/                    # Production overlay
│   ├── namespace.yaml       # prod-dungeon namespace
│   ├── doppler-secret.yaml  # DopplerSecret (config: prd)
│   ├── service.yaml         # DO LoadBalancer with TLS
│   ├── podmonitor.yaml      # Prometheus monitoring
│   ├── dashboards/          # Grafana dashboard JSON
│   └── kustomization.yaml
└── monitoring/              # Reference dashboards (copied to overlays)
    ├── kustomization.yaml   # ConfigMapGenerator for Grafana dashboard
    ├── podmonitor.yaml
    └── dashboards/
        └── dungeon-game-metrics.json
```

| Environment | Namespace | Doppler Config | Domain |
|-------------|-----------|----------------|--------|
| Staging | `staging-dungeon` | `stg` | `staging.dungeonminusone.com` |
| Production | `prod-dungeon` | `prd` | `dungeonminusone.com` |

## Base Resources

### Deployment (`base/deployment.yaml`)

- **Replicas**: 2
- **Strategy**: RollingUpdate (`maxUnavailable: 0`, `maxSurge: 1`)
- **Image**: `registry.digitalocean.com/dungeon-minus-one/dungeon-minus-one` (tag in kustomization.yaml)
- **Image pull secret**: `registry-dungeon-minus-one`
- **Env**: All env vars from `dungeon-app-secrets` secret (managed by Doppler)
- **Port**: 8000 (named `http`)

**Probes:**
| Probe | Path | Initial Delay | Period | Timeout | Failure Threshold |
|-------|------|---------------|--------|---------|-------------------|
| Readiness | `/health` | 10s | 5s | 3s | 3 |
| Liveness | `/health` | 30s | 10s | 5s | 3 |

**Resources:**
| | Request | Limit |
|--|---------|-------|
| Memory | 256Mi | 512Mi |
| CPU | 100m | 500m |

**Graceful shutdown:**
- `terminationGracePeriodSeconds: 60`
- `preStop` hook: `sleep 15` (allows LB to stop routing traffic)

### Kustomization (`base/kustomization.yaml`)

- Defines the image tag (e.g., `newTag: v1.2.1-staging`)
- GitHub Actions workflow auto-updates this tag on build
- Common labels: `app.kubernetes.io/name: dungeon`, `app.kubernetes.io/part-of: dungeon-minus-one`

## Overlay Resources

Each environment overlay (staging/prod) adds:

| Resource | Purpose |
|----------|---------|
| `namespace.yaml` | Environment-specific namespace with labels |
| `doppler-secret.yaml` | `DopplerSecret` CRD that syncs secrets from Doppler to `dungeon-app-secrets` K8s secret |
| `service.yaml` | DO LoadBalancer with TLS termination, HTTP→HTTPS redirect, health checks |
| `podmonitor.yaml` | Prometheus PodMonitor scraping `/metrics` every 15s |
| `kustomization.yaml` | References `../base` + all overlay resources, sets namespace |

### Service (LoadBalancer)

DO LoadBalancer annotations handle:
- Regional LB type
- TLS on port 443 with DO-managed certificate
- HTTP→HTTPS redirect
- Health checks on `/health` (10s interval, 5s timeout, 3 healthy/unhealthy threshold)
- Routes ports 80 and 443 → container port 8000

## Secrets Management (Doppler)

Secrets are managed in Doppler, not in the repository:

- **Doppler Operator** runs in-cluster and watches `DopplerSecret` resources
- Each environment has a `DopplerSecret` pointing to its config (`stg` or `prd`)
- The operator syncs secrets to a K8s `Opaque` secret named `dungeon-app-secrets`
- Secrets resync every 60 seconds
- The `doppler-token` K8s secret (created during setup) authenticates with Doppler

Setup creates the Doppler token secret:
```bash
make k8s-setup-staging  # Creates doppler-token + registry secrets, applies manifests
```

## Deployment Workflows

### GitHub Actions (Primary)

The `.github/workflows/docker-build.yml` workflow handles builds and asset publishing:

1. Trigger from GitHub UI: **Actions > Build and Push Docker Image > Run workflow**
2. Inputs: `tag` (e.g., `v0.9.2`) and `asset_env` (`staging` or `prod`)
3. Workflow steps:
   - Builds frontend with correct CDN URL (based on `asset_env`)
   - Validates frontend build output
   - Publishes assets to DO Spaces
   - Verifies assets accessible on CDN
   - Builds and pushes Docker image
   - Updates and commits `k8s/base/kustomization.yaml` with new tag

After workflow completes, deploy with:
```bash
make k8s-deploy K8S_ENV=staging  # or K8S_ENV=prod
```

### Manual Deployment (Alternative)

Requires `infra/.env.deploy` with Spaces credentials:
```bash
make release-staging TAG=v0.9.2  # or release-prod
```

## Infrastructure (OpenTofu)

```
infra/
├── k8s-cluster.tf    # DOKS cluster with auto-scaling node pool
├── database.tf       # Managed PostgreSQL cluster + firewall
├── variables.tf      # Configuration variables
└── outputs.tf        # Cluster endpoints and credentials
```

Commands:
```bash
make infra-init     # Initialize OpenTofu
make infra-plan     # Plan infrastructure changes
make infra-apply    # Apply infrastructure changes
make infra-destroy  # Destroy infrastructure
```

## Cluster Commands

All k8s commands accept `K8S_ENV=staging` (default) or `K8S_ENV=prod`:

```bash
make k8s-deploy K8S_ENV=staging  # Deploy to staging
make k8s-deploy K8S_ENV=prod     # Deploy to production
make k8s-status      # Show pods, services, secrets
make k8s-logs        # Stream pod logs
make k8s-restart     # Rolling restart
make k8s-rollback    # Rollback to previous revision
make k8s-db-migrate  # Run Alembic DB schema migrations
make k8s-seed        # Sync location fixtures
make k8s-invite      # Generate invite code
make k8s-reset       # Reset game sessions
make k8s-notify      # Create notification
make k8s-shell       # Open shell in running pod
make k8s-test-unit          # Run pytest in staging/prod pod
make k8s-verify-movement    # Run movement verification (K8s Job, staging)
make k8s-test               # Run all staging tests (unit + movement)
```

## Staging Lifecycle

```bash
make k8s-setup-staging    # Secrets + apply manifests + wait for LB + create DNS
make k8s-deploy K8S_ENV=staging  # Update image tag, rollout, migrate (no DNS)
# ...
make k8s-teardown-staging # Delete DNS + delete namespace
```

`k8s-setup-staging` handles full environment creation including DNS. Subsequent deploys via `k8s-deploy` do not touch DNS. Use `k8s-dns-upsert` to re-sync DNS if the LB IP changes.

## High Availability (HA)

**Connection Resilience:**
- `app/connection_manager.py` - Tracks active SSE connections for graceful shutdown
- `frontend/src/js/sse-handler.js` - Implements exponential backoff retry (1s > 30s, max 5 retries)
- Backend sends `closing` event before shutdown to notify clients

**Graceful Shutdown Flow:**
1. Pod receives SIGTERM
2. `connection_manager.shutdown_event` is set
3. Active SSE streams receive `closing` event and complete
4. `wait_for_connections_to_drain()` waits up to 30s for streams to finish
5. Uvicorn shutdown completes

**K8s HA Features:**
- Rolling updates with `maxUnavailable: 0`
- Readiness/liveness probes on `/health`
- `preStop` hook with 15s sleep for connection draining
- `terminationGracePeriodSeconds: 60`
- DO Load Balancer with TLS certificate

## Observability

Prometheus metrics are exposed at `/metrics` via `prometheus-fastapi-instrumentator`. HTTP-level metrics (request count, latency, in-progress) plus custom game metrics (location entries, dwell time, victories).

**PodMonitor** in each overlay scrapes `/metrics` on port `http` every 15s. Must have label `release: prometheus` to match the Prometheus operator selector.

**Grafana Dashboard** is deployed via ConfigMapGenerator with `grafana_dashboard: "1"` label for auto-discovery.

**Access:**
```bash
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
# Credentials: admin / prom-operator
```

## Troubleshooting

```bash
# Check pod status and recent events
make k8s-status K8S_ENV=staging

# Stream logs from all pods
make k8s-logs K8S_ENV=staging

# Open a shell in a running pod
make k8s-shell K8S_ENV=staging

# Check if secrets are synced from Doppler
kubectl get secrets -n staging-dungeon

# Check Doppler operator status
kubectl get dopplersecrets -n staging-dungeon

# Rollback a bad deployment
make k8s-rollback K8S_ENV=staging

# Run DB migrations manually
make k8s-db-migrate K8S_ENV=staging
```
