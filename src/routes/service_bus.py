"""Service Bus utility endpoints for debugging and monitoring."""

from fastapi import APIRouter, Request

from common.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/service-bus", tags=["service-bus"])


@router.get("/messages")
async def peek_messages(request: Request, max_count: int = 5):
    """Peek at messages in the subscription without consuming them."""
    service_bus = request.app.state.service_bus

    if service_bus is None:
        return {
            "status": "disabled",
            "message": "Service Bus listener is disabled. Set SERVICE_BUS_ENABLED=true to enable.",
        }

    try:
        messages = await service_bus.get_messages(max_count=max_count)
        return {
            "status": "success",
            "count": len(messages),
            "messages": messages,
        }
    except Exception as e:
        logger.error(f"Failed to peek messages: {e}")
        return {
            "status": "error",
            "error": f"{type(e).__name__}: {e}",
        }
