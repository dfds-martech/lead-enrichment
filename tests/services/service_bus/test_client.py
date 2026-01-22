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
    mock_message.__str__ = lambda x: json.dumps(sample_event)

    with (
        patch("services.service_bus.client.AzureServiceBusClient"),
        patch("services.service_bus.client.ClientSecretCredential"),
        patch("services.service_bus.client.BigQueryClient") as mock_bq,
        patch("services.service_bus.client.SegmentClient") as mock_segment,
        patch("services.service_bus.client.PipelineOrchestrator") as mock_orch_class,
    ):
        # Setup mocks
        mock_bq.return_value.add_row = AsyncMock(return_value=True)
        mock_segment.return_value.track = AsyncMock(return_value=True)
        mock_orch = AsyncMock()
        mock_orch.run_pipeline = AsyncMock(return_value={})
        mock_orch_class.return_value = mock_orch

        from services.service_bus.client import ServiceBusClient

        client = ServiceBusClient()
        client.bq_service.add_row = AsyncMock(return_value=True)
        client.segment_service.track = AsyncMock(return_value=True)
        client.orchestrator = mock_orch

        await client._handle_message(mock_message, mock_receiver)

        mock_orch.run_pipeline.assert_called_once()
        mock_receiver.complete_message.assert_called_once_with(mock_message)


@pytest.mark.asyncio
async def test_handle_message_dead_letters_unknown_event(mock_message, mock_receiver):
    """Test that unknown event types are dead-lettered."""
    unknown_event = {"eventType": "unknown.event"}
    mock_message.__str__ = lambda x: json.dumps(unknown_event)

    with (
        patch("services.service_bus.client.AzureServiceBusClient"),
        patch("services.service_bus.client.ClientSecretCredential"),
        patch("services.service_bus.client.BigQueryClient"),
        patch("services.service_bus.client.SegmentClient"),
        patch("services.service_bus.client.PipelineOrchestrator"),
    ):
        from services.service_bus.client import ServiceBusClient

        client = ServiceBusClient()
        await client._handle_message(mock_message, mock_receiver)

        mock_receiver.dead_letter_message.assert_called_once()
        mock_receiver.complete_message.assert_not_called()


@pytest.mark.asyncio
async def test_handle_message_does_not_complete_on_error(mock_message, mock_receiver, sample_event):
    """Test that message is NOT completed when processing fails."""
    mock_message.__str__ = lambda x: json.dumps(sample_event)

    with (
        patch("services.service_bus.client.AzureServiceBusClient"),
        patch("services.service_bus.client.ClientSecretCredential"),
        patch("services.service_bus.client.BigQueryClient"),
        patch("services.service_bus.client.SegmentClient"),
        patch("services.service_bus.client.PipelineOrchestrator") as mock_orch_class,
    ):
        mock_orch = AsyncMock()
        mock_orch.run_pipeline = AsyncMock(side_effect=Exception("Test error"))
        mock_orch_class.return_value = mock_orch

        from services.service_bus.client import ServiceBusClient

        client = ServiceBusClient()
        client.orchestrator = mock_orch

        await client._handle_message(mock_message, mock_receiver)

        mock_receiver.complete_message.assert_not_called()
