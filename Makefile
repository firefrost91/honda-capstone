VENV := ./.venv/bin

.PHONY: install install-dev index chat serve eval test test-all quality ingest ingest-gis \
        collapse regress regress-all baseline clean

install:
	python3 -m venv .venv && $(VENV)/pip install -q -r requirements.txt

install-dev: install
	$(VENV)/pip install -q -r requirements-dev.txt

# ---- data ------------------------------------------------------------------
quality:          ## corpus hygiene report -> eval/data_quality.json
	$(VENV)/python -m rag.quality

ingest:           ## fetch + extract + chunk registry sources into data/
	$(VENV)/python -m rag.ingest

ingest-gis:       ## aggregate crash statistics from the ArcGIS crash layers
	$(VENV)/python -m rag.ingest --gis

index:
	$(VENV)/python -m rag.index

# ---- app -------------------------------------------------------------------
chat:
	$(VENV)/python -m app.cli

serve:
	$(VENV)/python -m app.server

# ---- checks ----------------------------------------------------------------
test:             ## unit tests; no model or index needed
	$(VENV)/python -m pytest tests -q -m "not index and not llm"

test-all:         ## includes the real-index regression test
	$(VENV)/python -m pytest tests -q

collapse:         ## embedding-collapse diagnostics, vs baseline if present
	$(VENV)/python -m rag.embed_health --baseline eval/embed_health_baseline.json

regress:          ## corpus + retrieval regression gate (no LLM, seconds)
	$(VENV)/python -m rag.regress

regress-all:      ## + full answer generation (slow)
	$(VENV)/python -m rag.regress --tier all

baseline:         ## accept the current state: corpus, retrieval, embedding health
	$(VENV)/python -m rag.regress --update-baseline
	$(VENV)/python -m rag.embed_health --update-baseline

eval:
	$(VENV)/python -m rag.evaluate

clean:
	rm -rf index __pycache__ rag/__pycache__ rag/ingest/__pycache__ app/__pycache__ tests/__pycache__
