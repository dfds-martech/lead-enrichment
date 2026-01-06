"""Company enrichment endpoints."""

from fastapi import APIRouter, HTTPException

from common.logging import get_logger
from enrichments.company_enrichment import enrich_company
from models.company import CompanyResearchCriteria
from models.enrichment import CompanyEnrichmentResult

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["enrichment"])


@router.post("/enrich-company", response_model=CompanyEnrichmentResult)
async def enrich_company_endpoint(criteria: CompanyResearchCriteria):
    """
    Enrich a company using based on selected research criteria.

    This endpoint:
    1. Accepts basic company information (name, domain, city, country, phone)
    2. Runs web research to find additional company information
    3. Matches the company in the Orbis database
    4. Fetches detailed company data if matched

    Args:
        query: Company information (name required, others optional)

    Returns:
        CompanyEnrichmentResult with research, match, and details

    Example request:
        ```json
        {
            "name": "WILDWINE LTD",
            "domain": "wildwine.je",
            "city": "London",
            "country": "United Kingdom",
            "phone": "+447797893894"
        }
        ```
    """
    company_name = criteria.name
    logger.info(f"Starting enrichment for: {company_name}")

    try:
        result = await enrich_company(criteria)

        if result.error:
            logger.warning(f"Enrichment completed with errors: {result.error}")

        logger.info(
            f"Enrichment completed for {company_name}",
            extra={
                "has_research": result.research is not None,
                "has_match": result.match is not None,
                "has_details": result.details is not None,
            },
        )

        return result

    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"
        logger.error(f"Enrichment failed for {company_name}: {error_msg}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Enrichment failed: {error_msg}") from e
