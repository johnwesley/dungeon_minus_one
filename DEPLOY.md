# Production Deployment Guide (v0.3.0)

This guide covers the deployment steps for the v0.3.0 release, which adds the lantern/grue darkness mechanic.

## 0. Prerequisite: Environment Variables

Before running any deployment commands, ensure your `.env` file is sourced or that your environment variables are correctly loaded. The deployment commands rely on these variables (like `POSTGRES_DB` and `POSTGRES_USER`).

```bash
# Check your .env file
cat .env

# Source it if necessary
source .env
```

## 1. Checkout Release

Ensure you are on the correct release tag:

```bash
git fetch --tags
git checkout v0.3.0
```

## 2. Rebuild and Deploy

```bash
make prod-rebuild
```

This rebuilds the container with updated code/assets.
**Note**: The container may crash or restart immediately after this step if the database schema is not yet updated. This is normal; proceed to the next step.

## 3. Database Schema Update

A new column `requires_light` (Boolean) has been added to the `locations` table.

```bash
docker compose exec app alembic upgrade head
```

**Troubleshooting**: If the `app` container is in a restart loop (preventing `exec`), use `run --rm` to apply the migration in a fresh, one-off container:
```bash
docker compose -f docker-compose.prod.yml run --rm app alembic upgrade head
```

This applies migration `d9e5f6a7b8c9`.

## 4. Sync Location Fixtures

The location fixtures now include `requires_light: true` for ~22 dark underground locations. Sync these to the database:

```bash
make prod-seed
```

This updates the `requires_light` values for all locations.

## 5. Reset Player Sessions

To clear all active game sessions (conversations, messages, inventory) while preserving registered users:

```bash
make prod-reset
```

This is necessary for ensuring all players start fresh with the new mechanics (e.g. grue/light rules) and updated world state.

## 6. Post-Deployment Verification

1. **Health Check**: `curl http://localhost:8080/health`
2. **Verify Migration**: Run a direct SQL query to check the `cellar` location.

   ```bash
   # Use the user/db from your .env (e.g., -U dungeon_user -d dungeon_db)
   docker compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT id, requires_light FROM locations WHERE id = 'cellar';"
   ```

   **Expected Output**:
   ```
      id   | requires_light
   --------+----------------
    cellar | t
   ```

## 7. Send Release Notification

Notify players of the update and the session reset:

```bash
make prod-notify TITLE="Update v0.3.0: Darkness & Personalities" MSG="Darkness has fallen deep underground—bring a light or face the Grue! Also, some dungeon inhabitants seem to have developed... strong opinions about game design. Your session has been reset." TTL=48
```

## 8. Gameplay Impact

- Players entering dark locations (cellar, maze, caves, etc.) without a lit lantern will receive a grue warning
- On their next action without light, they die and the game restarts
- Light sources: `brass_lantern` (must be turned on) or `ivory_torch` (always lit)

## 9. Troubleshooting

- **Container Restart Loop**: If `prod-rebuild` leaves the app container restarting, it likely means the DB schema is mismatched. Run the migration step (Step 3) using `docker compose run --rm ...`.
- **"database does not exist"**: Check your `.env` file (`POSTGRES_DB` vs `POSTGRES_USER`). If you changed the DB name after initial creation, you may need to update `.env` to match the existing volume's DB name.
- **"column locations.requires_light does not exist"**: Run `alembic upgrade head`.
