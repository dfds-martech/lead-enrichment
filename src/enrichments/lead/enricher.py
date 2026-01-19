"""
Lead feature enrichment.

Extracts computed features from lead data:
- route_type: Geographic classification (europe_national, europe_cross_border, etc.)
"""

from common.logging import get_logger
from enrichments.lead.features import extract_lead_features
from enrichments.lead.schemas import LeadFeatures
from models.lead import Lead

logger = get_logger(__name__)


class LeadEnricher:
    """Lead feature extraction."""

    async def enrich(self, lead: Lead) -> LeadFeatures:
        """Extract features from lead data."""
        logger.debug(f"[Lead] Extracting features for lead: {lead.id}")

        features = extract_lead_features(lead)

        logger.info(f"[Lead] Features extracted - route_type: {features.route_type.value}")
        return features
