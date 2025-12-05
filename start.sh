#!/bin/bash
set -e

# Run migrations/seeding
echo "Seeding database..."
python scripts/seed_locations.py

# Start the application
echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

