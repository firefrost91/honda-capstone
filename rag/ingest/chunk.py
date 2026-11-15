"""Page-aware chunker that emits the existing ``document_chunks.jsonl`` schema.

Matches the handoff's conventions so new and old chunks are interchangeable:
``chunk_id = <source_id>__p<page:04d>__c<n:03d>`` (page 0000 for web pages),
<= 350 words per chunk with a short overlap, ``char_start``/``char_end`` into
the page text, ``content_sha256`` of the chunk text, and a ``locator`` /
``citation_url`` that point a reader at the exact page.
"""
from __future__ import annotations

import hashlib
import re

MAX_WORDS = 350
TARGET_WORDS = 220
OVERLAP_WORDS = 40

_SENT_END = re.compile(r"(?<=[.!?:;])\s+|\n{2,}")


def _units(text: str) -> list[tuple[int, int]]:
    """Sentence/paragraph spans (start, end) covering ``text``."""
    spans, pos = [], 0
    for m in _SENT_END.finditer(text):
        if m.start() > pos:
            spans.append((pos, m.start()))
        pos = m.end()
    if pos < len(text):
        spans.append((pos, len(text)))
    # a single "sentence" longer than MAX_WORDS (a table) is split on words
    out = []
    for a, b in spans:
        words = list(re.finditer(r"\S+", text[a:b]))
        if len(words) <= MAX_WORDS:
            out.append((a, b))
            continue
        for i in range(0, len(words), TARGET_WORDS):
            w = words[i:i + TARGET_WORDS]
            out.append((a + w[0].start(), a + w[-1].end()))
    return out


def _wc(text: str) -> int:
    return len(text.split())


def split_page(text: str) -> list[tuple[int, int]]:
    """Group sentence units into chunk spans of ~TARGET_WORDS, max MAX_WORDS."""
    units = _units(text)
    chunks: list[tuple[int, int]] = []
    i = 0
    while i < len(units):
        start = units[i][0]
        j, words = i, 0
        while j < len(units):
            w = _wc(text[units[j][0]:units[j][1]])
            if words and words + w > MAX_WORDS:
                break
            words += w
            j += 1
            if words >= TARGET_WORDS:
                break
        end = units[j - 1][1]
        chunks.append((start, end))
        if j >= len(units):
            break
        # step back for overlap, but always make progress
        back, k = 0, j
        while k - 1 > i and back < OVERLAP_WORDS:
            k -= 1
            back += _wc(text[units[k][0]:units[k][1]])
        i = max(k, i + 1)
    return chunks


def chunk_source(source: dict, pages: list[tuple[int | None, str]],
                 original_path: str = "") -> list[dict]:
    """Chunk every page of an extracted source into schema-compatible dicts."""
    sid = source["source_id"]
    url = source.get("source_url", "")
    rows = []
    seg = 0
    for page_number, page_text in pages:
        text = page_text or ""
        for n, (a, b) in enumerate(split_page(text), 1):
            body = text[a:b].strip()
            if not body:
                continue
            seg += 1
            is_pdf = page_number is not None
            rows.append({
                "chunk_id": f"{sid}__p{(page_number or 0):04d}__c{n:03d}",
                "source_id": sid,
                "title": source.get("title", sid),
                "text": body,
                "source_url": url,
                "citation_url": f"{url}#page={page_number}" if is_pdf else url,
                "page_number": page_number,
                "locator": f"PDF page {page_number}" if is_pdf else f"Web text segment {seg}",
                "organization": source.get("organization", ""),
                "theme": source.get("theme", ""),
                "related_project_ids": source.get("related_project_ids", []),
                "parent_source_id": source.get("parent_source_id"),
                "retrieved_at": source.get("retrieved_at", ""),
                "original_path": original_path,
                "caveats": list(source.get("caveats") or []),
                "word_count": _wc(body),
                "char_start": a,
                "char_end": b,
                "content_sha256": hashlib.sha256(body.encode()).hexdigest(),
            })
    return rows
