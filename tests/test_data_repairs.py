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
    verified={(a['source_id'],a['project_id']) for a in audit if a['status'].startswith('verified_')}
    assert len(audit)==50 and len(verified)==19
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


def test_recovered_demographics_preserve_groups_and_are_retrievable():
    root=Path(CONFIG.documents_file).parent
    d=json.loads((root/'curated/rtmc_demographics.json').read_text())
    assert [t['pdf_page'] for t in d['tables']]==[2,3,4,5]
    assert sum(len(g['values']) for t in d['tables'] for g in t['groups'])==104
    for t in [d['tables'][0],d['tables'][2]]:
        for g in t['groups']:
            assert abs(sum(v['percent'] for v in g['values'])-100)<0.03
    ps=[p for p in load_passages() if p.source_id==d['source_id'] and p.kind=='chunk']
    assert {p.page_number for p in ps}=={2,3,4,5}
    assert all('not crash' in p.text or 'does not state' in p.text for p in ps)


def test_hin_recovery_is_complete_and_not_crash_counts():
    root=Path(CONFIG.documents_file).parent/'local_hin'
    features=json.loads((root/'network.geojson').read_text())['features']
    manifest=json.loads((root/'manifest.json').read_text())
    assert len(features)==len({f['properties']['OBJECTID'] for f in features})==manifest['expected_count']==509
    assert manifest['limitations']


def test_refresh_cannot_restore_context_links(tmp_path):
    cat=tmp_path/'docs.json'; chunks=tmp_path/'chunks.jsonl'
    cfg=replace(CONFIG,documents_file=cat,chunks_file=chunks)
    cat.write_text(json.dumps({'sources':[{'source_id':'a','index_eligible':True,'content_status':'ready',
        'project_association_audit':'audit.json','related_project_ids':[], 'context_project_ids':['NP-125']}]}))
    chunks.write_text('')
    merge([{'source_id':'a','index_eligible':True,'content_status':'ready','related_project_ids':['NP-125']}],
          [{'source_id':'a','chunk_id':'new','content_sha256':'new','text':'Newly extracted content','related_project_ids':['NP-125']}],cfg)
    assert json.loads(cat.read_text())['sources'][0]['related_project_ids']==[]
    assert json.loads(chunks.read_text())['related_project_ids']==[]


def test_case_records_are_an_exact_subset_and_counts_match():
    root=Path(CONFIG.documents_file).parent/'cases/hilliard_rome_renner'
    case=json.loads((root/'case.json').read_text())
    members=[json.loads(x) for x in (root/'crashes.jsonl').read_text().splitlines()]
    original={r['crash_id']:r for r in load_records()}
    assert len(members)==len({r['crash_id'] for r in members})==131
    assert all(r==original[r['crash_id']] for r in members)
    assert sum(r['fatal_crash'] for r in members)==case['crashes']['fatal_crashes']==0
    assert sum(r['serious_injury_crash'] for r in members)==case['crashes']['serious_injury_crashes']==2
    assert case['radius_sensitivity_crashes']=={'75m':117,'100m':131,'150m':150}
    assert case['crashes']['rate'] is None


def test_case_infrastructure_keeps_nulls_and_duplicate_aadt_explicit():
    root=Path(CONFIG.documents_file).parent/'cases/hilliard_rome_renner'
    case=json.loads((root/'case.json').read_text())
    data=case['nearby_infrastructure_100m']
    assert len(data['columbus_crosswalks_sidewalks'])==6
    assert all(r['attributes']['ADACOMPLY'] is None for r in data['columbus_crosswalks_sidewalks'])
    counts=[r['attributes']['AADT_TOTAL'] for r in data['odot_traffic_volume']]
    assert sorted(counts)==[13851,13851,48624]
    for source,records in data.items():
        raw={r['properties']['OBJECTID']:r['properties'] for r in json.loads((root/'raw'/f'{source}.geojson').read_text())['features']}
        assert all(r['distance_m']<=100 for r in records)
        for r in records:
            for field,value in r['attributes'].items():
                original=raw[r['attributes']['OBJECTID']][field]
                assert value==(original.strip() if isinstance(original,str) else original)


def test_demo_evidence_links_resolve_to_eligible_sources():
    root=Path(CONFIG.documents_file).parent
    docs=json.loads((root/'documents.json').read_text())['sources']
    gis=json.loads((root/'gis_sources.json').read_text())['sources']
    eligible={s['source_id'] for s in docs+gis if s.get('index_eligible',True)}
    evidence=json.loads((root/'cases/hilliard_rome_renner/evidence.json').read_text())
    assert all(e['source_id'] in eligible and e['url'].startswith('https://') for e in evidence)
    for q in json.loads((root/'cases/hilliard_rome_renner/questions.json').read_text())['questions']:
        assert set(q['expected_sources']) <= eligible


def test_evidence_limits_survive_excerpt_truncation():
    from rag.corpus import Passage
    from rag.prompts import render_passage
    p=Passage('x','chunk','Long source text. '*100,'Source','sid',scope='Study area only',caveats=('Sample date unknown; not citywide.',))
    text=render_passage(1,p,max_chars=40)
    assert 'Sample date unknown; not citywide.' in text
    assert 'Study area only' in text
    assert len(text)<400


def test_case_scope_uses_evidence_manifest_not_reference_answers():
    import numpy as np
    from rag.case import case_index
    from rag.corpus import Passage
    from rag.index import HybridIndex
    from rag.lexical import BM25,tokenize
    root=Path(CONFIG.documents_file).parent/'cases/hilliard_rome_renner'
    allowed=[(pid,e['source_id']) for e in json.loads((root/'evidence.json').read_text()) for pid in e['passage_ids']]
    ps=[Passage(pid,'chunk','Source content',sid,sid) for pid,sid in allowed]
    ps.append(Passage('unrelated','chunk','Unrelated project', 'Other project','other'))
    index=HybridIndex(ps,np.eye(len(ps),dtype=np.float32),BM25([tokenize(p.text) for p in ps]),'test')
    scoped=case_index('hilliard_rome_renner',index)
    assert {p.passage_id for p in scoped.passages}=={pid for pid,_ in allowed}
    assert 'unrelated' not in {p.passage_id for p in scoped.passages}
    with pytest.raises(ValueError):case_index('../outside',index)


def test_legacy_gap_claims_are_not_prompted():
    from rag.prompts import GAP_EXAMPLES, SYSTEM_PROMPT
    assert all(example not in SYSTEM_PROMPT for example in GAP_EXAMPLES)
