# Acceptance criteria — The Unofficial Guide

Five criteria that say what "working" means for this system, written in unit 1
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"Retrieval works"* is an opinion. *"For at
least 4 of my 5 test questions, the top results include a chunk containing the
answer"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter or looser one. A reason that says something about your corpus or your
pipeline earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

---

## 1. Retrieved chunks contain the answer

For at least 4 of my 5 test questions, the retrieved chunks include one that
contains the answer.

**Why this target:**
Questions 1-4 are specific and should retrieve cleanly, while question 5
("Is laundry free in the dorms?") is intentionally ambiguous — there are five
housing halls, each with its own laundry doc and its own price, so there is
no single best-match chunk. I confirmed this with `app.py retrieve`: the
laundry question returns four plausible-but-different docs with close,
non-dominant distances (0.43 / 0.44 / 0.47 / 0.48), unlike the other four
questions which each have one clear best match well under 0.43. A target of
5 of 5 would mean removing the hard case entirely; 3 of 5 would mean two
clean questions failed, which is too weak a bar.

---

## 2. Every answer names a source

Every answer the system produces names at least one source document.

**Why this target:**
This isn't enforced by code — it's a line in the system prompt
(`generate.py:281`, "Name the document your answer came from"), so it's a
model-compliance target, not a guarantee. For only five questions, 100%
compliance is realistic and I'd rather keep the bar at "every answer" and
treat any omission as a real bug to investigate than water the criterion
down to 4 of 5 and lose the ability to say "every answer" at all.

---

## 3. The relevance gate stops out-of-corpus questions

When I ask a question my documents clearly don't cover, the relevance gate
stops it and the system returns "I don't have enough information about that" —
in at least 4 of 5 tries.

<!-- The five questions are the ones in `OUT_OF_SCOPE` at the bottom of
     `questions.py`, and `run_eval.py` puts them through the gate and writes
     what happened into your run log. Swap them for your own if you'd rather —
     just keep five of them, or the "4 of 5" above has nothing to be 4 of. -->

**Why this target:**
I measured this before tuning anything, using `app.py retrieve` (no model
calls). Best distances for my 5 in-scope questions run 0.175-0.427. Best
distances for the 5 `OUT_OF_SCOPE` questions run 0.82-0.93. That's a clean
gap of nearly 0.4 with no overlap, so any cutoff placed between roughly 0.5
and 0.8 should catch all five out-of-scope questions. 4 of 5 is a
conservative floor given how wide that gap is, not a stretch target — if one
fails in practice, that's a sign to inspect the cutoff or look for an
embedding anomaly rather than a sign the target was wrong. 3 of 5 would be
too low given how clean the separation actually is.

---

## 4. Something about your chunks

At least 4 of 5 sampled chunks are complete thoughts, with no sentence cut
off at either edge, and no split-produced chunk is shorter than 178
characters (the length of the shortest whole document in this corpus)
unless its source document is itself under 178 characters. My chunker must
also split at least two documents over 400 characters into two or more
chunks — proving it does something other than the starter's "one document
equals one chunk" behavior.

**Why this target:**
The starter's 800-character chunker never split anything on this corpus:
88 documents in, 88 chunks out, because every document (avg 317 characters,
longest 549) is under its 800-character threshold. That's the baseline my
own chunker has to actually differ from. The 178-character floor is
data-driven, not arbitrary — it's the shortest whole document in the
corpus, so no fragment my chunker produces should read as less complete
than the shortest real post already does. I picked 4 of 5 and not 5 of 5
because chunking is heuristic — one paragraph or sentence boundary can
reasonably fail — but 4 of 5 still proves the chunker is producing complete,
non-fragment chunks rather than getting lucky once. 15 of my 88 documents
are over 400 characters, so the split requirement has real room to be
tested against.

---

## 5. Your choice

On the laundry question ("Is laundry free in the dorms?"), the system must
not silently pick one hall and answer as if that's the whole story. It must
either ask which hall the user means, or list at least two hall-specific
policies with sources. I'll score this 1 of 1 — pass or fail, no partial
credit.

**Why this target:**
This corpus has five separate laundry docs with five different prices, so
there is no single correct chunk for a hall-unspecified question — there's
only a correct set of chunks. A system that silently picks one hall's price
and presents it as *the* answer is confidently wrong in a way that's harder
to catch than an obvious refusal, because it sounds grounded and cites a
real source. Asking for clarification or naming multiple halls is the
honest behavior for this exact failure mode, and it's a binary I can check
by reading one answer, which is why 1 of 1 is the right shape here rather
than a fraction across several questions.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 2 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 1. Retrieved chunks contain the answer

         For at least 4 of my 5 test questions, the retrieved chunks include
         one that contains the answer.

         **Why this target:** ...

         > **Revised in unit 2:** For at least 4 of 5 questions, the top three
         > results contain the answer.
         >
         > **Why revised:** I couldn't judge "the chunks include one that
         > contains the answer" the same way twice — I scored two questions
         > differently on Monday than on Wednesday. The new version is
         > something I can actually check.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said 4 of 5 but got 2 of 5, so 2 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.

     The whole reason the originals stay visible is so someone can see what you
     said before you knew the answer.
     ───────────────────────────────────────────────────────────────────────── -->
