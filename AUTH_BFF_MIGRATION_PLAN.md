# Auth + Invite Hardening Plan (BFF, short-lived accounts)

This file is an implementation plan for migrating the app from SPA-stored JWTs
to a BFF session model, with 24h email-bound invites, single-use redemption,
7-day account lifetimes, and 2-4 hour session idle timeouts. It also includes
support for non-expiring accounts (e.g., admins), indefinite invites (explicit),
and account suspension/deletion.

## Requirements (fixed)
- Invite code TTL: 24 hours
- Invite usage: single-use, bound to email
- Account lifetime: 7 days (hard disable on expiry, no recovery)
- Session idle timeout: 2-4 hours (configurable, default 4 hours)
- No reverse proxy/WAF protections assumed
## Requirements (options)
- Non-expiring accounts supported (e.g., admins): `expires_at = NULL`
- Indefinite invites supported only when explicitly requested/admin-created
- Suspend and delete accounts (immediate access removal)

---

## Chunk 0: Scope + config wiring
Goal: centralize new auth/session/invite TTL settings.

Tasks:
- Add config entries in `app/config.py`:
  - `invite_ttl_hours = 24`
  - `account_ttl_days = 7`
  - `session_idle_timeout_minutes = 240`
  - `session_cookie_name = "session"`
  - `session_cookie_secure = True` (override for local dev)
  - `session_cookie_samesite = "Lax"` (or "Strict")
  - `session_cookie_domain` (optional)
  - `session_absolute_ttl_days` (optional if you want absolute session cap)
  - `allow_indefinite_invites = false` (optional guardrail)
  - `default_account_expires = true` (optional guardrail)
- Add config validation for staging/prod:
  - Fail startup if `dev_auth_bypass` is True outside dev.
  - Fail startup if `auth_secret_key` remains default (still used for invite HMAC or CSRF).

Files:
- `app/config.py`
- `app/main.py` (if validation is located there)

Acceptance:
- App boots in dev with defaults, but fails in staging/prod if `dev_auth_bypass` is true.

---

## Chunk 1: Data model updates (Invite + User + Sessions)
Goal: support email-bound single-use invites, account TTL, non-expiring accounts,
account suspension/deletion, and server-side sessions.

Tasks:
1) Update `InviteCode` model in `app/models/database.py`:
   - Add `invite_email` (String, index, required).
   - Add `token_hash` (String, unique, index, required).
   - Add `expires_at` (DateTime, index, nullable) for optional indefinite invites.
   - Add `sent_at` (DateTime, nullable).
   - Add `revoked_at` (DateTime, nullable).
   - Keep `is_used`, `used_at`, `used_by_user_id`.
2) Update `User` model in `app/models/database.py`:
   - Add `expires_at` (DateTime, index, nullable) for non-expiring accounts.
   - Add `suspended_at` (DateTime, nullable).
   - Add `suspended_reason` (String/Text, nullable).
   - Add `deleted_at` (DateTime, nullable) for soft delete.
   - Ensure `email` is stored and unique for invite-created accounts.
3) Add new `UserSession` model in `app/models/database.py`:
   - `id` (String, primary key) -> random session id
   - `user_id` (FK)
   - `created_at`, `last_seen_at`, `expires_at`, `revoked_at`
   - `csrf_token_hash`
   - `ip`, `user_agent` (optional)
   - Indexes on `user_id`, `expires_at`, `revoked_at`.

4) Create alembic migration(s) in `alembic/versions/`.

Files:
- `app/models/database.py`
- `alembic/versions/*.py`

Acceptance:
- Migrations apply cleanly; new tables/columns exist.

---

## Chunk 2: Session service (BFF core)
Goal: create, validate, update, and revoke sessions with idle timeouts.

