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

CommodityCategory = Literal[
    "perishable_food",  # salmon, frozen meat/fries, yogurt, berries, eggs
    "automotive_vehicle",  # cars, vans, motorcycles, tractors, halfcut cars
    "electronics_consumer",  # headphones, small appliances, fitness
    "chemicals",  # ethyl alcohol, ADR, N2O
    "textiles",  # textiles, tiles, pallets, rubber fenders, soymeal
    "general_dry",  # tiles, pallets, rubber fenders, soymeal
    "pharma",
    "project_oversized",  # machinery, long screws, hoist, metal structures
    "livestock",
    "personal_household",
    "other",
]

Urgency = Literal["immediate", "soon", "normal", "flexible"]
Frequency = Literal["one_off", "weekly", "bi_monthly", "monthly", "quarterly", "few_per_year", "annual"]
PartnershipNeeds = Literal["one_off", "test_run", "long_term"]

EquipmentGroup = Literal[
    "trailer",
    "reefer trailer",
    "container",
    "cassette",
    "chassi",
    "driveable unit",
    "flat",
    "shuttlewaggon",
    "other",
]

UnitType = Literal[
    "pallet",
    "container",
    "box",
    "crate",
    "barrel",
    "bag",
    "car",
    "car carrier",
    "trailer",
    "trailer (tank)",
    "reefer",
]


class CargoExtractionResult(BaseModel):
    """Output from the cargo extraction agent."""

    # Commodity
    commodity_type: str | None = Field(
        None,
        description="Specific commodity (e.g., 'fresh salmon fillets', 'new passenger cars', 'consumer electronics')",
    )
    commodity_category: CommodityCategory | None = Field(
        None, description="Categorized commodity type for high-value scoring"
    )

    # Packaging
    packaging_type: str | None = Field(
        None,
        description="Packaging (e.g., 'pallets', 'crates', 'drums', 'bulk', 'cartons on pallets', 'none')",
    )

    # Equipment
    equipment_type: str | None = Field(
        None,
        description="Specific equipment inferred (e.g., 'Reefer trailer', '40ft dry container', 'Car transporter trailer', 'Curtain sider/Euroliner', 'Flatbed', 'MAFI/roll trailer')",
    )
    equipment_group: EquipmentGroup | None = Field(
        None, description="Broader group (trailer, container, vehicle, special, reefer, breakbulk)"
    )

    # Unit
    unit_type: UnitType | None = Field(None, description="Type of unit (e.g., pallet, container, box)")
    unit_count: int | None = Field(None, description="Number of units")

    # Special handling flags (high-value drivers)
    temperature_controlled: bool = Field(False, description="Reefer/chilled/frozen needed")
    hazardous: bool | str | None = Field(None, description="True or IMDG class if mentioned")
    oversized_project: bool = Field(False, description="Out-of-gauge, heavy, project cargo")
    high_value: bool = Field(
        False, description="Inferred from commodity (electronics, luxury, pharma) or explicit mention"
    )

    # Timing
    urgency: Urgency | None = Field(None, description="How soon transport is needed")
    frequency: Frequency | None = Field(None, description="How often transports will occur")

    # Intent
    partnership_needs: PartnershipNeeds | None = Field(
        None, description="Partnership intent: one_off, test_run, or long_term"
    )

    # Metadata
    reasoning: str = Field(
        ..., description="Detailed step-by-step extraction and inference logic (key for audit/high-value rules)"
    )
    confidence: float = Field(..., description="0-1 extraction confidence")
    error: str | None = Field(None, description="Error message if extraction failed", exclude=True)


