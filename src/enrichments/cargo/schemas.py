"""Cargo enrichment schemas.

Defines the structured output models for cargo enrichment,
organized by domain for clarity and maintainability.
"""

from pydantic import BaseModel, Field

from .agents.cargo_extraction import (
    CargoExtractionResult,
    CommodityCategory,
    EquipmentGroup,
    Frequency,
    PartnershipNeeds,
    UnitType,
    Urgency,
)

# ============================================================================
# Domain-Specific Feature Models
# ============================================================================


class CargoCommodity(BaseModel):
    """Commodity information."""

    type: str | None = Field(None, description="Specific commodity (e.g., 'fresh salmon fillets')")
    category: CommodityCategory | None = Field(None, description="Categorized commodity type")


class CargoPackaging(BaseModel):
    """Packaging and unit information."""

    type: str | None = Field(None, description="Packaging type (e.g., 'pallets', 'crates', 'drums')")
    unit_type: UnitType | None = Field(None, description="Type of unit")
    unit_count: int | None = Field(None, description="Number of units")


class CargoEquipment(BaseModel):
    """Equipment information."""

    type: str | None = Field(None, description="Specific equipment (e.g., 'Reefer trailer', '40ft container')")
    group: EquipmentGroup | None = Field(None, description="Broader equipment category")


class CargoHandling(BaseModel):
    """Special handling requirements."""

    temperature_controlled: bool = Field(False, description="Requires reefer/chilled/frozen")
    hazardous: bool | str | None = Field(None, description="True or IMDG class if hazardous")
    oversized_project: bool = Field(False, description="Out-of-gauge, heavy lift, project cargo")
    high_value: bool = Field(False, description="High-value cargo (electronics, pharma, luxury)")


class CargoTiming(BaseModel):
    """Timing information."""

    urgency: Urgency | None = Field(None, description="How soon transport is needed")
    frequency: Frequency | None = Field(None, description="How often transports will occur")


class CargoIntent(BaseModel):
    """Partnership intent information."""

    partnership_needs: PartnershipNeeds | None = Field(None, description="Partnership intent")


class CargoMetadata(BaseModel):
    """Extraction metadata."""

    confidence: float = Field(0.0, description="0-1 extraction confidence")
    reasoning: str = Field("", description="Extraction reasoning")


# ============================================================================
# Aggregated Feature Model
# ============================================================================


class CargoFeatures(BaseModel):
    """Complete extracted features for cargo, organized by domain."""

    commodity: CargoCommodity = Field(default_factory=CargoCommodity)
    packaging: CargoPackaging = Field(default_factory=CargoPackaging)
    equipment: CargoEquipment = Field(default_factory=CargoEquipment)
    handling: CargoHandling = Field(default_factory=CargoHandling)
    timing: CargoTiming = Field(default_factory=CargoTiming)
    intent: CargoIntent = Field(default_factory=CargoIntent)
    metadata: CargoMetadata = Field(default_factory=CargoMetadata)


# ============================================================================
# Enrichment Result Model
# ============================================================================


class CargoEnrichmentResult(BaseModel):
    """Results from cargo enrichment pipeline (extraction → features)."""

    extraction: CargoExtractionResult | None = Field(None, description="Results from cargo extraction agent")
    # Future agent outputs can be added here:
    # risk: CargoRiskResult | None = Field(None, description="Results from risk assessment agent")
    features: CargoFeatures | None = Field(None, description="Extracted and categorized features")
    error: str | None = Field(None, description="Error message if enrichment failed")
