"""``python -m rag.ingest`` - fetch, extract, chunk and merge registry sources.

    python -m rag.ingest --list                # what the registry holds
    python -m rag.ingest                       # ingest every source not yet in the catalogue
    python -m rag.ingest --only odot_shsp_2025 # one source
    python -m rag.ingest --refresh             # re-download and re-chunk everything
    python -m rag.ingest --gis                 # aggregate crash statistics from GIS layers
    python -m rag.ingest --dry-run             # do everything except write data/

Then rebuild the index:  python -m rag.index
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from ..config import CONFIG, EVAL_DIR, ROOT, Config
from .chunk import chunk_source
from .extract import content_status, extract
from .fetch import fetch

#: Registry fields copied into the document catalogue.
_CATALOG_FIELDS = ("source_id", "title", "organization", "source_kind", "document_type",
                   "theme", "scope", "source_url", "download_url", "description",
                   "relevance", "topics", "related_project_ids", "parent_source_id",
                   "published_year", "gap_targeted")


def load_registry(cfg: Config = CONFIG) -> list[dict]:
    path = Path(cfg.registry_file)
    if not path.exists():
        return []
    return json.loads(path.read_text())["sources"]


def _read_catalog(cfg: Config) -> dict:
    return json.loads(Path(cfg.documents_file).read_text())


def _read_chunks(cfg: Config) -> list[dict]:
    with Path(cfg.chunks_file).open() as fh:
        return [json.loads(l) for l in fh if l.strip()]


def ingest_source(src: dict, cfg: Config = CONFIG, refresh: bool = False,
                  opener=None) -> tuple[dict, list[dict], dict]:
    """Fetch + extract + chunk one registry entry.

    Returns (catalogue entry, chunk rows, report row). Never raises: a failed
    source comes back with ``content_status = failed`` and no chunks, which is
    exactly how the handoff recorded its own failures.
    """
    sid = src["source_id"]
    url = src.get("download_url") or src["source_url"]
    entry = {k: src[k] for k in _CATALOG_FIELDS if k in src}
    entry.setdefault("source_kind", "document")
    entry.setdefault("parent_source_id", None)
    entry["catalog_verification_claim"] = "ingested_by_rag.ingest"
    entry["description_provenance"] = src.get("description_provenance",
                                              "registry_summary_not_primary_evidence")
    caveats = list(src.get("caveats") or [])

    res = fetch(sid, url, Path(cfg.originals_dir), refresh=refresh, opener=opener,
                expected=src.get("expected_media_type", ""))
    report = {"source_id": sid, "url": url, "fetched": res.ok, "from_cache": res.from_cache}
    if not res.ok:
        entry.update(content_status="failed", index_eligible=False,
                     caveats=caveats + [f"Download failed: {res.error}."])
        report.update(status="failed", error=res.error, n_chunks=0)
        return entry, [], report

    ex = extract(res.path, res.content_type)
    status, extra = content_status(ex)
    try:
        original_path = str(res.path.relative_to(ROOT))
    except ValueError:
        original_path = str(res.path)
    entry.update(
        resolved_url=res.resolved_url, retrieved_at=res.retrieved_at, sha256=res.sha256,
        content_status=status, index_eligible=status in ("ready", "ready_with_caveats"),
        original_path=original_path, caveats=caveats + extra,
    )
    rows = chunk_source(entry, ex.pages, original_path) if entry["index_eligible"] else []
    report.update(status=status, kind=ex.kind, pages=ex.n_pages,
                  empty_pages=ex.n_empty_pages, chars=ex.total_chars, n_chunks=len(rows))
    return entry, rows, report


def reject_shared_bodies(entries: list[dict], rows: list[dict],
                         known: dict[str, dict] | None = None) -> list[str]:
    """Fail any source whose bytes are byte-identical to another document's.

    The mismatch check in ``fetch`` catches a site that answers a moved PDF
    with an HTML page. It cannot catch the same thing happening to a source
    that legitimately *is* a web page - there the stand-in page is exactly the
    kind of document we asked for. What gives it away is that several distinct
    documents come back with the same sha256: one body cannot be eight
    different reports. Both are then marked failed rather than trusted, and
    their chunks are dropped.

    Mutates ``entries`` and ``rows`` in place; returns the rejected ids.
    """
    by_sha: dict[str, list[dict]] = defaultdict(list)
    for e in entries:
        if e.get("sha256") and e.get("index_eligible"):
            by_sha[e["sha256"]].append(e)
    # a body already trusted in the catalogue counts as a claimant too
    for sid, k in (known or {}).items():
        if k.get("sha256") and not any(e["source_id"] == sid for e in entries):
            by_sha[k["sha256"]].append({"source_id": sid, "_already_in_catalog": True})

    rejected = []
    for sha, claimants in by_sha.items():
        if len(claimants) < 2:
            continue
        others = sorted(c["source_id"] for c in claimants)
        for e in claimants:
            if e.get("_already_in_catalog"):
                continue
            peers = [s for s in others if s != e["source_id"]]
            e.update(content_status="failed", index_eligible=False,
                     caveats=list(e.get("caveats") or []) + [
                         f"Download rejected: identical bytes (sha256 {sha[:12]}) were also "
                         f"served for {', '.join(peers)}; the server is answering with one "
                         "stand-in page instead of these documents."])
            rejected.append(e["source_id"])
    if rejected:
        drop = set(rejected)
        rows[:] = [r for r in rows if r["source_id"] not in drop]
    return rejected


def merge(entries: list[dict], rows: list[dict], cfg: Config = CONFIG) -> tuple[int, int]:
    """Upsert catalogue entries and replace each source's chunks. Idempotent."""
    catalog = _read_catalog(cfg)
    by_id = {s["source_id"]: i for i, s in enumerate(catalog["sources"])}
    replaced = set()
    for e in entries:
        if e["source_id"] in by_id:
            # a failed retry must not wipe out a source that was ingested before
            old = catalog["sources"][by_id[e["source_id"]]]
            if e.get("content_status") == "failed" and old.get("index_eligible"):
                continue
            catalog["sources"][by_id[e["source_id"]]] = {**old, **e}
        else:
            catalog["sources"].append(e)
        replaced.add(e["source_id"])
    Path(cfg.documents_file).write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n")

    existing = [r for r in _read_chunks(cfg) if r["source_id"] not in replaced]
    seen = {r["content_sha256"] for r in existing if r.get("content_sha256")}
    added = 0
    for r in rows:
        if r["source_id"] not in replaced:
            continue
        if r["content_sha256"] in seen:
            continue
        seen.add(r["content_sha256"])
        existing.append(r)
        added += 1
    with Path(cfg.chunks_file).open("w") as fh:
        for r in existing:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(entries), added


