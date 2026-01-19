from pydantic import BaseModel, Field

from .agents.cargo_extraction import CargoExtractionResult


class CargoEnrichmentResult(BaseModel):
    """Results from cargo enrichment pipeline."""

    extraction: CargoExtractionResult | None = Field(None, description="Results from cargo extraction agent")
    error: str | None = Field(None, description="Error message if enrichment failed")
