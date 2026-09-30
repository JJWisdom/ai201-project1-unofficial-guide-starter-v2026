# The Unofficial Guide

Jeremiah Wisdom — corpus: `campus_life`

---

# Unit 1

## What This Does

The Unofficial Guide answers questions about student life using
`campus_life`, a corpus of 88 short posts covering admin policies, courses,
dining halls, housing, and campus logistics. Ask it something specific —
dining hall wait times, a course's exam format, a policy deadline, a dorm's
laundry price — and it retrieves the post(s) that actually cover it, answers
using only that text, and names the source file. Ask it something the corpus
doesn't cover (or something ambiguous, like a dorm policy question with no
dorm named) and it either refuses outright or hedges across the several
plausible sources, rather than guessing or silently picking one.

## Chunking Strategy

**Chunk size:** 350 characters target, only applied to documents over a 400-character split threshold
**Overlap:** 60 characters (word-boundary-aligned), carried between chunks split from the same document

campus_life is 88 short, single-topic posts averaging 317 characters — most
of them (76 of 88) are already one complete thought and are under the
800-character starter default anyway, which is why the starter's chunker
never split anything on this corpus (88 documents in, 88 chunks out). That's
not a bug, it's the right call for most of these posts: splitting a
three-sentence dining hall review would only shred a sentence for no
retrieval benefit.

The 12 documents that do exceed 400 characters (mostly housing and course
posts) have real internal structure worth cutting along: they're written in
paragraphs organized by sub-topic — an intro, "the good," "the bad," and a
practical facts paragraph (laundry cost, noise) for housing; format,
workload, and one piece of advice for courses. A fixed 800-character window
ignores those breaks entirely. My chunker splits on blank-line paragraph
breaks instead, grouping paragraphs up to 350 characters per chunk, so each
chunk stays one idea instead of a mid-sentence cut.

Two rules keep this from producing garbage: adjacent chunks share 60
characters of trailing context (trimmed to a clean word boundary, not a raw
character slice — an earlier version of this cut mid-word, e.g.
`"ween-two-rooms arrangement..."`, which I caught by reading actual output
and fixed), and any paragraph group under a minimum size gets merged into a
neighbour instead of shipped as a fragment. The floor is derived, not
hard-coded: the length of the shortest whole document in the corpus (178
here), capped at half the chunk size (so 175 at 350). If the corpus treats
that much text as a complete post, no piece cut from a longer one should be
shorter. In practice this floor means only 2 of the 12 eligible documents
(`housing_old_brewhouse.txt`, `housing_innisfree_hall.txt`) actually split
into two chunks; the other 10 have a short trailing paragraph (often the
one-sentence "advice" line) that can't stand alone, so the whole document
stays a single chunk.

The first version of the floor only checked the *last* group. Testing at
chunk_size=250–300 showed that a short first group — a 10-character chunk
containing only a document's title — slipped through, and so did the
occasional short middle group. I originally worked around that by leaving
the chunk size at 350, where it happened not to trigger; it's now fixed in
the code, since every group is checked (a short first group merges forward,
any other merges back). `python tools/check_chunks.py` asserts the
invariants this section claims — no split-produced chunk under the floor,
every chunk carries a source, overlap starts on a word boundary, at least
two campus_life documents split — across chunk sizes 150–500 and all four
shipped corpora, and prints the document counts quoted above straight from
the data.

Result after indexing: 90 chunks from 88 documents, 311 characters average,
shortest 178 (a whole short document, not a fragment), longest
461.

## Sample Chunks

The first three are whole-document chunks (documents under the 400-character
split threshold, left untouched). The last two are both halves of
`housing_old_brewhouse.txt`, chosen deliberately to show what the paragraph
splitter actually does to a document over the threshold — including the
word-boundary-trimmed overlap at the start of chunk 2.

**Chunk 1** — source: `admin_add_drop_deadline.txt#0` — produced by: `chunker.py::split_documents`

```
On the add/drop deadline

You can add a course through the end of the second week. Dropping is a longer window — through the end of week six — but a drop after week two shows as a W on your transcript. Nothing anywhere on the registrar's site says this plainly, and students find out from each other.
```

