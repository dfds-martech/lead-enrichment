# src/pipelines/orchestrator.py
"""
Pipeline orchestrator that runs enrichment steps sequentially.

Pure orchestration - no event publishing or side effects.
Returns enrichment results for downstream processing.
"""

from __future__ import annotations

import asyncio

from pydantic import BaseModel

from common.logging import get_logger
from enrichments.cargo.enricher import CargoEnricher
from enrichments.cargo.schemas import CargoEnrichmentResult
from enrichments.company.enricher import CompanyEnricher
from enrichments.company.schemas import CompanyEnrichmentResult
from enrichments.lead.enricher import LeadEnricher
from enrichments.lead.schemas import LeadEnrichmentResult
from models.lead import Lead

logger = get_logger(__name__)


class PipelineResult(BaseModel):
    lead: LeadEnrichmentResult | None = None
    company: CompanyEnrichmentResult | None = None
    cargo: CargoEnrichmentResult | None = None


class PipelineOrchestrator:
    """Orchestrates enrichment pipeline steps."""

    def __init__(self):
        self.lead_enricher = LeadEnricher()
        self.company_enricher = CompanyEnricher()
        self.cargo_enricher = CargoEnricher()

    async def run_lead_enrichment(self, lead: Lead) -> LeadEnrichmentResult:
        logger.info(f"Starting lead enrichment for lead: {lead.id}")
        return await self.lead_enricher.enrich(lead)

    async def run_company_enrichment(self, lead: Lead) -> CompanyEnrichmentResult:
        logger.info(f"Starting company enrichment for lead: {lead.id}")
        return await self.company_enricher.enrich(lead)

    async def run_cargo_enrichment(self, lead: Lead) -> CargoEnrichmentResult:
        logger.info(f"Starting cargo enrichment for lead: {lead.id}")
        return await self.cargo_enricher.enrich(lead)

    async def run_pipeline(self, lead: Lead) -> PipelineResult:
        """Run enrichments steps sequentially."""

        result = PipelineResult(
            lead=None,
            company=None,
            cargo=None,
        )

        result.lead = await self.run_lead_enrichment(lead)
        result.company = await self.run_company_enrichment(lead)
        result.cargo = await self.run_cargo_enrichment(lead)

        return result

    async def run_pipeline_parallel(self, lead: Lead) -> PipelineResult:
        """Run enrichments in parallel."""

        result = PipelineResult(
            lead=None,
            company=None,
            cargo=None,
        )

        result.lead, result.company, result.cargo = await asyncio.gather(
            self.run_lead_enrichment(lead),
            self.run_company_enrichment(lead),
            self.run_cargo_enrichment(lead),
        )

        return result
