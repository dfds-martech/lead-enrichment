"""
Company enrichment orchestrator.

Orchestrates the 4-stage company enrichment process:
1. Research - web search and scraping to find company information
2. Match - find the company in Orbis database using enriched data
3. Details - fetch detailed financial/employee data from Orbis
4. Features - extract categorized features from company data
"""

import json

from agents import Agent, Runner

from common.logging import get_logger
from common.openai_errors import handle_openai_errors
from custom_agents.company_match import CompanyMatchResult, create_company_match_agent
from custom_agents.company_research import CompanyResearchResult, create_company_research_agent
from enrichments.company.features import extract_company_features
from models.company import CompanyResearchCriteria
from models.enrichment import CompanyEnrichmentResult
from models.lead import Lead
from services.orbis.client import OrbisClient
from services.orbis.schemas import OrbisCompanyDetails

logger = get_logger(__name__)


class CompanyEnricher:
    """Company enrichment orchestrator with lazy-loaded agents."""

    def __init__(self):
        self._research_agent: Agent[CompanyResearchResult] | None = None
        self._match_agent: Agent[CompanyMatchResult] | None = None
        self._orbis_client: OrbisClient | None = None

    @property
    def research_agent(self) -> Agent[CompanyResearchResult]:
        if self._research_agent is None:
            self._research_agent = create_company_research_agent()
        return self._research_agent

    @property
    def match_agent(self) -> Agent[CompanyMatchResult]:
        if self._match_agent is None:
            self._match_agent = create_company_match_agent()
        return self._match_agent

    @property
    def orbis_client(self) -> OrbisClient:
        if self._orbis_client is None:
            self._orbis_client = OrbisClient()
        return self._orbis_client

    async def _research(self, criteria: CompanyResearchCriteria) -> CompanyResearchResult:
        logger.info(f"[Research] Starting for: {criteria.name}")

        research_input = criteria.to_prompt()
        logger.debug(f"[Research] Prompt length: {len(research_input)} chars")

        with handle_openai_errors("Research"):
            logger.debug("[Research] Runner.run()...start")
            run_result = await Runner.run(self.research_agent, research_input)
            logger.debug(f"[Research] Runner.run()...complete, result type: {type(run_result)}")

        result = run_result.final_output
        if result is None:
            logger.error("[Research] final_output is None")
            raise ValueError("Research agent returned None")

        logger.info(f"[Research] Completed - domain: {result.domain}, national_id: {result.national_id}")
        return result

    async def _match(
        self, criteria: CompanyResearchCriteria, research_result: CompanyResearchResult | None
    ) -> CompanyMatchResult:
        logger.info(f"[Match] Starting for: {criteria.name}")

        match_input = {
            "original": criteria.model_dump(exclude_none=True),
            "enriched": research_result.model_dump(exclude_none=True) if research_result else {},
        }
        logger.debug(f"[Match] Input has enriched data: {research_result is not None}")

        with handle_openai_errors("Match"):
            logger.debug("[Match] Calling Runner.run()...")
            run_result = await Runner.run(self.match_agent, json.dumps(match_input))
            logger.debug(f"[Match] Runner.run() completed, result type: {type(run_result)}")

        result = run_result.final_output
        if result is None:
            logger.error("[Match] final_output is None")
            raise ValueError("Match agent returned None")

        logger.info(f"[Match] Completed - Confidence: {result.confidence}")
        return result

    async def _fetch_details(self, bvd_id: str) -> OrbisCompanyDetails | None:
        logger.info(f"[Details] Fetching company details for BvD ID: {bvd_id}")

        try:
            company_details = self.orbis_client.company_lookup_by_bvd(bvd_id)
        except Exception as e:
            logger.error(f"[Details] Failed to fetch company details: {e}", exc_info=True)
            return None

        if not company_details:
            logger.warning(f"[Details] Fetch returned None for BvD ID: {bvd_id}")
            return None

        logger.info(f"[Details] fetched: {company_details.name} (BvD ID: {company_details.bvd_id})")
        return company_details

    async def enrich(self, lead: Lead) -> CompanyEnrichmentResult:
        """Run company enrichment through all stages."""
        criteria = lead.company_research_criteria

        company_research = None
        company_match = None
        company_details = None
        features = None
        error = None

        try:
            # Stage 1: Research (best effort - failures don't stop the pipeline)
            try:
                company_research = await self._research(criteria)
            except Exception as e:
                logger.warning(f"[Enrichment] Research failed, continuing: {type(e).__name__}: {e!r}")

            # Stage 2: Company Match
            company_match = await self._match(criteria, company_research)

            # Stage 3: Company Details
            if company_match.company:
                company_details = await self._fetch_details(company_match.company.bvd_id)

            # Stage 4: Feature Extraction
            features = extract_company_features(company_research, company_match, company_details)

            logger.info("[Enrichment] Completed successfully")

        except RuntimeError as e:
            # RuntimeError from handle_openai_errors contains formatted OpenAI error message
            error = str(e)
            logger.error(f"[Enrichment] OpenAI API error: {error}", exc_info=True)

        except Exception as e:
            # Log full exception details for debugging
            logger.error(
                f"[Enrichment] Failed: {type(e).__name__}: {e!r}",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "error_str": str(e),
                    "error_repr": repr(e),
                    "company_name": criteria.name,
                },
            )
            error = f"{type(e).__name__}: {e}"

        return CompanyEnrichmentResult(
            research=company_research,
            match=company_match,
            details=company_details,
            features=features,
            error=error,
        )
