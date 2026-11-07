"""Text extraction for PDFs and HTML pages.

PDFs go through ``pdfplumber`` (best layout handling for planning documents),
falling back to ``pypdf``. HTML goes through a small stdlib parser that keeps
headings, paragraphs, list items and table cells, and drops navigation,
scripts and footers - the parts of a city web page that would otherwise end up
as boilerplate in every chunk.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

from ..quality import GARBLED_WORD_RATIO, garble_ratio

#: A page with fewer characters than this is treated as image-only.
EMPTY_PAGE_CHARS = 40


@dataclass
class Extracted:
    kind: str                                   # pdf | html | text
    pages: list[tuple[int | None, str]] = field(default_factory=list)
    n_empty_pages: int = 0
    error: str = ""
    #: pages still coming out per-glyph after the reading-order retry
    n_garbled_pages: int = 0

    @property
    def n_pages(self) -> int:
        return len(self.pages)

    @property
    def total_chars(self) -> int:
        return sum(len(t) for _, t in self.pages)


def _page_text(page) -> str:
    """One PDF page's text, retrying the reading order if it comes out garbled.

    pdfplumber sorts glyphs by position, which is right for ordinary layouts
    and wrong for a page that draws every glyph separately - there it
    interleaves columns, map labels and overlays into character soup.
    ``use_text_flow`` reads them in the order the page draws them instead.
    Only garbled pages are retried, and the retry has to actually be better,
    so a normal page is never reordered on a false positive.
    """
    text = page.extract_text() or ""
    if garble_ratio(text) < GARBLED_WORD_RATIO:
        return text
    try:
        alt = page.extract_text(use_text_flow=True) or ""
    except Exception:
        return text
    return alt if garble_ratio(alt) < garble_ratio(text) else text


def _pdf_pages(path: Path) -> list[str]:
    try:
        import pdfplumber
        with pdfplumber.open(str(path)) as pdf:
            return [_page_text(p) for p in pdf.pages]
    except Exception:
        from pypdf import PdfReader
        return [(p.extract_text() or "") for p in PdfReader(str(path)).pages]


class _MainText(HTMLParser):
    SKIP = {"script", "style", "noscript", "nav", "header", "footer", "form", "svg",
            "button", "iframe", "aside", "select"}
    BLOCK = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "td", "th", "tr", "div",
             "section", "article", "br", "blockquote", "dd", "dt", "caption", "figcaption"}
    VOID = {"br", "img", "meta", "link", "input", "hr", "area", "base", "col", "source",
            "wbr", "embed", "param", "track"}
    _SKIP_CLASS = re.compile(r"\b(cookie|breadcrumbs?|site-nav|navbar|menu|footer|skip-link)\b")

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, bool]] = []   # (tag, starts a skipped region)
        self.parts: list[str] = []
        self.title = ""
        self._in_title = False

    @property
    def skipping(self) -> bool:
        return any(flag for _, flag in self.stack)

    def handle_starttag(self, tag, attrs):
        if tag in self.BLOCK:
            self.parts.append("\n")
        if tag == "title":
            self._in_title = True
        if tag in self.VOID:
            return
        cls = " ".join(v or "" for k, v in attrs if k in ("class", "id", "role")).lower()
        self.stack.append((tag, tag in self.SKIP or bool(self._SKIP_CLASS.search(cls))
                           or cls == "navigation"))

    def handle_startendtag(self, tag, attrs):
        if tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag in self.BLOCK:
            self.parts.append("\n")
        # pop to the matching open tag; tolerate unclosed children
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if self._in_title:
            self.title += data
            return
        if not self.skipping:
            self.parts.append(data)


def html_text(markup: str) -> tuple[str, str]:
    """Return (title, main text) from an HTML document."""
    p = _MainText()
    p.feed(markup)
    text = "".join(p.parts)
    text = re.sub(r"[ \t\xa0]+", " ", text)
    lines = [l.strip() for l in text.split("\n")]
    # drop one-word navigation crumbs; keep headings and sentences
    lines = [l for l in lines if l and (len(l.split()) >= 3 or l.endswith(":"))]
    return p.title.strip(), "\n".join(lines)


def extract(path: Path, content_type: str = "") -> Extracted:
    suffix = path.suffix.lower()
    try:
        if suffix == ".pdf" or "pdf" in content_type:
            pages = _pdf_pages(path)
            out = Extracted("pdf", [(i + 1, t) for i, t in enumerate(pages)])
            out.n_empty_pages = sum(1 for t in pages if len(t.strip()) < EMPTY_PAGE_CHARS)
            out.n_garbled_pages = sum(1 for t in pages
                                      if garble_ratio(t) >= GARBLED_WORD_RATIO)
            return out
        raw = path.read_bytes().decode("utf-8", errors="replace")
        if suffix in (".html", ".htm") or "html" in content_type or "<html" in raw[:2000].lower():
            _, text = html_text(raw)
            return Extracted("html", [(None, text)], int(len(text) < EMPTY_PAGE_CHARS))
        return Extracted("text", [(None, raw)], int(len(raw.strip()) < EMPTY_PAGE_CHARS))
    except Exception as exc:
        return Extracted("unknown", error=f"{type(exc).__name__}: {exc}")


def content_status(ex: Extracted) -> tuple[str, list[str]]:
    """Map an extraction to the catalogue's content_status vocabulary."""
    if ex.error or not ex.pages or ex.total_chars < 200:
        return "failed", [f"Extraction produced no usable text ({ex.error or 'empty'})."]
    if ex.kind == "pdf" and ex.n_garbled_pages:
        share = ex.n_garbled_pages / max(ex.n_pages, 1)
        note = (f"{ex.n_garbled_pages} of {ex.n_pages} PDF pages still extract per glyph "
                "rather than per word after retrying the reading order.")
        # Character soup embeds like every other scrambled page, so indexing it
        # buys nothing and poisons the near-duplicate and cohesion metrics.
        if share > 0.3:
            return "extraction_unusable", [
                note + " The document is not indexed: its text cannot be read. It needs an "
                "OCR pass or a different extractor before it can be used."]
        return "ready_with_caveats", [
            note + " Those pages are dropped by rag.quality; the rest of the document is "
            "indexed normally."]
    if ex.kind == "pdf" and ex.n_empty_pages:
        share = ex.n_empty_pages / max(ex.n_pages, 1)
        if share > 0.6:
            return "reference_only_visual_content", [
                f"{ex.n_empty_pages} of {ex.n_pages} PDF pages have no extractable text; "
                "image-heavy document."]
        return "ready_with_caveats", [
            f"{ex.n_empty_pages} of {ex.n_pages} PDF pages contain little/no extractable text. "
            "Maps, figures, and table alignment require original-PDF review."]
    return "ready", []
