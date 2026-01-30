from datetime import datetime

from pydantic import BaseModel, Field

from common.logging import get_logger

logger = get_logger(__name__)


class OrbisCompanyAddress(BaseModel):
    street1: str | None
    street2: str | None
    city: str | None
    state: str | None
    postal_code: str | None
    country_code: str | None  # ISO2 code
    websites: list[str] | None
    phone: str | None = None

    @staticmethod
    def from_dict(data: dict) -> "OrbisCompanyAddress":
        postal_code = (
            data.get("STANDARDIZED_POSTALCODE")
            or data.get("GLEIF_HEADQUARTERS_ADDRESS_POSTAL_CODE")
            or data.get("GLEIF_LEGAL_ADDRESS_POSTAL_CODE")
        )

        # Phone comes as an array from Orbis - extract first element
        phone_list = data.get("PHONE")
        phone = phone_list[0] if phone_list else None

        return OrbisCompanyAddress(
            street1=data.get("ADDRESS_LINE1"),
            street2=data.get("ADDRESS_LINE2"),
            city=data.get("CITY"),
            state=data.get("STATE"),
            postal_code=postal_code,
            country_code=data.get("COUNTRY_ISO_CODE"),
            websites=data.get("WEBSITE", []),
            phone=phone,
        )

    def __str__(self) -> str:
        parts = [
            self.street1,
            self.street2,
            " ".join(filter(None, [self.postal_code, self.city])),
            self.country_code,
        ]
        return ", ".join(filter(None, parts)) or "Address: N/A"


