from enum import Enum

from pydantic import BaseModel, Field

from enrichments.cargo.schemas import CargoEnrichmentResult
from enrichments.company.schemas import CompanyEnrichmentResult
from models.lead import Lead


class RouteType(str, Enum):
    """Geographic classification of transport routes."""

    EUROPE_NATIONAL = "europe_national"  # Same country within Europe
    EUROPE_CROSS_BORDER = "europe_cross_border"  # Different EU/EEA countries
    EUROPE_IMPORT = "europe_import"  # From outside EU into EU
    EUROPE_EXPORT = "europe_export"  # From EU to outside EU
    WORLD = "world"  # Non-EU to non-EU
    OTHER = "other"  # Missing data or unable to determine


class LeadFeatures(BaseModel):
    """Computed features from lead data."""

    route_type: RouteType = Field(description="Geographic classification of the route")


class EnrichedLead(BaseModel):
    """Complete enrichment results for a lead from all pipelines."""

    lead: Lead = Field(description="Original lead data")
    company: CompanyEnrichmentResult = Field(description="Company enrichment results")
    cargo: CargoEnrichmentResult | None = Field(None, description="Cargo enrichment results")
    # TODO: user: UserEnrichmentResult = Field(description="User enrichment results")
    metadata: dict = Field(default_factory=dict, description="Metadata about enrichment (timestamps, duration, etc.)")