**Chunk 2** — source: `course_math_220_exams.txt#0` — produced by: `chunker.py::split_documents`

```
MATH 220 Linear Algebra — assessment

Two midterms and a cumulative final. Curved to a b- median.

The problem sets are the course; the lectures make sense afterwards rather than during.
```

**Chunk 3** — source: `dining_the_ridgeway_cafe.txt#0` — produced by: `chunker.py::split_documents`

```
The Ridgeway Café

Second-year here. Wait times: 10 to 15 minutes at 12:30, none after 2:00. The thing worth going for is the only place on campus with real espresso. The thing to know is that seating is tight; about 40 seats for a building of 900.

Hours are 7:00am to 4:00pm weekdays only. Costs declining balance only, no meal swipes.
```

**Chunk 4** — source: `housing_old_brewhouse.txt#0` — produced by: `chunker.py::split_documents`

```
Old Brewhouse — what it's actually like

Took this last spring. Built 1902 as a brewery, converted to housing in 1998. Rooms are doubles and triples with unusual floor plans, no two alike.

The good: the most characterful building on campus and people get attached to it.
```

**Chunk 5** — source: `housing_old_brewhouse.txt#1` — produced by: `chunker.py::split_documents`

```
building on campus and people get attached to it.

The bad: the heating is uneven — some rooms run hot all winter and can't be adjusted.

Laundry costs $1.50 wash, $1.50 dry, coin only, and the machines are old. On noise: sound carries strangely because of the original brick; a room two floors up can be louder than next door.
```

## Sample Answer

**Question:** When is the wait longest at Pellew Dining Hall?

**Answer:**

```
  (best distance 0.175, cutoff 0.6)

The peak wait time at Pellew Dining Hall is early, specifically from 11:45 to 12:30.

Source: dining_pellew_dining_hall.txt

Sources retrieved: dining_halden_hall_followup.txt, dining_kestrel_commons_followup.txt, dining_pellew_dining_hall.txt, dining_pellew_dining_hall_followup.txt, dining_the_ridgeway_cafe_followup.txt
```

Worth noting: the retrieved context also contained wait-time and hours data
for four *other* dining halls (Halden, Kestrel Commons, Ridgeway Café), since
"wait" and "peak" language is similar across all the dining posts. The answer
still stayed scoped to Pellew and cited the correct file — checked with
`--show-prompt`, which is how I confirmed the grounding instruction
(`generate.py:276`) holds up even when the context has several
easily-confused near-duplicates in it, not just the right one.

**My relevance cutoff:** 0.6 (the starter default — kept, not changed)

I measured best-distance for all 5 of my in-scope questions and all 5
`OUT_OF_SCOPE` questions using `app.py retrieve` (no model calls), against
the index built with my own chunker. The two groups don't overlap at all:
in-scope tops out at 0.425, out-of-scope bottoms out at 0.825 — a gap of
exactly 0.4. 0.6 sits roughly in the middle of that gap, so I left it where
the starter set it rather than moving it for the sake of moving it.

| Question | In corpus? | Best distance |
|---|---|---|
| What are the University Health Center's walk-in hours? | Yes | 0.316 |
| When is the wait longest at Pellew Dining Hall? | Yes | 0.175 |
| How many pages per semester can an undergraduate print? | Yes | 0.321 |
| How often does the campus shuttle run on weekdays? | Yes | 0.425 |
| Is laundry free in the dorms? | Yes | 0.330 |
| What is the capital of Mongolia? | No | 0.825 |
| How do I change the oil in a diesel engine? | No | 0.934 |
| Who won the 1994 World Cup? | No | 0.886 |
| What is the recommended dosage of ibuprofen for a headache? | No | 0.844 |
| How do I write a for loop in Rust? | No | 0.896 |

## How I Used AI

