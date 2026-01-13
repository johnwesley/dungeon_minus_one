#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${1:-python}"
FRONTEND_DIR="${2:-frontend}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Compiling skills..."
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/compile_skills.py"

echo "Syncing locations..."
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/sync_locations.py"

echo "Starting backend on :8000..."
"${PYTHON_BIN}" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
backend_pid=$!

cleanup() {
  if kill -0 "${backend_pid}" 2>/dev/null; then
    kill "${backend_pid}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

echo "Waiting for backend health..."
for _ in {1..30}; do
  if curl -sf http://localhost:8000/health >/dev/null; then
    break
  fi
  if ! kill -0 "${backend_pid}" 2>/dev/null; then
    echo "Backend exited early. Check logs above."
    exit 1
  fi
  sleep 0.5
done

if ! curl -sf http://localhost:8000/health >/dev/null; then
  echo "Backend did not become ready. Check logs above."
  exit 1
fi

echo "Starting frontend on :5173..."
cd "${ROOT_DIR}/${FRONTEND_DIR}"
npm run dev
