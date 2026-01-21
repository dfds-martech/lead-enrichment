import asyncio
import base64
import json
import re
from datetime import datetime

import httpx
from azure.identity import ClientSecretCredential
from azure.servicebus import ServiceBusMessage
from azure.servicebus.aio import ServiceBusClient as AzureServiceBusClient
from google.cloud import bigquery, secretmanager

from common.config import config
from common.logging import get_logger
from models.lead import Lead
from pipeline.orchestrator import PipelineOrchestrator

logger = get_logger(__name__)


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

        # Google Cloud Clients (BigQuery & Secret Manager)
        self.bq_client = bigquery.Client(project=config.BQPROJECTID)
        self.secret_client = secretmanager.SecretManagerServiceClient()
        
        # Pipeline Orchestrator (Passing self to allow publishing events) 
        self.orchestrator = PipelineOrchestrator(service_bus=self)

        # --- 2. State & Config ---
        self.bq_table_id = f"{config.BQPROJECTID}.{config.BQDATASETID}.{config.BQTABLEID}"
        self.bq_batch = []
        self.bq_batch_size = 50
        self.bq_batch_interval = 10  # Seconds
        self.bq_lock = asyncio.Lock()  # Prevent race conditions on the batch list
        
        self.segment_write_key = None
        self.gcp_project_id = config.GCPPROJECTID

    async def _get_secret(self, secret_id):
        """Helper to fetch secrets from Google Secret Manager (Async wrapper)."""
        if not secret_id:
            return None
            
        def fetch():
            # Build the resource name: projects/*/secrets/*/versions/latest
            name = f"projects/{self.gcp_project_id}/secrets/{secret_id}/versions/latest"
            response = self.secret_client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        
        try:
            return await asyncio.to_thread(fetch)
        except Exception as e:
            logger.error(f"Failed to fetch secret {secret_id}: {e}")
            return None

    
    async def setup(self):
        """Async setup to load secrets before listening."""
        # Retrieve Segment Write Key from Secret Manager using the ID from config
        if config.SEGMENT_WRITE_KEY_ID:
            logger.info("Fetching Segment Write Key from Secret Manager...")
            self.segment_write_key = await self._get_secret(config.SEGMENT_WRITE_KEY_ID)
            if self.segment_write_key:
                logger.info("Segment Write Key loaded successfully.")
        else:
            logger.warning("SEGMENT_WRITE_KEY_ID not set in config.")

    # --- Testing Helper (Async) ---

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

    # --- BigQuery Logic ---

    async def _flush_bq_batch(self):
        """Flushes the current batch to BigQuery."""
        async with self.bq_lock:
            if not self.bq_batch:
                return
            
            # Copy and clear batch
            rows_to_insert = list(self.bq_batch)
            self.bq_batch = []

        try:
            # Insert rows (blocking call run in thread)
            errors = await asyncio.to_thread(
                self.bq_client.insert_rows_json, self.bq_table_id, rows_to_insert
            )
            
            if not errors:
                logger.info(f"Successfully flushed {len(rows_to_insert)} rows to BigQuery.")
            else:
                logger.error(f"BigQuery errors: {errors}")
        except Exception as e:
            logger.error(f"Error flushing batch to BigQuery: {e}")

    async def _add_to_bq(self, message, event_body):
        """Adds a row to the local batch and triggers flush if full."""
        try:
            row = {
                "eventid": message.message_id,
                "eventtype": message.subject,
                "eventtimestamp": message.enqueued_time_utc.isoformat() if message.enqueued_time_utc else datetime.now().isoformat(),
                "leadid": event_body.get("crmLeadId"),
                "email": event_body.get("leadEmail"),
                "status": event_body.get("leadStatus"),
                "sourcename": event_body.get("sourceName"),
                "leadsource": event_body.get("leadSource"),
                "topic": event_body.get("leadTopic"),
                "reference_number": event_body.get("leadReferenceNumber"),
                "payload": json.dumps(event_body) # Stores the ENRICHED payload
            }

            async with self.bq_lock:
                self.bq_batch.append(row)
                current_size = len(self.bq_batch)
                
            logger.debug(f"Added lead {row.get('email')} to BQ batch. Size: {current_size}")

            if current_size >= self.bq_batch_size:
                await self._flush_bq_batch()
            
            return True # if successful
                
        except Exception as e:
            logger.error(f"Error preparing BigQuery row: {e}")
            return False # if failure

    async def _bq_periodic_flusher(self):
        """Background task to flush BQ every 10 seconds."""
        logger.info("Starting BigQuery periodic flusher.")
        while True:
            await asyncio.sleep(self.bq_batch_interval)
            await self._flush_bq_batch()

    # --- Segment Logic ---

    async def _send_to_segment(self, message, event_body):
        """Sends event to Segment API."""
        if not self.segment_write_key:
            return True # Treat as success if disabled

        try:
            # Clean event name (CamelCase to Space separated)
            subject = message.subject or "UnknownEvent"
            event_name = re.sub(r"([A-Z])", r" \1", subject).strip()

            payload = {
                "userId": event_body.get("leadEmail"),
                "event": event_name,
                "properties": event_body, # Sends ENRICHED properties
                "timestamp": message.enqueued_time_utc.isoformat() if message.enqueued_time_utc else datetime.now().isoformat()
            }

            # Auth Header
            auth_str = f"{self.segment_write_key}:"
            b64_auth = base64.b64encode(auth_str.encode("ascii")).decode("ascii")
            headers = {
                "Authorization": f"Basic {b64_auth}",
                "Content-Type": "application/json"
            }

            # Send async request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://events.eu1.segmentapis.com/v1/track",
                    json=payload,
                    headers=headers,
                    timeout=10.0
                )
                if response.is_error:
                    logger.error(f"Segment API Error ({response.status_code}): {response.text}")
                    return False # API error
                else:
                    logger.info(f"Sent '{event_name}' to Segment for: {payload['userId']}")
                    return True # Success

        except Exception as e:
            logger.error(f"Error sending to Segment: {e}")
            return False # Exception
            
    # --- Main Handling Logic (Enrich-First) ---

    async def _handle_message(self, message):
        """Process a single message: Enrich -> Dispatch (BQ/Segment)."""
        try:
            # body = json.loads(str(message))
            body_str = str(message)
            event_body = json.loads(body_str)
            event_type = event_body.get("eventType")

            logger.info(f"Received event: {event_type} | Processing...")

            # --- STEP 1: ENRICHMENT ---
            # We run enrichment FIRST so we can send better data to BQ and Segment
            enrichment_result = {}

            # Only enrich if it's a relevant lead event
            if event_type in ["lead.created", "lead.updated", "lead.enrich.company"]:
                try:
                    lead = Lead.from_event(event_body)

                    # Run the pipeline (this takes time)
                    if event_type == "lead.enrich.company":
                         # Special case if we only want company enrichment
                        enrichment_result = await self.orchestrator.run_company_enrichment(lead)
                        # Convert result model to dict if needed, or extract data
                        if hasattr(enrichment_result, "model_dump"):
                            enrichment_result = enrichment_result.model_dump()
                    else:
                        # Full pipeline
                        pipeline_results = await self.orchestrator.run_pipeline(lead)
                        # Simplify structure for flat event body if desired, or keep nested
                        enrichment_result = pipeline_results
                    
                    logger.info(f"Enrichment successful for lead {lead.id}")
                    
                    # MERGE: Add enrichment data into the event body
                    # This ensures BQ and Segment get the enriched info
                    event_body["enrichment"] = enrichment_result

                except Exception as enrich_err:
                    logger.error(f"Enrichment failed (continuing to archive raw event): {enrich_err}")
                    event_body["enrichment_error"] = str(enrich_err)
            
            # --- STEP 2: DISPATCH (Side Effects) ---
            # Send the (potentially enriched) data to BQ and Segment
            results = await asyncio.gather(
                self._add_to_bq(message, event_body),
                self._send_to_segment(message, event_body),
                return_exceptions=True
            )
            
            # Check for failures
            for res in results:
                if isinstance(res, Exception) or res is False: # Assuming functions return False/Exception on fail
                    logger.error("Downstream failure, NACKing message to retry.")
                    raise res # This jumps to the outer except block, skipping the ACK

            # --- STEP 3: COMPLETE ---
            await self.client.get_subscription_receiver(self.topic_name, self.subscription_name).complete_message(message)

        except Exception as e:
            logger.error(f"Critical error processing message: {e}", exc_info=True)
            # Do NOT complete message so it can be retried
            
    async def listen(self):
        """Start the listener loop."""
        await self.setup()
        asyncio.create_task(self._bq_periodic_flusher())

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

        async with self.client:
            sender = self.client.get_topic_sender(topic_name=self.topic_name)
            async with sender:
                msg = ServiceBusMessage(json.dumps(event), correlation_id=correlation_id)
                await sender.send_messages(msg)
                logger.info(f"Published event: {event_type}")
