# Production Deployment Guide (v0.2.0)

This guide covers the deployment steps for the v0.2.0 release, specifically addressing new features and database schema changes.

## 1. Database Schema Update

We have added a new column `dev_snapshot` (JSON) to the `game_states` table. We use **Alembic** for migrations.

### Automated Migration (Recommended)
This will upgrade the database schema while **preserving all existing data**.

```bash
# On the production server:
docker compose exec app alembic upgrade head
```

*(Note: If this is the very first deploy with Alembic, and you have existing tables, Alembic might try to create them again. In that case, you may need to 'stamp' the current state first, but since this is v0.2.0, assuming a fresh or compatible state is safer. If tables exist, run `alembic stamp head` locally first to verify).*

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

