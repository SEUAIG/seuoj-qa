FROM python:3.10-slim

WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .

# Install build dependencies for packages with C extensions (psutil, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends gcc python3-dev && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y gcc python3-dev && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY src/ ./src/

# Expose port for API server
EXPOSE 8002

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Default command - run the API server
CMD ["uvicorn", "src.api_server:app", "--host", "0.0.0.0", "--port", "8002"]
