FROM python:3.11-slim

WORKDIR /app

# System dependencies required by Playwright Chromium
# Source: Playwright official apt dependency list for Debian Bookworm (python:3.11-slim base)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    libglib2.0-0 \
    libnss3 \
    libfontconfig1 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxext6 \
    libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium browser binary
RUN playwright install chromium

# Copy source
COPY . .

EXPOSE 8001

# sidecar/ and src/ are siblings under /app — use sidecar.main:app (not career_agent.sidecar.main:app)
CMD ["uvicorn", "sidecar.main:app", "--host", "0.0.0.0", "--port", "8001"]
