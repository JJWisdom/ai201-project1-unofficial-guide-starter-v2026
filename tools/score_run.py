#!/usr/bin/env python3
"""
Turn one run_eval.py results file into the per-criterion run log.

    python tools/score_run.py results/run_<stamp>_before.md

run_eval.py writes one row per QUESTION. The README's run log is one row per
CRITERION (see criteria.md). This reads the committed results file — the
answers exactly as they were produced, not a fresh generation — and applies
the rules below, which were written before the first run:

1. Retrieved chunks contain the answer. Re-runs retrieval for each question
   against the same index variant and top-k the file names (retrieval is
   deterministic, so this is the same retrieval the run saw) and checks the
   chunk texts with scorer.contains_expected. For the laundry question, the
   chunks must include laundry arrangements from at least two halls. Same
   number in every run column, because retrieval doesn't vary.
2. Every answer names a source. An answer passes if it names at least one
   corpus filename (with or without ".txt"). A refusal names no source, so
   an in-scope question refused — by the gate or by the model — fails.
3. Gate refuses out-of-corpus questions. Read straight from the file's gate
   table. One deterministic pass, so the same number in every column.
4. Chunk quality. For run N, a random sample of 5 chunks (seed N) from the
   index. A chunk is a complete thought if it starts where a sentence starts
   in its document and ends on sentence-final punctuation or at the end of
   its document. Also checked: no chunk from a split document under 178
   characters, and at least two documents split. All three parts must hold.
5. Laundry question hedges. The laundry answer passes if it names at least
   two halls or asks which hall is meant. 1 of 1 per run.

A criterion is MET only if its target holds in all three runs.
"""

import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
import questions as qs  # noqa: E402
from ingest import load_documents  # noqa: E402
from scorer import VARIES, contains_expected, halls_named  # noqa: E402

FLOOR = 178          # criteria.md, criterion 4 — the target as written
LAUNDRY = "Is laundry free in the dorms?"


def parse(path: Path):
    text = path.read_text(encoding="utf-8")
    variant = re.search(r"index variant `([^`]+)`", text).group(1)
    corpus = re.search(r"Corpus: `([^`]+)`", text).group(1)
    top_k = int(re.search(r"top-k: (\d+)", text).group(1))

    gate = re.findall(r"^\| (.+?) \| ([\d.]+) \| (refused|\*\*let through\*\*) \|$", text, re.M)

    runs = {}
    for m in re.finditer(
        r"^### (.+?) — run (\d+)\n\n- Best distance: .*\n- Sources retrieved: .*\n\n```\n(.*?)\n```",
        text, re.M | re.S,
    ):
        runs.setdefault(int(m.group(2)), {})[m.group(1)] = m.group(3)
    return corpus, variant, top_k, gate, runs


def names_source(answer: str, filenames: set[str]) -> bool:
    lowered = answer.lower()
    return any(name in lowered or name.removesuffix(".txt") in lowered for name in filenames)


def complete_thought(chunk: str, doc: str) -> bool:
    at = doc.find(chunk[:40])
    if at < 0:
        return False
    before = doc[:at].rstrip()
    starts_clean = at == 0 or before == "" or before[-1] in ".!?\n" or doc[at - 1] == "\n"
    end = at + len(chunk)
    ends_clean = chunk.rstrip()[-1] in ".!?\"')" or doc[end:].strip() == ""
    return starts_clean and ends_clean


def index_chunks(corpus: str, variant: str):
    from store import _client

    got = _client().get_collection(config.collection_name(corpus, variant)).get()
    return sorted(
        ({"id": i, "text": t, "source": m["source"], "index": m["index"]}
         for i, t, m in zip(got["ids"], got["documents"], got["metadatas"])),
        key=lambda c: c["id"],
    )


