# Optimized Multi-stage build for AI Job Engine
# Target: < 200MB (down from 539MB)
# Optimizations: Removed unused dependencies (pandas, numpy, extra DB drivers)
FROM python:3.12-slim AS builder

# Install minimal build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/* \
    && python -m venv /opt/venv

# Activate virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements
COPY requirements.txt pyproject.toml ./

# Install dependencies with optimizations
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir \
        --prefer-binary \
        --no-compile \
        -r requirements.txt \
    # Remove unnecessary files to reduce size
    && find /opt/venv -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true \
    && find /opt/venv -type d -name "test" -exec rm -rf {} + 2>/dev/null || true \
    && find /opt/venv -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true \
    && find /opt/venv -name "*.pyc" -delete 2>/dev/null || true \
    && find /opt/venv -name "*.pyo" -delete 2>/dev/null || true \
    && find /opt/venv -type f -name "*.c" -delete 2>/dev/null || true \
    && find /opt/venv -type f -name "*.h" -delete 2>/dev/null || true \
    && find /opt/venv -type f -name "*.cpp" -delete 2>/dev/null || true \
    # Remove pip cache and wheel files
    && rm -rf /root/.cache/pip \
    # Strip binaries to reduce size
    && find /opt/venv -type f -name "*.so" -exec strip --strip-unneeded {} \; 2>/dev/null || true

# Production stage - Ultra-slim
FROM python:3.12-slim AS production

# Update system packages to patch security vulnerabilities (CVE-2025-15467 openssl)
# Install only curl for health checks
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    # Clean apt cache
    && apt-get clean \
    && rm -rf /var/cache/apt/* \
    # Create user
    && groupadd -g 1001 aiengine \
    && useradd -u 1001 -g aiengine -s /bin/sh aiengine

# Set working directory
WORKDIR /app

# Copy optimized virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Activate virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Create logs directory
RUN mkdir -p /app/logs && chown -R aiengine:aiengine /app/logs

# Copy application files (only what's needed)
COPY --chown=aiengine:aiengine src/ ./src/
COPY --chown=aiengine:aiengine scripts/ ./scripts/
COPY --chown=aiengine:aiengine mcp_http_gateway.py ./
COPY --chown=aiengine:aiengine enterprise-knowledge/ ./enterprise-knowledge/

# Set environment variables
# PYTHONPATH includes both src/ and scripts/call-scripts/ for WXCC imports
ENV PYTHONPATH=/app/src:/app/scripts/call-scripts \
    API_HOST=0.0.0.0 \
    API_PORT=8000 \
    LOG_LEVEL=INFO \
    LOG_DIR=/app/logs \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    AWS_DEFAULT_REGION=us-east-1

# Switch to non-root user
USER aiengine

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Default command
CMD ["python", "mcp_http_gateway.py"]
