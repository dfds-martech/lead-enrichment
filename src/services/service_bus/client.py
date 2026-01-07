import json
from datetime import datetime

from azure.servicebus import ServiceBusClient as AzureServiceBusClient
from azure.servicebus import ServiceBusMessage

from common.config import config
from common.logging import get_logger
from models.lead import Lead
from pipeline.orchestrator import PipelineOrchestrator

logger = get_logger(__name__)


class ServiceBusClient:
    """Service Bus listener for processing lead events."""

    def __init__(self):
        self.conn_str = config.SERVICE_BUS_CONNECTION_STRING
        self.topic_name = config.SERVICE_BUS_TOPIC_NAME
        self.subscription_name = "lead-enrich"
        self.client = AzureServiceBusClient.from_connection_string(self.conn_str)
        self.orchestrator = PipelineOrchestrator()

    async def _handle_message(self, message):
        """Process a single message from the queue."""
        try:
            body = json.loads(str(message))
            event_type = body.get("eventType")
            logger.info(f"Received event: {event_type}")

            # Convert event to Lead model
            lead = Lead.from_event(body)

            # Run enrichment
            match event_type:
                case "lead.created" | "lead.updated":
                    await self.orchestrator.run_full_pipeline(lead)

                case "lead.enrich.company":
                    await self.orchestrator.run_company_enrichment(lead)

                case "lead.enrich.cargo":
                    await self.orchestrator.run_cargo_enrichment(lead)

                case _:
                    logger.warning(f"Unknown event type: {event_type}")

            logger.info(f"Enrichment completed for lead: {lead.id}")
            await message.complete()

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            # Don't complete - let it retry or dead-letter
            # Optionally: await message.dead_letter(reason=str(e))

    async def listen(self):
        """Listen for messages on the Service Bus."""
        async with self.client:
            receiver = self.client.get_subscription_receiver(
                topic_name=self.topic_name, subscription_name=self.subscription_name
            )
            async with receiver:
                logger.info(f"Listening on {self.topic_name}/{self.subscription_name}")
                async for msg in receiver:
                    await self._handle_message(msg)

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

        with self.client:
            sender = self.client.get_topic_sender(topic_name=self.topic_name)
            with sender:
                msg = ServiceBusMessage(json.dumps(event), correlation_id=correlation_id or event.get("correlationId"))
                sender.send_messages(msg)
                logger.info(f"Published event: {event_type}")
