from agents import function_tool

from common.logging import get_logger
from models.company import CompanyResearchCriteria
from services.orbis.client import OrbisClient
from services.orbis.schemas import OrbisCompanyMatch, OrbisMatchCompanyOptions

logger = get_logger(__name__)


@function_tool
def match_company(
    name: str,
    domain: str | None = None,
    city: str | None = None,
    country: str | None = None,
    address: str | None = None,
    postcode: str | None = None,
    national_id: str | None = None,
    phone: str | None = None,
    score_limit: float = 0.7,
) -> list[OrbisCompanyMatch]:
    """
    Search for company matches in the Orbis business database.

    This tool queries the Orbis API to find companies matching the provided criteria.
    It returns a list of potential matches with confidence scores and detailed information.

    Args:
        name (str): Company name (required). The more complete, the better.
        city (str, optional): City where the company is located.
        country (str, optional): Country where the company is located.
        address (str, optional): Full or partial address.
        postcode (str, optional): Postal/ZIP code.
        national_id (str, optional): Official national company ID (CVR, VAT, etc.).
        domain (str, optional): Company website domain.
        phone (str, optional): Company phone number.
        score_limit (float, optional): Minimum match score (0.0-1.0). Defaults to 0.7.

    Returns:
        OrbisMatchResult: Contains:
            - hits: List of OrbisMatch objects with company details and match scores
            - total_hits: Number of matches found

            Each OrbisMatch includes: bvd_id, name, address, city, country,
            national_id, domain, phone, score, and more.

    Tips:
        - national_id is the most reliable for exact matches
        - domain helps disambiguate companies with similar names
        - Combine name + city + country for better results
        - Higher score_limit (e.g., 0.9) returns only high-confidence matches
        - Lower score_limit (e.g., 0.6) returns more potential matches
    """
    logger.info(
        f"Orbis match company tool called with name: {name}, domain: {domain}, city: {city}, country: {country}, address: {address}, postcode: {postcode}, national_id: {national_id}, phone: {phone}, score_limit: {score_limit}"
    )
    try:
        orbis_client = OrbisClient()
        criteria = CompanyResearchCriteria(
            name=name,
            city=city,
            country=country,
            address=address,
            postcode=postcode,
            national_id=national_id,
            email_or_website=domain,
            phone_or_fax=phone,
        )
        options = OrbisMatchCompanyOptions(score_limit=score_limit)
        return orbis_client.company_match(criteria=criteria, options=options)

    except Exception as e:
        logger.error(f"Error in match_company tool: {e}", exc_info=True)
        # Return empty result on error
        return []
