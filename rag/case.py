"""Explicit case-scoped retrieval over audited evidence, using the existing index.

python -m rag.case --case hilliard_rome_renner --question 'What are the available crash counts?'

This does not automatically route the general chatbot or index reference answers.
"""
from __future__ import annotations
import argparse
import json
from dataclasses import replace
from pathlib import Path
from .config import ROOT,CONFIG
from .index import HybridIndex
from .lexical import BM25,tokenize


def case_index(case_id: str, index: HybridIndex | None = None) -> HybridIndex:
    if not case_id or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_' for c in case_id):
        raise ValueError('Use a registered lowercase case ID.')
    evidence=ROOT/'data/cases'/case_id/'evidence.json'
    if not evidence.exists():
        raise ValueError('Unknown case.')
    allowed={pid:e['source_id'] for e in json.loads(evidence.read_text()) for pid in e['passage_ids']}
    index=index or HybridIndex.load()
    ids=[i for i,p in enumerate(index.passages) if allowed.get(p.passage_id)==p.source_id]
    missing=set(allowed)-{index.passages[i].passage_id for i in ids}
    if missing:
        raise ValueError('Case evidence missing from index; rebuild it first: '+', '.join(sorted(missing)))
    passages=[index.passages[i] for i in ids]
    scoped=HybridIndex(passages,index.vectors[ids],BM25([tokenize(p.embed_text) for p in passages]),index.embed_model)
    scoped._encoder=index._encoder
    return scoped


def case_config():
    # Generic regional facet expansion remains lexical, but an LLM planner is unnecessary
    # for a preselected local evidence packet. Synthetic metrics remain disabled.
    return replace(CONFIG,use_query_planner=False,tools_enabled=False,
                   context_passage_chars=2400,context_char_budget=20000)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--case',required=True)
    ap.add_argument('--question',required=True)
    ap.add_argument('--evidence-only',action='store_true')
    a=ap.parse_args();index=case_index(a.case);cfg=case_config()
    if a.evidence_only:
        from .retrieve import Retriever
        hits,_=Retriever(index,cfg).retrieve(a.question)
        print(json.dumps([{'passage_id':h.passage.passage_id,'source_id':h.passage.source_id,'citation_url':h.passage.citation_url,'text':h.passage.text} for h in hits],indent=2))
    else:
        from .pipeline import RAGPipeline
        answer=RAGPipeline(index=index,cfg=cfg).answer(a.question)
        print(answer.text)
        for source in answer.sources:print(source.format())
        if answer.warnings:print('Warnings: '+'; '.join(answer.warnings))


if __name__=='__main__':main()
