"""Company feature extraction.

Extracts categorized features from company enrichment data (research, match, details)
organized by domain with explicit priority rules.

Priority order for data resolution: details > match > research
"""

from enrichments.base_features import (
    get_email_domain_type,
    get_employees_bracket,
    get_profit_before_tax_bracket,
    get_revenue_bracket,
    get_total_assets_bracket,
)
from enrichments.company.agents.company_match import CompanyMatchResult
from enrichments.company.agents.company_research import CompanyResearchResult
from enrichments.company.schemas import (
    CompanyAddress,
    CompanyEmployees,
    CompanyFeatures,
    CompanyFinancials,
    CompanyIdentifiers,
    CompanyIndustry,
    CompanyInfo,
    CompanyMatchMetadata,
    CompanyStatus,
)
from enrichments.company.utils import get_industry_category
from services.orbis.schemas import OrbisCompanyDetails

# ============================================================================
# Main Extraction Function
# ============================================================================


def extract_company_features(
    research: CompanyResearchResult | None,
    match: CompanyMatchResult | None,
    details: OrbisCompanyDetails | None,
) -> CompanyFeatures:
    """Extract categorized features from company enrichment data.

    Orchestrates domain-specific extractors, each handling their own
    data resolution with priority: details > match > research.

    Args:
        research: Web research results (company info scraped from web)
        match: Orbis matching results (company match from database)
        details: Orbis company details (full company record)

    Returns:
        CompanyFeatures with all domains populated
    """
    return CompanyFeatures(
        identifiers=_extract_identifiers(research, match, details),
        info=_extract_info(research, match, details),
        status=_extract_status(details),
        industry=_extract_industry(research, match, details),
        match=_extract_match_metadata(match),
        employees=_extract_employees(details),
        financials=_extract_financials(details),
    )


# ============================================================================
# Domain-Specific Extractors
# ============================================================================


def _extract_identifiers(
    research: CompanyResearchResult | None,
    match: CompanyMatchResult | None,
    details: OrbisCompanyDetails | None,
) -> CompanyIdentifiers:
    """Extract company identifiers with priority: details > match > research."""

    # Orbis/BvD IDs: only from Orbis sources
    orbis_id = details.orbis_id if details else None
    bvd_id = details.bvd_id if details else (match.company.bvd_id if match and match.company else None)

    # National ID: details > match > research
    national_id = None
    vat_number = None

    if details and details.national_id:
        for item in details.national_id:
            label = item.get("label", "")
            value = item.get("value")
            if label == "VAT number":
                vat_number = value
            elif value and not national_id:  ## TODO: inspect how many national_ids we can have
                national_id = value

    if not national_id and match and match.company:
        national_id = match.company.national_id

    if not national_id and research:
        national_id = research.national_id

    return CompanyIdentifiers(
        orbis_id=orbis_id,
        bvd_id=bvd_id,
        national_id=national_id,
        vat_number=vat_number,
    )


def _extract_info(
    research: CompanyResearchResult | None,
    match: CompanyMatchResult | None,
    details: OrbisCompanyDetails | None,
) -> CompanyInfo:
    """Extract basic company info with priority: details > match > research."""

    # Name: details > match > research
    name = (
        details.name
        if details
        else (match.company.name if match and match.company else (research.name if research else None))
    )

    # Address: primarily from details
    address = _extract_address(research, match, details)

    # Website/Domain: details > match > research
    website = None
    domain = None

    if details and details.address and details.address.websites:
        website = details.address.websites[0]
        domain = _normalize_domain(website)
    elif match and match.company and match.company.email_or_website:
        website = match.company.email_or_website
        domain = _normalize_domain(website)
    elif research and research.domain:
        domain = research.domain
        website = f"https://{domain}" if not domain.startswith("http") else domain

    # Description: only from research (Orbis doesn't have this)
    description = research.description if research else None

    # Email domain type
    email_domain_type = get_email_domain_type(domain)

    return CompanyInfo(
        name=name,
        address=address,
        website=website,
        domain=domain,
        email_domain_type=email_domain_type,
        description=description,
    )


def _extract_address(
    research: CompanyResearchResult | None,
    match: CompanyMatchResult | None,
    details: OrbisCompanyDetails | None,
) -> CompanyAddress:
    """Extract address with priority: details > match > research."""

    if details and details.address:
        addr = details.address
        return CompanyAddress(
            street=addr.street1,
            city=addr.city,
            postal_code=addr.postal_code,
            state=addr.state,
            country=None,
            country_code=addr.country_code,
            phone=addr.phone,
        )

    if match and match.company:
        company = match.company
        return CompanyAddress(
            street=company.address,
            city=company.city,
            postal_code=company.postcode,
            state=company.state,
            country=None,
            country_code=company.country,
            phone=company.phone_or_fax,
        )

    if research:
        return CompanyAddress(
            street=research.address,
            city=research.city,
            postal_code=research.postal_code,
            state=None,
            country=research.country,
            country_code=research.country_code,
            phone=None,
        )

    return CompanyAddress()


