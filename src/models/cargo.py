"""Cargo enrichment models."""

from pydantic import BaseModel, Field


class CargoExtractionResult(BaseModel):
    """Output from the cargo extraction agent."""

    goods_type: str | None = Field(None, description="Type of goods being transported (e.g., fresh fish, electronics)")
    unit_type: str | None = Field(None, description="Type of unit (e.g., pallet, container, box)")
    unit_count: int | None = Field(None, description="Number of units")
    reasoning: str = Field("", description="Explanation of extraction")
