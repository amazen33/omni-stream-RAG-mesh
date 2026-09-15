# =============================================================================
# Stage 1: Build & Dependency Resolution Stage
# =============================================================================
FROM python:3.11-slim-bookworm AS builder

# Set environment variables for build efficiency and reproducibility
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install minimal OS build tools required for compiling C-extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create isolated virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install CPU-optimized PyTorch wheel first to avoid CUDA multi-gigabyte bloat
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Copy dependency specifications and install application libraries
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Strip compiled Python bytecode and test directories to minimize size
RUN find /opt/venv -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# =============================================================================
# Stage 2: Final Minimal Runtime Image
# =============================================================================
FROM python:3.11-slim-bookworm AS runtime

LABEL maintainer="DevOps Team <devops@example.com>"
LABEL description="Optimized FastAPI + PyTorch/Ollama RAG Microservice"

# Configure runtime environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8000 \
    APP_HOME=/app

# Create a dedicated non-root user and group with explicit UID/GID
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /sbin/nologin -M -d ${APP_HOME} appuser

WORKDIR ${APP_HOME}

# Copy the pre-built virtual environment from builder stage
COPY --from=builder --chown=appuser:appgroup /opt/venv /opt/venv

# Copy application source code with non-root ownership
COPY --chown=appuser:appgroup . ${APP_HOME}

# Run as non-root user
USER 10001:10001

# Expose FastAPI listening port
EXPOSE 8000

# Health check using native Python standard library (no curl package needed)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')" || exit 1

# Launch FastAPI using Uvicorn
ENTRYPOINT ["uvicorn"]
CMD ["main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers", "--forwarded-allow-ips", "*"]
