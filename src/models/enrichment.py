"""Enrichment result models for the lead enrichment pipeline."""

from pydantic import BaseModel, Field

from custom_agents.company_match import CompanyMatchResult
from custom_agents.company_research import CompanyResearchResult
from models.features import CompanyFeatures
from models.lead import Lead
from services.orbis.schemas import OrbisCompanyDetails


class CompanyEnrichmentResult(BaseModel):
    """Results from company enrichment pipeline (research → match → details → features)."""

    research: CompanyResearchResult | None = Field(None, description="Results from web research agent")
    match: CompanyMatchResult | None = Field(None, description="Results from Orbis matching agent")
    details: OrbisCompanyDetails | None = Field(None, description="Detailed company data from Orbis (if matched)")
    features: CompanyFeatures | None = Field(None, description="Extracted and categorized features from company data")
    error: str | None = Field(None, description="Error message if enrichment failed")


class UserValidationResult(BaseModel):
    """Results from user/lead quality validation checks."""

    name_properly_formatted: bool | None = Field(None, description="Whether first/last name are properly capitalized")
    email_type: str | None = Field(None, description="Type of email: 'company' or 'free' (gmail, yahoo, etc)")
    phone_valid: bool | None = Field(None, description="Whether phone number is valid for the given country")
    error: str | None = Field(None, description="Error message if validation failed")


class CustomEnrichmentResult(BaseModel):
    """Placeholder for future custom enrichment processes."""

    data: dict | None = Field(None, description="Custom enrichment data")
    error: str | None = Field(None, description="Error message if enrichment failed")


class EnrichedLead(BaseModel):
    """Complete enrichment results for a lead from all pipelines."""

    lead: Lead = Field(description="Original lead data")
    company: CompanyEnrichmentResult = Field(description="Company enrichment results")
    user_validation: UserValidationResult = Field(description="User validation results")
    custom: CustomEnrichmentResult = Field(description="Custom enrichment results")
    metadata: dict = Field(default_factory=dict, description="Metadata about enrichment (timestamps, duration, etc.)")
