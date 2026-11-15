"""Read-only queries over the dated West Columbus crash snapshot.

This API deliberately returns crash counts, not injury-person counts or rates.
No estimates are substituted for locations or years outside the snapshot.
"""
from __future__ import annotations
import gzip
import json
from pathlib import Path
from collections import Counter
from ..config import ROOT

DATA = ROOT / 'data' / 'local_crashes'

def load_records():
    with gzip.open(DATA / 'crash_records.jsonl.gz', 'rt') as f:
        return [json.loads(line) for line in f if line.strip()]

def crash_counts(years=None, corridor_only=True, hotspot_id=None):
    years = set(range(2021, 2026) if years is None else years)
    if not years or not years <= set(range(2021, 2026)):
        raise ValueError('Snapshot supports 2021–2025 only.')
    records = load_records()
    if hotspot_id is not None:
        sites = {x['hotspot_id']: x for x in json.loads((DATA/'hotspot_candidates.json').read_text())}
        if hotspot_id not in sites:
            raise ValueError('Unknown hotspot; use a site ID from hotspot_candidates.json.')
        site = sites[hotspot_id]
        ids = set(site['crash_ids'])
        records = [r for r in records if r['crash_id'] in ids]
        scope = f"{site['location']}: {site['radius_m']} metre buffer"
    else:
        records = [r for r in records if not corridor_only or r['in_corridor_sample']]
        scope = 'Selected corridor buffers' if corridor_only else 'West Columbus study bounding box'
    records = [r for r in records if r['year'] in years]
    return {'total_crashes':len(records), 'fatal_crashes':sum(r['fatal_crash'] for r in records),
            'serious_injury_crashes':sum(r['serious_injury_crash'] for r in records),
            'annual_counts':dict(sorted(Counter(r['year'] for r in records).items())),
            'scope':scope, 'snapshot_date':'2026-09-25',
            'source_urls':sorted({r['source_url'] for r in records}),
            'rate':None, 'rate_unavailable_reason':'No matched exposure denominator.',
            'limitations':['Crash counts are not injury-person counts.',
                           'Overlapping site buffers must not be summed.',
                           'Descriptive frequency, not statistical significance or causal effect.']}

if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--year', type=int, action='append')
    p.add_argument('--hotspot-id')
    p.add_argument('--all-study-records',action='store_true')
    a=p.parse_args()
    print(json.dumps(crash_counts(a.year,not a.all_study_records,a.hotspot_id),indent=2))
