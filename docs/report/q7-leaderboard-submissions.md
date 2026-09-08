# Q7: leaderboard submissions, and the gap between what we report and what we upload

*Owner: Yash. Build with `python -m src.pipeline.submit {mind,ebnerd}`. Ledger rows in
`docs/FACTS.md`.*

## What is actually uploaded, stated first

**The submitted system is not our headline system, and the difference is not in our favour.**
`src/pipeline/submit.py` ships the **embeddings-only** scorer for both competitions. Our reported
headline is a two-stage BM25 + embeddings retrieve-then-rank pipeline with a LightGBM re-ranker
that scores 0.7429 per-impression AUC on EB-NeRD small test.

Offline, on our own splits, embeddings-only is:

* on EB-NeRD, **the weakest of the three stage-one systems** on test AUC: emb 0.5397 against
  bm25 0.5107 and fused 0.5380 — and far below rerank's 0.7429
* below `fused` on MIND by +0.0014 AUC in the A1 measurement

So the leaderboard number understates the system described in the rest of this report, and the
two should never be quoted as if they were the same thing.

**Why the gap exists.** The re-ranker's features cannot be computed for the leaderboard test sets:
they need `pop_causal` (clicks strictly before the impression) and the engagement columns, and the
held-out test sets ship neither labels nor the history structure the feature builder consumes.
BM25 was left out for a separate, purely practical reason: `get_scores` is dense over the whole
corpus per distinct query, measured at roughly 1.6 hours for MIND-large's 2M distinct histories.
That is expensive rather than impossible, and closing it is the first stretch item.

**This is reported rather than hidden because the assignment is explicit that grading is never on
leaderboard rank.** An honestly reported gap costs nothing; letting a better offline number stand
in for a weaker uploaded one would be the actual error.

## Scale of the two test sets

| competition | impressions | articles | candidate pairs |
|---|---|---|---|
| EB-NeRD (RecSys 2024) | 13.5M | 125,500 | 205,925,868 |
| MIND (Codabench 13967) | 2.37M | 120,961 | |

Neither fits in memory at once, so `submit.py` streams in slices rather than reusing the offline
retrieval path, which materialises every impression. **The scoring semantics are identical** —
mean of the last `history_len` article vectors, L2-normalised, cosine against each candidate —
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
3. **The zip must contain the text file and nothing else** — no directories, no `__MACOSX`.

## Partial output is prevented structurally, not remembered

A previous submission on this project uploaded a partial file that covered 0.84% of the test set
and scored 0.5012, i.e. exactly random, because a smoke test had been written to the real upload
path. It looked like a valid submission and a bad model.

`submit.py --limit N` now writes to `SMOKE-<N>-<name>` and prints that it is not submittable, so
a truncated run cannot occupy the path the real artifact uses. This is the project's most
repeated class of failure — output that is well-formed and wrong — and it is the same shape as
the mis-ordered join in Q5 and the vacuous tests in the methodology section.

## Submission budget

MIND allows **1 submission per day**, EB-NeRD **5**, and EB-NeRD scoring takes hours. Every file
is therefore validated offline before upload: row count against the test file, row order, inner
filename, and zip contents. A mistake found after upload costs a day on MIND, which is why the
structural checks above exist rather than a convention to be careful.

## Status

Submissions are built and validated offline. **Uploading and screenshotting both leaderboards
requires a Codabench account and is a manual step**; the screenshots are a required deliverable
for the design note and cannot be produced retroactively.
