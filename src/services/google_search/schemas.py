from typing import Literal

from pydantic import BaseModel


class GoogleSearchRequest(BaseModel):
    """
    Parameters for a Google Search request.

    Potential additions include (omitted for now)
    - search_type: Optional[Literal["image"]] = None
    - safe: Literal["off", "active"] = "off"
    - file_type: Optional[str] = None
    - sort: Optional[str] = None
    """

    query: str
    num_results: int = 10
    start: int = 1
    language: str | None = None
    country: str | None = None
    date_restrict: str | None = None
    site_search: str | None = None
    site_search_filter: Literal["e", "i"] | None = None
    exact_terms: str | None = None
    exclude_terms: str | None = None

    def to_api_params(self, search_engine_id: str) -> dict:
        """
        Convert request to Google Search API parameters.

        Args:
            search_engine_id: Required custom search engine ID
        """

        # Required
        params = {
            "q": self.query.strip(),
            "cx": search_engine_id,
            "num": self.num_results,
            "start": self.start,
        }

        # Optional
        if self.language:
            params["lr"] = self.language
        if self.country:
            params["cr"] = self.country
        if self.date_restrict:
            params["dateRestrict"] = self.date_restrict
        if self.site_search:
            params["siteSearch"] = self.site_search
        if self.site_search_filter:
            params["siteSearchFilter"] = self.site_search_filter
        if self.exact_terms:
            params["exactTerms"] = self.exact_terms
        if self.exclude_terms:
            params["excludeTerms"] = self.exclude_terms

        return params

    def validate_request(self) -> None:
        if not self.query.strip():
            raise ValueError("Query cannot be empty")
        if self.num_results < 1 or self.num_results > 10:
            raise ValueError("num_results must be between 1 and 10")
        if self.start < 1 or self.start > 100:
            raise ValueError("start must be between 1 and 100")

    def __str__(self) -> str:
        fields = self.model_dump(exclude_none=True, exclude_defaults=True)
        params = ", ".join(f"{k}={v!r}" for k, v in fields.items())
        return f"GoogleSearchRequest({params})"


class GoogleSearchQueryMetadata(BaseModel):
    """Metadata about search query (current, next, or previous page)."""

    title: str
    total_results: str
    search_terms: str
    count: int
    start_index: int
    input_encoding: str
    output_encoding: str
    safe: str
    cx: str
    language: str | None = None

    @staticmethod
    def from_dict(data: dict) -> "GoogleSearchQueryMetadata":
        return GoogleSearchQueryMetadata(
            title=data.get("title", ""),
            total_results=data.get("totalResults", "0"),
            search_terms=data.get("searchTerms", ""),
            count=data.get("count", 0),
            start_index=data.get("startIndex", 1),
            input_encoding=data.get("inputEncoding", "utf8"),
            output_encoding=data.get("outputEncoding", "utf8"),
            safe=data.get("safe", "off"),
            cx=data.get("cx", ""),
            language=data.get("lr"),
        )


class GoogleSearchQueries(BaseModel):
    """Collection of query metadata for current, next, and previous pages."""

    request: GoogleSearchQueryMetadata | None = None
    next_page: GoogleSearchQueryMetadata | None = None
    previous_page: GoogleSearchQueryMetadata | None = None

    @staticmethod
    def from_dict(data: dict) -> "GoogleSearchQueries":
        return GoogleSearchQueries(
            request=GoogleSearchQueryMetadata.from_dict(data["request"][0]) if data.get("request") else None,
            next_page=GoogleSearchQueryMetadata.from_dict(data["nextPage"][0]) if data.get("nextPage") else None,
            previous_page=GoogleSearchQueryMetadata.from_dict(data["previousPage"][0])
            if data.get("previousPage")
            else None,
        )

    def has_next_page(self) -> bool:
        return self.next_page is not None

    def has_previous_page(self) -> bool:
        return self.previous_page is not None


class GoogleSearchResult(BaseModel):
    """Individual search result."""

    title: str
    link: str
    snippet: str
    display_link: str | None = None
    formatted_url: str | None = None
    html_title: str | None = None
    html_snippet: str | None = None
    cache_id: str | None = None

    # pagemap fields
    thumbnail: str | None = None  # URL to thumbnail image
    image: str | None = None  # URL to main image
    metatags: dict | None = None  # Open Graph, Twitter cards, etc.

    @staticmethod
    def from_dict(data: dict) -> "GoogleSearchResult":
        pagemap = data.get("pagemap", {})
        thumbnail = None
        image = None
        metatags = None

        if pagemap:
            if "cse_thumbnail" in pagemap and pagemap["cse_thumbnail"]:
                thumbnail = pagemap["cse_thumbnail"][0].get("src")

            if "cse_image" in pagemap and pagemap["cse_image"]:
                image = pagemap["cse_image"][0].get("src")

            if "metatags" in pagemap and pagemap["metatags"]:
                metatags = pagemap["metatags"][0]

        return GoogleSearchResult(
            title=data.get("title", ""),
            link=data.get("link", ""),
            snippet=data.get("snippet", ""),
            display_link=data.get("displayLink"),
            formatted_url=data.get("formattedUrl"),
            html_title=data.get("htmlTitle"),
            html_snippet=data.get("htmlSnippet"),
            cache_id=data.get("cacheId"),
            thumbnail=thumbnail,
            image=image,
            metatags=metatags,
        )

    def __str__(self) -> str:
        output = f"Title: {self.title}\n"
        output += f"Link: {self.link}\n"
        output += f"Snippet: {self.snippet}\n"

        # Open Graph description (if available and different from snippet)
        if self.metatags and "og:description" in self.metatags:
            og_desc = self.metatags["og:description"]
            if og_desc != self.snippet and len(og_desc) > len(self.snippet):
                output += f"Description: {og_desc}\n"

        return output


class GoogleSearchResponse(BaseModel):
    """Response from Google Search API."""

    kind: str
    url: dict
    queries: GoogleSearchQueries
    context: dict | None = None
    search_information: dict
    items: list[GoogleSearchResult]
    spelling: dict | None = None
    error: dict | None = None

    @staticmethod
    def from_dict(data: dict) -> "GoogleSearchResponse":
        items = [GoogleSearchResult.from_dict(item) for item in data.get("items", [])]
        queries = GoogleSearchQueries.from_dict(data.get("queries", {}))

        return GoogleSearchResponse(
            kind=data.get("kind", ""),
            url=data.get("url", {}),
            queries=queries,
            context=data.get("context"),
            search_information=data.get("searchInformation", {}),
            items=items,
            spelling=data.get("spelling"),
            error=data.get("error"),
        )

    def total_results(self) -> int:
        if self.queries.request:
            return int(self.queries.request.total_results)
        return 0

    def has_more_results(self) -> bool:
        return self.queries.has_next_page()

    def next_start_index(self) -> int | None:
        if self.queries.next_page:
            return self.queries.next_page.start_index
        return None

    def __str__(self) -> str:
        if self.error:
            return f"Search Error: {self.error}"

        if not self.items:
            return "No results found."

        total = self.total_results()
        search_terms = self.queries.request.search_terms if self.queries.request else "Unknown"

        output = f"Search results for: '{search_terms}'\n"
        output += f"Found {len(self.items)} results (Total available: {total:,})\n"
        output += "=" * 80 + "\n\n"

        # Individual results
        for i, item in enumerate(self.items, 1):
            output += f"# Result [{i}]:\n"
            output += f"{str(item)}\n"
            output += "\n"

        # Pagination info
        if self.has_more_results():
            output += f"More results available. Next page starts at index {self.next_start_index()}\n"

        return output
