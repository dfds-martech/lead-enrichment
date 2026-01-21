import json
from datetime import datetime
from pydantic import BaseModel, Field

class BigQueryRow(BaseModel):
    """Schema for a single row in the BigQuery lead events table."""
    eventid: str
    eventtype: str
    eventtimestamp: str
    leadid: str | None = None
    email: str | None = None
    status: str | None = None
    sourcename: str | None = None
    leadsource: str | None = None
    topic: str | None = None
    reference_number: str | None = None
    payload: str = Field(description="Full JSON payload as string")

    @classmethod
    def from_message(cls, message, event_body: dict) -> "BigQueryRow":
        """Factory method to create a BigQueryRow from a Service Bus message."""
        return cls(
            eventid=message.message_id,
            eventtype=message.subject or "Unknown",
            eventtimestamp=(
                message.enqueued_time_utc.isoformat() 
                if message.enqueued_time_utc else datetime.now().isoformat()
            ),
            leadid=event_body.get("crmLeadId"),
            email=event_body.get("leadEmail"),
            status=event_body.get("leadStatus"),
            sourcename=event_body.get("sourceName"),
            leadsource=event_body.get("leadSource"),
            topic=event_body.get("leadTopic"),
            reference_number=event_body.get("leadReferenceNumber"),
            payload=json.dumps(event_body)
        )