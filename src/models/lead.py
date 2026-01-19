import ast
import json
from enum import Enum
from typing import ClassVar, Literal

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


class LeadQuote(BaseModel):
    """Quote form data normalized across form types."""

    # Field mappings
    _FIELD_MAPPINGS: ClassVar[dict[str, dict[str, str]]] = {
        "Logistics Quote Form": {
            "DescribeYourCargo": "description",
            "TypeOfCargoRoad": "cargo_type",
            "TypeOfRoadRequest": "load_type",
            "TypeOfRequest": "request_type",
            "PartnershipNeeds": "partnership_needs",
        },
        "Customs Clearance Quote Form": {
            "DescribeYourCargo": "description",
            "TypeOfCargo": "cargo_type",
            "TypeOfRequest": "request_type",
            "CustomsClearanceService": "clearance_service",
            "PartnershipNeeds": "partnership_needs",
        },
        "Freight Quote Form": {
            "DescribeYourCargo": "description",
            "Route": "route",
            "UnitType": "unit_type",
            "iNeedPackagingServices": "packaging_required",
            "PartnershipNeeds": "partnership_needs",
        },
        "Contract Logistics Quote Form": {
            "DescribeYourCargo": "description",
            "ContractLogisticsService": "service_type",
            "TypeOfRequest": "request_type",
            "PartnershipNeeds": "partnership_needs",
        },
    }

    # Common fields
    form_title: str | None = Field(None, description="Form type identifier")
    form_locale: str | None = Field(None, description="Form locale (en, de, etc.)")
    description: str | None = Field(None, description="DescribeYourCargo - user's cargo description")
    partnership_needs: str | None = Field(None, description="OneOff, Recurring, etc.")

    # Logistics & Customs fields
    cargo_type: str | None = Field(None, description="TypeOfCargoRoad/TypeOfCargo")
    load_type: str | None = Field(None, description="FullLoad, PartLoad (Logistics only)")
    request_type: str | None = Field(None, description="Business, Private (Logistics/Customs/Contract)")

    # Customs specific
    clearance_service: str | None = Field(None, description="Customs clearance service type")

    # Freight specific
    route: str | None = Field(None, description="Route type (Freight only)")
    unit_type: str | None = Field(None, description="Container type (Freight only)")
    packaging_required: str | None = Field(None, description="Packaging services needed (Freight only)")

    # Contract specific
    service_type: str | None = Field(None, description="Contract logistics service type")

    # CRM fields (from_crm only)
    number: int | None = Field(None, description="Request number from CRM")
    notes: str | None = Field(None, description="Quote notes from CRM")

    @classmethod
    def from_payload(cls, payload: dict, **extras) -> "LeadQuote":
        """Create LeadQuote from raw form payload.

        Args:
            payload: The raw form payload dict
            **extras: Additional fields to set (e.g., number, notes from CRM)
        """
        form_title = payload.get("formTitle")
        mappings = cls._FIELD_MAPPINGS.get(form_title, {})

        data = {
            "form_title": form_title,
            "form_locale": payload.get("formLocale"),
        }

        # Map payload fields to model fields
        for payload_key, model_key in mappings.items():
            if payload_key in payload:
                data[model_key] = payload[payload_key]

        # Add any extra fields (e.g., CRM-specific)
        data.update(extras)

        return cls(**data)

    def to_prompt(self) -> str:
        """Convert quote fields to prompt format for LLM extraction."""
        sections = []

        form_fields = []

        if self.request_type:
            form_fields.append(f"- Request Type: {self.request_type}")
        if self.partnership_needs:
            form_fields.append(f"- Partnership Needs: {self.partnership_needs}")
        if self.cargo_type:
            form_fields.append(f"- Cargo Type: {self.cargo_type}")
        if self.load_type:
            form_fields.append(f"- Load Type: {self.load_type}")
        if self.unit_type:
            form_fields.append(f"- Unit Type: {self.unit_type}")
        if self.route:
            form_fields.append(f"- Route: {self.route}")

        if form_fields:
            sections.append("<Form Fields>\n" + "\n".join(form_fields) + "\n</Form Fields>")

        if self.description:
            sections.append(f"<Cargo Description>\n{self.description}\n</Cargo Description>")

        return "\n\n".join(sections)


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
    id: str
    identifiers: dict
    contact: dict
    company: dict
    collection: dict
    delivery: dict
    quote: LeadQuote

    # Raw data
    record: dict
    payload: dict

    @classmethod
    def from_event(cls, event: dict) -> "Lead":
        """Build a Lead from an incoming lead event."""

        full_payload_str = event.get("lead", {}).get("fullPayload")
        if isinstance(full_payload_str, str):
            try:
                payload = json.loads(full_payload_str)
            except (json.JSONDecodeError, ValueError):
                payload = {}
        else:
            payload = full_payload_str or {}

        identifiers = _extract_identifiers_from_payload(event, payload)
        company = _extract_company(event, identifiers)
        contact = _extract_contact(event, payload)
        collection = _extract_loading_point("collection", event)
        delivery = _extract_loading_point("delivery", event)

        # Quote details
        form_title = payload.get("formTitle")
        lead_type = FORM_TYPE_MAPPING.get(form_title) if form_title else None
        quote = LeadQuote.from_payload(payload)

        return cls(
            id=event.get("lead", {}).get("crmLeadId", "UNKNOWN_LEAD_ID"),
            type=lead_type,
            created_on=event.get("eventDate"),
            modified_on=event.get("eventDate"),
            identifiers=identifiers,
            contact=contact,
            company=company,
            collection=collection,
            delivery=delivery,
            quote=quote,
            payload=payload,
            record=event,
        )

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
            "user_id": userSegmentID.get("dfdsUserId", None),
            "anonymous_id": userSegmentID.get("anonymousUserId", None),
            "email": company_email,
            "phone": phone_number,
        }

        # User details
        first_name = payload.get("FirstName", "").strip()
        last_name = payload.get("LastName", "").strip()
        contact = {
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
            "country_code": company_country.alpha2,
            "phone_number": phone_number,
        }

        # Logistics Solutions and Customs Clearance
        # Collection + Delivery
        collection_country = LeadCountry.from_crm_field(record.get("dfds_collectioncountry"))
        delivery_country = LeadCountry.from_crm_field(record.get("dfds_deliverycountry"))
        collection = {
            "city": record.get("dfds_collectioncity", None),
            "country": collection_country.name,
            "country_code": collection_country.alpha2,
        }
        delivery = {
            "city": record.get("dfds_deliverycity", None),
            "country": delivery_country.name,
            "country_code": delivery_country.alpha2,
        }

        # Quote details
        form_title = payload.get("formTitle")
        lead_type = FORM_TYPE_MAPPING.get(form_title)
        quote = LeadQuote.from_payload(
            payload,
            number=record.get("dfds_requestnumber"),
            notes=record.get("dfds_quotenotes"),
        )

        return cls(
            type=lead_type,
            created_on=record.get("createdon", None),
            modified_on=record.get("modifiedon", None),
            identifiers=identifiers,
            contact=contact,
            company=company,
            collection=collection,
            delivery=delivery,
            quote=quote,
            payload=payload,
            record=dict(sorted(record.items())),
        )

    @property
    def company_research_criteria(self) -> CompanyResearchCriteria:
        """Build a company research query from this lead."""
        return CompanyResearchCriteria(
            name=self.company.get("name"),
            domain=self.company.get("domain"),
            city=self.company.get("city"),
            address=self.company.get("street"),
            postcode=self.company.get("postal_code"),
            country=self.company.get("country"),
            country_code=self.company.get("country_code"),
            phone_or_fax=self.identifiers.get("phone"),
            representative=self.contact.get("full_name") or None,
        )


