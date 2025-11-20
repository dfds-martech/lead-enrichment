from enum import Enum

from pydantic import BaseModel


class ScrapeStrategy(Enum):
    REQUESTS = "requests"
    PLAYWRIGHT = "playwright"
    AUTO = "auto"  # requests first, fallback to playwright


class ScrapeResult(BaseModel):
    ok: bool
    final_url: str | None = None
    status_code: int | None = None
    content_type: str | None = None
    method: str | None = None
    title: str | None = None
    meta_description: str | None = None
    text: str | None = None
    text_chunks: list[str] = []
    word_count: int = 0
    error: str | None = None
    raw_html: str | None = None

    def to_markdown(self, max_chars: int = 5000) -> str:
        """Render a markdown summary combining title, meta, and first chunk(s)."""
        lines = []
        if self.title:
            lines.append(f"## {self.title}")
        if self.method:
            lines.append(f"**Method:** {self.method}")
        if self.final_url:
            lines.append(f"**URL:** {self.final_url}")
        if self.meta_description:
            lines.append(f"> {self.meta_description}")
        if self.text:
            lines.append(f"> {self.text}")
        # Append first few chunks (or truncated) for reading
        total = 0
        for chunk in self.text_chunks:
            if total >= max_chars:
                break
            piece = chunk[: (max_chars - total)]
            lines.append(piece)
            total += len(piece)
        if total < self.word_count:
            lines.append("\n_(… more text truncated …)_")
        return "\n\n".join(lines)

    def to_text(self, max_chars: int = 5000) -> str:
        """Plain-text fallback version."""
        return self.to_markdown(max_chars)


class WebScraperResponse(BaseModel):
    success: bool
    url: str | None = None
    title: str | None = None
    description: str | None = None
    content: str  # Single field, not array - easier for LLM
    word_count: int = 0
    method: str | None = None
    error: str | None = None

    @classmethod
    def from_scrape_result(cls, result: ScrapeResult, max_chars: int = 5000, full_content: bool = False):
        """Convert ScrapeResult to LLM-friendly format."""
        if not result.ok:
            return cls(
                success=False,
                url=result.final_url,
                error=result.error or "Unknown error",
                content="",
            )

        # Format content as single string
        if full_content:
            content = "\n\n".join(result.text_chunks)
        else:
            content = result.to_markdown(max_chars=max_chars)

        return cls(
            success=True,
            url=result.final_url,
            title=result.title,
            description=result.meta_description,
            content=content,
            word_count=result.word_count,
            method=result.method,
            error=None,
        )
