"""Prevent unavailable metadata or synthetic numbers from becoming evidence."""
import json
from dataclasses import replace
from pathlib import Path

import pytest

from rag.config import CONFIG, Config
from rag.corpus import load_passages, _chunk_passages, _summary_passages
from rag.ingest.__main__ import merge
from rag.tools.local_crashes import DATA, crash_counts, load_records


def test_snapshot_counts_reconcile_and_ids_are_unique():
    rows = load_records()
    assert len(rows) == len({r['crash_id'] for r in rows}) == 7167
    counts = crash_counts()
    assert (counts['total_crashes'], counts['fatal_crashes'], counts['serious_injury_crashes']) == (1802, 11, 29)
    assert counts['annual_counts'] == {2021:310,2022:359,2023:371,2024:385,2025:377}
    assert counts['rate'] is None
    assert crash_counts(corridor_only=False)['total_crashes'] == 7167


def test_every_hotspot_matches_underlying_records():
    sites = json.loads((DATA/'hotspot_candidates.json').read_text())
    assert len(sites) == 127
    for s in sites:
        c = crash_counts(hotspot_id=s['hotspot_id'])
        for key in ('total_crashes', 'fatal_crashes', 'serious_injury_crashes'):
            assert c[key] == s[key], (s['hotspot_id'],key)
        assert {str(k):v for k,v in c['annual_counts'].items()} == {k:v for k,v in s['annual_counts'].items() if v}


@pytest.mark.parametrize('years', [[], [2026], [2020,2021]])
def test_snapshot_rejects_unsupported_years(years):
    with pytest.raises(ValueError):
        crash_counts(years)


def test_exclusion_is_enforced_even_without_quality_filter(tmp_path):
    p=tmp_path/'chunks.jsonl'
    p.write_text(json.dumps({'source_id':'bad','chunk_id':'bad1','text':'Evidence should never survive an explicit source rejection. '*20})+'\n')
    cfg=replace(CONFIG,chunks_file=p,apply_quality_filters=False)
    assert list(_chunk_passages(cfg,{'bad':{'index_eligible':False}})) == []
    (tmp_path/'a_summary_chunks.jsonl').write_text(json.dumps({'source_id':'bad','chunk_id':'bad2','text':'Wrong layer statistics'})+'\n')
    assert list(_summary_passages(replace(cfg,derived_dir=tmp_path),{'bad':{'index_eligible':False}})) == []


def test_audited_links_and_gis_rejections_do_not_leak_into_corpus():
    root=Path(CONFIG.documents_file).parent
    docs=json.loads((root/'documents.json').read_text())['sources']
    audit=json.loads((root/'project_link_audit.json').read_text())
    verified={(a['source_id'],a['project_id']) for a in audit if a['status']=='verified_explicit_project_identifier'}
    assert len(audit)==49 and len(verified)==15
    for d in docs:
        assert all((d['source_id'],p) in verified for p in d.get('related_project_ids',[]))
    ps=load_passages()
    gis=json.loads((root/'gis_sources.json').read_text())['sources']
    rejected={s['source_id'] for s in gis if s.get('index_eligible') is False}
    assert rejected and not rejected.intersection(p.source_id for p in ps)
    local=[p for p in ps if p.source_id=='west_columbus_crash_snapshot' and p.kind=='data_summary']
    assert len(local)==127 and all(p.scope=='West Columbus study area only' for p in local)
    available={p.source_id for p in ps}
    for q in json.loads((root.parent/'eval/questions.json').read_text())['questions']:
        assert set(q.get('expected_sources',[])) <= available


def test_synthetic_tools_are_opt_in():
    assert Config().tools_enabled is False


def test_replacement_without_chunks_drops_stale_text_but_failed_retry_preserves_it(tmp_path):
    cat=tmp_path/'docs.json'; chunks=tmp_path/'chunks.jsonl'
    cfg=replace(CONFIG,documents_file=cat,chunks_file=chunks)
    cat.write_text(json.dumps({'sources':[{'source_id':'a','index_eligible':True,'content_status':'ready'}]}))
    row={'source_id':'a','chunk_id':'old','content_sha256':'abc','text':'Previously extracted evidence'}
    chunks.write_text(json.dumps(row)+'\n')
    merge([{'source_id':'a','index_eligible':False,'content_status':'failed'}],[],cfg)
    assert chunks.read_text().strip()
    merge([{'source_id':'a','index_eligible':False,'content_status':'reference_only_visual_content'}],[],cfg)
    assert not chunks.read_text().strip()
