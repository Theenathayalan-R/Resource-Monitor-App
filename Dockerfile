# Production Dockerfile for Spark Pod Resource Monitor
FROM python:3.11-slim

# Security: create non-root user
RUN groupadd -r sparkmonitor && useradd -r -g sparkmonitor sparkmonitor

# Install system deps (gcc for some wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install dependencies first (leverage build cache)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy application code
COPY src/ /app/src/
COPY run.sh /app/run.sh

# Create data and logs dirs and set permissions
RUN mkdir -p /app/data /app/logs && \
    chown -R sparkmonitor:sparkmonitor /app && \
    chmod +x /app/run.sh

USER sparkmonitor

ENV PORT=8502 \
    ADDRESS=0.0.0.0 \
    LOG_LEVEL=INFO

EXPOSE 8502

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${PORT}/_stcore/health || exit 1

CMD ["/app/run.sh"]
