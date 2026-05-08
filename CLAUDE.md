# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **See also:** [app/CLAUDE.md](app/CLAUDE.md) for application architecture, database, config, auth, and API endpoints. [k8s/CLAUDE.md](k8s/CLAUDE.md) for deployment infrastructure, manifests, and observability.

## Project Overview

This is a text-adventure game powered by Claude. The application uses FastAPI with streaming SSE responses and a web UI for gameplay. Claude acts as the game narrator with a dry, sarcastic wit.

### Prompts Directory

System prompts are stored as markdown files in `prompts/` at the project root, separate from Python code:

```
prompts/
├── __init__.py    # Prompt loading utilities
├── narrator.md    # Game narrator system prompt
└── premise.md     # Game opening narrative/premise
```

The narrator prompt defines the game's tone:
- Describes scenes vividly but concisely
- Presents interactable elements clearly (objects, characters, paths)
- Responds with guidance and playful sarcasm
- Never controls player actions; only reacts to them
- Never breaks character or mentions being an AI
- Maintains continuity across game steps

### Template Variables

The system prompt uses `{{ENVIRONMENT}}` and `{{PLAYER_INFO}}` template placeholders for dynamic content injection. Use the `render_prompt()` helper:

```python
from prompts import render_prompt, NARRATOR_PROMPT

system_prompt = render_prompt(
    NARRATOR_PROMPT,
    ENVIRONMENT=environment_data,
    PLAYER_INFO=player_data
)
await llm_client.chat(messages, system_prompt=system_prompt)
```

To add a new prompt, create a `.md` file in `prompts/` and add a constant to `prompts/__init__.py`.

## Common Commands

```bash
make setup      # Create venv and install dependencies
make run        # Start dev server (uvicorn with --reload on port 8000)
make dev        # Setup and run in one command
make reset      # Soft reset: clear game state but keep locations
make hard-reset # Delete DB and re-seed locations
make verify-movement # Run automated regression test for movement
make invite     # Generate a new invite code
make notify     # Create a system notification
make clean      # Remove venv and cache files

# Database (local Postgres via Docker)
make db-up      # Start local Postgres container
make db-down    # Stop local Postgres container
make db-migrate # Run Alembic migrations against local Postgres

# Frontend (Vite)
make frontend-install  # Install frontend npm dependencies
make frontend-dev      # Start Vite dev server (port 5173)
make frontend-build    # Build frontend for staging/prod-style
make dev-full          # Start backend + frontend in parallel

# Location Data
make sync-locations        # Sync location fixtures (non-destructive)
make sync-locations-prune  # Sync + prune orphaned locations
make sync-locations-check  # Check DB matches fixtures (dry-run)

# Validation
make validate-config  # Validate configuration settings

# Docker
make docker-build    # Build Docker image
make docker-push     # Push image to registry
make docker-release  # Build and push Docker image

# Infrastructure (OpenTofu)
make infra-init     # Initialize OpenTofu
make infra-plan     # Plan infrastructure changes
make infra-apply    # Apply infrastructure changes
make infra-destroy  # Destroy infrastructure

# Kubernetes (K8S_ENV=staging|prod)
make k8s-deploy         # Deploy app (default: staging)
make k8s-deploy K8S_ENV=prod  # Deploy to production
make k8s-status         # Show pods, services, secrets
make k8s-logs           # Stream pod logs
make k8s-restart        # Rolling restart deployment
make k8s-db-migrate     # Run Alembic DB migrations
make k8s-seed           # Sync location fixtures
make k8s-seed-prune     # Sync + prune location fixtures
make k8s-invite         # Generate invite code
make k8s-kubeconfig     # Export kubeconfig for DOKS cluster
make k8s-setup-staging  # One-time staging setup (Doppler, namespace, manifests, DNS)
make k8s-setup-prod     # One-time production setup (namespace)
make k8s-teardown-staging  # Tear down staging (DNS + namespace)
make k8s-shell          # Open shell in running pod
make k8s-rollback       # Rollback to previous deployment
make k8s-dns-upsert     # Create/update staging DNS from LB IP
make k8s-dns-delete     # Delete staging DNS A record
make k8s-test-unit          # Run pytest in staging/prod pod
make k8s-verify-movement    # Run movement verification (K8s Job, staging)
make k8s-test               # Run all staging tests (unit + movement)
```

### Development Workflow

**Option 1: Frontend development with hot reload**
```bash
# Terminal 1: Backend
make run

# Terminal 2: Frontend (with hot reload)
make frontend-dev
# Access at http://localhost:5173 (proxies API to backend)
```

**Option 2: Production-style (build frontend first)**
```bash
make frontend-build
make run
# Access at http://localhost:8000
```

## Project Structure

```
app/               # Python backend (see app/CLAUDE.md)
frontend/          # Vite + HTMX frontend (see app/CLAUDE.md)
k8s/               # Kubernetes manifests (see k8s/CLAUDE.md)
infra/             # OpenTofu infrastructure (see k8s/CLAUDE.md)
prompts/           # System prompt markdown files
skills/            # Game mechanic skill files
data/locations/    # Location fixture JSON files (72 files)
scripts/           # Utility scripts
alembic/           # Database migration files
```

