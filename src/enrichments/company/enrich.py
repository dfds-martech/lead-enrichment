"""
Company enrichment orchestrator.

Orchestrates the 3-stage company enrichment process:
1. Research - web search and scraping to find company information
2. Match - find the company in Orbis database using enriched data
3. Details - fetch detailed financial/employee data from Orbis
"""

from common.logging import get_logger
from enrichments.company.orbis_match import fetch_company_details_from_orbis, match_company_in_orbis
from enrichments.company.research import research_company
from models.enrichment import CompanyEnrichmentResult
from models.lead import Lead

logger = get_logger(__name__)


async def enrich_company(lead: Lead) -> CompanyEnrichmentResult:
    """
    Run company enrichment through all stages.

    Research failures are non-fatal - the pipeline continues with original criteria.
    Match/Details failures are captured in the error field.

    Args:
        lead: Lead object containing company information to enrich

    Returns:
        CompanyEnrichmentResult containing research, match, and details (if found)
    """
    criteria = lead.company_research_criteria

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

        # Stage 2: Company Match
        match_result = await match_company_in_orbis(criteria, research_result)

        # Stage 3: Company Details
        if match_result.company:
            company_details = await fetch_company_details_from_orbis(match_result.company.bvd_id)

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
        research=research_result,
        match=match_result,
        details=company_details,
        error=error,
    )
