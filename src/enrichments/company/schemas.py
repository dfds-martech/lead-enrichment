"""Company enrichment schemas.

Defines the structured output models for company enrichment,
organized by domain for clarity and maintainability.
"""

from typing import Literal

from pydantic import BaseModel, Field

from services.orbis.schemas import OrbisCompanyDetails

from .agents.company_match import CompanyMatchResult
from .agents.company_research import CompanyResearchResult

# ============================================================================
# Domain-Specific Feature Models
# ============================================================================


class CompanyIdentifiers(BaseModel):
    """Unique identifiers for the company."""

    orbis_id: str | None = Field(None, description="Orbis ID")
    bvd_id: str | None = Field(None, description="Bureau van Dijk ID")
    national_id: str | None = Field(None, description="National company identifier (e.g., company number)")
    vat_number: str | None = Field(None, description="VAT number if available")


class CompanyAddress(BaseModel):
    """Company address information."""

    street: str | None = Field(None, description="Street address")
    city: str | None = Field(None, description="City")
    postal_code: str | None = Field(None, description="Postal/ZIP code")
    country: str | None = Field(None, description="Country name")
    country_code: str | None = Field(None, description="ISO country code")
    phone: str | None = Field(None, description="Phone number")


class CompanyInfo(BaseModel):
    """Basic company information."""

    name: str | None = Field(None, description="Official company name")
    address: CompanyAddress | None = Field(None, description="Company address")
    website: str | None = Field(None, description="Company website URL")
    domain: str | None = Field(None, description="Primary domain")
    email_domain_type: str = Field("unknown", description="'company', 'free', or 'unknown'")
    description: str | None = Field(None, description="Company description from research")


class CompanyIndustry(BaseModel):
    """Industry classification."""

    description: str | None = Field(None, description="Industry description from research")
    nace_code: str | None = Field(None, description="NACE code from Orbis")
    category: str = Field("unknown", description="Industry category mapped from NACE code")


class CompanyStatus(BaseModel):
    """Company legal and operational status."""

    legal_status: str | None = Field(None, description="Legal status code from Orbis")
    consolidation_code: str | None = Field(None, description="Reporting type: C1|C2|U1|U2|LF")
    is_active: bool = Field(True, description="Whether company is active")


class CompanyMatchMetadata(BaseModel):
    """Metadata about the Orbis matching process."""

    confidence: str = Field("very_low", description="Confidence level: very_low|low|medium|high|very_high")
    score: float | None = Field(None, description="Match score (0.0 - 1.0)")
    candidates_considered: int = Field(0, description="Number of candidates evaluated")
    notes: str | None = Field(None, description="Notes about the match")


class CompanyEmployees(BaseModel):
    """Employee information."""

    count: float | None = Field(None, description="Number of employees")
    bracket: str = Field("unknown", description="Size bracket: 1-9|10-49|50-249|250+|unknown")


class CompanyFinancials(BaseModel):
    """Financial metrics and health indicators."""

    # Raw values (EUR)
    revenue: float | None = Field(None, description="Operating revenue in EUR")
    profit_before_tax: float | None = Field(None, description="Profit before tax in EUR")
    profit_loss: float | None = Field(None, description="Net profit/loss in EUR")
    cash_flow: float | None = Field(None, description="Cash flow in EUR")
    total_assets: float | None = Field(None, description="Total assets in EUR")
    shareholders_funds: float | None = Field(None, description="Shareholders funds in EUR")

    # Brackets for bucketing/filtering
    revenue_bracket: str = Field("unknown", description="Revenue bracket")
    profit_bracket: str = Field("unknown", description="Profit bracket")
    assets_bracket: str = Field("unknown", description="Assets bracket")

    # Credit risk
    credit_risk_rating: str | None = Field(None, description="Credit risk rating category")
    credit_risk_rating_label: str | None = Field(None, description="Credit risk rating short label")

    # Derived metrics
    accounting_year: str = Field("unknown", description="Year of financial data")
    financial_health: Literal["healthy", "moderate", "at_risk", "unknown"] = Field(
        "unknown", description="Financial health assessment"
    )
    has_data: bool = Field(False, description="Whether any financial data is available")


# ============================================================================
# Aggregated Feature Model
# ============================================================================


class CompanyFeatures(BaseModel):
    """Complete extracted features for a company, organized by domain."""

    identifiers: CompanyIdentifiers = Field(default_factory=CompanyIdentifiers)
    info: CompanyInfo = Field(default_factory=CompanyInfo)
    status: CompanyStatus = Field(default_factory=CompanyStatus)
    industry: CompanyIndustry = Field(default_factory=CompanyIndustry)
    match: CompanyMatchMetadata = Field(default_factory=CompanyMatchMetadata)
    employees: CompanyEmployees = Field(default_factory=CompanyEmployees)
    financials: CompanyFinancials = Field(default_factory=CompanyFinancials)


# ============================================================================
# Enrichment Result Model
# ============================================================================


class CompanyEnrichmentResult(BaseModel):
    """Results from company enrichment pipeline (research → match → details → features)."""

    research: CompanyResearchResult | None = Field(None, description="Results from web research agent")
    match: CompanyMatchResult | None = Field(None, description="Results from Orbis matching agent")
    details: OrbisCompanyDetails | None = Field(None, description="Detailed company data from Orbis")
    features: CompanyFeatures | None = Field(None, description="Extracted and categorized features")
    error: str | None = Field(None, description="Error message if enrichment failed")
