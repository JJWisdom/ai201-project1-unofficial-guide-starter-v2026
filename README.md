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
neighbor instead of shipped as a fragment. The floor is not hard-coded. It
is the length of the shortest whole document in the corpus, which is 178
here, capped at half the chunk size, so 175 at 350. If the corpus treats
that much text as a complete post, no piece cut from a longer one should be
shorter than it. In practice this floor means only 2 of the 12 eligible
documents actually split into two chunks, `housing_old_brewhouse.txt` and
`housing_innisfree_hall.txt`. The other 10 end on a short paragraph, usually
the one line "advice" paragraph, that cannot stand on its own, so the whole
document stays a single chunk.

The first version of the floor only checked the last group. Testing at
chunk sizes of 250 to 300 showed a short first group getting through, a
10 character chunk with nothing in it but the document's title. A short
group in the middle got through sometimes too. My first answer was to leave
the chunk size at 350, where the bug happened not to trigger. That was a
config workaround for a code bug. It is fixed in the code now. Every group
gets checked, a short first group merges forward, and any other short group
merges back. `python tools/check_chunks.py` checks the claims in this
section. No chunk from a split document is under the floor, every chunk
carries a source, the overlap starts on a word boundary, and at least two
campus_life documents split. It runs those checks at chunk sizes from 150 to
500 against all four corpora in the repo, and it prints the document counts
above straight from the data.

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

**1.** I asked Claude to write a paragraph-aware chunker for `chunker.py::split_documents`, based on what I'd read in Milestone 1: most campus_life posts are short and already one complete thought, but the longer housing/course posts have real paragraph structure ("the good" / "the bad" / a practical-facts paragraph) worth splitting on instead of the fixed 800-character window. The first version worked at the default settings, but when I asked it to test smaller chunk-size values to see if more documents would split, it surfaced its own bug: at chunk_size=250-300, some documents produced a 10-character chunk containing nothing but a document's title, because the floor rule only protected the *last* paragraph group, not an isolated first one. It also caught a second bug on inspection of real output — the overlap between split chunks was slicing at a fixed character count with no regard for word boundaries, producing chunks that started mid-word (`"ween-two-rooms arrangement..."` instead of `"between-two-rooms"`). I had it fix the overlap to trim to the nearest word boundary and initially kept the chunk-size at 350, where the floor rule doesn't hit the title-fragment bug on this corpus. Review feedback pointed out that this was a config workaround for a code bug, and it was. I had it fix the floor so every group gets checked, work the floor out from the corpus instead of hard-coding 178, and add `tools/check_chunks.py` so those checks run at every chunk size instead of relying on me to remember them.

**2.** Before finalizing my five test questions, I asked Claude to pressure-test them by actually running each one through the live pipeline rather than reasoning about them abstractly. Two of my five had a real problem it caught this way: my health center question asked for "weekday hours" expecting an opening-closing range, but the source document only ever states walk-in hours (8am-11am) — there's no closing time anywhere in it, so no correct answer could ever have matched what I'd written for `expects`. Similarly, my Pellew dining hall question asked for "hours," which the live system correctly answered with the operating hours (7am-8pm) — not the peak wait-time window (11:45-12:30) I actually meant for `expects` to check. I reworded both questions to ask for the specific fact I actually wanted, then reran them live to confirm the new wording retrieved cleanly and the answer matched the updated `expects` phrase before writing anything into `questions.py`.

**3. (Unit 2)** I designed the plan for this unit first. Score against my unit 1 criteria exactly as written, lock the scoring rules in before the first run, and make one improvement that comes out of the diagnosis. After that I used Claude as the assistant that revised and audited my ideas and the evidence. It turned my scoring rules into code (`scorer.py` and `tools/score_run.py`), ran the evals, drafted the verdicts and diagnoses for me to review, and checked each step against the unit requirements. Three things it caught are worth writing down, because each one would have made the evidence wrong.

