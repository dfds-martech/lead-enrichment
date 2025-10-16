#!/usr/bin/env python3
"""Development server startup script."""

import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def main():
    import uvicorn

    print("Starting development server (hot reload enabled)...")
    print("Server at: http://localhost:8080")
    print("API docs at: http://localhost:8080/docs")
    print("Auto-reload enabled")
    print("Logs: DEBUG level")
    print("-" * 50)

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="debug",
    )


if __name__ == "__main__":
    main()
