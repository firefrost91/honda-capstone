# Stakeholder evaluation: issues and fix roadmap

Based on the 2026-10-03 run (`report.md`, commit `f224584`) and the diagnostics in
`diagnostics.md` (regenerate with `python -m rag.diagnose_eval`).

## TL;DR

- **Retrieval is the real problem, and the pipeline's own extra stages are causing it.** The
  production retriever (hybrid + LLM planner) is the *worst* row in the ablation: recall 0.30 vs
  0.45 for plain dense search, MRR 0.28 vs 0.57. Three causes, each measured:
  1. the LLM planner writes junk probes;
  2. keyword-triggered rule facets add the same generic probes to most questions;
  3. the per-source cap is per `source_id`, so the MTP's ten attachments get ten caps.
  
  Together they pull in the same hub documents (MTP attachments in 33/34 questions, Vision Zero
  in 32/34). Project records, LinkUS, Bike Plus and the rail manual are never retrieved.
- **Three scorecard lines measure the wrong thing.** The "invented figure" flag (82%) fires
  on years and route numbers: **0 of 7** flagged sentences actually quote a statistic.
  Groundedness (100% on every answer) is saturated and can't rank anything. Probe coverage passes,
  but the no-retrieval baseline beats RAG on it (15 losses, 5 wins).
- **Generation has one serious, under-reported failure.** In 4 of 8 shared-scenario answers, the model
  attaches the *hypothetical* "8 → 2 crashes" project to a real intersection (Renner Road /
  Hilliard Road), and the 100% groundedness score lets it through. Renner Road appears in
  15/34 answers, most of which aren't about it.
- **Labels are a secondary issue.** 4 expected documents (5 label entries) have no text in the corpus, only a catalogue card. Fixing
  them moves recall by about 0.02–0.04. The retriever changes move it by about 0.3 (measured on BM25).

---

## 1. Issues, metric by metric

| Metric (reported) | Verdict | What is actually going on | Evidence |
|---|---|---|---|
| Source recall 0.30, hit 0.79 (below target) | **Real** | Hub documents crowd out question-specific sources (causes below). Labels contribute a little. | Ablation: dense-only 0.45 / 0.88, hybrid without planner 0.39 / 0.97. Diagnostics §2, §4 |
| MRR 0.28 | **Real** | Fusion with generic probes pushes the passage that best matches the question down the ranking | Dense-only MRR 0.57; BM25 MRR drops 0.58 → 0.34 when shipped facets are fused in (§4) |
| Hard-flag-free 82% (below target) | **Metric bug** | `_FIGURE` matches `2026` in "ODOT 2026 HSIP", `23`/`71` in "US 23 and I-71", and years in the gap section, which is *meant* to talk about catalogue entries | §5: 0 real statistics among 7 flagged sentences. Q34 is a real but different bug: a 2013-2017 date that comes from MTP att. 08 got attributed to the HIN data card |
| Groundedness 1.00 (pass) | **Metric saturated** | 0.50 cosine threshold sits below almost every in-domain pair; 0 unsupported sentences in 34 answers | §6; contrast judge faithfulness 0.22 |
| Judge faithfulness 0.22 | **Noisy, with real signal** | Judge scores preambles ("To evaluate… we need to consider") as claims, so 0.22 is too low. But it also catches real binding errors | §6: Q26/28/29/31 assign the scenario to a real intersection |
| Context precision (judge) | **Missing** | Relevance judge accepted 12% of obviously relevant passages; withheld, correctly | `judge_validation.json` |
| Relevancy margin 0.08 (pass) | **Pass, but trails baseline** | Baseline margin 0.13; RAG higher on only 3/34. Answers drift toward hub content | §7 |
| Probe coverage 0.65 (pass) | **Not discriminating** | Baseline 0.72. RAG trails by *more* when retrieval succeeded, so probes measure vocabulary, not evidence | §7 |
| L2 perspective alignment 38%, similarity 0.90 | **Real** | Same retrieval for every stakeholder (Jaccard 0.73); locality falls to 2.2 vs 8.9 on Layer 1 | report §5, diagnostics §8 |
| Latency 129 s mean | **Skewed** | Q17 took 1,036 s (8× the median), which inflates the mean | §8 |
| `final_k = 14` | **Silently 12** | 16,000-char budget at ~1,300 chars/passage fits 12-13; the last 1-2 hits are always dropped | §8 |

### Root causes of the retrieval failure

1. **LLM planner** (`rag/retrieve.py: plan_subqueries`). 25% of its probes are malformed:
   headings ending in `:`, `Columbus Central_Ohio projects`, "Which GIS datasets catalogues…".
   80% contain *Columbus / Central Ohio*, which every document mentions. It takes hit rate from 0.97
   to 0.79.
2. **Rule facets** (`_FACET_RULES`). They fire on bare keywords: *improvement* (23/34),
   *data/evidence* (17/34). *delay* means traffic delay in every scenario question, but it fires the
   **project cost / schedule** probes. In live BM25, adding them cuts recall 0.371 → 0.289 and MRR
   0.576 → 0.338. The ×(1 + 0.12·n) multi-probe boost then rewards the passages that match the most
   generic probes, which are the hubs.
