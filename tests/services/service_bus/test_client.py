import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_message():
    """Create a mock Service Bus message."""
    msg = MagicMock()
    msg.message_id = "test-message-id"
    msg.subject = "lead.created"
    msg.enqueued_time_utc = None
    return msg


@pytest.fixture
def mock_receiver():
    """Create a mock Service Bus receiver."""
    return AsyncMock()


@pytest.fixture
def sample_event():
    """Minimal valid event payload."""
    return {
        "eventType": "lead.created",
        "lead": {"crmLeadId": "test-lead-123"},
        "company": {"name": "Test Corp"},
    }


@pytest.mark.asyncio
async def test_handle_message_calls_orchestrator(mock_message, mock_receiver, sample_event):
    """Test that _handle_message calls the orchestrator for accepted events."""
    # Add required fields for valid event
    sample_event["eventId"] = "test-event-id"
    sample_event["sourceSystem"] = "test-system"
    sample_event["sourceSystemRecordID"] = "test-record-id"
    mock_message.__str__ = lambda x: json.dumps(sample_event)

    with (
        patch("services.service_bus.client.AzureServiceBusClient"),
        patch("services.service_bus.client.ClientSecretCredential"),
        patch("services.service_bus.client.config") as mock_config,
        patch("services.service_bus.client.PipelineOrchestrator") as mock_orch_class,
    ):
        # Disable BigQuery and Segment
        mock_config.BQPROJECTID = None
        mock_config.SERVICE_BUS_NAMESPACE = "test.servicebus.windows.net"
        mock_config.SERVICE_BUS_TOPIC_NAME = "test-topic"
        mock_config.SERVICE_BUS_SUBSCRIPTION_NAME = "test-subscription"
        mock_config.SERVICE_BUS_MAX_CONCURRENT = 10
        mock_config.SERVICE_BUS_USE_WEBSOCKET = True
        mock_config.ENVIRONMENT = "test"
        
        # Setup orchestrator mock
        mock_orch = AsyncMock()
        mock_orch.run_pipeline = AsyncMock(return_value=MagicMock())
        mock_orch_class.return_value = mock_orch

        from services.service_bus.client import ServiceBusClient

        client = ServiceBusClient()
        client.orchestrator = mock_orch

        await client._handle_message(mock_message, mock_receiver)

        mock_orch.run_pipeline.assert_called_once()
        mock_receiver.complete_message.assert_called_once_with(mock_message)


@pytest.mark.asyncio
async def test_handle_message_dead_letters_unknown_event(mock_message, mock_receiver):
    """Test that unknown event types are dead-lettered."""
    unknown_event = {
        "eventType": "unknown.event",
        "eventId": "test-event-id",
        "sourceSystem": "test-system",
    }
    mock_message.__str__ = lambda x: json.dumps(unknown_event)

    with (
        patch("services.service_bus.client.AzureServiceBusClient"),
        patch("services.service_bus.client.ClientSecretCredential"),
        patch("services.service_bus.client.config") as mock_config,
        patch("services.service_bus.client.PipelineOrchestrator"),
    ):
        mock_config.BQPROJECTID = None
        mock_config.SERVICE_BUS_NAMESPACE = "test.servicebus.windows.net"
        mock_config.SERVICE_BUS_TOPIC_NAME = "test-topic"
        mock_config.SERVICE_BUS_SUBSCRIPTION_NAME = "test-subscription"
        mock_config.SERVICE_BUS_MAX_CONCURRENT = 10
        mock_config.SERVICE_BUS_USE_WEBSOCKET = True
        mock_config.ENVIRONMENT = "test"
        
        from services.service_bus.client import ServiceBusClient

        client = ServiceBusClient()
        await client._handle_message(mock_message, mock_receiver)

        mock_receiver.dead_letter_message.assert_called_once()
        mock_receiver.complete_message.assert_not_called()


@pytest.mark.asyncio
async def test_handle_message_completes_after_enrichment_error(mock_message, mock_receiver, sample_event):
    """Test that message IS completed even when enrichment fails (after archiving)."""
    # Add required fields
    sample_event["eventId"] = "test-event-id"
    sample_event["sourceSystem"] = "test-system"
    sample_event["sourceSystemRecordID"] = "test-record-id"
    mock_message.__str__ = lambda x: json.dumps(sample_event)

    with (
        patch("services.service_bus.client.AzureServiceBusClient"),
        patch("services.service_bus.client.ClientSecretCredential"),
        patch("services.service_bus.client.config") as mock_config,
        patch("services.service_bus.client.PipelineOrchestrator") as mock_orch_class,
    ):
        mock_config.BQPROJECTID = None
        mock_config.SERVICE_BUS_NAMESPACE = "test.servicebus.windows.net"
        mock_config.SERVICE_BUS_TOPIC_NAME = "test-topic"
        mock_config.SERVICE_BUS_SUBSCRIPTION_NAME = "test-subscription"
        mock_config.SERVICE_BUS_MAX_CONCURRENT = 10
        mock_config.SERVICE_BUS_USE_WEBSOCKET = True
        mock_config.ENVIRONMENT = "test"
        
        # Setup orchestrator to fail
        mock_orch = AsyncMock()
        mock_orch.run_pipeline = AsyncMock(side_effect=Exception("Test error"))
        mock_orch_class.return_value = mock_orch

        from services.service_bus.client import ServiceBusClient

        client = ServiceBusClient()
        client.orchestrator = mock_orch

        await client._handle_message(mock_message, mock_receiver)

        # Message should still be completed after archiving (even though enrichment failed)
        mock_receiver.complete_message.assert_called_once_with(mock_message)


@pytest.mark.asyncio
async def test_handle_message_not_completed_on_fatal_error(mock_message, mock_receiver):
    """Test that message is NOT completed when a fatal error occurs (e.g., JSON parsing)."""
    # Invalid JSON will cause parsing error
    mock_message.__str__ = lambda x: "invalid json"

    with (
        patch("services.service_bus.client.AzureServiceBusClient"),
        patch("services.service_bus.client.ClientSecretCredential"),
        patch("services.service_bus.client.config") as mock_config,
        patch("services.service_bus.client.PipelineOrchestrator"),
    ):
        mock_config.BQPROJECTID = None
        mock_config.SERVICE_BUS_NAMESPACE = "test.servicebus.windows.net"
        mock_config.SERVICE_BUS_TOPIC_NAME = "test-topic"
        mock_config.SERVICE_BUS_SUBSCRIPTION_NAME = "test-subscription"
        mock_config.SERVICE_BUS_MAX_CONCURRENT = 10
        mock_config.SERVICE_BUS_USE_WEBSOCKET = True
        mock_config.ENVIRONMENT = "test"
        
        from services.service_bus.client import ServiceBusClient

        client = ServiceBusClient()
        await client._handle_message(mock_message, mock_receiver)

        # Message should NOT be completed on fatal error
        mock_receiver.complete_message.assert_not_called()
