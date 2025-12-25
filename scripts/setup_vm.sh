#!/bin/bash
set -e

# Update system
apt-get update && apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Create app directory
mkdir -p /opt/dungeon-minus-one
cd /opt/dungeon-minus-one

echo "Setup complete. Copy docker-compose.staging.yml and .env to /opt/dungeon-minus-one"
echo "Ensure .env includes APP_IMAGE, DATABASE_URL, ANTHROPIC_API_KEY, AUTH_SECRET_KEY"
echo "Then run: docker compose -f docker-compose.staging.yml up -d"
