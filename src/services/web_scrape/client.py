import re
import time

import justext
import requests
from bs4 import BeautifulSoup
from readability import Document

from common.logging import get_logger
from services.web_scrape.schemas import ScrapeResult

logger = get_logger(__name__)

USER_AGENT = "CompanyIntelBot/1.0 (contact: karsols@dfds.com)"
CONNECT_TIMEOUT = 5.0
READ_TIMEOUT = 25.0


class WebScrapeService:
    """Web scraper with multiple extraction methods for robust content extraction.

    Example:
        scraper = WebsiteScraper()
        result = scraper.scrape(request)
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept": "text/html;q=0.9,*/*;q=0.8"})

    def _get_meta_description(self, soup: BeautifulSoup) -> str | None:
        tag = (
            soup.find("meta", attrs={"name": "description"})
            or soup.find("meta", attrs={"property": "og:description"})
            or soup.find("meta", attrs={"name": "og:description"})
        )
        if tag and tag.get("content"):
            return tag["content"].strip()
        return None

    def _extract_with_readability(self, html: str) -> str | None:
        """Use python-readability (arc90 port) to extract main content HTML, then get textual text."""
        if Document is None:
            return None
        try:
            doc = Document(html)
            summary_html = doc.summary()
            # Optionally, you might also use doc.title()
            soup = BeautifulSoup(summary_html, "html.parser")
            # Remove irrelevant tags
            for tag in soup(["script", "style", "noscript", "iframe", "footer", "header", "nav"]):
                tag.decompose()
            txt = soup.get_text(" ", strip=True)
            return re.sub(r"\s+", " ", txt).strip()
        except Exception:
            # Could log the error
            return None

    def _extract_with_justext(self, html: str | bytes, lang: str = "English") -> str | None:
        """Use jusText to remove boilerplate. Returns joined paragraphs."""
        if justext is None:
            return None
        try:
            # justext expects bytes
            if isinstance(html, str):
                html_bytes = html.encode("utf-8", errors="ignore")
            else:
                html_bytes = html
            # choose stoplist based on language; you may want detection logic
            paragraphs = justext.justext(html_bytes, justext.get_stoplist(lang))
            texts = []
            for para in paragraphs:
                if not para.is_boilerplate:
                    texts.append(para.text.strip())
            if texts:
                return " ".join(texts)
            else:
                return None
        except Exception:
            logger.error("Error extracting with justext", exc_info=True)
            return None

    def _fallback_clean(self, html: str) -> str:
        """Fallback simpler text extraction: strip tags, use body / root."""
        soup = BeautifulSoup(html, "html.parser")
        for t in soup(["script", "style", "noscript", "iframe", "svg", "canvas"]):
            t.decompose()

        # Use body directly to avoid missing content outside semantic tags
        root = soup.body or soup
        text = root.get_text(" ", strip=True) if root else soup.get_text(" ", strip=True)
        return re.sub(r"\s+", " ", text).strip()

    def _chunk_text(self, text: str, max_chars: int, overlap: int = 200) -> list[str]:
        """Chunk into overlapping pieces aligned at natural breaks (paragraphs) if possible."""
        if len(text) <= max_chars:
            return [text]
        # try chunking by paragraphs
        paras = text.split("\n")
        chunks = []
        current = ""
        for para in paras:
            if len(current) + len(para) + 1 <= max_chars:
                current = current + "\n" + para if current else para
            else:
                # commit current
                chunks.append(current)
                # start new
                current = para
        if current:
            chunks.append(current)

        # if some chunks are still too big (rare), fallback to sliding window
        out = []
        for chunk in chunks:
            if len(chunk) <= max_chars:
                out.append(chunk)
            else:
                # slide-window fallback
                start = 0
                while start < len(chunk):
                    end = min(start + max_chars, len(chunk))
                    out.append(chunk[start:end])
                    if end == len(chunk):
                        break
                    start = end - overlap
        return out

    def scrape(
        self, url: str, max_chars: int = 30_000, sleep_ms: int = 200, allow_redirects: bool = True
    ) -> ScrapeResult:
        """Scrape a URL and extract text content using multiple extraction methods."""
        if sleep_ms:
            time.sleep(sleep_ms / 1000.0)

        try:
            response = self.session.get(
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
        soup = BeautifulSoup(html, "html.parser")
        title = None
        try:
            ttag = soup.find("title")
            if ttag:
                title = ttag.get_text(strip=True)
        except Exception:
            title = None

        meta_desc = self._get_meta_description(soup)

        # Try all extraction methods and pick the best one
        candidates = []

        # 1. readability
        text_read = self._extract_with_readability(html)
        if text_read:
            candidates.append(("readability", text_read))

        # 2. justext
        text_just = self._extract_with_justext(html)
        if text_just:
            candidates.append(("justext", text_just))

        # 3. fallback
        text_fall = self._fallback_clean(html)
        if text_fall:
            candidates.append(("fallback", text_fall))

        # Pick the longest extraction
        if candidates:
            method, text = max(candidates, key=lambda x: len(x[1]))
            logger.info(f"Using {method} extraction with {len(text)} chars")
        else:
            text = ""

        # Chunk
        chunks = self._chunk_text(text, max_chars)

        total_words = sum(len(c.split()) for c in chunks)

        return ScrapeResult(
            ok=True,
            final_url=final_url,
            status_code=status,
            content_type=content_type,
            title=title,
            meta_description=meta_desc,
            text_chunks=chunks,
            word_count=total_words,
            raw_html=html,
        )
