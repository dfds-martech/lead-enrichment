import json
from datetime import datetime
from typing import NoReturn

import requests

from common.config import config
from common.logging import get_logger
from models.company import CompanyResearchCriteria
from services.orbis.schemas import (
    OrbisCompanyDetails,
    OrbisCompanyMatch,
    OrbisMatchCompanyOptions,
)

logger = get_logger(__name__)

DEFAULT_TIMEOUT = 30

DEFAULT_FIELDS = [
    "ORBISID",
    "BvDID",
    {
        "NATIONAL_ID_FIXED_FORMAT": {
            "SELECT": [
                {"NATIONAL_ID": {"AS": "NATIONAL_ID"}},
                {"NATIONAL_ID_LABEL": {"AS": "NATIONAL_ID_LABEL"}},
            ]
        }
    },
    "NAME",
    "ADDRESS_LINE1",
    "CITY",
    "STATE",
    "GLEIF_HEADQUARTERS_ADDRESS_POSTAL_CODE",
    "GLEIF_LEGAL_ADDRESS_POSTAL_CODE",
    "STANDARDIZED_POSTALCODE",
    "PHONE",
    "WEBSITE",
    "CONSOLIDATION_CODE",
    "COUNTRY_ISO_CODE",
    "NACE2_CORE_CODE",
]

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


