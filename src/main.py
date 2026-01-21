#!/usr/bin/env python3
"""
FastAPI server for lead enrichment application.
Deploy to Google Cloud Run.
"""
import asyncio
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from agents import set_tracing_disabled
from common.logging import get_logger
from services.service_bus.client import ServiceBusClient

from routes import enrichment, health, scrape

# Load environment variables first
load_dotenv()

# Disable OpenAI agents SDK tracing (as we are using azure openai)
set_tracing_disabled(disabled=True)

logger = get_logger("main")

# Lifespan Manager (Background Listener)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Starts the Service Bus listener in the background."""
    logger.info("Application starting up... initializing Service Bus Listener.")
    
    # Initialize Client
    service_bus = ServiceBusClient()
    
    # Start the listener loop as a non-blocking background task
    listener_task = asyncio.create_task(service_bus.listen())
    logger.info("Service Bus listener started.")

    yield  # Application runs here

    # Cleanup on Shutdown
    logger.info("Application shutting down...")
    
    # Flush any remaining data in buffers
    await service_bus.flush_all()
    
    listener_task.cancel()
    try:
        await listener_task
    except asyncio.CancelledError:
        logger.info("Listener stopped gracefully.")

# Initialize app with lifespan
app = FastAPI(
    title="Lead Enrichment API",
    description="B2B lead enrichment service with company research and Orbis matching",
    version="0.1.0",
    lifespan=lifespan,
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