**1.** I asked Claude to write a paragraph-aware chunker for `chunker.py::split_documents`, based on what I'd read in Milestone 1: most campus_life posts are short and already one complete thought, but the longer housing/course posts have real paragraph structure ("the good" / "the bad" / a practical-facts paragraph) worth splitting on instead of the fixed 800-character window. The first version worked at the default settings, but when I asked it to test smaller chunk-size values to see if more documents would split, it surfaced its own bug: at chunk_size=250-300, some documents produced a 10-character chunk containing nothing but a document's title, because the floor rule only protected the *last* paragraph group, not an isolated first one. It also caught a second bug on inspection of real output — the overlap between split chunks was slicing at a fixed character count with no regard for word boundaries, producing chunks that started mid-word (`"ween-two-rooms arrangement..."` instead of `"between-two-rooms"`). I had it fix the overlap to trim to the nearest word boundary and initially kept the chunk-size at 350, where the floor rule doesn't hit the title-fragment bug on this corpus. After review feedback pointed out that this was a config workaround for a code bug, I had it fix the floor to check every group, derive the floor from the corpus instead of hard-coding 178, and add `tools/check_chunks.py` so the invariants are asserted at every chunk size rather than remembered.

**2.** Before finalizing my five test questions, I asked Claude to pressure-test them by actually running each one through the live pipeline rather than reasoning about them abstractly. Two of my five had a real problem it caught this way: my health center question asked for "weekday hours" expecting an opening-closing range, but the source document only ever states walk-in hours (8am-11am) — there's no closing time anywhere in it, so no correct answer could ever have matched what I'd written for `expects`. Similarly, my Pellew dining hall question asked for "hours," which the live system correctly answered with the operating hours (7am-8pm) — not the peak wait-time window (11:45-12:30) I actually meant for `expects` to check. I reworded both questions to ask for the specific fact I actually wanted, then reran them live to confirm the new wording retrieved cleanly and the answer matched the updated `expects` phrase before writing anything into `questions.py`.

**3. (Unit 2)** After designing my plan for this unit — score against my
unit 1 criteria as written, fix the scoring rules before the first run, and
make one improvement chosen from the diagnosis — I used Claude as an
assistant to revise and audit my ideas and the evidence. It turned my
scoring rules into code (`scorer.py`, `tools/score_run.py`), ran both
evals, drafted the verdicts and diagnoses for me to review, and checked
each step against the unit's requirements. Three things its auditing caught
are worth recording, because each would have made the evidence wrong:

- **A corrupted index.** Its first retrieval check showed best distances
  near 0.9 for every question, against the 0.175–0.425 in `criteria.md`.
  The cause: the staff smoke test (`tools/smoke_test.py`), run while
  verifying the unit 1 chunker fix, had rebuilt the real `campus_life`
  index with its fake stand-in embeddings. It rebuilt the index with
  `app.py index` and confirmed all ten distances matched the unit 1
  measurements exactly before running the baseline.
- **A scorer parser bug.** The first scoring pass reported 1 of 5 answers
  naming a source. Reading the raw answers showed all 15 did. The parser
  had read only run 1. It fixed the parser and changed no rules, which is
  documented in commit `6f1c717`.
- **The laundry pattern.** Looking at the top 15 for the laundry question,
  it spotted the near-duplicate crowding: a hall review's split-off laundry
  paragraph and that hall's laundry post, taking two of the five slots each.

It also argued the opposite verdict against my calls on each close
criterion (Milestone 2's check). That's how the "three halls presented as
all of them" gap got into the criterion 5 verdict instead of being passed
over.

**Stretch features:** None attempted in unit 1. Unit 2: none. The second
improvement, the grounding-prompt change, is written up under What's
Still Broken but not made.

---

# Unit 2

<!-- These sections get ADDED to what's already above. Don't delete or rewrite
     unit 1 — the point is that someone can see what you said before you knew
     how it went. -->

## Run Log — Before

Raw evidence: [results/run_2026-09-30_0001_before.md](results/run_2026-09-30_0001_before.md),
produced by `run_eval.py::main` with `python run_eval.py --label before`
(caching off, 15 real model calls, top-k 5, cutoff 0.6). The table below
is `python tools/score_run.py results/run_2026-09-30_0001_before.md`.

**How it's scored.** The scoring rules were committed (`scorer.py`,
`tools/score_run.py`, commit `6572350`) before this run existed. The rule
for each criterion:

