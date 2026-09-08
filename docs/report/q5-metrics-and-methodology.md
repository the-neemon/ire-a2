# Q5: metrics, slices, and why the methodology is the result

*Owner: Yash. Source `results/ebnerd_small_{val,test}.md`, ledger `docs/FACTS.md` sections 8,
10, 11, 12.*

## The convention, stated once

**Every AUC here is per-impression**, the Mann-Whitney AUC computed inside one impression and
averaged over impressions containing both a click and a non-click. Pooled AUC is not used.

This is not a stylistic choice and the difference is large. Measured on val: `recency` reads
**0.5861 pooled but 0.5087 per impression**, and features that are constant within an impression,
`user_read` and `hist_len`, score **exactly 0.5000** per impression while reading 0.4868 and
0.5154 pooled. Candidates inside one impression are all roughly the same age, so a pooled number
measures variation *across* impressions, which the ranking is never judged on. Pooled AUC
systematically overstates any feature that varies across impressions rather than within them.

**Every claimed difference carries a paired bootstrap 95% CI** over 1,000 resamples, with both
systems scored on the *same* resampled impressions. Paired because two systems evaluated on the
same impressions have correlated errors, so comparing two independent intervals is far too
conservative and hides real differences. A difference counts only if its interval excludes zero.

**Selection on val, test scored once.** Stated before running and honoured even where test
disagreed.

## The two-stage result

| comparison | val AUC | test AUC | significant |
|---|---|---|---|
| rerank - bm25 | +0.2370 [+0.2339, +0.2402] | +0.2322 [+0.2306, +0.2338] | yes |
| rerank - emb | +0.2068 [+0.2039, +0.2095] | +0.2032 [+0.2018, +0.2048] | yes |
| rerank - fused | +0.2047 [+0.2018, +0.2076] | +0.2049 [+0.2034, +0.2064] | yes |

Reported against all three stage-one systems rather than only the weakest, because "beats the
best baseline" and "beats the baseline we happened to ship" are different claims.

Full metric set, val:

| system | AUC | MRR (first click) | MRR (all clicks) | nDCG@5 | nDCG@10 |
|---|---|---|---|---|---|
| bm25 | 0.5205 | 0.3418 | 0.3414 | 0.3794 | 0.4607 |
| emb | 0.5506 | 0.3594 | 0.3589 | 0.4017 | 0.4778 |
| fused | 0.5528 | 0.3628 | 0.3623 | 0.4043 | 0.4807 |
| **rerank** | **0.7575** | **0.5319** | **0.5314** | **0.5967** | **0.6341** |

The two MRR columns differ by only ~0.0005 here, which is itself the confirming evidence for
finding 2 below: EB-NeRD is 0.5% multi-click, so the definitions almost coincide. The same
comparison on MIND, at 28.8% multi-click, moves MRR by -0.0415. **The size of the discrepancy is
a property of the dataset, not of the ranker**, which is exactly why it surfaced on one dataset
and not the other.

### How the join was verified

The re-ranker writes one row per candidate; the harness needs one score list per impression,
aligned to the `candidates` column. A regrouped list that comes back in a different order is
still the right length with the right values, so **a mis-ordered join produces a plausible wrong
number rather than an error**. The order is therefore rebuilt from `candidates` by joining on
(impression_id, candidate) against an explicit position index, never taken from the flat file's
row order, and the join asserts it covered every candidate.

That is checked, not assumed: the trainer computes per-impression AUC in independent code and
agrees with the harness to four decimals on both splits (0.7575 val, 0.7429 test).

## Slices: the average hides the interesting part

cold = history <= 42 clicks; head = clicked article with >= 379 train clicks. **Sizes are printed
in every table**, because a badly placed threshold can silently select nearly everything and a
slice table without sizes is unreadable.

| slice | n | bm25 | fused | rerank | fused+popularity |
|---|---|---|---|---|---|
| cold | 6,463 | 0.5281 | 0.5612 | **0.7836** | 0.5843 |
| warm | 57,902 | 0.5196 | 0.5518 | **0.7545** | 0.5778 |
| head | 1,094 | 0.5091 | 0.6638 | **0.7046** | 0.7192 |
| tail | 63,271 | 0.5207 | 0.5509 | **0.7584** | 0.5760 |

**The re-ranker is better on cold users than warm** (0.7836 against 0.7545), inverting the usual
expectation that a recommender struggles without history. Its top feature by gain is causally
valid popularity, which needs no history at all, so a user with nothing behind them is exactly
where a popularity prior is the best available signal and where the history-driven stage-one
systems have least to work with.

