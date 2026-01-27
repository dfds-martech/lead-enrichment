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
        """Factory method handles both FLAT (root) and NESTED (data wrapper) structures."""
        
        # 1. INTELLIGENT ROUTING
        # If the 'data' wrapper exists, dive inside. Otherwise, use the root.
        if "data" in event_body and isinstance(event_body["data"], dict):
            print("🔹 DEBUG: Detected 'data' wrapper structure.")
            root = event_body["data"]
        else:
            print("🔹 DEBUG: Detected FLAT structure.")
            root = event_body

        # 2. Extract sub-objects safely
        # Note: We look for 'lead', 'contact' inside whatever 'root' we decided on
        lead_data = root.get("lead", {})
        contact_data = root.get("contact", {})
        campaign_data = root.get("campaign", {}) 
        
        return cls(
            eventid=message.message_id,
            eventtype=message.subject or "Unknown",
            eventtimestamp=(
                message.enqueued_time_utc.isoformat() 
                if message.enqueued_time_utc else datetime.now().isoformat()
            ),
            # 3. Map fields
            leadid=lead_data.get("crmLeadId"), 
            email=contact_data.get("email"),
            status=lead_data.get("status"),
            
            # Source fallback logic
            sourcename=campaign_data.get("sourceName") or lead_data.get("sourceName"),
            leadsource=campaign_data.get("leadSource") or lead_data.get("leadSource"),
            
            topic=lead_data.get("subject"),
            reference_number=str(lead_data.get("requestNumber")) if lead_data.get("requestNumber") else None,
            
            payload=json.dumps(event_body)
        )