- **1.** A retrieved chunk contains the `expects` phrase, after normalising
  times and ranges. For the laundry question, the chunks must include
  laundry prices from at least two halls.
- **2.** The answer names a corpus filename. A refusal counts as a fail.
- **3.** Read from the gate table in the results file.
- **4.** For run N, a random sample of 5 chunks from the index (seed N). A
  chunk passes if it starts where a sentence starts and ends on
  sentence-final punctuation. Also checked: no chunk from a split document
  is under 178 characters, and at least two documents split.
- **5.** The laundry answer names at least two halls, or asks which one.

Criteria 1, 3 and 4 don't involve the model, so they can't vary between
runs. Retrieval is deterministic and the gate is a comparison against a
fixed number, so criteria 1 and 3 repeat the same number in all three
columns. Criterion 4 draws a different sample of chunks each run. The
identical columns aren't a cache artifact: the 15 answers were generated
separately, and their wording differs (see below).

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunks contain the answer | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 2. Every answer names a source | 5 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 3. Gate stops out-of-corpus questions | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 4. Sampled chunks are complete thoughts, none under 178 chars, ≥2 docs split | 4 of 5, all parts | 5/5 | 5/5 | 4/5 | MET |
| 5. Laundry answer doesn't silently pick one hall | 1 of 1 | 1/1 | 1/1 | 1/1 | MET |

**Real output, criterion by criterion.** All answers below come from
`run_eval.py::run_once`, which calls `generate.py::answer_from_chunks`
after retrieval with `store.py::search`.

**Criterion 1.** Deterministic retrieval, from `tools/score_run.py`:

```
✓ What are the University Health Center's walk-in hours? — found in health_center.txt#0
✓ When is the wait longest at Pellew Dining Hall? — found in dining_pellew_dining_hall.txt#0, dining_the_ridgeway_cafe_followup.txt#0
✓ How many pages per semester can an undergraduate print? — found in admin_printing_quota.txt#0
✓ How often does the campus shuttle run on weekdays? — found in transit_shuttle.txt#0
✓ Is laundry free in the dorms? — laundry chunks from 3 hall(s): Aldridge Hall, Innisfree Hall, Old Brewhouse
```

**Criterion 2.** Run 1 answer to the printing question:

```
Every student gets $30 of printing per semester, which is roughly 600 black-and-white pages (admin_printing_quota.txt).
```

Run 2 answer to the walk-in hours question:

```
The University Health Center's walk-in hours are from 8am to 11am. 

Source: health_center.txt
```

**Criterion 3.** From `run_eval.py::check_out_of_scope`:

```
refused  (best distance 0.825)  What is the capital of Mongolia?
refused  (best distance 0.934)  How do I change the oil in a diesel engine?
refused  (best distance 0.886)  Who won the 1994 World Cup?
refused  (best distance 0.844)  What is the recommended dosage of ibuprofen for a headache?
refused  (best distance 0.896)  How do I write a for loop in Rust?
-> gate refused 5 of 5
```

**Criterion 4.** Run 3 sample, from `tools/score_run.py`. The chunks were
produced by `chunker.py::split_documents`.

```
documents split: 2 (housing_innisfree_hall.txt, housing_old_brewhouse.txt)
split-produced chunks under 178: none
run 3: course_engl_205_exams.txt#0, housing_old_brewhouse.txt#0, housing_innisfree_hall.txt#1, advising_registration.txt#0, dining_kestrel_commons_followup.txt#0; cut at an edge: housing_innisfree_hall.txt#1
```

The chunk that failed, `housing_innisfree_hall.txt#1`, starts mid-sentence:

```
arrangement is the best compromise on campus.

The bad: no air conditioning, which matters for the first three weeks of September.

Laundry costs $1.75 wash, $1.75 dry, app-based. On noise: moderate; the building is L-shaped and the short wing is much quieter.
```

