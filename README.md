# Central Ohio Transportation Safety — Local RAG

A retrieval-augmented chatbot over Columbus / Central Ohio transportation-safety
sources, running entirely on open-source models on your own machine. No API keys,
no data leaves the box.

It is built to answer the analytical questions a planner actually asks — *how have
trends changed*, *what should we prioritise*, *what do we still not know* — rather
than single-fact lookups, and to be explicit about the limits of its evidence.

---

## What it knows

| Layer | Count | What it is |
|---|---|---|
| Document chunks | 1,389 | Text from MORPC plans, Vision Zero Columbus action plans, ODOT manuals, corridor studies, project fact sheets — after the hygiene pass in `rag/quality.py` (1,563 raw) |
| Source cards | 38 | One per catalogued document — title, publisher, topics, scope, caveats |
| GIS data cards | 38 | One per regional dataset — ODOT crash years, AADT, speed limits, Columbus High Injury Network, sidewalks, signals, Safe Routes to School |

| GIS aggregate summaries | 0 until `make ingest-gis` | Server-side year × severity × county counts from the ODOT / Columbus crash layers, as citable `data_summary` passages |

**The GIS records themselves are not loaded — only their catalogue entries** (and, once
`make ingest-gis` has run, aggregate counts computed from them). The
system is built to respect that line: it will tell you the Columbus High Injury
Network layer exists, who maintains it and what fields it reports, and it will
refuse to quote a crash count from it. That distinction is enforced in the data
cards, the system prompt, and the tests.

---

## Quick start

```bash
cd ~/Documents/columbus-safety-rag
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
./.venv/bin/python -m rag.index          # build the index (~1 min)
./.venv/bin/python -m app.server         # then open http://127.0.0.1:8000
```

Terminal chat instead of the browser:

```bash
./.venv/bin/python -m app.cli
```

One-shot question:

```bash
./.venv/bin/python -m app.cli -q "What should Columbus prioritise to reduce serious crashes?"
```

---

## How it works

```
question
   │
   ├─ query planning ........ rule-based facets + LLM-generated sub-queries
   │
   ├─ hybrid retrieval ...... BGE-small dense vectors ∥ BM25 (domain tokeniser)
   │                          fused with reciprocal rank fusion
   │
   ├─ selection ............. cap 3 passages/document · MMR for diversity
   │                          · floor on real document text vs catalogue cards
   │
   ├─ coverage diagnosis .... tells the model how thin its evidence actually is
   │
   ├─ generation ............ Qwen2.5-3B-Instruct-4bit via MLX (Apple Silicon)
   │                          answer pass, then a separate evidence-gap pass
   │
   └─ verification .......... template-echo removal · acronym repair ·
                              sentence-level attribution + groundedness ·
                              catalogue-figure check · geographic scope check
```

Each stage exists because a simpler version failed on these questions. The
reasoning is written up in the module docstrings; the short version:

**Query planning.** A broad question like "how have trends changed" embeds to the
centroid of several topics and retrieves none of them well. Splitting it into
facets and fusing the results reaches all of them.

**Hybrid retrieval.** Dense search misses exact identifiers (`SR-161`, PID
numbers); BM25 misses paraphrase. RRF combines them without needing the two score
scales to be comparable.

**Per-document caps.** The MORPC TIP is 47% of the corpus. Uncapped, it wins most
queries on surface area alone and every answer cites one document.

**Chunk floor.** Catalogue cards are short and keyword-dense, so on any question
phrased around "data" they sweep every slot — leaving an answer that inventories
where evidence might live without containing any.

**Post-hoc attribution.** A 3B model will not reliably place `[S#]` markers, so
citation is treated as verification, not generation: every factual sentence is
embedded and matched against the passages it is supposed to rest on. Sentences
nothing supports are flagged inline as `[unsupported by retrieved evidence]`.
This is what catches fluent inventions — an early run expanded "HIN" to *High
Impact Neighborhood* instead of *High Injury Network*.

**Catalogue-claim check.** Similarity attribution has one blind spot it cannot
close: a sentence that quotes a crash count and cites only a GIS *catalogue*
entry is topically perfect and still fabricated, because those records were
never loaded. Any figure whose every citation is a data card is flagged
separately.

