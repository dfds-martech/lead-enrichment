import asyncio
import json
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from azure.identity.aio import ClientSecretCredential
from azure.servicebus import ServiceBusMessage
from azure.servicebus.aio import ServiceBusClient as AzureServiceBusClient
from azure.servicebus.aio import ServiceBusReceiver

from common.config import config
from common.logging import get_logger
from models.lead import Lead
from pipeline.orchestrator import PipelineOrchestrator, PipelineResult

# Service Imports
from services.bigquery.client import BigQueryClient
from services.bigquery.schemas import BigQueryRow
from services.segment.client import SegmentClient
from services.segment.schemas import SegmentTrackEvent

logger = get_logger(__name__)


class IncommingEventType(str, Enum):
    LEAD_CREATED = "lead.created"
    COMPANY_ENRICHMENT = "lead.enrich.company"
    CARGO_ENRICHMENT = "lead.enrich.cargo"

    @classmethod
    def from_string(cls, value: str) -> "IncommingEventType | None":
        """Parse string to enum, returns None if not accepted."""
        for member in cls:
            if member.value == value:
                return member
        return None

    def is_full_pipeline(self) -> bool:
        """Check if this event triggers the full enrichment pipeline."""
        return self == IncommingEventType.LEAD_CREATED


class OutputEventType(str, Enum):
    """Event type constants for enrichment completion events."""

    LEAD_ENRICHMENT = "lead.enriched.lead"
    COMPANY_ENRICHMENT = "lead.enriched.company"
    CARGO_ENRICHMENT = "lead.enriched.cargo"
    PIPELINE_COMPLETED = "lead.enrichment.completed"

    @classmethod
    def for_enrichment_type(cls, enrichment_type: str) -> "OutputEventType":
        """Get output event type for a given enrichment type."""
        mapping = {
            "lead": cls.LEAD_ENRICHMENT,
            "company": cls.COMPANY_ENRICHMENT,
            "cargo": cls.CARGO_ENRICHMENT,
        }
        return mapping[enrichment_type]


