#!/usr/bin/env python3
"""
Assertion checks for chunker.py::split_documents.

    python tools/check_chunks.py

The README makes claims about what the chunker produces — no split-produced
chunk under the floor, every chunk carries a source, overlap starts on a word
boundary, at least two campus_life documents actually split. This checks them
instead of trusting prose, and it checks them at a sweep of CHUNK_SIZE values
and against every shipped corpus, because the title-fragment bug only showed
up away from the default settings.

It prints the corpus numbers the docs used to hard-code, so when you need them,
copy them from here rather than from a comment that may have drifted.
Exits non-zero on the first failing sweep, listing every violation found.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
from chunker import Chunk, min_chunk_size, split_documents  # noqa: E402
from ingest import Document, load_documents  # noqa: E402

CORPORA = ["campus_life", "advice_threads", "city_guides", "practice"]
CHUNK_SIZES = range(150, 501, 25)


def violations(docs: list[Document], chunks: list[Chunk], floor: int) -> list[str]:
    """Every invariant split_documents promises, as a list of what broke."""
    problems = []
    by_source: dict[str, list[Chunk]] = {}
    for c in chunks:
        if not (c.source and c.produced_by):
            problems.append(f"{c.label}: missing source or produced_by")
        if not c.text.strip():
            problems.append(f"{c.label}: empty")
        by_source.setdefault(c.source, []).append(c)

    for doc in docs:
        own = by_source.get(doc.source, [])
        if not own:
            problems.append(f"{doc.source}: produced no chunks")
            continue
        if [c.index for c in own] != list(range(len(own))):
            problems.append(f"{doc.source}: indices not 0..n-1")
        if len(doc.text) <= config.SPLIT_THRESHOLD and len(own) != 1:
            problems.append(f"{doc.source}: under threshold but split")
        if len(own) < 2:
            continue
        for c in own:
            if len(c.text) < floor:
                problems.append(f"{c.label}: {len(c.text)} chars, under floor {floor}")
            # Overlap is trimmed to a word boundary, so each chunk should start
            # where a word starts in the original document.
            head = c.text[:20]
            at = doc.text.find(head)
            if at > 0 and not doc.text[at - 1].isspace():
                problems.append(f"{c.label}: starts mid-word ({head!r})")
    return problems


def main() -> int:
    failed = False
    for corpus in CORPORA:
        docs = load_documents(corpus)
        floor = min_chunk_size(docs)
        short = sum(len(d.text) <= config.SPLIT_THRESHOLD for d in docs)
        print(
            f"\n{corpus}: {len(docs)} documents, {short} at or under "
            f"SPLIT_THRESHOLD={config.SPLIT_THRESHOLD}, "
            f"{len(docs) - short} over it, floor {floor} at CHUNK_SIZE={config.CHUNK_SIZE}"
        )

        for size in CHUNK_SIZES:
            chunks = split_documents(docs, chunk_size=size)
            problems = violations(docs, chunks, min_chunk_size(docs, size))
            if problems:
                failed = True
                print(f"  FAIL chunk_size={size}:")
                for p in problems:
                    print(f"    {p}")

        chunks = split_documents(docs)
        split = sorted({c.source for c in chunks if c.index > 0})
        print(
            f"  at CHUNK_SIZE={config.CHUNK_SIZE}: {len(chunks)} chunks, "
            f"{len(split)} documents split: {', '.join(split) or '-'}"
        )
        if corpus == "campus_life" and len(split) < 2:
            failed = True
            print("  FAIL: README says at least two campus_life documents split")

    print("\nFAILED" if failed else "\nall checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
