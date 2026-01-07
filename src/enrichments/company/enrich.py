"""
Company enrichment orchestrator.

Orchestrates the 4-stage company enrichment process:
1. Research - web search and scraping to find company information
2. Match - find the company in Orbis database using enriched data
3. Details - fetch detailed financial/employee data from Orbis
4. Features - extract categorized features from company data
"""

from common.logging import get_logger
from enrichments.company.features import extract_company_features
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
        CompanyEnrichmentResult containing research, match, details, and features
    """
    criteria = lead.company_research_criteria

    company_research = None
    company_match = None
    company_details = None
    features = None
    error = None

    try:
        # Stage 1: Research (best effort - failures don't stop the pipeline)
        try:
            company_research = await research_company(criteria)
        except Exception as e:
            logger.warning(f"[Enrichment] Research failed, continuing: {type(e).__name__}: {e!r}")

        # Stage 2: Company Match
        company_match = await match_company_in_orbis(criteria, company_research)

        # Stage 3: Company Details
        if company_match.company:
            company_details = await fetch_company_details_from_orbis(company_match.company.bvd_id)

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
