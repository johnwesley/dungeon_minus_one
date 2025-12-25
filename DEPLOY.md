# Deployment Guide (Staging)

This guide covers the current staging deployment process. Production is not configured yet.

## 1. Release Strategy

We use a standard Git flow for releases:

1.  **Development**: All new features are merged into `main`.
2.  **Release Branch**: When feature-complete, create a branch `release/X.Y.Z` from `main`.
3.  **Staging (Beta)**:
    -   Create tags on the release branch: `vX.Y.Z-beta.1`, `vX.Y.Z-beta.2`, etc.
    -   Deploy these tags to the **Staging Environment** for testing.
4.  **Production (Future)**:
    -   Once stable, create the final tag `vX.Y.Z` on the release branch.
    -   Deploy this tag to the production environment (not yet configured).
    -   Merge the release branch back into `main`.

## 2. Prerequisites

Before running any deployment commands, ensure your `.env` file is present and valid. The deployment commands rely on these variables (e.g., `POSTGRES_DB`, `POSTGRES_USER`).

```bash
# Check your .env file
cat .env

# Source it if necessary (though Make usually handles env vars for docker-compose)
source .env
```

Ensure `ENVIRONMENT=staging`, `DB_AUTO_CREATE=false`, and a strong `AUTH_SECRET_KEY` are set for staging deployments.

Example `.env` values for staging (managed Postgres):

```bash
# Staging
ENVIRONMENT=staging
DB_AUTO_CREATE=false
DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>:5432/dungeon_staging
AUTH_SECRET_KEY=<staging-secret>
ANTHROPIC_API_KEY=<anthropic-key>
APP_IMAGE=registry.digitalocean.com/<registry>/dungeon-minus-one:<tag>
```

Note on `DB_AUTO_CREATE`: when set to `true`, the app runs `create_all()` at startup to auto-create tables. This is convenient for local dev but should be `false` in staging so migrations are the only schema source and multiple instances don't race at boot.

## 3. Deployment Steps

Perform these steps on the server for every release.

### Step 1: Choose Release Tag

Select the image tag you want to deploy (e.g., `v0.4.0-beta.1`).

### Step 2: Update Image and Restart

Update `APP_IMAGE` in `/opt/dungeon-minus-one/.env`, then restart the systemd unit (it pulls the image on start).

```bash
sudo systemctl restart dungeon-minus-one
```

**Note**: The container may crash or restart immediately after this step if the database schema is not yet updated. This is normal; proceed to the next step.

### Step 3: Database Schema Update

Run database migrations to ensure the schema matches the code.

```bash
docker compose -f /opt/dungeon-minus-one/docker-compose.staging.yml exec app alembic upgrade head
```

*   **Note**: This command is **idempotent**. It is safe to run even if there are no schema changes in this release; Alembic will simply do nothing.
*   **Troubleshooting**: If the `app` container is in a restart loop (preventing `exec`), use `run --rm` to apply the migration in a temporary container:
    ```bash
    docker compose -f /opt/dungeon-minus-one/docker-compose.staging.yml run --rm app alembic upgrade head
    ```

### Step 4: Sync Location Fixtures

Sync static location data (JSON files) into the database. This updates descriptions, exits, and item placements.

```bash
docker compose -f /opt/dungeon-minus-one/docker-compose.staging.yml exec app python scripts/sync_locations.py
```

### Step 5: Reset Player Sessions (Optional)

**Only performs this if the release requires it.**
Major gameplay changes (e.g., new mechanics, map restructuring) may require resetting active sessions to prevent broken states. This clears conversations and inventories but preserves user accounts.

```bash
docker compose -f /opt/dungeon-minus-one/docker-compose.staging.yml exec app python scripts/reset_game_state.py
```

## 4. Post-Deployment Verification

1.  **Health Check**: Ensure the service is responding.
    ```bash
    curl http://localhost:8080/health
    ```
2.  **Send Notification**: Notify players of the update.
    ```bash
    docker compose -f /opt/dungeon-minus-one/docker-compose.staging.yml exec app python scripts/create_notification.py "Update vX.Y.Z" "A new update has been deployed. Check the changelog!" --ttl 48
    ```

## 5. Troubleshooting

*   **Container Restart Loop**: If `systemctl restart dungeon-minus-one` leaves the app container restarting, it likely means the DB schema is mismatched. Run the migration step (Step 3) using `docker compose -f /opt/dungeon-minus-one/docker-compose.staging.yml run --rm ...`.
*   **"database does not exist"**: Check your `.env` file (`DATABASE_URL`) and verify the database exists in the managed cluster.
*   **"column does not exist"**: You skipped Step 3. Run `alembic upgrade head`.
