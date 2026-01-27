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
        """Factory method to create a SegmentTrackEvent from the nested structure."""
        subject = message.subject or "UnknownEvent"
        
        # --- FIX: Handle Dot Notation (lead.updated -> Lead Updated) ---
        # 1. Replace dots and underscores with spaces
        # 2. Convert to Title Case (e.g., "lead updated" -> "Lead Updated")
        clean_subject = subject.replace(".", " ").replace("_", " ")
        event_name = clean_subject.title()
        
        # 1. Determine root (Wrapper check)
        if "data" in event_body and isinstance(event_body["data"], dict):
            root = event_body["data"]
        else:
            root = event_body

        # 2. Find Email for UserID
        contact_data = root.get("contact", {})
        email = contact_data.get("email")

        # Fallback to top-level if needed
        user_id = email or event_body.get("leadEmail")

        return cls(
            userId=user_id,
            event=event_name,
            properties=event_body, 
            timestamp=(
                message.enqueued_time_utc.isoformat() 
                if message.enqueued_time_utc else datetime.now().isoformat()
            )
        )