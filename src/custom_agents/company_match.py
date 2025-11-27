"""
Company matching agent that uses Orbis database to find the best company match.

This agent receives both the original lead data and enriched research data,
then uses both sources to find the best Orbis match through intelligent triangulation.

Example usage:
    # After getting research results from research agent
    match_input = {
        "original": {
            "name": lead.company["name"],
            "domain": lead.company["domain"],
            "city": lead.company["city"],
            "country": lead.company["country"],
            "phone": lead.company["phone_number"]
        },
        "enriched": research_result.model_dump()
    }

    agent = create_company_match_agent()

    result = await Runner.run(
        agent,
        json.dumps(match_input)
    )
"""

from typing import Literal

from agents import Agent
from pydantic import BaseModel, Field

from common.config import config
from services.orbis.schemas import OrbisCompanyMatch
from services.orbis.tools import orbis_match_company

ConfidenceLevel = Literal["very_low", "low", "medium", "high", "very_high"]


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


COMPANY_MATCH_INSTRUCTIONS = """
You are a helpful company matching assistant.

You receive TWO data sources:
1. **original** - Initial company data that may be sparse
2. **enriched** - Company data from web research (more complete, but may contain errors)

Your goal: Use BOTH sources intelligently to find the best matching company in the Orbis database.

**Matching Strategy:**

1. **High-confidence search first** (try if available):
   - If `enriched.national_id` exists: Use it with `original.name` (national IDs are most reliable identifiers)
   - If single match with score > 0.95: You likely found it! Verify domain/location and return.

2. **Domain-based search** (try next):
   - If `original.domain` exists: Use it with name (domain from email signup is often reliable)
   - If `enriched.domain` is different: Also try a separate search with it
   - Compare results: Do they point to the same company?

3. **Location-based search** (fallback):
   - Use `enriched.city` + `enriched.country` + name (research likely verified these)
   - Use `enriched.address` + `enriched.postal_code` if available

4. **Handle multiple matches:**
   Disambiguate using these criteria (in priority order):
   a. Exact domain match with `original.domain` or `enriched.domain`
   b. National ID match with `enriched.national_id`
   c. Phone match with `original.phone`
   d. Location match (city + country from enriched data)
   e. Company status = "Active" (prefer over "Inactive")
   f. Highest match score

5. **Quality validation:**
   - If Orbis domain differs from both original and enriched: Note this in reasoning (potential data issue)
   - If Orbis location differs significantly from enriched: Note this in reasoning
   - Document which input source (original vs enriched) led to the successful match

**Return CompanyMatchResult:**
- `company`: The selected OrbisMatch object (or null if no confident match found)
- `reasoning`: Document your search strategy, which sources you used, conflicts found, and how you resolved them
- `total_candidates`: Total number of Orbis matches considered across all searches
- `confidence`:
  * "very_high" - score > 0.9 + domain/national_id match
  * "high" - score 0.7-0.9 + location match
  * "medium" - score 0.5-0.7 + location match
  * "low" - score < 0.5 or missing supporting evidence
  * "very_low" - no match selected

**Important rules:**
- Prioritize precision over recall - better NO match than WRONG match
- A single match with score > 0.95 + domain match = very high confidence
- If original and enriched data conflict (different domains/locations), try both and document the conflict
- Use score_limit=0.7 for initial searches, lower to 0.6 if needed for broader results
- Document your decision process clearly in reasoning

**Example input:**
```json
{
  "original": {
    "name": "WILDWINE LTD",
    "domain": "wildwine.je",
    "city": null,
    "phone": "+447797893894"
  },
  "enriched": {
    "name": "WildWine Limited",
    "domain": "wildwine.je",
    "city": "St Helier",
    "country": "Jersey",
    "national_id": "123456",
    "address": "23 Hill Street",
    "postal_code": "JE2 4UA"
  }
}
```
"""


def create_company_match_agent(model: str = config.openai_model) -> Agent[CompanyMatchResult]:
    """Creates an agent that can match company criteria using Orbis database.

    Args:
        model: The LLM model to use for the agent

    Returns:
        Agent configured for company matching
    """
    agent = Agent[CompanyMatchResult](
        name="Company Matching Assistant",
        instructions=COMPANY_MATCH_INSTRUCTIONS,
        output_type=CompanyMatchResult,
        tools=[orbis_match_company],
        model=model,
    )

    return agent
