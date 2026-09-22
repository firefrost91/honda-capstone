"""Build and load the hybrid index (dense vectors + BM25)."""
from __future__ import annotations

import json
import pickle
import time
from pathlib import Path

import numpy as np

from .config import CONFIG, Config
from .corpus import Passage, load_passages
from .lexical import BM25, tokenize

_VECTORS = "vectors.npy"
_PASSAGES = "passages.jsonl"
_BM25 = "bm25.pkl"
_MANIFEST = "manifest.json"


def _load_encoder(cfg: Config):
    from sentence_transformers import SentenceTransformer
    try:
        return SentenceTransformer(cfg.embed_model), cfg.embed_model
    except Exception as exc:  # offline, or model unavailable
        print(f"[index] {cfg.embed_model} unavailable ({exc}); "
              f"falling back to {cfg.embed_fallback_model}")
        return SentenceTransformer(cfg.embed_fallback_model), cfg.embed_fallback_model


class HybridIndex:
    def __init__(self, passages: list[Passage], vectors: np.ndarray, bm25: BM25,
                 embed_model: str):
        self.passages = passages
        self.vectors = vectors            # (n, d) L2-normalised float32
        self.bm25 = bm25
        self.embed_model = embed_model
        self._encoder = None

    # -- encoding -------------------------------------------------------
    def encode_query(self, text: str, cfg: Config = CONFIG) -> np.ndarray:
        if self._encoder is None:
            from sentence_transformers import SentenceTransformer
            self._encoder = SentenceTransformer(self.embed_model)
        prefix = cfg.query_instruction if "bge" in self.embed_model.lower() else ""
        vec = self._encoder.encode(
            [prefix + text], normalize_embeddings=True, show_progress_bar=False
        )
        return np.asarray(vec, dtype=np.float32)[0]

    # -- search ---------------------------------------------------------
    def dense_search(self, qvec: np.ndarray, top_k: int) -> list[tuple[int, float]]:
        sims = self.vectors @ qvec
        k = min(top_k, sims.shape[0])
        idx = np.argpartition(-sims, k - 1)[:k]
        idx = idx[np.argsort(-sims[idx])]
        return [(int(i), float(sims[i])) for i in idx]

    def sparse_search(self, query: str, top_k: int) -> list[tuple[int, float]]:
        from .lexical import expand_query
        return self.bm25.search(expand_query(tokenize(query)), top_k=top_k)

    # -- persistence ----------------------------------------------------
    def save(self, cfg: Config = CONFIG) -> None:
        d = cfg.index_dir
        np.save(d / _VECTORS, self.vectors)
        with (d / _PASSAGES).open("w") as fh:
            for p in self.passages:
                fh.write(json.dumps(p.to_dict()) + "\n")
        (d / _BM25).write_bytes(pickle.dumps(self.bm25))
        (d / _MANIFEST).write_text(json.dumps({
            "embed_model": self.embed_model,
            "n_passages": len(self.passages),
            "dim": int(self.vectors.shape[1]),
            "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }, indent=2))

    @classmethod
    def load(cls, cfg: Config = CONFIG) -> "HybridIndex":
        d = cfg.index_dir
        manifest_path = d / _MANIFEST
        if not manifest_path.exists():
            raise FileNotFoundError(
                f"No index at {d}. Build it first:  python -m rag.index"
            )
        manifest = json.loads(manifest_path.read_text())
        passages = [Passage.from_dict(json.loads(l)) for l in (d / _PASSAGES).open() if l.strip()]
        vectors = np.load(d / _VECTORS)
        bm25 = pickle.loads((d / _BM25).read_bytes())
        return cls(passages, vectors, bm25, manifest["embed_model"])


def build(cfg: Config = CONFIG) -> HybridIndex:
    t0 = time.time()
    passages = load_passages(cfg)
    print(f"[index] {len(passages)} passages loaded")

    encoder, model_name = _load_encoder(cfg)
    texts = [p.embed_text for p in passages]
    print(f"[index] embedding with {model_name} ...")
    vectors = encoder.encode(
        texts,
        batch_size=cfg.embed_batch_size,
        normalize_embeddings=True,
        show_progress_bar=True,
        convert_to_numpy=True,
    ).astype(np.float32)

    print("[index] building BM25 ...")
    bm25 = BM25([tokenize(t) for t in texts])

    index = HybridIndex(passages, vectors, bm25, model_name)
    index.save(cfg)
    print(f"[index] done in {time.time()-t0:.1f}s -> {cfg.index_dir}")
    return index


if __name__ == "__main__":
    build()
