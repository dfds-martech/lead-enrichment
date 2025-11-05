"""
Main lead enrichment orchestrator.

Coordinates all enrichment pipelines and runs them in optimal order:
- Company enrichment (sequential internally: research → match → details)
- User validation (parallel)
- Custom enrichment (parallel)

Usage:
    from pipelines.lead_enrichment import enrich_lead

    lead = crm.get_lead(0)
    enriched = await enrich_lead(lead)
"""

import asyncio
import time
from datetime import datetime

from common.logging import get_logger
from models.enrichment import (
    CompanyEnrichmentResult,
    CustomEnrichmentResult,
    EnrichedLead,
    UserValidationResult,
)
from models.lead import Lead
from pipelines.company_enrichment import enrich_company
from pipelines.custom_enrichment import custom_enrichment
from pipelines.user_validation import validate_user

logger = get_logger(__name__)


async def enrich_lead(lead: Lead) -> EnrichedLead:
    """
    Main orchestrator - runs all enrichment pipelines for a lead.

    Execution flow:
    - company_enrichment, user_validation, and custom_enrichment run in parallel
    - Each pipeline handles its own errors and returns partial results if needed
    - Results are combined into a single EnrichedLead object

    Args:
        lead: The lead to enrich

    Returns:
        EnrichedLead with all enrichment results and metadata
    """
    start_time = time.time()
    logger.info(f"Starting lead enrichment for: {lead.company.get('name')}")

    try:
        # Run all pipelines in parallel
        company_result, user_result, custom_result = await asyncio.gather(
            enrich_company(lead), validate_user(lead), custom_enrichment(lead), return_exceptions=True
        )

        # Handle exceptions from gather (though pipelines should catch their own)
        if isinstance(company_result, Exception):
            logger.error(f"Company enrichment failed with exception: {company_result}")
            company_result = CompanyEnrichmentResult(research=None, match=None, details=None, error=str(company_result))

        if isinstance(user_result, Exception):
            logger.error(f"User validation failed with exception: {user_result}")
            user_result = UserValidationResult(
                name_properly_formatted=None, email_type=None, phone_valid=None, error=str(user_result)
            )

        if isinstance(custom_result, Exception):
            logger.error(f"Custom enrichment failed with exception: {custom_result}")
            custom_result = CustomEnrichmentResult(data=None, error=str(custom_result))

        duration = time.time() - start_time

        enriched = EnrichedLead(
            lead=lead,
            company=company_result,
            user_validation=user_result,
            custom=custom_result,
            metadata={
                "enriched_at": datetime.now().isoformat(),
                "duration_seconds": round(duration, 2),
                "company_matched": company_result.match.matched if company_result.match else False,
                "company_confidence": company_result.match.confidence if company_result.match else "none",
            },
        )

        logger.info(f"Lead enrichment completed in {duration:.2f}s")
        return enriched

    except Exception as e:
        logger.error(f"Fatal error in lead enrichment orchestrator: {e}", exc_info=True)
        # Return a minimal EnrichedLead with error information
        duration = time.time() - start_time
        return EnrichedLead(
            lead=lead,
            company=CompanyEnrichmentResult(error=f"Fatal error: {str(e)}"),
            user_validation=UserValidationResult(error="Skipped due to fatal error"),
            custom=CustomEnrichmentResult(error="Skipped due to fatal error"),
            metadata={
                "enriched_at": datetime.now().isoformat(),
                "duration_seconds": round(duration, 2),
                "fatal_error": str(e),
            },
        )
