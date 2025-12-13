# Deployment Checklist

Lessons learned from v0.2.0 deployment issues. Use this checklist to prevent and detect common deployment problems.

## Pre-Deployment Checks

### Docker Image Verification
- [ ] Build image locally and verify all required files are present:
  - `alembic.ini`
  - `alembic/` directory
  - `data/` directory
- [ ] Run `docker compose exec app alembic current` to verify Alembic is configured

### Database Migrations
- [ ] Review pending migrations with `alembic upgrade head --sql` (dry run)
- [ ] Never use `alembic stamp` in production without verifying schema matches
- [ ] After migration, verify columns exist: `\d table_name` in psql

### Environment Variables
- [ ] Verify `.env` file has all required variables
- [ ] Confirm `DATABASE_URL`, `ANTHROPIC_API_KEY`, `AUTH_SECRET_KEY` are set

## Deployment Steps

```bash
# 1. Fetch and checkout new version
git fetch origin --tags -f
git checkout <tag>

# 2. Rebuild containers
make prod-rebuild

# 3. Run migrations (verify first!)
docker compose exec app alembic upgrade head --sql  # Preview
docker compose exec app alembic upgrade head        # Apply

# 4. Verify deployment
docker compose logs --tail=50 app
```

## Post-Deployment Verification

### Smoke Test
- [ ] Load the application in browser
- [ ] Start a new game
- [ ] Verify location displays correctly (not "Unknown")
- [ ] Send a chat message and receive a response

### Database Checks
```bash
# Verify locations loaded
source .env && docker compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT COUNT(*) FROM locations;"
# Expected: 72

# Verify schema
source .env && docker compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB -c "\d game_states"
```

## Troubleshooting

### "InFailedSQLTransactionError"
**Cause:** A previous query in the transaction failed, cascading to subsequent queries.
**Solution:**
1. Check logs for the *original* error (scroll up past the cascade)
2. Often caused by missing columns - verify schema
3. Restart the app: `docker compose restart app`

### "column X does not exist"
**Cause:** Migration didn't run or was stamped without applying.
**Solution:**
```bash
# Add missing column manually
source .env && docker compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB -c "ALTER TABLE table_name ADD COLUMN column_name TYPE;"
docker compose restart app
```

### Location shows "Unknown"
**Cause:** Locations not seeded or seed script failed.
**Solution:**
```bash
docker compose exec app python scripts/sync_locations.py
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
