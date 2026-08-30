#!/bin/bash
set -e

# Dynamic port binding for Railway ($PORT) and local fallback (8000)
PORT="${PORT:-8000}"

# Start Node.js signal listener in the background if present
if [ -d "/app/listener" ]; then
    echo "Starting Node.js signal listener..."
    (cd /app/listener && npm start) &
fi

# Start Python FastAPI backend in the foreground
echo "Starting Python FastAPI backend..."
cd /app/backend && exec python run.py