For comparison, a chunk that passed, `admin_printing_quota.txt#0`:

```
On the printing quota

Every student gets $30 of printing per semester, which is roughly 600 black-and-white pages. It does not roll over. Colour costs eight times as much per page, which people discover after printing one poster.
```

**Criterion 5.** Run 1 answer to the laundry question:

```
Based on the documents, laundry is not free. 

- In Innisfree Hall, it costs $1.75 for a wash and $1.75 for a dry (`housing_innisfree_hall.txt`).
- In Old Brewhouse, it costs $1.50 for a wash and $1.50 for a dry (`housing_old_brewhouse.txt`).
- In Aldridge Hall, it costs $1.75 for a wash and $1.50 for a dry (`housing_aldridge_hall_laundry.txt`).
```

## Verdicts

| # | Criterion | Verdict | How I decided |
|---|---|---|---|
| 1 | Retrieved chunks contain the answer (4 of 5) | MET | All five questions retrieved a chunk with the answer (5/5, above the 4-of-5 target). Retrieval is deterministic, so all three runs show the same 5/5. |
| 2 | Every answer names a source (5 of 5) | MET | All 15 answers name a filename. None was refused, so none failed on that rule either. The format drifts (inline parentheses, a "Source:" line, backticks, italics), but every one names the file. |
| 3 | Gate stops out-of-corpus questions (4 of 5) | MET | 5 of 5 refused. The closest one (0.825) is still 0.225 above the 0.6 cutoff, so this isn't close. |
| 4 | Chunk quality (4 of 5, and all parts) | MET, and this was the closest call | Run 3 scored 4/5, exactly at the target: `housing_innisfree_hall.txt#1` opens mid-sentence ("arrangement is the best compromise…"). The other two parts are also right at their bar: exactly 2 documents split, against a target of at least two. Each part holds, but none with any margin. |
| 5 | Laundry answer doesn't pick one hall (1 of 1) | MET | All three answers list three halls, with prices and sources, which is exactly what the criterion asks for. The strongest case for MISSED: all three answers open with "laundry is not free" as a blanket fact about the dorms, when they cover only 3 of the 7 halls. That's the failure this criterion was meant to catch, just with three halls instead of one. I kept MET because the criterion as written says "list at least two hall-specific policies with sources", and moving the bar after seeing results is what the rules say not to do. The gap is picked up in the diagnosis below. |

## Diagnoses

<!-- For each miss: which stage caused it, and how. The stage alone isn't
     enough — you need the mechanism.

     Not a diagnosis: "Question 3 didn't work."
     A diagnosis:     "Question 3 asks about laundry costs. The answer is in
                       one sentence that got split across two chunks, so
                       neither chunk on its own contains it."

     The five stages: loading → chunking → embedding → retrieval → generation.

     Look for a pattern. If three misses all ask about numbers, that's one
     problem, not three.

     Missed nothing? Say so, then say honestly whether your targets were set
     low, and which one you'd tighten and to what.

     Milestone 3. -->

**I missed nothing, and at least three of my five targets were set low.**
Clearing all five on the first try says more about the targets than about
the system:

- **Criterion 3 was the safest.** I wrote in `criteria.md` that 4 of 5 was
  "a conservative floor" given a 0.4 distance gap. My five out-of-scope
  questions (Mongolia, diesel engines, Rust) are so far from a campus corpus
  that no reasonable cutoff could fail them. **Tighten to:** 5 of 5, on five
  questions that sound like they belong but aren't covered. For example:
  "What's the tuition at State?", "When does the city library close?", "Is
  there a dress code for the career fair?" Those would test whether 0.6 is
  in the right place, not just whether it's below 0.8.
- **Criterion 1 was loose because it counts any of the top 5.** I checked a
  stricter version against the same run: "the *top* chunk contains the
  answer" scores **3 of 5**, which misses. On the Pellew question the top
  chunk is `dining_pellew_dining_hall_followup.txt#0` (distance 0.175). It
  says "go before 11:45" but never gives the 12:30 end. On the laundry
  question the top chunk covers one hall. **Tighten to:** at least 4 of 5
  with the answer in the top 1, or 5 of 5 in the top 3.