def _extract_identifiers_from_payload(event: dict, payload: dict) -> dict:
    """Extract user identifiers from the payload."""

    contact = payload.get("contact", {})
    phone_number = contact.get("phone", None)

    # segment ids are potentially also stored in the 'userSegmentID' object
    userSegmentID = payload.get("userSegmentID", {})
    user_id = userSegmentID.get("userId", None)
    anonymous_id = userSegmentID.get("anonymousUserId", None)

    return {
        "user_id": payload.get("segmentId", user_id) or None,
        "anonymous_id": payload.get("anonymousSegmentId", anonymous_id) or None,
        "email": payload.get("CompanyEmail", None),
        "phone": payload.get("PhoneNumber", None) or phone_number,
    }


def _extract_contact(event: dict, payload: dict) -> dict:
    """Extract user details from the payload."""
    contact = event.get("contact", {})

    # CRM extracts
    contact_first_name = (contact.get("firstName") or "").strip()
    contact_last_name = (contact.get("lastName") or "").strip()
    contact_full_name = f"{contact_first_name} {contact_last_name}".strip()

    # Form payload
    form_first_name = (payload.get("FirstName") or "").strip()
    form_last_name = (payload.get("LastName") or "").strip()
    form_full_name = f"{form_first_name} {form_last_name}".strip()

    # Priotize form payload over CRM extracts
    return {
        "first_name": form_first_name or contact_first_name or None,
        "last_name": form_last_name or contact_last_name or None,
        "full_name": form_full_name or contact_full_name or None,
        "job_title": contact.get("jobTitle"),
        "job_function": contact.get("jobFunction"),
    }


def _extract_company(event: dict, identifiers: dict) -> dict:
    """Extract company details from the event."""
    company = event.get("company", {})
    address = company.get("address", {})
    street_parts = [address.get("line1"), address.get("line2")]
    street = ", ".join(part for part in street_parts if part)

    email = identifiers.get("email")
    domain = email.split("@")[1] if email else None

    return {
        "domain": domain,
        "name": company.get("name", None),
        "street": street or None,
        "city": address.get("city", None),
        "postal_code": address.get("postalCode", None),
        "state": address.get("state", None),
        "country": address.get("country", None),
        "country_code": address.get("country_code", None),
        "crm_account_id": company.get("crmAccountId", None),
        "crm_account_type": company.get("type", None),
        "crm_account_segment": company.get("segment", None),
        "orbis_id": company.get("orbisId", None),
    }


def _extract_loading_point(point: Literal["collection", "delivery"], event: dict) -> dict:
    """Extract collection point details from the event."""
    lead = event.get("lead", {})

    return {
        "city": lead.get(f"{point}City", None),
        "country": lead.get(f"{point}Country", None),
        "country_code": lead.get(f"{point}CountryCode", None),
    }
