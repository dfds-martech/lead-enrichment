#!/usr/bin/env python3
"""Production server startup script."""

import os
import subprocess


def main():
    """Start the production server."""
    os.environ.setdefault("PYTHONPATH", "src")

    port = os.environ.get("PORT", "8080")

    cmd = [
        "uvicorn",
        "src.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        port,
        "--workers",
        "1",  # Cloud Run handles scaling
        "--log-level",
        "info",
    ]

    print(f"Starting production server on port {port}...")
    subprocess.run(cmd)


if __name__ == "__main__":
    main()