**Geographic scope check.** The highest-risk error for a regional RAG is not an
invented number but a real one attached to the wrong geography — these documents
constantly set a national statistic beside a regional one ("177,409 people across
the U.S. … Central Ohio has seen similarly concerning trends"). Similarity
attribution is blind to it, because the number really is in the cited passage. So
every figure is traced back to the sentence that governs it in the source, and a
national→local flip is reported.

**Split generation.** Asking one small model for the answer *and* the evidence-gap
section in a single shot makes it trade them off: it either leads with the gap
section and never writes an answer, or writes a good answer and forgets the
section. So the two are requested separately — a body retry if the answer is
missing, and a focused second pass for the gaps, which also produces much
sharper ones (naming Renner Road, McKinley Avenue and the COTSP rather than
"more data is needed"). A deterministic section derived from retrieval is the
last-resort fallback.

---

## Data quality, sources, embedding health and regression

The workflow for growing the corpus without making answers worse:

```bash
make install-dev
make ingest          # fetch + chunk the sources in data/source_registry.json
make ingest-gis      # aggregate crash counts from the ArcGIS crash layers
make ingest-fars     # fatal-crash trends per county from NHTSA FARS (2014+)
make quality         # what the hygiene pass kept and dropped
make index           # re-embed; also records embedding health in index/manifest.json
make collapse        # embedding-collapse diagnostics (fails on alarm or drift)
make regress         # corpus + retrieval gate against the committed baselines
make baseline        # once you're happy: accept the new state, then commit eval/baseline_*.json
```

**Corpus hygiene** (`rag/quality.py`, applied at load time — the raw chunk file is never
rewritten). Running headers and template lines that recur in ≥25% of a document's chunks are
stripped (the MORPC TIP's `PID: Project Name: …` block alone appeared ~300 times; 149k
characters removed in total), tables of contents and dot-leader pages are dropped, exact and
near duplicates are removed, `index_eligible` / `indexed_page_range` from the catalogue are
finally respected, and a short page-head split from its page is folded into the next chunk
instead of being lost. Short-but-substantive pages ("In 2019, 54 deaths occurred in 49 fatal
crashes") are kept. `make quality` writes the per-source table to `eval/data_quality.json`.

**More sources** (`rag/ingest/`). `data/source_registry.json` lists 32 candidate documents found
by targeted search for the known coverage gaps: MORPC's COTSP and five State of Safety reports
(2012–2022 trends), the 2025 Ohio SHSP and Ohio's 2022/2024 HSIP reports, the Franklin County SS4A
plan, MORPC's 2024 Complete Streets policy, Vision Zero's 2024 annual report and 2026 updates,
Columbus Fire's 2022/2023 annual reports and the 2023/2024 Ohio trauma reports (post-crash care),
FHWA's Columbus I-70/I-71 reconnection case study and the Columbus Crossroads Phase 4 overview
(King-Lincoln Bronzeville, cost), ODOT District 6's 2024 projects briefing, LinkUS, plus retries
of the two handoff downloads that failed. Each entry names the question/gap it targets. `make ingest` downloads,
extracts (pdfplumber / HTML main-text), chunks into the existing schema and merges
idempotently; a failed retry never overwrites a good source. URLs are search results, not yet
downloaded — check `eval/ingest_report.json` after the first run.

**FARS fatal-crash trends** (`rag/ingest/fars.py`, `make ingest-fars`). NHTSA's Fatality Analysis
Reporting System, via its CrashAPI, gives every fatal crash since 2010. For each of seven Central
Ohio counties it counts fatal crashes and deaths per year (2014 onward) and writes one trend
passage per county plus a regional total, as citable `data_summary` passages. Records are counted,
never stored; a response without a deaths field is an error.

**GIS aggregates** (`rag/ingest/gis_aggregates.py`). Field names are read from each layer's
metadata (never assumed; pin them in `data/gis_field_map.json` if matching fails), severity
codes are decoded only from the layer's own coded-value domains, and counts are grouped
server-side. Every passage states the layer, grouping and date that produced it; statewide
totals are labelled *NOT a Central Ohio figure*. A cross-year trend passage per county is
built from the per-year layers. Figures cited to these `data_summary` passages are allowed;
figures cited only to a catalogue `data_card` are still flagged.

**Embedding collapse** (`rag/embed_health.py`). Checks the stored vectors for anisotropy
(mean pairwise cosine), low effective rank / one dominant direction, near-duplicate rate,
hubness (k-occurrence skew + the top hub passages by id), per-source collapse (documents whose
passages are indistinguishable), and the query-side symptom — different eval questions
retrieving the same passages. Absolute thresholds are in `Thresholds` (override with
`CBRAG_HEALTH_<NAME>`), drift tolerances against `eval/embed_health_baseline.json` in
`DRIFT_TOLERANCE`. Every `make index` records the summary in the manifest.

**Regression gate** (`rag/regress.py`). Three tiers:

| tier | needs | checks |
|---|---|---|
| `corpus` | nothing | every eligible document still has passages; passage count hasn't dropped >5%; every `expected_sources` id exists |
| `retrieval` (default) | index + embedder | per question: recall of `expected_sources` in the final context, distinct documents, evidence share — deterministic (rule-based planning, no LLM) |
| `all` | + LLM | locality, groundedness ≥ 85%, gap section, `must_mention_any`, `forbidden` strings |

Questions live in `eval/questions.json`; the `schema` block there documents each field.
**To add the remaining questions, append entries** — only `id` and `question` are required.
A question with no baseline entry is held to the absolute checks and reported as *new* until
`make baseline` is run. `aspirational_sources` names registry documents that *should* surface
once ingested; they are reported, not gated.

## Evaluation

```bash
./.venv/bin/python -m rag.evaluate            # all prototype questions
./.venv/bin/python -m rag.evaluate --only 3 7 # a subset
```

Writes `eval/results.json` and a readable `eval/transcript.md`.

Current run on an M1 / 8 GB Mac, all ten questions passing:

| metric | value |
|---|---|
| mean locality (local proper nouns per answer) | 7.5 |
| mean distinct documents cited | 8.5 |
| mean groundedness | 100% |
| answers with an evidence-gap section | 10 / 10 |
| mean latency | 70 s |

Locality moves by a point or two between runs — generation is sampled, not
greedy. Latency is roughly half that with `CBRAG_GAP_SECOND_PASS=0`, at the cost
of vaguer gap sections.

The headline metric is **locality**: how many Columbus/Central Ohio proper nouns
and programme names the answer uses (`Renner Road`, `COTSP`, `SFY 2026–2029 TIP`,
`High Injury Network`). A general-purpose LLM answering the same questions from
memory scores near zero by construction — it has no way to name them. Alongside
it: groundedness, distinct documents cited, retrieval confidence, and whether the
answer produced its *what the evidence does not cover* section.

---

## Configuration

Every setting in `rag/config.py` can be overridden with a `CBRAG_` env var:

```bash
CBRAG_FINAL_K=20 CBRAG_MAX_PER_SOURCE=2 ./.venv/bin/python -m app.cli
```

Useful ones: `FINAL_K`, `MAX_PER_SOURCE`, `MMR_LAMBDA`, `MIN_CHUNK_FRACTION`,
`LLM_BACKEND`, `LLM_MODEL`, `TEMPERATURE`, `CONTEXT_CHAR_BUDGET`.

### Swapping the model

The default is Qwen2.5-3B-4bit via MLX, chosen to fit comfortably on an 8 GB
Apple Silicon machine. Backends are auto-detected in order `mlx → ollama →
llamacpp → transformers`.

```bash
# larger model, if you have the RAM (~4.3 GB resident)
CBRAG_LLM_MODEL=mlx-community/Qwen2.5-7B-Instruct-4bit ./.venv/bin/python -m app.cli

# Ollama instead
ollama serve && ollama pull qwen2.5:7b-instruct
CBRAG_LLM_BACKEND=ollama ./.venv/bin/python -m app.cli

# GGUF via llama.cpp (Linux / Windows / CPU)
pip install llama-cpp-python
CBRAG_LLM_BACKEND=llamacpp CBRAG_GGUF_PATH=/path/model.gguf ./.venv/bin/python -m app.cli
```

With `CBRAG_LLM_BACKEND=none` retrieval still runs and answers become extractive —
useful for testing retrieval changes without generation cost.

---

## HTTP API

```bash
curl -s localhost:8000/health

curl -s localhost:8000/ask -H 'Content-Type: application/json' \
  -d '{"question":"What data exists for pedestrian safety analysis?"}' | jq
```

`POST /ask/stream` is the same thing as server-sent events: `{"type":"token"}`
deltas followed by a final `{"type":"done"}` carrying the verified answer,
sources, groundedness and warnings.

---

## Known limits

- **Coverage is uneven.** Post-crash / EMS response is thin, and the
  King-Lincoln Bronzeville and Long Street Bridge history that some reference
  answers expect is not in this corpus until the registry sources targeting
  them are ingested (`make ingest`). The system says so rather than
  filling the hole from memory — but that means those answers are gap statements,
  not narratives.
- **GIS records are not loaded**, so no question that needs a computed crash rate,
  count or hotspot can be answered here. Answers point at the service endpoint
  instead.
- **PDF extraction is imperfect.** Tables and figure-heavy pages come through
  ragged; some numbers live only in images and are invisible to retrieval.
- **A 3B model is the weak link**, not retrieval. It occasionally writes flat,
  list-like prose. Moving to 7B noticeably improves synthesis if RAM allows.
- **Groundedness is a similarity check**, not entailment. It reliably catches
  topical invention, and the scope and catalogue checks close the two specific
  blind spots that mattered most here — but it will not catch a correctly-themed
  sentence that reverses a document's meaning.
- **Warnings are part of the answer.** A response can be 100% "grounded" and still
  carry a scope-mismatch or catalogue-figure warning. Read them.

## Layout

```
rag/          corpus · quality · lexical · index · embed_health · retrieve · llm ·
              prompts · postprocess · attribute · pipeline · evaluate · regress
rag/ingest/   fetch · extract · chunk · gis_aggregates · fars · __main__ (CLI)
app/          cli.py · server.py · static/index.html
data/         documents.json · document_chunks.jsonl · gis_sources.json ·
              source_registry.json · derived/ (GIS aggregates)
eval/         questions.json · local_lexicon.json · results.json · transcript.md ·
              data_quality.json · baseline_*.json · embed_health_baseline.json
tests/        test_rag · test_quality · test_ingest · test_embed_health · test_regression
.github/      workflows/ci.yml — unit tests, index build, collapse check, retrieval gate
```
