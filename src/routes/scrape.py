"""Scrape a website endpoints."""

from fastapi import APIRouter, HTTPException

from common.logging import get_logger
from services.web_scraper.client import WebScraperClient
from services.web_scraper.schemas import ScrapeStrategy, WebScraperResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["scrape"])


@router.post("/scrape-website", response_model=WebScraperResponse)
async def scrape_website_endpoint(url: str):
    """
    Scrape a website and extract clean textual content for company research.

    This endpoint uses the WebScraperClient to scrape a website and extract clean textual content for company research.

    Args:
        url: The URL to scrape (must include protocol, e.g. "https://...").

    Returns:
        WebScraperResponse: Structured result with:
            - success (bool): Whether scraping succeeded
            - url (str | None): Final URL after redirects
            - title (str | None): Page title
            - description (str | None): Meta description
            - content (str): Main text content (formatted markdown or full text)
            - word_count (int): Total words extracted
            - method (str | None): Extraction method used
            - error (str | None): Error message if scraping failed
    """
    try:
        logger.debug(f"Scraping website: {url}")
        scraper = WebScraperClient()

        scrape_result = await scraper.scrape(url, strategy=ScrapeStrategy.PLAYWRIGHT)

        logger.info(f"Scraping completed\n: {scrape_result.model_dump_json(indent=2, exclude_none=True)}")

        return scrape_result.model_dump(exclude_none=True)

    except Exception as e:
        logger.error(f"Scraping request failed for {url}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}") from e
