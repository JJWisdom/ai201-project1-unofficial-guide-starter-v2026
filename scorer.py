"""
Scoring rules for unit 2. I wrote these before the first run_eval.py run.

run_eval.py finds `judge` on its own and uses it to fill in the per-question
Run columns, meaning did this answer contain the expected answer. The
per-criterion run log in the README is built from the same rules by
tools/score_run.py, which also covers the criteria that are not about
whether an answer was right.

The rules are fixed here so they cannot drift after I have seen results.

- Matching an `expects` string. Both sides get normalized first. That means
  lowercase, "a.m." and "p.m." collapsed to "am" and "pm", dashes and the
  words "to" or "until" treated as the same separator, and whitespace
  removed. Then `expects` is split on that separator and every part has to
  show up. "8am to 11am" passes on "8 a.m. to 11 a.m." but not on "8am"
  alone.

- The laundry question has no single right string. Its `expects` is
  "varies by hall". It passes if the text names at least two different
  halls, or asks which hall is meant. Criterion 5 uses this on the answer.
  Criterion 1 uses it on the retrieved chunks, where it needs laundry
  chunks from at least two halls.
"""

import re

HALLS = {
    "aldridge": "Aldridge Hall",
    "calder": "Calder Annexe",
    "fenwick": "Fenwick Court",
    "innisfree": "Innisfree Hall",
    "morrow": "Morrow House",
    "brewhouse": "Old Brewhouse",
    "tamsin": "Tamsin Court",
}

VARIES = "varies by hall"
_CLARIFY = re.compile(r"which (hall|dorm|residence|building)", re.I)


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\b([ap])\.m\.?", r"\1m", text)
    text = re.sub(r"\s*(–|—|-|\bto\b|\buntil\b|\bthrough\b)\s*", "~", text)
    return re.sub(r"\s+", "", text)


def contains_expected(expects: str, text: str) -> bool:
    """True if every part of `expects` shows up in `text` once both are normalized."""
    if expects == VARIES:
        return len(halls_named(text)) >= 2 or bool(_CLARIFY.search(text))
    haystack = normalize(text)
    return all(part in haystack for part in normalize(expects).split("~") if part)


def halls_named(text: str) -> set[str]:
    lowered = text.lower()
    return {name for key, name in HALLS.items() if key in lowered}


def judge(question: str, expects: str, answer: str, results) -> bool:
    """run_eval.py calls this once per question, per run."""
    return contains_expected(expects, answer)
