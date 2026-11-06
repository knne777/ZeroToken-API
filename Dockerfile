# ==========================================
# Stage 1: Build Frontend React Dashboard
# ==========================================
FROM node:20-alpine AS frontend-builder
WORKDIR /build

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ==========================================
# Stage 2: Production Python & CLI Runtime
# ==========================================
FROM python:3.12-slim
WORKDIR /app

# Install system dependencies, Node.js 20, Codex CLI and Claude Code CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g @openai/codex @anthropic-ai/claude-code \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy custom binaries if provided (e.g. Google Antigravity 'agy')
COPY bin/ /tmp/bin/
RUN if [ -f /tmp/bin/agy ]; then cp /tmp/bin/agy /usr/local/bin/agy && chmod +x /usr/local/bin/agy; fi \
    && rm -rf /tmp/bin

# Copy application source and compiled frontend
COPY app/ ./app/
COPY --from=frontend-builder /build/dist ./frontend/dist

# Default environment configuration
ENV ZEROTOKEN_HOST=0.0.0.0 \
    ZEROTOKEN_PORT=8000 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
