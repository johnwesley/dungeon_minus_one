# Production Deployment Guide (v0.3.0)

This guide covers the deployment steps for the v0.3.0 release, which adds the lantern/grue darkness mechanic.

## 1. Rebuild and Deploy

```bash
make prod-rebuild
```

This rebuilds the container with:
- Updated Python code (models, repositories)
- New Alembic migration
- Updated narrator prompt with grue rules
- Location fixtures with `requires_light` flags

## 2. Database Schema Update

A new column `requires_light` (Boolean) has been added to the `locations` table.

```bash
docker compose exec app alembic upgrade head
```

This applies migration `d9e5f6a7b8c9` which adds the `requires_light` column.

## 3. Sync Location Fixtures

The location fixtures now include `requires_light: true` for ~22 dark underground locations. Sync these to the database:

```bash
make prod-seed
```

This updates the `requires_light` values for all locations and verifies the sync.

## 4. Post-Deployment Verification

1. **Health Check**: `curl http://localhost:8080/health`
2. **Verify Migration**: Check that locations have the new column:
   ```bash
   docker compose exec app python -c "
   from app.database import async_session_factory
   from app.models.database import Location
   from sqlalchemy import select
   import asyncio

   async def check():
       async with async_session_factory() as s:
           loc = (await s.execute(select(Location).where(Location.id == 'cellar'))).scalar_one()
           print(f'cellar.requires_light = {loc.requires_light}')

   asyncio.run(check())
   "
   ```
   Should print `cellar.requires_light = True`

## 5. Gameplay Impact

- Players entering dark locations (cellar, maze, caves, etc.) without a lit lantern will receive a grue warning
- On their next action without light, they die and the game restarts
- Light sources: `brass_lantern` (must be turned on) or `ivory_torch` (always lit)

## 6. Troubleshooting

- **"column locations.requires_light does not exist"**: Run `alembic upgrade head`
- **Dark locations not marked correctly**: Run `sync_locations.py --verify`
- **Grue not triggering**: Check `prompts/narrator.md` has the Light and Darkness section
