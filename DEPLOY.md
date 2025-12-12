# Production Deployment Guide (v0.2.0)

This guide covers the deployment steps for the v0.2.0 release, specifically addressing new features and database schema changes.

## 1. Database Schema Update

We have added a new column `dev_snapshot` (JSON) to the `game_states` table to support development testing features.

### Option A: Clean Rebuild (Recommended for v0.2.0)
Since we are in early development, the simplest way to apply the schema change is to wipe the production database and let it rebuild.

**Warning: This deletes all existing production game data.**

```bash
# On the production server:
docker compose down -v
docker compose up -d --build
make prod-seed  # Re-seed location data
```

### Option B: Manual Migration (Preserve Data)
If you need to preserve existing user data, you must manually alter the database table because we are not using an automated migration tool (like Alembic) yet.

```bash
# On the production server:
docker compose exec db psql -U postgres -d chat_db -c "ALTER TABLE game_states ADD COLUMN dev_snapshot JSONB;"
```
*(Replace `postgres`, `chat_db` with your actual POSTGRES_USER/DB env vars if different).*

## 2. Environment Variables

Ensure your production `.env` file is up to date.

-   **`GAME_ENV`**: Set to `production` (optional, but good practice if we add strict environment gating later).
-   **`AUTH_SECRET_KEY`**: Ensure this is a strong, random string.

## 3. Post-Deployment Verification

1.  **Health Check**: Ensure the app is running (`curl http://localhost:8080/health` or check logs).
2.  **Seed Data**: Verify locations are loaded.
3.  **Admin Access**: If you need to use `/teleport` or `/save` in production (not recommended, but possible), you must explicitly create an admin user:
    ```bash
    docker compose exec app python scripts/create_admin.py <username> <password>
    ```

## 4. Troubleshooting

-   **"Internal Server Error" on Chat**: Likely a schema mismatch. Check logs for `UndefinedColumn: column game_states.dev_snapshot does not exist`. Run the migration steps above.
-   **"Unauthorized" on Dev Commands**: Ensure the user has `is_admin=True` in the database.

