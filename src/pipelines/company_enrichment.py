"""
Company enrichment pipeline.

Orchestrates the 3-stage company enrichment process:
1. Research - web search and scraping to find company information
2. Match - find the company in Orbis database using enriched data
3. Details - fetch detailed financial/employee data from Orbis
"""

import json

from agents import Runner
from openai import (
    APIConnectionError,
    APIError,
    AuthenticationError,
    PermissionDeniedError,
    RateLimitError,
)

from common.logging import get_logger
from custom_agents.company_match import CompanyMatchResult, create_company_match_agent
from custom_agents.company_research import CompanyResearchResult, create_company_research_agent
from models.company import CompanyResearchCriteria
from models.enrichment import CompanyEnrichmentResult
from services.orbis.client import OrbisClient
from services.orbis.schemas import OrbisCompanyDetails

logger = get_logger(__name__)


def _format_openai_error(e: Exception) -> str:
    """Extract a clean error message from OpenAI SDK exceptions."""
    error_type = type(e).__name__

    # Handle OpenAI-specific errors with better messages
    if isinstance(e, PermissionDeniedError):
        return f"Azure OpenAI access denied: {e.message}"
    elif isinstance(e, AuthenticationError):
        return f"Azure OpenAI authentication failed: {e.message}"
    elif isinstance(e, RateLimitError):
        return f"Azure OpenAI rate limit exceeded: {e.message}"
    elif isinstance(e, APIConnectionError):
        return f"Cannot connect to Azure OpenAI: {e.message}"
    elif isinstance(e, APIError):
        return f"Azure OpenAI API error ({e.status_code}): {e.message}"

    # For other exceptions, return type and message
    return f"{error_type}: {e}"


async def research_company(criteria: CompanyResearchCriteria) -> CompanyResearchResult:
    """
    Stage 1: Research company using web search and scraping.

    Args:
        criteria: CompanyResearchCriteria with company information

    Returns:
        CompanyResearchResult with enriched company data
    """
    logger.info(f"[Research] Starting for: {criteria.name}")

    try:
        research_agent = create_company_research_agent()
        logger.debug("[Research] Agent created successfully")
    except Exception as e:
        logger.error(f"[Research] Failed to create agent: {type(e).__name__}: {e}")
        raise

    research_input = criteria.to_prompt()
    logger.debug(f"[Research] Input prompt length: {len(research_input)} chars")

    try:
        logger.debug("[Research] Calling Runner.run()...")
        run_result = await Runner.run(research_agent, research_input)
        logger.debug(f"[Research] Runner.run() completed, result type: {type(run_result)}")
    except (PermissionDeniedError, AuthenticationError, RateLimitError, APIConnectionError, APIError) as e:
        error_msg = _format_openai_error(e)
        logger.error(f"[Research] OpenAI API error: {error_msg}")
        raise RuntimeError(error_msg) from e
    except Exception as e:
        logger.error(f"[Research] Runner.run() failed: {type(e).__name__}: {e!r}")
        raise

    result = run_result.final_output
    if result is None:
        logger.error("[Research] final_output is None")
        raise ValueError("Research agent returned None")

    logger.info(f"[Research] Completed - domain: {result.domain}, national_id: {result.national_id}")
    return result


async def match_company_in_orbis(
    criteria: CompanyResearchCriteria, research_result: CompanyResearchResult | None
) -> CompanyMatchResult:
    """
    Stage 2: Match company in Orbis database.

    Args:
        criteria: Original company criteria
        research_result: Enriched research data (can be None if research failed)

    Returns:
        CompanyMatchResult with match information
    """
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

    try:
        logger.debug("[Match] Calling Runner.run()...")
        run_result = await Runner.run(match_agent, json.dumps(match_input))
        logger.debug(f"[Match] Runner.run() completed, result type: {type(run_result)}")
    except (PermissionDeniedError, AuthenticationError, RateLimitError, APIConnectionError, APIError) as e:
        error_msg = _format_openai_error(e)
        logger.error(f"[Match] OpenAI API error: {error_msg}")
        raise RuntimeError(error_msg) from e
    except Exception as e:
        logger.error(f"[Match] Runner.run() failed: {type(e).__name__}: {e!r}")
        raise

    result = run_result.final_output
    if result is None:
        logger.error("[Match] final_output is None")
        raise ValueError("Match agent returned None")

    logger.info(f"[Match] Completed - Confidence: {result.confidence}")
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


async def enrich_company(criteria: CompanyResearchCriteria) -> CompanyEnrichmentResult:
    """
    Run company enrichment through all stages.

    Research failures are non-fatal - the pipeline continues with original criteria.
    Match/Details failures are captured in the error field.

    Args:
        criteria: CompanyResearchCriteria with company information to enrich

    Returns:
        CompanyEnrichmentResult containing research, match, and details (if found)
    """
    research_result = None
    match_result = None
    company_details = None
    error = None

    try:
        # Stage 1: Research (best effort - failures don't stop the pipeline)
        try:
            research_result = await research_company(criteria)
        except Exception as e:
            logger.warning(f"[Enrichment] Research failed, continuing: {type(e).__name__}: {e!r}")

        # Stage 2: Match
        match_result = await match_company_in_orbis(criteria, research_result)

        # Stage 3: Details (only if matched)
        if match_result.company:
            logger.debug(f"[Enrichment] Fetching details for BvD ID: {match_result.company.bvd_id}")
            company_details = fetch_company_details(match_result.company.bvd_id)

        logger.info("[Enrichment] Completed successfully")

    except (PermissionDeniedError, AuthenticationError, RateLimitError, APIConnectionError, APIError) as e:
        # Handle OpenAI errors with clear messages
        error = _format_openai_error(e)
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
        research=research_result,
        match=match_result,
        details=company_details,
        error=error,
    )
