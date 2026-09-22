"""Central configuration.

Every tunable lives here so the retrieval behaviour can be adjusted without
touching pipeline code. Values can be overridden with environment variables
prefixed ``CBRAG_`` (e.g. ``CBRAG_LLM_MODEL``).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
INDEX_DIR = ROOT / "index"
EVAL_DIR = ROOT / "eval"


def _env(name: str, default):
    raw = os.environ.get(f"CBRAG_{name.upper()}")
    if raw is None:
        return default
    if isinstance(default, bool):
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(default, int):
        return int(raw)
    if isinstance(default, float):
        return float(raw)
    return raw


@dataclass
class Config:
    # ---- corpus -------------------------------------------------------
    chunks_file: Path = DATA_DIR / "document_chunks.jsonl"
    documents_file: Path = DATA_DIR / "documents.json"
    gis_file: Path = DATA_DIR / "gis_sources.json"
    #: chunks shorter than this are page furniture (headers, page numbers)
    min_chunk_words: int = 20

    # ---- embeddings ---------------------------------------------------
    #: bge-small is 133MB and markedly better at retrieval than MiniLM.
    #: all-MiniLM-L6-v2 is the offline fallback (already cached on most boxes).
    embed_model: str = "BAAI/bge-small-en-v1.5"
    embed_fallback_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embed_batch_size: int = 64
    #: bge models want an instruction prefix on the *query* side only.
    query_instruction: str = "Represent this sentence for searching relevant passages: "

    # ---- retrieval ----------------------------------------------------
    dense_k: int = 60          # candidates from vector search, per sub-query
    sparse_k: int = 60         # candidates from BM25, per sub-query
    rrf_k: int = 60            # reciprocal-rank-fusion damping constant
    final_k: int = 14          # passages handed to the generator
    #: Hard cap on passages from any single source_id. The MORPC TIP alone is
    #: 47% of the corpus; without this it drowns out every other document.
    max_per_source: int = 3
    #: MMR trade-off: 1.0 = pure relevance, 0.0 = pure diversity.
    mmr_lambda: float = 0.65
    #: Fraction of the final slots reserved for real document text. Catalog
    #: cards are short and dense, so they out-score prose on catalog-flavoured
    #: questions and can take every slot - leaving an answer with no evidence,
    #: only an inventory of where evidence might live.
    min_chunk_fraction: float = 0.4
    #: Multi-query expansion: how many sub-queries to plan per question.
    n_subqueries: int = 4
    use_query_planner: bool = True

    # ---- generation ---------------------------------------------------
    llm_backend: str = "auto"   # auto | mlx | ollama | llamacpp | transformers | none
    llm_model: str = "mlx-community/Qwen2.5-3B-Instruct-4bit"
    ollama_model: str = "qwen2.5:7b-instruct"
    ollama_host: str = "http://localhost:11434"
    max_tokens: int = 1500
    temperature: float = 0.2
    #: Rough budget for retrieved context, in characters.
    context_char_budget: int = 16000
    #: Request the evidence-gap section in its own pass. Roughly doubles
    #: latency and markedly sharpens the gaps; set false for speed.
    gap_second_pass: bool = True

    # ---- serving ------------------------------------------------------
    host: str = "127.0.0.1"
    port: int = 8000

    def __post_init__(self) -> None:
        for f in fields(self):
            current = getattr(self, f.name)
            if isinstance(current, Path):
                continue
            setattr(self, f.name, _env(f.name, current))

    @property
    def index_dir(self) -> Path:
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        return INDEX_DIR


CONFIG = Config()
