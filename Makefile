VENV := ./.venv/bin

.PHONY: install index chat serve eval test clean

install:
	python3 -m venv .venv && $(VENV)/pip install -q -r requirements.txt

index:
	$(VENV)/python -m rag.index

chat:
	$(VENV)/python -m app.cli

serve:
	$(VENV)/python -m app.server

eval:
	$(VENV)/python -m rag.evaluate

test:
	$(VENV)/python tests/test_rag.py

clean:
	rm -rf index __pycache__ rag/__pycache__ app/__pycache__ tests/__pycache__
