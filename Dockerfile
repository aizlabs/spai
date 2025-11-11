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

# Create output directories
RUN mkdir -p /app/output/_posts /app/output/logs /app/output/metrics /app/logs

# Run as non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

CMD ["python", "scripts/main.py"]
