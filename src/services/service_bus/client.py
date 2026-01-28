import asyncio
import json
import uuid
from datetime import UTC, datetime
from enum import Enum

from azure.identity.aio import ClientSecretCredential
from azure.servicebus import ServiceBusMessage, TransportType
from azure.servicebus.aio import ServiceBusClient as AzureServiceBusClient
from azure.servicebus.aio import ServiceBusReceiver

from common.config import config
from common.logging import get_logger
from models.lead import Lead
from pipeline.orchestrator import PipelineOrchestrator, PipelineResult

# Service Imports
from services.bigquery.client import BigQueryClient
from services.segment.client import SegmentClient

logger = get_logger(__name__)


class IncomingEventType(str, Enum):
    """Incoming event types that trigger enrichment."""

    LEAD_CREATED = "lead.created"
    LEAD_ENRICHMENT = "lead.enrich.lead"
    COMPANY_ENRICHMENT = "lead.enrich.company"
    CARGO_ENRICHMENT = "lead.enrich.cargo"

    @classmethod
    def from_string(cls, value: str) -> "IncomingEventType | None":
        try:
            return cls(value)
        except ValueError:
            return None

    def is_full_pipeline(self) -> bool:
        return self == IncomingEventType.LEAD_CREATED


class OutgoingEventType(str, Enum):
    """Outgoing event types published after enrichment."""

    LEAD_ENRICHMENT = "lead.enriched.lead"
    COMPANY_ENRICHMENT = "lead.enriched.company"
    CARGO_ENRICHMENT = "lead.enriched.cargo"
    PIPELINE_COMPLETED = "lead.enriched.completed"

    @classmethod
    def for_enrichment_type(cls, enrichment_type: str) -> "OutgoingEventType":
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
        # Azure Service Bus
        self.topic_name = config.SERVICE_BUS_TOPIC_NAME
        self.subscription_name = config.SERVICE_BUS_SUBSCRIPTION_NAME
        self.client = self._create_service_bus_client()

        # Initialize Dedicated Services
        self.bq_service = BigQueryClient()
        self.segment_service = SegmentClient()
        self.orchestrator = PipelineOrchestrator()

        # Config
        self.bq_flush_interval = 10  # Seconds

        # Background task tracking
        self._flusher_task: asyncio.Task | None = None

    def _create_service_bus_client(self) -> AzureServiceBusClient:
        credential = ClientSecretCredential(
            tenant_id=config.AZURE_TENANT_ID,
            client_id=config.AZURE_CLIENT_ID,
            client_secret=config.AZURE_CLIENT_SECRET.get_secret_value(),
        )

        client_kwargs = {
            "fully_qualified_namespace": config.SERVICE_BUS_NAMESPACE,
            "credential": credential,
        }

        if config.SERVICE_BUS_USE_WEBSOCKET:
            client_kwargs["transport_type"] = TransportType.AmqpOverWebsocket
            logger.info("Using WebSocket transport (VPN-compatible, port 443)")
        else:
            logger.info("Using AMQP transport (standard, port 5671)")

        return AzureServiceBusClient(**client_kwargs)

    async def setup(self) -> None:
        """Async setup to load secrets."""
        await self.segment_service.setup()

    # --- Testing Helpers ---

    async def get_messages(self, max_count: int) -> list[dict]:
        """Get some messages from the queue without removing (Async version for testing)."""
        messages = []

        async with self.client:
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

        logger.info(f"Peeked {len(messages)} messages from the queue.")
        return messages

    async def send_message(self, event: dict) -> None:
        """Send a message to the topic (for testing)."""
        try:
            logger.info(f"Starting send_message for event type: {event.get('eventType')}")
            async with asyncio.timeout(30):
                async with self.client:
                    sender = self.client.get_topic_sender(topic_name=self.topic_name)
                    async with sender:
                        msg = ServiceBusMessage(json.dumps(event))
                        await sender.send_messages(msg)

        except TimeoutError:
            logger.error("Send message timed out after 30 seconds")
            raise
        except Exception as e:
            logger.error(f"Failed to send message: {type(e).__name__}: {e}")
            raise

    async def flush_queue(self, max_count: int = 100) -> int:
        """Delete all messages from the queue (for testing/cleanup)."""
        completed_count = 0

        async with self.client:
            receiver = self.client.get_subscription_receiver(
                topic_name=self.topic_name, subscription_name=self.subscription_name
            )

            async with receiver:
                while True:
                    messages = await receiver.receive_messages(max_message_count=max_count, max_wait_time=5)
                    if not messages:
                        break

                    for msg in messages:
                        await receiver.complete_message(msg)
                        completed_count += 1

                    logger.info(f"Completed batch of {len(messages)} messages...")

        logger.info(f"Flushed {completed_count} messages from the queue.")
        return completed_count

    # --- Test save output results ---

    def _save_results_to_file(self, lead: Lead, result_dict: dict) -> None:
        """Save enrichment results to file for inspection."""
        if config.ENVIRONMENT != "development":
            return

        from pathlib import Path

        results_dir = Path("results")
        results_dir.mkdir(exist_ok=True)

        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}-{lead.id}.json"
        filepath = results_dir / filename

        output = {"lead": lead.model_dump(mode="json"), "results": result_dict}

        with open(filepath, "w") as f:
            json.dump(output, f, indent=2)

        logger.info(f"Results saved to {filepath}")

    # --- Event Publishing ---

    async def _publish_enrichment_events(
        self,
        correlation_id: str,
        source_system_record_id: str,
        lead: Lead,
        result: PipelineResult,
    ) -> None:
        """Publish enrichment events for each enrichment type."""
        result_dict = result.model_dump(mode="json")

        for enrichment_type, enrichment_result in result_dict.items():
            if enrichment_result is not None:
                output_event = OutgoingEventType.for_enrichment_type(enrichment_type)
                await self.publish(
                    event_type=output_event.value,
                    event_data=enrichment_result,
                    correlation_id=correlation_id,
                    source_system_record_id=source_system_record_id,
                )

        # Publish pipeline completion if all enrichments ran
        if all(r is not None for r in result_dict.values()):
            await self.publish(
                event_type=OutgoingEventType.PIPELINE_COMPLETED.value,
                event_data={"leadId": lead.id, "status": "success"},
                correlation_id=correlation_id,
                source_system_record_id=source_system_record_id,
            )

        # TEMP - SAVE TO FILE
        self._save_results_to_file(lead, result_dict)

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
            event_id = event_body.get("eventId", "unknown")
            event_type_str = event_body.get("eventType")

            # Source System
            source_system = event_body.get("sourceSystem")
            source_system_record_id = event_body.get("sourceSystemRecordID", "unknown")
            logger.info(f"Event received: {event_type_str} | id={event_id} | source={source_system} | Processing...")

            # Skip our own published events
            if source_system == "lead-enrichment":
                logger.info(f"Skipping own event: {event_type_str}")
                await receiver.complete_message(message)
                return

            event_type = IncomingEventType.from_string(event_type_str)
            if event_type is None:
                logger.warning(f"Event type '{event_type_str}' not accepted. Dead-lettering.")
                await receiver.dead_letter_message(
                    message,
                    reason="UnknownEventType",
                    error_description=f"Event type '{event_type_str}' not in accepted list",
                )
                return

            result = PipelineResult()

            # --- STEP 1: ENRICHMENT ---
            try:
                lead = Lead.from_event(event_body)

                if event_type == IncomingEventType.LEAD_ENRICHMENT:
                    result.lead = await self.orchestrator.run_lead_enrichment(lead)

                elif event_type == IncomingEventType.COMPANY_ENRICHMENT:
                    result.company = await self.orchestrator.run_company_enrichment(lead)

                elif event_type == IncomingEventType.CARGO_ENRICHMENT:
                    result.cargo = await self.orchestrator.run_cargo_enrichment(lead)

                elif event_type.is_full_pipeline():
                    result = await self.orchestrator.run_pipeline(lead)

                await self._publish_enrichment_events(event_id, source_system_record_id, lead, result)
                event_body["enrichment"] = result.model_dump()
                logger.info(f"Enrichment successful for lead {lead.id}")

            except Exception as enrich_err:
                logger.error(f"Enrichment failed (continuing to archive raw event): {enrich_err}")
                event_body["enrichment_error"] = str(enrich_err)

            # # --- STEP 2: DISPATCH (Side Effects) ---
            # # Prepare data objects using Schemas
            # bq_row = BigQueryRow.from_message(message, event_body)
            # segment_event = SegmentTrackEvent.from_message(message, event_body)

            # # Send to BQ and Segment in parallel
            # dispatch_results = await asyncio.gather(
            #     self.bq_service.add_row(bq_row), self.segment_service.track(segment_event), return_exceptions=True
            # )

            # # Check results (Strict Reliability: Fail if any service returns False/Exception)
            # has_failures = any(isinstance(res, Exception) or res is False for res in dispatch_results)

            # if has_failures:
            #     # This raises an exception, which jumps to the `except` block below.
            #     # The message is NOT ACKed, so Azure will redeliver it.
            #     raise Exception("Downstream dispatch failed. NACKing message.")

            # --- STEP 3: COMPLETE (ACK) ---
            await receiver.complete_message(message)
            logger.info(f"Message {message.message_id} completed")

        except Exception as e:
            logger.error(f"Processing failed for message {message.message_id}: {e}")

    async def listen(self) -> None:
        """Start the listener loop."""
        await self.setup()

        # Start the periodic flusher for BigQuery
        self._flusher_task = asyncio.create_task(self._periodic_flusher())

        try:
            async with self.client:
                receiver = self.client.get_subscription_receiver(
                    topic_name=self.topic_name,
                    subscription_name=self.subscription_name,
                    max_lock_renewal_duration=300,  # 5 minutes
                )
                async with receiver:
                    logger.info(f"Listening on {self.topic_name}/{self.subscription_name}")
                    async for msg in receiver:
                        await self._handle_message(msg, receiver)
        except asyncio.CancelledError:
            logger.info("Listener task cancelled. Shutting down...")
        except Exception as e:
            logger.error(f"Listener error: {e}")
            raise

    async def publish(
        self, event_type: str, event_data: dict, correlation_id: str | None, source_system_record_id: str | None = None
    ) -> None:
        """Publish an event to Service Bus."""
        event = {
            "eventId": str(uuid.uuid4()),
            "eventType": event_type,
            "eventVersion": "1.0",
            "eventTimestamp": datetime.now(UTC).isoformat(),
            "sourceSystem": "lead-enrichment",
            "sourceSystemRecordId": source_system_record_id,
            "correlationId": correlation_id,
            "data": event_data,
        }

        sender = self.client.get_topic_sender(topic_name=self.topic_name)
        async with sender:
            msg = ServiceBusMessage(json.dumps(event), subject=event_type, correlation_id=correlation_id)
            await sender.send_messages(msg)
            logger.info(f"Published event: {event_type}")

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
