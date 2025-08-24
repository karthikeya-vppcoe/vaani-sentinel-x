# Multi-stage Dockerfile for Vaani Sentinel X
# Production-ready with security best practices

# Stage 1: Base image with dependencies
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user for security
RUN groupadd -r vaani && useradd -r -g vaani vaani

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Dependencies installation
FROM base as deps

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml requirements-minimal.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-minimal.txt

# Stage 3: Production image
FROM base as production

# Set working directory
WORKDIR /app

# Copy installed packages from deps stage
COPY --from=deps /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=deps /usr/local/bin/ /usr/local/bin/

# Copy application code
COPY agents/ ./agents/
COPY cli/ ./cli/
COPY config/ ./config/
COPY utils/ ./utils/
COPY web-ui/ ./web-ui/
COPY content/ ./content/
COPY kill_switch.py ./
COPY .env.template ./

# Create required directories
RUN mkdir -p logs scheduler_db analytics_db archives scheduled_posts data && \
    chown -R vaani:vaani /app

# Switch to non-root user
USER vaani

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "from utils.common import HealthChecker; hc = HealthChecker(); result = hc.full_health_check(); exit(0 if all(result['dependencies'].values()) else 1)"

# Expose port
EXPOSE 5000

# Default command
CMD ["python", "cli/command_center.py", "list"]