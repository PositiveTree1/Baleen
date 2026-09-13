# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Install Node.js
RUN apt-get update && \
    apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files first
COPY backend/requirements.txt backend/requirements-pinned.txt ./backend/
COPY listener/package.json listener/package-lock.json ./listener/

# Install Python dependencies
RUN pip install --no-cache-dir --require-hashes -r backend/requirements-pinned.txt

# Install Node dependencies
RUN cd listener && npm ci

# Copy all code
COPY backend/ ./backend/
COPY listener/ ./listener/

# Verify clean Python import
RUN cd backend && python -c "import app.main; print('Backend smoke-test passed')"

# Build Node TypeScript
RUN cd listener && npm run build

# Make the start script executable
COPY start.sh /app/
RUN chmod +x /app/start.sh

# Expose backend port
EXPOSE 8000

# Start both services
CMD ["/app/start.sh"]
