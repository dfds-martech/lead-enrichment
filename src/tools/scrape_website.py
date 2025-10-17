from agents import function_tool

from services.web_scrape_service import ScrapeRequest, ScrapeResult, WebScrapeService


@function_tool
def scrape_website(url: str, max_chars: int = 30000, debug: bool = False) -> ScrapeResult:
    """
    Scrape a website and extract clean textual content.

    This tool fetches the web page at `url` (following redirects),
    then attempts to extract the main readable content using
    multiple strategies (readability, jusText, fallback). It returns
    a `ScrapeResult` with structured info about title, description,
    text chunks, and metadata.

    Args:
        url (str): The URL to scrape (must include protocol, e.g. "https://...").
        max_chars (int, optional): Maximum characters per chunk. Defaults to 30,000.
        debug (bool, optional): If True, include raw_html in the result for debugging.

    Returns:
        ScrapeResult: A Pydantic model containing fields:
            ok (bool),
            final_url (HttpUrl | None),
            status_code (int | None),
            content_type (str | None),
            title (str | None),
            meta_description (str | None),
            text_chunks (List[str]),
            word_count (int),
            error (str | None),
            raw_html (str | None) — only populated if debug=True.
    """
    try:
        scraper = WebScrapeService()
        req = ScrapeRequest(url=url, max_chars=max_chars)
        res = scraper.scrape(req)
    except Exception as e:
        return ScrapeResult(
            ok=False,
            final_url=None,
            status_code=None,
            content_type=None,
            title=None,
            meta_description=None,
            text_chunks=[],
            word_count=0,
            error=f"Internal exception in scrape_website: {e!r}",
            raw_html=None,
        )

    # Optionally prune raw_html to reduce payload size when not debugging
    if not debug:
        res.raw_html = None

    return res
