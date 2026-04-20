FROM python:3.10-slim

WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Expose port for API server
EXPOSE 8002

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Default command - run the API server
CMD ["uvicorn", "src.api_server:app", "--host", "0.0.0.0", "--port", "8002"]