def _extract_status(details: OrbisCompanyDetails | None) -> CompanyStatus:
    """Extract company legal and operational status from Orbis details."""

    if not details:
        return CompanyStatus()

    legal_status = details.legal_status
    consolidation_code = details.consolidation_code

    # Determine if company is active based on legal_status
    # Orbis codes: 1 = Active, 2 = Active (default of reorganization), 3+ = Inactive/other
    is_active = legal_status in ("1", "2") if legal_status else True

    return CompanyStatus(
        legal_status=legal_status,
        consolidation_code=consolidation_code,
        is_active=is_active,
    )


def _extract_industry(
    research: CompanyResearchResult | None,
    match: CompanyMatchResult | None,
    details: OrbisCompanyDetails | None,
) -> CompanyIndustry:
    """Extract industry classification."""

    # NACE code: only from Orbis
    nace_code = details.nace_code if details else None

    # Industry description: prefer research (more detailed), fallback to match
    description = research.industry if research else (match.industry if match else None)

    # Category: mapped from NACE, or fall back to research description
    category = get_industry_category(nace_code)
    if category == "unknown" and description:
        # Use first part of description as fallback category
        category = description.split(";")[0].strip() if ";" in description else description

    return CompanyIndustry(
        description=description,
        nace_code=nace_code,
        category=category,
    )


def _extract_match_metadata(match: CompanyMatchResult | None) -> CompanyMatchMetadata:
    """Extract match metadata from Orbis matching."""

    if not match:
        return CompanyMatchMetadata()

    score = match.company.score if match.company else None

    return CompanyMatchMetadata(
        confidence=match.confidence,
        score=score,
        candidates_considered=match.total_candidates,
        notes=match.reasoning,
    )


def _extract_employees(details: OrbisCompanyDetails | None) -> CompanyEmployees:
    """Extract employee information from Orbis details."""

    if not details:
        return CompanyEmployees()

    count = details.employees

    return CompanyEmployees(
        count=count,
        bracket=get_employees_bracket(count),
    )


def _extract_financials(details: OrbisCompanyDetails | None) -> CompanyFinancials:
    """Extract financial metrics from Orbis details."""

    if not details or not details.financials:
        return CompanyFinancials()

    fin = details.financials

    # Determine if any financial data exists
    has_data = (
        fin.has_data()
        if hasattr(fin, "has_data")
        else any(
            [
                fin.operating_revenue,
                fin.profit_before_tax,
                fin.profit_loss,
                fin.cash_flow,
                fin.total_assets,
                fin.shareholders_funds,
            ]
        )
    )

    # Financial health assessment
    financial_health = _assess_financial_health(fin)

    # Accounting year
    accounting_year = fin.accounting_year.strftime("%Y-%m-%d") if fin.accounting_year else "unknown"

    return CompanyFinancials(
        # Raw values
        revenue=fin.operating_revenue,
        profit_before_tax=fin.profit_before_tax,
        profit_loss=fin.profit_loss,
        cash_flow=fin.cash_flow,
        total_assets=fin.total_assets,
        shareholders_funds=fin.shareholders_funds,
        # Brackets
        revenue_bracket=get_revenue_bracket(fin.operating_revenue),
        profit_bracket=get_profit_before_tax_bracket(fin.profit_before_tax),
        assets_bracket=get_total_assets_bracket(fin.total_assets),
        # Derived
        accounting_year=accounting_year,
        financial_health=financial_health,
        has_data=has_data,
    )


# ============================================================================
# Helper Functions
# ============================================================================


def _assess_financial_health(financials) -> str:
    """Assess financial health based on financial indicators.

    Returns:
        'healthy', 'moderate', 'at_risk', or 'unknown'
    """
    if not financials:
        return "unknown"

    has_data = (
        financials.has_data()
        if hasattr(financials, "has_data")
        else any(
            [
                financials.profit_before_tax,
                financials.profit_loss,
                financials.cash_flow,
            ]
        )
    )

    if not has_data:
        return "unknown"

    profit_positive = (financials.profit_before_tax is not None and financials.profit_before_tax > 0) or (
        financials.profit_loss is not None and financials.profit_loss > 0
    )

    cash_flow_positive = financials.cash_flow is not None and financials.cash_flow > 0

    if profit_positive and cash_flow_positive:
        return "healthy"
    if not profit_positive and not cash_flow_positive:
        return "at_risk"

    return "moderate"


def _normalize_domain(url: str | None) -> str | None:
    """Extract domain from URL or website string."""
    if not url:
        return None

    domain = url.lower().strip()

    # Remove protocol
    for prefix in ["https://", "http://", "www."]:
        if domain.startswith(prefix):
            domain = domain[len(prefix) :]

    # Remove path
    if "/" in domain:
        domain = domain.split("/")[0]

    return domain or None
