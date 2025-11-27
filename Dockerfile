# Multi-stage build for optimal image size with Playwright support
FROM python:3.12-slim-bookworm as builder

WORKDIR /app

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files and source structure
COPY pyproject.toml uv.lock README.md ./
COPY src ./src

# Install dependencies to system Python (no venv needed in container)
RUN uv pip install --system --no-cache .

# Final runtime stage
FROM python:3.12-slim-bookworm

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source code
COPY src ./src

# Install Playwright browsers (Chromium only to save space)
# --with-deps automatically installs all system dependencies needed for headless operation
# This includes libnss3, libnspr4, libgbm1, fonts, ca-certificates, etc. (~300MB total)
RUN playwright install chromium --with-deps

# Set environment variables
ENV PORT=8080 \
    PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    ## NOTE: Playwright specific env vars (installed by playwright)
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Create non-root user for security (Cloud Run best practice)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "src/scripts/prod.py"]
