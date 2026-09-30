"""
Stage 2 of the pipeline: splitting documents into chunks.

⚠️ THIS IS THE FILE YOU CHANGE IN MILESTONE 3.

`split_documents` below is deliberately plain. It cuts every document into
fixed-size pieces with a fixed overlap and pays no attention to where sentences
or paragraphs end. It works, and it is not good.

On a corpus of short posts it may not cut anything at all: `campus_life` comes
out as 88 documents and 88 chunks, because almost nothing in it reaches 800
characters. That is the baseline, not a bug — Milestone 3 is where you decide
whether one post should stay one chunk.

Your job in Milestone 3 is to replace the *body* of `split_documents` with a
strategy that fits the documents you actually read in Milestone 1. Keep the
name and the shape of what it returns — the rest of the pipeline calls it, and
your README has to name the function that produced your chunks.

If you get stuck for 30 minutes, `fallback_split` is the original. Switch back
to it, write down what you saw, and move on. That's a real observation about
your pipeline, not giving up.
"""

import re
from dataclasses import dataclass

import config
from ingest import Document


@dataclass
class Chunk:
    """One piece of one document."""

    text: str
    source: str        # which file it came from
    index: int         # which chunk within that file, starting at 0
    produced_by: str   # the function that made it — cite this in your README

    @property
    def label(self) -> str:
        return f"{self.source}#{self.index}"


def fallback_split(
    documents: list[Document],
    chunk_size: int | None = None,
    overlap: int | None = None,
) -> list[Chunk]:
    """
    The starter's original chunker. Fixed-size character windows with overlap.

    Keep this function. Milestone 3's stop rule points back at it, and having
    something to compare your own strategy against is useful in unit 2.
    """
    chunk_size = chunk_size or config.CHUNK_SIZE
    overlap = overlap or config.CHUNK_OVERLAP

    if overlap >= chunk_size:
        raise ValueError("overlap has to be smaller than chunk_size")

    chunks: list[Chunk] = []
    for doc in documents:
        start = 0
        index = 0
        while start < len(doc.text):
            piece = doc.text[start : start + chunk_size].strip()
            if piece:
                chunks.append(
                    Chunk(
                        text=piece,
                        source=doc.source,
                        index=index,
                        produced_by="chunker.py::fallback_split",
                    )
                )
                index += 1
            start += chunk_size - overlap

    return chunks


def split_documents(
    documents: list[Document],
    chunk_size: int | None = None,
    overlap: int | None = None,
    min_chunk: int | None = None,
) -> list[Chunk]:
    """
    Paragraph-aware chunker, built for campus_life's short single-topic posts.

    Most documents here are short and already read as one complete thought,
    so any document at or under SPLIT_THRESHOLD stays a single chunk
    untouched — splitting it would only shred a sentence for no benefit.
    (For the actual counts, run `python tools/check_chunks.py`; they're
    printed from the data rather than written here, where they'd go stale.)
    The documents over the threshold are the ones worth cutting, and they
    have real internal structure to cut along: paragraphs are already
    organised by sub-topic ("the good" / "the bad" / a laundry-and-noise
    paragraph; or format / workload / advice for course posts). Splitting on
    those blank-line breaks keeps each chunk to one idea, instead of the
    fallback's fixed-size window, which pays no attention to where a sentence
    ends.

    Paragraphs are grouped up to CHUNK_SIZE characters per chunk. Adjacent
    chunks share CHUNK_OVERLAP characters of trailing context, so a fact
    stated right at a paragraph boundary isn't lost to whichever chunk didn't
    get it. Any group under the minimum chunk size — a bare title at the
    start, a one-sentence "advice" paragraph at the end, or a short paragraph
    stranded in between — gets merged into a neighbour rather than shipped as
    a fragment nobody could answer a question from alone.

    The minimum is derived from the documents passed in (see
    `min_chunk_size`), so the floor tracks the corpus instead of being a
    hand-copied number.
    """
    chunk_size = chunk_size or config.CHUNK_SIZE
    overlap = overlap or config.CHUNK_OVERLAP
    min_chunk = min_chunk or min_chunk_size(documents, chunk_size)
    split_threshold = config.SPLIT_THRESHOLD

    chunks: list[Chunk] = []
    for doc in documents:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", doc.text) if p.strip()]

        if len(doc.text) <= split_threshold or len(paragraphs) <= 1:
            chunks.append(
                Chunk(
                    text=doc.text,
                    source=doc.source,
                    index=0,
                    produced_by="chunker.py::split_documents",
                )
            )
            continue

        groups: list[str] = []
        current = ""
        for para in paragraphs:
            candidate = f"{current}\n\n{para}" if current else para
            if len(candidate) > chunk_size and current:
                groups.append(current)
                current = para
            else:
                current = candidate
        if current:
            groups.append(current)

        # A short group reads as a fragment rather than a complete thought,
        # wherever it sits. Checking only the last group let a bare title
        # through as chunk 0 whenever CHUNK_SIZE was small enough to cut
        # right after it, so check every group: a short first group merges
        # forward, any other merges back.
        i = 0
        while len(groups) > 1 and i < len(groups):
            if len(groups[i]) >= min_chunk:
                i += 1
            elif i == 0:
                groups[0:2] = [f"{groups[0]}\n\n{groups[1]}"]
            else:
                groups[i - 1 : i + 1] = [f"{groups[i - 1]}\n\n{groups[i]}"]
                i -= 1

        for i, group in enumerate(groups):
            if i > 0:
                tail = groups[i - 1][-overlap:]
                # The slice above almost always lands mid-word. Drop the
                # partial leading word so overlap starts clean.
                if " " in tail:
                    tail = tail.split(" ", 1)[1]
                group = f"{tail.strip()}\n\n{group}"
            chunks.append(
                Chunk(
                    text=group.strip(),
                    source=doc.source,
                    index=i,
                    produced_by="chunker.py::split_documents",
                )
            )

    return chunks


def min_chunk_size(documents: list[Document], chunk_size: int | None = None) -> int:
    """
    The floor for a split-produced chunk.

    config.MIN_CHUNK_SIZE wins if set. Otherwise it's the length of the
    shortest whole document — if the corpus itself treats that much text as a
    complete post, no piece cut from a longer post should be shorter — capped
    at half of chunk_size. Without the cap, a corpus of long documents
    (city_guides' shortest is over 1400 characters) gets a floor no group can
    reach, and nothing splits at all.
    """
    if config.MIN_CHUNK_SIZE:
        return config.MIN_CHUNK_SIZE
    chunk_size = chunk_size or config.CHUNK_SIZE
    shortest = min((len(d.text) for d in documents), default=0)
    return min(shortest, chunk_size // 2)


def describe(chunks: list[Chunk]) -> str:
    """A one-line summary, printed after indexing."""
    if not chunks:
        return "0 chunks"
    lengths = [len(c.text) for c in chunks]
    return (
        f"{len(chunks)} chunks, "
        f"{sum(lengths) // len(lengths)} characters on average "
        f"(shortest {min(lengths)}, longest {max(lengths)}), "
        f"produced by {chunks[0].produced_by}"
    )


if __name__ == "__main__":
    from ingest import load_documents

    chunks = split_documents(load_documents())
    print(describe(chunks))