## Game Data Layer

Location data is stored in the **database** and synced from JSON files in `data/locations/`. This directory contains 72 location definition files (e.g., `cellar.json`, `clearing.json`, `cave.json`) that are loaded by `scripts/sync_locations.py` on initial setup or hard reset. By default it upserts locations, reconciles exits (one per `source_id` + `direction`), and verifies the DB matches the fixtures; use `--prune` to delete DB locations/exits that are not present in the JSON fixtures and to reset any `game_states.current_location` that points to a missing location back to `start`. Use `--dry-run --prune` to check whether the DB is out of sync without making changes.

Access locations using the repository:

```python
from app.repositories.game_repository import GameRepository

game_repo = GameRepository(session)
location = await game_repo.get_location("tavern")  # Returns dict with exits
```

### Tool Use

Claude (as narrator) has access to four tools via the Anthropic SDK tool use feature:

| Tool | Purpose |
|------|---------|
| `get_game_state` | Fetch player's current location, inventory, stats |
| `get_location_data` | Fetch static location description and elements |
| `update_game_state` | Persist changes after player actions |
| `restart_game` | Reset game to beginning (clears conversation + game state) |

The `chat_stream_with_tools()` method in `ConversationService` handles tool resolution with hybrid streaming (tools resolve first, then response streams).

### Skills System

Game mechanics are decomposed into modular skills using a prompt concatenation approach. Skills provide focused instructions for specific game behaviors and are appended to the system prompt at runtime.

**Skills Directory:**
```
skills/
├── README.md                          # Documentation
├── movement-resolution/SKILL.md       # Location movement, exit validation
├── inventory-management/SKILL.md      # Take/drop items, container logic
├── npc-blocking/SKILL.md              # NPC guards, bypass flags
├── lock-and-gate-resolution/SKILL.md  # Grating lock, keys
├── environmental-state-water/SKILL.md # Dam/reservoir water level
├── victory-and-trophy/SKILL.md        # Trophy case, victory sequence
├── darkness-and-grue/SKILL.md         # Light sources, grue death
├── written-materials/SKILL.md         # Verbatim quoting of text
└── gas-room-hazard/SKILL.md           # Coal gas explosion, electric light
```

**Configuration:**
- `SKILLS_ENABLED` - Enable skills (default: false)

**Architecture:**
- Skills are instruction-based markdown files, not code execution
- The base `prompts/narrator.md` contains core personality (~76 lines)
- Game mechanic details live in skill files
- `load_all_skills()` in `prompts/__init__.py` concatenates all SKILL.md files
- Concatenated skills are appended to the system prompt when `SKILLS_ENABLED=true`
- Zero latency - no external API calls, purely local prompt assembly

**Game Controls:**
- **RESTART**: Available via button in left sidebar or by asking the narrator. Deletes current conversation and starts fresh.
- **SAVE/RESTORE**: Not supported - game auto-saves after every action. No save slots.

### Trophy Case (Victory Progress)

The trophy case in the Living Room stores treasures. Deposited treasures are tracked in `flags.trophy_case`.

**UI Display:**
- **INVENTORY** (right panel): Shows all items the player is carrying, including treasures not yet deposited
- **TROPHY CASE** (right panel): Shows deposited treasures with progress (X/13). Hidden until first deposit.

**Mechanics:**
- Player deposits treasures by saying "put [treasure] in trophy case" while in `living_room`
- Treasures move from `inventory` to `flags.trophy_case`
- Player can retrieve treasures from the case if desired
- Victory triggers when all 13 treasures are in `flags.trophy_case`

### Light and Darkness (Grue Mechanic)

Some underground locations require a light source. The `Location` model has a `requires_light` boolean column (default: false).

**Light sources:**
- `brass_lantern` - found in living_room, can be turned on/off via `flags.lantern_lit`
- `ivory_torch` - found in torch_room, always lit when held

**Grue mechanic (handled by narrator via prompt rules):**
1. When player enters `requires_light: true` location without light → set `flags.in_darkness = true`, warn about grue
2. On next action if still in darkness → player dies, call `restart_game`
3. Lighting lantern clears `flags.in_darkness`

Dark locations are defined in `data/locations/*.json` with `"requires_light": true`. Currently ~22 underground locations are marked dark.

## Utility Scripts

| Script | Purpose |
|--------|---------|
| `scripts/create_admin.py` | Create first admin user interactively |
| `scripts/create_notification.py` | Create system notifications with TTL |
| `scripts/generate_invite.py` | Generate and print a new invite code |
| `scripts/reset_game_state.py` | Clear game states (soft reset) |
| `scripts/sync_locations.py` | Sync/prune location fixture data |
| `scripts/validate_config.py` | Validate configuration with optional DB check |
| `scripts/verify_movement.py` | Automated regression test for movement |
| `scripts/manage_dns.py` | Manage staging DNS A record in DNSimple (upsert/delete) |
| `scripts/publish_frontend_assets.py` | Upload frontend assets to DO Spaces CDN |

## Anthropic Python SDK

When working with the Anthropic Claude Python SDK, always search the web for the latest documentation as the API evolves frequently.

Documentation: https://docs.anthropic.com/en/api/client-sdks#python
