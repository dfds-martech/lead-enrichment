#!/usr/bin/env python3
"""Development server startup script."""

import os
import subprocess


def main():
    os.environ.setdefault("PYTHONPATH", "src")

    cmd = ["uvicorn", "src.main:app", "--reload", "--host", "0.0.0.0", "--port", "8080", "--log-level", "debug"]

    print("Starting development server...")
    print(f"Command: {' '.join(cmd)}")
    print("Server at: http://localhost:8080")
    print("API docs at: http://localhost:8080/docs")
    print("Auto-reload enabled")
    print("-" * 50)

    subprocess.run(cmd)


if __name__ == "__main__":
    main()
