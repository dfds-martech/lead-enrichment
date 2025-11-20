import logging
import re

import justext
from bs4 import BeautifulSoup
from readability import Document

logger = logging.getLogger(__name__)

REMOVE_TAGS = ["script", "style", "noscript", "iframe", "footer", "header", "nav", "svg", "canvas"]


class HtmlExtractor:
    """Extracts text content and metadata from HTML using multiple strategies."""

    def extract(self, html: str, language_name: str = "English", soup: BeautifulSoup | None = None) -> tuple[str, str]:
        """Extract text using best available method.

        Args:
            html: Raw HTML string
            language_name: Language name for justext (e.g., "English", "Danish")
            soup: Pre-parsed BeautifulSoup object (optional, will parse if not provided)

        Returns:
            Tuple of (method_name, extracted_text)
        """
        logger.info(f"Extracting text from HTML with language: {language_name}")

        if not soup:
            soup = BeautifulSoup(html, "html.parser")

        text_read = self.extract_with_readability(html)
        text_just = self.extract_with_justext(html, language_name)
        text_fall = self.extract_fallback(html, soup)

        candidates = []
        if text_read:
            score = self._score_extraction("readability", text_read)
            if score > 0:
                candidates.append(("readability", text_read, score))

        if text_just:
            score = self._score_extraction("justext", text_just)
            if score > 0:
                candidates.append(("justext", text_just, score))

        if text_fall:
            score = self._score_extraction("fallback", text_fall)
            if score > 0:
                candidates.append(("fallback", text_fall, score))

        if not candidates:
            # All extractions were too poor, return fallback anyway
            logger.warning("All extractions below quality threshold, using fallback")
            return "fallback", text_fall if text_fall else ""

        # Pick highest scoring extraction
        method, text, score = max(candidates, key=lambda x: x[2])

        word_count = len(text.split())
        logger.info(f"Selected {method} extraction: {word_count} words, score={score:.1f}")

        return method, text

    def extract_with_readability(self, html: str) -> str | None:
        """Use 'readability' library to extract main content HTML, then get textual text."""
        if Document is None:
            return None

        try:
            doc = Document(html)
            summary_html = doc.summary()
            soup = BeautifulSoup(summary_html, "html.parser")

            # Remove irrelevant tags
            for tag in soup(REMOVE_TAGS):
                tag.decompose()

            # Collect content preserving structure
            paragraphs = []
            for elem in soup.find_all(["p", "h1", "h2", "h3", "h4", "h5", "li"]):
                text = elem.get_text(" ", strip=True)
                if not text:
                    continue

                # Format headers to preserve hierarchy
                if elem.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                    level = int(elem.name[1])
                    paragraphs.append(f"{'#' * level} {text}")
                else:
                    paragraphs.append(text)

            if not paragraphs:
                # fallback to full text
                text = soup.get_text(" ", strip=True)
                return re.sub(r"\s+", " ", text).strip()

            result = "\n\n".join(paragraphs)
            return result

        except Exception:
            logger.warning("Extraction failed", exc_info=True)
            return None

    def extract_with_justext(self, html: str | bytes, language_name: str) -> str | None:
        """Use jusText to remove boilerplate. Returns joined paragraphs."""
        if justext is None:
            return None
        try:
            # justext expects bytes
            html_bytes = html.encode("utf-8", errors="ignore") if isinstance(html, str) else html

            # Get accepted justext stoplist for language, fallback to English if not supported
            try:
                stoplist = justext.get_stoplist(language_name)
            except KeyError:
                stoplist = justext.get_stoplist("English")

            paragraphs = justext.justext(html_bytes, stoplist)

            non_boilerplate = [p for p in paragraphs if not p.is_boilerplate]
            if not non_boilerplate:
                logger.warning(f"No non-boilerplate paragraphs found for language: {language_name}")
                return None

            texts = []
            for para in non_boilerplate:
                texts.append(para.text.strip())

            if not texts:
                logger.warning(f"No text found for language: {language_name}")
                return None
            return "\n\n".join(texts)

        except Exception:
            logger.error("Error extracting with justext", exc_info=True)
            return None

    def extract_fallback(self, html: str, soup: BeautifulSoup | None = None) -> str:
        """Fallback text extraction: strip tags and preserve paragraph structure."""
        if soup is None:
            soup = BeautifulSoup(html, "html.parser")

        for t in soup(REMOVE_TAGS):
            t.decompose()

        root = soup.body or soup

        # Walk through elements in order, preserving structure
        paragraphs = []
        for elem in root.find_all(["p", "h1", "h2", "h3", "h4", "h5", "li", "div"]):
            # Skip divs that are just containers (have block children)
            if elem.name == "div":
                # Only include if it has direct text content
                direct_text = "".join(str(t) for t in elem.find_all(text=True, recursive=False)).strip()
                if not direct_text:
                    continue

            text = elem.get_text(" ", strip=True)
            if text and len(text) > 3:  # Filter very short fragments
                paragraphs.append(text)

        if not paragraphs:
            # fallback to full text if no paragraphs found
            text = root.get_text(" ", strip=True)
            return re.sub(r"\s+", " ", text).strip()

        result = "\n\n".join(paragraphs)
        return re.sub(r"\n{3,}", "\n\n", result).strip()

    def get_meta_description(self, soup: BeautifulSoup) -> str | None:
        """Extract meta description from HTML."""
        tag = (
            soup.find("meta", attrs={"name": "description"})
            or soup.find("meta", attrs={"property": "og:description"})
            or soup.find("meta", attrs={"name": "og:description"})
        )
        if tag and tag.get("content"):
            return str(tag["content"]).strip()
        return None

    def chunk_text(self, text: str, max_chars: int, overlap: int = 200) -> list[str]:
        """Chunk text into overlapping segments by words, approximate max_chars"""
        if len(text) <= max_chars:
            return [text]

        words = text.split()
        chunks: list[str] = []

        current_words: list[str] = []
        current_len = 0

        for word in words:
            # +1 for the space
            word_len = len(word) + (1 if current_words else 0)
            if current_len + word_len > max_chars and current_words:
                # add current chunk
                chunks.append(" ".join(current_words))

                # new chunk with overlap
                if overlap > 0:
                    # take trailing words from previous chunk as overlap
                    overlap_words = current_words[-overlap:]
                    current_words = overlap_words + [word]
                    current_len = sum(len(w) + 1 for w in current_words) - 1
                else:
                    current_words = [word]
                    current_len = len(word)
            else:
                current_words.append(word)
                current_len += word_len

        if current_words:
            chunks.append(" ".join(current_words))

        return chunks

    def _score_extraction(self, method: str, text: str) -> float:
        """Score an extraction based on heuristics."""
        if not text or len(text.strip()) < 50:
            return 0.0

        words = text.split()
        word_count = len(words)

        # Base score: word count
        score = word_count

        # Method preference multipliers (readability > justext > fallback)
        method_multipliers = {
            "readability": 1.3,
            "justext": 1.1,
            "fallback": 1.0,
        }

        score *= method_multipliers.get(method, 1.0)

        # Penalize short or long
        if word_count < 30:
            score *= 0.5
        elif word_count > 10000:
            score *= 0.9

        # Structure bonus (has headings/paragraphs)
        if "\n\n" in text and any(marker in text for marker in ["\n", ". ", "? ", "! "]):
            score *= 1.1

        return score
