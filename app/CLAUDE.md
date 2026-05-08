# Application Architecture

> Part of the [project documentation](../CLAUDE.md). This file covers the Python backend and frontend application code.

## Layer Structure

```
app/
├── api/           # FastAPI route handlers
│   ├── router.py        # Aggregates all routes under /api prefix
│   ├── auth.py          # POST /api/auth/* (register, login, invite)
│   ├── chat.py          # POST /api/chat (SSE streaming with tools)
│   ├── conversations.py # CRUD endpoints for conversations
│   ├── game.py          # GET /api/game/* (game state endpoints)
│   ├── admin.py         # Admin dashboard + user/invite management API
│   └── notifications.py # Notification CRUD endpoints
├── services/      # Business logic
│   ├── conversation_service.py  # Orchestrates chat flow, emits StreamEvents
│   ├── game_tools.py    # Tool handlers for game state operations
│   ├── auth_service.py  # Password hashing, JWT token management
│   ├── session_service.py  # Session creation, validation, revocation
│   ├── invite_service.py   # Invite token creation and validation
│   ├── email_service.py    # Transactional emails via Postmark
│   ├── captcha_service.py  # Cloudflare Turnstile verification
│   └── rate_limit_service.py  # Fixed-window rate limiting
├── repositories/  # Data access (SQLAlchemy async)
│   ├── conversation_repository.py
│   ├── message_repository.py
│   ├── game_repository.py      # Game state + location data access
│   ├── location_repository.py  # Location CRUD operations
│   └── notification_repository.py  # Notification data access
├── clients/       # External API integrations
│   ├── llm_client.py    # Abstract LLMClient + AnthropicClient with tool support
│   └── tools.py         # Tool definitions for Claude
├── models/
│   ├── database.py      # SQLAlchemy ORM models (see Database section)
│   ├── schemas.py       # Pydantic request/response schemas
│   └── auth_schemas.py  # Pydantic auth schemas (UserLogin, UserRegister, Token)
├── utils/
│   ├── input_guard.py   # Player input validation (length, multi-command detection)
│   └── message_sanitizer.py  # Strip internal state/tool markers from output
├── config.py      # pydantic-settings configuration
├── database.py    # Async SQLAlchemy engine/session setup
├── main.py        # FastAPI app, lifespan, CORS, static files
├── metrics.py     # Prometheus counters/histograms (location entries, dwell time, victories)
├── connection_manager.py  # SSE connection tracking for graceful shutdown
└── static/        # Legacy frontend (fallback)

frontend/              # Vite + HTMX frontend
├── src/
│   ├── css/
│   │   ├── variables.css    # CSS custom properties (phosphor colors)
│   │   ├── bbs-base.css     # Core BBS/terminal aesthetic
│   │   ├── box-drawing.css  # Unicode box-drawing utilities
│   │   ├── scanlines.css    # CRT scanline effects
│   │   └── main.css         # Entry point
│   ├── js/
│   │   ├── auth.js          # JWT token management
│   │   ├── sse-handler.js   # SSE streaming for chat
│   │   └── main.js          # App entry point
│   └── pages/
│       ├── index.html       # Main game UI
│       ├── login.html       # Login page
│       └── register.html    # Registration page
├── vite.config.js           # Vite config with API proxy
└── package.json
```

## Key Patterns

- **Dependency Injection**: Route handlers use `Depends()` to inject database sessions and services
- **Repository Pattern**: Data access is abstracted through repository classes
- **Streaming**: Chat responses use SSE via `sse-starlette` with event types: `start`, `delta`, `done`, `error`, `progress`
- **Async Throughout**: All database operations and API calls use async/await
- **JWT Authentication**: Bearer token auth on protected endpoints

## Service Layer

| Service | Responsibility |
|---------|---------------|
| `conversation_service.py` | Core chat orchestration: message history windowing (last 20), tool resolution loop, state diff tracking, input guard integration, dev commands (`/warp`, `/save`, `/load`, `/reset`), NPC turn limits |
| `game_tools.py` | Tool handler implementations for `get_game_state`, `get_location_data`, `update_game_state`, `restart_game` |
| `auth_service.py` | Password hashing (bcrypt), JWT creation/validation, user lookup |
| `session_service.py` | Session token creation, validation, and revocation |
| `invite_service.py` | Invite token generation and redemption |
| `email_service.py` | Transactional emails via Postmark API (invite delivery) |
| `captcha_service.py` | Cloudflare Turnstile token verification (bypassed in dev when unconfigured) |
| `rate_limit_service.py` | Fixed-window rate limiting backed by `rate_limits` table |

