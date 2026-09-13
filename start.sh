#!/bin/bash
set -e

PORT="${PORT:-8000}"
export PORT
export BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:$PORT}"
export LISTENER_SERVICE_KEY="${LISTENER_SERVICE_KEY:-baleen_internal_listener_key_2026}"

# Start Node.js signal listener in the background if present
if [ -d "/app/listener" ]; then
    echo "Starting Node.js signal listener (connecting to $BACKEND_URL)..."
    (cd /app/listener && npm start) &
fi

# Start Python FastAPI backend in the foreground
echo "Starting Python FastAPI backend..."
cd /app/backend && exec python run.py
