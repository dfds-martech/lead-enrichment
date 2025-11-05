"""Company enrichment endpoints."""

from fastapi import APIRouter, HTTPException

from common.logging import get_logger
from models.company import CompanyResearchCriteria
from models.enrichment import CompanyEnrichmentResult
from pipelines.company_enrichment import enrich_company

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
    try:
        logger.debug(f"Enrichment criteria\n: {criteria.model_dump_json(indent=2, exclude_none=True)}")

        enrichment_result = await enrich_company(criteria)

        logger.info(f"Enrichment completed\n: {enrichment_result.model_dump_json(indent=2, exclude_none=True)}")

        return enrichment_result

    except Exception as e:
        logger.error(f"Enrichment request failed for {criteria.name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Enrichment failed: {str(e)}") from e
