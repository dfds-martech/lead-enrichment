#!/usr/bin/env python3
"""Production server startup script."""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def main():
    import uvicorn

    port = int(os.environ.get("PORT", "8080"))

    print(f"Starting production server on port {port}...")
    print("Logs: INFO level")
    print(f"Health check: http://0.0.0.0:{port}/health")
    print("-" * 50)

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=port,
        workers=1,  # Cloud Run handles scaling
        log_level="info",
    )


if __name__ == "__main__":
    main()