**On head articles the leaky system beats the honest one** (0.7192 against 0.7046), the only
slice where that happens and exactly where it should: head articles are by definition those whose
lifetime view count is largest, so that is where knowing the future is worth most. 1,094
impressions with overlapping intervals, so a caution rather than a finding.

### The threshold trap that did not fire

Over 90% of articles in both datasets have zero train clicks (92.3% MIND, 92.9% EB-NeRD), so a
percentile taken over the whole catalogue would be 0 and `>=` would put every impression in head.
The slicing code takes the percentile over articles *seen in train* instead, giving thresholds of
152 and 349 clicks. Verified directly rather than assumed. The head slice is nonetheless small,
860 and 803 impressions, so its intervals are wide and its differences are indicative only.

## Beyond accuracy: the gain is not free

| system | diversity | novelty | coverage |
|---|---|---|---|
| bm25 | 0.8039 | 16.3525 | 0.1142 |
| fused | 0.7916 | 16.3909 | 0.1131 |
| rerank | 0.8006 | **16.4824** | **0.1030** |
| fused+popularity | 0.7963 | 16.3572 | 0.1099 |

The re-ranker buys +0.20 AUC at a real cost in **catalogue coverage**: 0.1131 to 0.1030, about 9%
fewer distinct articles ever reaching a top-10. Its novelty is the highest of any system, so it is
not collapsing onto popular items; it concentrates on a narrower set of individually
less-clicked articles. Reported as a tradeoff rather than presenting the accuracy gain alone.

## One metric name, two definitions: three times

The single most repeated failure mode in this project, and the reason the methodology section
exists at all.

**1. Recall against hit-rate.** The retrieval stage printed a hit-rate@200 (share of impressions
with at least one clicked article retrieved) under the label recall@200 (mean of found/clicked).
They reconcile exactly, 0.0333 x 0.6775 = 0.0226, and agree only when impressions have one click.
MIND is 28.8% multi-click against EB-NeRD's 0.5%, which is why the number appeared to fail to
reproduce on exactly one dataset and looked like a corpus bug.

**2. MRR, first click against all clicks.** Our offline 0.3548 against the leaderboard's 0.3198.
MIND's official scorer averages the reciprocal rank over *every* clicked article; ours credited
only the best-placed one. Measured on MIND small test: 0.3108 against 0.2693, a paired difference
of -0.0415 [-0.0423, -0.0405], while AUC and nDCG@10 are **identical** under both definitions.
That is precisely the reported signature of MRR falling while AUC and the nDCGs rose. The effect
is entirely multi-click: single-click impressions differ by exactly 0.0. Both are now reported as
separate columns rather than one being swapped in, since they answer different questions. The
arithmetic cannot be closed exactly, because 0.3548 is MIND small test and 0.3198 is MIND large
test whose click distribution we cannot see, and the report says so rather than implying a
reconciliation.

**3. Two history files with the same name.** A semantic history sweep scored 0.6473 where the
equivalent retrieval feature scored 0.5506. Neither the truncation length nor the normalisation
explained it: the two implementations read different `history.parquet` files. EB-NeRD ships one
per block, each describing clicks before *that block's* period, and merging them let a validation
-block history describe the future of a val impression. **99.8% of val impressions were affected,
and the leak was worth +0.0967 AUC on that feature.** Confirmed by making one implementation
produce both numbers with only the history source varying.

**The generalisable lesson.** When a number fails to reproduce on exactly one dataset, check the
definition against that dataset's distribution before suspecting the data. All three cases above
were invisible on EB-NeRD and obvious on MIND, or vice versa, for the same structural reason.

## Vacuous tests, and what was done about them

A test that passes without asserting anything is worse than no test. Five were found here:

1. The MIND history-time leakage assertion guarded on dtype, but MIND's empty timestamp lists
   come back as `List(Datetime)` not `Null`, so it never skipped; every `list.max()` was null,
   `null >= t` is null, the filter dropped every row, and it reported green over 95,071 of 95,071.
2. The anti-gaming guard globbed paths that stopped existing after a directory move and scanned
   **zero files**.
3. An install script recorded success from a package manager's exit code while the import it was
   supposed to verify had been broken throughout.
4. A job waiter matched its own command line and reported a finished build as still running.
5. Neither leakage test covered the engagement arrays, which is how case 3 above went unnoticed.

**Every assertion now states what it checked and fails if that count is zero**, and both leakage
guards are verified by injecting a violation and confirming they fire. Verify the artifact, never
a proxy for it.
