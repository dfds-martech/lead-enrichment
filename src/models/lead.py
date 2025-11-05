import ast
import json
from enum import Enum

from pydantic import BaseModel, Field

from models.company import CompanyResearchCriteria


class LeadType(str, Enum):
    """Types of leads based on form type."""

    LOGISTICS_SOLUTIONS = "logistics_solutions"
    CUSTOMS_CLEARANCE = "customs_clearance"
    FREIGHT_SHIPPING = "freight_shipping"
    CONTRACT_LOGISTICS = "contract_logistics"


FORM_TYPE_MAPPING: dict = {
    "Logistics Quote Form": LeadType.LOGISTICS_SOLUTIONS,
    "Customs Clearance Quote Form": LeadType.CUSTOMS_CLEARANCE,
    "Freight Quote Form": LeadType.FREIGHT_SHIPPING,
    "Contract Logistics Quote Form": LeadType.CONTRACT_LOGISTICS,
}

# mapping for differnet lead forms
FORM_PAYLOAD_MAPPINGS: dict = {
    "Logistics Quote Form": {
        "cargo_type": "TypeOfCargoRoad",
        "request_type": "TypeOfRequest",
        "partnership_needs": "PartnershipNeeds",
    },
    "Customs Clearance Quote Form": {
        "cargo_type": "TypeOfCargo",
        "request_type": "TypeOfRequest",
        "clearance_service": "CustomsClearanceService",
        "partnership_needs": "PartnershipNeeds",
    },
    "Freight Quote Form": {
        "route": "Route",
        "unit_type": "UnitType",
        "packaging_required": "iNeedPackagingServices",
        "partnership_needs": "PartnershipNeeds",
    },
    "Contract Logistics Quote Form": {
        "service_type": "ContractLogisticsService",
        "request_type": "TypeOfRequest",
        "partnership_needs": "PartnershipNeeds",
    },
}


class LeadCountry(BaseModel):
    """A country from the CRM lead record."""

    alpha2: str | None = Field(None, alias="dfds_alpha2code")
    alpha3: str | None = Field(None, alias="dfds_alpha3code")
    name: str | None = Field(None, alias="dfds_name")

    class Config:
        populate_by_name = True  # Allows using either the field name or alias

    @classmethod
    def from_crm_field(cls, value) -> "LeadCountry":
        """Parse country data that might be dict, JSON string, Python dict string, or None."""
        if value is None:
            return cls()
        if isinstance(value, str):
            try:
                # Try JSON first
                value = json.loads(value)
            except (json.JSONDecodeError, ValueError):
                try:
                    # Fall back to Python dict string
                    value = ast.literal_eval(value)
                except (ValueError, SyntaxError):
                    return cls()
        if isinstance(value, dict):
            return cls(**value)
        return cls()


class Lead(BaseModel):
    """A lead from the CRM (including associated entires, e.g. company, delivery, and collection)."""

    # Metadata
    type: LeadType | None = None
    created_on: str | None = None
    modified_on: str | None = None

    # Processed fields
    identifiers: dict
    user: dict
    company: dict
    collection: dict
    delivery: dict
    quote: dict

    # Raw data
    record: dict
    payload: dict

    @classmethod
    def from_crm(cls, record) -> "Lead":
        """Build a Lead from a CRM record."""
        payload = json.loads(record.get("dfds_fullpayload", "{}"))

        # Extract user info
        userSegmentID = payload.get("userSegmentID", {})
        phone_number = payload.get("PhoneNumber", None)
        company_email = payload.get("CompanyEmail", None)

        # User identifiers
        identifiers = {
            "user_id": userSegmentID.get("UserId", None),
            "anonymous_id": userSegmentID.get("anonymousUserId", None),
            "email": company_email,
            "phone": phone_number,
        }

        # User details
        first_name = payload.get("FirstName", "").strip()
        last_name = payload.get("LastName", "").strip()
        user = {
            "first_name": first_name,
            "last_name": last_name,
            "full_name": f"{first_name} {last_name}",
        }

        # Company details
        company_city = record.get("address1_city", None) or record.get("address1_composite", None)
        company_country = LeadCountry.from_crm_field(record.get("dfds_countrylookup"))
        company = {
            "name": payload.get("CompanyName"),
            "domain": company_email.split("@")[1] if company_email else None,
            "city": company_city,
            "postal_code": record.get("address1_postalcode", None),
            "country": company_country.name,
            "country_alpha2": company_country.alpha2,
            "phone_number": phone_number,
        }

        # Logistics Solutions and Customs Clearance
        # Collection + Delivery
        collection_country = LeadCountry.from_crm_field(record.get("dfds_collectioncountry"))
        delivery_country = LeadCountry.from_crm_field(record.get("dfds_deliverycountry"))
        collection = {
            "city": record.get("dfds_collectioncity", None),
            "country": collection_country.name,
            "country_alpha2": collection_country.alpha2,
        }
        delivery = {
            "city": record.get("dfds_deliverycity", None),
            "country": delivery_country.name,
            "country_alpha2": delivery_country.alpha2,
        }

        # Quote details
        form_title = payload.get("formTitle")
        lead_type = FORM_TYPE_MAPPING.get(form_title)

        quote = {
            "form_title": form_title,
            "form_locale": payload.get("formLocale"),
            "number": record.get("dfds_requestnumber"),
            "type": record.get("dfds_requesttype"),
            "description": payload.get("DescribeYourCargo"),
            "notes": record.get("dfds_quotenotes"),
        }
        for key, value in FORM_PAYLOAD_MAPPINGS.get(form_title, {}).items():
            quote[key] = payload.get(value, None)

        return cls(
            type=lead_type,
            created_on=record.get("createdon", None),
            modified_on=record.get("modifiedon", None),
            identifiers=identifiers,
            user=user,
            company=company,
            collection=collection,
            delivery=delivery,
            quote=quote,
            payload=payload,
            record=dict(sorted(record.items())),
        )

    @property
    def company_research_query(self) -> CompanyResearchCriteria:
        """Build a company research query from this lead."""
        return CompanyResearchCriteria(
            name=self.company.get("name"),
            domain=self.company.get("domain"),
            city=self.company.get("city"),
            country=self.company.get("country"),
            phone=self.company.get("phone_number"),
            representative=self.user.get("full_name") or None,
        )
