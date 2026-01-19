"""Company feature extraction.

Extracts categorized features from the entire CompanyEnrichmentResult for analysis and decision-making.
"""

from enrichments.base_features import (
    get_cash_flow_bracket,
    get_email_domain_type,
    get_employees_bracket,
    get_match_rating,
    get_profit_before_tax_bracket,
    get_profit_loss_bracket,
    get_revenue_bracket,
    get_shareholders_funds_bracket,
    get_total_assets_bracket,
)
from enrichments.company.agents.company_match import CompanyMatchResult
from enrichments.company.agents.company_research import CompanyResearchResult
from enrichments.company.schemas import CompanyFeatures
from services.orbis.schemas import OrbisCompanyDetails

# NACE code to industry category mapping (simplified - can be expanded)
NACE_INDUSTRY_MAPPING: dict[str, str] = {
    # Agriculture, forestry and fishing
    "01": "Agriculture",
    "02": "Forestry",
    "03": "Fishing",
    # Mining and quarrying
    "05": "Mining",
    "06": "Oil & Gas",
    "07": "Mining",
    "08": "Mining",
    "09": "Mining",
    # Manufacturing
    "10": "Food & Beverages",
    "11": "Beverages",
    "12": "Tobacco",
    "13": "Textiles",
    "14": "Apparel",
    "15": "Leather",
    "16": "Wood",
    "17": "Paper",
    "18": "Printing",
    "19": "Petroleum",
    "20": "Chemicals",
    "21": "Pharmaceuticals",
    "22": "Rubber & Plastics",
    "23": "Non-metallic Minerals",
    "24": "Metals",
    "25": "Metal Products",
    "26": "Electronics",
    "27": "Electrical Equipment",
    "28": "Machinery",
    "29": "Motor Vehicles",
    "30": "Transport Equipment",
    "31": "Furniture",
    "32": "Other Manufacturing",
    "33": "Repair & Installation",
    # Utilities
    "35": "Energy",
    "36": "Water",
    "37": "Sewerage",
    "38": "Waste Management",
    "39": "Remediation",
    # Construction
    "41": "Construction",
    "42": "Civil Engineering",
    "43": "Specialized Construction",
    # Wholesale and retail trade
    "45": "Motor Vehicle Trade",
    "46": "Wholesale Trade",
    "47": "Retail Trade",
    # Transportation and storage
    "49": "Land Transport",
    "50": "Water Transport",
    "51": "Air Transport",
    "52": "Warehousing",
    "53": "Postal & Courier",
    # Accommodation and food service
    "55": "Accommodation",
    "56": "Food Service",
    # Information and communication
    "58": "Publishing",
    "59": "Motion Pictures",
    "60": "Broadcasting",
    "61": "Telecommunications",
    "62": "IT Services",
    "63": "Information Services",
    # Financial and insurance
    "64": "Financial Services",
    "65": "Insurance",
    "66": "Auxiliary Financial",
    # Real estate
    "68": "Real Estate",
    # Professional, scientific and technical
    "69": "Legal & Accounting",
    "70": "Management Consulting",
    "71": "Architecture & Engineering",
    "72": "R&D",
    "73": "Advertising",
    "74": "Other Professional",
    "75": "Veterinary",
    # Administrative and support
    "77": "Rental & Leasing",
    "78": "Employment",
    "79": "Travel Agencies",
    "80": "Security",
    "81": "Services to Buildings",
    "82": "Office Administration",
    # Public administration
    "84": "Public Administration",
    # Education
    "85": "Education",
    # Human health and social work
    "86": "Human Health",
    "87": "Residential Care",
    "88": "Social Work",
    # Arts, entertainment and recreation
    "90": "Creative Arts",
    "91": "Libraries & Archives",
    "92": "Gambling",
    "93": "Sports & Recreation",
    # Other service activities
    "94": "Membership Organizations",
    "95": "Repair Services",
    "96": "Personal Services",
    # Activities of households
    "97": "Household Activities",
    "98": "Household Activities",
    # Extraterritorial organizations
    "99": "Extraterritorial",
}


def get_industry_category(nace_code: str | None) -> str:
    """Map NACE code to industry category."""
    if not nace_code:
        return "unknown"

    # Use first 2 digits for broad category
    category_code = nace_code[:2] if len(nace_code) >= 2 else nace_code
    return NACE_INDUSTRY_MAPPING.get(category_code, "unknown")


def get_financial_health(financials: any) -> str:
    """
    Assess financial health based on financial indicators.

    Returns:
        Financial health indicator: 'healthy', 'moderate', 'at_risk', or 'unknown'
    """
    if not financials or not financials.has_data():
        return "unknown"

    profit_positive = (financials.profit_before_tax is not None and financials.profit_before_tax > 0) or (
        financials.profit_loss is not None and financials.profit_loss > 0
    )

    cash_flow_positive = financials.cash_flow is not None and financials.cash_flow > 0

    # Healthy: positive profit and positive cash flow
    if profit_positive and cash_flow_positive:
        return "healthy"

    # At risk: negative profit and negative cash flow
    if not profit_positive and not cash_flow_positive:
        return "at_risk"

    # Moderate: mixed indicators
    return "moderate"


