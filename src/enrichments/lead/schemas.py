from pydantic import BaseModel, Field

from enrichments.cargo.schemas import CargoEnrichmentResult
from enrichments.company.schemas import CompanyEnrichmentResult
from models.lead import Lead


class EnrichedLead(BaseModel):
    """Complete enrichment results for a lead from all pipelines."""

    lead: Lead = Field(description="Original lead data")
    company: CompanyEnrichmentResult = Field(description="Company enrichment results")
    cargo: CargoEnrichmentResult | None = Field(None, description="Cargo enrichment results")
    # TODO: user: UserEnrichmentResult = Field(description="User enrichment results")
    metadata: dict = Field(default_factory=dict, description="Metadata about enrichment (timestamps, duration, etc.)")
