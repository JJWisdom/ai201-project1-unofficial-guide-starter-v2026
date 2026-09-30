"""
Scoring rules for unit 2, written before the first `run_eval.py` run.

`run_eval.py` finds `judge` automatically and uses it to fill the per-question
Run columns: did this answer contain the expected answer? The criterion-level
run log (one row per criterion) is built from the same rules by
`tools/score_run.py`, which also covers the criteria that aren't about answer
correctness.

The rules, fixed here so they can't drift after I've seen results:

- **Matching an `expects` string.** Both sides are normalised (lowercase,
  "a.m."/"p.m." collapsed to "am"/"pm", dashes and "to"/"until" treated as the
  same separator, whitespace removed), then `expects` is split on its range
  separator and *every* part has to appear. "8am to 11am" passes on
  "8 a.m.–11 a.m." but not on "8am" alone.
- **The laundry question** (`expects` "varies by hall") has no single string.
  It passes if the text names at least two different halls, or asks which
  hall is meant. Used for the answer (criteria 5) and, for retrieved chunks,
  criterion 1 requires chunks from at least two halls that state a laundry
  arrangement.
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


def normalise(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\b([ap])\.m\.?", r"\1m", text)
    text = re.sub(r"\s*(–|—|-|\bto\b|\buntil\b|\bthrough\b)\s*", "~", text)
    return re.sub(r"\s+", "", text)


def contains_expected(expects: str, text: str) -> bool:
    """Every part of `expects` appears in `text`, after normalising both."""
    if expects == VARIES:
        return len(halls_named(text)) >= 2 or bool(_CLARIFY.search(text))
    haystack = normalise(text)
    return all(part in haystack for part in normalise(expects).split("~") if part)


def halls_named(text: str) -> set[str]:
    lowered = text.lower()
    return {name for key, name in HALLS.items() if key in lowered}


def judge(question: str, expects: str, answer: str, results) -> bool:
    """Called by run_eval.py once per question per run."""
    return contains_expected(expects, answer)
