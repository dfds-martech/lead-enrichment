import asyncio
import os
from contextlib import asynccontextmanager

from agents import set_tracing_disabled
from fastapi import FastAPI

from common.config import config
from common.logging import get_logger
from routes import enrichment, health, scrape, service_bus
from services.service_bus.client import ServiceBusClient

# Disable OpenAI agents SDK tracing (as we are using azure openai)
set_tracing_disabled(disabled=True)

logger = get_logger(__name__)


# Lifespan Manager (Background Listener)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Starts the Service Bus listener in the background."""
    listener_task = None

    if config.SERVICE_BUS_ENABLED:
        logger.info("Application starting up... initializing Service Bus Listener.")

        # Initialize Client
        service_bus = ServiceBusClient()
        app.state.service_bus = service_bus

        # Start the listener loop as a non-blocking background task
        listener_task = asyncio.create_task(service_bus.listen())
        logger.info("Service Bus listener started.")
    else:
        logger.info("Service Bus listener disabled via SERVICE_BUS_ENABLED=false")
        app.state.service_bus = None

    yield  # Application runs here

    # Cleanup on Shutdown
    logger.info("Application shutting down...")

    if app.state.service_bus is not None:
        await app.state.service_bus.flush_all()

    if listener_task is not None:
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
app.include_router(service_bus.router)


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
