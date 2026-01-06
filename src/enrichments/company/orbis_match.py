"""
Company matching and details fetching from Orbis.

Contains two stages:
1. Match - find company in Orbis database using enriched research data
2. Details - fetch detailed financial/employee data from Orbis
"""

import json

from agents import Runner

from common.logging import get_logger
from common.openai_errors import handle_openai_errors
from custom_agents.company_match import CompanyMatchResult, create_company_match_agent
from custom_agents.company_research import CompanyResearchResult
from models.company import CompanyResearchCriteria
from services.orbis.client import OrbisClient
from services.orbis.schemas import OrbisCompanyDetails

logger = get_logger(__name__)


async def match_company_in_orbis(
    criteria: CompanyResearchCriteria, research_result: CompanyResearchResult | None
) -> CompanyMatchResult:
    """Match company in Orbis database."""
    logger.info(f"[Match] Starting for: {criteria.name}")

    try:
        match_agent = create_company_match_agent()
        logger.debug("[Match] Agent created successfully")
    except Exception as e:
        logger.error(f"[Match] Failed to create agent: {type(e).__name__}: {e}")
        raise

    match_input = {
        "original": criteria.model_dump(exclude_none=True),
        "enriched": research_result.model_dump(exclude_none=True) if research_result else {},
    }
    logger.debug(f"[Match] Input has enriched data: {research_result is not None}")

    with handle_openai_errors("Match"):
        logger.debug("[Match] Calling Runner.run()...")
        run_result = await Runner.run(match_agent, json.dumps(match_input))
        logger.debug(f"[Match] Runner.run() completed, result type: {type(run_result)}")

    result = run_result.final_output
    if result is None:
        logger.error("[Match] final_output is None")
        raise ValueError("Match agent returned None")

    logger.info(f"[Match] Completed - Confidence: {result.confidence}")
    return result


async def fetch_company_details_from_orbis(bvd_id: str) -> OrbisCompanyDetails | None:
    """Fetch detailed company data from Orbis."""
    logger.info(f"Fetching company details for BvD ID: {bvd_id}")
    orbis_client = OrbisClient()

    try:
        company_details = orbis_client.company_lookup_by_bvd(bvd_id)
    except Exception as e:
        logger.error(f"Error fetching company details: {e}", exc_info=True)
        return None

    if not company_details:
        logger.warning(f"Details fetch returned None for BvD ID: {bvd_id}")
        return None

    logger.info(f"Details fetched: {company_details.name} (BvD ID: {company_details.bvd_id})")
    return company_details