def run(only: list[str] | None = None, refresh: bool = False, dry_run: bool = False,
        cfg: Config = CONFIG, opener=None) -> list[dict]:
    registry = load_registry(cfg)
    known = {s["source_id"]: s for s in _read_catalog(cfg)["sources"]}
    todo = []
    for src in registry:
        if only and src["source_id"] not in only:
            continue
        if src.get("status") == "skip":
            continue
        already = known.get(src["source_id"], {})
        if not refresh and not only and already.get("index_eligible"):
            continue
        todo.append(src)
    if not todo:
        print("nothing to ingest (use --refresh or --only to force)")
        return []

    entries, rows, reports = [], [], []
    for src in todo:
        print(f"  {src['source_id']:46s} ", end="", flush=True)
        e, r, rep = ingest_source(src, cfg, refresh=refresh, opener=opener)
        entries.append(e)
        rows += r
        reports.append(rep)
        print(f"{rep['status']:30s} {rep.get('n_chunks', 0):4d} chunks  {rep.get('error', '')}")

    shared = reject_shared_bodies(entries, rows, known)
    for sid in shared:
        rep = next(r for r in reports if r["source_id"] == sid)
        rep.update(status="failed", n_chunks=0,
                   error="identical bytes served for several sources")
        print(f"  {sid:46s} REJECTED: shared response body")

    if dry_run:
        print("\ndry run: data/ not modified")
    else:
        n_e, n_c = merge(entries, rows, cfg)
        print(f"\nmerged {n_e} catalogue entries, {n_c} new chunks -> "
              f"{cfg.documents_file.name}, {cfg.chunks_file.name}")
        print("next: python -m rag.quality && python -m rag.index")
    (EVAL_DIR / "ingest_report.json").write_text(json.dumps(reports, indent=2))
    return reports


def _list(cfg: Config = CONFIG) -> None:
    known = {s["source_id"]: s for s in _read_catalog(cfg)["sources"]}
    for s in load_registry(cfg):
        state = known.get(s["source_id"], {}).get("content_status", "not ingested")
        print(f"{s['source_id']:46s} {state:24s} {', '.join(s.get('gap_targeted', []))}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--only", nargs="*", help="registry source_ids to ingest")
    ap.add_argument("--refresh", action="store_true", help="re-download and re-chunk")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--list", action="store_true", help="show the registry and its status")
    ap.add_argument("--gis", action="store_true",
                    help="compute aggregate crash statistics from GIS layers")
    a = ap.parse_args(argv)
    if a.list:
        _list()
        return 0
    if a.gis:
        from .gis_aggregates import run as run_gis
        return run_gis(only=a.only, dry_run=a.dry_run)
    reports = run(only=a.only, refresh=a.refresh, dry_run=a.dry_run)
    return 1 if reports and all(r["status"] == "failed" for r in reports) else 0


if __name__ == "__main__":
    sys.exit(main())
