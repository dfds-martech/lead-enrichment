"""
Cargo enrichment orchestrator.

Orchestrates the cargo enrichment process:
1. Extraction - LLM-based cargo information extraction from lead data
2. Features - extract categorized features from extraction results
"""

from agents import Agent, Runner

from common.logging import get_logger
from common.openai_errors import handle_openai_errors
from enrichments.cargo.agents.cargo_extraction import CargoExtractionResult, create_cargo_extraction_agent
from enrichments.cargo.features import extract_cargo_features
from enrichments.cargo.schemas import CargoEnrichmentResult
from models.lead import Lead

logger = get_logger(__name__)


class CargoEnricher:
    """Cargo enrichment orchestrator."""

    def __init__(self):
        self._extraction_agent: Agent[CargoExtractionResult] | None = None

    @property
    def extraction_agent(self) -> Agent[CargoExtractionResult]:
        if self._extraction_agent is None:
            self._extraction_agent = create_cargo_extraction_agent()
        return self._extraction_agent

    def _build_prompt(self, lead: Lead) -> str:
        """Build extraction prompt from lead data."""
        sections = []

        # Quote (cargo description, form fields, notes)
        quote_prompt = lead.quote.to_prompt()
        if quote_prompt:
            sections.append(quote_prompt)

        # Route (Lead-level)
        route_parts = []
        if lead.collection.get("city") or lead.collection.get("country"):
            origin = ", ".join(filter(None, [lead.collection.get("city"), lead.collection.get("country")]))
            if origin:
                route_parts.append(f"- From: {origin}")
        if lead.delivery.get("city") or lead.delivery.get("country"):
            dest = ", ".join(filter(None, [lead.delivery.get("city"), lead.delivery.get("country")]))
            if dest:
                route_parts.append(f"- To: {dest}")

        if route_parts:
            sections.append("<Route>\n" + "\n".join(route_parts) + "\n</Route>")

        return "\n\n".join(sections) if sections else "No cargo information provided."

    def inspect_prompt(self, lead: Lead) -> str:
        prompt = self._build_prompt(lead)
        print(prompt)

    async def _extract(self, lead: Lead) -> CargoExtractionResult:
        """Run the cargo extraction agent."""
        prompt = self._build_prompt(lead)

        logger.info(f"[Cargo] Starting extraction for lead: {lead.id}")

        with handle_openai_errors("Cargo Extraction"):
            run_result = await Runner.run(self.extraction_agent, prompt)

        result = run_result.final_output
        if result is None:
            error = f"extraction returned None for lead: {lead.id}"
            logger.error(f"[Cargo] {error}")
            raise ValueError(error)

        logger.info(f"[Cargo] Extracted - commodity_type: {result.commodity_type}, unit_type: {result.unit_type}")
        return result

    async def enrich(self, lead: Lead) -> CargoEnrichmentResult:
        """Run cargo enrichment through all stages."""
        extraction = None
        features = None
        errors: list[str] = []

        # Stage 1: Extraction (best effort)
        try:
            extraction = await self._extract(lead)
        except Exception as e:
            errors.append(f"extraction: {type(e).__name__}: {e}")
            logger.warning(f"[Cargo] Extraction failed: {e!r}")

        # Stage 2: Feature Extraction (best effort, handles None inputs)
        try:
            features = extract_cargo_features(extraction)
        except Exception as e:
            errors.append(f"features: {type(e).__name__}: {e}")
            logger.warning(f"[Cargo] Feature extraction failed: {e!r}")

        # Log final status
        if errors:
            logger.warning(f"[Cargo] Completed with {len(errors)} error(s): {errors}")
        else:
            logger.info("[Cargo] Completed successfully")

        return CargoEnrichmentResult(
            extraction=extraction,
            features=features,
            error="; ".join(errors) if errors else None,
        )
