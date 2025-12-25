# Deployment Checklist

Lessons learned from v0.2.0 deployment issues. Use this checklist to prevent and detect common deployment problems.

## Pre-Deployment Checks

### Docker Image Verification
- [ ] Build image locally and verify all required files are present:
  - `alembic.ini`
  - `alembic/` directory
  - `data/` directory
- [ ] Run `docker compose -f /opt/dungeon-minus-one/docker-compose.staging.yml exec app alembic current` to verify Alembic is configured

### Database Migrations
- [ ] Review pending migrations with `alembic upgrade head --sql` (dry run)
- [ ] Never use `alembic stamp` in staging without verifying schema matches
- [ ] After migration, verify columns exist: `\d table_name` in psql

### Environment Variables
- [ ] Verify `.env` file has all required variables
- [ ] Confirm `APP_IMAGE`, `DATABASE_URL`, `ANTHROPIC_API_KEY`, `AUTH_SECRET_KEY` are set

## Deployment Steps

```bash
# 1. Update APP_IMAGE to the new tag
sudo sed -i 's/^APP_IMAGE=.*/APP_IMAGE=registry.digitalocean.com\\/your-registry\\/dungeon-minus-one:<tag>/' /opt/dungeon-minus-one/.env

# 2. Pull latest image
sudo systemctl restart dungeon-minus-one

# 3. Run migrations (verify first!)
docker compose -f /opt/dungeon-minus-one/docker-compose.staging.yml exec app alembic upgrade head --sql  # Preview
docker compose -f /opt/dungeon-minus-one/docker-compose.staging.yml exec app alembic upgrade head        # Apply

# 4. Verify deployment
docker compose -f /opt/dungeon-minus-one/docker-compose.staging.yml logs --tail=50 app
```

## Post-Deployment Verification

### Smoke Test
- [ ] Load the application in browser
- [ ] Start a new game
- [ ] Verify location displays correctly (not "Unknown")
- [ ] Send a chat message and receive a response

### Database Checks
```bash
# Verify locations loaded (expects no diffs)
docker compose -f /opt/dungeon-minus-one/docker-compose.staging.yml exec app python scripts/sync_locations.py --dry-run --prune

# Verify schema is at head
docker compose -f /opt/dungeon-minus-one/docker-compose.staging.yml exec app alembic current
```

## Troubleshooting

### "InFailedSQLTransactionError"
**Cause:** A previous query in the transaction failed, cascading to subsequent queries.
**Solution:**
1. Check logs for the *original* error (scroll up past the cascade)
2. Often caused by missing columns - verify schema
3. Restart the app: `sudo systemctl restart dungeon-minus-one`

### "column X does not exist"
**Cause:** Migration didn't run or was stamped without applying.
**Solution:**
```bash
# Add missing column manually
docker compose -f /opt/dungeon-minus-one/docker-compose.staging.yml exec app alembic upgrade head
sudo systemctl restart dungeon-minus-one
```

### Location shows "Unknown"
**Cause:** Locations not seeded or seed script failed.
**Solution:**
```bash
docker compose -f /opt/dungeon-minus-one/docker-compose.staging.yml exec app python scripts/sync_locations.py
```

### Seed script duplicate key error
**Cause:** SQLAlchemy autoflush during upsert loop.
**Solution:** Ensure `sync_locations.py` uses `with session.no_autoflush:` block.

## Future Improvements

Consider implementing:
1. **Startup validation** - App checks required tables/columns on boot
2. **Enhanced /health endpoint** - Verify DB schema, not just connectivity
3. **CI/CD checks** - Build verification, migration dry-run in pipeline
4. **Post-deploy smoke tests** - Automated test script after deployment
