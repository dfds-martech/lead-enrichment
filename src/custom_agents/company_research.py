"""
Web search agent

Example usage:
    query = CompanyResearchQuery(
        name="WILDWINE LTD",
        domain="wildwine.com",
        city="London",
        country="UK",
        representative="John Doe"
    )
    agent = create_company_research_agent()

    result = await Runner.run(
        agent,
        query.prompt
    )

"""

from agents import Agent
from pydantic import BaseModel, Field

from common.config import config
from tools.scrape_website import scrape_website
from tools.search_web import search_web


class CompanyResearchResult(BaseModel):
    """Profile summary of a company as discovered by the research agent."""

    domain: str | None = Field(None, description="Primary web domain / website host")
    name: str | None = Field(None, description="Official company name")
    address: str | None = Field(None, description="Registered address or headquarters location")
    city: str | None = Field(None, description="City of the company")
    zip_code: str | None = Field(None, description="Postal code code of the company")
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

    @property
    def to_text(self) -> str:
        out = ""
        for field, value in self.model_dump().items():
            out += f"{field}: {value}\n"
        return out.strip()


COMPANY_RESEARCH_INSTRUCTIONS = """
You are a **Company Research Assistant**.

You receive a `CompanyResearchQuery` object with fields: `name`, `domain`, `city`, `country`, and `representative` (contact person).

You may use two tools: `search_web` (to get search hits) and `scrape_website` (to fetch page text). Use them strategically:

1. Use `search_web` with targeted queries such as:
   - "{name} official website"
   - "{name} {city} {country}"
   - "About {name}"
   - "{name} company information"
   - Search for business registries, LinkedIn pages, company directories

2. Select 2-3 promising URLs (prioritize those matching the provided `domain`) and use `scrape_website` to retrieve their content.

3. From your web search and scraped text, extract factual information and map it into the `CompanyResearchResult` schema.
   Available output fields:
   - name, domain, address, city, zip_code, country, national_id, industry, employee_count, revenue, description, reasoning, sources

4. **Critical rules:**
   - **Do not hallucinate.** Only fill fields you are confident about based on actual sources.
   - **If uncertain, leave null.** Never guess or make assumptions.
   - For conflicting information, prefer authoritative sources (official website, government registry, LinkedIn) and document this in `reasoning`.
   - The `reasoning` field should briefly explain your findings (e.g., "National ID from company registry; employee count from LinkedIn; revenue not found in reliable sources").
   - The `sources` list must include ALL URLs from which you extracted information.

5. **Output requirement:** Return exactly valid JSON conforming to `CompanyResearchResult`. No extra keys, no narrative text.

6. **Efficiency**: Use as few tool calls as possible (2-3 web searches, 2-3 scrapes maximum). If scraping fails, return what you have from search results.

**Example input:**
```json
{
  "name": "Acme Widgets Inc",
  "domain": "acme-widgets.com",
  "city": "Copenhagen",
  "country": "Denmark",
  "representative": "Alice Smith"
}
```
"""


def create_company_research_agent(model: str = config.openai_model) -> Agent[CompanyResearchResult]:
    agent = Agent[CompanyResearchResult](
        name="Company Research Assistant",
        instructions=COMPANY_RESEARCH_INSTRUCTIONS,
        output_type=CompanyResearchResult,
        tools=[search_web, scrape_website],
        model=model,
    )

    return agent