class OrbisCompanyFinancials(BaseModel):
    operating_revenue: float | None
    profit_before_tax: float | None
    profit_loss: float | None
    cash_flow: float | None
    total_assets: float | None
    shareholders_funds: float | None
    accounting_year: datetime | None
    credit_risk_rating: str | None  # Credit risk rating category
    credit_risk_rating_label: str | None  # Credit risk rating short label

    @staticmethod
    def from_dict(data: dict) -> "OrbisCompanyFinancials":
        year_str = data.get("YEAR_LAST_ACCOUNTS")
        year = None
        if year_str:
            try:
                year = datetime.fromisoformat(year_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                logger.warning(f"Financials: Failed to parse accounting year {year_str}")
                pass

        return OrbisCompanyFinancials(
            operating_revenue=data.get("OPRE_EUR"),
            profit_before_tax=data.get("PLBT_EUR"),
            profit_loss=data.get("PL_EUR"),
            cash_flow=data.get("CF_EUR"),
            total_assets=data.get("TOAS_EUR"),
            shareholders_funds=data.get("SHFD_EUR"),
            accounting_year=year,
            credit_risk_rating=data.get("FSPulse_CreditRiskRating"),
            credit_risk_rating_label=data.get("FSPulse_CreditRiskRating_SHORT"),
        )

    def has_data(self) -> bool:
        """Check if financial data is present."""
        return any(
            [
                self.operating_revenue is not None,
                self.profit_before_tax is not None,
                self.profit_loss is not None,
                self.cash_flow is not None,
                self.total_assets is not None,
                self.shareholders_funds is not None,
            ]
        )

    def __str__(self) -> str:
        if not self.has_data():
            return ""

        year_str = self.accounting_year.year if self.accounting_year else "N/A"
        return (
            f"Financials ({year_str}):\n"
            f"- Operating Revenue: {self._format_amount(self.operating_revenue)}\n"
            f"- Profit Before Tax: {self._format_amount(self.profit_before_tax)}\n"
            f"- Profit/Loss: {self._format_amount(self.profit_loss)}\n"
            f"- Cash Flow: {self._format_amount(self.cash_flow)}\n"
            f"- Total Assets: {self._format_amount(self.total_assets)}\n"
            f"- Shareholders' Funds: {self._format_amount(self.shareholders_funds)}"
        )

    @staticmethod
    def _format_amount(amount: float | None) -> str:
        if amount is None:
            return "N/A"
        if amount >= 1_000_000_000:
            return f"{amount / 1_000_000_000:.0f}B"
        if amount >= 1_000_000:
            return f"{amount / 1_000_000:.0f}M"
        if amount >= 1_000:
            return f"{amount / 1_000:.0f}K"
        return f"{amount:.2f}"


class OrbisCompanyDetails(BaseModel):
    bvd_id: str | None = Field(None, description="BvD ID of the company")
    orbis_id: str | None = Field(None, description="Orbis ID of the company")
    country_code: str | None = Field(
        None, description="Country code of the company"
    )  # For convenience (also part of address)
    national_id: list[dict] | None = Field(None, description="National ID of the company")
    name: str | None = Field(None, description="Name of the company")
    address: OrbisCompanyAddress | None = Field(None, description="Address of the company")
    consolidation_code: str | None = Field(
        None, description="Consolidation code of the company"
    )  # C1 = Consolidated, C2 = Unconsolidated, etc.
    nace_code: str | None = Field(None, description="Industry classification (NACE2 - 4 digits)")
    employees: float | None = Field(None, description="Number of employees of the company")
    legal_status: str | None = Field(None, description="Legal status of the company")
    financials: OrbisCompanyFinancials | None = Field(None, description="Financials of the company")
    raw_data: dict | None = Field(None, description="Raw data from the company")

    @staticmethod
    def from_dict(data: dict) -> "OrbisCompanyDetails":
        return OrbisCompanyDetails(
            bvd_id=data.get("BvDID"),
            orbis_id=data.get("ORBISID"),
            country_code=data.get("COUNTRY_ISO_CODE"),
            national_id=[
                {"value": item.get("NATIONAL_ID"), "label": item.get("NATIONAL_ID_LABEL")}
                for item in data.get("NATIONAL_ID_FIXED_FORMAT") or []
            ],
            name=data.get("NAME"),
            address=OrbisCompanyAddress.from_dict(data),
            consolidation_code=data.get("CONSOLIDATION_CODE"),
            nace_code=data.get("NACE2_CORE_CODE"),
            employees=data.get("EMPL"),
            financials=OrbisCompanyFinancials.from_dict(data),
            legal_status=data.get("LEGAL_STATUS"),
            raw_data=data,
        )

    def __str__(self) -> str:
        financials_str = str(self.financials) if self.financials else ""

        return (
            f"Company Name: {self.name or 'N/A'} (BvD ID: {self.bvd_id})\n"
            f"Company Address: {self.address}\n"
            f"Employees: {int(self.employees) if self.employees else 'N/A'}\n"
            f"NACE Code: {self.nace_code or 'N/A'}\n"
            f"Consolidation: {self.consolidation_code or 'N/A'}\n"
            f"Legal Status: {self.legal_status or 'N/A'}\n"
            f"{financials_str}"
        )


class OrbisMatchCompanyOptions(BaseModel):
    """Options for Orbis company matching."""

    score_limit: float = 0.7
    selection_mode: str = "Normal"
    exclusion_flags: list[str] | None = None
    fields: list[str] | None = None


class OrbisCompanyMatch(BaseModel):
    bvd_id: str | None = None
    name: str | None = None
    matched_name: str | None = None
    matched_name_type: str | None = None
    address: str | None = None
    postcode: str | None = None
    city: str | None = None
    country: str | None = None
    state: str | None = None
    phone_or_fax: str | None = None
    email_or_website: str | None = None
    national_id: str | None = None
    national_id_label: str | None = None
    legal_form: str | None = None
    status: str | None = None
    hint: str | None = None
    score: float | None = None

    @staticmethod
    def from_dict(data: dict) -> "OrbisCompanyMatch":
        return OrbisCompanyMatch(
            bvd_id=data.get("BvDId"),
            name=data.get("Name"),
            matched_name=data.get("MatchedName"),
            matched_name_type=data.get("MatchedName_Type"),
            address=data.get("Address"),
            postcode=data.get("Postcode"),
            city=data.get("City"),
            country=data.get("Country"),
            state=data.get("State"),
            phone_or_fax=data.get("PhoneOrFax"),
            email_or_website=data.get("EmailOrWebsite"),
            national_id=data.get("National_Id"),
            national_id_label=data.get("NationalIdLabel"),
            legal_form=data.get("LegalForm"),
            status=data.get("Status"),
            hint=data.get("Hint"),
            score=data.get("Score"),
        )

    def __str__(self) -> str:
        return (
            f"Company Name: {self.name}\n"
            f"Address: {self.address}\n"
            f"City: {self.city}\n"
            f"Postcode: {self.postcode}\n"
            f"Country: {self.country}\n"
            f"National ID: {self.national_id}\n"
            f"State: {self.state}\n"
            f"Phone or Fax: {self.phone_or_fax}\n"
            f"Email or Website: {self.email_or_website}\n"
            f"Legal Form: {self.legal_form}\n"
            f"Status: {self.status}\n"
            f"Hint: {self.hint}\n"
            f"Score: {self.score}"
        )
