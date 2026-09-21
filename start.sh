#!/bin/bash
set -e

PORT="${PORT:-8000}"
export PORT
export BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:$PORT}"
export LISTENER_SERVICE_KEY="${LISTENER_SERVICE_KEY:-baleen_internal_listener_key_2026}"

# Supervise both required processes. A dead listener must restart the container,
# rather than leaving a healthy-looking API that silently receives no trades.
cd /app/listener
node dist/index.js &
listener_pid=$!
cd /app/backend
python run.py &
backend_pid=$!
trap 'kill "$listener_pid" "$backend_pid" 2>/dev/null || true' EXIT
trap 'exit 143' TERM
trap 'exit 130' INT
set +e
wait -n "$listener_pid" "$backend_pid"
exit_code=$?
if [ "$exit_code" -eq 0 ]; then exit_code=1; fi
exit "$exit_code"
