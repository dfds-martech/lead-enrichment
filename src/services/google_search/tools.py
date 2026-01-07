# In tools.py
from typing import Literal

from agents import function_tool

from common.logging import get_logger
from services.google_search.client import GoogleSearchClient
from services.google_search.schemas import GoogleSearchRequest

logger = get_logger(__name__)


@function_tool
async def google_search(
    query: str,
    num_results: int = 10,
    start: int = 1,
    language: str | None = None,
    country: str | None = None,
    date_restrict: str | None = None,
    site_search: str | None = None,
    site_search_filter: Literal["e", "i"] | None = None,
    exact_terms: str | None = None,
    exclude_terms: str | None = None,
) -> str:
    """
    Search the web using Google Custom Search API.

    Use this tool to find specific information about companies, products, news, or any topic by searching the web. Returns the most relevant web pages with titles, URLs, and snippets.

    Args:
        query: Search query (e.g., "DFDS shipping company", "annual report 2024")
        num_results: Number of results to return (1-10, default 10)
        start: Starting index for pagination (1-100). Use 11 for page 2, 21 for page 3, etc.
        language: Language restriction (e.g., "lang_en", "lang_da", "lang_de", "lang_fr")
        country: Country restriction (e.g., "countryDK", "countryUS", "countryDE")
        date_restrict: Restrict by time period:
            - "d1" = past day
            - "w1" = past week
            - "m1" = past month
            - "y1" = past year
        site_search: Restrict to specific domain (e.g., "dfds.com", "wikipedia.org")
        site_search_filter: "i" = only include site_search domain, "e" = exclude it
        exact_terms: Phrase that must appear exactly in results
        exclude_terms: Terms to exclude from results (e.g., "cruise" to exclude cruises)

    Returns:
        Formatted search results as a string with titles, URLs, and web page snippets.
        Results are numbered according to Google rank.

    Examples:
        # Basic search
        google_search("DFDS Copenhagen")

        # Search in Danish from Denmark
        google_search("DFDS København", language="lang_da", country="countryDK")

        # Find recent news from past week
        google_search("DFDS financial news", date_restrict="w1")

        # Search only on company website
        google_search("financial report", site_search="dfds.com")

        # Get second page of results
        google_search("shipping and logistics industry", start=11)

        # Exclude certain terms
        google_search("DFDS ferry", exclude_terms="passenger")

    Note:
        - Maximum 100 results total (10 pages of 10 results)
        - Use pagination (start parameter) to get more results
        - Language codes: lang_en (English), lang_da (Danish), lang_de (German), etc.
        - Country codes: countryDK (Denmark), countryUS (USA), countryDE (Germany), etc.
    """
    logger.info(f"Google search tool called with query: {query}")
    try:
        request = GoogleSearchRequest(
            query=query,
            num_results=num_results,
            start=start,
            language=language,
            country=country,
            date_restrict=date_restrict,
            site_search=site_search,
            site_search_filter=site_search_filter,
            exact_terms=exact_terms,
            exclude_terms=exclude_terms,
        )

        request.validate_request()

        client = GoogleSearchClient()
        response = client.search(request)

        return str(response)

    except ValueError as e:
        logger.error(f"Validation error in google_search: {e}")
        return f"Error: {str(e)}"
    except Exception as e:
        logger.error(f"Error in google_search: {e}", exc_info=True)
        return f"Search failed: {str(e)}"
