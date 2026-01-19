"""
Cargo extraction agent.

Extracts cargo information from lead descriptions:
- commodity_type: what type of commodity is being transported
- unit_type: what unit type (pallet, container, box, etc.)
- unit_count: how many units
- urgency: how soon transport is needed
- frequency: how often transports will occur
- partnership_needs: one_off, test_run, or long_term
"""

from typing import Literal

from agents import Agent, OpenAIChatCompletionsModel
from pydantic import BaseModel, Field

from common.config import config
from services.azure_openai_service import AzureOpenAIService

Urgency = Literal["immediate", "soon", "normal", "flexible"]
Frequency = Literal["one_off", "weekly", "bi_monthly", "monthly", "quarterly", "few_per_year", "annual"]
PartnershipNeeds = Literal["one_off", "test_run", "long_term"]


class CargoExtractionResult(BaseModel):
    """Output from the cargo extraction agent."""

    # Cargo
    commodity_type: str | None = Field(
        None, description="Type of commodity being transported (e.g., fresh fish, electronics)"
    )
    unit_type: str | None = Field(None, description="Type of unit (e.g., pallet, container, box)")
    unit_count: int | None = Field(None, description="Number of units")

    # Timing
    urgency: Urgency | None = Field(None, description="How soon transport is needed")
    frequency: Frequency | None = Field(None, description="How often transports will occur")

    # Intent
    partnership_needs: PartnershipNeeds | None = Field(
        None, description="Partnership intent: one_off, test_run, or long_term"
    )

    reasoning: str = Field("", description="Explanation of extraction")
    error: str | None = Field(None, description="Error message if extraction failed")


CARGO_EXTRACTION_INSTRUCTIONS = """
You are a Cargo Information Extractor for a logistics company.

You receive user-provided form field inputs and cargo descriptions. Extract the following information:

<CARGO>
1. **commodity_type**: What type of commodity is being transported?
   - Examples: "fresh fish", "electronics", "machinery", "textiles", "chemicals"
   - Be specific but concise
   - Return null if not mentioned

2. **unit_type**: What is the unit/packaging type?
   - Examples: "pallet", "container", "box", "crate", "barrel", "bag"
   - Return null if not mentioned

3. **unit_count**: How many units?
   - Return as an integer
   - Return null if not mentioned or unclear
</CARGO>

<TIMING>
4. **urgency**: How soon is the transport needed?
   - "immediate": ASAP, urgent, within days
   - "soon": within 1-2 weeks
   - "normal": within a month, standard timeline
   - "flexible": no rush, whenever convenient
   - Return null if not mentioned

5. **frequency**: What is the user's intent for frequency of transports?
   - "one_off": single shipment, one-time
   - "weekly": every week
   - "bi_monthly": 2-3 times per month
   - "monthly": once per month
   - "quarterly": once per quarter
   - "few_per_year": 2-3 times per year
   - "annual": once per year
   - Look for hints like "test shipment could lead to longer term" → potential for recurring
   - Check {partnership_needs} field: "OneOff" suggests one_off, "Recurring" suggests regular frequency
   - Return null if not mentioned
</TIMING>

<INTENT>
6. **partnership_needs**: What is the user's partnership intent?
   - "test_run": description mentions "test", "trial", "test shipment", "test run" - this OVERRIDES the form field
   - "long_term": form field {partnership_needs} is "Recurring" or "LongTerm", and no test mentioned
   - "one_off": form field {partnership_needs} is "OneOff", and no test mentioned
   - Priority: description mentioning test > form field value
   - Return null if unclear
</INTENT>

<OTHER>
**reasoning**: Brief explanation of what you found or why fields are null
</OTHER>

<RULES>
- Only extract what is explicitly stated or clearly implied
- Return null for fields where information is not available
- Keep reasoning brief (1-2 sentences)
</RULES>

<OUTPUT>
Return valid JSON conforming to the CargoExtractionResult schema. No extra text.
</OUTPUT>
"""


def create_cargo_extraction_agent(model: str = config.openai_model) -> Agent[CargoExtractionResult]:
    """Create an agent for extracting basic cargo information."""
    azure_client = AzureOpenAIService.get_async_client(model=model)

    azure_model = OpenAIChatCompletionsModel(
        model=model,
        openai_client=azure_client,
    )

    return Agent[CargoExtractionResult](
        name="Cargo Extraction Assistant",
        instructions=CARGO_EXTRACTION_INSTRUCTIONS,
        output_type=CargoExtractionResult,
        tools=[],
        model=azure_model,
    )