Tasks:
- Add a `SessionService` in `app/services/session_service.py`:
  - `create_session(user_id, ip, user_agent) -> session_id, csrf_token`
  - `validate_session(session_id) -> user or None`
    - Check `revoked_at` is null.
    - Check `expires_at` (absolute) if used.
    - Check idle timeout: `now - last_seen_at <= session_idle_timeout_minutes`.
    - If invalid: revoke + return None.
    - If valid: update `last_seen_at`.
  - `revoke_session(session_id)`.
- Store session id in cookie; store CSRF token hash in DB.
- If session is invalid due to idle timeout or account expiration, delete/revoke it.

Files:
- `app/services/session_service.py`
- `app/repositories/` (optional session repo)

Acceptance:
- Unit-level checks: sessions expire on idle timeout and are revoked on invalidation.

---

## Chunk 3: Auth dependency (replace JWT)
Goal: enforce auth based on BFF sessions + account expiry.

Tasks:
- Replace `get_current_user` logic in `app/api/auth.py`:
  - Read session cookie (`session_cookie_name`).
  - Validate via `SessionService`.
  - Enforce `user.expires_at` only when set (non-expiring accounts skip this).
  - Ensure `user.is_active` is true and `user.suspended_at` is null.
  - Ensure `user.deleted_at` is null.
  - On failure, raise 401 and clear cookie.
- Remove JWT decode and OAuth2PasswordBearer dependencies.
- Remove dev bypass logic in non-dev or guard it with config validation.

Files:
- `app/api/auth.py`
- `app/services/auth_service.py` (JWT functions can remain if still used elsewhere, but unused ones can be removed)

Acceptance:
- All protected endpoints require a valid session cookie.
- Expired users get 401 and session is revoked.

---

## Chunk 4: Auth endpoints (login/logout/session/csrf)
Goal: endpoints for BFF sessions + CSRF.

Tasks:
- Update `POST /api/auth/login`:
  - Verify username/password (bcrypt ok for now).
  - Deny if `user.expires_at < now` (skip if null).
  - Deny if `user.suspended_at` or `user.deleted_at` is set.
  - Create session + set cookie.
  - Return minimal user info.
- Add `POST /api/auth/logout`:
  - Revoke session + clear cookie.
- Add `GET /api/auth/session`:
  - Return `{authenticated, username, account_expires_at, session_expires_at}`.
- Add `GET /api/auth/csrf` (or include CSRF token in `/session`):
  - Issue CSRF token for header usage.
- Ensure cookie flags: HttpOnly, Secure (staging/prod), SameSite.

Files:
- `app/api/auth.py`
- `app/services/session_service.py`

Acceptance:
- Browser can authenticate without storing tokens in JS.
- Logout removes server-side session.

---

## Chunk 5: Invite flow (email-bound, 24h TTL, single-use)
Goal: enforce the invite lifecycle and binding to email.

Tasks:
- Update `POST /api/auth/invite/generate`:
  - Require admin.
  - Input: email, `never_expires` (optional, default false).
  - Generate random invite token (>=128 bits).
  - Store only hash + `invite_email` + `expires_at = now + 24h` unless `never_expires`.
  - Send email containing the invite token (via existing SMTP).
- Update `POST /api/auth/register`:
  - Input: `invite_token`, `username`, `password`.
  - Hash token and find invite where:
    - `token_hash` matches
    - `expires_at > now` or `expires_at` is null
    - `is_used = false`
    - `revoked_at` is null
  - Create user with `email = invite.invite_email` and `expires_at = now + 7 days`.
  - Mark invite used.
  - Create session cookie and return user info.
- Explicitly reject expired or already-used invites.

Files:
- `app/api/auth.py`
- `app/models/database.py`
- `app/services/email_service.py` (if used for invite mails)

Acceptance:
- Invite can be redeemed once, within 24 hours, and only creates a 7-day account.
- If `never_expires` is set, invite remains valid until used or revoked.

---

## Chunk 6: Admin lifecycle controls (suspend/delete/extend)
Goal: allow admins to suspend/delete users and revoke/extend invites.

