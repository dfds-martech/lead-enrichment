#!/usr/bin/env python3
"""
FastAPI server for lead enrichment application.
Deploy to Google Cloud Run.
"""

# Load environment variables first
import os

from dotenv import load_dotenv
from fastapi import FastAPI

from routes import enrichment, health

load_dotenv()

# Initialize
app = FastAPI(
    title="Lead Enrichment API",
    description="B2B lead enrichment service with company research and Orbis matching",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Include routers
app.include_router(health.router)
app.include_router(enrichment.router)


if __name__ == "__main__":
    import uvicorn

    # Get port from environment (Cloud Run sets this)
    port = int(os.environ.get("PORT", 8080))

    # Run the server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Disable reload in production
        log_level="info",
    )