class OrbisClient:
    def __init__(self) -> None:
        self.base_url = config.ORBIS_BASE_URL
        self.api_key = config.ORBIS_API_KEY.get_secret_value()
        self.session = requests.Session()
        self.session.headers.update({"ApiToken": self.api_key, "Accept": "application/json"})
        self._metadata: dict | None = None

    @property
    def metadata(self) -> dict:
        if not self._metadata:
            result = self._get_request("Companies/metadata/data/select")
            if isinstance(result, dict):
                self._metadata = result
            else:
                raise TypeError(f"Expected dict from metadata endpoint, got {type(result)}")
        return self._metadata

    def metadata_search(self, keyword: str) -> list[dict]:
        """
        Search metadata object for fields whose Label or Description contains the keyword
        Returns list of matching field metadata dictionaries.
        """
        keyword_lower = keyword.lower()
        matches: list[dict] = []

        # Metadata is a nested structure of 'Sections' with 'Fields'
        def search_fields(sections: list[dict]) -> None:
            for section in sections:
                for field in section.get("Fields", []):
                    label = field.get("Label", "").lower()
                    description = (field.get("Description") or "").lower()
                    if keyword_lower in label or keyword_lower in description:
                        matches.append(field)
                # Recurse into nested sections
                search_fields(section.get("Sections", []))

        search_fields(self.metadata.get("Sections", []))
        return matches

    def company_search(
        self,
        name: str | None = None,
        street: str | None = None,
        city: str | None = None,
        country: str | None = None,
        national_id: str | None = None,
        max_results: int = 10,
    ) -> list[OrbisCompanyDetails]:
        """
        Search for companies by name, street, city, country, and national_id.
        Returns only default company info fields (DEFAULT_FIELDS)
        """
        payload = self._build_company_search_payload(
            name=name, street=street, city=city, country=country, national_id=national_id
        )
        query = payload["QUERY"]["WHERE"]
        data = self._post_request("companies/data", payload)

        if not data.get("Data"):
            logger.debug(f"No results for query: {query}")
            return []

        results: list[OrbisCompanyDetails] = []
        for company_data in data["Data"][:max_results]:
            results.append(OrbisCompanyDetails.from_dict(company_data))

        return results

    def company_lookup(
        self, country_code: str, national_id: str, fields: list[str] | None = None
    ) -> OrbisCompanyDetails:
        """
        Look up single company by country_code and national_id.
        (The combination of "country_code" (iso2) and national_id (VAT) = Bvd ID)
        """
        return self.company_lookup_by_bvd(f"{country_code}{national_id}", fields)

    def company_lookup_by_bvd(self, bvd_id: str, fields: list[str] | None = None) -> OrbisCompanyDetails:
        """
        Lookup a company by BvD ID. (country_code + vat_number)
        """
        payload = self._build_company_lookup_payload(bvd_id, fields)
        data = self._post_request("companies/data", payload)

        if not data.get("Data"):
            logger.warning(f"No data for BvD ID: {bvd_id}")
            return OrbisCompanyDetails.from_dict({})

        if len(data["Data"]) > 1:
            logger.warning(f"Multiple companies for BvD ID: {bvd_id}")

        company_data = data["Data"][0]
        return OrbisCompanyDetails.from_dict(company_data)

    def company_match(
        self,
        criteria: CompanyResearchCriteria,
        options: OrbisMatchCompanyOptions | None = None,
    ) -> list[OrbisCompanyMatch]:
        """
        Match companies using Orbis' fuzzy matching API.

        Args:
            criteria: Search criteria (name, city, country, etc.)
            options: Match options (score_limit, selection_mode, etc.)

        Returns:
            List of matched companies ranked by confidence score
        """
        options = options or OrbisMatchCompanyOptions()
        query = self._build_company_match_query(criteria=criteria, options=options)
        params = {"QUERY": json.dumps(query)}
        data = self._get_request("companies/match", params)

        if not data:
            logger.debug(f"No matches found for: {criteria.name}")
            return []

        return [OrbisCompanyMatch.from_dict(item) for item in data]

    # Private

    def _build_company_search_payload(
        self,
        name: str | None = None,
        street: str | None = None,
        city: str | None = None,
        country: str | None = None,
        national_id: str | None = None,
    ) -> dict:
        """Build the search payload from search parameters."""
        query: list[dict] = []

        if name:
            query.append({"CompanyName": name})
        if street:
            query.append({"StreetAddress": street})
        if city:
            query.append({"City": city})
        if country:
            if len(country) == 2:
                query.append({"CountryCode": [country]})
            else:
                query.append({"CountryRegion": {"Text": country}})
        if national_id:
            query.append({"NationalId": national_id})

        if not query:
            raise ValueError("At least one search parameter must be provided")

        return {"QUERY": {"WHERE": query, "SELECT": DEFAULT_FIELDS}}

    def _build_company_lookup_payload(self, bvd_id: str, fields: list[str] | None = None) -> dict:
        """
        Payload for a company search request.
        Notes:
            - financials by codes
            - monetary_unit: 0 (actual), 3 (thousands), 6 (millions), 9 (billions), 12 (trillions)',
        """
        # latest_year = datetime.now().year - 1
        monetary_unit = 0

        financial_codes = ["OPRE", "PLBT", "PL", "CF", "TOAS", "SHFD"]
        financial_fields = [
            {
                code: {
                    # "IndexOrYear": latest_year, (optional - gets latest by default)
                    "Currency": "EUR",
                    "Unit": monetary_unit,
                    "As": f"{code}_EUR",
                }
            }
            for code in financial_codes
        ]

        default_fields = [
            *DEFAULT_FIELDS,
            "ADDRESS_LINE2",
            "EMPL",  # Employees
            "YEAR_LAST_ACCOUNTS",
            "LEGAL_STATUS",
            *financial_fields,
        ]

        payload = {
            "QUERY": {
                "WHERE": [{"BvDID": [bvd_id]}],
                "SELECT": fields or [*default_fields],
            }
        }

        return payload

    def _build_company_match_query(
        self,
        criteria: CompanyResearchCriteria,
        options: OrbisMatchCompanyOptions,
    ) -> dict:
        """Build the match query from criteria and options dataclasses."""

        criteria_dict = criteria.to_orbis_match_criteria()

        if not criteria_dict:
            raise ValueError("At least one search criterion must be given")

        options_dict = {
            "ScoreLimit": options.score_limit,
            "SelectionMode": options.selection_mode,
        }
        if options.exclusion_flags:
            options_dict["ExclusionFlags"] = options.exclusion_flags

        return {
            "MATCH": {"Criteria": criteria_dict, "Options": options_dict},
            "SELECT": options.fields or DEFAULT_MATCH_FIELDS,
        }

    def _post_request(self, endpoint: str, payload: dict) -> dict:
        """Make a POST request to the API and return parsed JSON."""
        try:
            response = self.session.post(f"{self.base_url}/{endpoint}", json=payload, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            self._handle_http_error(e, endpoint)
        except requests.RequestException as e:
            raise Exception(f"Request failed: {str(e)}") from e

    def _get_request(self, endpoint: str, params: dict | None = None) -> dict | list[dict]:
        """Make a GET request to the API and return parsed JSON."""
        try:
            url = f"{self.base_url}/{endpoint}"
            response = self.session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            self._handle_http_error(e, endpoint)
        except requests.RequestException as e:
            raise Exception(f"Request failed: {str(e)}") from e

    def _handle_http_error(self, e: requests.HTTPError, operation: str) -> NoReturn:
        try:
            error_detail = e.response.json()
        except Exception:
            error_detail = e.response.text
        raise Exception(f"failed {operation}, status: {e.response.status_code}: {error_detail}") from e