- A corrupted index. The first retrieval check came back with best distances near 0.9 on every question, when `criteria.md` has them between 0.175 and 0.425. Claude had run the staff smoke test, `tools/smoke_test.py`, while checking the unit 1 chunker fix, and that test rebuilt the real `campus_life` index with its fake embeddings. It rebuilt the index with `app.py index` and confirmed all ten distances matched my unit 1 numbers exactly before the baseline ran.
- A parser bug in the scorer. The first scoring pass said only 1 of 5 answers named a source. Reading the raw answers showed all 15 did. The parser was only reading run 1. It fixed the parser without changing any of the rules, and that fix is its own commit, `6f1c717`.
- The laundry pattern. Pulling the top 15 results for the laundry question is how the near duplicate problem showed up. A hall review's laundry paragraph and that same hall's laundry post were taking two of the five slots each.

It also argued the opposite verdict against my call on every close criterion, which is the Milestone 2 check. That is how the gap in criterion 5, three halls presented as if they were all of them, ended up in the verdict instead of getting skipped over.

**Stretch features:** None in unit 1. Unit 2: a second measured improvement, a change to the grounding prompt. It is declared in "Second Improvement (Stretch)" below before any of it was built.

---

# Unit 2

## Run Log - Before

The raw file is [results/run_2026-09-30_0001_before.md](results/run_2026-09-30_0001_before.md). It came from `run_eval.py::main`, run as `python run_eval.py --label before`, with caching off, 15 real model calls, top-k 5, and the cutoff at 0.6. The table is the output of `python tools/score_run.py results/run_2026-09-30_0001_before.md`.

### How I scored it

I wrote the scoring rules as code and committed them before this run existed. That is `scorer.py` and `tools/score_run.py`, commit `6572350`. One rule per criterion:

- Criterion 1. A retrieved chunk contains the `expects` phrase once times and ranges are normalized. For the laundry question the chunks need laundry prices from at least two halls.
- Criterion 2. The answer names a corpus filename. A refusal counts as a fail.
- Criterion 3. Read from the gate table in the results file.
- Criterion 4. For run N, a random sample of 5 chunks from the index, seeded with N. A chunk passes if it starts where a sentence starts and ends on a period, question mark, or exclamation point. On top of that, no chunk from a split document can be under 178 characters, and at least two documents have to split.
- Criterion 5. The laundry answer names at least two halls, or asks which hall is meant.

Criteria 1, 3, and 4 never touch the model, so they cannot move between runs. Retrieval is deterministic and the gate is a comparison against a fixed number, so criteria 1 and 3 have the same number in all three columns. Criterion 4 draws a new sample each run. The matching columns are not a cache problem. The 15 answers were generated separately and the wording changes from run to run, which shows in the output below.

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunks contain the answer | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 2. Every answer names a source | 5 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 3. Gate stops out-of-corpus questions | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 4. Sampled chunks are complete thoughts, none under 178 characters, at least 2 documents split | 4 of 5, all parts | 5/5 | 5/5 | 4/5 | MET |
| 5. Laundry answer does not silently pick one hall | 1 of 1 | 1/1 | 1/1 | 1/1 | MET |

### Real output

Every answer below came from `run_eval.py::run_once`, which retrieves with `store.py::search` and then calls `generate.py::answer_from_chunks`.

Criterion 1, from `tools/score_run.py`. Retrieval is deterministic, so this is the same for every run.

```
pass  What are the University Health Center's walk-in hours?  found in health_center.txt#0
pass  When is the wait longest at Pellew Dining Hall?  found in dining_pellew_dining_hall.txt#0, dining_the_ridgeway_cafe_followup.txt#0
pass  How many pages per semester can an undergraduate print?  found in admin_printing_quota.txt#0
pass  How often does the campus shuttle run on weekdays?  found in transit_shuttle.txt#0
pass  Is laundry free in the dorms?  laundry chunks from 3 hall(s): Aldridge Hall, Innisfree Hall, Old Brewhouse
```

Criterion 2, the run 1 answer to the printing question:

```
Every student gets $30 of printing per semester, which is roughly 600 black-and-white pages (admin_printing_quota.txt).
```

And the run 2 answer to the walk-in hours question:

```
The University Health Center's walk-in hours are from 8am to 11am. 

Source: health_center.txt
```

Criterion 3, from `run_eval.py::check_out_of_scope`:

