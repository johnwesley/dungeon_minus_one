# Dungeon Minus One

## Project Overview

**Dungeon Minus One** is a conversational text-adventure game powered by Anthropic's Claude. It combines the narrative flexibility of a Large Language Model (LLM) with the deterministic rules of a classic text adventure engine.

**Key Architecture:**
*   **Hybrid Engine:** The LLM acts as the narrator and intent parser, but movement, inventory, and world state are strictly managed by Python code and a database.
*   **Backend:** Python 3.x (tested with 3.11+) using **FastAPI**.
*   **Frontend:** A lightweight web interface built with **Vite** (served by FastAPI or CDN).
*   **Database:** **PostgreSQL** (local development + production).
*   **AI:** Uses the Anthropic API (Claude) for generating responses and handling user intent.
*   **Infrastructure:** Dockerized, deployed to DigitalOcean Kubernetes (DOKS) via Terraform (OpenTofu).

## Project Structure

*   **`app/`**: Main application source code.
    *   `api/`: FastAPI route handlers (chat, auth, game).
    *   `services/`: Business logic (game engine, LLM integration).
    *   `models/`: Pydantic schemas and SQLAlchemy models.
    *   `repositories/`: Database access layer.
    *   `clients/`: External API clients (Anthropic) and tool definitions.
    *   `static/`: Legacy/fallback frontend assets. (The modern UI source is in `frontend/`).
*   **`frontend/`**: Modern web interface source code (Vite + JavaScript).
*   **`data/locations/`**: JSON files defining the game world (rooms, items, exits).
*   **`prompts/`**: Markdown files containing system prompts for the Narrator and other personas.
*   **`skills/`**: Markdown prompt files for game mechanics (concatenated to system prompt at runtime). Includes: movement-resolution, inventory-management, npc-blocking, lock-and-gate-resolution, environmental-state-water, victory-and-trophy, darkness-and-grue, written-materials, restart-protocol.
*   **`scripts/`**: Utility scripts for admin tasks, data syncing, and deployment.
*   **`infra/`**: Terraform/OpenTofu configuration for DigitalOcean resources.
*   **`k8s/`**: Kubernetes manifests for deployment.

## Getting Started

### Prerequisites
*   Python 3.x (tested with 3.11+)
*   Node.js & npm (for frontend changes)
*   An Anthropic API Key

### Setup & Run (Local)

1.  **Initialize the Environment:**
    ```bash
    make setup
    ```
    This creates a virtual environment (`venv`) and installs Python dependencies.

2.  **Configuration:**
    Copy the example environment file and edit it:
    ```bash
    cp .env.example .env
    ```
    *   **Crucial:** Add your `ANTHROPIC_API_KEY` to `.env`.
    *   Set `ENVIRONMENT=dev`.

3.  **Run the Server:**
    ```bash
    make run
    ```
    This starts the FastAPI server at `http://localhost:8000`.
    *   *Note:* The command automatically runs `scripts/sync_locations.py` to populate the local Postgres database with location data.

4.  **Frontend Development (Optional):**
    If working on the frontend specifically:
    ```bash
    make frontend-install
    make frontend-dev
    ```

### Common Tasks

*   **Reset Game State:**
    *   `make reset`: Clears user sessions/inventory but keeps the world map.
*   `make hard-reset`: Drops and recreates tables, then re-seeds everything from `data/locations/`.
*   **Sync Locations:**
    *   `make sync-locations`: Updates the DB with changes from `data/locations/` JSON files.
*   **Create Invite Code:**
    *   `make invite`: Generates a code for the invite-only auth system.
*   **Tests:**
    *   `make test`: Runs full test pipeline (pytest + walkthrough verification).
    *   `make verify-movement`: Runs automated tests for movement logic.
*   **Admin:**
    *   `make create-admin`: Create a new admin user.
    *   `make auth-reset`: Reset auth-related tables (requires `FORCE=true`).

## Development Conventions

*   **Code Style:** Follow PEP 8. Use type hints extensively.
*   **Async-First:** Repositories, services, and routes should be `async` to keep DB/LLM calls non-blocking.
*   **Game Data:**
    *   Locations are defined in `data/locations/`.
    *   Use kebab-case for IDs (e.g., `living-room`).
    *   Always run `make sync-locations` (or restart the server) after modifying JSON files.
*   **Prompts:** System prompts live in `prompts/`. Changes here affect the narrator's personality and rule adherence.
*   **Tools:** The LLM interacts with the game state via "tools" defined in `app/clients/tools.py` and handled in `app/services/game_tools.py`. Ensure these remain in sync.

## Observability

*   **Metrics:** Prometheus metrics exposed at `/metrics` endpoint.
*   **Monitoring:** Grafana dashboards available via `kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80`.

## Documentation References

*   **`CLAUDE.md`**: Comprehensive codebase documentation (primary reference for AI assistants).
*   **`WALKTHROUGH.md`**: A complete guide to beating the game, useful for testing game logic.
*   **`AGENTS.md`**: Condensed repository guidelines for AI code generation.
*   **`README.md`**: General project info and deployment details.
