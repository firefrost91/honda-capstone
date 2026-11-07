"""Source ingestion: registry -> fetch -> extract -> chunk -> merge.

``data/source_registry.json`` lists candidate documents that fill known
coverage gaps. ``python -m rag.ingest`` downloads each one, extracts text,
chunks it into the same schema as ``data/document_chunks.jsonl`` and merges
the result (idempotent by content hash) into the catalogue and chunk file.
``python -m rag.ingest --gis`` computes aggregate crash statistics from the
ArcGIS layers in ``data/gis_sources.json`` (see ``gis_aggregates``).

Run ``make index`` afterwards to re-embed.
"""
