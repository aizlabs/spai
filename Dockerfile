FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download SpaCy Spanish model
RUN python -m spacy download es_core_news_sm

# Copy application code
COPY scripts/ ./scripts/
COPY config/ ./config/

# Run as non-root user
# Note: Create user before creating directories so they get correct ownership
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Create output directories as appuser
# These will be overridden by volume mounts in docker-compose, but ensure
# the container can write to these locations in standalone mode
RUN mkdir -p /app/output/_posts /app/output/logs /app/output/metrics /app/logs

# Default command runs topic discovery test
# Override with docker run command for other components
CMD ["python", "scripts/test_discovery.py"]
