"""Tests for lead geographic features."""

from enrichments.lead.features import (
    RouteType,
    extract_is_cross_channel_transport,
    extract_is_europe_company_location,
    extract_lead_features,
    extract_route_type,
)
from enrichments.lead.geography import (
    EUROPEAN_ISO_CODES,
    is_cross_channel_country,
    is_european_country,
    normalize_country_name,
)
from enrichments.lead.schemas import LeadFeatures
from models.lead import Lead, LeadQuote


def make_lead(
    collection_country: str | None = None,
    collection_code: str | None = None,
    delivery_country: str | None = None,
    delivery_code: str | None = None,
    company_country: str | None = None,
    company_code: str | None = None,
) -> Lead:
    """Create a minimal Lead for testing."""
    return Lead(
        id="test",
        identifiers={},
        contact={},
        company={"country": company_country, "country_code": company_code},
        collection={"country": collection_country, "country_code": collection_code},
        delivery={"country": delivery_country, "country_code": delivery_code},
        quote=LeadQuote(),
        record={},
        payload={},
    )


# --- Geography tests ---


def test_normalize_country_name_removes_articles():
    assert normalize_country_name("Netherlands (the)") == "Netherlands"
    assert normalize_country_name("United Kingdom (the)") == "United Kingdom"


def test_normalize_country_name_preserves_normal_names():
    assert normalize_country_name("Germany") == "Germany"
    assert normalize_country_name("France") == "France"


def test_normalize_country_name_handles_none():
    assert normalize_country_name(None) is None


def test_is_european_country_with_eu_code():
    assert is_european_country(country_code="DE") is True
    assert is_european_country(country_code="FR") is True
    assert is_european_country(country_code="NL") is True


def test_is_european_country_with_non_eu_code():
    assert is_european_country(country_code="US") is False
    assert is_european_country(country_code="CN") is False


def test_is_european_country_with_name():
    assert is_european_country(country_name="Germany") is True
    assert is_european_country(country_name="France") is True
    assert is_european_country(country_name="China") is False


def test_is_european_country_with_article_name():
    assert is_european_country(country_name="Netherlands (the)") is True


def test_european_iso_codes_contains_expected():
    assert "DE" in EUROPEAN_ISO_CODES  # Germany
    assert "FR" in EUROPEAN_ISO_CODES  # France
    assert "NO" in EUROPEAN_ISO_CODES  # Norway (EEA)
    assert "CH" in EUROPEAN_ISO_CODES  # Switzerland


# --- Route type tests ---


def test_route_type_europe_national():
    lead = make_lead(collection_code="DE", delivery_code="DE")
    assert extract_route_type(lead) == RouteType.EUROPE_NATIONAL


def test_route_type_europe_national_by_name():
    lead = make_lead(collection_country="Germany", delivery_country="Germany")
    assert extract_route_type(lead) == RouteType.EUROPE_NATIONAL


def test_route_type_europe_cross_border():
    lead = make_lead(collection_code="DE", delivery_code="FR")
    assert extract_route_type(lead) == RouteType.EUROPE_CROSS_BORDER


def test_route_type_europe_export():
    lead = make_lead(collection_code="DE", delivery_code="US")
    assert extract_route_type(lead) == RouteType.EUROPE_EXPORT


def test_route_type_europe_import():
    lead = make_lead(collection_code="CN", delivery_code="DE")
    assert extract_route_type(lead) == RouteType.EUROPE_IMPORT


def test_route_type_world_same_country():
    lead = make_lead(collection_code="US", delivery_code="US")
    assert extract_route_type(lead) == RouteType.WORLD


def test_route_type_world_cross_border():
    lead = make_lead(collection_code="US", delivery_code="CN")
    assert extract_route_type(lead) == RouteType.WORLD


def test_route_type_other_missing_data():
    lead = make_lead()
    assert extract_route_type(lead) == RouteType.OTHER


def test_route_type_other_partial_data():
    lead = make_lead(collection_code="DE")
    assert extract_route_type(lead) == RouteType.OTHER


# --- Cross-channel country tests ---


def test_is_cross_channel_country_with_uk():
    assert is_cross_channel_country(country_code="GB") is True
    assert is_cross_channel_country(country_name="United Kingdom") is True


def test_is_cross_channel_country_with_ireland():
    assert is_cross_channel_country(country_code="IE") is True
    assert is_cross_channel_country(country_name="Ireland") is True


def test_is_cross_channel_country_with_continental():
    assert is_cross_channel_country(country_code="DE") is False
    assert is_cross_channel_country(country_code="FR") is False


# --- Cross-channel transport tests ---


def test_cross_channel_transport_uk_to_germany():
    lead = make_lead(collection_code="GB", delivery_code="DE")
    assert extract_is_cross_channel_transport(lead) is True


def test_cross_channel_transport_france_to_ireland():
    lead = make_lead(collection_code="FR", delivery_code="IE")
    assert extract_is_cross_channel_transport(lead) is True


def test_cross_channel_transport_germany_to_france():
    lead = make_lead(collection_code="DE", delivery_code="FR")
    assert extract_is_cross_channel_transport(lead) is False


def test_cross_channel_transport_uk_to_ireland():
    # Both are channel countries - not a cross-channel transport
    lead = make_lead(collection_code="GB", delivery_code="IE")
    assert extract_is_cross_channel_transport(lead) is False


def test_cross_channel_transport_missing_data():
    lead = make_lead(collection_code="GB")
    assert extract_is_cross_channel_transport(lead) is None


# --- Europe company location tests ---


def test_europe_company_location_germany():
    lead = make_lead(company_code="DE")
    assert extract_is_europe_company_location(lead) is True


def test_europe_company_location_us():
    lead = make_lead(company_code="US")
    assert extract_is_europe_company_location(lead) is False


def test_europe_company_location_by_name():
    lead = make_lead(company_country="France")
    assert extract_is_europe_company_location(lead) is True


def test_europe_company_location_missing():
    lead = make_lead()
    assert extract_is_europe_company_location(lead) is None


# --- Feature extraction tests ---


def test_extract_lead_features_returns_model():
    lead = make_lead(collection_code="DE", delivery_code="FR", company_code="DE")
    features = extract_lead_features(lead)
    assert isinstance(features, LeadFeatures)
    assert features.route_type == RouteType.EUROPE_CROSS_BORDER
    assert features.is_cross_channel_transport is False
    assert features.is_europe_company_location is True


def test_extract_lead_features_cross_channel():
    lead = make_lead(collection_code="GB", delivery_code="DE", company_code="GB")
    features = extract_lead_features(lead)
    assert features.route_type == RouteType.EUROPE_CROSS_BORDER
    assert features.is_cross_channel_transport is True
    assert features.is_europe_company_location is True
