# Q7: leaderboard submissions, and the gap between what we report and what we upload

*Owners: Yash (format, budget, validation), Naman (the re-ranker submission path). Build with
`python -m src.pipeline.submit_{ebnerd,mind}_rerank`. Ledger rows in `docs/FACTS.md` sections 13
and 18.*

## What is actually uploaded, stated first

**The submitted system carries the behavioural axis, but it is still not the system this report
headlines, and the difference is not in our favour.**

| | EB-NeRD small, our test split |
|---|---|
| reported system, 22 features | **0.7908** |
| **uploaded system, 16 features** | **0.7351** |
| gap | **-0.0556** [-0.0565, -0.0547], paired bootstrap, significant |

For scale: stage one alone is 0.5430 on the same split, and an earlier embeddings-only entry
scored 0.5967 on the EB-NeRD leaderboard in Assignment 1. So the uploaded system is far closer to
the reported one than to a retrieval baseline, and the remaining gap has a single cause.

## Why six features are missing, in two different senses

These should not be conflated, because one is a property of the competition and the other is a
decision we made.

**Five are impossible.** The Codabench test files **withhold `article_ids_clicked`**. Verified by
diffing columns rather than assumed: `ebnerd_small/train/behaviors.parquet` minus
`ebnerd_testset/test/behaviors.parquet` leaves exactly `article_ids_clicked`, `article_id`,
`next_read_time` and `next_scroll_percentage`, all of them outcomes, and the test file adds
`is_beyond_accuracy`. That is the ordinary leaderboard arrangement: labelled data to train on,
labels withheld on the evaluation set, scoring done server-side.

`pop_causal` counts clicks strictly before each impression. On the test period those clicks *are*
the withheld labels, so it cannot be computed there at any cost, and nor can `pop_24h`,
`pop_velocity`, `pop_rank` or `pop_rel_max`, which all derive from it. This is the single largest
contributor to the reported system: removing the family costs -0.0502 test on our own split.

**One is a choice.** `bm25` is fully computable on the leaderboard but dense over the corpus per
distinct history, measured at roughly 1.6 hours for MIND-large's 2M distinct histories. The
ablation prices it at +0.0011 val and +0.0004 test, so it is dropped on cost and the decision is
reversible.

## What replaced them, and why it is the more honest feature anyway

`article_ids_inview` **is** present on the test files, so **exposure** is computable: how often an
article was *shown* strictly before `t`. Five exposure features mirror the popularity family
exactly, with the same strict `< t` upper bound, so no window setting can leak.

Two things are worth saying about this beyond the submission.

**It is closer to what a deployed recommender actually has.** A live system knows its own exposure
log immediately; click feedback arrives later and is noisier. Building the system around exposure
is arguably the more realistic design, and the leaderboard constraint pushed us toward it.

**It improved the reported system too**, which was not the intent. Adding the exposure family took
EB-NeRD from 0.7653 to **0.7908** test, **+0.0255**, and `exp_rel_max` is now the second-highest
gain feature in the model behind `pop_rel_max`. Exposure and clicks are not redundant: how often an
article was shown carries information that how often it was clicked does not, presumably about
editorial promotion.

## Reporting two numbers rather than one

The assignment is explicit that grading is never on leaderboard rank, so there is no incentive to
blur this, and a blurred version would be the actual error. The rule we followed is that **the
uploaded number and the reported number are quoted separately, always, and the better one never
stands in for the other.**

The same discipline applies within the report: Q9's honest-versus-leaky comparison, the
select-on-val rule, and this section are the same commitment applied to three different
temptations.

## Scale of the two test sets

| competition | impressions | articles | candidate pairs |
|---|---|---|---|
| EB-NeRD (RecSys 2024) | 13.5M | 125,500 | 205,925,868 |
| MIND (Codabench 13967) | 2.37M | 120,961 | |

Neither fits in memory at once, so `submit.py` streams in slices rather than reusing the offline
retrieval path, which materialises every impression. **The scoring semantics are identical**,
mean of the last `history_len` article vectors, L2-normalised, cosine against each candidate,
and only the execution differs. Which article vectors are used comes from the same
`configs/datasets.yaml` key the offline path reads, so the encoder chosen by ablation cannot
silently diverge between the report and the submission.

## The format, and the three things that break it

Both competitions want one line per impression:

```
<impression_id> [r1,r2,...,rn]
```

where `ri` is the **rank of the i-th candidate as listed in the test file**, an integer in 1..n
with 1 best. Three traps, each of which has cost time on this project or is documented to:

1. **Row order must match the test file.** The ranks are positional against the test file's own
   candidate order, so a correctly-ranked but reordered file scores as a plausible bad number
   rather than erroring.
2. **The inner filename differs between the two competitions.** MIND wants `prediction.txt`
   singular; EB-NeRD wants `predictions.txt` plural. Nothing else about the format differs.
3. **The zip must contain the text file and nothing else**: no directories, no `__MACOSX`.

## Partial output is prevented structurally, not remembered

A previous submission on this project uploaded a partial file that covered 0.84% of the test set
and scored 0.5012, i.e. exactly random, because a smoke test had been written to the real upload
path. It looked like a valid submission and a bad model.

`submit.py --limit N` writes to `SMOKE-<N>-<name>` and prints that it is not submittable, so a
truncated run cannot occupy the path the real artifact uses.

