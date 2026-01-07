import json
from typing import Literal

from pydantic import BaseModel, Field

from services.orbis.schemas import OrbisCompanyMatch

ConfidenceLevel = Literal["very_low", "low", "medium", "high", "very_high"]


class CompanyResearchCriteria(BaseModel):
    """Query to research a company."""

    name: str | None = Field(None, description="Company name")
    domain: str | None = Field(None, description="Primary web domain / website host")
    city: str | None = Field(None, description="City of the company")
    country: str | None = Field(None, description="Country of the company")
    country_code: str | None = Field(None, description="Country code of the company")
    address: str | None = Field(None, description="Address of the company")
    postcode: str | None = Field(None, description="Postcode of the company")
    national_id: str | None = Field(None, description="National ID of the company")
    industry: str | None = Field(None, description="Industry of the company")
    email_or_website: str | None = Field(None, description="Email or website domain")
    phone_or_fax: str | None = Field(None, description="Phone number or fax number")
    ticker: str | None = Field(None, description="Ticker symbol of the company")
    representative: str | None = Field(None, description="Optional contact person associated with the company.")

    def to_prompt(self) -> str:
        qjson = self.model_dump(exclude_none=True, by_alias=False)
        qjson_text = json.dumps(qjson, ensure_ascii=False, indent=2)

        lines = [
            f"Use this JSON object as input to conduct your company research:\n{qjson_text}\n",
            "Instructions:",
            "- Use these hints as starting points, but verify via web search and scraping.\n"
            "- Do not hallucinate any data. Only fill fields you are confident in.\n"
            "- Output exactly valid JSON conforming to the `CompanyResearchResult` schema.",
        ]

        if self.representative:
            lines.extend(
                [
                    "\nNotes:",
                    "The field 'representative' refers to the person who submitted or is associated with the lead, ",
                    "not the company itself.\n\n",
                ]
            )

        return "\n".join(lines)

    def to_orbis_match_criteria(self) -> dict[str, str]:
        """
        Convert to Orbis match criteria format.

        Returns:
            Dictionary with Orbis API field names as keys
        """
        criteria = {}

        if self.name:
            criteria["Name"] = self.name
        if self.city:
            criteria["City"] = self.city
        if self.country:
            criteria["Country"] = self.country
        if self.address:
            criteria["Address"] = self.address
        if self.postcode:
            criteria["PostCode"] = self.postcode
        if self.national_id:
            criteria["NationalId"] = self.national_id
        if self.domain or self.email_or_website:
            criteria["EMailOrWebsite"] = self.domain or self.email_or_website
        if self.phone_or_fax:
            criteria["PhoneOrFax"] = self.phone_or_fax
        if self.ticker:
            criteria["Ticker"] = self.ticker

        return criteria

    def __str__(self) -> str:
        return f"CompanyResearchCriteria(name='{self.name}', domain='{self.domain}', city='{self.city}', country='{self.country}')"


class CompanyResearchResult(BaseModel):
    """Profile summary of a company as discovered by the research agent."""

    domain: str | None = Field(None, description="Primary web domain / website host")
    name: str | None = Field(None, description="Official company name")
    address: str | None = Field(None, description="Registered address or headquarters location")
    city: str | None = Field(None, description="City of the company")
    postal_code: str | None = Field(None, description="Postal code code of the company")
    country: str | None = Field(None, description="Country of the company")
    national_id: str | None = Field(None, description="Official national company identifier (e.g. CVR, VAT, etc.)")
    industry: str | None = Field(None, description="Industry or sector in which the company operates")
    employee_count: int | None = Field(None, description="Number of employees (if available)")
    revenue: str | None = Field(None, description="Annual revenue, in local currency or approximate (if available)")
    description: str | None = Field(None, description="Short company description or summary")
    reasoning: str | None = Field(
        None,
        description="Your reasoning or chain-of-thought for choices/values. Keep it short and concise.",
    )
    sources: list[str] = Field(default_factory=list, description="List of URLs from which you extracted information")

    def __str__(self) -> str:
        return f"CompanyResearchResult(name='{self.name}', domain='{self.domain}', city='{self.city}', country='{self.country}')"


class CompanyMatchResult(BaseModel):
    """Result of matching a company in Orbis database."""

    company: OrbisCompanyMatch | None = Field(None, description="The selected Orbis company match, if found")
    reasoning: str = Field(description="Explanation of match selection or why no match was found")
    total_candidates: int = Field(0, description="Total number of candidates considered")
    confidence: ConfidenceLevel = Field(default="very_low", description="Confidence level of the match")

    # Enriched fields not in Orbis
    domain: str | None = Field(None, description="Domain from research if not available in Orbis")
    industry: str | None = Field(None, description="Industry from research if not available in Orbis")
    description: str | None = Field(None, description="Company description from research")

    def inspect(self) -> str:
        parts = [
            "### CompanyMatchResult ###\n",
            f"name: {self.company.name if self.company else 'No match'}",
            f"bvd_id: {self.company.bvd_id if self.company else 'No match'}",
            f"Industry: {self.industry or '-'}",
            f"Domain: {self.domain or '-'}",
            "",
            f"score: {self.company.score if self.company else 'No match'}",
            f"Confidence: {self.confidence}",
            f"Total candidates considered: {self.total_candidates}",
            "",
            "\n[Reasoning]",
            self.reasoning,
            "",
            "\n[Research]",
            f"{self.description or '-'}",
        ]
        return "\n".join(line for line in parts if line)