3. **Cap per `source_id`, not per document.** The MTP is 10 source_ids (10 × 3 slots), the RTMC study 5,
   Vision Zero 2. In live BM25, capping at 2 per *document family* lifts recall 0.371 → 0.638 and hit
   0.794 → 0.971.
4. **Small documents can't compete.** `proj_*` records are 1–3 chunks each; LinkUS has 5. They lose every
   RRF contest to documents with 40+ chunks.
5. **Catalogue cards take ~23% of slots.** The HIN card appears in 18/34 questions and HSIP intersections
   in 15/34. They are useful once per answer, not in every answer.

---

## 2. Roadmap

Ordered so that every later phase is measured with a correct ruler. Each item names the change,
where it goes, the evidence for it, and how to check it.

### Phase 0: Fix the measurement first (≈ 1 day)

| # | Change | Where | Expected effect | Verify |
|---|---|---|---|---|
| 0.1 | Use a stats-only regex in the catalogue check (comma numbers, %, 3+ digit non-years; strip `I-/US/SR` routes) and skip the gap section | `rag/attribute.py: _FIGURE`, `check_catalog_claims`; `pipeline._finish` | Hard-flag-free 82% → ~100% on the saved answers, with no real flag lost | Unit tests on the 7 sentences in diagnostics §5 |
| 0.2 | Make the attribution number-aware: prefer the passage that *contains* the figure or year | `rag/attribute.py: attribute` | Fixes the Q34 class of wrong-citation errors | Test: "2013-2017" sentence cites MTP att. 08, not the HIN card |
| 0.3 | Recalibrate groundedness like the judge: build controls (sentence vs own passage / vs a same-topic unrelated passage) and pick the threshold that separates them. Or swap in a small local NLI cross-encoder | `rag/attribute.py: SUPPORT_THRESHOLD`, new control test in `evaluate_stakeholders.validate_judge` | Groundedness drops below 1.0 and starts ranking answers | Control accept/reject ≥ 75% |
| 0.4 | Drop non-claims (preambles, questions, headings) before judging | `rag/metrics.py: cited_claims` | Judge faithfulness becomes interpretable | Spot-check 20 rejects |
| 0.5 | Fix labels: 4 card-only documents (`vision_zero_hin_map`, `cota_park_and_ride_locations`, `proj_np37*`, `fhwa_railway_crossing_resources`). Either ingest the documents (see 3.1) or relabel to the closest retrievable source. Get a domain reviewer to sign off on all `expected_sources` | `eval/stakeholder_questions.json` | +0.02–0.04 recall; recall becomes quotable | Diagnostics §1: no card-only rows |
| 0.6 | Count the 8 shared-scenario questions as **one** retrieval sample (their retrieval is near-identical) | `rag/evaluate_stakeholders.summarise` | Stops one retrieval result from carrying 8/34 of the weight | Report shows n=27 for retrieval |
| 0.7 | Demote probe coverage to a diagnostic. Report median latency next to the mean. Add an *entity-reuse rate* and a *scenario-binding* check | `evaluate_stakeholders.py` | The scorecard tracks things that move with quality | n/a |

**Exit:** the rebuilt `report.md` (`--report-only` after the metric changes) shows ~100% hard-flag-free,
non-saturated groundedness, and recall on the corrected labels.

### Phase 1: Retrieval (≈ 2 days, biggest lever)

You can test each change without generation:
`CBRAG_LLM_BACKEND=none python -m rag.evaluate_stakeholders`. Change one thing at a time.

| # | Change | Where | Evidence / expected effect |
|---|---|---|---|
| 1.1 | **Turn the LLM planner off by default** (`use_query_planner=False`). If you bring it back later, add guards: reject lines ending in `:`, lines containing `_`, "GIS dataset", "knowledge base", or > 15 words, and strip *Columbus/Central Ohio* | `rag/config.py`, `retrieve.plan_subqueries` | Ablation: hit 0.79 → 0.97, recall 0.30 → 0.39, and one fewer LLM call per question |
| 1.2 | **Narrow the rule facets.** Group the regex `\b(?:a|b|c)\b`. Drop the broad triggers (*improvement, data, evidence, information, expected, delay, future, impact, reduce*). Give facet rankings a lower RRF weight than the question (≈ 0.3) | `retrieve._FACET_RULES`, `rrf_fuse` (add weights) | Live BM25: recall 0.289 → 0.377, hit 0.71 → 0.85, MRR 0.34 → 0.67 |
| 1.3 | **Cap per document family, not per source_id.** Add a `family` field at load time (MTP attachments, RTMC attachments, VZ plans, each `proj_<id>`). Cap at 2 | `rag/corpus.py`, `retrieve._cap_per_source` | Live BM25: recall 0.371 → 0.638, hit 0.79 → 0.97. With 1.2: **0.644 / 1.00 / MRR 0.69** |
| 1.4 | Remove or shrink the multi-probe boost `×(1 + 0.12·(n-1))`. It rewards matching many generic probes | `retrieve.Retriever.retrieve` | Fewer hubs; check `max_doc_share` and how often the top family appears |
| 1.5 | Limit catalogue cards to ~3 slots unless the question is about data/datasets | `retrieve._select` | `card_share` 23% → ≤ 15% |
| 1.6 | Make `final_k` honest: either budget ~19k chars or `final_k=12`, so truncation never drops ranked hits silently | `config.py` / `prompts.build_context` | n_passages = final_k |
| 1.7 | Then try a cross-encoder reranker (e.g. bge-reranker-base) over the top ~50 fused candidates. Dense-only already has the best MRR, so reranking is likely to help more than adding probes | `retrieve.py` | Target MRR ≥ 0.6 |

