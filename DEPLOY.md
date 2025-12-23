# Deployment Guide

This guide covers the standard deployment process for Dungeon Minus One, using a release-branch workflow for Staging and Production.

## 1. Release Strategy

We use a standard Git flow for releases:

1.  **Development**: All new features are merged into `main`.
2.  **Release Branch**: When feature-complete, create a branch `release/X.Y.Z` from `main`.
3.  **Staging (Beta)**:
    -   Create tags on the release branch: `vX.Y.Z-beta.1`, `vX.Y.Z-beta.2`, etc.
    -   Deploy these tags to the **Staging Environment** for testing.
4.  **Production**:
    -   Once stable, create the final tag `vX.Y.Z` on the release branch.
    -   Deploy this tag to the **Production Environment**.
    -   Merge the release branch back into `main`.

## 2. Prerequisites

Before running any deployment commands, ensure your `.env` file is present and valid. The deployment commands rely on these variables (e.g., `POSTGRES_DB`, `POSTGRES_USER`).

```bash
# Check your .env file
cat .env

# Source it if necessary (though Make usually handles env vars for docker-compose)
source .env
```

Ensure `ENVIRONMENT=staging` or `ENVIRONMENT=prod`, `DB_AUTO_CREATE=false`, and a strong `AUTH_SECRET_KEY` are set for non-dev deployments.

Example `.env` values for a single managed Postgres cluster with two databases:

```bash
# Staging
ENVIRONMENT=staging
DB_AUTO_CREATE=false
DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>:5432/dungeon_staging
AUTH_SECRET_KEY=<staging-secret>
```

```bash
# Production
ENVIRONMENT=prod
DB_AUTO_CREATE=false
DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>:5432/dungeon_prod
AUTH_SECRET_KEY=<prod-secret>
```

Note on `DB_AUTO_CREATE`: when set to `true`, the app runs `create_all()` at startup to auto-create tables. This is convenient for local dev but should be `false` in staging/prod so migrations are the only schema source and multiple instances don't race at boot.

## 3. Deployment Steps

Perform these steps on the server for every release.

### Step 1: Checkout Release Tag

Fetch the latest tags and checkout the specific version you are deploying (e.g., `v0.4.0` or `v0.4.0-beta.1`).

```bash
git fetch --tags
git checkout vX.Y.Z
```

### Step 2: Rebuild Containers

Rebuild the application container with the updated code and assets.

```bash
make prod-rebuild
```

**Note**: The container may crash or restart immediately after this step if the database schema is not yet updated. This is normal; proceed to the next step.

### Step 3: Database Schema Update

Run database migrations to ensure the schema matches the code.

```bash
docker compose exec app alembic upgrade head
```

*   **Note**: This command is **idempotent**. It is safe to run even if there are no schema changes in this release; Alembic will simply do nothing.
*   **Troubleshooting**: If the `app` container is in a restart loop (preventing `exec`), use `run --rm` to apply the migration in a temporary container:
    ```bash
    docker compose -f docker-compose.prod.yml run --rm app alembic upgrade head
    ```

### Step 4: Sync Location Fixtures

Sync static location data (JSON files) into the database. This updates descriptions, exits, and item placements.

```bash
make prod-seed
```

### Step 5: Reset Player Sessions (Optional)

**Only performs this if the release requires it.**
Major gameplay changes (e.g., new mechanics, map restructuring) may require resetting active sessions to prevent broken states. This clears conversations and inventories but preserves user accounts.

```bash
make prod-reset
```

## 4. Post-Deployment Verification

1.  **Health Check**: Ensure the service is responding.
    ```bash
    curl http://localhost:8080/health
    ```
2.  **Send Notification**: Notify players of the update.
    ```bash
    make prod-notify TITLE="Update vX.Y.Z" MSG="A new update has been deployed. Check the changelog!" TTL=48
    ```

## 5. Troubleshooting

*   **Container Restart Loop**: If `prod-rebuild` leaves the app container restarting, it likely means the DB schema is mismatched. Run the migration step (Step 3) using `docker compose run --rm ...`.
*   **"database does not exist"**: Check your `.env` file (`POSTGRES_DB` vs `POSTGRES_USER`).
*   **"column does not exist"**: You skipped Step 3. Run `alembic upgrade head`.
