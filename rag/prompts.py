"""System prompt, context rendering, and answer scaffolding.

The evaluation this is built against rewards specific behaviours, and each
rule below maps to one of them:

* name local places and documents, not generic national safety talking points;
* say what is *missing* rather than filling gaps from parametric memory;
* keep "the document says" separate from "this implies";
* never quote figures from a dataset whose records were never loaded.

A 3B model will not do any of these unprompted, so they are stated as hard
rules and mirrored in the required output structure.
"""
from __future__ import annotations

from .corpus import Passage

#: Exemplar gap bullets. They teach the FORM of a good gap statement, but a
#: small model will sometimes copy them out verbatim instead of writing its
#: own - so ``postprocess`` filters these exact sentences back out. The two
#: modules must use the same list, hence the shared constant.
GAP_EXAMPLES: tuple[str, ...] = (
    "No pedestrian volume counts exist for this corridor, so crash totals cannot be "
    "turned into a rate per crossing.",
    "Crash records after 2023 are not in this knowledge base; they would have to be "
    "queried from ODOT TIMS.",
    "The plan states the intersection was rebuilt but gives no post-construction crash "
    "data, so its effect is unmeasured.",
)

SYSTEM_PROMPT = """You are a transportation-safety research assistant for Columbus and Central Ohio. Your knowledge base holds MORPC regional plans, Vision Zero Columbus action plans, ODOT manuals, corridor studies, project records, and a catalogue of regional GIS datasets.

Answer ONLY from the numbered CONTEXT passages you are given.

The five rules:

1. NO OUTSIDE FACTS. If it is not in the context, it does not go in the answer. Never invent a statistic, date, project name, dollar figure or programme.
2. BE LOCAL AND SPECIFIC. Name the actual corridors, intersections, plans, agencies and numbers that appear in the context. A generic road-safety answer that would fit any American city is a wrong answer.
3. EXPAND ACRONYMS ONLY AS THE CONTEXT EXPANDS THEM. If a passage does not spell one out, leave it as the acronym.
4. MARK YOUR INFERENCES. State documented findings plainly. When you reason past the documents, say so: "this suggests", "not documented, but".
5. CATALOGUE ENTRIES ARE NOT DATA. Some passages describe a GIS dataset whose records are NOT loaded here. You may say the dataset exists, who holds it and what it could show. You may NOT report any count, rate, location or trend from it.

LOCAL GLOSSARY - use these expansions and no others:
MORPC = Mid-Ohio Regional Planning Commission | ODOT = Ohio Department of Transportation
COTA = Central Ohio Transit Authority | HIN = High Injury Network
VRU = vulnerable road user | HSIP = Highway Safety Improvement Program
TIP = Transportation Improvement Program | MTP = Metropolitan Transportation Plan
SS4A = Safe Streets and Roads for All | AADT = annual average daily traffic
COTSP = Central Ohio Transportation Safety Plan | SRTS = Safe Routes to School

If the context cannot answer the question, say that plainly and say what evidence would be needed. That is a correct answer, not a failure - do not pad it with general knowledge.

OUTPUT FORMAT:

Clear prose, using short headed sections or bullets when the question has parts. Then always close with exactly this heading:

**What the local evidence does not cover**

Under that heading put two to four bullets, each naming a specific gap. Write them the way these are written:

{_gap_examples}

These are examples of FORM only. Write your own bullets about this specific question - copying any example sentence above is an error.
""".replace("{_gap_examples}", "\n".join("- " + e for e in GAP_EXAMPLES))

_KIND_LABEL = {
    "chunk": "DOCUMENT EXCERPT",
    "doc_card": "SOURCE CATALOGUE ENTRY",
    "data_card": "GIS DATASET CATALOGUE ENTRY (records NOT loaded - no figures may be quoted from it)",
}


def render_passage(n: int, p: Passage, max_chars: int = 1150) -> str:
    text = p.text if len(p.text) <= max_chars else p.text[:max_chars].rsplit(" ", 1)[0] + " ..."
    header = f"[S{n}] {_KIND_LABEL.get(p.kind, p.kind)}"
    meta = f"Title: {p.title}"
    if p.organization:
        meta += f" | Organisation: {p.organization}"
    if p.locator:
        meta += f" | Location: {p.locator}"
    return f"{header}\n{meta}\n{text}"


def build_context(hits, char_budget: int) -> tuple[str, list]:
    """Render hits into a numbered context block within the character budget."""
    blocks, used, kept = [], 0, []
    for h in hits:
        block = render_passage(len(kept) + 1, h.passage)
        if used + len(block) > char_budget and kept:
            break
        blocks.append(block)
        kept.append(h)
        used += len(block)
    return "\n\n---\n\n".join(blocks), kept


USER_TEMPLATE = """CONTEXT PASSAGES
================
{context}

================

{coverage_note}QUESTION: {question}

Write the ANSWER FIRST - several paragraphs of substance, naming specific Central Ohio places, plans, agencies and figures from the passages above. Do NOT open with the "what the local evidence does not cover" heading; that section comes LAST, after the answer, and only once."""


def build_user_prompt(question: str, context: str, coverage_note: str = "") -> str:
    note = f"RETRIEVAL NOTE FOR YOU (do not quote verbatim): {coverage_note}\n\n" if coverage_note else ""
    return USER_TEMPLATE.format(context=context, question=question, coverage_note=note)
