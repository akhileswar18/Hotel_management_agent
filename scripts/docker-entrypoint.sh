#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────────
# HMS Docker Entrypoint
#
# Starts both the FastAPI backend and Flet UI in a single container.
# FastAPI runs in the background; Flet runs in the foreground.
# ──────────────────────────────────────────────────────────────────────────────

set -e

echo "============================================"
echo "  Hotel Management System v1.0 (Docker)"
echo "============================================"
echo ""

# ── Initialize database ──────────────────────────────────────────────────────
echo "[1/3] Initializing database..."
python -c "
from src.infrastructure.database import Database
db = Database()
print('      [OK] Database ready')
"

# ── Start FastAPI backend (background) ───────────────────────────────────────
echo "[2/3] Starting API server on ${API_HOST:-0.0.0.0}:${API_PORT:-8000}..."
python -m uvicorn src.api.app:app \
    --host "${API_HOST:-0.0.0.0}" \
    --port "${API_PORT:-8000}" \
    --log-level warning &

API_PID=$!

# Wait for API to be ready
for i in $(seq 1 30); do
    if python -c "
import socket
s = socket.socket()
try:
    s.connect(('127.0.0.1', ${API_PORT:-8000}))
    s.close()
    exit(0)
except:
    exit(1)
" 2>/dev/null; then
        echo "      [OK] API ready"
        break
    fi
    sleep 0.5
done

# ── Start Flet UI (foreground) ───────────────────────────────────────────────
echo "[3/3] Starting Flet UI on port 8080..."
echo ""
echo "  Access the application:"
echo "    API:  http://localhost:${API_PORT:-8000}/docs"
echo "    UI:   http://localhost:8080"
echo ""

# Run Flet UI in the foreground (keeps container alive)
exec python -m src.ui.app

# If Flet exits, clean up API
trap "kill $API_PID 2>/dev/null" EXIT
