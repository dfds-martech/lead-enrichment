"""Lead feature extraction."""

from enrichments.lead.geography import is_european_country
from enrichments.lead.schemas import LeadFeatures, RouteType
from models.lead import Lead


def extract_route_type(lead: Lead) -> RouteType:
    """Compute route type from collection/delivery countries.

    Classifications:
        - europe_national: Same country within Europe
        - europe_cross_border: Different EU/EEA countries
        - europe_export: From EU/EEA to outside EU
        - europe_import: From outside EU into EU/EEA
        - world: Non-EU to non-EU
        - other: Missing country data or unable to determine
    """
    # Collection
    collection_country = lead.collection.get("country")
    collection_code = lead.collection.get("country_code")

    # Delivery
    delivery_country = lead.delivery.get("country")
    delivery_code = lead.delivery.get("country_code")

    # Missing data check
    if not (collection_country or collection_code) or not (delivery_country or delivery_code):
        return RouteType.OTHER

    # Determine EU membership
    collection_is_european = is_european_country(collection_country, collection_code)
    delivery_is_european = is_european_country(delivery_country, delivery_code)

    if collection_is_european is None or delivery_is_european is None:
        return RouteType.OTHER

    # Check if same country (national)
    is_same_country = (collection_code and delivery_code and collection_code.upper() == delivery_code.upper()) or (
        collection_country and delivery_country and collection_country.lower() == delivery_country.lower()
    )

    if is_same_country:
        return RouteType.EUROPE_NATIONAL if collection_is_european else RouteType.WORLD

    # Cross-border routes
    if collection_is_european and delivery_is_european:
        return RouteType.EUROPE_CROSS_BORDER
    elif collection_is_european and not delivery_is_european:
        return RouteType.EUROPE_EXPORT
    elif not collection_is_european and delivery_is_european:
        return RouteType.EUROPE_IMPORT

    return RouteType.WORLD


def extract_lead_features(lead: Lead) -> LeadFeatures:
    """Extract all computed features from a lead."""
    return LeadFeatures(route_type=extract_route_type(lead))
