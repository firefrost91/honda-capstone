"""Clean raw model output before it is attributed and shown.

Small instruct models leak their own instructions. Observed failure modes that
each of the functions below exists to repair:

* the "2-4 bullets naming concretely what is missing" template line is copied
  out as if it were content;
* the closing gap section is emitted twice, sometimes before the answer;
* generation stops mid-sentence at the token cap;
* markdown headings from a source passage bleed into the prose.
"""
from __future__ import annotations

import re

GAP_HEADING = "**What the local evidence does not cover**"
_GAP_RE = re.compile(r"\*\*\s*What the local evidence does not cover\s*\*\*", re.I)

#: Lines that are the instruction, not an answer.
_TEMPLATE_ECHO = re.compile(
    r"^\s*[-*]?\s*(2-4 bullets|Name the specific data and where it lives"
    r"|Clear prose, using short headed|not \"more data is needed\""
    r"|naming concretely what is missing)", re.I)

#: "[**SOME HEADING**, S6]" style bleed from a passage's own formatting.
_HEADING_BLEED = re.compile(r"^\s*\[\s*\*\*[^\]]*\*\*\s*,?\s*S?\d*\s*\]\s*", re.M)


def _strip_template_echo(text: str) -> str:
    return "\n".join(l for l in text.split("\n") if not _TEMPLATE_ECHO.match(l))


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", s.lower()).strip()


def _is_echoed_example(bullet: str) -> bool:
    """True if the bullet is one of the prompt's exemplars, copied verbatim."""
    from .prompts import GAP_EXAMPLES
    b = _norm(bullet.lstrip("-*• "))
    return any(_norm(ex) in b or b in _norm(ex) for ex in GAP_EXAMPLES if b)


#: A bullet is "- x", "* x" or "• x". Crucially NOT "**bold**" - a naive
#: startswith("*") test treats the gap heading itself as a bullet, which
#: swallows the second heading into the first group and merges the two.
_BULLET = re.compile(r"(?:[-•]|\*(?!\*))\s+\S")


def _is_bullet(line: str) -> bool:
    return bool(_BULLET.match(line.strip()))


def _dedupe_gap_section(text: str) -> str:
    """Keep exactly one gap section, at the end, without eating the answer.

    A gap section is the heading plus the run of bullets under it - nothing
    more. Splitting on the heading and treating everything after it as "the
    section" loses the whole answer whenever the model emits the heading
    first, which it does regularly.
    """
    lines = text.split("\n")
    body: list[str] = []
    groups: list[list[str]] = []
    i = 0
    while i < len(lines):
        if _GAP_RE.search(lines[i]):
            i += 1
            bullets: list[str] = []
            # consume blank lines and bullets; the first prose line ends it
            while i < len(lines) and (not lines[i].strip() or _is_bullet(lines[i])):
                if _is_bullet(lines[i]):
                    bullets.append(lines[i].rstrip())
                i += 1
            groups.append(bullets)
            continue
        body.append(lines[i])
        i += 1

    body_text = "\n".join(body).strip()
    groups = [[b for b in g if not _is_echoed_example(b)] for g in groups]
    groups = [g for g in groups if g]
    if not groups:
        return body_text
    best = max(groups, key=len)
    return f"{body_text}\n\n{GAP_HEADING}\n" + "\n".join(best)


def _mark_truncation(text: str) -> tuple[str, bool]:
    stripped = text.rstrip()
    if not stripped:
        return text, False
    # A dangling citation or a line with no terminal punctuation means the
    # token budget ran out mid-thought.
    if re.search(r"\[S\d*$", stripped) or not re.search(r"[.!?)\]*]\s*$", stripped):
        stripped = re.sub(r"\s*\[S\d*$", "", stripped)
        stripped = stripped.rsplit("\n", 1)[0] if "\n" in stripped else stripped
        return stripped.rstrip() + "\n\n[answer truncated at the generation limit]", True
    return stripped, False


def clean(text: str) -> tuple[str, list[str]]:
    warnings: list[str] = []
    original = text

    text = _HEADING_BLEED.sub("", text)
    text = _strip_template_echo(text)
    if _TEMPLATE_ECHO.search(original) :
        warnings.append("removed echoed prompt-template text from the answer")

    n_sections = len(_GAP_RE.findall(text))
    text = _dedupe_gap_section(text)
    if n_sections > 1:
        warnings.append("merged duplicated 'what the evidence does not cover' sections")

    text, truncated = _mark_truncation(text)
    if truncated:
        warnings.append("generation hit the token limit and was trimmed to the last "
                        "complete sentence")

    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"(?<=\S)[ \t]{2,}(?=\S)", " ", text)
    text = re.sub(r"\bThe\s+document\b", "The source document", text)
    return text.strip(), warnings
