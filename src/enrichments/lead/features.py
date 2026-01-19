"""Lead feature extraction."""

from enrichments.lead.geography import is_cross_channel_country, is_european_country
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


def extract_is_cross_channel_transport(lead: Lead) -> bool | None:
    """Check if transport requires channel crossing (UK/Ireland ↔ continental Europe).

    Returns True if one endpoint is in UK/Ireland and the other is in continental Europe.
    """
    collection_country = lead.collection.get("country")
    collection_code = lead.collection.get("country_code")
    delivery_country = lead.delivery.get("country")
    delivery_code = lead.delivery.get("country_code")

    # Need both endpoints to determine
    if not (collection_country or collection_code) or not (delivery_country or delivery_code):
        return None

    collection_is_channel = is_cross_channel_country(collection_country, collection_code)
    delivery_is_channel = is_cross_channel_country(delivery_country, delivery_code)
    collection_is_european = is_european_country(collection_country, collection_code)
    delivery_is_european = is_european_country(delivery_country, delivery_code)

    if collection_is_channel is None or delivery_is_channel is None:
        return None
    if collection_is_european is None or delivery_is_european is None:
        return None

    # Cross-channel: one side is UK/Ireland, other side is continental Europe (not UK/Ireland)
    return (collection_is_channel and delivery_is_european and not delivery_is_channel) or (
        delivery_is_channel and collection_is_european and not collection_is_channel
    )


def extract_is_europe_company_location(lead: Lead) -> bool | None:
    """Check if the company is located in Europe."""
    company_country = lead.company.get("country")
    company_code = lead.company.get("country_alpha2") or lead.company.get("country_code")

    if not company_country and not company_code:
        return None

    return is_european_country(company_country, company_code)


def extract_lead_features(lead: Lead) -> LeadFeatures:
    """Extract all computed features from a lead."""
    return LeadFeatures(
        route_type=extract_route_type(lead),
        is_cross_channel_transport=extract_is_cross_channel_transport(lead),
        is_europe_company_location=extract_is_europe_company_location(lead),
    )
