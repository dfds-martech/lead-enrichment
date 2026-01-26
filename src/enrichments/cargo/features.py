"""Cargo feature extraction.

Extracts categorized features from cargo enrichment data (extraction agent output)
organized by domain. Designed to be extensible for additional agent outputs.
"""

from enrichments.cargo.agents.cargo_extraction import CargoExtractionResult
from enrichments.cargo.schemas import (
    CargoCommodity,
    CargoEquipment,
    CargoFeatures,
    CargoHandling,
    CargoIntent,
    CargoMetadata,
    CargoPackaging,
    CargoTiming,
)

# ============================================================================
# Main Extraction Function
# ============================================================================


def extract_cargo_features(
    extraction: CargoExtractionResult | None,
    # Future agent outputs can be added as parameters:
    # risk: CargoRiskResult | None = None,
) -> CargoFeatures:
    """Extract categorized features from cargo enrichment data.

    Orchestrates domain-specific extractors. When additional agents are added,
    their outputs can be passed as parameters and merged in the extractors.

    Args:
        extraction: Cargo extraction agent results

    Returns:
        CargoFeatures with all domains populated
    """
    return CargoFeatures(
        commodity=_extract_commodity(extraction),
        packaging=_extract_packaging(extraction),
        equipment=_extract_equipment(extraction),
        handling=_extract_handling(extraction),
        timing=_extract_timing(extraction),
        intent=_extract_intent(extraction),
        metadata=_extract_metadata(extraction),
    )


# ============================================================================
# Domain-Specific Extractors
# ============================================================================


def _extract_commodity(extraction: CargoExtractionResult | None) -> CargoCommodity:
    """Extract commodity information."""
    if not extraction:
        return CargoCommodity()

    return CargoCommodity(
        type=extraction.commodity_type,
        category=extraction.commodity_category,
    )


def _extract_packaging(extraction: CargoExtractionResult | None) -> CargoPackaging:
    """Extract packaging and unit information."""
    if not extraction:
        return CargoPackaging()

    return CargoPackaging(
        type=extraction.packaging_type,
        unit_type=extraction.unit_type,
        unit_count=extraction.unit_count,
    )


def _extract_equipment(extraction: CargoExtractionResult | None) -> CargoEquipment:
    """Extract equipment information."""
    if not extraction:
        return CargoEquipment()

    return CargoEquipment(
        type=extraction.equipment_type,
        group=extraction.equipment_group,
    )


def _extract_handling(extraction: CargoExtractionResult | None) -> CargoHandling:
    """Extract special handling requirements."""
    if not extraction:
        return CargoHandling()

    return CargoHandling(
        temperature_controlled=extraction.temperature_controlled,
        hazardous=extraction.hazardous,
        oversized_project=extraction.oversized_project,
        high_value=extraction.high_value,
    )


def _extract_timing(extraction: CargoExtractionResult | None) -> CargoTiming:
    """Extract timing information."""
    if not extraction:
        return CargoTiming()

    return CargoTiming(
        urgency=extraction.urgency,
        frequency=extraction.frequency,
    )


def _extract_intent(extraction: CargoExtractionResult | None) -> CargoIntent:
    """Extract partnership intent."""
    if not extraction:
        return CargoIntent()

    return CargoIntent(
        partnership_needs=extraction.partnership_needs,
    )


def _extract_metadata(extraction: CargoExtractionResult | None) -> CargoMetadata:
    """Extract extraction metadata."""
    if not extraction:
        return CargoMetadata()

    return CargoMetadata(
        confidence=extraction.confidence,
        reasoning=extraction.reasoning,
    )
