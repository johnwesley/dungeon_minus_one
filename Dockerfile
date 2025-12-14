# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python app
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY prompts/ ./prompts/
COPY scripts/ ./scripts/
COPY data/ ./data/
COPY alembic.ini .
COPY alembic/ ./alembic/

# Copy built frontend
COPY --from=frontend-builder /frontend/dist ./frontend/dist

RUN chmod +x scripts/start.sh

CMD ["./scripts/start.sh"]

