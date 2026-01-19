"""
Lead feature enrichment.

Extracts computed features from lead data:
- route_type: Geographic classification (europe_national, europe_cross_border, etc.)
- is_cross_channel_transport: UK/Ireland ↔ continental Europe
- is_europe_company_location: Company located in Europe
"""

from common.logging import get_logger
from enrichments.lead.features import extract_lead_features
from enrichments.lead.schemas import LeadEnrichmentResult
from models.lead import Lead

logger = get_logger(__name__)


class LeadEnricher:
    """Lead feature extraction."""

    async def enrich(self, lead: Lead) -> LeadEnrichmentResult:
        """Extract features from lead data."""
        logger.debug(f"[Lead] Extracting features for lead: {lead.id}")

        features = None
        error = None

        try:
            features = extract_lead_features(lead)
            logger.info(f"[Lead] Features extracted - route_type: {features.route_type.value}")
        except Exception as e:
            logger.error(f"[Lead] Failed: {type(e).__name__}: {e}", exc_info=True)
            error = f"{type(e).__name__}: {e}"

        return LeadEnrichmentResult(features=features, error=error)