```
refused  (best distance 0.825)  What is the capital of Mongolia?
refused  (best distance 0.934)  How do I change the oil in a diesel engine?
refused  (best distance 0.886)  Who won the 1994 World Cup?
refused  (best distance 0.844)  What is the recommended dosage of ibuprofen for a headache?
refused  (best distance 0.896)  How do I write a for loop in Rust?
-> gate refused 5 of 5
```

Criterion 4, the run 3 sample from `tools/score_run.py`. The chunks themselves came from `chunker.py::split_documents`.

```
documents split: 2 (housing_innisfree_hall.txt, housing_old_brewhouse.txt)
split-produced chunks under 178: none
run 3: course_engl_205_exams.txt#0, housing_old_brewhouse.txt#0, housing_innisfree_hall.txt#1, advising_registration.txt#0, dining_kestrel_commons_followup.txt#0. Cut at an edge: housing_innisfree_hall.txt#1
```

This is the chunk that failed, `housing_innisfree_hall.txt#1`. It starts in the middle of a sentence.

```
arrangement is the best compromise on campus.

The bad: no air conditioning, which matters for the first three weeks of September.

Laundry costs $1.75 wash, $1.75 dry, app-based. On noise: moderate; the building is L-shaped and the short wing is much quieter.
```

For comparison, this one passed, `admin_printing_quota.txt#0`:

```
On the printing quota

Every student gets $30 of printing per semester, which is roughly 600 black-and-white pages. It does not roll over. Colour costs eight times as much per page, which people discover after printing one poster.
```

Criterion 5, the run 1 answer to the laundry question:

```
Based on the documents, laundry is not free. 

- In Innisfree Hall, it costs $1.75 for a wash and $1.75 for a dry (`housing_innisfree_hall.txt`).
- In Old Brewhouse, it costs $1.50 for a wash and $1.50 for a dry (`housing_old_brewhouse.txt`).
- In Aldridge Hall, it costs $1.75 for a wash and $1.50 for a dry (`housing_aldridge_hall_laundry.txt`).
```

## Verdicts

| # | Criterion | Verdict | How I decided |
|---|---|---|---|
| 1 | Retrieved chunks contain the answer (4 of 5) | MET | All five questions pulled back a chunk with the answer in it. That is 5 of 5 against a target of 4. Retrieval is deterministic, so it is 5 of 5 in every run. |
| 2 | Every answer names a source (5 of 5) | MET | All 15 answers name a file. None were refused, so none failed that way either. The format moves around, parentheses in one, a Source line in another, backticks, italics, but every answer names the file. |
| 3 | Gate stops out-of-corpus questions (4 of 5) | MET | 5 of 5 refused. The closest one was 0.825, which is still 0.225 over the cutoff. This one was not close. |
| 4 | Chunk quality (4 of 5, all parts) | MET, and the closest call | Run 3 came out 4 of 5, which is exactly the target. `housing_innisfree_hall.txt#1` starts in the middle of a sentence. The other parts are right at the line too. Exactly 2 documents split and the target is at least two. Every part holds, but none of them hold with room to spare. |
| 5 | Laundry answer does not pick one hall (1 of 1) | MET | All three answers list three halls with prices and sources, which is what the criterion asks for. The best argument for MISSED is that every answer opens with "laundry is not free" as if it covers all the dorms, when it only covers 3 of the 7 halls. That is the failure this criterion was supposed to catch, just with three halls instead of one. I kept it MET because the criterion says to list at least two hall policies with sources, and moving the bar after seeing results is exactly what this unit says not to do. The gap goes into the diagnosis instead. |

## Diagnoses

Nothing missed. At least three of my five targets were set too low, and clearing all five on the first try says more about the targets than it does about the system.