- **Criterion 5 measured the letter of what I wanted, not the point.** I
  wanted "don't present part of the answer as the whole answer." I wrote
  "list at least two halls," and the system passed by listing three of
  seven while claiming "laundry is not free" for all of them. **Tighten
  to:** the answer either covers every hall or says it only covers some.

**What the runs did show: two weak spots, one mechanism.** No criterion
missed, but two results came in at the edge of a target, and both come
from the same place. Splitting two housing reviews
(`housing_innisfree_hall.txt`, `housing_old_brewhouse.txt`) produced a
second-half chunk that, in both cases, holds the review's laundry-and-noise
paragraph.

1. **Chunking caused the near-miss on criterion 4.** The overlap carried
   into chunk #1 is trimmed to a *word* boundary (the unit 1 fix), but not
   to a *sentence* boundary. So `housing_innisfree_hall.txt#1` opens with
   "arrangement is the best compromise on campus.", the tail of a sentence
   whose start is in chunk #0. The overlap copies the last 60 characters
   and drops the leading partial word. 60 characters almost never lines up
   with the start of a sentence, so every split-produced chunk after the
   first opens mid-sentence. Run 3's sample happened to include one.
2. **Retrieval caused the laundry gap on criterion 5, and generation
   stretched it.** Those second-half chunks are just the laundry-and-noise
   paragraphs, so they repeat the dedicated `housing_*_laundry.txt`
   documents. For "Is laundry free in the dorms?" they rank #1 and #2
   (0.330, 0.371), and the matching laundry documents rank #3 and #4. With
   top-k = 5, those near-duplicates fill four of the five slots, covering
   just two halls. Aldridge takes the fifth. The other four halls' laundry
   documents are close behind at ranks 7–10 (0.517–0.550, all well inside
   the 0.6 cutoff) and never reach the model:

   ```
   0.330 housing_innisfree_hall.txt#1         ← retrieved (top 5)
   0.371 housing_old_brewhouse.txt#1          ← retrieved
   0.427 housing_innisfree_hall_laundry.txt#0 ← retrieved, same hall again
   0.442 housing_old_brewhouse_laundry.txt#0  ← retrieved, same hall again
   0.479 housing_aldridge_hall_laundry.txt#0  ← retrieved
   0.512 housing_aldridge_hall.txt#0
   0.517 housing_fenwick_court_laundry.txt#0  ← never seen
   0.521 housing_morrow_house_laundry.txt#0   ← never seen (the cheapest hall)
   0.544 housing_calder_annexe_laundry.txt#0  ← never seen
   0.550 housing_tamsin_court_laundry.txt#0   ← never seen (in-unit washer-dryer)
   ```

   The model then generalises from what it was given: "laundry is not
   free", about all the dorms. The four halls it never saw include Tamsin
   Court, whose laundry is an in-unit washer-dryer with no per-load price,
   the one hall where the blanket claim is unsupported. The model did what
   its prompt asked (answer from the documents given). The documents it was
   given were three halls' worth of a seven-hall answer.

The pattern: in a corpus where each hall has both a review and a dedicated
laundry post, retrieval by closest meaning fills the top 5 with
near-duplicates. Any question whose correct answer is spread across many
documents gets a partial answer that reads as complete. Laundry is the only
test question of that kind. The noise and dining questions have the same
shape, since there are seven noise posts and several dining posts.

## The Improvement

**What I changed:** `TOP_K` in `config.py`, from 5 to 10. That's the only
change. The chunker, index, prompt, gate cutoff and model are the same as
in the before run.

**Why I picked it:** Diagnosis 2 found near-duplicate chunks filling the
top 5 for the laundry question, so the model only ever saw 3 of the 7
halls. At top-k = 10, all seven halls' laundry posts are retrieved (ranks
3–10 in the table above). I chose this over diagnosis 1, the overlap
starting mid-sentence, because the laundry gap produces a wrong claim for
the user. The overlap problem is a cosmetic flaw in two chunks.

