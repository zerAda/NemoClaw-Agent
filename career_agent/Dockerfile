# Diamond Grade Dockerfile for Career Agent
# Expert Hardening: Non-root user & optimized layers
FROM python:3.11-slim

LABEL maintainer="NemoClaw Team"
LABEL version="1.3.0"

# Create non-privileged user for Diamond-Grade security
RUN groupadd -r python-group && useradd -r -g python-group -m -s /sbin/nologin python-user

WORKDIR /app

# System dependencies for Playwright/patchright Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl libglib2.0-0 libnss3 libfontconfig1 libdbus-1-3 \
    libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2 libx11-6 libx11-xcb1 \
    libxcb1 libxext6 libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

# Browser install - separate layer for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    patchright install chromium

# Copy application code (obeying .dockerignore)
COPY --chown=python-user:python-group . .

# Set permissions for brain path if mounted
RUN mkdir -p /app/brain && chown -R python-user:python-group /app/brain

# Set environment defaults
ENV BRAIN_PATH=/app/brain
ENV LOG_LEVEL=INFO

# Switch to non-privileged user
USER python-user

EXPOSE 8001

# Healthcheck for sidecar stability
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "sidecar.main:app", "--host", "0.0.0.0", "--port", "8001"]
