# tests/services/service_bus/test_client.py
"""
Tests for Service Bus client/listener.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.crm_service import CRMService
from services.service_bus.client import ServiceBusClient


@pytest.fixture
def crm_service():
    """Fixture for CRM service."""
    return CRMService()


@pytest.fixture
def mock_lead_event(crm_service):
    """Fixture that returns a mock lead event from CRM service."""
    return crm_service.mock_lead_event(0)


@pytest.fixture
def service_bus_client():
    """Fixture that creates a ServiceBusClient with mocked dependencies."""
    with patch("services.service_bus.client.AzureServiceBusClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.from_connection_string.return_value = mock_client

        with patch("services.service_bus.client.PipelineOrchestrator") as mock_orchestrator_class:
            mock_orchestrator = AsyncMock()
            mock_orchestrator_class.return_value = mock_orchestrator

            client = ServiceBusClient()
            client.orchestrator = mock_orchestrator
            yield client, mock_orchestrator


@pytest.mark.asyncio
async def test_handle_message_lead_created(service_bus_client, mock_lead_event):
    """Test handling a lead.created event."""
    client, mock_orchestrator = service_bus_client

    # Create a mock message
    mock_message = AsyncMock()
    mock_lead_event["eventType"] = "lead.created"
    mock_message.__str__ = lambda x: json.dumps(mock_lead_event)

    # Call the handler
    await client._handle_message(mock_message)

    # Verify orchestrator was called
    mock_orchestrator.run_full_pipeline.assert_called_once()

    # Verify message was completed
    mock_message.complete.assert_called_once()


@pytest.mark.asyncio
async def test_handle_message_lead_enrich_company(service_bus_client, mock_lead_event):
    """Test handling a lead.enrich.company event."""
    client, mock_orchestrator = service_bus_client

    # Create a mock message
    mock_message = AsyncMock()
    mock_lead_event["eventType"] = "lead.enrich.company"
    mock_message.__str__ = lambda x: json.dumps(mock_lead_event)

    # Call the handler
    await client._handle_message(mock_message)

    # Verify only company enrichment was called
    mock_orchestrator.run_company_enrichment.assert_called_once()
    mock_orchestrator.run_full_pipeline.assert_not_called()

    # Verify message was completed
    mock_message.complete.assert_called_once()


@pytest.mark.asyncio
async def test_handle_message_with_crm_mock_event(service_bus_client, mock_lead_event):
    """Test listener with a real CRM mock event - verifies Lead conversion."""
    client, mock_orchestrator = service_bus_client

    # Set event type
    mock_lead_event["eventType"] = "lead.created"

    # Create mock message
    mock_message = AsyncMock()
    mock_message.__str__ = lambda x: json.dumps(mock_lead_event)

    # Process message
    await client._handle_message(mock_message)

    # Verify orchestrator was called
    assert mock_orchestrator.run_full_pipeline.called

    # Verify Lead was created correctly from the event
    call_args = mock_orchestrator.run_full_pipeline.call_args
    lead = call_args[0][0]  # First positional argument

    # Verify lead has correct identifiers
    assert lead.identifiers.get("crm_lead_id") == mock_lead_event["lead"]["crmLeadId"]
    assert lead.company.get("name") == mock_lead_event["company"]["name"]

    # Verify message was completed
    mock_message.complete.assert_called_once()


@pytest.mark.asyncio
async def test_handle_message_error_handling(service_bus_client, mock_lead_event):
    """Test error handling when processing fails."""
    client, mock_orchestrator = service_bus_client

    # Make orchestrator raise an exception
    mock_orchestrator.run_full_pipeline.side_effect = Exception("Test error")

    # Create a mock message
    mock_message = AsyncMock()
    mock_lead_event["eventType"] = "lead.created"
    mock_message.__str__ = lambda x: json.dumps(mock_lead_event)

    # Call the handler
    await client._handle_message(mock_message)

    # Verify message was NOT completed (should retry)
    mock_message.complete.assert_not_called()
