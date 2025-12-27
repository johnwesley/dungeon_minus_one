# Dungeon Minus One

A conversational text-adventure game powered by Claude.

## System Architecture

```mermaid
flowchart TB
    subgraph Local["Local Development"]
        L_Browser[Browser] <--> L_App[FastAPI :8000]
        L_App <--> L_DB[(SQLite)]
    end

    subgraph DOKS["Kubernetes (DOKS)"]
        K_LB[Load Balancer :443] <--> K_App[App Pods]
        K_App <--> K_DB[(Managed Postgres)]
    end

    L_App -.-> Claude[Anthropic API]
    K_App -.-> Claude
```

## Quick Start (Local)

1.  **Setup**: Create venv and install dependencies.
    ```bash
    make setup
    cp .env.example .env  # Add your ANTHROPIC_API_KEY
    ```
    Set `ENVIRONMENT=dev` and leave `DB_AUTO_CREATE=true` for local use.

2.  **Run**: Start the dev server.
    ```bash
    make run
    ```
    Access at `http://localhost:8000`.

## Kubernetes Deployment

The application is deployed to DigitalOcean Kubernetes (DOKS) with a managed PostgreSQL database.

```bash
# Build and push Docker image
make docker-release TAG=v0.6.0

# Deploy to cluster
make k8s-deploy TAG=v0.6.0

# Check status
make k8s-status
```

-   **TLS**: DO Load Balancer with managed certificate
-   **Database**: Managed PostgreSQL
-   **Secrets**: Doppler Kubernetes Operator
-   **Auth**: Invite-only (`make k8s-invite`)

## Commands

Run `make help` to see all available commands.

| Command | Description |
| :--- | :--- |
| `make run` | Run local dev server |
| `make reset` | Clear game state (keep locations) |
| `make hard-reset` | Wipe DB and re-seed locations |
| `make verify-movement` | Run automated test for movement logic |
| `make validate-config` | Validate configuration (set `DB_CHECK=true` to test DB) |
| `make invite` | Generate invite code (local) |
| `make k8s-deploy` | Deploy app to DOKS cluster |
| `make k8s-status` | Show pods, services, secrets |
| `make k8s-logs` | Stream pod logs |
| `make k8s-invite` | Generate invite code in cluster |

## Debug Logging

The API output includes debug prints only when explicitly enabled. Leave these unset/false for clean responses.

- `DEBUG_LLM=true` enables LLM context debug prints and writes JSON lines to `.cursor/llm_debug.log`.
- `DEBUG_GAME_TOOLS=true` enables tool handler debug prints and writes JSON lines to `.cursor/debug.log`.
- `DEBUG_SERVICE=true` enables service debug JSON logging to `.cursor/service_debug.log` (no console output).

To silence Uvicorn access logs, run with `--log-level warning` (for example, update `make run`).
