import json

from pydantic import BaseModel

from models.company import CompanyResearchQuery


class Lead(BaseModel):
    """A lead from the CRM."""

    # Raw data
    record: dict
    form: dict

    # Processed fields
    user: dict
    company: dict
    identifiers: dict

    @classmethod
    def from_crm(cls, record) -> "Lead":
        """Build a Lead from a CRM record."""
        form = json.loads(record.get("dfds_fullpayload", "{}"))

        # Extract user info
        userSegmentID = form.get("userSegmentID", {})
        phone_number = form.get("PhoneNumber", None)
        company_email = form.get("CompanyEmail", None)

        user = {
            "first_name": form.get("FirstName", "").strip(),
            "last_name": form.get("LastName", "").strip(),
        }
        user["full_name"] = f"{user['first_name']} {user['last_name']}".strip()

        # Extract company info
        company_city = record.get("address1_city", None) or record.get("address1_composite", None)
        company_country = record.get("address1_country", None)

        company = {
            "name": form.get("CompanyName"),
            "domain": company_email.split("@")[1] if company_email else None,
            "city": company_city,
            "country": company_country,
            "phone_number": phone_number,
        }
        print(company)

        # Extract identifiers
        identifiers = {
            "user_id": userSegmentID.get("UserId", None),
            "anonymous_id": userSegmentID.get("anonymousUserId", None),
            "email": company_email,
            "phone": phone_number,
        }

        return cls(
            record=record.to_dict() if hasattr(record, "to_dict") else dict(record),
            form=form,
            user=user,
            company=company,
            identifiers=identifiers,
        )

    @property
    def company_research_query(self) -> CompanyResearchQuery:
        """Build a company research query from this lead."""
        return CompanyResearchQuery(
            name=self.company.get("name"),
            domain=self.company.get("domain"),
            city=self.company.get("city"),
            country=self.company.get("country"),
            representative=self.user.get("full_name"),
        )
