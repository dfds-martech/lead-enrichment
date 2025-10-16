# Multi-stage build for optimal image size
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

# Copy application source code
COPY src ./src

# Set environment variables
ENV PORT=8080 \
    PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1

# Health check for Cloud Run
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health', timeout=2)"

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "src/scripts/prod.py"]