- Criterion 3 was the safest one. In `criteria.md` I called 4 of 5 "a conservative floor" because of the 0.4 gap. My out-of-scope questions, Mongolia, diesel engines, Rust, are so far from a campus corpus that no reasonable cutoff would let them through. I would tighten it to 5 of 5 on five questions that sound like they belong but are not covered, like "What is the tuition at State?", "When does the city library close?", or "Is there a dress code for the career fair?" Those would actually test where 0.6 sits instead of just proving it is under 0.8.
- Criterion 1 was loose because any of the top 5 counts. I checked a stricter version against the same run. "The top chunk contains the answer" scores 3 of 5, which is a miss. On Pellew the top chunk is `dining_pellew_dining_hall_followup.txt#0` at 0.175. It says "go before 11:45" and never gives the 12:30 end. On laundry the top chunk only covers one hall. I would tighten it to at least 4 of 5 with the answer in the top chunk, or 5 of 5 in the top 3.
- Criterion 5 measured what I wrote, not what I meant. What I meant was do not present part of the answer as the whole answer. What I wrote was list at least two halls. The system passed by listing three of seven and still saying laundry is not free anywhere. I would tighten it to the answer either covers every hall or says which halls it covers.

### What the runs did show

No criterion missed, but two results landed right at the edge of a target, and both come back to the same thing. Splitting `housing_innisfree_hall.txt` and `housing_old_brewhouse.txt` produced a second chunk that holds the review's laundry and noise paragraph in both cases.

1. Chunking caused the near miss on criterion 4. The overlap carried into chunk #1 gets trimmed to a word boundary, which was the unit 1 fix, but not to a sentence boundary. So `housing_innisfree_hall.txt#1` opens with "arrangement is the best compromise on campus.", which is the end of a sentence that starts back in chunk #0. The overlap copies the last 60 characters and drops the partial word at the front. 60 characters almost never lines up with the start of a sentence, so every split chunk after the first one opens mid-sentence. Run 3's sample happened to pick one up.

2. Retrieval caused the laundry gap on criterion 5, and generation made it worse. Those second chunks are basically just the laundry and noise paragraph, so they repeat the dedicated `housing_*_laundry.txt` posts. For "Is laundry free in the dorms?" they rank first and second at 0.330 and 0.371, and the matching laundry posts rank third and fourth. With top-k at 5, those near duplicates take four of the five slots and only cover two halls. Aldridge gets the fifth. The other four halls' laundry posts sit at ranks 7 to 10, between 0.517 and 0.550, all well inside the 0.6 cutoff, and they never reach the model.

   ```
   0.330 housing_innisfree_hall.txt#1          retrieved
   0.371 housing_old_brewhouse.txt#1           retrieved
   0.427 housing_innisfree_hall_laundry.txt#0  retrieved, same hall again
   0.442 housing_old_brewhouse_laundry.txt#0   retrieved, same hall again
   0.479 housing_aldridge_hall_laundry.txt#0   retrieved
   0.512 housing_aldridge_hall.txt#0
   0.517 housing_fenwick_court_laundry.txt#0   never seen
   0.521 housing_morrow_house_laundry.txt#0    never seen, cheapest hall
   0.544 housing_calder_annexe_laundry.txt#0   never seen
   0.550 housing_tamsin_court_laundry.txt#0    never seen, in-unit washer-dryer
   ```

   The model then generalizes from what it got and says laundry is not free, for all the dorms. One of the halls it never saw is Tamsin Court, which has an in-unit washer-dryer and no per-load price. That is the one hall where the blanket claim is not backed up. The model did what the prompt told it to do and answered from the documents it was given. It was just given three halls' worth of a seven hall answer.

The pattern is this. Each hall has both a review and a dedicated laundry post, so retrieval by closest meaning fills the top 5 with near duplicates. Any question where the answer is spread across a lot of documents gets a partial answer that reads like a complete one. Laundry is the only test question like that. Noise and dining have the same shape, seven noise posts and several dining posts, but I have no test question that would show it.

## The Improvement

What I changed: `TOP_K` in `config.py`, from 5 to 10. That is the only change. The chunker, the index, the prompt, the cutoff, and the model are all the same as the before run.

Why I picked it: diagnosis 2 found near duplicate chunks filling the top 5 for the laundry question, so the model only ever saw 3 of the 7 halls. At top-k 10 every hall's laundry post gets retrieved, ranks 3 through 10 in the list above. I picked this over the overlap problem from diagnosis 1 because the laundry gap gives the user a wrong answer. The overlap problem is a cosmetic flaw in two chunks.

How I measured it: none of the five criteria count halls, since criterion 5 passes at two. So next to the criteria I counted how many of the 7 halls the laundry answer covers, using the "halls named" line from `tools/score_run.py` on both result files. I did not change criterion 5.

