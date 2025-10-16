import json
from typing import Any

import requests
from pydantic import BaseModel, Field

from common.config import config, get_logger
from custom_agents.company_research import CompanyResearchProfile

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

        endpoint = f"{ORBIS_BASE}/match"

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

            response = self.session.get(endpoint, params={"QUERY": json.dumps(query)}, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Parse response items
            hits = [OrbisMatch.build_from_response(item) for item in data]

            logger.info(f"Found {len(hits)} matches")
            return OrbisMatchResult(hits=hits, total_hits=len(hits))

        except requests.RequestException as e:
            logger.error(f"Orbis API request failed: {e}", exc_info=True)
            raise Exception(f"API request failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in match_company: {e}", exc_info=True)
            raise

    def match_from_company_search_profile(
        self, profile: CompanyResearchProfile, score_limit: float = 0.7, exclusion_flags: list[str] | None = None
    ) -> OrbisMatchResult:
        """
        Match a company from a CompanyResearchProfile.

        Args:
            profile: Dictionary with company profile data
            score_limit: Minimum match score
            exclusion_flags: List of exclusion flags

        Returns:
            OrbisMatchResult with structured match data
        """
        return self.match_company(
            name=profile.get("name"),
            city=profile.get("city"),
            country=profile.get("country"),
            address=profile.get("address"),
            postcode=profile.get("zip_code"),
            national_id=profile.get("national_id"),
            email_or_website=profile.get("domain"),
            score_limit=score_limit,
            exclusion_flags=exclusion_flags,
        )
