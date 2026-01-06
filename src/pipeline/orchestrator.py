# src/pipelines/orchestrator.py
"""
Pipeline orchestrator that runs enrichment steps sequentially
and publishes events after each step completion.
"""

import asyncio

from common.logging import get_logger
from enrichments.company.enrich import enrich_company
from models.lead import Lead
from services.service_bus.client import ServiceBusClient

logger = get_logger(__name__)


class PipelineOrchestrator:
    """Orchestrates enrichment pipeline steps with event publishing."""

    def __init__(self):
        self.service_bus = ServiceBusClient()

    async def run_company_enrichment(self, lead: Lead):
        """Run company enrichment and publish event."""
        logger.info(f"Starting company enrichment for lead: {lead.id}")

        result = await enrich_company(lead)
        data = result.model_dump() if result else None

        # Publish completion event
        self.service_bus.publish(
            event_type="lead.enriched.company",
            event_data={"leadId": lead.id, "result": data},
        )

        return data

    async def run_cargo_enrichment(self, lead: Lead):
        """Run cargo enrichment and publish event."""
        logger.info(f"Starting cargo enrichment for lead: {lead.id}")

        # TODO: Implement cargo_enrichment
        # result = await enrich_cargo(lead)
        data = {"status": "not_implemented"}

        # Publish completion event
        self.service_bus.publish(
            event_type="lead.enriched.cargo",
            event_data={"leadId": lead.id, "result": data},
        )

        return data

    async def run_full_pipeline(self, lead: Lead):
        """
        Run all enrichment steps .
        Each step publishes its own completion event.
        """

        result = {
            "company": None,
            "cargo": None,
            # "other": None,
        }

        company_result = await self.run_company_enrichment(lead)
        result["company"] = company_result.model_dump() if company_result else None

        cargo_result = await self.run_cargo_enrichment(lead)
        result["cargo"] = cargo_result.model_dump() if cargo_result else None

        # Publish pipeline completed event
        self.event_publisher.publish(
            event_type="lead.enrichment.completed",
            event_data={
                "steps": result,
            },
        )

        return result

    async def run_full_pipeline_parallel(self, lead: Lead):
        """
        Run all enrichment steps in parallel.
        """
        result = {
            "company": None,
            "cargo": None,
            # "other": None,
        }

        company_result, cargo_result = await asyncio.gather(
            self.run_company_enrichment(lead),
            self.run_cargo_enrichment(lead),
        )

        result["company"] = company_result.model_dump() if company_result else None
        result["cargo"] = cargo_result.model_dump() if cargo_result else None

        return result
