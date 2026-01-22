import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SegmentTrackEvent(BaseModel):
    """Schema for a Segment track event."""

    user_id: str | None = Field(None, alias="userId")
    event: str
    properties: dict[str, Any]
    timestamp: str | None = None

    @classmethod
    def from_message(cls, message, event_body: dict) -> "SegmentTrackEvent":
        """Factory method to create a SegmentTrackEvent from a Service Bus message."""
        # Clean event name (CamelCase to Space separated)
        subject = message.subject or "UnknownEvent"
        event_name = re.sub(r"([A-Z])", r" \1", subject).strip()

        return cls(
            userId=event_body.get("leadEmail"),
            event=event_name,
            properties=event_body,
            timestamp=(
                message.enqueued_time_utc.isoformat() if message.enqueued_time_utc else datetime.now().isoformat()
            ),
        )
