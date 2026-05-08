# Dungeon Minus One

A text-adventure game narrated by Claude. Explore an underground facility, recover forgotten treasures, and try not to get eaten by a grue.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Sponsor](https://img.shields.io/badge/Sponsor-%E2%9D%A4-pink)](https://github.com/sponsors/johnwesley)

**[Play Now at dungeonminusone.com](https://dungeonminusone.com)**

## The Game

The game is live and playable right now. You type commands, Claude narrates what happens — with a blunt, mildly cynical voice that guides you through a forgotten underground facility. The UI is a retro CRT terminal with phosphor green text, scanline effects, and a three-panel layout: game chat in the center, location and inventory on the right, controls on the left.

The premise: an underground facility was built to preserve cultural artifacts indefinitely, but funding vanished and its original purpose was forgotten. You're not a hero — you're just present. Your task is to explore below, recover items of residual value, and deposit them in the trophy case in the house above.

The world is based on the classic Zork map — 72 locations, 13 treasures, NPCs, locks, a dam, dark rooms, and a grue — so development could focus on the mechanics of an AI-narrated game rather than world building. There are NPCs who guard passages, locks that need keys, a dam that controls water levels, dark rooms where a grue waits, and a narrator who understands every parser command you throw at it.

## Quick Start

```bash
git clone https://github.com/johnwesley/dungeon_minus_one.git
cd dungeon_minus_one
make setup
make db-up
cp .env.example .env  # Add your ANTHROPIC_API_KEY
make dev-full          # http://localhost:5173
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Browser ↔ FastAPI :8000 ↔ Postgres                         │
│                 ↓                                           │
│           Anthropic API (Claude)                            │
└─────────────────────────────────────────────────────────────┘
```

- **Backend**: FastAPI with streaming SSE responses, SQLAlchemy + Alembic, Postgres
- **Frontend**: Vite + HTMX with a CRT terminal aesthetic
- **AI**: Anthropic Claude with tool use for game state management

## Game Features

- **72 interconnected locations** with rich descriptions and interactable elements
- **13 collectible treasures** to find and deposit in the trophy case
- **Darkness and grue** — ~22 underground locations require a light source or you die
- **NPC guards** that block passages until you defeat, persuade, or distract them
- **Locks and keys** — grating, dam controls, and environmental puzzles
- **Environmental mechanics** — water levels, gas room hazards, written materials to read
- **Skills system** — 10 modular game mechanics loaded as prompt instructions at runtime
- **Tool use** — Claude manages game state through structured tool calls, not free-form text
## Project Structure

```
app/               # Python backend (FastAPI, services, repositories)
frontend/          # Vite + HTMX frontend
prompts/           # System prompt markdown files
skills/            # Game mechanic skill files
data/locations/    # Location fixture JSON files (72 files)
scripts/           # Utility scripts
alembic/           # Database migrations
infra/             # OpenTofu (Terraform) — DigitalOcean cluster, Spaces, networking
k8s/               # Kubernetes manifests (base + staging + prod overlays)
docs/              # Architecture docs (auth, etc.); spoilers/ holds walkthroughs
```

## Useful Commands

| Command | Description |
|---------|-------------|
| `make dev-full` | Start backend + frontend with hot reload |
| `make setup` | Create venv and install dependencies |
| `make db-up` / `make db-down` | Start / stop local Postgres |
| `make db-migrate` | Run database migrations |
| `make reset` | Clear game state (keep locations) |
| `make hard-reset` | Wipe DB and re-seed locations |
| `make sync-locations` | Sync location fixtures from `data/locations/` |
| `make verify-movement` | Run movement regression test |
| `make invite` | Generate an invite code |
| `make frontend-build` | Build frontend for production |
| `make validate-config` | Validate configuration |

## Deployment

The repo includes a full reference deployment for DigitalOcean Kubernetes (DOKS) under `infra/` (OpenTofu) and `k8s/` (Kustomize overlays). The same Docker image runs locally, in staging, and in production; runtime secrets are pulled at startup via Doppler.

### Docker (any host)

```bash
docker build -t dungeon-minus-one .
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dungeon \
  -e ANTHROPIC_API_KEY=sk-... \
  dungeon-minus-one
```

### DigitalOcean Kubernetes (reference)

```bash
make infra-init && make infra-apply        # Provision DOKS, Spaces, networking
make k8s-setup-staging                     # Namespace + Doppler + DNS bootstrap
make docker-release                        # Build + push image to DOCR
make k8s-deploy K8S_ENV=staging            # Apply manifests, roll out
```

See `infra/README.md` and `k8s/CLAUDE.md` for the long-form runbooks.

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions and guidelines.

## Sponsors

If you enjoy the game, consider [sponsoring the project](https://github.com/sponsors/johnwesley).

## License

[MIT](LICENSE)
