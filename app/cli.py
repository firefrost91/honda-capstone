"""Interactive terminal chat.

    python -m app.cli                      # chat
    python -m app.cli -q "your question"   # one-shot
"""
from __future__ import annotations

import argparse
import sys

from rag.config import CONFIG
from rag.pipeline import RAGPipeline
from rag.tools import STAKEHOLDERS

BANNER = """
  Columbus / Central Ohio Transportation Safety - local RAG
  ---------------------------------------------------------
  Grounded in MORPC plans, Vision Zero Columbus, ODOT manuals,
  corridor studies and the regional GIS data catalogue.

  /sources   show every retrieved passage, not just the cited ones
  /why       show the sub-queries used for the last question
  /k <n>     change how many passages are retrieved (now {k})
  /as <id>   answer from a stakeholder's perspective (/as none to auto-detect)
  /who       list the stakeholder perspectives and their metric tools
  /quit      exit
"""


def _print_answer(answer, show_all: bool) -> None:
    print("\n" + answer.render(show_all_sources=show_all) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Columbus transportation-safety RAG chat")
    ap.add_argument("-q", "--question", help="ask one question and exit")
    ap.add_argument("--all-sources", action="store_true",
                    help="always list retrieved passages, not only cited ones")
    ap.add_argument("--no-stream", action="store_true", help="wait for the full answer")
    ap.add_argument("-s", "--stakeholder", choices=sorted(STAKEHOLDERS), default=None,
                    help="frame the answer for this stakeholder (default: detect from the question)")
    args = ap.parse_args()

    pipeline = RAGPipeline()

    if args.question:
        _print_answer(pipeline.answer(args.question, stakeholder=args.stakeholder),
                      args.all_sources)
        return 0

    print(BANNER.format(k=CONFIG.final_k))
    print(f"  backend: {pipeline.llm.name} ({CONFIG.llm_model if pipeline.llm.name=='mlx' else ''})"
          f" | {len(pipeline.index.passages)} passages indexed")
    if not pipeline.llm.available:
        print("  NOTE: no language model available - answers will be extractive.\n")

    k, last, who = CONFIG.final_k, None, args.stakeholder
    while True:
        try:
            q = input("\nask> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not q:
            continue
        if q in {"/quit", "/exit", "/q"}:
            return 0
        if q == "/sources":
            if last:
                print("\n".join("  " + s.format() for s in last.sources))
            continue
        if q == "/why":
            if last:
                print("  retrieval sub-queries:")
                print("\n".join(f"    - {s}" for s in last.subqueries))
            continue
        if q == "/who":
            for s in STAKEHOLDERS.values():
                print(f"  {s.id:<10} {s.name}  [{', '.join(s.tools)}]")
            print(f"  current: {who or 'auto-detect'}")
            continue
        if q.startswith("/as"):
            arg = q[3:].strip()
            if arg in STAKEHOLDERS:
                who = arg
                print(f"  answering for {STAKEHOLDERS[who].name}")
            elif arg in {"", "none", "auto"}:
                who = None
                print("  stakeholder auto-detected from each question")
            else:
                print("  usage: /as <" + "|".join(STAKEHOLDERS) + "|none>")
            continue
        if q.startswith("/k "):
            try:
                k = int(q.split()[1])
                print(f"  retrieving {k} passages")
            except (ValueError, IndexError):
                print("  usage: /k 14")
            continue

        if args.no_stream:
            last = pipeline.answer(q, k=k, stakeholder=who)
            _print_answer(last, args.all_sources)
        else:
            print()
            for kind, payload in pipeline.stream(q, k=k, stakeholder=who):
                if kind == "token":
                    sys.stdout.write(payload)
                    sys.stdout.flush()
                elif kind == "answer":
                    last = payload
            # Streamed text is pre-attribution; reprint the verified version.
            print("\n\n--- verified answer ---")
            _print_answer(last, args.all_sources)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
