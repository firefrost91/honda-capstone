"""Download a source document, with provenance.

stdlib only (``urllib``), so it honours ``HTTPS_PROXY`` and needs no extra
dependency. Every download records what a citation needs later: the URL that
actually answered, when, its content type and a sha256 of the bytes.
"""
from __future__ import annotations

import hashlib
import mimetypes
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

USER_AGENT = ("Mozilla/5.0 (compatible; columbus-safety-rag/1.0; "
              "research use; +https://github.com/firefrost91/honda-capstone)")

_EXT = {"application/pdf": ".pdf", "text/html": ".html", "application/xhtml+xml": ".html",
        "text/plain": ".txt", "application/json": ".json"}

#: Leading bytes of a real PDF. Content-Type is advisory - servers mislabel
#: both ways - so the magic number is what decides.
_PDF_MAGIC = b"%PDF-"


@dataclass
class FetchResult:
    source_id: str
    ok: bool
    path: Path | None = None
    sha256: str = ""
    content_type: str = ""
    resolved_url: str = ""
    retrieved_at: str = ""
    error: str = ""
    from_cache: bool = False


def _ext_for(content_type: str, url: str) -> str:
    ct = content_type.split(";")[0].strip().lower()
    if ct in _EXT:
        return _EXT[ct]
    guess = mimetypes.guess_extension(ct) if ct else None
    if guess:
        return guess
    suffix = Path(url.split("?")[0]).suffix.lower()
    return suffix if suffix in {".pdf", ".html", ".htm", ".txt"} else ".bin"


def wants_pdf(url: str, expected: str = "") -> bool:
    """Did we ask for a PDF? From the registry's hint, else the URL's suffix."""
    if expected:
        return expected.split("/")[-1].strip().lower() == "pdf"
    return Path(url.split("?")[0]).suffix.lower() == ".pdf"


def content_mismatch(url: str, content_type: str, data: bytes, expected: str = "") -> str:
    """Why these bytes are not what the URL promised, or "" if they are.

    A site that has reorganised its uploads often answers a moved PDF with
    HTTP 200 and its own home page rather than a 404. Those bytes are a
    perfectly valid HTML document: ``extract`` pulls the navigation copy out
    of it, ``content_status`` calls it ``ready``, and the catalogue ends up
    recording a planning PDF that was never fetched - with site boilerplate
    indexed under the document's title and citation URL. Checking what the
    bytes actually are is the only thing that catches it.
    """
    if not wants_pdf(url, expected):
        return ""
    if data.lstrip()[:len(_PDF_MAGIC)] == _PDF_MAGIC:
        return ""
    ct = content_type.split(";")[0].strip().lower() or "an unknown type"
    return (f"expected a PDF but the server returned {ct}, {len(data):,} bytes, "
            f"not starting with {_PDF_MAGIC.decode()} "
            f"(moved file served as a soft 404?)")


def _cached(dest_dir: Path, source_id: str, url: str = "", expected: str = "") -> Path | None:
    """A previously downloaded original, unless it disagrees with the URL.

    A ``.html`` cache file for a ``.pdf`` URL is a soft-404 body saved before
    the mismatch check existed; ignore it so the source is re-fetched.
    """
    hits = sorted(dest_dir.glob(f"{source_id}.*"))
    if not hits:
        return None
    if wants_pdf(url, expected) and hits[0].suffix.lower() != ".pdf":
        return None
    return hits[0]


def fetch(source_id: str, url: str, dest_dir: Path, refresh: bool = False,
          timeout: float = 60.0, retries: int = 3, opener=None,
          expected: str = "") -> FetchResult:
    """Download ``url`` to ``dest_dir/<source_id>.<ext>``.

    ``expected`` is the registry's ``expected_media_type`` hint, used to reject
    a response whose bytes are not the kind of document that was asked for.

    ``opener`` is injectable (anything with ``.open(request, timeout=)``) so
    tests can run without the network.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    if not refresh:
        cached = _cached(dest_dir, source_id, url, expected)
        if cached is not None:
            data = cached.read_bytes()
            ct = mimetypes.guess_type(cached.name)[0] or ""
            return FetchResult(source_id, True, cached, hashlib.sha256(data).hexdigest(), ct,
                               url, datetime.fromtimestamp(cached.stat().st_mtime,
                                                           timezone.utc).isoformat(),
                               from_cache=True)

    opener = opener or urllib.request.build_opener()
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                               "Accept": "application/pdf,text/html,*/*"})
    last_err = ""
    for attempt in range(retries):
        try:
            with opener.open(req, timeout=timeout) as resp:
                data = resp.read()
                ct = resp.headers.get("Content-Type", "") if hasattr(resp, "headers") else ""
                resolved = resp.geturl() if hasattr(resp, "geturl") else url
            if not data:
                raise ValueError("empty response body")
            mismatch = content_mismatch(resolved, ct, data, expected)
            if mismatch:
                # Not a transport failure, so retrying is pointless, and the
                # body must not be written: a cached soft-404 page would look
                # like a successful download on the next run.
                return FetchResult(source_id, False, error=mismatch,
                                   resolved_url=resolved,
                                   sha256=hashlib.sha256(data).hexdigest())
            ext = _ext_for(ct, resolved)
            for old in dest_dir.glob(f"{source_id}.*"):
                old.unlink()
            path = dest_dir / f"{source_id}{ext}"
            path.write_bytes(data)
            return FetchResult(source_id, True, path, hashlib.sha256(data).hexdigest(), ct,
                               resolved, datetime.now(timezone.utc).isoformat())
        except urllib.error.HTTPError as exc:
            last_err = f"HTTP {exc.code}"
            if exc.code in (401, 403, 404, 410):
                break  # retrying will not help
        except Exception as exc:  # timeouts, resets, DNS
            last_err = f"{type(exc).__name__}: {exc}"
        time.sleep(2 ** attempt)
    return FetchResult(source_id, False, error=last_err or "unknown error")
