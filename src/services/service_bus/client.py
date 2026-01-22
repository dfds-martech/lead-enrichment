import asyncio
import json
from datetime import datetime

from azure.identity.aio import ClientSecretCredential
from azure.servicebus import ServiceBusMessage
from azure.servicebus.aio import ServiceBusClient as AzureServiceBusClient
from azure.servicebus.aio import ServiceBusReceiver

from common.config import config
from common.logging import get_logger
from models.lead import Lead
from pipeline.orchestrator import PipelineOrchestrator

# Service Imports
from services.bigquery.client import BigQueryClient
from services.bigquery.schemas import BigQueryRow
from services.segment.client import SegmentClient
from services.segment.schemas import SegmentTrackEvent

logger = get_logger(__name__)

ACCEPTED_EVENTS = {"lead.created", "lead.updated", "lead.enrich.company", "lead.enrich.cargo"}


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
        # Pipeline Orchestrator
        self.orchestrator = PipelineOrchestrator(service_bus=self)

        # Config
        self.bq_flush_interval = 10  # Seconds

    async def setup(self):
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

    # --- Background Tasks ---

    async def _periodic_flusher(self):
        """Background task to trigger BigQuery flush periodically."""
        logger.info("Starting periodic flusher.")
        while True:
            await asyncio.sleep(self.bq_flush_interval)
            await self.bq_service.flush()

    # --- Main Handling Logic ---

    async def _handle_message(self, message: ServiceBusMessage, receiver: ServiceBusReceiver):
        """Process a single message: Enrich -> Dispatch -> ACK."""
        try:
            body_str = str(message)
            event_body = json.loads(body_str)
            event_type = event_body.get("eventType")

            logger.info(f"Event received: {event_type} | Processing...")

            if event_type not in ACCEPTED_EVENTS:
                logger.warning(f"Event type '{event_type}' not accepted. Dead-lettering.")
                await receiver.dead_letter_message(
                    message,
                    reason="UnknownEventType",
                    error_description=f"Event type '{event_type}' not in accepted list",
                )
                return

            enrichment_result = {}

            # --- STEP 1: ENRICHMENT ---
            try:
                lead = Lead.from_event(event_body)

                if event_type == "lead.enrich.company":
                    enrichment_result = await self.orchestrator.run_company_enrichment(lead)
                    if hasattr(enrichment_result, "model_dump"):
                        enrichment_result = enrichment_result.model_dump()

                elif event_type == "lead.enrich.cargo":
                    enrichment_result = await self.orchestrator.run_cargo_enrichment(lead)
                    if hasattr(enrichment_result, "model_dump"):
                        enrichment_result = enrichment_result.model_dump()

                else:
                    pipeline_results = await self.orchestrator.run_pipeline(lead)
                    enrichment_result = pipeline_results

                logger.info(f"Enrichment successful for lead {lead.id}")
                event_body["enrichment"] = enrichment_result

            except Exception as enrich_err:
                logger.error(f"Enrichment failed (continuing to archive raw event): {enrich_err}")
                event_body["enrichment_error"] = str(enrich_err)

            # --- STEP 2: DISPATCH (Side Effects) ---
            # Prepare data objects using Schemas
            bq_row = BigQueryRow.from_message(message, event_body)
            segment_event = SegmentTrackEvent.from_message(message, event_body)

            # Send to BQ and Segment in parallel
            results = await asyncio.gather(
                self.bq_service.add_row(bq_row), self.segment_service.track(segment_event), return_exceptions=True
            )

            # Check results (Strict Reliability: Fail if any service returns False/Exception)
            has_failures = False
            for res in results:
                if isinstance(res, Exception) or res is False:
                    has_failures = True

            if has_failures:
                # This raises an exception, which jumps to the `except` block below.
                # The message is NOT ACKed, so Azure will redeliver it.
                raise Exception("Downstream dispatch failed. NACKing message.")

            # --- STEP 3: COMPLETE (ACK) ---
            await receiver.complete_message(message)

        except Exception as e:
            logger.error(f"Processing failed for message {message.message_id}: {e}")
            # Message NOT completed -> Retry

    async def listen(self):
        """Start the listener loop."""
        await self.setup()

        # Start the periodic flusher for BigQuery
        asyncio.create_task(self._periodic_flusher())

        async with self.client:
            receiver = self.client.get_subscription_receiver(
                topic_name=self.topic_name, subscription_name=self.subscription_name
            )
            async with receiver:
                logger.info(f"Listening on {self.topic_name}/{self.subscription_name}")
                async for msg in receiver:
                    await self._handle_message(msg, receiver)

    # Used for clean shutdown in main.py
    async def flush_all(self):
        await self.bq_service.flush()

    async def publish(self, event_type: str, event_data: dict, correlation_id: str | None = None):
        """Publish an event to Service Bus."""
        event = {
            "eventId": f"{event_type}-{datetime.now().isoformat()}",
            "eventType": event_type,
            "eventVersion": "1.0",
            "eventTimestamp": datetime.now().isoformat(),
            "sourceSystem": "lead-enrichment",
            "correlationId": correlation_id or event_data.get("leadId"),
            "data": event_data,
        }

        async with self.client:
            sender = self.client.get_topic_sender(topic_name=self.topic_name)
            async with sender:
                msg = ServiceBusMessage(json.dumps(event), correlation_id=correlation_id)
                await sender.send_messages(msg)
                logger.info(f"Published event: {event_type}")
