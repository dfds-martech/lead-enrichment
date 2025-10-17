import json
from typing import Any

import requests
from pydantic import BaseModel, Field

from common.config import config, get_logger
from custom_agents.company_research import CompanyResearchResult

logger = get_logger(__name__)

ORBIS_BASE = "https://api.bvdinfo.com/v1/orbis/companies"

# Most useful fields for company matching
DEFAULT_MATCH_FIELDS = [
    "Match.BvDId",
    "Match.Name",
    "Match.MatchedName",
    "Match.MatchedName_Type",
    "Match.Address",
    "Match.Postcode",
    "Match.City",
    "Match.Country",
    "Match.State",
    "Match.PhoneOrFax",
    "Match.EmailOrWebsite",
    "Match.National_Id",
    "Match.NationalIdLabel",
    "Match.LegalForm",
    "Match.Status",
    "Match.Hint",
    "Match.Score",
]


COMMON_EXCLUSION_FLAGS = ["ExcludeInactive", "ExcludeBranchLocations", "ExcludeHistorical", "ExcludePreviousNames"]


class OrbisMatch(BaseModel):
    """A single match hit from Orbis."""

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

    @classmethod
    def build_from_response(cls, item: dict[str, Any]) -> "OrbisMatch":
        """Build OrbisMatch from API response item."""
        return cls(
            bvd_id=item.get("BvDId"),
            name=item.get("Name"),
            matched_name=item.get("MatchedName"),
            matched_name_type=item.get("MatchedName_Type"),
            address=item.get("Address"),
            postcode=item.get("Postcode"),
            city=item.get("City"),
            country=item.get("Country"),
            state=item.get("State"),
            phone_or_fax=item.get("PhoneOrFax"),
            email_or_website=item.get("EmailOrWebsite"),
            national_id=item.get("National_Id"),
            national_id_label=item.get("NationalIdLabel"),
            legal_form=item.get("LegalForm"),
            status=item.get("Status"),
            hint=item.get("Hint"),
            score=item.get("Score"),
        )


class OrbisMatchResult(BaseModel):
    """Result from Orbis match API with filtering capabilities."""

    hits: list[OrbisMatch] = Field(default_factory=list)
    total_hits: int = 0

    def filter_by_score(self, min_score: float) -> "OrbisMatchResult":
        filtered_hits = [hit for hit in self.hits if (hit.score or 0) >= min_score]
        return OrbisMatchResult(hits=filtered_hits, total_hits=len(filtered_hits))

    def filter_by_hint(self, hint: str) -> "OrbisMatchResult":
        filtered_hits = [hit for hit in self.hits if hit.hint == hint]
        return OrbisMatchResult(hits=filtered_hits, total_hits=len(filtered_hits))

    def filter_by_country(self, country: str) -> "OrbisMatchResult":
        filtered_hits = [hit for hit in self.hits if hit.country == country]
        return OrbisMatchResult(hits=filtered_hits, total_hits=len(filtered_hits))

    def filter_by_status(self, status: str) -> "OrbisMatchResult":
        filtered_hits = [hit for hit in self.hits if hit.status == status]
        return OrbisMatchResult(hits=filtered_hits, total_hits=len(filtered_hits))

    def best_match(self) -> OrbisMatch | None:
        if not self.hits:
            return None
        return max(self.hits, key=lambda x: x.score or 0)


class OrbisCompanyDetails(BaseModel):
    """Detailed company information from Orbis data endpoint."""

    bvd_id: str
    name: str | None = None
    consolidation_code: str | None = None
    country_iso_code: str | None = None
    nace2_core_code: str | None = None
    employees: int | None = None
    operating_revenue: float | None = None
    year_last_accounts: str | None = None
    legal_status: str | None = None

    @classmethod
    def build_from_response(cls, bvd_id: str, item: dict[str, Any]) -> "OrbisCompanyDetails":
        """Build OrbisCompanyDetails from API response item."""
        return cls(
            bvd_id=bvd_id,
            name=item.get("NAME"),
            consolidation_code=item.get("CONSOLIDATION_CODE"),
            country_iso_code=item.get("COUNTRY_ISO_CODE"),
            nace2_core_code=item.get("NACE2_CORE_CODE"),
            employees=item.get("EMPL"),
            operating_revenue=item.get("OPRE"),
            year_last_accounts=item.get("YEAR_LAST_ACCOUNTS"),
            legal_status=item.get("LEGAL_STATUS"),
        )


