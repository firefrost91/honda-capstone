"""Dissect a stakeholder evaluation run: why do the metrics look the way they do?

    python -m rag.diagnose_eval                 # writes eval/reports/stakeholder/diagnostics.md
    python -m rag.diagnose_eval --stdout        # print instead

``evaluate_stakeholders`` reports *what* scored low. This module asks *why*, and
separates three causes that the scorecard blends together:

* the label is wrong      - an expected source has no text in the corpus, or no
                            passage from it is lexically near the question;
* the retriever is wrong  - reachable evidence was crowded out (hub documents,
                            generic facet queries, a noisy LLM planner);
* the metric is wrong     - a check fires on years or route numbers, or a
                            threshold is so low that every answer passes.

It needs only numpy: everything is computed from the saved run
(``raw.jsonl`` / ``results.json``) plus live BM25 experiments over the corpus,
so it runs without the embedding model or an LLM. Dense and generation results
are read from the saved run, never re-simulated.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from statistics import mean, median

from . import metrics as M
from .attribute import _CITE, _FIGURE, _split_sentences
from .config import CONFIG, EVAL_DIR
from .corpus import load_passages
from .lexical import BM25, expand_query, tokenize
from .retrieve import _FACET_RULES, _cap_per_source, rrf_fuse

RUN_DIR = EVAL_DIR / "reports" / "stakeholder"

#: Statistics only: comma-grouped numbers, percentages, and 3+ digit numbers
#: that are not years. Years ("2026 HSIP"), route numbers ("US 23", "I-71") and
#: date ranges are what the shipped ``_FIGURE`` pattern trips on.
_STAT = re.compile(r"\b\d{1,3}(?:,\d{3})+\b|\b\d+(?:\.\d+)?\s?%|\b(?!(?:19|20)\d{2}\b)\d{3,}\b")
_ROUTE = re.compile(r"\b(?:I|IR|US|SR|OH)[- ]?\d+\b", re.I)

#: Corridors the generator attaches to unrelated questions. Counted to measure
#: how often answers reuse one memorable passage instead of question evidence.
#: Facet trigger words that appear in most questions or mean something else
#: there ("traffic delay" is not a project delay). Used by the narrowed variant.
BROAD_TRIGGERS = {"improvement", "data", "evidence", "information", "expected", "delay",
                  "future", "impact", "reduce"}

REPEATED_ENTITIES = ("Renner Road", "Trabue Road", "McKinley Avenue", "Hilliard-Rome Road")


def _family(source_id: str) -> str:
    """Collapse multi-part documents to one family (MTP attachments, RTMC study)."""
    for fam in ("morpc_mtp_2024_2050", "rtmc_mobility_study", "vision_zero_action_plan",
                "morpc_ej", "linkus"):
        if source_id.startswith(fam):
            return fam
    m = re.match(r"(proj_\w+?)_", source_id)
    return m.group(1) if m else source_id


def _load_run():
    rows = {json.loads(l)["id"]: json.loads(l)
            for l in (RUN_DIR / "raw.jsonl").read_text().splitlines() if l.strip()}
    res = json.loads((RUN_DIR / "results.json").read_text())
    for q in res["questions"]:
        if q["id"] in rows:
            rows[q["id"]]["relevancy_margin"] = q.get("relevancy_margin")
            if rows[q["id"]].get("baseline") and q.get("baseline"):
                rows[q["id"]]["baseline"]["relevancy_margin"] = q["baseline"].get("relevancy_margin")
    spec = json.loads((EVAL_DIR / "stakeholder_questions.json").read_text())
    return [rows[k] for k in sorted(rows)], res, spec


def _table(headers, body) -> list[str]:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    return out + ["| " + " | ".join(str(c) for c in r) + " |" for r in body] + [""]


# --------------------------------------------------------------------------
# 1. label audit
# --------------------------------------------------------------------------

def label_audit(passages, bm25, spec) -> tuple[list[str], dict]:
    chunks = Counter(p.source_id for p in passages if p.kind == "chunk")
    cards = {p.source_id: p.kind for p in passages if p.kind != "chunk"}
    by_prefix: dict[str, list[int]] = defaultdict(list)
    prefixes = sorted({e for q in spec["questions"] for e in q["expected_sources"]})
    for i, p in enumerate(passages):
        for e in prefixes:
            if p.source_id.startswith(e):
                by_prefix[e].append(i)

    out = ["## 1. Label audit: can the expected sources be retrieved at all?", "",
           "Each `expected_sources` entry is a prefix. Below: how much text it matches in the "
           "corpus. A prefix with no chunks can be hit only by its one catalogue card.", ""]
    body = []
    for e in prefixes:
        ids = sorted({passages[i].source_id for i in by_prefix[e]})
        n_chunk = sum(chunks[s] for s in ids)
        n_card = sum(1 for s in ids if s in cards)
        uses = sum(e in q["expected_sources"] for q in spec["questions"])
        status = ("**card only**" if n_chunk == 0 else "tiny (≤5 chunks)" if n_chunk <= 5
                  else "very broad (>100 chunks)" if n_chunk > 100 else "ok")
        body.append([f"`{e}`", uses, len(ids), n_chunk, n_card, status])
    out += _table(["Expected prefix", "Used by #q", "Source ids", "Chunks", "Cards", "Status"], body)

    # Per question: best BM25 rank (over the whole corpus) of any passage from
    # each expected prefix, querying with the raw question. Rank > 100 means the
    # label is lexically far from the question - suspect the label first.
    far, rows = 0, []
    total = 0
    for q in spec["questions"]:
        if q["layer"] == "L2" and q["id"] != 25:
            continue   # the eight L2 questions share labels; show one
        ranking = [i for i, _ in bm25.search(expand_query(tokenize(q["question"])), top_k=len(passages))]
        pos = {i: r for r, i in enumerate(ranking, 1)}
        cells = []
        for e in q["expected_sources"]:
            ranks = [pos.get(i) for i in by_prefix[e] if pos.get(i)]
            best = min(ranks) if ranks else None
            total += 1
            far += best is None or best > 100
            cells.append(f"{e}: {best or '—'}")
        rows.append([q["id"], q["theme"][:38], "; ".join(cells)])
    out += ["**Best BM25 rank of each expected source for its question** (whole corpus, "
            f"{len(passages)} passages; `—` = no lexical overlap at all). Top-14 is what the generator sees.", ""]
    out += _table(["Q", "Theme", "expected source: best rank"], rows)
    out += [f"{far} of {total} question-label pairs have no passage in BM25's top 100. "
            "Those cannot be fixed by tuning fusion weights; either the evidence is absent or the label "
            "names the wrong document.", ""]
    return out, {"card_only": [e for e in prefixes if not any(passages[i].kind == "chunk" for i in by_prefix[e])],
                 "far_pairs": far, "pairs": total}


# --------------------------------------------------------------------------
# 2. hub concentration
# --------------------------------------------------------------------------

def hub_analysis(rows, passages) -> list[str]:
    freq = Counter(s for r in rows for s in r["retrieved_sources"])
    fam_freq = Counter(f for r in rows for f in {_family(s) for s in r["retrieved_sources"]})
    corpus_fam = Counter(_family(p.source_id) for p in passages if p.kind == "chunk")
    n = len(rows)
    out = ["## 2. Hub documents crowd out question-specific evidence", "",
           f"How many of the {n} questions retrieved each source family (production run). "
           "The per-source cap is per `source_id`, so a document split into ten attachments "
           "(the MTP) gets ten caps.", ""]
    body = [[fam, f"{c}/{n}", corpus_fam.get(fam, 0),
             len({p.source_id for p in passages if _family(p.source_id) == fam})]
            for fam, c in fam_freq.most_common(12)]
    out += _table(["Family", "Questions retrieving it", "Chunks in corpus", "source_ids (caps)"], body)
    never = sorted(f for f in corpus_fam if f not in fam_freq)
    out += [f"Families with text that were **never retrieved** for any question: {', '.join(never) or 'none'}.", ""]
    mtp_share = mean(sum(_family(s) == "morpc_mtp_2024_2050" for s in r["retrieved_sources"])
                     / max(len(r["retrieved_sources"]), 1) for r in rows)
    out += [f"Mean share of a question's retrieved documents that are MTP attachments: {mtp_share:.0%}. "
            f"Top single sources: " + ", ".join(f"`{s}` {c}/{n}" for s, c in freq.most_common(3)) + ".", ""]
    return out


# --------------------------------------------------------------------------
# 3. query planning
# --------------------------------------------------------------------------

def facet_analysis(rows, spec) -> list[str]:
    out = ["## 3. Query planning adds generic probes that all point at the same hubs", ""]
    fires = Counter()
    trig_rows = []
    for q in spec["questions"]:
        low = q["question"].lower()
        hit = []
        for pattern, facets in _FACET_RULES:
            m = re.search(pattern, low)
            if m:
                fires[facets[0]] += 1
                hit.append(f"'{m.group(0)}'→{facets[0][:28]}…")
        trig_rows.append((q["id"], len(hit), hit))
    out += ["**Rule facets** fire on a keyword regex over the question, with no sense of what the word means "
            "there. Broad words (*improvement*, *data*, *evidence*) appear in most questions, so the same fixed "
            "probes are added again and again. The patterns are also written `\\bA|B|C\\b`, which binds as "
            "`\\bA` or `B` or `C\\b`: only the first and last alternatives get a word boundary.", ""]
    out += _table(["Facet group (first probe)", "Questions it fires on"],
                  [[f, f"{c}/{len(spec['questions'])}"] for f, c in fires.most_common()])
    sense = [(q["id"], m.group(0)) for q in spec["questions"]
             if (m := re.search(_FACET_RULES[5][0], q["question"].lower()))]
    out += ["**Word-sense misfires.** The cost/schedule group (\"project cost estimate\", \"construction "
            "timeline\", \"fiscal constraint\") fires on: "
            + ", ".join(f"Q{i} ('{w}')" for i, w in sense)
            + ". In every scenario question *delay* means traffic delay, and in Q8 *expected* is ordinary "
            "English, so these probes retrieve TIP budget tables for questions about intersections and EMS.", ""]
    out += [f"Mean rule facets triggered per question: {mean(n for _, n, _ in trig_rows):.1f} groups "
            f"(each adds 3-4 fixed probes). Examples: "
            + "; ".join(f"Q{i}: {', '.join(h[:3])}" for i, _, h in trig_rows if h)[:900] + "", ""]

    rule_probes = {p.lower() for _, fs in _FACET_RULES for p in fs}
    planner, bad = [], []
    for r in rows:
        for s in r["subqueries"]:
            if s == r["question"] or s.lower() in rule_probes:
                continue
            planner.append(s)
            reasons = []
            if s.rstrip().endswith(":"):
                reasons.append("heading, not a query")
            if "_" in s:
                reasons.append("underscore token")
            if re.search(r"\b(?:GIS datasets?|catalogues?|knowledge base|project records)\b", s, re.I):
                reasons.append("names the corpus, not the topic")
            if len(s.split()) > 20:
                reasons.append("over-long")
            if reasons:
                bad.append((r["id"], s, reasons))
    loc = sum(bool(re.search(r"Columbus|Central Ohio", s)) for s in planner)
    out += ["**LLM planner probes**", "",
            f"- {len(planner)} planner probes over {len(rows)} questions; {len(bad)} malformed "
            f"({len(bad) / max(len(planner), 1):.0%}).",
            f"- {loc} ({loc / max(len(planner), 1):.0%}) contain *Columbus* / *Central Ohio*, which every "
            "document in this corpus mentions, so they add no discrimination and favour the longest documents.",
            "- Examples of malformed probes:"]
    out += [f"  - Q{i}: `{s[:110]}` ({', '.join(why)})" for i, s, why in bad[:8]]
    out.append("")
    return out


# --------------------------------------------------------------------------
# 4. live sparse-side experiment
# --------------------------------------------------------------------------

def _cap_family(ordered, passages, cap):
    kept, counts = [], Counter()
    for i in ordered:
        f = _family(passages[i].source_id)
        if counts[f] >= cap:
            continue
        counts[f] += 1
        kept.append(i)
    return kept


def sparse_experiment(passages, bm25, spec, k: int) -> list[str]:
    """BM25-side variants, run live. Isolates the effect of facets and caps
    without the dense half (which needs the embedding model)."""
    def rank(query):
        return bm25.search(expand_query(tokenize(query)), top_k=CONFIG.sparse_k)

    def facets(q):
        out = [q]
        for pattern, fs in _FACET_RULES:
            if re.search(pattern, q.lower()):
                out.extend(fs)
        return out

    def narrowed(q):
        """Grouped word boundaries, broad trigger words dropped (roadmap item 1.2)."""
        out = []
        for pattern, fs in _FACET_RULES:
            m = re.search(r"\b(?:" + pattern.replace("\\b", "") + ")", q.lower())
            if m and m.group(0) not in BROAD_TRIGGERS:
                out.extend(fs)
        return out

    def weighted(q, facet_weight=0.3):
        fused: dict[int, float] = {}
        for w, ranking in [(1.0, rank(q))] + [(facet_weight, rank(f)) for f in narrowed(q)]:
            for r, (i, _) in enumerate(ranking):
                fused[i] = fused.get(i, 0.0) + w / (CONFIG.rrf_k + r + 1)
        return sorted(fused, key=fused.get, reverse=True)

    variants = {
        "bm25 question only (= saved bm25_only ablation)": lambda q: [i for i, _ in rank(q)][:k],
        "bm25 question + rule facets, RRF": lambda q: sorted(
            (f := rrf_fuse([rank(s) for s in facets(q)], CONFIG.rrf_k)), key=f.get, reverse=True)[:k],
        "bm25 question + rule facets, RRF, cap 3/source_id": lambda q: _cap_per_source(sorted(
            (f := rrf_fuse([rank(s) for s in facets(q)], CONFIG.rrf_k)), key=f.get, reverse=True),
            passages, 3)[:k],
        "bm25 question only, cap 3/source_id": lambda q: _cap_per_source(
            [i for i, _ in rank(q)], passages, 3)[:k],
        "bm25 question only, cap 2/document family": lambda q: _cap_family(
            [i for i, _ in rank(q)], passages, 2)[:k],
        "bm25 question + narrowed facets (weight 0.3), RRF": lambda q: weighted(q)[:k],
        "bm25 question + narrowed facets (weight 0.3), cap 2/family": lambda q: _cap_family(
            weighted(q), passages, 2)[:k],
    }
    body = []
    for name, fn in variants.items():
        ms = []
        for q in spec["questions"]:
            ids = [passages[i].source_id for i in fn(q["question"])]
            ms.append(M.retrieval_metrics(ids, q["expected_sources"]))
        body.append([name] + [f"{mean(m[key] for m in ms):.3f}" for key in ("source_recall", "hit", "mrr", "precision")])
    out = ["## 4. Live experiment: the sparse half of the retriever", "",
           f"Run now on the corpus ({len(passages)} passages, top-{k}). The first row reproduces the saved "
           "`bm25_only` ablation, which checks this harness against the original run. Dense retrieval needs "
           "the embedding model and is not re-run here; its numbers come from the saved ablation.", ""]
    out += _table(["Variant", "Source recall", "Hit", "MRR", "Precision"], body)
    return out


# --------------------------------------------------------------------------
# 5. faithfulness checks
# --------------------------------------------------------------------------

def flag_audit(rows) -> list[str]:
    out = ["## 5. Hard flags: the catalogue-figure check fires on years and route numbers", ""]
    body, real = [], 0
    for r in rows:
        if r["hard_flag_free"]:
            continue
        cards = {int(re.match(r"\[S(\d+)\]", s).group(1)) for s in r["cited_sources"]
                 if "GIS data catalog entry" in s}
        body_text, gaps = M.split_body_and_gaps(r["answer"])
        for piece in _split_sentences(r["answer"]):
            cites = {int(n) for n in _CITE.findall(piece)}
            clean = _CITE.sub("", piece)
            if not cites or not cites <= cards or not _FIGURE.search(clean):
                continue
            in_gaps = piece.strip() in gaps
            stats = [x for x in _STAT.findall(_ROUTE.sub("", clean))]
            real += bool(stats) and not in_gaps
            body.append([r["id"], ", ".join(_FIGURE.findall(clean)), "gap section" if in_gaps else "body",
                         ", ".join(stats) or "none", clean.strip()[:120].replace("|", "/")])
    out += _table(["Q", "Tokens the shipped regex read as figures", "Where", "Actual statistics", "Sentence"], body)
    n = len([r for r in rows if not r["hard_flag_free"]])
    out += [f"{n} answers carry a `catalog_figure` flag; with years, route numbers and the gap section "
            f"excluded, **{real}** sentence(s) still quote a statistic from a catalogue card. "
            "Note Q34's '2013-2017' date range: it is in a document chunk (MTP attachment 08, PDF page 21) "
            "but the attribution pinned it to the HIN data card, so the citation is wrong even though "
            "the fact exists.", ""]
    return out


def groundedness_audit(rows, res) -> list[str]:
    g = [r["groundedness"] for r in rows]
    un = sum(r["n_unsupported"] for r in rows)
    jf = [r["judge_faithfulness"] for r in rows if r.get("judge_faithfulness") is not None]
    jv = res["summary"].get("judge_validation") or {}
    out = ["## 6. Groundedness is saturated; the judge disagrees", "",
           f"- Embedding groundedness: min {min(g):.2f}, median {median(g):.2f}, max {max(g):.2f}; "
           f"{un} sentences flagged unsupported across {len(rows)} answers.",
           f"- LLM-judge faithfulness on cited claims: mean {mean(jf):.2f} (judge passed its control at "
           f"{jv.get('claim_pos_accept', 0):.0%} accept / {jv.get('claim_neg_reject', 0):.0%} reject).",
           "- A metric where every answer scores 100% cannot rank anything. BGE cosine scores are compressed "
           "into a high band (BAAI's model card says so), and mean query-passage similarity in this run is "
           f"{mean(r['retrieval_confidence'] for r in rows):.2f}, so `SUPPORT_THRESHOLD = 0.50` sits below "
           "almost any in-domain pair and passes topical sentences that assert things the passage does not say. The judge's rejects include planning boilerplate "
           "(\"To evaluate ... we need to consider\") which is not a claim, so 0.22 under-states faithfulness too: "
           "the true value is somewhere between, and neither metric can tell you where.", ""]

    reuse = {e: [r["id"] for r in rows if e.lower() in r["answer"].lower()] for e in REPEATED_ENTITIES}
    l2 = [r for r in rows if r["layer"] == "L2"]
    bound = [r["id"] for r in l2 if re.search(r"8 to 2|from 8|eight to two", r["answer"])
             and any(e.lower() in r["answer"].lower() for e in REPEATED_ENTITIES)]
    out += ["**Entity reuse across unrelated questions** (answers that name the corridor):", ""]
    out += _table(["Entity", "Answers", "Question ids"],
                  [[e, len(v), ", ".join(map(str, v))] for e, v in reuse.items()])
    out += [f"Layer 2 answers that attach the *hypothetical* 8→2 scenario to a real named intersection: "
            f"{', '.join('Q' + str(i) for i in bound) or 'none'}. These pass groundedness at 100% because the "
            "intersection really is in a retrieved passage; the claim that it is *the* project is invented.", ""]
    return out


# --------------------------------------------------------------------------
# 6. answer quality vs baseline, context, latency
# --------------------------------------------------------------------------

def answer_audit(rows) -> list[str]:
    base = [r for r in rows if r.get("baseline")]
    pw = sum(r["probe_recall"] > r["baseline"]["probe_recall"] for r in base)
    pl = sum(r["probe_recall"] < r["baseline"]["probe_recall"] for r in base)
    mw = sum(r["relevancy_margin"] > r["baseline"]["relevancy_margin"] for r in base
             if r.get("relevancy_margin") is not None and r["baseline"].get("relevancy_margin") is not None)
    hit = [r for r in base if r["ret_hit"]]
    miss = [r for r in base if not r["ret_hit"]]

    def gap(rs, key):
        return mean(r[key] - r["baseline"][key] for r in rs) if rs else float("nan")

    out = ["## 7. RAG vs the no-retrieval baseline, per question", "",
           f"- Probe coverage: RAG wins {pw}, loses {pl}, ties {len(base) - pw - pl} of {len(base)}.",
           f"- Relevancy margin: RAG higher on {mw} of {len(base)}.",
           f"- When retrieval hit an expected source (n={len(hit)}), RAG − baseline probe coverage = {gap(hit, 'probe_recall'):+.2f}; "
           f"when it missed (n={len(miss)}), {gap(miss, 'probe_recall'):+.2f}.",
           "- Read: RAG trails by *more* when retrieval succeeded, so probe coverage is not tracking evidence. "
           "Probes are generic vocabulary (*speed*, *crash*, *intersection*) that a longer generic answer hits as "
           "easily as a grounded one. Treat it as a diagnostic, not a target. The margin gap is different: RAG "
           "answers drift toward whatever the hub passages discuss (see entity reuse above), so they fit their "
           "own question less well than the baseline does.", ""]
    np_ = Counter(r["n_passages"] for r in rows)
    lat = sorted(rows, key=lambda r: -r["elapsed_s"])[:3]
    l1 = mean(r["locality"] for r in rows if r["layer"] == "L1")
    l2 = mean(r["locality"] for r in rows if r["layer"] == "L2")
    out += ["## 8. Smaller findings", "",
            f"- **Context budget truncates.** Passages that reached the generator: "
            + ", ".join(f"{k}→{v}q" for k, v in sorted(np_.items()))
            + f" (asked for {CONFIG.final_k}). The {CONFIG.context_char_budget}-char budget at 1,150 chars per passage "
              "fits ~12; the lowest-ranked 1-2 hits are always dropped, so `final_k` above 12 is not doing anything.",
            f"- **Layer 2 loses locality**: mean {l2:.1f} local terms vs {l1:.1f} on Layer 1. Scenario prompts pull "
            "generic retrieval; perspective alignment 38%, answers 0.90 similar.",
            "- **Latency**: " + ", ".join(f"Q{r['id']} {r['elapsed_s']:.0f}s" for r in lat)
            + ". One outlier (Q17) is 8x the median and shifts the mean; report the median alongside.",
            "- **Report bug**: `render_report` re-reads the question file inside a loop and indexes it by "
            "`id - 1`, which silently mislabels rows if ids ever stop being 1..N.", ""]
    return out


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------

def build_report() -> str:
    rows, res, spec = _load_run()
    passages = load_passages(CONFIG)
    bm25 = BM25([tokenize(p.embed_text) for p in passages])
    s = res["summary"]
    out = ["# Stakeholder evaluation: diagnostics", "",
           f"Dissects run {s['date']} (commit `{s['git_commit']}`, {s['n_questions']} questions). "
           "Generated by `python -m rag.diagnose_eval`. Sections 1-4 explain retrieval, 5-6 faithfulness, "
           "7-8 answers. Section 4 is a live run; the rest analyses the saved run.", ""]
    labels, _ = label_audit(passages, bm25, spec)
    out += labels
    out += hub_analysis(rows, passages)
    out += facet_analysis(rows, spec)
    out += sparse_experiment(passages, bm25, spec, CONFIG.final_k)
    out += flag_audit(rows)
    out += groundedness_audit(rows, res)
    out += answer_audit(rows)
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()
    text = build_report()
    if args.stdout:
        print(text)
    else:
        (RUN_DIR / "diagnostics.md").write_text(text)
        print(f"wrote {RUN_DIR / 'diagnostics.md'}")


if __name__ == "__main__":
    main()
