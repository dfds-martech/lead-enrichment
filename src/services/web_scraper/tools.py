from agents import function_tool

from services.web_scraper.client import WebScraperClient
from services.web_scraper.schemas import ScrapeStrategy, WebScraperResponse


@function_tool
async def scrape_website(
    url: str,
    max_chars: int = 5_000,
    strategy: str = "auto",
    full_content: bool = False,
) -> WebScraperResponse:
    """
    Scrape a website and extract clean textual content for company research.

    This tool fetches web pages and extracts main readable content using
    multiple strategies (readability, jusText, fallback). Automatically handles
    JavaScript-heavy sites when needed.

    Args:
        url: The URL to scrape (must include protocol, e.g. "https://...").
        max_chars: Maximum characters to return (default: 5000 for quick analysis).
        strategy: Scraping strategy:
            - "requests" (fast, default)
            - "playwright" (for JavaScript-heavy sites)
            - "auto" (tries requests first, falls back to playwright on failure)
        full_content: If True, returns all available text. If False (default),
                     returns a formatted summary optimized for LLM analysis.

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
        scraper = WebScraperClient()

        # Map string strategy to enum
        strategy_map = {
            "requests": ScrapeStrategy.REQUESTS,
            "playwright": ScrapeStrategy.PLAYWRIGHT,
            "auto": ScrapeStrategy.AUTO,
        }
        scrape_strategy = strategy_map.get(strategy.lower(), ScrapeStrategy.AUTO)

        # Perform the scrape
        result = await scraper.scrape(
            url,
            max_chars=max_chars if full_content else 5_000,
            strategy=scrape_strategy,
        )

        # Convert to LLM-friendly format
        return WebScraperResponse.from_scrape_result(result, max_chars, full_content)

    except Exception as e:
        # Return error response in consistent format
        return WebScraperResponse(
            success=False,
            url=url,
            content="",
            error=f"Internal exception: {e!r}",
        )
