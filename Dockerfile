# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
ARG ASSET_BASE_URL
ENV ASSET_BASE_URL=$ASSET_BASE_URL
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python app
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies + Doppler CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    gnupg \
    && curl -sLf --retry 3 --tlsv1.2 --proto "=https" \
       'https://packages.doppler.com/public/cli/gpg.DE2A7741A397C129.key' | gpg --dearmor -o /usr/share/keyrings/doppler-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/doppler-archive-keyring.gpg] https://packages.doppler.com/public/cli/deb/debian any-version main" > /etc/apt/sources.list.d/doppler-cli.list \
    && apt-get update && apt-get install -y doppler \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY prompts/ ./prompts/
COPY scripts/ ./scripts/
COPY skills/ ./skills/
RUN python scripts/compile_skills.py
COPY data/ ./data/
COPY alembic.ini .
COPY alembic/ ./alembic/

# Copy built frontend
COPY --from=frontend-builder /frontend/dist ./frontend/dist

RUN chmod +x scripts/start.sh

# Conditional entrypoint: use Doppler if token provided, else run directly
# - With DOPPLER_TOKEN: doppler run fetches secrets and injects as env vars
# - Without DOPPLER_TOKEN: runs directly, reads from .env file (local dev)
ENTRYPOINT ["sh", "-c", "if [ -n \"$DOPPLER_TOKEN\" ]; then exec doppler run -- \"$@\"; else exec \"$@\"; fi", "--"]
CMD ["./scripts/start.sh"]
