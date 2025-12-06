#!/bin/bash
set -e

# Run database init (creates tables if they don't exist)
# In a real production setup with existing data, you'd use Alembic for migrations
# For now, this relies on SQLAlchemy creating new tables on startup if missing.

# Seeding database (locations)
echo "Seeding database..."
python scripts/seed_locations.py

# Start the application
echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
