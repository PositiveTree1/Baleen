# Use an official Python runtime
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl gcc python3-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements-pinned.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements-pinned.txt

# Copy all backend code
COPY . .
RUN python -c "import app.main"

# Expose port
EXPOSE 8000

# Start FastAPI via python run.py
CMD ["python", "run.py"]

