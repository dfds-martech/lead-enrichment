# Build stage
FROM python:3.12.8-bookworm AS builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files and source structure
COPY pyproject.toml README.md ./
COPY uv.lock* ./
COPY src ./src

# Install dependencies to system Python (no venv needed in container)
RUN uv pip install --system --no-cache .

# Set Playwright browsers path and install Playwright browsers in builder stage
# Clean apt cache first to maximize available space
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* && \
    playwright install chromium --with-deps && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# Runtime stage
FROM python:3.12.8-slim-bookworm

# OCI image labels
LABEL org.opencontainers.image.title="lead-enrichment"
LABEL org.opencontainers.image.description="B2B lead-form enrichment service"
LABEL org.opencontainers.image.vendor="DFDS"
LABEL org.opencontainers.image.version="0.1.0"

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy Playwright browsers from builder (already installed in builder stage)
COPY --from=builder /ms-playwright /ms-playwright

# Copy application source code
COPY src ./src

# Install only the system dependencies for Playwright (without re-downloading chromium)
# Using playwright install-deps for accurate dependency installation
RUN apt-get update && \
    playwright install-deps chromium && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PORT=8080 \
    PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    ## NOTE: Playwright specific env vars (installed by playwright)
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Create non-root user for security (Cloud Run best practice)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app && \
    chown -R appuser:appuser /ms-playwright
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health', timeout=2)" || exit 1

# Run the application
CMD ["python", "src/scripts/prod.py"]
