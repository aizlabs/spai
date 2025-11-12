FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install Python dependencies using uv
# This includes the SpaCy model from the direct dependency
RUN uv sync --frozen

# Copy application code
COPY scripts/ ./scripts/
COPY config/ ./config/

# Create output directories
RUN mkdir -p /app/output/_posts /app/output/logs /app/output/metrics /app/logs

# Run as non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

CMD ["uv", "run", "python", "scripts/main.py"]
