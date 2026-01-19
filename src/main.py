#!/usr/bin/env python3
"""
FastAPI server for lead enrichment application.
Deploy to Google Cloud Run.
"""

# Load environment variables first
import os

from agents import set_tracing_disabled
from dotenv import load_dotenv
from fastapi import FastAPI

from routes import enrichment, health, scrape

# from services.service_bus.client import ServiceBusClient

load_dotenv()

# Disable OpenAI agents SDK tracing (as we are using azure openai)
set_tracing_disabled(disabled=True)

# Initialize app
app = FastAPI(
    title="Lead Enrichment API",
    description="B2B lead enrichment service with company research and Orbis matching",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Set routers
app.include_router(health.router)
app.include_router(enrichment.router)
app.include_router(scrape.router)


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

    # Run service bus listener
    # service_bus = ServiceBusClient()
    # asyncio.run(service_bus.listen())
