import json

from pydantic import BaseModel, Field


class CompanyResearchQuery(BaseModel):
    """Query to research a company."""

    name: str = Field(description="Official company name")
    domain: str | None = Field(None, description="Primary web domain / website host")
    city: str | None = Field(None, description="City of the company")
    country: str | None = Field(None, description="Country of the company")
    representative: str | None = Field(None, description="Optional contact person associated with the company.")

    @property
    def prompt(self) -> str:
        qjson = self.model_dump(exclude_none=True, by_alias=False)
        qjson_text = json.dumps(qjson, ensure_ascii=False, indent=2)
        return (
            "Use this JSON object as input to conduct your company research:\n"
            f"{qjson_text}\n\n"
            "Notes:\n"
            "- The field 'representative' refers to the person who submitted or is associated with the lead, "
            "not the company itself.\n\n"
            "Instructions:\n"
            "- Use these hints as starting points, but verify via web search and scraping.\n"
            "- Do not hallucinate any data. Only fill fields you are confident in.\n"
            "- Output exactly valid JSON conforming to the `CompanyResearchResult` schema."
        )

        # field_labels = {
        #     "domain": "Comapny website domain",
        #     "name": "Company name",
        #     "location": "Company location",
        #     "first_name": "First Name of company representative",
        #     "last_name": "Last Name of company representative",
        # }
        # out = "Research this company:\n"
        # for field, value in self.model_dump().items():
        #     label = field_labels.get(field, field.replace("_", " ").title())
        #     if value is not None:
        #         out += f"{label}: {str(value).strip()}\n"
        #  return out.strip()
