#!/usr/bin/env bash
set -e

export PATH="$HOME/.local/bin:$PATH"

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "==> Running migrations..."
cd "$ROOT/backend"
uv run python manage.py migrate --run-syncdb -v 0

echo ""
echo "==> Starting Django backend  →  http://localhost:8000"
uv run python manage.py runserver 0.0.0.0:8000 &
BACKEND_PID=$!

echo "==> Starting React frontend  →  http://localhost:5173"
cd "$ROOT/frontend"
npm run dev &
FRONTEND_PID=$!

cleanup() {
  echo ""
  echo "Shutting down..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo ""
echo "Both servers running. Press Ctrl+C to stop."
wait