## Repository Layer

| Repository | Responsibility |
|------------|---------------|
| `conversation_repository.py` | CRUD for conversations, `touch()` to update timestamps |
| `message_repository.py` | Create and list messages by conversation |
| `game_repository.py` | Game state read/update, location data access with exits |
| `location_repository.py` | Location CRUD, used by sync script |
| `notification_repository.py` | Notification CRUD with TTL and dismissal tracking |

## Client Layer

| Client | Responsibility |
|--------|---------------|
| `llm_client.py` | Abstract `LLMClient` base class + `AnthropicClient` implementation. Supports `chat_stream()` and `chat_stream_with_tools()` with real-time streaming. Uses prompt caching (`cache_control: ephemeral`). |
| `tools.py` | Tool schema definitions passed to Claude API (`get_game_state`, `get_location_data`, `update_game_state`, `restart_game`) |

## Utilities

| Utility | Responsibility |
|---------|---------------|
| `input_guard.py` | Validates player input: rejects inputs >1000 chars, detects multi-command inputs (e.g., "go north then take sword"). Returns `GuardResult` with `soft_reject` flag and reason. |
| `message_sanitizer.py` | Strips internal markers (`[State: ...]`, `[Tools used: ...]`) from assistant messages before sending to frontend |
| `connection_manager.py` | Tracks active SSE connections via `register()`/`unregister()`. Provides `shutdown_event` and `wait_for_connections_to_drain(timeout=30)` for graceful shutdown. |
| `metrics.py` | Prometheus metrics: `game_location_entries_total` (Counter), `game_location_dwell_seconds` (Histogram), `game_victories_total` (Counter) |

## Frontend Architecture

The frontend uses Vite + HTMX with a BBS/terminal aesthetic:

- **Vite**: Dev server with hot reload, proxies `/api` to FastAPI
- **HTMX**: Declarative AJAX for auth forms and conversation management
- **Hybrid SSE**: Custom JS handler for chat streaming (preserves backend format)
- **BBS Aesthetic**: Phosphor green/amber colors, box-drawing borders, scanline overlay

CSS custom properties in `variables.css`:
```css
--phosphor-green: #33ff33;  /* Primary text color */
--phosphor-amber: #ffb000;  /* User message color */
--terminal-bg: #0a0a0a;     /* Background */
```

The frontend auto-starts a new game if no conversations exist (sends "Wake up" message).

## Database

PostgreSQL via asyncpg. Tables auto-create on startup via `init_db()` in dev. Tables:

| Table | Description |
|-------|-------------|
| `users` | Player accounts (id, username, email, hashed_password, is_active, is_admin, expires_at, suspended_at, deleted_at) |
| `user_sessions` | Server-side BFF sessions (user_id FK, token_hash, expires_at, revoked_at, csrf_token_hash, ip, user_agent) |
| `invite_codes` | Registration gates (code, token_hash, invite_email, expires_at, is_used, used_at, used_by_user_id) |
| `invite_requests` | Access requests for admin approval (email, status [pending/approved/rejected], captcha_verified_at) |
| `conversations` | Chat sessions (tenant_id, user_id FK, title, timestamps) |
| `messages` | Chat messages (conversation_id FK, role, content, timestamp) |
| `game_states` | Player progress per conversation (current_location, inventory, visited_locations, player_stats, flags via MutableDict, dev_snapshot, location_entered_at) |
| `locations` | Static game world locations (id, name, description, interactables, npcs, requires_light) |
| `location_exits` | Connections between locations (source_id, target_id, direction) |
| `notifications` | System notifications with TTL (id, title, message, notification_type, expires_at) |
| `notification_dismissals` | Tracks user dismissals (notification_id FK, user_id FK, dismissed_at) |
| `rate_limits` | Rate limiting counters (key, count, window_start, expires_at) |

### Database Migrations

Alembic is used for database schema migrations:

