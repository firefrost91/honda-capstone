"""FastAPI server exposing the RAG pipeline plus a small chat UI.

    python -m app.server      then open http://127.0.0.1:8000
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from rag.config import CONFIG
from rag.pipeline import RAGPipeline

app = FastAPI(title="Columbus / Central Ohio Transportation Safety RAG")
_pipeline: RAGPipeline | None = None


def pipeline() -> RAGPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline()
    return _pipeline


class Ask(BaseModel):
    question: str = Field(..., min_length=3)
    k: int | None = None


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
    a = pipeline().answer(body.question, k=body.k)
    return {
        "question": a.question,
        "answer": a.text,
        "sources": [
            {"n": s.n, "title": s.title, "organization": s.organization,
             "locator": s.locator, "url": s.url, "kind": s.kind, "cited": s.cited}
            for s in a.sources
        ],
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
    """Server-sent events: token deltas, then a final payload with sources."""
    def gen():
        for kind, payload in pipeline().stream(body.question, k=body.k):
            if kind == "token":
                yield f"data: {json.dumps({'type': 'token', 'text': payload})}\n\n"
            else:
                a = payload
                final = {
                    "type": "done",
                    "answer": a.text,
                    "sources": [
                        {"n": s.n, "title": s.title, "organization": s.organization,
                         "locator": s.locator, "url": s.url, "cited": s.cited}
                        for s in a.sources
                    ],
                    "subqueries": a.subqueries,
                    "confidence": round(a.confidence, 3),
                    "groundedness": round(a.groundedness, 3),
                    "n_documents": a.n_sources,
                    "warnings": a.warnings,
                    "elapsed_s": round(a.elapsed_s, 1),
                }
                yield f"data: {json.dumps(final)}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (Path(__file__).parent / "static" / "index.html").read_text()


def main() -> None:
    import uvicorn
    print(f"serving on http://{CONFIG.host}:{CONFIG.port}")
    uvicorn.run(app, host=CONFIG.host, port=CONFIG.port, log_level="info")


if __name__ == "__main__":
    main()
