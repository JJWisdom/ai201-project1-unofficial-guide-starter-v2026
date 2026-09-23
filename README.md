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
of them (73 of 88) are already one complete thought and are under the
800-character starter default anyway, which is why the starter's chunker
never split anything on this corpus (88 documents in, 88 chunks out). That's
not a bug, it's the right call for most of these posts: splitting a
three-sentence dining hall review would only shred a sentence for no
retrieval benefit.

The 15 documents that do exceed 400 characters (mostly housing and course
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
and fixed), and any trailing paragraph group under 178 characters — the
length of the shortest whole document in this corpus — gets folded back into
the previous chunk instead of shipped as a fragment. In practice this floor
means only 2 of the 15 eligible documents (`housing_old_brewhouse.txt`,
`housing_innisfree_hall.txt`) actually split into two chunks; the other 13
have a short trailing paragraph (often the one-sentence "advice" line) that
can't stand alone, so the whole document stays a single chunk. I considered
lowering the floor to force more documents to split, but tested it directly
(`chunker.py` at chunk_size=250–300) and found it reintroduces the exact
problem the floor exists to prevent — a 10-character chunk containing only a
document's title, with nothing else in it. I kept the floor and accepted
that most long documents in this corpus don't have a clean second half to
split off, rather than force a split that produces a worse chunk than no
split at all.

Result after indexing: 90 chunks from 88 documents, 311 characters average,
shortest 178 (a whole short document, at the floor, not a fragment), longest
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

**1.** I asked Claude to write a paragraph-aware chunker for `chunker.py::split_documents`, based on what I'd read in Milestone 1: most campus_life posts are short and already one complete thought, but the longer housing/course posts have real paragraph structure ("the good" / "the bad" / a practical-facts paragraph) worth splitting on instead of the fixed 800-character window. The first version worked at the default settings, but when I asked it to test smaller chunk-size values to see if more documents would split, it surfaced its own bug: at chunk_size=250-300, some documents produced a 10-character chunk containing nothing but a document's title, because the floor rule only protected the *last* paragraph group, not an isolated first one. It also caught a second bug on inspection of real output — the overlap between split chunks was slicing at a fixed character count with no regard for word boundaries, producing chunks that started mid-word (`"ween-two-rooms arrangement..."` instead of `"between-two-rooms"`). I had it fix the overlap to trim to the nearest word boundary and kept the chunk-size at 350, where the floor rule doesn't hit the title-fragment bug on this corpus.

**2.** Before finalizing my five test questions, I asked Claude to pressure-test them by actually running each one through the live pipeline rather than reasoning about them abstractly. Two of my five had a real problem it caught this way: my health center question asked for "weekday hours" expecting an opening-closing range, but the source document only ever states walk-in hours (8am-11am) — there's no closing time anywhere in it, so no correct answer could ever have matched what I'd written for `expects`. Similarly, my Pellew dining hall question asked for "hours," which the live system correctly answered with the operating hours (7am-8pm) — not the peak wait-time window (11:45-12:30) I actually meant for `expects` to check. I reworded both questions to ask for the specific fact I actually wanted, then reran them live to confirm the new wording retrieved cleanly and the answer matched the updated `expects` phrase before writing anything into `questions.py`.

**Stretch features:** None attempted this unit.

---

# Unit 2

<!-- These sections get ADDED to what's already above. Don't delete or rewrite
     unit 1 — the point is that someone can see what you said before you knew
     how it went. -->

## Run Log — Before

<!-- Your five criteria, three runs each. `python run_eval.py --label before`
     runs the questions, puts the OUT_OF_SCOPE ones through the gate, and
     writes it all into results/ for you. Targets come from criteria.md; the
     verdict column is your call.

     Criterion 3 is measured in one deterministic pass rather than three, so
     the same number goes in all three run columns. That's correct, not lazy.

     Milestone 1. -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 |  |  |  |  |
| 2. Every answer names a source | 5 of 5 |  |  |  |  |
| 3. Gate stops out-of-corpus questions | 4 of 5 |  |  |  |  |
| 4. | | | | | |
| 5. | | | | | |

<!-- Underneath, paste the REAL output for each criterion from one of your
     runs — the actual text your system produced, not a description of it.
     Name the file and function that produced it. -->

## Verdicts

<!-- MET or MISSED for each of the five, against the target you wrote last
     unit — not a new one. Plus a sentence on how you decided. That sentence
     matters most where it was close.

     If your target said 4 of 5 and your runs came out 4, 3, 4, that's a MISS.
     The target has to hold, not show up occasionally.

     Milestone 2. -->

| # | Criterion | Verdict | How I decided |
|---|---|---|---|
| 1 |  |  |  |
| 2 |  |  |  |
| 3 |  |  |  |
| 4 |  |  |  |
| 5 |  |  |  |

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

## The Improvement

**What I changed:**

**Why I picked it:**

<!-- Connect it to a specific diagnosis above in one sentence. If you can't,
     you picked a fix because it sounded impressive. -->

### Run Log — After

<!-- Same format, same five criteria, three runs each.
     `python run_eval.py --label after` -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 |  |  |  |  |
| 2. Every answer names a source | 5 of 5 |  |  |  |  |
| 3. Gate stops out-of-corpus questions | 4 of 5 |  |  |  |  |
| 4. | | | | | |
| 5. | | | | | |

**Did it help?**

<!-- Say plainly whether it did, and how you know. If it made things worse,
     say that — a change that backfired, honestly reported, earns full credit
     and is more interesting than one that worked. What matters is that you can
     tell.

     Milestone 4. -->

## What's Still Broken

<!-- For each criterion still missed after your fix: what you'd do about it,
     and why you stopped where you did.

     "I ran out of time" is fine if it's true. Pretending nothing is left is
     not.

     Milestone 5. -->

## What I'd Do Differently

<!-- Knowing what you know now — which of your five criteria would you write
     differently, and why?

     Milestone 5. -->