def main(path: Path):
    from store import search

    corpus, variant, top_k, gate, runs = parse(path)
    docs = {d.source: d.text for d in load_documents(corpus)}
    filenames = {name.lower() for name in docs}
    items = qs.answered()
    n_runs = sorted(runs)

    # 1 — deterministic retrieval
    c1_detail = []
    for item in items:
        results = search(item["question"], top_k=top_k, corpus=corpus, variant=variant)
        if item["expects"] == VARIES:
            halls = set()
            for r in results:
                if "laundry" in r.text.lower():
                    halls |= halls_named(r.source.replace("_", " "))
            hit = len(halls) >= 2
            why = f"laundry chunks from {len(halls)} hall(s): {', '.join(sorted(halls)) or '-'}"
        else:
            found = [r.label for r in results if contains_expected(item["expects"], r.text)]
            hit = bool(found)
            why = f"found in {', '.join(found)}" if found else "not in any retrieved chunk"
        c1_detail.append((item["question"], hit, why))
    c1 = sum(hit for _, hit, _ in c1_detail)

    # 2, 5 — from the answers actually produced
    c2 = {}
    c2_detail = {}
    c5 = {}
    for n in n_runs:
        misses = [q for q, a in runs[n].items() if not names_source(a, filenames)]
        c2[n] = len(runs[n]) - len(misses)
        c2_detail[n] = misses
        c5[n] = int(contains_expected(VARIES, runs[n].get(LAUNDRY, "")))

    # 3 — deterministic gate
    c3 = sum(verdict == "refused" for _, _, verdict in gate)

    # 4 — chunk sample per run, plus the two whole-index checks
    chunks = index_chunks(corpus, variant)
    split_sources = {c["source"] for c in chunks if c["index"] > 0}
    short = [c["id"] for c in chunks if c["source"] in split_sources and len(c["text"]) < FLOOR]
    c4 = {}
    c4_detail = {}
    for n in n_runs:
        sample = random.Random(n).sample(chunks, 5)
        bad = [c["id"] for c in sample if not complete_thought(c["text"], docs[c["source"]])]
        c4[n] = 5 - len(bad)
        c4_detail[n] = ([c["id"] for c in sample], bad)
    c4_ok = {n: c4[n] >= 4 and not short and len(split_sources) >= 2 for n in n_runs}

    def row(name, target, cells, met):
        cols = " | ".join(cells)
        return f"| {name} | {target} | {cols} | {'MET' if met else 'MISSED'} |"

    head = " | ".join(f"Run {n}" for n in n_runs)
    print(f"Scored from `{path.as_posix()}` by `tools/score_run.py`\n")
    print(f"| Criterion | Target | {head} | Verdict |")
    print("|---|---|" + "---|" * len(n_runs) + "---|")
    print(row("1. Retrieved chunks contain the answer", "4 of 5",
              [f"{c1}/5"] * len(n_runs), c1 >= 4))
    print(row("2. Every answer names a source", "5 of 5",
              [f"{c2[n]}/5" for n in n_runs], all(c2[n] == 5 for n in n_runs)))
    print(row("3. Gate refuses out-of-corpus questions", "4 of 5",
              [f"{c3}/{len(gate)}"] * len(n_runs), c3 >= 4))
    print(row("4. Sampled chunks are complete thoughts (+ floor, + 2 splits)",
              "4 of 5, all parts",
              [f"{c4[n]}/5{'' if c4_ok[n] else ' ✗'}" for n in n_runs],
              all(c4_ok.values())))
    print(row("5. Laundry answer doesn't silently pick one hall", "1 of 1",
              [f"{c5[n]}/1" for n in n_runs], all(c5.values())))

    print("\nDetail")
    print("\n1. Retrieved chunks (same every run):")
    for q, hit, why in c1_detail:
        print(f"   {'✓' if hit else '✗'} {q} — {why}")
    print("\n2. Answers with no source named:")
    for n in n_runs:
        print(f"   run {n}: {', '.join(c2_detail[n]) or 'none'}")
    print("\n3. Gate:")
    for q, d, v in gate:
        print(f"   {v.strip('*')} ({d}) {q}")
    print("\n4. Chunk samples:")
    print(f"   documents split: {len(split_sources)} ({', '.join(sorted(split_sources))})")
    print(f"   split-produced chunks under {FLOOR}: {', '.join(short) or 'none'}")
    for n in n_runs:
        sample, bad = c4_detail[n]
        print(f"   run {n}: {', '.join(sample)}; cut at an edge: {', '.join(bad) or 'none'}")
    print("\n5. Laundry answer halls named:")
    for n in n_runs:
        named = halls_named(runs[n].get(LAUNDRY, ""))
        print(f"   run {n}: {', '.join(sorted(named)) or 'none'}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python tools/score_run.py results/<file>.md")
    main(Path(sys.argv[1]))
