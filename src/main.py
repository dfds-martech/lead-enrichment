#!/usr/bin/env python3
"""
FastAPI server for lead enrichment application.
Deploy to Google Cloud Run.
"""

import os

from fastapi import FastAPI

# Initialize
app = FastAPI(
    title="Lead Enrichment API",
    description="B2B lead enrichment service with company research and Orbis matching",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.get("/")
async def root():
    """Root endpoint with basic info."""
    return {
        "service": "Lead Enrichment API",
        "version": "0.1.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run."""
    return {"status": "healthy", "service": "lead-enrichment"}


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