def extract_company_features(
    research: CompanyResearchResult | None,
    match: CompanyMatchResult | None,
    details: OrbisCompanyDetails | None,
) -> CompanyFeatures:
    """Extract categorized features from the entire CompanyEnrichmentResult."""

    # ===== Identifiers =====
    orbis_id = details.orbis_id if details else None
    bvd_id = details.bvd_id if details else (match.company.bvd_id if match and match.company else None)
    vat_number = None
    national_id = None

    # Extract VAT number and national_id from details
    if details and details.national_id:
        for item in details.national_id:
            if item.get("label") == "VAT number" and item.get("value"):
                vat_number = item.get("value")
            elif item.get("value"):
                national_id = item.get("value") or national_id

    # Fall back to match national_id if not in details
    if not national_id and match and match.company:
        national_id = match.company.national_id

    # Fall back to research national_id
    if not national_id and research:
        national_id = research.national_id

    # ===== Company Info =====
    # Name: prefer details, then match, then research
    name = (
        details.name
        if details
        else (match.company.name if match and match.company else (research.name if research else None))
    )

    # Website/Domain: priority order
    website = None
    domain = None
    if details and details.address and details.address.websites:
        website = details.address.websites[0]
        domain = website
    elif research and research.domain:
        domain = research.domain
        website = f"https://{domain}" if not domain.startswith("http") else domain
    elif match and match.company and match.company.email_or_website:
        website = match.company.email_or_website
        domain = website

    email_domain_type = get_email_domain_type(domain)

    # Industry: prefer research.industry (more descriptive), fall back to NACE category
    industry = research.industry if research else None
    main_industry = get_industry_category(details.nace_code if details else None)
    if not main_industry or main_industry == "unknown":
        main_industry = industry or "unknown"

    # ===== Match Metadata =====
    match_confidence = match.confidence if match else "very_low"
    match_score = match.company.score if match and match.company else None
    match_rating = get_match_rating(match_score)

    # ===== Employees =====
    employees = details.employees if details else None
    employees_bracket = get_employees_bracket(employees)

    # ===== Financials =====
    financials = details.financials if details else None

    revenue = financials.operating_revenue if financials else None
    revenue_bracket = get_revenue_bracket(revenue)

    cash_flow = financials.cash_flow if financials else None
    cash_flow_bracket = get_cash_flow_bracket(cash_flow)

    profit_before_tax = financials.profit_before_tax if financials else None
    profit_before_tax_bracket = get_profit_before_tax_bracket(profit_before_tax)

    profit_loss = financials.profit_loss if financials else None
    profit_loss_bracket = get_profit_loss_bracket(profit_loss)

    shareholders_funds = financials.shareholders_funds if financials else None
    shareholders_funds_bracket = get_shareholders_funds_bracket(shareholders_funds)

    total_assets = financials.total_assets if financials else None
    total_assets_bracket = get_total_assets_bracket(total_assets)

    accounting_year = (
        financials.accounting_year.strftime("%Y-%m-%d") if financials and financials.accounting_year else "unknown"
    )

    financial_health = get_financial_health(financials)
    has_financial_data = financials.has_data() if financials else False

    # ===== Industry Category =====
    industry_category = get_industry_category(details.nace_code if details else None)

    return CompanyFeatures(
        # Identifiers
        orbis_id=orbis_id,
        bvd_id=bvd_id,
        vat_number=vat_number,
        national_id=national_id,
        # Company Info
        name=name,
        website=website,
        domain=domain,
        email_domain_type=email_domain_type,
        industry=industry,
        main_industry=main_industry,
        # Match Metadata
        match_confidence=match_confidence,
        match_score=match_score,
        match_rating=match_rating,
        # Employees
        employees=employees,
        employees_bracket=employees_bracket,
        # Financials with brackets
        revenue=revenue,
        revenue_bracket=revenue_bracket,
        cash_flow=cash_flow,
        cash_flow_bracket=cash_flow_bracket,
        profit_before_tax=profit_before_tax,
        profit_before_tax_bracket=profit_before_tax_bracket,
        profit_loss=profit_loss,
        profit_loss_bracket=profit_loss_bracket,
        shareholders_funds=shareholders_funds,
        shareholders_funds_bracket=shareholders_funds_bracket,
        total_assets=total_assets,
        total_assets_bracket=total_assets_bracket,
        # Other
        accounting_year=accounting_year,
        financial_health=financial_health,
        has_financial_data=has_financial_data,
        industry_category=industry_category,
    )
