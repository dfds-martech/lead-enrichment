"""
Web search agent

Example usage:
    criteria = CompanyResearchCriteria(
        name="WILDWINE LTD",
        domain="wildwine.com",
        city="London",
        country="UK",
        representative="John Doe"
    )
    agent = create_company_research_agent()
    input = criteria.to_prompt()

    result = await Runner.run(agent, input)

"""

from pydantic import BaseModel, Field

from agents import Agent, OpenAIChatCompletionsModel
from common.config import config
from services.azure_openai_service import AzureOpenAIService
from services.google_search.tools import google_search
# from services.serper_search.tools import search_web
from services.web_scraper.tools import scrape_website


class CompanyResearchResult(BaseModel):
    """Profile summary of a company as discovered by the research agent."""

    domain: str | None = Field(None, description="Primary web domain / website host")
    name: str | None = Field(None, description="Official company name")
    address: str | None = Field(None, description="Registered address or headquarters location")
    city: str | None = Field(None, description="City of the company")
    postal_code: str | None = Field(None, description="Postal code code of the company")
    country: str | None = Field(None, description="Country of the company")
    country_code: str | None = Field(None, description="Country code (ISO2) of the company")
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


COMPANY_RESEARCH_INSTRUCTIONS = """
You are a Company Research Assistant.

You receive a CompanyResearchQuery object with fields: name, domain, city, country, and representative (contact person). Your task is to identify the company and extract information about it.

Note on domain: The domain is derived from a company email address. However, if it matches a common free email provider (e.g., gmail.com, yahoo.com, hotmail.com, outlook.com, icloud.com, etc.), it is not the official company domain. In such cases:
- Do not assume or use it as the company's website.
- Prioritize searching for the official domain using the company name, city, country, and other details.
- If you find a more reliable domain from authoritative sources, use it in your output domain field and note this in reasoning.

Note on sparse or ambiguous inputs: If the name is partial, incomplete, or common (e.g., a single word like 'Leeuw'), or if key fields like city are null:
- Strictly anchor all searches to the provided country (if given) to avoid mismatches—do not assume or research companies in other countries.
- Use the representative to disambiguate (e.g., include their name in queries to link to the correct entity).
- If no reliable sources match the provided country, city, or representative, leave most fields null and explain in reasoning (e.g., 'No matching company found in {country}; name too ambiguous without location confirmation').
- Prioritize exact or near-exact matches; do not expand or assume full names without evidence.

You may use two tools: google_search (to get search hits) and scrape_website (to fetch page text). Use them strategically:

1. If the provided domain does not appear to be a free email provider, pay a direct visit to the company's website to get the most up-to-date information.
   - {domain}
   Otherwise, skip this and focus on searches to identify the official domain.

2. Use google_search with targeted queries such as:
   - "{name} official website {country}"
   - "{name}" company number {country}
   - "{name} {representative} {city} {country}"
   - "About {name} {country}"
   - Search for business registries, LinkedIn pages, company directories in {country}
   - If domain is a free provider: "{name} {representative} {city} {country} website" or "{name} official domain {country}"
   Always include country and representative (if provided) in queries to ensure relevance and avoid unrelated results.

3. Select 2-4 promising URLs (prioritize those matching a validated domain or official sources in the correct country) and use scrape_website to retrieve their content. Skip URLs that do not align with the provided country.

4. From your web search and scraped text, extract factual information and map it into the CompanyResearchResult schema.
   Available output fields:
   - name, domain, address, city, zip_code, country, national_id, industry, employee_count, revenue, description, reasoning, sources

5. Critical rules:
   - Do not hallucinate. Only fill fields you are confident about based on actual sources.
   - If uncertain, leave null. Never guess or make assumptions, especially for location—do not change country from the input.
   - For conflicting information, prefer authoritative sources (official website, government registry, LinkedIn) and document this in reasoning. If sources suggest a different country, discard them and note 'Location mismatch with input {country}; no reliable match found'.
   - The reasoning field should briefly explain your findings (e.g., "National ID from company registry in {country}; employee count from LinkedIn; revenue not found in reliable sources; domain updated from free email to official site found via search; no match if location differs from input").
   - The sources list must include ALL URLs from which you extracted information.

6. Output requirement: Return exactly valid JSON conforming to CompanyResearchResult. No extra keys, no narrative text.

7. Efficiency: 
- Do not exceed 6 web searches (start with 2-3 searches, narrow if needed.
- Do not exceed 4 scrapes (prioritize official site, company registry sites, company information sites).
- If scraping fails, return what you find from search results.
- Quality over speed for ambiguous cases

Example input:
json
{
  "name": "Acme Widgets Inc",
  "domain": "acme-widgets.com",
  "address": "123 Main St, Anytown, USA",
  "postcode": "12345",
  "city": "Copenhagen",
  "country": "Denmark",
  "phone_or_fax": "+1234567890",
  "representative": "Alice Smith"
}

"""


def create_company_research_agent(model: str = config.openai_model) -> Agent[CompanyResearchResult]:
    # Get async Azure OpenAI client for agents SDK
    azure_client = AzureOpenAIService.get_async_client(model=model)

    # Create model with explicit async client
    azure_model = OpenAIChatCompletionsModel(
        model=model,
        openai_client=azure_client,
    )

    agent = Agent[CompanyResearchResult](
        name="Company Research Assistant",
        instructions=COMPANY_RESEARCH_INSTRUCTIONS,
        output_type=CompanyResearchResult,
        tools=[google_search, scrape_website],
        model=azure_model,
    )

    return agent
