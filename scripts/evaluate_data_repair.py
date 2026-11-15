"""Persist regression findings and full answers without replacing baselines.

Run after `python -m rag.index`:
  python -m scripts.evaluate_data_repair --stage option_a --answers
  python -m scripts.evaluate_data_repair --stage option_b
"""
import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path
from rag import regress
from rag.config import CONFIG, ROOT


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--stage',default='option_a')
    ap.add_argument('--answers',action='store_true')
    a=ap.parse_args()
    if not a.stage.replace('_','').isalnum():
        ap.error('stage must contain letters, numbers or underscores')
    out=Path('eval')/a.stage;out.mkdir(exist_ok=True)
    def save(name,obj):
        (out/(name+'.json')).write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
    qs=regress.load_questions()
    def portable(value):
        if not isinstance(value, Path):
            return value
        return str(value.relative_to(ROOT)) if value.is_relative_to(ROOT) else str(value)
    save('run_metadata',{'config':{k:portable(v) for k,v in asdict(CONFIG).items()},'index_manifest':json.loads((CONFIG.index_dir/'manifest.json').read_text()),'gguf_artifact':Path(os.environ.get('CBRAG_GGUF_PATH','')).name or None,'baseline_policy':'Compare only; do not replace committed baselines.'})
    corpus=regress.corpus_snapshot()
    cf=regress.check_corpus(corpus,regress._read(regress.BASELINE_CORPUS),qs)
    save('corpus',{'snapshot':corpus,'failures':cf})
    retrieval=regress.retrieval_snapshot(qs,CONFIG)
    rf,rn=regress.check_retrieval(retrieval,regress._read(regress.BASELINE_RETRIEVAL),qs)
    save('retrieval',{'questions':retrieval,'failures':rf,'notes':rn})
    print('Corpus failures:',cf,'Retrieval failures:',rf,flush=True)
    failed = bool(cf or rf)
    if a.answers:
        from rag.pipeline import RAGPipeline
        from rag.evaluate import score_answer
        from rag.llm import NullLLM
        pipe=RAGPipeline(cfg=CONFIG)
        if not pipe.llm.available or isinstance(pipe.llm,NullLLM):
            raise RuntimeError('A real LLM is required for answer evaluation.')
        lexicon=json.loads(Path('eval/local_lexicon.json').read_text())['terms']
        result={'backend':pipe.llm.name,'llm_model':CONFIG.llm_model,'questions':{}}
        for q in qs:
            print('Answering',q['id'],flush=True)
            ans=pipe.answer(q['question']);score=score_answer(q,ans,lexicon)
            result['questions'][str(q['id'])]={**asdict(score),'answer_text':ans.text,'sources':[asdict(s) for s in ans.sources],'warnings':ans.warnings,'unsupported_claims':ans.unsupported_claims}
            save('answers',result)
            print('Completed',q['id'],'groundedness',ans.groundedness,'seconds',ans.elapsed_s,flush=True)
        af,an=regress.check_answers(result,regress._read(regress.BASELINE_ANSWERS),qs)
        save('answer_gate',{'failures':af,'notes':an})
        print('Answer failures:',af,flush=True)
        failed |= bool(af)
    return int(failed)


if __name__=='__main__':raise SystemExit(main())
