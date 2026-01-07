# src/pipelines/orchestrator.py
"""
Pipeline orchestrator that runs enrichment steps sequentially
and publishes events after each step completion.
"""

import asyncio
from enum import Enum

from common.logging import get_logger
from enrichments.company.enricher import CompanyEnricher
from models.lead import Lead
from services.service_bus.client import ServiceBusClient

logger = get_logger(__name__)


class EventType(str, Enum):
    COMPANY_ENRICHMENT = "lead.enriched.company"
    CARGO_ENRICHMENT = "lead.enriched.cargo"
    PIPELINE_COMPLETED = "lead.enrichment.completed"


class PipelineOrchestrator:
    """Orchestrates enrichment pipeline steps with event publishing."""

    def __init__(self):
        self.service_bus = ServiceBusClient()
        self.company_enricher = CompanyEnricher()

    async def run_company_enrichment(self, lead: Lead):
        logger.info(f"Starting company enrichment for lead: {lead.id}")

        enrichment_result = await self.company_enricher.enrich(lead)
        result = enrichment_result.model_dump() if enrichment_result else None

        self.service_bus.publish(
            event_type=EventType.COMPANY_ENRICHMENT,
            event_data={"leadId": lead.id, "result": result},
        )

        return result

    async def run_cargo_enrichment(self, lead: Lead):
        logger.info(f"Starting cargo enrichment for lead: {lead.id}")

        # enrichment_result = await enrich_cargo(lead)
        result = {"status": "not_implemented"}

        self.service_bus.publish(
            event_type=EventType.CARGO_ENRICHMENT,
            event_data={"leadId": lead.id, "result": result},
        )

        return result

    async def run_full_pipeline(self, lead: Lead):
        """Run enrichments steps sequentially."""

        result = {
            "company": None,
            "cargo": None,
            # "other": None,
        }

        result["company"] = await self.run_company_enrichment(lead)
        result["cargo"] = await self.run_cargo_enrichment(lead)

        self.event_publisher.publish(
            event_type=EventType.PIPELINE_COMPLETED,
            event_data={"leadId": lead.id, "result": result},
        )

        return result

    async def run_full_pipeline_parallel(self, lead: Lead):
        """Run enrichments in parallel."""

        result = {
            "company": None,
            "cargo": None,
            # "other": None,
        }

        company_result, cargo_result = await asyncio.gather(
            self.run_company_enrichment(lead),
            self.run_cargo_enrichment(lead),
        )

        result["company"] = company_result
        result["cargo"] = cargo_result

        return result
