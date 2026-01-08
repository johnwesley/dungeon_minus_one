# Auth + Invites (BFF sessions)

This document describes the account creation flow, admin approval process, and
required configuration for Turnstile + Postmark.

## Overview
- Authentication uses **server-side sessions** (cookie-based) instead of JWTs.
- Registration is **invite-only**.
- Invites are **email-bound**, **single-use**, and **expire after 24 hours** by default.
- Accounts expire after **7 days** by default (admins can be non-expiring).
- Session idle timeout defaults to **4 hours**.

## Account Creation Flow
1) **Request access**
   - User submits their email in the **Request Access** form on `/login.html`.
   - Client sends `POST /api/auth/invite-request` with `{ email, turnstile_token }`.
   - Server verifies Turnstile (when configured) and stores an `InviteRequest` as `pending`.

2) **Admin approval**
   - Admin opens the approvals UI and reviews pending requests.
   - On approve, the server creates a **single-use invite token** bound to the request email.
   - If `INVITE_EMAIL_SEND_MODE=auto` and the admin chooses “send email,” the invite is sent via Postmark.
   - If `INVITE_EMAIL_SEND_MODE=manual`, the UI returns the token for manual delivery.

3) **User registers**
   - User visits `/register.html` and submits `{ invite_token, username, password }`.
   - Server validates the invite (unused + not expired + email bound).
   - User is created with:
     - `email` + `email_normalized` from the invite
     - `username` from the form
     - `expires_at = now + 7 days` (unless non-expiring)
   - Server issues a session cookie + CSRF token.

4) **User logs in**
   - Login accepts **username OR email** plus password.
   - Server issues a new session cookie + CSRF token on success.

## Admin Approvals UI
- **App-served (staging/prod and local when using FastAPI static)**:
  - `/admin/invites`
- **Vite dev server**:
  - `http://localhost:5173/admin-invites.html`

## Session + CSRF
- Session cookie name: `session`
- Cookie flags: `HttpOnly`, `SameSite=Lax`, `Secure=true` in staging/prod
- CSRF token is required for `POST/PUT/PATCH/DELETE` and is sent via `X-CSRF-Token`.

## Required Env Vars (staging/prod)
```
ENVIRONMENT=staging
AUTH_SECRET_KEY=...
SESSION_COOKIE_SECURE=true
PUBLIC_APP_URL=https://staging.dungeonminusone.com

TURNSTILE_SITE_KEY=...
TURNSTILE_SECRET_KEY=...

POSTMARK_SERVER_TOKEN=...
POSTMARK_FROM_EMAIL=...
POSTMARK_MESSAGE_STREAM=outbound
INVITE_EMAIL_SEND_MODE=auto
```

Optional:
```
SESSION_COOKIE_DOMAIN=
SESSION_COOKIE_SAMESITE=Lax
SESSION_ABSOLUTE_TTL_DAYS=
ALLOW_INDEFINITE_INVITES=false
DEFAULT_ACCOUNT_EXPIRES=true
```

## Turnstile Setup (Cloudflare)
1) Create a new Turnstile site in Cloudflare.
2) Add the production domain (`dungeonminusone.com`) and staging domain (`staging.dungeonminusone.com`).
3) Choose “Managed” widget type (recommended default).
4) Copy **Site Key** and **Secret Key** into env vars:
   - `TURNSTILE_SITE_KEY`
   - `TURNSTILE_SECRET_KEY`

## Postmark Setup
1) Create a Postmark account and create a **Server**.
2) Verify a **Sender Signature** or domain, and pick a From address.
3) Copy the **Server API Token** and From address into env vars:
   - `POSTMARK_SERVER_TOKEN`
   - `POSTMARK_FROM_EMAIL`
4) Set `PUBLIC_APP_URL` so invite links point to the correct environment.
5) Set `INVITE_EMAIL_SEND_MODE=auto` to enable automatic email sends.

## Local Development
- Use `INVITE_EMAIL_SEND_MODE=manual` so invite tokens are returned for manual copy/paste.
- Turnstile is optional locally; if `TURNSTILE_SECRET_KEY` is blank, captcha checks are skipped.

Common local commands:
```
# Create admin
python scripts/create_admin.py admin yourpassword --email admin@example.com

# Generate invite (manual mode prints token)
make invite EMAIL="player@example.com"
```

## Manual Invites (no email service)
Manual invites work without Postmark as long as `INVITE_EMAIL_SEND_MODE=manual`.

Flow:
1) Generate an invite token bound to the player’s email:
```
make invite EMAIL="player@example.com"
```
2) Send the token to the player out-of-band.
3) Player registers at `/register.html` (or `/register.html?invite_token=...`).
4) Player can log in with **email or username**.

Note: In staging/prod, Turnstile keys are still required because captcha enforcement is enabled.

## Staging Reset (after deployment)
```
make k8s-auth-reset FORCE=true
make k8s-create-admin USERNAME="admin" PASSWORD="pass" EMAIL="admin@example.com"
make k8s-invite EMAIL="player@example.com"
```
