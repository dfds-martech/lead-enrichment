from typing import Any
from urllib.parse import urlsplit

import httpx

from common.config import config
from common.logging import get_logger
from services.serper_search.schemas import SearchHit, SearchResult

logger = get_logger(__name__)

USER_AGENT = "CompanyIntelBot/1.0 (contact: karsols@dfds.com)"
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RESULTS = 8


class WebSearchService:
    """
    Searches the web using Serper and returns structured results.

    Example:
        ws = WebSearchService()
        result = await ws.search("company name", max_results=4)
    """

    def __init__(self, base_url: str = config.SERPER_BASE_URL):
        self.base_url = base_url
        self.api_key = config.SERPER_API_KEY.get_secret_value()

    def _build_search_hit(self, item: dict[str, Any]) -> SearchHit | None:
        link = item.get("link")
        title = (item.get("title") or "").strip()
        if not link or not title:
            return None

        parts = urlsplit(link)
        try:
            return SearchHit(
                title=title,
                url=link,
                snippet=item.get("snippet"),
                position=item.get("position"),
                hostname=(parts.hostname or "").lower(),
                path=(parts.path or "").lower(),
                provider="serper",
            )
        except Exception as e:
            logger.warning(f"Could not build SearchHit for {link}: {e}")
            return None

    async def search(self, query: str, max_results: int = DEFAULT_MAX_RESULTS) -> SearchResult:
        if not self.api_key:
            return SearchResult(query=query, error="Missing SERPER_API_KEY")

        payload = {"q": query}

        # Create client
        logger.info(f"Searching for '{query}' with max_results {max_results}")
        async with httpx.AsyncClient(
            headers={
                "User-Agent": USER_AGENT,
                "Content-Type": "application/json",
                "X-API-KEY": self.api_key,
            },
            timeout=DEFAULT_TIMEOUT,
        ) as client:
            try:
                resp = await client.post(self.base_url, json=payload)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP {e.response.status_code}: {e}", exc_info=True)
                return SearchResult(
                    query=query,
                    error=f"HTTP {e.response.status_code}",
                )
            except httpx.RequestError as e:
                logger.error(f"Request failed: {e}", exc_info=True)
                return SearchResult(query=query, error=str(e))
            except ValueError as e:
                logger.error(f"JSON parse error: {e}", exc_info=True)
                return SearchResult(query=query, error="Invalid JSON in response")

        # Process response
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
