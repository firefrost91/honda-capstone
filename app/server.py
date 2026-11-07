"""FastAPI server exposing the RAG pipeline plus a small chat UI.

    python -m app.server      then open http://127.0.0.1:8000
"""
from __future__ import annotations

import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from rag.config import CONFIG
from rag.pipeline import RAGPipeline
from rag.tools import STAKEHOLDERS, catalog

app = FastAPI(title="Columbus / Central Ohio Transportation Safety RAG")
_pipeline: RAGPipeline | None = None
_load_lock = threading.Lock()
#: One local model, one answer at a time. A stopped request can still be
#: finishing its last step in a worker thread when the next one arrives.
_answer_lock = threading.Lock()


def pipeline() -> RAGPipeline:
    global _pipeline
    with _load_lock:
        if _pipeline is None:
            _pipeline = RAGPipeline()
    return _pipeline


@app.on_event("startup")
def _warm_up() -> None:
    """Load the index in the background so the first visitor is not the one who waits."""
    threading.Thread(target=pipeline, daemon=True).start()


class Ask(BaseModel):
    question: str = Field(..., min_length=3)
    k: int | None = None
    #: stakeholder profile id (see GET /stakeholders); None = detect from the question
    stakeholder: str | None = None


def _sources(a) -> list[dict]:
    return [{"n": s.n, "title": s.title, "organization": s.organization,
             "locator": s.locator, "url": s.url, "kind": s.kind, "cited": s.cited}
            for s in a.sources]


@app.get("/stakeholders")
def stakeholders() -> dict:
    """The perspectives a caller can ask from, with the tools each one uses."""
    return {"stakeholders": catalog()["stakeholders"],
            "tools_enabled": CONFIG.tools_enabled}


@app.get("/tools")
def tools() -> dict:
    """The metric tools and the metric catalogue they emit against."""
    c = catalog()
    return {"tools": c["tools"], "metrics": c["metrics"], "synthetic": True}


@app.get("/health")
def health() -> dict:
    p = pipeline()
    return {
        "status": "ok",
        "backend": p.llm.name,
        "llm_available": p.llm.available,
        "llm_model": CONFIG.llm_model,
        "embed_model": p.index.embed_model,
        "passages": len(p.index.passages),
        "documents": len({x.source_id for x in p.index.passages}),
    }


@app.post("/ask")
def ask(body: Ask) -> dict:
    a = pipeline().answer(body.question, k=body.k, stakeholder=_stakeholder(body))
    return {
        "question": a.question,
        "answer": a.text,
        "stakeholder": a.stakeholder,
        "tool_calls": a.tool_calls,
        "sources": _sources(a),
        "subqueries": a.subqueries,
        "confidence": round(a.confidence, 3),
        "groundedness": round(a.groundedness, 3),
        "unsupported_claims": a.unsupported_claims,
        "n_documents": a.n_sources,
        "warnings": a.warnings,
        "elapsed_s": round(a.elapsed_s, 1),
        "backend": a.backend,
    }


@app.post("/ask/stream")
def ask_stream(body: Ask):
    """Server-sent events: stage updates and token deltas, then a final payload
    with sources - or an error event, so the page never waits on a dead stream."""
    _stakeholder(body)          # a bad id is a 422 now, not an error mid-stream
    def gen():
        with _answer_lock:
            try:
                yield from _events(body)
            except Exception as e:                      # noqa: BLE001
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    return StreamingResponse(_closing(gen()), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


async def _closing(events):
    """Step a blocking event generator on its own thread, and close it when
    the client goes away.

    On disconnect Starlette cancels the response but never closes a sync
    generator, so a stopped answer would sit suspended holding _answer_lock
    and the next question would wait behind it. Every step and the close run
    on one thread, in order: mlx_lm generates inside a thread-local stream
    context that must exit on the thread that entered it, and a single worker
    queues the close behind any step still running instead of racing it.
    """
    worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="answer")
    loop = asyncio.get_running_loop()
    try:
        while (chunk := await loop.run_in_executor(worker, next, events, None)) is not None:
            yield chunk
    finally:
        worker.submit(events.close)
        worker.shutdown(wait=False)


def _stakeholder(body: Ask) -> str | None:
    sid = (body.stakeholder or "").strip() or None
    if sid is not None and sid not in STAKEHOLDERS:
        raise HTTPException(status_code=422,
                            detail=f"unknown stakeholder {sid!r}; see GET /stakeholders")
    return sid


def _events(body: Ask):
    for kind, payload in pipeline().stream(body.question, k=body.k,
                                           stakeholder=_stakeholder(body)):
        if kind == "stage":
            yield f"data: {json.dumps({'type': 'stage', **payload})}\n\n"
        elif kind == "token":
            yield f"data: {json.dumps({'type': 'token', 'text': payload})}\n\n"
        else:
            a = payload
            final = {
                "type": "done",
                "answer": a.text,
                "stakeholder": a.stakeholder,
                "tool_calls": a.tool_calls,
                "sources": _sources(a),
                "subqueries": a.subqueries,
                "confidence": round(a.confidence, 3),
                "groundedness": round(a.groundedness, 3),
                "n_documents": a.n_sources,
                "warnings": a.warnings,
                "elapsed_s": round(a.elapsed_s, 1),
            }
            yield f"data: {json.dumps(final)}\n\n"


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (Path(__file__).parent / "static" / "index.html").read_text()


def main() -> None:
    import uvicorn
    print(f"serving on http://{CONFIG.host}:{CONFIG.port}")
    uvicorn.run(app, host=CONFIG.host, port=CONFIG.port, log_level="info")


if __name__ == "__main__":
    main()
