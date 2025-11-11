from pydantic import BaseModel, HttpUrl


class SearchHit(BaseModel):
    """A single search hit"""

    title: str
    url: HttpUrl
    snippet: str | None = None
    position: int | None = None
    hostname: str
    path: str
    provider: str


class SearchResult(BaseModel):
    """A search result from Serper"""

    query: str
    success: bool = False
    hits: list[SearchHit] = []
    engine: str | None = None
    credits_used: int | None = None
    error: str | None = None
