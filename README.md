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
| Document chunks | 1,402 | Text from MORPC plans, Vision Zero Columbus action plans, ODOT manuals, corridor studies, project fact sheets |
| Source cards | 38 | One per catalogued document — title, publisher, topics, scope, caveats |
| GIS data cards | 38 | One per regional dataset — ODOT crash years, AADT, speed limits, Columbus High Injury Network, sidewalks, signals, Safe Routes to School |

**The GIS records themselves are not loaded — only their catalogue entries.** The
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

## Evaluation

```bash
./.venv/bin/python -m rag.evaluate            # all 10 prototype questions
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

### Stakeholder evaluation (34 questions)

```bash
make eval-stakeholders            # ~2 h on an M-series Mac; checkpoints after every question
./.venv/bin/python -m rag.evaluate_stakeholders --report-only   # rebuild reports from a partial run
```

Runs `eval/stakeholder_questions.json` (24 stakeholder-specific questions, the 8-stakeholder
shared scenario, 2 add-ons) and writes `eval/reports/stakeholder/` - `report.md`,
`results.json`, `per_question.csv`, `transcript.md`. Scores the RAG triad (retrieval,
faithfulness, answer relevance), a retrieval ablation, a no-retrieval baseline, and
whether Layer 2 answers differ by stakeholder perspective. `expected_sources` and `probes`
in the question file are unreviewed silver labels.

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
  answers expect is not in this corpus at all. The system says so rather than
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
rag/     corpus · lexical · index · retrieve · llm · prompts ·
         postprocess · attribute · pipeline · evaluate
app/     cli.py · server.py · static/index.html
eval/    questions.json · local_lexicon.json · results.json · transcript.md
tests/   test_rag.py
```