class ServiceBusClient:
    """Service Bus listener for processing lead events with BQ and Segment integration."""

    def __init__(self):
        # --- 1. Clients Initialization ---

        # Azure Service Bus
        self.topic_name = config.SERVICE_BUS_TOPIC_NAME
        self.subscription_name = config.SERVICE_BUS_SUBSCRIPTION_NAME

        # Create Azure AD credential
        credential = ClientSecretCredential(
            tenant_id=config.AZURE_TENANT_ID,
            client_id=config.AZURE_CLIENT_ID,
            client_secret=config.AZURE_CLIENT_SECRET.get_secret_value(),
        )

        # Create Service Bus client
        self.client = AzureServiceBusClient(
            fully_qualified_namespace=config.SERVICE_BUS_NAMESPACE, credential=credential
        )

        # Initialize Dedicated Services
        self.bq_service = BigQueryClient()
        self.segment_service = SegmentClient()
        # Pipeline Orchestrator (pure orchestration, no publishing)
        self.orchestrator = PipelineOrchestrator()

        # Config
        self.bq_flush_interval = 10  # Seconds

        # Background task tracking
        self._flusher_task: asyncio.Task | None = None

    async def setup(self) -> None:
        """Async setup to load secrets."""
        await self.segment_service.setup()

    # --- Testing Helper ---

    async def get_messages(self, max_count: int = 5) -> list[dict]:
        """Get some messages from the queue without removing (Async version for testing)."""
        messages = []

        # Create a receiver just for peeking
        receiver = self.client.get_subscription_receiver(
            topic_name=self.topic_name, subscription_name=self.subscription_name
        )

        async with receiver:
            # peek_messages is awaitable in the async client
            peeked = await receiver.peek_messages(max_message_count=max_count)
            for msg in peeked:
                try:
                    body = json.loads(str(msg))
                    messages.append(body)
                except json.JSONDecodeError:
                    messages.append({"raw": str(msg)})

        return messages
    
    async def send_message(self, event: dict) -> None:
        """Send a message to the topic (Async version for testing)."""
        sender = self.client.get_topic_sender(topic_name=self.topic_name)
        async with sender:
            msg = ServiceBusMessage(json.dumps(event))
            await sender.send_messages(msg)
            logger.info("Test event sent!")

    # --- Event Payload Builders ---

    def _build_enrichment_event_payload(
        self,
        lead_id: str,
        enrichment_type: str,  # "lead", "company", "cargo"
        result: dict,  # Already model_dump()'ed
    ) -> dict:
        """Build event payload for enrichment completion events."""
        return {
            "leadId": lead_id,
            "enrichmentType": enrichment_type,
            "result": result,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    async def _publish_enrichment_events(
        self,
        lead: Lead,
        result: PipelineResult,
    ) -> None:
        """Publish enrichment events for each enrichment type."""
        enrichment_results = {
            "lead": result.lead,
            "company": result.company, 
            "cargo": result.cargo,
        }

        for enrichment_type, result in enrichment_results.items():
            if result is not None:
                output_event = OutputEventType.for_enrichment_type(enrichment_type)
                payload = self._build_enrichment_event_payload(
                    lead_id=lead.id,
                    enrichment_type=enrichment_type,
                    result=result.model_dump(),
                )
                await self.publish(
                    event_type=output_event.value,
                    event_data=payload,
                    correlation_id=lead.id,
                )

        # Publish pipeline completion if all enrichments ran
        if all(r is not None for r in enrichment_results.values()):
            await self.publish(
                event_type=OutputEventType.PIPELINE_COMPLETED.value,
                event_data={"leadId": lead.id, "status": "success"},
                correlation_id=lead.id,
            )

    # --- Background Tasks ---

    async def _periodic_flusher(self) -> None:
        """Background task to trigger BigQuery flush periodically."""
        logger.info("Starting periodic flusher.")
        while True:
            await asyncio.sleep(self.bq_flush_interval)
            await self.bq_service.flush()

    # --- Main Handling Logic ---

    async def _handle_message(self, message: ServiceBusMessage, receiver: ServiceBusReceiver) -> None:
        """Process a single message: Enrich -> Dispatch -> ACK."""
        try:
            body_str = str(message)
            event_body = json.loads(body_str)
            event_type_str = event_body.get("eventType")
            logger.info(f"Event received: {event_type_str} | Processing...")

            event_type = IncommingEventType.from_string(event_type_str)
            if event_type is None:
                logger.warning(f"Event type '{event_type_str}' not accepted. Dead-lettering.")
                await receiver.dead_letter_message(
                    message,
                    reason="UnknownEventType",
                    error_description=f"Event type '{event_type_str}' not in accepted list",
                )
                return

            result = PipelineResult()

            # --- STEP 1: ENRICHMENT (pure orchestration) ---
            try:
                lead = Lead.from_event(event_body)
                
                if event_type == IncommingEventType.COMPANY_ENRICHMENT:
                    result.company = await self.orchestrator.run_company_enrichment(lead)

                elif event_type == IncommingEventType.CARGO_ENRICHMENT:
                    result.cargo = await self.orchestrator.run_cargo_enrichment(lead)

                elif event_type.is_full_pipeline():
                    result = await self.orchestrator.run_pipeline(lead)
                    
                await self._publish_enrichment_events(lead, result)
                event_body["enrichment"] = result.model_dump()
                logger.info(f"Enrichment successful for lead {lead.id}")

            except Exception as enrich_err:
                logger.error(f"Enrichment failed (continuing to archive raw event): {enrich_err}")
                event_body["enrichment_error"] = str(enrich_err)

            # --- STEP 2: DISPATCH (Side Effects) ---
            # Prepare data objects using Schemas
            bq_row = BigQueryRow.from_message(message, event_body)
            segment_event = SegmentTrackEvent.from_message(message, event_body)

            # Send to BQ and Segment in parallel
            dispatch_results = await asyncio.gather(
                self.bq_service.add_row(bq_row), self.segment_service.track(segment_event), return_exceptions=True
            )

            # Check results (Strict Reliability: Fail if any service returns False/Exception)
            has_failures = any(
                isinstance(res, Exception) or res is False
                for res in dispatch_results
            )

            if has_failures:
                # This raises an exception, which jumps to the `except` block below.
                # The message is NOT ACKed, so Azure will redeliver it.
                raise Exception("Downstream dispatch failed. NACKing message.")

            # --- STEP 3: COMPLETE (ACK) ---
            await receiver.complete_message(message)

        except Exception as e:
            logger.error(f"Processing failed for message {message.message_id}: {e}")
            # Message NOT completed -> Retry

    async def listen(self) -> None:
        """Start the listener loop."""
        await self.setup()

        # Start the periodic flusher for BigQuery
        self._flusher_task = asyncio.create_task(self._periodic_flusher())

        async with self.client:
            receiver = self.client.get_subscription_receiver(
                topic_name=self.topic_name, subscription_name=self.subscription_name
            )
            async with receiver:
                logger.info(f"Listening on {self.topic_name}/{self.subscription_name}")
                async for msg in receiver:
                    await self._handle_message(msg, receiver)

    async def flush_all(self) -> None:
        """Flush pending data and stop background tasks. Used for clean shutdown."""
        # Cancel periodic flusher if running
        if self._flusher_task is not None:
            self._flusher_task.cancel()
            try:
                await self._flusher_task
            except asyncio.CancelledError:
                pass

        # Final flush of any remaining data
        await self.bq_service.flush()

    async def publish(self, event_type: str, event_data: dict, correlation_id: str | None = None) -> None:
        """Publish an event to Service Bus.

        Note: Assumes client is already open (called from within listen context).
        """
        event = {
            "eventId": f"{event_type}-{datetime.now(UTC).isoformat()}",
            "eventType": event_type,
            "eventVersion": "1.0",
            "eventTimestamp": datetime.now(UTC).isoformat(),
            "sourceSystem": "lead-enrichment",
            "correlationId": correlation_id or event_data.get("leadId"),
            "data": event_data,
        }

        sender = self.client.get_topic_sender(topic_name=self.topic_name)
        async with sender:
            msg = ServiceBusMessage(json.dumps(event), correlation_id=correlation_id)
            await sender.send_messages(msg)
            logger.info(f"Published event: {event_type}")
