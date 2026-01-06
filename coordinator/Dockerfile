FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including curl for health checks
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    nodejs \
    npm \
    docker.io \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies from repo root
COPY requirements.txt /app/repo-requirements.txt
RUN pip install --no-cache-dir -r /app/repo-requirements.txt

# Copy coordinator requirements
COPY coordinator/requirements.txt /app/coordinator-requirements.txt
RUN pip install --no-cache-dir -r /app/coordinator-requirements.txt

# Copy full application (context is repo root in production compose)
COPY . /app

WORKDIR /app/coordinator

# Create directories
RUN mkdir -p /app/generated /app/.sb_artifacts

EXPOSE 5000

# Use uvicorn for production
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]