CARGO_EXTRACTION_INSTRUCTIONS = """
<ROLE>
You are an expert DFDS cargo classifier for freight ferries, ro-ro, containers, trailers, and logistics.
</ROLE>

<TASK>
Analyze the full submission: including the form type, collection/delivery locations if available, form fields (Request Type, Partnership Needs, Cargo Type, Load Type, Unit Type, Route), and especially the Cargo Description (often multilingual, noisy, or detailed with dims/weights).

Extract and infer accurately. Translate non-English text. Use DFDS domain knowledge to infer equipment from commodity + load type.
</TASK>

<FIELDS>
## Commodity
- **commodity_type**: Specific commodity (e.g., "fresh salmon fillets", "new passenger cars")
- **commodity_category**: Classify into one of: perishable_food, automotive_vehicle, electronics_consumer, chemicals_hazardous, general_dry, pharma, project_oversized, livestock, personal_household, other

## Packaging & Equipment
- **packaging_type**: How it's packaged (pallets, crates, drums, bulk, none)
- **equipment_type**: Specific equipment (Reefer trailer, 40ft container, Car transporter, Flatbed, etc.)
- **equipment_group**: Broader category - trailer|car|cassette|chassi|container|driveable unit|flat|shuttlewaggon|other
  - Container: mentions "container", "20ft", "40ft"
  - Trailer: standard cargo (pallets, boxes, food) — most common default. Reefer = still Trailer.
  - Car: passenger vehicles (new cars, SUVs)
  - Flat: oversized/heavy (steel beams, machinery, wind turbines)
  - Driveable Unit: powered vehicle with goods

## Units
- **unit_type**: pallet|container|box|crate|barrel|bag|car|trailer|reefer|etc.
- **unit_count**: integer, null if unclear

## Special Handling Flags
- **temperature_controlled**: True if frozen/chilled/reefer keywords (-18°C, +2-8°C, fresh fish, pharma)
- **hazardous**: True or IMDG class (Class 3, ADR, UN number)
- **oversized_project**: True if out-of-gauge, heavy lift, project cargo
- **high_value**: Infer from commodity (electronics, pharma, luxury) or explicit mention

## Timing & Intent
- **urgency**: immediate|soon|normal|flexible (null if not mentioned)
- **frequency**: one_off|weekly|bi_monthly|monthly|quarterly|few_per_year|annual
- **partnership_needs**:
  - "test_run" if description mentions test/trial (OVERRIDES form field)
  - "long_term" if form says Recurring/LongTerm
  - "one_off" if form says OneOff

## Metadata
- **reasoning**: Step-by-step extraction logic (2-4 sentences)
- **confidence**: 0.0-1.0 based on clarity of input
</FIELDS>

<INFERENCE_RULES>
- Pallets + low count (1-5) → likely PartLoad
- Pallets + high count or FullLoad → Trailer/Container
- Vehicles mentioned → equipment_group = "car"
- Temperature keywords (frozen, chilled, -18, fresh fish, pharma) → temperature_controlled = True, equipment = Reefer
- Dangerous goods / ADR / Class X → hazardous = True with details
- Large dimensions / heavy / project → oversized_project = True, equipment = Flat
</INFERENCE_RULES>

<EXAMPLES>
Example 1:
Input: "BEVERAGE. TABLE WINE. x3 pallet 120x80x180 855kgs each, x1 pallet 120x80x150 620kgs" + Load Type: FullLoad, Cargo Type: TemperatureControlled
Output: commodity_type="Table wine/beverage", commodity_category="perishable_food", packaging_type="pallets", equipment_type="Reefer trailer", equipment_group="trailer", unit_type="pallet", unit_count=4, temperature_controlled=True

Example 2:
Input: "commodity is fresh fish/salmon" + Cargo Type: FoodProducts, PartnershipNeeds: OneOff
Output: commodity_type="Fresh salmon/fish", commodity_category="perishable_food", equipment_type="Reefer trailer", temperature_controlled=True, partnership_needs="one_off"

Example 3:
Input: "Vi importerer biler fra England... vanlige personbiler" + LongTerm
Output: commodity_type="Passenger cars", commodity_category="automotive_vehicle", packaging_type="none", equipment_group="car", partnership_needs="long_term"

Example 4:
Input: "10 industrial pallets Frozen French fries ca 800 kg per pallet"
Output: commodity_type="Frozen French fries", commodity_category="perishable_food", packaging_type="pallets", equipment_type="Reefer trailer", equipment_group="trailer", unit_type="pallet", unit_count=10, temperature_controlled=True

Example 5:
Input: "1 Screw D.203,2 x 5409 mm, Wooden
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
