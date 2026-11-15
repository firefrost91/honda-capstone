"""Persist case retrieval results; optionally run two difficult generated answers."""
import argparse,json
from pathlib import Path
from dataclasses import asdict
from rag.config import CONFIG
from rag.regress import retrieval_snapshot
from rag.index import HybridIndex
from rag.case import case_index,case_config


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--answers',action='store_true');a=ap.parse_args()
    out=Path('eval/option_b');out.mkdir(exist_ok=True)
    questions=json.loads(Path('data/cases/hilliard_rome_renner/questions.json').read_text())['questions']
    index=case_index("hilliard_rome_renner");retrieval=retrieval_snapshot(questions,case_config(),index=index)
    result={'index_manifest':json.loads((CONFIG.index_dir/'manifest.json').read_text()),'questions':retrieval,'scope':'Explicit audited case evidence; no gold-label-based filtering', 'note':'Case reference answers were not indexed. Exact source recall is a diagnostic, not a factual correctness score.'}
    (out/'case_retrieval.json').write_text(json.dumps(result,indent=2)+'\n')
    for q in questions:print(q['id'],retrieval[str(q['id'])]['expected_recall'],retrieval[str(q['id'])]['missing_expected'],flush=True)
    if a.answers:
        from rag.pipeline import RAGPipeline
        pipe=RAGPipeline(index=index,cfg=case_config())
        if not pipe.llm.available:raise RuntimeError('A real LLM is required.')
        results={'model':CONFIG.llm_model,'backend':pipe.llm.name,'answers':[]}
        for q in [q for q in questions if q['id'] in [3,5]]:
            print('Answering case',q['id'],flush=True)
            ans=pipe.answer(q['question'])
            results['answers'].append({'id':q['id'],**asdict(ans)})
            (out/'case_answers.json').write_text(json.dumps(results,indent=2)+'\n')


if __name__=='__main__':main()
