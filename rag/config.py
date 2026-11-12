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
    #: aggregate statistics computed from GIS layers (rag.ingest.gis_aggregates)
    derived_dir: Path = DATA_DIR / "derived"
    #: candidate sources for ingestion (rag.ingest)
    registry_file: Path = DATA_DIR / "source_registry.json"
    #: downloaded originals; large, so kept out of git
    originals_dir: Path = ROOT / "documents" / "originals"
    #: chunks shorter than this are page furniture (headers, page numbers)
    min_chunk_words: int = 20
    #: strip page furniture, TOCs, duplicates and ineligible pages (rag.quality)
    apply_quality_filters: bool = True

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
    max_per_source: int = 2
    #: MMR trade-off: 1.0 = pure relevance, 0.0 = pure diversity.
    mmr_lambda: float = 0.65
    #: Small preference for passages from sources not yet represented.
    source_diversity_bonus: float = 0.05
    #: Fraction of the final slots reserved for real document text. Catalog
    #: cards are short and dense, so they out-score prose on catalog-flavoured
    #: questions and can take every slot - leaving an answer with no evidence,
    #: only an inventory of where evidence might live.
    #:
    #: This is a floor, not a budget: whatever it does not reserve goes to
    #: whichever passages win fusion, and on questions containing the word
    #: "data" or "evidence" that is reliably the catalogue cards. At 0.4 the
    #: observed split was exactly 6 chunks + 8 cards out of 14. Raised to 0.7
    #: after measuring expected-source recall across the eval questions on the
    #: 2,615-passage corpus: 0.4 -> 0.500, 0.7 -> 0.600, 1.0 -> 0.717. 1.0
    #: scores well but makes a catalogue card unreachable by construction, and
    #: Q9 legitimately expects one, so 0.7 is the stopping point. Combined with
    #: ``max_subqueries`` the measured recall is 0.750.
    min_chunk_fraction: float = 0.7
    #: How many sub-queries the LLM planner is ASKED for. The rule-based
    #: facets in ``retrieve._FACET_RULES`` are not counted against it.
    n_subqueries: int = 4
    #: Hard ceiling on the sub-queries actually issued, the original question
    #: included. Reciprocal rank fusion scores breadth over depth: one list at
    #: rank 0 contributes 1/(rrf_k+1) = 0.016, while eight lists at rank 25
    #: contribute 0.093 - 5.7x more. So a passage that is the single best
    #: answer to the question loses to one that places mediocrely on every
    #: facet probe, which is what short keyword-dense catalogue cards do. The
    #: old ceiling was 1 + 3 * n_subqueries = 13; 8 probes were enough to push
    #: a dense-rank-0 passage to fused rank 45. Recall by ceiling: 13 -> 0.500,
    #: 6 -> 0.600, 5 -> 0.700, 4 -> 0.700.
    max_subqueries: int = 5
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

    # ---- stakeholder metric tools --------------------------------------
    #: Run the metric tools (rag.tools) and hand their output to the generator
    #: as citable passages. Today every tool is a synthetic stub.
    tools_enabled: bool = True
    #: Guess the stakeholder from the question when none is given explicitly.
    tools_auto_detect: bool = True
    #: Ceiling on tool passages per question. Each is ~1.5k characters, so four
    #: cost roughly the same context as five document passages.
    max_tool_passages: int = 4

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
