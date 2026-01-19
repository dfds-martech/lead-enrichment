"""Geographic utilities for lead classification."""

import re

import pycountry

# EU member states + EEA countries (Norway, Iceland, Liechtenstein) + Switzerland + United Kingdom
EUROPEAN_ISO_CODES = {
    # EU member states
    "AT",  # Austria
    "BE",  # Belgium
    "BG",  # Bulgaria
    "HR",  # Croatia
    "CY",  # Cyprus
    "CZ",  # Czech Republic
    "DK",  # Denmark
    "EE",  # Estonia
    "FI",  # Finland
    "FR",  # France
    "DE",  # Germany
    "GR",  # Greece
    "HU",  # Hungary
    "IE",  # Ireland
    "IT",  # Italy
    "LV",  # Latvia
    "LT",  # Lithuania
    "LU",  # Luxembourg
    "MT",  # Malta
    "NL",  # Netherlands
    "PL",  # Poland
    "PT",  # Portugal
    "RO",  # Romania
    "SK",  # Slovakia
    "SI",  # Slovenia
    "ES",  # Spain
    "SE",  # Sweden
    # EEA countries
    "NO",  # Norway
    "IS",  # Iceland
    "LI",  # Liechtenstein
    # Switzerland (EFTA, treated as EU for customs)
    "CH",  # Switzerland
    # Special cases
    "GB",  # United Kingdom
}


def normalize_country_name(country_name: str | None) -> str | None:
    """Normalize country names by removing articles and parenthetical suffixes.

    Examples:
        "Netherlands (the)" -> "Netherlands"
        "United Kingdom of Great Britain and Northern Ireland (the)" -> "United Kingdom of Great Britain and Northern Ireland"
    """
    if not country_name:
        return None
    # Remove parenthetical suffixes like "(the)" or "(Kingdom of)"
    return re.sub(r"\s*\([^)]*\)\s*$", "", country_name).strip()


def is_european_country(country_name: str | None = None, country_code: str | None = None) -> bool | None:
    """Check if a country is in Europe (EU/EEA/CH).

    Args:
        country_name: Country name (e.g., "Germany", "Netherlands (the)")
        country_code: ISO 3166-1 alpha-2 code (e.g., "DE", "NL")

    Returns:
        True if European, False if not, None if unable to determine
    """
    # Try direct code lookup first
    if country_code:
        code_upper = country_code.upper()
        if code_upper in EUROPEAN_ISO_CODES:
            return True
        # If we have a valid code that's not in EU, it's non-EU
        if len(code_upper) == 2:
            return False

    # Fall back to name lookup using pycountry
    if country_name:
        normalized = normalize_country_name(country_name)
        if normalized:
            try:
                country = pycountry.countries.search_fuzzy(normalized)[0]
                return country.alpha_2 in EUROPEAN_ISO_CODES
            except LookupError:
                pass

    return None
