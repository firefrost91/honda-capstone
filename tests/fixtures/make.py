"""Tiny fixtures built in code, so no binary files live in the repo."""
from __future__ import annotations

import json


def minimal_pdf(pages: list[str]) -> bytes:
    """A valid PDF with one line of Helvetica text per page (empty string = blank page)."""
    objs: list[bytes] = []
    n = len(pages)
    page_ids = [3 + 2 * i for i in range(n)]
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{pid} 0 R" for pid in page_ids).encode()
    objs.append(b"<< /Type /Pages /Kids [" + kids + b"] /Count " + str(n).encode() + b" >>")
    font_id = 3 + 2 * n
    for i, text in enumerate(pages):
        content_id = page_ids[i] + 1
        objs.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 "
            + str(font_id).encode() + b" 0 R >> >> /Contents " + str(content_id).encode() + b" 0 R >>")
        safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = (f"BT /F1 10 Tf 40 750 Td ({safe}) Tj ET" if text else "").encode()
        objs.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream
                    + b"\nendstream")
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n").encode()
    return bytes(out)


HTML_PAGE = """<!doctype html><html><head><title>Vision Zero Progress</title>
<script>var tracking = 1;</script></head><body>
<header><nav><a href="/">Home</a> <a href="/services">City services menu link</a></nav></header>
<div class="site-nav"><ul><li>Navigation item that should vanish</li></ul></div>
<main><h1>Vision Zero Columbus progress update</h1>
<p>In 2024 the city recorded fewer pedestrian deaths on the High Injury Network than in 2023.</p>
<p>Speed management projects on Morse Road and Cleveland Avenue were completed this year.</p>
<ul><li>Leading pedestrian intervals were added at 40 signalised intersections.</li></ul>
</main><footer>Copyright City of Columbus footer text</footer></body></html>"""


#: ArcGIS layer metadata + group-by statistics, shaped like a real MapServer.
ARCGIS_META = {
    "name": "2023_Crash_Locations",
    "objectIdField": "OBJECTID",
    "fields": [
        {"name": "OBJECTID", "type": "esriFieldTypeOID"},
        {"name": "COUNTY_NME", "type": "esriFieldTypeString"},
        {"name": "CRASH_YR", "type": "esriFieldTypeInteger"},
        {"name": "CRASH_SEVERITY_CD", "type": "esriFieldTypeString",
         "domain": {"type": "codedValue", "codedValues": [
             {"code": "1", "name": "Fatal"}, {"code": "2", "name": "Serious Injury"},
             {"code": "5", "name": "Property Damage Only"}]}},
        {"name": "PEDESTRIAN_IND", "type": "esriFieldTypeString"},
        {"name": "BICYCLE_IND", "type": "esriFieldTypeString"},
    ],
}


def arcgis_stats(params: dict) -> dict:
    group = params["groupByFieldsForStatistics"].split(",")
    rows = [
        {"COUNTY_NME": "FRANKLIN", "CRASH_YR": 2023, "CRASH_SEVERITY_CD": "1", "n": 120},
        {"COUNTY_NME": "FRANKLIN", "CRASH_YR": 2023, "CRASH_SEVERITY_CD": "2", "n": 900},
        {"COUNTY_NME": "FRANKLIN", "CRASH_YR": 2023, "CRASH_SEVERITY_CD": "5", "n": 30000},
        {"COUNTY_NME": "DELAWARE", "CRASH_YR": 2023, "CRASH_SEVERITY_CD": "1", "n": 15},
        {"COUNTY_NME": "CUYAHOGA", "CRASH_YR": 2023, "CRASH_SEVERITY_CD": "1", "n": 140},
    ]
    if "PEDESTRIAN_IND" in group:
        rows = [{"COUNTY_NME": "FRANKLIN", "CRASH_YR": 2023, "PEDESTRIAN_IND": "Y", "n": 700},
                {"COUNTY_NME": "FRANKLIN", "CRASH_YR": 2023, "PEDESTRIAN_IND": "N", "n": 30320}]
    elif "BICYCLE_IND" in group:
        rows = [{"COUNTY_NME": "FRANKLIN", "CRASH_YR": 2023, "BICYCLE_IND": "Y", "n": 210}]
    return {"features": [{"attributes": {k: v for k, v in r.items() if k in group or k == "n"}}
                         for r in rows]}


def fake_arcgis(url: str, params: dict) -> dict:
    if params.get("f") == "json" and "outStatistics" not in params:
        return json.loads(json.dumps(ARCGIS_META))
    return arcgis_stats(params)


class HashingEncoder:
    """Deterministic stand-in for the sentence encoder (hashed bag of words).

    Lets retrieval and regression code run end to end without downloading a
    model. Its numbers mean nothing about BGE quality - only about plumbing.
    """

    def __init__(self, dim: int = 256):
        self.dim = dim

    def encode(self, texts, normalize_embeddings=True, **_):
        import hashlib

        import numpy as np

        from rag.lexical import tokenize
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            for tok in tokenize(t):
                h = int.from_bytes(hashlib.md5(tok.encode()).digest()[:4], "little")
                out[i, h % self.dim] += 1.0 if (h >> 31) & 1 else -1.0
        if normalize_embeddings:
            out /= np.maximum(np.linalg.norm(out, axis=1, keepdims=True), 1e-9)
        return out


def toy_index(passages=None, dim: int = 256):
    """A HybridIndex over ``passages`` (default: the real corpus) using HashingEncoder."""
    from rag.corpus import load_passages
    from rag.index import HybridIndex
    from rag.lexical import BM25, tokenize
    passages = passages if passages is not None else load_passages()
    enc = HashingEncoder(dim)
    texts = [p.embed_text for p in passages]
    idx = HybridIndex(passages, enc.encode(texts), BM25([tokenize(t) for t in texts]),
                      "hashing-test-encoder")
    idx._encoder = enc
    return idx