```
alembic/
├── env.py              # Migration environment config
├── script.py.mako      # Template for new migrations
└── versions/           # Migration files
```

Commands:
```bash
alembic upgrade head     # Apply all pending migrations
alembic revision -m "description"  # Create new migration
```

## Configuration

Environment variables (via `.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | (required) | Claude API key |
| `DATABASE_URL` | `postgresql+asyncpg://dungeon:password@localhost:5432/dungeon` | Async database URL |
| `MODEL_NAME` | `claude-opus-4-7` | Claude model to use |
| `LLM_MAX_TOKENS` | `16000` | Max response tokens |
| `THINKING_EFFORT` | `xhigh` | Adaptive thinking effort level (`max`, `xhigh`, `high`, `medium`, `low`) |
| `DEBUG_LLM` | `false` | Log LLM metadata to `.cursor/llm_debug.log` |
| `auth_secret_key` | (has dev default) | JWT signing key |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` (7 days) | JWT expiration |
| `SKILLS_ENABLED` | (deprecated) | Skills now always compiled when present |
| `environment` | — | `dev`, `staging`, or `prod` |
| `trust_proxy_headers` | `false` | Trust X-Forwarded-For headers |
| `trusted_proxy_ips` | — | Comma-separated IPs/CIDRs for load balancer |
| `db_auto_create` | `true` | Auto-create schema on startup |
| `invite_ip_allowlist` | — | Comma-separated IPs allowed to generate invites |
| `invite_rate_limit_max` | `5` | Max invites per window |
| `invite_rate_limit_window_seconds` | `3600` | Rate limit window |

## Authentication

The application uses invite-only registration with JWT authentication.

### Flow

1. **Admin creates invite code**: `make invite` or via API (admin only)
2. **User registers**: Provides username, password, and valid invite code
3. **User receives JWT**: Token returned on successful registration/login
4. **Protected endpoints**: All chat/conversation endpoints require `Authorization: Bearer <token>`

### User Roles

- **Regular users**: Can play the game (chat, manage their conversations)
- **Admin users**: Can generate invite codes via API, manage users

Create the first admin user:
```bash
./venv/bin/python scripts/create_admin.py
```

## API Endpoints

### Authentication (no auth required)
- `POST /api/auth/register` - Register with invite code, returns JWT
- `POST /api/auth/login` - Login with credentials, returns JWT

### Admin Only
- `POST /api/auth/invite/generate` - Generate new invite code
- `POST /api/notifications` - Create new notification

### Admin Pages
- `GET /admin` - Unified admin dashboard (invite requests + user management)
- `GET /admin/invites` - Redirects to `/admin` (legacy URL)

### Admin API (requires admin role)
- `GET /api/admin/users?status={all|active|suspended|deleted}&search={query}` - List users
- `POST /api/admin/users/{id}/suspend` - Suspend user account
- `POST /api/admin/users/{id}/unsuspend` - Unsuspend user account
- `DELETE /api/admin/users/{id}` - Soft delete user
- `POST /api/admin/users/{id}/extend` - Extend account expiration
- `GET /api/admin/invite-requests?status={pending|approved|rejected}` - List invite requests
- `POST /api/admin/invite-requests/{id}/approve` - Approve request (optionally sends email)
- `POST /api/admin/invite-requests/{id}/reject` - Reject request

### Protected (requires Bearer token)
- `POST /api/chat` - Send message, returns SSE stream
- `GET /api/conversations` - List user's conversations
- `POST /api/conversations` - Create conversation
- `GET /api/conversations/{id}` - Get conversation with messages
- `GET /api/conversations/{id}/game-state` - Get game state for conversation
- `DELETE /api/conversations/{id}` - Delete conversation
- `GET /api/notifications` - Get active notifications for user
- `POST /api/notifications/{id}/dismiss` - Dismiss a notification

### Public (no auth)
- `GET /api/auth/dev-mode` - Check if dev auth bypass is enabled

### SSE Event Types

| Event | Description |
|-------|-------------|
| `start` | Stream started, contains `conversation_id` |
| `delta` | Content chunk |
| `progress` | Tool execution progress |
| `done` | Stream completed successfully |
| `error` | Error occurred |
| `closing` | Server shutting down (client should reconnect) |
