#!/bin/bash

# Exit on any error
set -e

# Start the Node.js listener in the background
echo "Starting Node.js signal listener..."
cd /app/listener && npm start &

# Start the Python FastAPI backend in the foreground
echo "Starting Python FastAPI backend..."
cd /app/backend && uvicorn app.main:app --host 0.0.0.0 --port 8000
