import asyncio
import random

import pycountry
import requests
from bs4 import BeautifulSoup
from langdetect import DetectorFactory, detect
from requests.structures import CaseInsensitiveDict

from common.logging import get_logger
from services.web_scraper.html_extractor import HtmlExtractor
from services.web_scraper.schemas import ScrapeResult, ScrapeStrategy

logger = get_logger(__name__)

DetectorFactory.seed = 0

CONNECT_TIMEOUT = 5.0
READ_TIMEOUT = 25.0
MAX_CHARS = 15_000

# User-Agents to rotate through (lower rejection)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6114.123 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
]


class WebScraperClient:
    """Web scraper with multiple extraction methods for robust content extraction.

    Example:
        scraper = WebScraperClient()
        result = scraper.scrape(request)
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9,*;q=0.5",
                "Connection": "keep-alive",
            }
        )
        self.extractor = HtmlExtractor()

    async def scrape(
        self, url: str, max_chars: int = MAX_CHARS, strategy: ScrapeStrategy = ScrapeStrategy.REQUESTS, **kwargs
    ) -> ScrapeResult:
        """Scrape with automatic strategy selection or explicit choice."""

        if strategy == ScrapeStrategy.PLAYWRIGHT:
            return await self._scrape_with_playwright(url, max_chars, **kwargs)

        result = await self._scrape_with_requests(url, max_chars, **kwargs)

        if not result.ok and strategy == ScrapeStrategy.AUTO:
            result = await self._scrape_with_playwright(url, max_chars, **kwargs)

        return result

    def _normalize_language_code(self, lang_str: str) -> str:
        return lang_str.split(";")[0].strip().split("-")[0]

    def detect_language_code_for_page(self, response_headers: CaseInsensitiveDict[str], soup: BeautifulSoup) -> str:
        # Detect from html lang attribute
        if soup.html and soup.html.get("lang"):
            return self._normalize_language_code(str(soup.html["lang"]))

        # Detect from http header
        content_lang = response_headers.get("Content-Language")
        if content_lang:
            try:
                return self._normalize_language_code(str(content_lang))
            except Exception:
                ...

        # Detect from HTML title
        title_tag = soup.find("title")
        if title_tag:
            title_text = title_tag.get_text(strip=True)
            if title_text:
                try:
                    return detect(title_text)
                except Exception as e:
                    logger.warning(f"Title language detection failed: {e}", exc_info=True)
                    ...

        # Detect from body text sample
        body = soup.body
        if body:
            sample_text = body.get_text(" ", strip=True)[:1000]
            if len(sample_text.split()) >= 20:
                try:
                    return detect(sample_text)
                except Exception as e:
                    logger.warning(f"Body language detection failed: {e}", exc_info=True)
                    ...

        # Fallback to English
        return "en"

    def get_language_name(self, language_code: str) -> str:
        language = pycountry.languages.get(alpha_2=language_code)
        return language.name if language else "English"

    async def _prepare_request(self, min_delay_s: float, max_delay_s: float) -> str:
        """Prepare for request: apply delay and select user agent."""
        delay = random.uniform(min_delay_s, max_delay_s)  # noqa: S311
        await asyncio.sleep(delay)
        user_agent = random.choice(USER_AGENTS)  # noqa: S311
        logger.debug(f"Delayed {delay:.2f}s, using User-Agent: {user_agent}")
        return user_agent

    def _parse_and_extract(
        self,
        html: str,
        headers: dict | CaseInsensitiveDict,
        final_url: str,
        status: int,
        content_type: str,
        max_chars: int,
        method_suffix: str = "",
    ) -> ScrapeResult:
        soup = BeautifulSoup(html, "html.parser")

        if not isinstance(headers, CaseInsensitiveDict):
            headers = CaseInsensitiveDict(headers)

        language_code = self.detect_language_code_for_page(headers, soup)
        language_name = self.get_language_name(language_code)

        title = None
        try:
            ttag = soup.find("title")
            if ttag:
                title = ttag.get_text(strip=True)
        except Exception:
            pass

        meta_desc = self.extractor.get_meta_description(soup)

        # Extract text using best available method
        method, text = self.extractor.extract(html, language_name, soup)
        if method_suffix:
            method = f"{method} {method_suffix}"

        chunks = self.extractor.chunk_text(text, max_chars)
        total_words = sum(len(c.split()) for c in chunks)

        return ScrapeResult(
            ok=True,
            final_url=final_url,
            status_code=status,
            content_type=content_type,
            method=method,
            title=title,
            meta_description=meta_desc,
            text=text,
            text_chunks=chunks,
            word_count=total_words,
            raw_html=html,
        )

    async def _scrape_with_playwright(
        self,
        url: str,
        max_chars: int,
        min_delay_s: float = 1.0,
        max_delay_s: float = 5.0,
    ) -> ScrapeResult:
        """Scrape a URL using Playwright for JavaScript-heavy sites."""
        from playwright.async_api import async_playwright

        user_agent = await self._prepare_request(min_delay_s, max_delay_s)

        try:
            logger.info(f"Playwright: Scraping {url}")
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(
                    user_agent=user_agent,
                    locale="en-US",
                )

                try:
                    response = await page.goto(url, wait_until="networkidle", timeout=45_000)
                    if response is None:
                        return ScrapeResult(ok=False, error="No response from page")

                    status = response.status
                    final_url = page.url
                    headers = response.headers
                    content_type = headers.get("content-type", "")

                    if status >= 400:
                        return ScrapeResult(
                            ok=False,
                            final_url=final_url,
                            status_code=status,
                            content_type=content_type,
                            error=f"HTTP error {status}",
                        )

                    html = await page.content()

                finally:
                    await browser.close()

        except Exception as e:
            logger.error(f"Playwright: Error for {url}: {e}", exc_info=True)
            return ScrapeResult(ok=False, error=str(e))

        if "html" not in content_type.lower():
            # Non-HTML content
            return ScrapeResult(
                ok=True,
                final_url=final_url,
                status_code=status,
                content_type=content_type,
                text_chunks=[],
                word_count=0,
                raw_html=html,
            )

        return self._parse_and_extract(html, headers, final_url, status, content_type, max_chars, "(playwright)")

    async def _scrape_with_requests(
        self,
        url: str,
        max_chars: int,
        min_delay_s: float = 1.0,
        max_delay_s: float = 5.0,
        allow_redirects: bool = True,
    ) -> ScrapeResult:
        """Scrape a URL and extract text content using multiple extraction methods."""

        user_agent = await self._prepare_request(min_delay_s, max_delay_s)
        self.session.headers.update({"User-Agent": user_agent})

        try:
            logger.info(f"Requests: Scraping {url}")
            # Run blocking requests call in thread pool to avoid blocking event loop
            response = await asyncio.to_thread(
                self.session.get,
                str(url),
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                allow_redirects=allow_redirects,
            )
        except requests.RequestException as e:
            return ScrapeResult(ok=False, error=str(e))

        content_type = response.headers.get("Content-Type", "")
        status = response.status_code
        final_url = response.url

        if status >= 400:
            return ScrapeResult(
                ok=False,
                final_url=final_url,
                status_code=status,
                content_type=content_type,
                error=f"HTTP error {status}",
            )

        if "html" not in content_type.lower():
            # Non-HTML (e.g. PDF, image) — we might decide to skip or handle specially
            return ScrapeResult(
                ok=True,
                final_url=final_url,
                status_code=status,
                content_type=content_type,
                text_chunks=[],
                word_count=0,
                raw_html=response.text,
            )

        html = response.text
        return self._parse_and_extract(html, response.headers, final_url, status, content_type, max_chars)