### Run Log - After

The raw file is [results/run_2026-09-30_0004_after.md](results/run_2026-09-30_0004_after.md), from `python run_eval.py --label after`, with caching off, 15 real model calls, top-k 10, and the cutoff at 0.6. Scored by `tools/score_run.py`.

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunks contain the answer | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 2. Every answer names a source | 5 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 3. Gate stops out-of-corpus questions | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 4. Sampled chunks are complete thoughts, none under 178 characters, at least 2 documents split | 4 of 5, all parts | 5/5 | 5/5 | 4/5 | MET |
| 5. Laundry answer does not silently pick one hall | 1 of 1 | 1/1 | 1/1 | 1/1 | MET |

Before and after, side by side, including the thing the change was aimed at:

| Measure | Before (top-k 5) | After (top-k 10) |
|---|---|---|
| Criteria met | 5 of 5 | 5 of 5, no change |
| Halls whose laundry chunks were retrieved | 3 of 7 | 7 of 7 |
| Halls named in the laundry answer, runs 1 / 2 / 3 | 3 / 3 / 3 | 2 / 6 / 3 |
| Laundry answers that open with a blanket "laundry is not free" | 3 of 3 | 3 of 3 |
| Laundry answers that mention Tamsin Court | 0 of 3 | 0 of 3 |
| Input tokens for the 15 calls | 9,555 | 17,001 (78% more) |

The run 1 laundry answer after the change. It covers fewer halls than any before run, even though all seven were in its context.

```
Based on the provided documents, laundry is not free. Each dorm has specific costs for washing and drying (for example, $1.75 to wash and $1.75 to dry in Innisfree Hall, and $1.50 to wash and $1.50 to dry in Old Brewhouse). 

Sources: `housing_innisfree_hall.txt` and `housing_old_brewhouse.txt`
```

The run 2 laundry answer after the change. This is the best answer either log produced, six halls with a source for each.

```
Based on the documents, laundry is not free. It costs varying amounts depending on the building, such as $1.75 for a wash and $1.75 for a dry in Innisfree Hall (`housing_innisfree_hall.txt`), $1.50 for a wash and $1.50 for a dry in Old Brewhouse (`housing_old_brewhouse.txt`), $1.75 for a wash and $1.50 for a dry in Aldridge Hall (`housing_aldridge_hall.txt`), $2.00 for a wash and $1.75 for a dry in Fenwick Court (`housing_fenwick_court_laundry.txt`), $1.50 for a wash and $1.25 for a dry in Morrow House (`housing_morrow_house_laundry.txt`), and $2.00 for a wash and $1.75 for a dry in Calder Annexe (`housing_calder_annexe_laundry.txt`).
```

Did it help? It fixed the stage it was aimed at, but not the failure. Retrieval went from 3 of 7 halls to 7 of 7, and the ranking shows that directly. The answer went from a steady 3 halls to 2, 6, and 3. That averages a little higher, 3.7 against 3.0, but it is less consistent, and run 1 is worse than every before run. All three answers still open with the blanket claim and none of them mention Tamsin Court. None of the five criteria moved, and input tokens went up 78%.

I know which stage is left because the evidence is sitting in the context in every after run. All seven halls reach the model and the model picks a couple of examples out of them. The problem moved from retrieval to generation. The grounding prompt says "Be brief. Two or three sentences is usually enough." and that pushes the model to summarize with a "such as" instead of listing every hall. I am keeping the change, because any fix on the generation side needs all seven halls in the context to work with. On its own though, it did not make the laundry answer reliably complete.

One measurement error, reported and not fixed after the fact. The per-question columns in the after file show the health center question failing in runs 1 and 2. Those answers say "8:00 am to 11:00 am", which is right. The normalizer in `scorer.py` does not treat ":00" as optional, so it missed them. None of the five criteria are scored from that column, and the before run never phrased the time that way, so no verdict changes. I left the rule the way it was committed instead of editing it after seeing results. The fix is to strip ":00" in `scorer.normalize`.

## Second Improvement (Stretch)

Declared before building. Nothing in this section exists in the code yet.