**How I measured the targeted failure.** None of the five criteria counts
halls, because criterion 5 passes at two. So alongside the criteria, I
counted how many of the 7 halls the laundry answer covers, using
`tools/score_run.py`'s "halls named" line on both result files. I did
**not** change criterion 5.

### Run Log — After

Raw evidence: [results/run_2026-09-30_0004_after.md](results/run_2026-09-30_0004_after.md)
(`python run_eval.py --label after`, caching off, 15 real model calls,
top-k 10, cutoff 0.6), scored by `tools/score_run.py`.

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunks contain the answer | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 2. Every answer names a source | 5 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 3. Gate stops out-of-corpus questions | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 4. Sampled chunks are complete thoughts, none under 178 chars, ≥2 docs split | 4 of 5, all parts | 5/5 | 5/5 | 4/5 | MET |
| 5. Laundry answer doesn't silently pick one hall | 1 of 1 | 1/1 | 1/1 | 1/1 | MET |

**Side by side, including what the change was aimed at:**

| Measure | Before (top-k 5) | After (top-k 10) |
|---|---|---|
| Criteria met | 5 of 5 | 5 of 5 (unchanged) |
| Halls whose laundry chunks were **retrieved** | 3 of 7 | **7 of 7** |
| Halls **named in the laundry answer**, runs 1 / 2 / 3 | 3 / 3 / 3 | **2 / 6 / 3** |
| Laundry answers opening with a blanket "laundry is not free" | 3 of 3 | 3 of 3 |
| Laundry answers mentioning Tamsin Court (in-unit, no per-load price) | 0 of 3 | 0 of 3 |
| Input tokens for the 15 calls | 9,555 | 17,001 (+78%) |

Real output, laundry question, run 1 after. It covers fewer halls than
any before run, even though all seven were in its context:

```
Based on the provided documents, laundry is not free. Each dorm has specific costs for washing and drying (for example, $1.75 to wash and $1.75 to dry in Innisfree Hall, and $1.50 to wash and $1.50 to dry in Old Brewhouse). 

Sources: `housing_innisfree_hall.txt` and `housing_old_brewhouse.txt`
```

Run 2 after, the best answer either run log produced (six halls, each
with its source):

```
Based on the documents, laundry is not free. It costs varying amounts depending on the building, such as $1.75 for a wash and $1.75 for a dry in Innisfree Hall (`housing_innisfree_hall.txt`), $1.50 for a wash and $1.50 for a dry in Old Brewhouse (`housing_old_brewhouse.txt`), $1.75 for a wash and $1.50 for a dry in Aldridge Hall (`housing_aldridge_hall.txt`), $2.00 for a wash and $1.75 for a dry in Fenwick Court (`housing_fenwick_court_laundry.txt`), $1.50 for a wash and $1.25 for a dry in Morrow House (`housing_morrow_house_laundry.txt`), and $2.00 for a wash and $1.75 for a dry in Calder Annexe (`housing_calder_annexe_laundry.txt`).
```

**Did it help?** It fixed the stage it was aimed at, but not the failure.
Retrieval went from 3 to 7 of 7 halls, which the retrieval ranking shows
directly. The answer went from a steady 3 halls to 2, 6 and 3. That averages
slightly higher (3.7 against 3.0), but the answers are less consistent,
and one run is worse than every before run. All three answers still open
with the unsupported blanket claim, and none mentions Tamsin Court. None
of the five criteria moved, and input tokens went up 78%. I know which stage
is left because the evidence is in the context in every after run: all
seven halls reach the model, and the model picks examples from them. The
bottleneck has moved from **retrieval to generation**. The grounding
prompt says "Be brief. Two or three sentences is usually enough", which
pushes the model to summarise with a couple of examples ("such as…") rather
than enumerate. I'm keeping the change, because any generation-side fix
needs all seven halls in the context to work with. On its own, it did not
make the laundry answer reliably complete.

