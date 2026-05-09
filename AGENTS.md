# Repository Guidelines

## Project Structure & Modules
- `app/` FastAPI backend and game logic: `api/` routes, `services/` orchestration, `repositories/` data access, `clients/` LLM + tools, `models/` ORM + schemas, `static/` web UI assets, `main.py` app entry.
- `frontend/` Vite frontend source (`frontend/src/`); builds to `frontend/dist/` which FastAPI serves when present (otherwise it falls back to `app/static/`).
- `prompts/` system prompts and renderer utilities; keep narrator tone consistent with `CLAUDE.md`.
- `skills/` skill instructions compiled into `prompts/skills_compiled.md` via `scripts/compile_skills.py`.
- `scripts/` utilities for admin/invite creation, validation, notifications, and resetting/seeding data.
- Location data lives in the database; `scripts/sync_locations.py` can ingest JSON under `data/locations/` (create/populate as needed when adding locations).
- `infra/` OpenTofu infrastructure and `k8s/` Kubernetes manifests; `docker-compose.yml` is for local Postgres.

## Setup, Run, Build
- `make setup` — create `venv` and install deps.
- `make install` — install deps into an existing `venv`.
- `make db-up` — start the local Postgres container.
- `make db-down` — stop local Postgres.
- `make db-migrate` — run Alembic migrations against local Postgres.
- `make run` — compile skills, sync locations, then start dev server on http://localhost:8000 with reload.
- `make dev` — one-shot setup + run; handy on fresh clones.
- `make frontend-install` / `make frontend-dev` — install deps and run Vite on http://localhost:5173.
- `make dev-full` — start backend + frontend dev servers together.
- `make frontend-build` — build Vite assets (used for staging/prod-style static serving).
- `make reset` — clear conversations/messages/game state while keeping location data.
- `make hard-reset` — drop and recreate tables, then re-seed locations from `data/locations/`.
- `make sync-locations` / `make sync-locations-prune` / `make sync-locations-check` — manage location fixtures.
- `make test` — run pytest + movement verification.
- `make invite` — generate a new invite code; see `make release-*`, `make infra-*`, and `make k8s-*` for deployment workflows.
- `make clean` — remove `venv` and Python caches.
Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY`. See `.env.example` for the full list (common: `DATABASE_URL`, `MODEL_NAME`, `AUTH_SECRET_KEY`, `DB_AUTO_CREATE`, `LLM_MAX_TOKENS`, `THINKING_EFFORT`, `SESSION_COOKIE_*`, `TURNSTILE_*`, `DEBUG_LLM`).

## Coding Style & Naming
- Python, PEP 8, 4-space indent; favor type hints on function signatures.
- Async-first: repositories/services/routes use `async def`; keep DB/LLM calls non-blocking.
- Keep new routes under `app/api/`, business logic in `app/services/`, persistence in `app/repositories/`.
- Name prompts and data files with kebab-case IDs matching in-game location IDs.

## Game Data, Prompts & Tools
- Locations are stored in DB tables (`Location`, `LocationExit`); use `GameRepository`/`LocationRepository` for access and `scripts/sync_locations.py` to load JSON fixtures when needed.
- Prompts live in `prompts/` (narrator + premise); use `render_prompt` helpers and follow narrator tone guidance in `CLAUDE.md`.
- Skills live in `skills/`; compile with `scripts/compile_skills.py` (or `make run`) to refresh `prompts/skills_compiled.md`.
- Tool schemas are in `app/clients/tools.py` with handlers in `app/services/game_tools.py`; keep names and shapes in sync across docs and code.

## Auth & Frontend
- Invite-only, session-cookie auth with CSRF: create admins via `scripts/create_admin.py` or `make create-admin`, generate codes with `scripts/generate_invite.py` or `make invite`, register at `/register.html`, and log in at `/login.html`.
- `/api/chat` streams SSE events (`start`, `delta`, `progress`, `done`, `error`, `restart`, `closing`) and requires a valid session cookie plus `x-csrf-token` for POSTs; the UI is served from `frontend/dist/` when built (otherwise `app/static/`).

## Testing Guidelines
- Minimal test suite exists; add `pytest` tests under `app/tests/` as you introduce features.
- For manual checks: start server (`make run`), create/login a user via the static pages, exercise chat streaming or POST `/api/chat`, and re-run `scripts/sync_locations.py`/`make hard-reset` after location changes to confirm lookup via repositories.
- `make test` runs pytest plus `scripts/verify_movement.py`; use a dedicated Postgres test database when adding async DB logic.

## Commit & Pull Requests
- Commits are short, imperative summaries (e.g., “Add tavern location,” “Refine narrator prompt”); keep body for rationale and key changes.
- PRs should include: brief overview, linked issue (if any), before/after notes for prompt or data changes, and test results or manual steps run.
- Screenshots/recordings encouraged when UI/UX in `frontend/` or `app/static/` changes; paste curl examples for new endpoints.

## Security & Configuration
- Never commit API keys; `.env` is gitignored. Use `.env.example` for new settings.
- Set a strong `AUTH_SECRET_KEY` for staging/production; the default dev secret is only for local use.
- If changing Anthropic models or tool schemas, document updates in `prompts/` or `CLAUDE.md` and ensure tool names stay in sync with `app/clients/tools.py`.
- Debug output is opt-in via env vars: `DEBUG_LLM` (LLM context + `.cursor/llm_debug.log`), `DEBUG_GAME_TOOLS` (tool handler prints + `.cursor/debug.log`), `DEBUG_SERVICE` (service JSON logs to `.cursor/service_debug.log`).
- Thinking configuration is controlled via env vars: `LLM_MAX_TOKENS`, `THINKING_EFFORT` (defaulted in `app/config.py`). The model uses adaptive thinking; `THINKING_EFFORT` accepts `low`, `medium`, `high`, `xhigh`, or `max` — `xhigh` is the recommended default for Opus 4.7 agentic workloads.