Tasks:
- Add admin-only endpoints:
  - `POST /api/admin/users/{id}/suspend` -> set `suspended_at`, `is_active = false`, revoke sessions.
  - `POST /api/admin/users/{id}/unsuspend` -> clear `suspended_at`, set `is_active = true`.
  - `DELETE /api/admin/users/{id}` -> set `deleted_at`, revoke sessions.
  - `POST /api/admin/users/{id}/extend` -> set `expires_at` (or null for non-expiring).
  - `POST /api/admin/invites/{id}/revoke` -> set `revoked_at`.
  - `POST /api/admin/invites/{id}/extend` -> set `expires_at` or null.
- Add DB queries for session revocation by user id.

Files:
- `app/api/admin.py` (new) or `app/api/auth.py` (if keeping in one file)
- `app/services/session_service.py`
- `app/models/database.py`

Acceptance:
- Suspended/deleted users lose access immediately.
- Admin can extend or revoke invites and set non-expiring accounts.

---

## Chunk 7: Rate limiting (login/register)
Goal: enforce brute-force and abuse protections without WAF.

Tasks:
- Extend `app/services/rate_limit_service.py` with generic helpers:
  - `enforce_login_rate_limit(ip, username)`
  - `enforce_register_rate_limit(ip, invite_token_hash)`
- Use per-IP + per-identifier buckets.
- Enforce in `POST /api/auth/login` and `POST /api/auth/register`.

Files:
- `app/services/rate_limit_service.py`
- `app/api/auth.py`

Acceptance:
- Repeated failures hit 429; thresholds are configurable.

---

## Chunk 8: Frontend migration to BFF
Goal: remove localStorage tokens and use cookie-backed sessions.

Tasks:
- Update `frontend/src/js/auth.js`:
  - Remove localStorage token methods.
  - Replace `fetchWithAuth` to include `credentials: 'same-origin'`.
  - Add CSRF header for POST/PUT/DELETE.
  - `checkDevMode` can be removed if dev bypass is removed.
- Update `frontend/src/login.html` + `register.html`:
  - On success, redirect without storing token.
- Update `frontend/src/js/sse-handler.js`, `frontend/src/js/main.js`:
  - Remove Bearer header usage.
  - Ensure `fetch` uses cookies.
- If using legacy `app/static/*`, duplicate these changes there or remove legacy assets.

Files:
- `frontend/src/js/auth.js`
- `frontend/src/login.html`
- `frontend/src/register.html`
- `frontend/src/js/main.js`
- `frontend/src/js/sse-handler.js`
- `app/static/*` (if still served)

Acceptance:
- UI works without tokens in localStorage.

---

## Chunk 9: Cleanup + validation
Goal: align startup rules and remove dead paths.

Tasks:
- Ensure `dev_auth_bypass` is enforced as dev-only.
- Remove JWT usage from auth dependency (if not used elsewhere).
- Add migration/cleanup job for expired invites/sessions (optional).
- Update `README.md` with new auth flow and config settings.

Files:
- `app/main.py`
- `app/api/auth.py`
- `README.md`

Acceptance:
- Staging config is safe by default and matches requirements.

---

## Suggested manual checks
- Login + chat flow works end-to-end with cookies only.
- Invite expires after 24 hours (manual time change or DB update).
- Account expires after 7 days and access is denied immediately.
- Session idle timeout forces re-login after 4 hours of inactivity.
- Rate limits trigger 429 for brute-force attempts.
- Suspended users are denied immediately.
- Non-expiring admin accounts remain accessible.
- Indefinite invites work only when explicitly requested and not revoked.

---

## Notes for the next agent
- Keep all auth/session logic async.
- Prefer storing hashes (invite tokens, CSRF tokens).
- Avoid storing auth tokens in browser storage.
- Use secure cookie attributes in staging/prod.