**A measurement error, reported rather than fixed after the fact.**
`run_eval.py`'s per-question columns in the after file show the health
centre question as "fail" in runs 1 and 2. Those answers say "8:00 am to
11:00 am", which is correct. `scorer.py`'s normaliser doesn't treat ":00"
as optional, so it misses them. None of the five criteria is scored from
that column, and the before run didn't phrase the time that way, so no
verdict changes. I left the rule as committed rather than editing it after
seeing results. The fix is to strip ":00" in `scorer.normalise`.

## What's Still Broken

<!-- For each criterion still missed after your fix: what you'd do about it,
     and why you stopped where you did.

     "I ran out of time" is fine if it's true. Pretending nothing is left is
     not.

     Milestone 5. -->

No criterion is missed, before or after. But "all five met" isn't
"nothing broken". These are the problems the runs found that my criteria
were too loose to catch:

1. **The laundry answer is still incomplete, and it overstates.** This is a
   generation-stage problem. With all seven halls now retrieved, the model
   still names 2–6 of them, still opens with "laundry is not free" for every
   dorm, and never mentions Tamsin Court's in-unit washer-dryer. **Next:**
   change the grounding prompt (`generate.py::GROUNDING_INSTRUCTION`). When
   the documents give different values per building, list every building,
   or say explicitly which ones the answer covers. The "Be brief" rule would
   need an exception for that case. **Why I stopped:** this unit allows one
   change, and I used it on top-k. The prompt change would be a second
   improvement, and I'd measure it the same way: the halls-named count and
   the blanket-claim count across three runs.
2. **Chunks after the first in a split document start mid-sentence.** This
   is the chunking stage. The overlap is trimmed to a word boundary but not
   a sentence boundary, so `housing_innisfree_hall.txt#1` opens
   "arrangement is the best compromise on campus." **Next:** start the
   overlap tail at the first sentence boundary inside it, or drop it if
   there isn't one. **Why I stopped:** it affects the 2 split-off chunks out
   of 90, and it cost criterion 4 one sampled chunk in one run. The laundry
   problem gives users wrong answers; this one doesn't.
3. **The scorer's ":00" false negative.** "8:00 am" isn't matched to "8am",
   so the per-question column in the after file shows two false fails for
   the health centre question. **Next:** make ":00" optional in
   `scorer.normalise`. **Why I stopped:** it changes no verdict, and editing
   a scoring rule after seeing the results it scores is exactly the thing
   this unit says not to do. I'd fix it before the next unit's baseline, not
   inside this one.
4. **The test set has only one question whose answer is spread across
   documents.** The near-duplicate crowding in diagnosis 2 should also hit
   noise (seven `housing_*_noise.txt` posts) and cross-hall dining
   questions, but I have no test question that would show it.

## What I'd Do Differently

Three of my five criteria passed because of how I wrote them, not because
of the system:

- **Criterion 1**, "the retrieved chunks include one that contains the
  answer", counts any of the top 5 (now 10). I'd write "the top-ranked
  chunk contains the answer for at least 4 of 5". Scored against the same
  before run, that version gives 3 of 5 and misses, on Pellew and laundry.
  A criterion that can catch the Pellew near-miss is worth more than one
  that can't.
- **Criterion 3's** out-of-scope questions (Mongolia, diesel engines, Rust)
  are too far from the corpus to test the cutoff. I'd keep 4 of 5, but use
  questions that sound like campus life and aren't covered, so the gate has
  to separate close from not-quite.
- **Criterion 5** should have said what I meant: "the answer covers every
  hall, or says which halls it covers". "At least two halls" passed an
  answer that claims something about all seven halls from three of them.
- **Criterion 4's** sample is too easy. 86 of 90 chunks are whole documents,
  which pass the complete-thought check by construction. I'd sample only
  from chunks produced by splitting, since those are the chunks my chunker
  actually made decisions about.

I'd also write down scoring rules like `scorer.py`'s *as part of* each
criterion in unit 1. Several judgment calls, like what counts as "the
answer" for the laundry question and whether a refusal counts as naming a
source, had to be made in unit 2, before the run but after the criteria.
They belonged next to the targets.