The re-ranker paths initially did **not** inherit this. Both wrote their intermediate text file to
a fixed `predictions.txt` regardless of the `--out` archive name, so a smoke run would have
silently overwritten a completed full run's output. The archives were unaffected and no bad file
was produced, but the hazard was real and is now closed: the intermediate is named after the
archive, while the zip still stores the inner filename each competition requires.

Worth noting how it was found. It was not caught by a test; it was caught by writing this section
and checking whether the claim already in it was actually true of the new code. **A documented
safeguard is a claim about the system, and claims need checking like any other.**

This is the project's most repeated class of failure, output that is well-formed and wrong, and it
is the same shape as the mis-ordered join in Q5 and the vacuous tests in the methodology section.

## Submission budget

MIND allows **1 submission per day**, EB-NeRD **5**, and EB-NeRD scoring takes hours. Every file
is therefore validated offline before upload: row count against the test file, row order, inner
filename, and zip contents. A mistake found after upload costs a day on MIND, which is why the
structural checks above exist rather than a convention to be careful.

## Status

Both submissions are built, transferred and validated.

| file | rows | size | checks |
|---|---|---|---|
| `mind_prediction.zip` | 2,370,727 | 108 MB | filename, zip contents, row count, row order, rank permutations |
| `ebnerd_predictions.zip` | 13,536,710 | 230 MB | same five |

EB-NeRD was scored on the cluster: 3 h 06 m, 44 GB peak RSS, 16 features over 205,925,868
candidate pairs. SHA256 verified after transfer.

### Uploaded: results

**MIND, scored.** Submission `932812`, 2026-09-19 09:23, user `namsyn`, rank 54.
Screenshot: [screenshots/mind-leaderboard-2026-09-19.png](screenshots/mind-leaderboard-2026-09-19.png).

| | AUC | MRR | nDCG@5 | nDCG@10 |
|---|---|---|---|---|
| **A2, uploaded, 11 features** | **0.6473** | 0.3174 | 0.3448 | 0.4010 |
| A1 entry, embeddings + entity blend | 0.6503 | 0.3198 | 0.3454 | 0.4010 |
| difference | **-0.0030** | -0.0024 | -0.0006 | 0.0000 |

**Two things to say about this, and the second is the uncomfortable one.**

The offline prediction was good. We projected 0.6460 on our own MIND test split for exactly this
11-feature configuration; the leaderboard returned 0.6473, **+0.0013**. The submission path and
the offline path agree to three decimals on a 2.37M-impression set we have no labels for, which
is the strongest available evidence that the streaming re-implementation preserves the scoring
semantics it claims to.

**The A2 entry is marginally below the A1 entry on every metric.** That is the honest headline
for MIND and it is not a regression in the re-ranker; it is the withheld-label constraint biting
hardest exactly where the dataset is weakest. MIND ships almost no behavioural signal to begin
with (no `published_time`, no per-click history timestamps, no read time or scroll), so the A2
system there is 11 features against EB-NeRD's 22, and the click-popularity family that carries
most of the behavioural gain is unavailable on the test period by construction. What remains is
close to the A1 system plus exposure features, and it lands within 0.003 of it.

So the behavioural axis is worth +0.2077 AUC on EB-NeRD where the columns exist, and
approximately nothing on the MIND leaderboard where they do not. Both statements are in this
report and neither is allowed to stand in for the other.

**EB-NeRD, submitted but not scored.** `ebnerd_predictions.zip` was uploaded, and at the time of
writing it has not run. Codabench executes the RecSys 2024 competition on volunteered compute
workers, none were available, and the queue is first-come-first-served, so making a machine
available would not guarantee our own submission is the one it picks up. **There is therefore no
EB-NeRD leaderboard screenshot, and it is not within our control to produce one.**

This is a limitation of the competition infrastructure rather than of the submission: the file was
built, validated against all five structural checks, scored on the cluster in 3 h 06 m, and
transferred with its SHA256 verified. What is missing is a server to run it, not a prediction.

The EB-NeRD numbers this report relies on are all from **our own labelled test split**, never from
the leaderboard, so nothing downstream depends on that screenshot existing. The one thing we
cannot do is state an EB-NeRD leaderboard rank, and we do not.

### Getting the submission path to run at all

Three implementations were abandoned before one finished, each rejected on a measured rate rather
than a guess, which is the only reason none of them consumed its full wall clock:

| attempt | measured | projected | cause |
|---|---|---|---|
| per-candidate binary search | 3.1M in 8 h 41 m | ~38 h | two `searchsorted` calls per candidate, ~200M from Python |
| sliding-window sweep | <25,000 in 15 min | ~135 h | user-level work recomputed per impression, 16.8 times per user |
| plus per-user cache | 25,000 in >10 min | ~90 h | `booster.predict()` called once per impression, 13.5M times |
| **plus batched predict** | **13.5M in 3 h 06 m** | | 541 predict calls instead of 13.5M |

Each rewrite was checked for **byte-identical output** against the previous implementation before
being trusted, except where a deliberate fix changed values. When the per-user cache was added at
the same time as a NaN-handling correction, the outputs necessarily differed, so the check became:
do the differences fall exactly on users whose history contains NaN? They did, **4,422 of 4,422
changed impressions and none of the unchanged ones**, which isolates the cache as value-neutral.

The NaN correction is worth recording on its own. `build.py` stores `nan_to_num(read_time)` and
then takes a plain mean, so a missing value counts as zero. The first submission path used
`nanmean`, which skips it. Same user, different feature value, no error: a silent train/serve
mismatch that only surfaced because a `RuntimeWarning` in a log prompted a comparison against the
feature builder.
