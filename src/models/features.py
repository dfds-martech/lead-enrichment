"""Feature models for enrichment results.

Extracted features from raw enrichment data, providing categorized
and normalized values for analysis and decision-making.
"""

from pydantic import BaseModel, Field


class CompanyFeatures(BaseModel):
    """Extracted features from company enrichment data."""

    # Identifiers
    orbis_id: str | None = Field(None, description="Orbis ID of the company")
    bvd_id: str | None = Field(None, description="BvD ID of the company")
    vat_number: str | None = Field(None, description="VAT number if available")
    national_id: str | None = Field(None, description="National company identifier")

    # Company Info
    name: str | None = Field(None, description="Company name")
    website: str | None = Field(None, description="Company website URL")
    domain: str | None = Field(None, description="Company domain")
    email_domain_type: str = Field(description="Email domain type: 'company' or 'free' or 'unknown'")
    industry: str | None = Field(None, description="Industry description from research")
    main_industry: str = Field(description="Main industry category")

    # Match Metadata
    match_confidence: str = Field(description="Match confidence level")
    match_score: float | None = Field(None, description="Match score from Orbis")
    match_rating: str = Field(
        description="Match rating: 'excellent', 'very_good', 'good', 'fair', 'poor', or 'unknown'"
    )

    # Employees
    employees: float | None = Field(None, description="Number of employees")
    employees_bracket: str

    # Financials with brackets
    revenue: float | None = Field(None, description="Operating revenue in EUR")
    revenue_bracket: str
    cash_flow: float | None = Field(None, description="Cash flow in EUR")
    cash_flow_bracket: str
    profit_before_tax: float | None = Field(None, description="Profit before tax in EUR")
    profit_before_tax_bracket: str
    profit_loss: float | None = Field(None, description="Profit/loss in EUR")
    profit_loss_bracket: str
    shareholders_funds: float | None = Field(None, description="Shareholders funds in EUR")
    shareholders_funds_bracket: str
    total_assets: float | None = Field(None, description="Total assets in EUR")
    total_assets_bracket: str

    # Other
    accounting_year: str
    financial_health: str = Field(
        description="Financial health indicator: 'healthy', 'moderate', 'at_risk', or 'unknown'"
    )
    has_financial_data: bool = Field(description="Whether financial data is available")
    industry_category: str = Field(description="Industry category derived from NACE code, or 'unknown'")