**Exit (on corrected labels):** source recall ≥ 0.50, hit ≥ 0.90, MRR ≥ 0.5, MTP family in < 60% of
questions, and every family with chunks retrieved at least once.
> The BM25 numbers above are live. The hybrid numbers need confirming on the Mac, where the embedding
> model is available (see *Limits of this analysis*).

### Phase 2: Generation and faithfulness (≈ 2–3 days)

| # | Change | Where | Evidence |
|---|---|---|---|
| 2.1 | **Hypothetical-scenario guard.** Add a prompt rule: "the scenario is hypothetical; do not identify it with a named location". Add a post-check that flags any sentence pairing the scenario figures with a corridor name | `prompts.py`, new check in `attribute.py` | Q26/28/29/31 currently do this |
| 2.2 | Track the entity-reuse rate (share of answers naming a corridor not in the question or the top-3 passages). It should fall after Phase 1. If not, add a prompt rule to prefer passages tied to the question's topic | `evaluate_stakeholders.py` | Renner Road in 15/34 answers |
| 2.3 | **Stakeholder-aware retrieval for Layer 2.** Add each stakeholder's `perspective_terms` (already in the question file) as one weighted probe, so the evidence differs by lens, and add a "lens" line to the prompt | `retrieve.py`, `pipeline.answer(…, stakeholder=)` | Alignment 38%, similarity 0.90, source Jaccard 0.73, L2 locality 2.2 |
| 2.4 | Find out why Q17 took 1,036 s (likely a body retry plus a runaway generation). Add per-stage timing and a hard timeout per LLM call | `pipeline.py`, `llm.py` | One question is ~23% of total runtime |
| 2.5 | Re-run generation on the 7B model (README says synthesis improves) and compare on the Phase 0 metrics | config only | 3B is also the judge, so it shares blind spots with the generator |

**Exit:** no scenario-binding flags, perspective alignment ≥ 75%, relevancy margin ≥ baseline,
recalibrated groundedness ≥ 0.85, judge faithfulness (claims only) ≥ 0.7.

### Phase 3: Coverage (ongoing)

| # | Change | Why |
|---|---|---|
| 3.1 | Ingest text for the 5 card-only documents (NP37 Hilliard construction update, COTA Park & Ride, FHWA rail crossing resources, VZ HIN map page, RTMC attachment 03) | Q1, Q7, Q9, Q10, Q11, Q15, Q19, Q21, Q23, Q33 expect one of them |
| 3.2 | Merge each project's 1–3 chunks (fact sheet + Engage Columbus page + crash stats) into one "project record" passage, alongside the raw chunks | Project docs can't win RRF at 1 chunk each |
| 3.3 | Source documents for the thin themes the report names: EMS / traffic incident management, transit first/last mile, construction-impact communications | Q9, Q10, Q15 recall 0.00. The honest answer today is a gap statement |

---

## 3. How to validate each change

1. Freeze the current run as the baseline (copy `eval/reports/stakeholder/` to `…/baseline_2026-10-03/`).
2. Phase 0 changes are scoring-only. Rebuild with `--report-only` and compare without re-running generation.
3. Phase 1 changes are retrieval-only. Use `CBRAG_LLM_BACKEND=none` for fast loops, then one full run.
4. Phase 2 changes need generation. Do 3 runs (temperature 0.2 is sampled) and report the median ±
   range. With 27–34 questions, differences under ~0.1 are within noise (see the report's CIs).
5. Re-run `python -m rag.diagnose_eval` after each phase. Hub frequency, facet firing and flag audits
   should all improve, not just the headline numbers.
6. Watch for **overfitting to silver labels**. The family cap raises recall partly by adding document
   diversity. Check that judge context precision (once a relevance judge passes its control) does not fall.

## Limits of this analysis

- This container could not download `BAAI/bge-small-en-v1.5` or run MLX. Hugging Face and the PyTorch
  index are blocked by the network policy. So **dense retrieval and generation were not re-run**.
  Section 4 of `diagnostics.md` is a live BM25 run; it reproduces the saved `bm25_only` ablation exactly
  (0.371 / 0.794 / 0.576 / 0.317), which validates the harness. Everything else is analysis of the
  saved run. Hybrid-retriever numbers after the changes have to be measured on the Mac.
- Recall is measured against silver labels. Treat absolute values as provisional until a domain
  reviewer signs off on them (item 0.5).
