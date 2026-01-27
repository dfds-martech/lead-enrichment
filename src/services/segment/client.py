import asyncio
import base64
import httpx

from common.config import config
from common.logging import get_logger
from services.segment.schemas import SegmentTrackEvent

logger = get_logger(__name__)

class SegmentClient:
    """Client for sending events to Segment."""

    def __init__(self):
        self.write_key: str | None = None
        self.api_url = "https://events.eu1.segmentapis.com/v1/track"
    

    async def setup(self):
        """Load the Segment Write Key from Secret Manager."""
        if config.SEGMENT_WRITE_KEY_ID:
            logger.info("Fetching Segment Write Key...")
            self.write_key = config.SEGMENT_WRITE_KEY_ID
            if self.write_key:
                logger.info("Segment Write Key loaded.")
        else:
            logger.warning("SEGMENT_WRITE_KEY_ID not set in config.")

    async def track(self, event: SegmentTrackEvent) -> bool:
        """Sends a track event to Segment. Returns True on success."""
        if not self.write_key:
            # If no key is configured, we treat it as 'success' (skipped) to not block the pipeline
            return True

        # Prepare Headers
        auth_str = f"{self.write_key}:"
        b64_auth = base64.b64encode(auth_str.encode("ascii")).decode("ascii")
        headers = {
            "Authorization": f"Basic {b64_auth}",
            "Content-Type": "application/json"
        }

        # Prepare Payload (using Pydantic alias for userId)
        payload = event.model_dump(by_alias=True, exclude_none=True)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                    timeout=10.0
                )
                
                if response.is_error:
                    logger.error(f"Segment API Error ({response.status_code}): {response.text}")
                    return False
                
                logger.info(f"Sent '{event.event}' to Segment for: {event.user_id}")
                return True

        except Exception as e:
            logger.error(f"Error sending to Segment: {e}")
            return False