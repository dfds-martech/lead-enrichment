# src/pipelines/orchestrator.py
"""
Pipeline orchestrator that runs enrichment steps sequentially
and publishes events after each step completion.
"""

from __future__ import annotations

import asyncio
from enum import Enum
from typing import TYPE_CHECKING

from common.logging import get_logger
from enrichments.cargo.enricher import CargoEnricher
from enrichments.cargo.schemas import CargoEnrichmentResult
from enrichments.company.enricher import CompanyEnricher
from enrichments.company.schemas import CompanyEnrichmentResult
from enrichments.lead.enricher import LeadEnricher
from enrichments.lead.schemas import LeadEnrichmentResult
from models.lead import Lead

if TYPE_CHECKING:
    from services.service_bus.client import ServiceBusClient

logger = get_logger(__name__)


class EventType(str, Enum):
    LEAD_ENRICHMENT = "lead.enriched.lead"
    COMPANY_ENRICHMENT = "lead.enriched.company"
    CARGO_ENRICHMENT = "lead.enriched.cargo"
    PIPELINE_COMPLETED = "lead.enrichment.completed"


class PipelineOrchestrator:
    """Orchestrates enrichment pipeline steps with optional event publishing."""

    def __init__(self, service_bus: ServiceBusClient | None = None):
        # Initialize service bus
        self.service_bus = service_bus

        # Initialize enrichers
        self.lead_enricher = LeadEnricher()
        self.company_enricher = CompanyEnricher()
        self.cargo_enricher = CargoEnricher()

    def _publish(self, event_type: EventType, event_data: dict):
        """Publish event if service bus is configured."""
        if self.service_bus:
            self.service_bus.publish(event_type=event_type, event_data=event_data)

    async def run_lead_enrichment(self, lead: Lead) -> LeadEnrichmentResult:
        """Run lead feature extraction."""
        logger.info(f"Starting lead enrichment for lead: {lead.id}")

        lead_result = await self.lead_enricher.enrich(lead)

        self._publish(
            event_type=EventType.LEAD_ENRICHMENT,
            event_data={"leadId": lead.id, "result": lead_result.model_dump()},
        )

        return lead_result

    async def run_company_enrichment(self, lead: Lead) -> CompanyEnrichmentResult:
        """Run company enrichment."""
        logger.info(f"Starting company enrichment for lead: {lead.id}")

        company_result = await self.company_enricher.enrich(lead)

        self._publish(
            event_type=EventType.COMPANY_ENRICHMENT,
            event_data={"leadId": lead.id, "result": company_result.model_dump()},
        )

        return company_result

    async def run_cargo_enrichment(self, lead: Lead) -> CargoEnrichmentResult:
        """Run cargo enrichment."""
        logger.info(f"Starting cargo enrichment for lead: {lead.id}")

        cargo_result = await self.cargo_enricher.enrich(lead)

        self._publish(
            event_type=EventType.CARGO_ENRICHMENT,
            event_data={"leadId": lead.id, "result": cargo_result.model_dump()},
        )

        return cargo_result

    async def run_pipeline(self, lead: Lead) -> dict:
        """Run enrichments steps sequentially."""

        result = {
            "lead": None,
            "company": None,
            "cargo": None,
        }

        result["lead"] = await self.run_lead_enrichment(lead)
        result["company"] = await self.run_company_enrichment(lead)
        result["cargo"] = await self.run_cargo_enrichment(lead)

        self._publish(
            event_type=EventType.PIPELINE_COMPLETED,
            event_data={"leadId": lead.id, "result": "success"},
        )

        return result

    async def run_pipeline_parallel(self, lead: Lead) -> dict:
        """Run enrichments in parallel."""

        result = {
            "lead": None,
            "company": None,
            "cargo": None,
        }

        lead_result, company_result, cargo_result = await asyncio.gather(
            self.run_lead_enrichment(lead),
            self.run_company_enrichment(lead),
            self.run_cargo_enrichment(lead),
        )

        result["lead"] = lead_result
        result["company"] = company_result
        result["cargo"] = cargo_result

        self._publish(
            event_type=EventType.PIPELINE_COMPLETED,
            event_data={"leadId": lead.id},
        )

        return result
