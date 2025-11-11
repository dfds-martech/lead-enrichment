from pydantic import BaseModel


class ScrapeResult(BaseModel):
    ok: bool
    final_url: str | None = None
    status_code: int | None = None
    content_type: str | None = None
    title: str | None = None
    meta_description: str | None = None
    text_chunks: list[str] = []
    word_count: int = 0
    error: str | None = None
    raw_html: str | None = None

    def to_markdown(self, max_chars: int = 5000) -> str:
        """Render a markdown summary combining title, meta, and first chunk(s)."""
        lines = []
        if self.title:
            lines.append(f"## {self.title}")
        if self.final_url:
            lines.append(f"**URL:** {self.final_url}")
        if self.meta_description:
            lines.append(f"> {self.meta_description}")
        lines.append("")
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
