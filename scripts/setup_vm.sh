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

echo "Setup complete. Please copy your files (or clone repo) to /opt/dungeon-minus-one"
echo "Then run: docker compose -f docker-compose.prod.yml up -d"