class OrbisService:
    """Service for interacting with Orbis API."""

    def __init__(
        self,
    ):
        self.api_key = config.orbis_api_key
        self.session = requests.Session()
        self.session.headers.update({"ApiToken": self.api_key, "Accept": "application/json"})

    def match_company(
        self,
        name: str | None = None,
        city: str | None = None,
        country: str | None = None,
        address: str | None = None,
        postcode: str | None = None,
        national_id: str | None = None,
        email_or_website: str | None = None,
        phone_or_fax: str | None = None,
        ticker: str | None = None,
        isin: str | None = None,
        score_limit: float = 0.7,
        selection_mode: str = "Normal",
        exclusion_flags: list[str] | None = None,
        select_fields: list[str] | None = None,
    ) -> OrbisMatchResult:
        """
        Match a company using Orbis API.

        Returns:
            OrbisMatchResult with structured match data and filtering capabilities
        """

        # Build criteria - only include non-None values
        criteria = {}
        if name:
            criteria["Name"] = name
        if city:
            criteria["City"] = city
        if country:
            criteria["Country"] = country
        if address:
            criteria["Address"] = address
        if postcode:
            criteria["PostCode"] = postcode
        if national_id:
            criteria["NationalId"] = national_id
        if email_or_website:
            criteria["EMailOrWebsite"] = email_or_website
        if phone_or_fax:
            criteria["PhoneOrFax"] = phone_or_fax
        if ticker:
            criteria["Ticker"] = ticker
        if isin:
            criteria["Isin"] = isin

        if not criteria:
            raise ValueError("At least one search criterion must be provided")

        # Build options
        options = {"ScoreLimit": score_limit, "SelectionMode": selection_mode}

        if exclusion_flags:
            options["ExclusionFlags"] = exclusion_flags

        # Build query
        query = {"MATCH": {"Criteria": criteria, "Options": options}, "SELECT": select_fields or DEFAULT_MATCH_FIELDS}

        try:
            logger.info(f"Matching company with criteria: {criteria}")

            response = self.session.get(f"{ORBIS_BASE}/match", params={"QUERY": json.dumps(query)}, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Parse response items
            hits = [OrbisMatch.build_from_response(item) for item in data]

            logger.info(f"Found {len(hits)} matches")
            return OrbisMatchResult(hits=hits, total_hits=len(hits))

        except requests.RequestException as e:
            logger.error(f"Orbis API request failed: {e}", exc_info=True)
            raise Exception(f"API request failed: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error in match_company: {e}", exc_info=True)
            raise

    def match_from_company_search_result(
        self, result: CompanyResearchResult, score_limit: float = 0.7, exclusion_flags: list[str] | None = None
    ) -> OrbisMatchResult:
        """
        Match a company from a CompanyResearchResult.

        Args:
            result: Dictionary with company reserach result data
            score_limit: Minimum match score
            exclusion_flags: List of exclusion flags

        Returns:
            OrbisMatchResult with structured match data
        """
        return self.match_company(
            name=result.name,
            city=result.city,
            country=result.country,
            address=result.address,
            postcode=result.zip_code,
            national_id=result.national_id,
            email_or_website=result.domain,
            score_limit=score_limit,
            exclusion_flags=exclusion_flags,
        )

    def get_company_details(self, bvd_id: str, fields: list[str] | None = None) -> OrbisCompanyDetails | None:
        """
        Get detailed company information using BvDID.

        Args:
            bvd_id: The BvD identifier for the company
            fields: Optional list of fields to select. Defaults to standard fields.

        Returns:
            OrbisCompanyDetails object with company information, or None if not found
        """

        default_fields = [
            "NAME",
            "CONSOLIDATION_CODE",
            "COUNTRY_ISO_CODE",
            "NACE2_CORE_CODE",
            "EMPL",
            "OPRE",
            "YEAR_LAST_ACCOUNTS",
            "LEGAL_STATUS",
        ]

        query_payload = {
            "QUERY": {
                "WHERE": [{"BvDID": [bvd_id]}],
                "SELECT": fields or default_fields,
            }
        }

        try:
            logger.info(f"Fetching company details for BvD ID: {bvd_id}")

            response = self.session.post(f"{ORBIS_BASE}/data", json=query_payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            if not data.get("Data"):
                logger.warning(f"No data found for BvD ID: {bvd_id}")
                return None

            if len(data["Data"]) > 1:
                logger.warning(f"Multiple companies found for BvD ID: {bvd_id}")

            company_data = data["Data"][0]
            print(company_data)
            details = OrbisCompanyDetails.build_from_response(bvd_id, company_data)

            logger.info(f"Successfully fetched details for {details.name}")
            return details

        except requests.RequestException as e:
            logger.error(f"Orbis API request failed for BvD ID {bvd_id}: {e}", exc_info=True)
            raise Exception(f"API request failed: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error in get_company_details: {e}", exc_info=True)
            raise
