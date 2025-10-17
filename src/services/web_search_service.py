from typing import Any
from urllib.parse import urlsplit

import requests
from pydantic import BaseModel, HttpUrl

from common.config import config, get_logger

logger = get_logger(__name__)

SERPER_URL = "https://google.serper.dev/search"
USER_AGENT = "CompanyIntelBot/1.0 (contact: karsols@dfds.com)"


class SearchHit(BaseModel):
    title: str
    url: HttpUrl
    snippet: str | None = None
    position: int | None = None
    hostname: str
    path: str
    provider: str


class SearchResult(BaseModel):
    success: bool
    query: str
    hits: list[SearchHit]
    engine: str | None = None
    credits_used: int | None = None
    error: str | None = None


class WebSearchService:
    """Searches the web using Serper and returns structured results.

    Example:
        ws = WebSearchService()
        response = ws.search(query, max_results)
        return response
    """

    def __init__(self, api_key: str = None, base_url: str = SERPER_URL):
        self.api_key = api_key or config.serper_api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Content-Type": "application/json",
            }
        )

    def _build_search_hit(self, item: dict[str, Any]) -> SearchHit | None:
        link = item.get("link")
        title = (item.get("title") or "").strip()
        if not link or not title:
            return None
        parts = urlsplit(link)
        hostname = (parts.hostname or "").lower()
        path = parts.path or "/"
        try:
            return SearchHit(
                title=title,
                url=link,
                snippet=item.get("snippet"),
                position=item.get("position"),
                hostname=hostname,
                path=path,
                provider="serper",
            )
        except Exception as e:
            logger.warning(f"Could not build SearchHit for {link}: {e}")
            return None

    def search(self, query: str, max_results: int = 8) -> SearchResult:
        if not self.api_key:
            return SearchResult(
                success=False,
                query=query,
                hits=[],
                engine=None,
                credits_used=None,
                error="Missing SERPER_API_KEY",
            )
        payload = {"q": query}
        try:
            resp = self.session.post(self.base_url, json=payload, timeout=30, headers={"X-API-KEY": self.api_key})
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error(f"Search request failed: {e}", exc_info=True)
            return SearchResult(
                success=False,
                query=query,
                hits=[],
                engine=None,
                credits_used=None,
                error=str(e),
            )
        except ValueError as e:
            logger.error(f"JSON parse error in search response: {e}", exc_info=True)
            return SearchResult(
                success=False,
                query=query,
                hits=[],
                engine=None,
                credits_used=None,
                error="Invalid JSON in response",
            )

        organics = data.get("organic", [])[:max_results]
        seen = set()
        hits: list[SearchHit] = []
        for item in organics:
            h = self._build_search_hit(item)
            if h and str(h.url) not in seen:
                seen.add(str(h.url))
                hits.append(h)

        return SearchResult(
            success=True,
            query=data.get("searchParameters", {}).get("q", query),
            hits=hits,
            engine=data.get("engine"),
            credits_used=data.get("credits"),
            error=None,
        )