What I am going to change: the grounding prompt, `GROUNDING_INSTRUCTION` in `generate.py`. I am adding one rule. When the documents give different answers for different buildings or options, list every one the documents mention with its file, and do not make a general claim about all of them that the documents only support for some. The "Be brief" rule gets an exception for that case. Top-k stays at 10, and everything else stays the same as the first improvement's after run.

Which failure it is meant to fix: the one the first improvement left behind. After top-k went to 10, all seven halls reach the model, but the answer still names anywhere from 2 to 6 of them, opens with a blanket "laundry is not free" in 3 of 3 runs, and never mentions Tamsin Court. That is the generation stage.

How I will measure it, decided now: the full test again with `python run_eval.py --label after2`, three runs, caching off, scored by `tools/score_run.py` into the same five-row table. Next to that, the same three numbers from the first improvement.

- Halls named in the laundry answer, out of 7, per run. The "halls named" line from `tools/score_run.py`.
- Blanket claims, out of 3. An answer counts as a blanket claim if it says laundry is or is not free for the dorms in general without limiting that to the halls it lists.
- Answers that mention Tamsin Court, out of 3.

It also has to not break anything else. If criterion 2 drops, or the other four answers get worse, that counts against it.

## What's Still Broken

No criterion is missed, before or after. All five met is not the same as nothing broken. These are the problems the runs turned up that my criteria were too loose to catch.

1. The laundry answer is still incomplete and it still overstates. This is generation. With all seven halls retrieved, the model still names anywhere from 2 to 6 of them, still opens with laundry is not free for every dorm, and never mentions Tamsin Court's in-unit washer-dryer. The next step is changing the grounding prompt, `generate.py::GROUNDING_INSTRUCTION`, so that when the documents give different values per building it lists every building, or says which ones it is covering. The "Be brief" rule needs an exception for that. I stopped because this unit allows one change and I used it on top-k. The prompt change would be a second improvement, measured the same way, halls named and blanket claims across three runs.
2. Split chunks after the first one start mid-sentence. This is chunking. The overlap is trimmed to a word boundary but not a sentence boundary, so `housing_innisfree_hall.txt#1` opens with "arrangement is the best compromise on campus." The next step is starting the overlap at the first sentence boundary inside it, or dropping it if there is not one. I stopped because it affects 2 chunks out of 90, and it cost criterion 4 one sampled chunk in one run. The laundry problem gives people wrong answers. This one does not.
3. The scorer misses "8:00 am". It does not match it to "8am", so the per-question column in the after file shows two false fails on the health center question. The next step is making ":00" optional in `scorer.normalize`. I stopped because it changes no verdict, and editing a scoring rule after seeing the results it scores is the exact thing this unit says not to do. I would fix it before the next baseline, not in the middle of this one.
4. The test set only has one question where the answer is spread across documents. The near duplicate problem from diagnosis 2 should also hit noise, with seven `housing_*_noise.txt` posts, and questions that compare dining halls. I have no test question that would show it.

## What I'd Do Differently

Three of my five criteria passed because of how I wrote them, not because of the system.

- Criterion 1 counts any of the top 5, and now the top 10. I would write "the top ranked chunk contains the answer for at least 4 of 5". Scored against the same before run, that version gets 3 of 5 and misses on Pellew and laundry. A criterion that can catch the Pellew near miss is worth more than one that cannot.
- Criterion 3's out-of-scope questions are too far from the corpus to test the cutoff. Mongolia, diesel engines, and Rust are never going to get close. I would keep 4 of 5 but use questions that sound like campus life and are not covered, so the gate actually has to separate close from not quite.
- Criterion 5 should have said what I meant, which is the answer covers every hall or says which halls it covers. "At least two halls" passed an answer that makes a claim about all seven halls from three of them.
- Criterion 4's sample is too easy. 86 of the 90 chunks are whole documents, and those pass the complete thought check by default. I would sample only from chunks that came out of a split, because those are the only chunks where my chunker actually made a decision.

I would also write the scoring rules down as part of each criterion in unit 1, the way `scorer.py` has them now. A few calls, like what counts as the answer for the laundry question and whether a refusal counts as naming a source, had to be made in unit 2. They were made before the run but after the criteria. They belonged next to the targets from the start.
