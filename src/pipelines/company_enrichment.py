"""
Company enrichment pipeline.

Orchestrates the 3-stage company enrichment process:
1. Research - web search and scraping to find company information
2. Match - find the company in Orbis database using enriched data
3. Details - fetch detailed financial/employee data from Orbis
"""

import json

from agents import Runner

from common.logging import get_logger
from custom_agents.company_match import CompanyMatchResult, create_company_match_agent
from custom_agents.company_research import CompanyResearchResult, create_company_research_agent
from models.company import CompanyResearchCriteria
from models.enrichment import CompanyEnrichmentResult
from services.orbis.client import OrbisClient
from services.orbis.schemas import OrbisCompanyDetails

logger = get_logger(__name__)


async def research_company(criteria: CompanyResearchCriteria) -> CompanyResearchResult:
    """
    Stage 1: Research company using web search and scraping.

    Args:
        criteria: CompanyResearchCriteria with company information

    Returns:
        CompanyResearchResult with enriched company data
    """
    logger.info(f"Researching company: {criteria.name}")
    research_agent = create_company_research_agent()
    research_input = criteria.to_prompt()

    run_result = await Runner.run(research_agent, research_input)
    result = run_result.final_output

    logger.info(f"Research completed - domain: {result.domain}, national_id: {result.national_id}")
    return result


async def match_company_in_orbis(
    criteria: CompanyResearchCriteria, research_result: CompanyResearchResult
) -> CompanyMatchResult:
    """
    Stage 2: Match company in Orbis database.

    Args:
        criteria: Original company criteria
        research_result: Enriched research data

    Returns:
        CompanyMatchResult with match information
    """
    logger.info("Matching company in Orbis database")
    match_agent = create_company_match_agent()
    match_input = {
        "original": criteria.model_dump(indent=2, exclude_none=True),
        "enriched": research_result.model_dump(indent=2, exclude_none=True),
    }

    run_result = await Runner.run(match_agent, json.dumps(match_input))
    result = run_result.final_output

    logger.info(f"Match completed - matched: {result.matched}, confidence: {result.confidence}")
    return result


def fetch_company_details(bvd_id: str) -> OrbisCompanyDetails | None:
    """
    Stage 3: Fetch detailed company data from Orbis.

    Args:
        bvd_id: Orbis BvD ID of the matched company

    Returns:
        OrbisCompanyDetails if found, None otherwise
    """
    logger.info(f"Fetching company details for BvD ID: {bvd_id}")
    orbis_client = OrbisClient()
    details = orbis_client.company_lookup_by_bvd(bvd_id)

    if details:
        logger.info(f"Details fetched - employees: {details.employees}, revenue: {details.operating_revenue}")
    else:
        logger.warning(f"Details fetch returned None for BvD ID: {bvd_id}")

    return details


async def enrich_company(criteria: CompanyResearchCriteria) -> CompanyEnrichmentResult:
    """
    Run company enrichment through all stages.

    Args:
        criteria: CompanyResearchCriteria with company information to enrich

    Returns:
        CompanyEnrichmentResult containing research, match, and details (if found)
    """
    research_result = None
    match_result = None
    details = None
    error = None

    try:
        # Stage 1: Research
        research_result = await research_company(criteria)

        # Stage 2: Match
        match_result = await match_company_in_orbis(criteria, research_result)

        # Stage 3: Details (only if matched)
        if match_result.matched and match_result.match and match_result.match.bvd_id:
            details = fetch_company_details(match_result.match.bvd_id)

        logger.info("Company enrichment completed successfully")

    except Exception as e:
        logger.error(f"Error in company enrichment: {e}", exc_info=True)
        error = str(e)

    return CompanyEnrichmentResult(
        research=research_result,
        match=match_result,
        details=details,
        error=error,
    )
