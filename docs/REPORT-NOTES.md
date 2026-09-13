# Report source notes

Everything the Q6 design note will draw on, in one place: what we built, every measured number
with its provenance, what worked, what did not, the tradeoffs, and the open questions.

**Status: living document, updated as results land.** Anything marked TO MEASURE is a known gap,
not an oversight. Last updated 2026-09-08 with Yash's `ebnerd_small` ablations (3.2), the Q5
harness over the two-stage output (2, 5) and the Q4 serving bench (7.3). Every number here also exists in `FACTS.md` (measurements) or `ABLATIONS.md`
(experiments); this file is the narrative view, those two are the ledgers. If they disagree, the
ledgers win.

**Metric convention, stated once.** Ranking numbers are **per-impression AUC**: the Mann-Whitney
AUC computed within each impression and averaged over impressions containing both classes.
Pooled AUC is not used, for reasons in section 6. Retrieval numbers are recall@K unless a row
says hit-rate@K, which is a different thing (section 6 again).

---

## 1. What we built

A two-stage retrieve-then-rank news recommender, extending our two separate Assignment-1
systems.

**Stage one, candidate generation** (carried over from A1, both datasets):
BM25 over article text via `bm25s`, and semantic retrieval via FAISS `IndexFlatIP` over
L2-normalised article embeddings. Top-K = 200, `OVERFETCH = 3` before the publication-date
filter. Both indexes are held in RAM.

**Stage two, the re-ranker** (new in A2, EB-NeRD):
LightGBM `lambdarank` over 10 per-candidate features. lambdarank rather than binary
classification so the training objective matches the metric: it weights each candidate pair by
how much swapping them would move nDCG.

**The features, all causally valid**, meaning computable strictly before the impression's own
timestamp:

| feature | source | varies within an impression? |
|---|---|---|
| `bm25` | stage one lexical score | yes |
| `emb` | stage one semantic score, uniform-weighted user vector | yes |
| `pop_causal` | clicks on the candidate strictly before `t` | yes |
| `engage_sim` | cosine to a `log1p(read_time_fixed)`-weighted user vector | yes |
| `recency` | `0.5 ** (age_hours / 24)` from `published_time` | yes |
| `age_hours` | article age at impression time | yes |
| `cat_match` | share of user history in the candidate's category | yes |
| `hist_len` | number of history items | **no** |
| `user_read` | mean `log1p(read_time_fixed)` over history | **no** |
| `user_scroll` | mean `scroll_percentage_fixed` over history | **no** |

The three that do not vary within an impression cannot reorder candidates on their own; they are
present for the ranker to interact with. Section 6 has the measurement that makes this concrete.

---

## 2. Headline results (EB-NeRD small)

**Per-impression AUC. Selection on val, test scored once.**

| system | val | test |
|---|---|---|
| stage one alone (bm25 + emb) | 0.5498 | |
| **two-stage re-ranker (ships)** | **0.7575** | **0.7429** |
| same model + serving-unavailable features | 0.7796 | |

**The behavioural axis is worth +0.2077 AUC**, CI [+0.2048, +0.2107], over what Assignment 1
could do. That is the single most important number in the report.

For scale, A1's best complete systems were 0.5397 (EB-NeRD small test) and 0.6503 (MIND
Codabench). `pop_causal` **alone** reaches 0.6954, above both.

**Stage two against every stage-one baseline**, paired bootstrap, `src.eval.run`. Reported
against all three rather than only the strongest, because "beats the best baseline" and "beats
the baseline we happened to ship" are different claims.

| comparison | val AUC | test AUC | significant |
|---|---|---|---|
| rerank - bm25 | **+0.2370** [+0.2339, +0.2402] | **+0.2322** [+0.2306, +0.2338] | yes |
| rerank - emb | **+0.2068** [+0.2039, +0.2095] | **+0.2032** [+0.2018, +0.2048] | yes |
| rerank - fused | **+0.2047** [+0.2018, +0.2076] | **+0.2049** [+0.2034, +0.2064] | yes |

The trainer computes per-impression AUC in independent code and agrees with the harness to four
decimals on both splits. That agreement is the check that the flat per-candidate table was
reshaped into `candidates` order correctly: a mis-ordered join yields a plausible number rather
than an error, so it is verified against a figure produced elsewhere rather than assumed.

**The full metric set (Q5), val, with CIs in `results/ebnerd_small_val.md`:**

| system | AUC | MRR (first click) | MRR (all clicks) | nDCG@5 | nDCG@10 |
|---|---|---|---|---|---|
| bm25 | 0.5205 | 0.3418 | 0.3414 | 0.3794 | 0.4607 |
| emb | 0.5506 | 0.3594 | 0.3589 | 0.4017 | 0.4778 |
| fused | 0.5528 | 0.3628 | 0.3623 | 0.4043 | 0.4807 |
| **rerank** | **0.7575** | **0.5319** | **0.5314** | **0.5967** | **0.6341** |
| fused+popularity | 0.5784 | 0.3707 | 0.3703 | 0.4184 | 0.4910 |

The two MRR columns differ by only ~0.0005 here, which is the confirming evidence for 9.2:
EB-NeRD is 0.5% multi-click, so the two definitions almost coincide. On MIND, at 28.8%
multi-click, the same comparison moves MRR by -0.0415.

**The same set on test, which section 9.1 makes the numbers to quote for now**, since the
val figures rest partly on contaminated engagement features and the test ones do not:

| system | AUC | MRR (first click) | MRR (all clicks) | nDCG@5 | nDCG@10 |
|---|---|---|---|---|---|
| bm25 | 0.5107 | 0.3257 | 0.3253 | 0.3577 | 0.4409 |
| emb | 0.5397 | 0.3492 | 0.3487 | 0.3831 | 0.4627 |
| fused | 0.5380 | 0.3474 | 0.3470 | 0.3813 | 0.4613 |
| **rerank** | **0.7429** | **0.5149** | **0.5143** | **0.5750** | **0.6140** |
| fused+popularity | 0.5797 | 0.3688 | 0.3684 | 0.4101 | 0.4841 |

Test tracks val closely on every system, which is the evidence that the contamination in 9.1 has
a bounded effect rather than carrying the result: `rerank` falls only 0.7575 to 0.7429, and
`rerank - fused` is +0.2049 on test against +0.2047 on val.

### Slices: where the gain actually lands

cold = history <= 42 clicks; head = clicked article with >= 379 train clicks. Sizes printed
because a badly-placed threshold can silently select nearly everything.

| slice | n | bm25 | fused | rerank | fused+popularity |
|---|---|---|---|---|---|
| cold | 6,463 | 0.5281 | 0.5612 | **0.7836** | 0.5843 |
| warm | 57,902 | 0.5196 | 0.5518 | **0.7545** | 0.5778 |
| head | 1,094 | 0.5091 | 0.6638 | **0.7046** | 0.7192 |
| tail | 63,271 | 0.5207 | 0.5509 | **0.7584** | 0.5760 |

* **The re-ranker is better on cold users than warm** (0.7836 vs 0.7545), inverting the usual
  expectation. Its top feature by gain is `pop_causal`, which needs no history at all: a user
  with no history is exactly where a popularity prior is the best available signal and where the
  history-driven stage-one systems have least to work with.
* **On head articles the leaky system beats the honest one** (0.7192 vs 0.7046), the only slice
  where that happens, and exactly where you would predict it: head articles are by definition
  those whose lifetime `total_inviews` is largest. 1,094 impressions with overlapping intervals,
  so a caution rather than a finding.

### Beyond accuracy (top-10, val): the gain is not free

| system | diversity | novelty | coverage |
|---|---|---|---|
| bm25 | 0.8039 | 16.3525 | 0.1142 |
| fused | 0.7916 | 16.3909 | 0.1131 |
| rerank | 0.8006 | **16.4824** | **0.1030** |
| fused+popularity | 0.7963 | 16.3572 | 0.1099 |

The re-ranker buys +0.20 AUC at a real cost in **catalogue coverage**: 0.1131 -> 0.1030, about
9% fewer distinct articles ever reaching a top-10. Its novelty is the highest of any system, so
it is not collapsing onto popular items; it concentrates on a narrower set of individually
less-clicked articles. Stated as a tradeoff rather than reporting the accuracy gain alone.

---

## 3. Ablations: what worked

### 3.1 The A2 re-ranker (paired bootstrap, 1000 resamples, shared, seed 13)

> **Caveat added 2026-09-08, read section 9.1 before quoting this table.** Every number in it is
> a **val** figure, and three of the ten features (`engage_sim`, `user_read`, `user_scroll`) were
> built from future-contaminated history on train and val. The grid needs re-running once that is
> fixed. The test-split headline is unaffected and is the number to quote in the meantime.

**RE-RUN 2026-09-12 on clean features.** The table below replaces the contaminated one; the
superseded figures are kept in the comparison at the end of this section because they are the
evidence for what the leak was worth.

Each arm removes exactly one feature and retrains. Full model = **0.7489** on 64,365 val
impressions, and **0.7461** on 244,647 test impressions.

| arm | val AUC | full - arm | 95% CI | sig | test delta | sig |
|---|---|---|---|---|---|---|
| stage1_only | 0.5498 | **+0.1991** | [+0.1963, +0.2020] | yes | **+0.2031** | yes |
| pop_only | 0.6954 | +0.0535 | [+0.0517, +0.0553] | yes | +0.0605 | yes |
| minus `pop_causal` | 0.7126 | +0.0363 | [+0.0346, +0.0379] | yes | +0.0403 | yes |
| minus `cat_match` | 0.7451 | +0.0038 | [+0.0027, +0.0048] | yes | +0.0047 | yes |
| minus `bm25` | 0.7480 | +0.0009 | [+0.0004, +0.0015] | yes | +0.0008 | yes |
| minus `engage_sim` | 0.7487 | +0.0002 | [-0.0004, +0.0009] | **no** | +0.0012 | yes |
| minus `hist_len` | 0.7489 | +0.0000 | [-0.0004, +0.0004] | **no** | +0.0006 | yes |
| minus `emb` | 0.7490 | -0.0001 | [-0.0006, +0.0004] | **no** | +0.0010 | yes |
| minus `age_hours` | 0.7491 | -0.0002 | [-0.0008, +0.0003] | **no** | +0.0012 | yes |
| minus `user_scroll` | 0.7493 | -0.0004 | [-0.0009, +0.0001] | **no** | +0.0009 | yes |
| minus `recency` | 0.7493 | -0.0004 | [-0.0010, +0.0001] | **no** | -0.0001 | no |
| minus `user_read` | 0.7496 | **-0.0006** | [-0.0012, -0.0002] | **yes, negative** | +0.0002 | no |

**Causally valid popularity is the single biggest win**, and more so than before. Removing it
costs 0.0363 val and 0.0403 test; alone it reaches 0.6954. This was the highest-ranked item on
the A2 plan and it delivered.

**`engage_sim`'s +0.0085 was entirely the leak.** On clean history the val interval straddles
zero at +0.0002 [-0.0004, +0.0009]. It was the largest per-feature effect after popularity and
category, and it does not survive. The read-time-weighted user vector does not beat the uniform
one inside the ranker, which was the question that feature existed to answer. Do not describe
this as "engagement weighting beats uniform pooling" in any form.

**`minus_user_read` is significantly negative on val**: removing the feature improves the model
by 0.0006. It is not significant on test, so the case for dropping it rests on a val-only effect
and is left pending rather than acted on mid-report.

**Val and test disagree systematically on the small arms**, almost all significant on test and
not on val. Test has 3.8x the impressions and therefore much tighter intervals, so where the
sign is stable and only significance changes, the reading is underpowered on val, not absent.

### What the leak was worth, by comparison

| | contaminated | clean |
|---|---|---|
| full, val | 0.7575 | 0.7489 |
| full, test | 0.7429 | **0.7461** |
| `minus engage_sim`, val | +0.0085, sig | +0.0002, **not sig** |
| `stage1_only`, val | +0.2077 | +0.1991 |

**Test performance went up.** Test features were always correct, since the test split is drawn
from the same block its history comes from, so the only thing that changed is the model, which
now trains on clean features. Removing the leak improved genuine generalisation by +0.0032,
which is the opposite of the usual "the number was inflated" story.

**Consistency check.** `stage1_only` (0.5498) and `pop_only` (0.6954) are bit-identical to the
contaminated run, because neither arm reads an engagement feature. The fix changed exactly the
arms it should have and nothing else.

The superseded discussion follows, kept because the sweep it cites is itself withdrawn:

**`engage_sim` contributed +0.0085** on contaminated features. Neither A1 system used the
read-time column at all. A dedicated sweep (section 4) was read as showing read-time weighting is
*worse* than uniform at every history length from 5 to 50; that sweep ran on contaminated history
and its conclusion is withdrawn. `engage_sim` pools over the user's entire history while
`emb` uses `history_len: 30`, so the two differ in two variables and the gain is attributable to
the pooling length, not the weights.

### 3.2 Stage-one ablations (Yash, MIND and EB-NeRD small)

Full detail in `ABLATIONS.md` 6a/7a (MIND), 6b/7b (EB-NeRD demo) and **6c/7c (EB-NeRD small,
the ones to quote)**. Demo rows are retained as evidence for the power lesson below, not as
results.

**BM25 field choice, MIND**: title-only wins on AUC, val +0.0024 [+0.0006, +0.0041], test
+0.0065 [+0.0047, +0.0083], reproducing the A1 number to four decimals. **But A1's claim of "no
measured downside" was wrong**: val MRR falls -0.0022 [-0.0039, -0.0005]. Left unshipped pending
a team decision.

**BM25 field choice, EB-NeRD small**: a genuine two-sided trade-off, and **the demo verdict
reverses**.

| split | AUC | MRR | recall@200 |
|---|---|---|---|
| val | **+0.0025** [+0.0002, +0.0047] | +0.0019 [-0.0001, +0.0039] | **-0.0024** [-0.0035, -0.0013] |
| test | **+0.0043** [+0.0031, +0.0055] | **+0.0024** [+0.0014, +0.0034] | -0.0005 [-0.0011, +0.0001] |

At demo scale this was rejected on AUC +0.0009 [-0.0062, +0.0081], which was the right call on
the evidence then available. At 10x the gain is +0.0025 and significant, and the demo interval
contained it comfortably: same effect, previously unresolvable.

**It reproduces the A1 EB-NeRD prior to four decimals on both axes at once** (A1: +0.0025 AUC,
-0.0024 recall@200; val here: +0.0025, -0.0024). Two independent systems on different codebases
agreeing to that precision on a two-sided trade-off is the strongest cross-validation we have.

**MIND and EB-NeRD pay for it in different metrics**, and neither was visible without a paired
CI per metric: MIND pays in MRR (-0.0022, significant), EB-NeRD pays in stage-one recall. So the
MIND MRR loss is a property of MIND, not of dropping the abstract. Cost is lower either way:
vocabulary 30,388 -> 15,132, build 1.0 s -> 0.6 s. Still `shipped-pending`, because it costs
exactly the stage-one recall that Q2's re-ranker consumes, making it a pipeline-level decision.

**Stemming**: keep it **on for both** datasets. The plan's premise ("Danish on, English off") is
rejected: turning it off costs MIND -0.0023 [-0.0034, -0.0013] val AUC.

For Danish at 10x, **the A1 prior of +22 to +36% recall@200 is now excluded rather than merely
unconfirmed**. All four ranking metrics sit within ±0.0004 of zero on both splits, with the val
AUC interval only ±0.0017 wide, so an effect a fifth the size of the field ablation's would have
shown. recall@200 *is* significant but **flips sign across the split boundary** (-8.5% val,
+4.7% test), which makes it a property of which articles fell in each window rather than of
stemming, and it should not be quoted directionally. Kept on for cost alone: vocabulary
43,451 -> 30,388 and val scoring 23.6 s -> 19.2 s. The standing explanation is that the Danish
stopword list already captures those wins (A1 measured it at 0.5035 -> 0.5232 AUC); testing it
needs a `stem x stopwords` 2x2, which is a second variable and so its own ablation.

---

## 4. Ablations: what did not work

| change | measured effect | verdict |
|---|---|---|
| `recency` as a ranker feature | +0.0001 [-0.0003, +0.0006] | **no measurable contribution** despite third-highest gain |
| `age_hours` as a ranker feature | +0.0003 [-0.0002, +0.0007] | same |
| BM25 title-only on EB-NeRD **demo** | AUC +0.0009 [-0.0062, +0.0081], recall@200 -0.0049 | rejected **at demo; reversed at `small`**, see 3.2 |
| Danish stemming, EB-NeRD small | ranking flat within ±0.0004; recall@200 sign-flips across splits | A1's +22-36% prior **excluded**, kept for cost |
| Disabling English stemming | -0.0023 [-0.0034, -0.0013] AUC | rejected, the plan's premise was wrong |
| Read-time weighting of the user vector | worse than uniform at N=5,10,20,50; +0.0013 only at N=100 | **withdrawn, see 9.1**: measured on contaminated history, re-run before quoting |

**Carried from A1, still true, do not re-run:** body text in the BM25 index (-0.0166 AUC),
Danish compound splitting (-0.0040), max-similarity pooling (-0.0030, confirmed independently on
both A1 systems), RRF instead of linear fusion (lost at every k), time and position decay on
click weighting (neutral to harmful at every constant), BM25 k1/b grid search (+0.001),
`rank_bm25` (782x slower than a sparse matmul), raw multilingual BERT as an encoder (below
random), ANN indexes (10 to 20x faster but exact search was never the bottleneck at this scale).

---

## 5. Q9, anti-gaming: with and without serving-unavailable features

**RE-RUN 2026-09-12 on clean features.** The caveat that stood here is discharged.

| arm | val AUC |
|---|---|
| causal only, **ships** | **0.7489** |
| + article lifetime aggregates | **0.7753** |
| **difference** | **+0.0264** [+0.0249, +0.0277], significant |

Previously +0.0222 on contaminated features. The gap **widened**, which looks backwards until you
see why: fixing the leak lowered the honest arm from 0.7575 to 0.7489, because part of its
measured quality had been future clicks in `engage_sim`, `user_read` and `user_scroll`. The leaky
arm fell less, since it still holds the lifetime aggregates. So the system became more honest and
the measured cost of honesty rose. The conclusion is unchanged and slightly stronger.

The leaky columns are `total_inviews`, `total_pageviews`, `total_read_time`, which aggregate an
article's whole lifetime including time after the impression.

**The story is how small +0.0264 is.** A1 measured the same class of feature at +0.042 (EB-NeRD
small) and +0.075 (demo). A1 was comparing leaky popularity against a system with **no**
popularity signal; here it competes with `pop_causal`. So most of what lifetime popularity
provided is legitimately obtainable. Cheating is worth +0.0264; the honest behavioural axis is
worth +0.1991, about 7.5 times more.

**MIND cannot run this comparison at all.** `total_inviews`, `total_pageviews` and
`total_read_time` are 100% null across all 65,238 MIND articles, so this is an EB-NeRD result.
`q9.py` now refuses on a dataset with no leaky feature file rather than silently comparing a
model against itself.

**Put end to end, the honest system beats the leaky one outright, and not narrowly.** Measured
through the full Q5 harness, where `rerank` uses only pre-impression features and
`fused+popularity` adds lifetime `total_inviews` on top of stage one:

| | val AUC | test AUC |
|---|---|---|
| rerank (servable) | **0.7575** | **0.7429** |
| fused+popularity (**not** servable) | 0.5784 | 0.5797 |

A1 framed giving up the leak as "the cost of honesty". At the two-stage level that framing no
longer holds: the behavioural axis done causally is worth roughly **four times** what the leak
was worth, so honesty costs nothing here. It only looked expensive while the comparison was
between single-signal retrieval systems. The one slice that resists this is head articles
(0.7192 leaky vs 0.7046 honest), which is precisely where lifetime popularity is most
informative.

**Enforcement.** `tests/test_leakage.py::test_no_scorer_reads_a_serving_unavailable_column` fails
if any scoring module names those columns. `src/features/leaky.py` is allow-listed because
producing this row is its only purpose. `src/pipeline/` is out of scope: carrying the columns
into the corpus is what lets the comparison exist at all.

---

## 6. Methodology findings worth a paragraph each

These are the observations that generalise beyond this assignment.

**Pooled AUC systematically overstates features that vary across impressions rather than within
them.** Measured on val: `recency` reads **0.5861 pooled but 0.5087 per impression**;
`user_read` and `hist_len` are constant within an impression and score **exactly 0.5000** per
impression while reading 0.4868 and 0.5154 pooled. Candidates inside one impression are all
roughly the same age, so the pooled number was measuring cross-impression variation, which the
ranking is not judged on.

**Feature importance is not feature contribution.** `recency` has the third-highest LightGBM gain
(161,327, behind only `pop_causal` and `engage_sim`) and an ablation delta indistinguishable from
zero. The model does split on it, but the information is available elsewhere: a fresh article has
had less time to accumulate clicks, so `pop_causal` already encodes most of it. Reporting gain
instead of an ablation delta would have claimed a contribution that is not there.

**One metric name, two definitions, three times.** The full third case is in 9.2 and the
history-file case in 9.1; the first is below. `bm25.py` printed a **hit-rate@200** (share of
impressions with at least one clicked article retrieved) labelled as recall@200 (mean of
found/clicked). They reconcile exactly: 0.0333 x 0.6775 = 0.0226. They agree only when
impressions have one click, and MIND is 28.8% multi-click against EB-NeRD demo's 0.5%, which is
why the number failed to reproduce on exactly one dataset. The same shape is still open for MRR:
official 0.3198 against our offline 0.3548, likely first-click versus all-clicks.

**Underpowered is not a synonym for zero, and a small tier cannot tell them apart.** Four
EB-NeRD ablation cells were measured at demo scale (11,777 articles, 6,872 val impressions) and
two of them spanned zero. Re-run at `ebnerd_small`, those two resolved in **opposite**
directions: the field ablation's effect was real and simply unresolvable (+0.0009 [-0.0062,
+0.0081] became +0.0025 [+0.0002, +0.0047]), while Danish stemming's was genuinely absent
(ranking flat within ±0.0004 at intervals tight enough to have seen a fifth of that effect).
Writing both up as "inconclusive" would have been true and useless. The operational rule: any
ablation whose interval spans zero at demo scale gets re-run at `small` before a verdict is
recorded, never written off.

**Five vacuous checks found in this codebase**, plus a sixth near-miss caught by injection
before it could matter (9.4). A test that passes without asserting anything is
worse than no test. (1) The MIND history-time leakage assertion guarded on dtype, but MIND's
empty timestamp lists come back as `List(Datetime)` not `Null`, so it never skipped, every
`list.max()` was null, `null >= t` is null, the filter dropped every row and it reported green
over 95,071 of 95,071 rows. (2) The Q9 serving-unavailable guard globbed paths that stopped
existing at the A1-to-`src/` port and scanned **zero files**. (3) An install script recorded
`TF_OK=1` from pip's exit code while `import tensorflow` was broken throughout. (4) A job waiter
used `pgrep -f` with a pattern that matched its own command line, so it reported a finished build
as still running. **(5)** Neither leakage test covered the engagement arrays, so the future-click
contamination in 9.1 survived a suite of nineteen passing tests, on 99.8% of val impressions.
**Every assertion now states what it checked and fails if that count is zero**, and every leakage
guard is verified by injecting a violation and confirming it fires.

The pattern across all five is the same and it is worth naming: **each check verified a proxy
rather than the artifact.** A dtype instead of the values, a glob instead of the files it should
have matched, an exit code instead of the import, a process pattern instead of the job, a
timestamp column instead of the array actually fed to the model. The rule adopted is that a test
is not done until a violation has been injected and watched to fail.

---

## 7. Serving and scale (Q4)

### 7.1 Measured, laptop-yash (**8 physical / 12 logical cores**, no GPU, 15.3 GB RAM)

**Not a correction, two different machines.** This was filed as a correction to `CLAUDE.md`'s
"20 cores". That note describes laptop-naman, an i7-13700H with 14 physical and 20 logical
cores, and 20 is right for it. These numbers ran on laptop-yash, which reports 8 physical and
12 logical. Capacity below is priced off 8, the physical count of the machine it ran on, because
this path is dense float work in BLAS and LightGBM where a hyperthread shares an execution port
and adds much less than a real core. Nothing earlier needs rescaling: no prior figure was
scaled by this box's core count.

| stage | dataset | wall | peak RSS |
|---|---|---|---|
| temporal split | EB-NeRD small | 41.5 s | **9.69 GB** |
| temporal split | MIND small | 7.0 s | 1.28 GB |
| BM25 index + score, 3 splits | EB-NeRD small | 100.7 s | 7.15 GB |
| BM25 index + score, 3 splits | MIND small | 258.2 s | 1.96 GB |
| embeddings + FAISS, 3 splits | EB-NeRD small | 88.4 s | 7.04 GB |
| embeddings + FAISS, 3 splits, incl. encoding 65,238 articles | MIND small | 967.8 s | 2.50 GB |
| leakage suite, 19 tests | all dev tiers | 28.2 s | |

`make split` across all three datasets in one process is **OOM-killed** on this box. Per-dataset
invocation is fine. This is a real deployment constraint, not a curiosity.

### 7.2 Measured, cluster node (RTX 2080 Ti, 40 cores, 128 GB)

| stage | wall | peak RSS | vs laptop |
|---|---|---|---|
| temporal split, EB-NeRD small | | 9.93 GB | comparable |
| BM25, EB-NeRD small, val+test | 73.1 s | 7.23 GB | 1.4x faster |
| embeddings, EB-NeRD small, val+test | 70.3 s | 7.14 GB | 1.3x faster |

**Cross-machine reproducibility**: BM25 recall@200 and emb recall@200 on EB-NeRD small test came
out **identical to four decimal places** on both machines (0.0248 and 0.0278), despite different
numpy (2.4.6 vs 2.2.6) and scikit-learn (1.9.0 vs 1.7.2) versions.

### 7.3 Q4, measured (EB-NeRD small, laptop, `make bench`)

Full report in `results/bench_ebnerd_small.md`, ledger rows in `FACTS.md` section 9.

**Q4.1 Index footprints.** RAM and serialised on-disk measured separately, which is what the
professor asked for in the A1 viva.

| Index | Scale | RAM | On disk | RAM/disk |
|---|---|---|---|---|
| BM25 (`bm25s` CSR) | 297,145 postings, 30,388 terms | 7.0 MiB | 3.0 MiB | 2.32x |
| FAISS `IndexFlatIP` | 20,738 x 768-d float32 | 60.8 MiB | 60.8 MiB | 1.00x |
| Feature store (parquet) | 5,514,689 candidate rows | 294.5 MiB | 115.7 MiB | 2.55x |

FAISS is 1.00x because a flat index *is* its raw matrix, so there is nothing to compress or
reconstruct. The other two differ because parquet and CSR both store compressed on disk and
expand on load. The dense 60.8 MiB is also the largest single index despite covering the
fewest objects, which is what makes stage two's ANN cost dominate below.

**Q4.2 Single-request latency**, unbatched, one impression at a time end to end.

| Stage | p50 | p95 | **p99** | share of p50 |
|---|---|---|---|---|
| tokenise | 0.70 ms | 1.22 ms | 3.13 ms | 3% |
| bm25 | 1.36 ms | 5.64 ms | 8.16 ms | 6% |
| **ann** | **13.55 ms** | **33.37 ms** | **45.41 ms** | **61%** |
| features | 0.32 ms | 0.53 ms | 1.18 ms | 1% |
| rerank | 5.02 ms | 11.68 ms | 29.47 ms | 23% |
| **total** | **22.06 ms** | **48.94 ms** | **64.90 ms** | |

**Q4.3 Cost per 1000 queries at p99 < 100 ms.** The SLA is **met, with 1.5x headroom**.
Serial throughput one core: **45 QPS, measured**. Whole box at 8 physical cores: 363 QPS,
**projected** on the assumption that requests are independent and scale linearly.
**$0.000245 per 1000 queries, projected** at an assumed $0.040/vCPU-hour; the price is an
assumption, only the latency it multiplies is measured.

**Q4.4 What breaks first at 10x: `ann`, and this overturns A1's answer.** The corpus is
subsampled and every stage re-timed, rather than extrapolated from one point under an assumed
growth law.

| Corpus | Articles | FAISS RAM | ann p50 | total p50 | total p99 |
|---|---|---|---|---|---|
| 10% | 2,074 | 6.1 MiB | 0.59 ms | 2.53 ms | 4.52 ms |
| 25% | 5,184 | 15.2 MiB | 1.18 ms | 3.29 ms | 5.85 ms |
| 50% | 10,369 | 30.4 MiB | 2.16 ms | 4.58 ms | 8.54 ms |
| 100% | 20,738 | 60.8 MiB | 11.39 ms | 20.06 ms | 33.47 ms |

`ann` grows **19.4x for a 10x corpus**, super-linear where `IndexFlatIP` should be at worst
linear. The excess is the memory hierarchy: 6.1 MiB of vectors is cache-resident, 60.8 MiB is
not, so each query goes from cache to streaming from RAM. **At 10x the catalogue this is a
bandwidth problem, not a FLOPs problem.**

**A1 concluded the per-impression Python loop was the bottleneck rather than the linear
algebra.** With stage two in the path that is no longer true: every Python-side stage is roughly
flat in corpus size, so its share *shrinks* as the catalogue grows, and making the re-ranker
faster buys nothing at scale. The only lever that matters is replacing the exact index with an
approximate one. That is the ANN row A1 measured and rejected as "10 to 20x faster but exact search was
never the bottleneck at this scale", explicitly flagging a revisit at 10x. **This is that
revisit and it says the opposite. ANN belongs on the A2 queue.**

**Limitation, disclosed rather than buried.** Subsampling the corpus also shortens the query,
because the query is built from history titles and a subsampled-out article contributes none:
the mean number of last-30 history items still resolving to a title falls **29.2 -> 2.3** from
full corpus to 10%. So the `tokenise` and `bm25` growth factors conflate two variables and are
**upper bounds** on the corpus effect, not estimates of it. `ann` is unaffected, since a FAISS
scan costs vectors x dim whatever the query contains, which is why the verdict rests on it.
Isolating the other two needs a bench that holds the query fixed while shrinking only the index.

**Run-to-run variance.** Two full bench runs an hour apart gave end-to-end p99 of 78.16 ms and
64.90 ms, and re-ranker training of 47.5 s and 97.8 s, on an otherwise-busy laptop. The second
is the recorded run. Treat single-run timings from this machine as good to roughly ±20%, and
never compare one against a cluster number.

### 7.4 Carried from A1, useful for the scaling argument

Submission at full scale: EB-NeRD testset, 13.5M impressions / 205,925,868 pairs, 13 m 30 s at
~16.7k impressions/s with flat peak RSS; MIND large test, 2.37M impressions, 4 m 38 s at 2.0 GB.
Streaming in 200k-impression slices keeps peak RSS flat against dataset size; slice pushdown
reaches the parquet row groups, so an offset-13M slice costs the same as one at offset 0. CSV has
no slice pushdown, which is why MIND needed a one-off TSV to parquet conversion.

---

### 7.5 Still to measure

- **Every Q4 number above is EB-NeRD.** MIND has no feature store or re-ranker built locally, so
  MIND index footprints, latency and cost/QPS are still TO MEASURE.

## 8. Data

| dataset | articles | impressions train/val/test |
|---|---|---|
| EB-NeRD demo | 11,777 | 17,852 / 6,872 / 25,356 |
| EB-NeRD small | 20,738 | 168,522 / 64,365 / 244,647 |
| EB-NeRD testset | 125,500 | 13.5M, no labels |
| MIND small | 65,238 | 95,071 / 61,894 / 73,152 |
| MIND large test | 120,961 | 2.37M, no labels |

Feature matrix, EB-NeRD small: 1,882,518 / 703,229 / 2,928,942 candidate rows, 9.19% positive.

Splits are temporal, never random. EB-NeRD boundaries: train from 2023-05-18 07:00, val from
05-23 07:00, test from 05-25 07:00. MIND: last calendar day of train.tsv to val, dev.tsv held out
as test.

Article vectors: `Ekstra_Bladet_contrastive_vector` 768-d (provided) for EB-NeRD,
`all-MiniLM-L6-v2` 384-d (self-encoded, 967.8 s on CPU) for MIND. Both chosen by measurement in
A1.

---

## 9. Honest gaps and open questions

**Everything in section 2 and 3.1 is EB-NeRD only.** MIND has no `published_time`, no per-click
history timestamps and no engagement columns, so `recency`, `age_hours`, `engage_sim`,
`user_read` and `user_scroll` cannot be computed there. Five of ten features are unavailable.
The two datasets therefore need explicitly separate configurations, and the report must say which
features are active on each rather than presenting one "system" that is quietly two. **The MIND
re-ranker is not yet built.**

**~~Yash's EB-NeRD ablation verdicts are demo-scale.~~ Done 2026-09-08.** Both re-ran at
`ebnerd_small`; see 3.2 and `ABLATIONS.md` 6c/7c. One verdict reversed and one hardened, which
is itself the power lesson in section 6. **Quote 6c/7c, not 6b/7b.**

**Q4 is measured for EB-NeRD but not MIND**, because MIND has no locally-built feature store or
re-ranker. Section 7.5.

**ANN is now an open item, not a closed one.** A1 rejected approximate indexes as unnecessary;
the 10x curve in 7.3 says exact search is the only thing that breaks. Nobody has yet measured
what recall an IVF or HNSW index would cost us at this catalogue size, so the replacement is
motivated but unquantified.

**The `tokenise`/`bm25` scaling factors are upper bounds, not estimates**, because subsampling
the corpus also shortens the query (7.3). The `ann` verdict is unaffected, but if the report
quotes those two growth numbers it must quote the caveat with them.

**Q3 is not done.** NRMS reproduction is in progress; the environment took five attempts because
`ebnerd-benchmark` is TensorFlow with pins that conflict with our pipeline, and the cluster has no
usable PyPI access.

**Open, unexplained.** EB-NeRD BM25 recall@200 was more than 2x better at history N=1 than at any
larger N in A1, while MIND improves monotonically with more history. **The claim that a semantic
N sweep confirmed this is withdrawn** (see 9.1): that sweep scored on contaminated history, and on
clean history the order reverses, N=30 beating N=10. So the anomaly stands entirely on the A1
lexical measurement and has no independent confirmation. The mechanism is unknown, and the
`info.md` low-quality-click hypothesis is neither supported nor refuted, because the weighting
result that was read as refuting it came from the same contaminated sweep.

**RESOLVED, was "the 0.6473 against 0.5506 gap".** It was neither the `history_len: 30`
truncation nor a normalisation difference. The two implementations read **different history
files**, and one of them was reading the future. Full account in 9.1 and `FACTS.md` section 10.

**RESOLVED, was "MIND official MRR 0.3198 against our offline 0.3548".** First-click against
all-clicks reciprocal rank, confirmed by measurement. See 9.2 and `FACTS.md` section 11.

---

## 9.1 The leakage found on 2026-09-08, and what it costs

**This is the most consequential finding of the day and it changes how several numbers above
must be read.** Full evidence and reproduction in `FACTS.md` section 10. Found while chasing the
0.6473 against 0.5506 gap, which turned out to be a symptom rather than the problem.

### What went wrong, in plain terms

EB-NeRD ships the dataset in two blocks, `train` and `validation`, and **each block has its own
`history.parquet`** describing what users clicked *before that block starts*. The feature builder
loaded both and let the second overwrite the first, for the 11,658 users appearing in both.

That would be harmless if our splits matched the blocks. They do not. Our **val split is carved
out of the train block**, so a val impression ended up being described by history collected up to
the *validation* block's start, which is later. The model was told what the user would click
after the moment it was supposed to be predicting.

### Measured

| split | impressions | matched to validation-block history | with history at or after the impression |
|---|---|---|---|
| train | 168,522 | 144,087 | **143,998 (99.9%)** |
| val | 64,365 | 61,026 | **60,901 (99.8%)** |
| test | 244,647 | 244,647 | 0 (0.0%) |

**Test is clean**, because test comes from the validation block, so that block's history genuinely
precedes it. Train and val are not.

Confirmed by making one implementation produce both disputed numbers with only the history source
varying, rather than by argument:

| history source | N=10 | N=30 |
|---|---|---|
| train + validation blocks merged | **0.6473** | 0.6250 |
| train block only, causally valid | 0.5416 | **0.5506** |

The top-left cell reproduces the sweep exactly; the bottom-right reproduces the `emb` feature
exactly. **The leak is worth +0.0967 AUC on that one feature.**

### What this invalidates

1. **The history sweep's headline.** With the leak the curve peaks at N=10; with clean history
   the order **reverses**, N=30 beating N=10. The "peak at small N" was an artefact. Section 4's
   rejection of read-time weighting came from the same sweep and should be re-checked on clean
   history before it is quoted.
2. **Three of the ten re-ranker features.** `build()` calls the engagement loader with no split
   argument, so `engage_sim`, `user_read` and `user_scroll` are not causally valid on train or
   val. `hist_len` and the six stage-one and popularity features are unaffected.
3. **Every val-selected number in sections 3.1 and 5.** The 13-arm ablation grid, `engage_sim`'s
   +0.0085, LightGBM's early-stopping iteration count, and Q9's +0.0222 are all val figures
   computed on contaminated features. **They need re-running before they go in the report.**

### What survives, stated so this is not over-claimed

**The headline is not retracted.** On test, where the features are clean, `rerank - fused` is
**+0.2049** [+0.2034, +0.2064] against +0.2047 on val, and test `rerank` AUC is 0.7429. The claim
that the behavioural axis is worth about +0.20 AUC does not rest on the leak. This is a
correctness fix with a bounded blast radius, not a collapse of the result.

### Status and ownership

**Fixed, 2026-09-08**, in the lane that owns it. The engagement loader now takes the split and
reads one block, chosen from the same `early_root` / `test_root` config keys `split.py` uses so
the two cannot drift apart. The merge loop is gone.

Confirmed by running both paths side by side on EB-NeRD small val: the fixed source gives 0
violations over 64,365 matched impressions, the block the merge used to select gives 60,901 of
61,026 at 99.8%, reproducing the measurement above exactly.

The missing assertion now exists: `tests/test_features_leakage.py` joins each split's
impressions against the history block that split actually reads and requires no click at or
after the impression using it, with an injection companion that must fail. The block-per-split
rule is restated in the test rather than imported, so a regression in the loader cannot take the
test with it.

What this does not do is re-run anything. Every val-selected figure listed above was measured on
contaminated features and still needs regenerating.

## 9.2 MIND MRR: first click against all clicks

`FACTS.md` section 11. Our offline 0.3548 against the leaderboard's 0.3198, while AUC and both
nDCGs rose. **Third instance in this project of one metric name covering two definitions.**

MIND's official scorer averages the reciprocal rank over **every** clicked article. Ours credited
only the best-placed one. Measured on MIND small test with BM25, 73,152 impressions:

| definition | MRR |
|---|---|
| first clicked article only (ours) | **0.3108** |
| mean over all clicked articles (MIND official) | **0.2693** |
| paired difference | **-0.0415** [-0.0423, -0.0405] |

**AUC (0.5685) and nDCG@10 (0.3479) are identical under both**, because neither reads which click
came first. That is exactly the reported signature of MRR falling while AUC and the nDCGs rose.

The effect is **entirely multi-click**: the 71.2% of impressions with one click score identically
under both definitions, maximum absolute difference exactly 0.0, and the 28.8% with more than one
go 0.3095 to 0.1657. On EB-NeRD, at 0.5% multi-click, the two definitions differ by only 0.0005.
**The size of the discrepancy is a property of the dataset, not of the ranker.**

**The arithmetic cannot be closed exactly, and the report should say so** rather than implying a
reconciliation: 0.3548 was MIND *small* test and 0.3198 was MIND *large* test, whose click
distribution we cannot observe. Measured ratio 0.867 against the observed 0.901, same direction
and magnitude.

`eval.metrics.mrr_all` now implements the official definition and both columns are reported.
Neither is swapped in for the other, because they answer different questions: `mrr` asks how fast
the user finds something they wanted, `mrr_all` asks how well the whole clicked set is placed.
**When quoting against a MIND leaderboard number, use `mrr_all`.**

## 9.3 Slice thresholds: the trap that did not fire

`FACTS.md` section 12. Over 90% of articles in both datasets have zero train clicks, so a
percentile taken over the whole catalogue would be **0**, and a `>=` comparison would classify
every impression as head. Checked directly rather than assumed.

| dataset | articles with 0 train clicks | head threshold | head | tail | cold threshold | cold | warm |
|---|---|---|---|---|---|---|---|
| MIND small | 60,192/65,238 (92.3%) | 152 clicks | 860 (1.2%) | 72,292 (98.8%) | 3 | 7,529 | 65,623 |
| EB-NeRD small | 19,272/20,738 (92.9%) | 349 clicks | 803 (0.3%) | 243,844 (99.7%) | 34 | 25,105 | 219,542 |

The guard is that `eval.slicing.by_article_popularity` takes the percentile over articles
**actually seen in train**, excluding the zeros. The hazard is real on both datasets and this is
what defuses it.

**The head slice is small**, 860 and 803 impressions, just above the harness's 30-impression floor
for reporting a slice at all, so its intervals are wide and its differences are indicative only.
This is why slice sizes are printed in every table, and it is the direct answer to a viva question
about what "head" meant. MIND additionally has a `zero_history` slice of 2,214 impressions;
EB-NeRD small has none, its cold decile starting at 34 clicks.

## 9.4 Q7: what was actually submitted

`FACTS.md` section 13, design-note section `docs/report/q7-leaderboard-submissions.md`.

| | MIND | EB-NeRD |
|---|---|---|
| impressions | **2,370,727** | **13,536,710** |
| archive | `mind_prediction.zip`, 107.3 MB | `ebnerd_predictions.zip`, 230.0 MB |
| inner filename | `prediction.txt` (singular) | `predictions.txt` (plural) |
| validated offline | yes, all checks | yes, all checks |

Build cost for the EB-NeRD full test set on the laptop: **6 m 28 s, peak RSS 5.90 GB**, about
34,900 impressions/s. Peak RSS is flat against dataset size because the stream reads in slices;
the 5.90 GB is dominated by the 125,500 x 768 article matrix, not by the impressions.

**The uploaded system is the embeddings-only scorer, which is not our headline system.** On
EB-NeRD small test it reads 0.5397 AUC against `fused` 0.5380, `bm25` 0.5107 and the two-stage
`rerank` **0.7429**, so the leaderboard entry sits roughly 0.20 AUC below the system this document
describes. The gap is structural: the re-ranker's features need `pop_causal` and the engagement
columns, which the held-out test sets do not ship in a usable form. BM25 was excluded separately
for cost, measured at roughly 1.6 h for MIND-large's 2M distinct histories. **Reported as two
different systems rather than letting the better offline number stand in for the uploaded one.**

**Upload and screenshots are still outstanding** and need a Codabench login. MIND allows one
submission per day, so that clock matters.

### A sixth structural check, and a sixth near-miss

`src/submission/validate.py` checks inner filename, zip contents, row count, row order and that
every row is a permutation of 1..n, offline, before upload. Row order is the check that earns its
keep: ranks are **positional** against the test file's candidate order, so a correctly-ranked but
reordered file scores as a plausible bad model rather than erroring. A previous submission on this
project covered 0.84% of the test set and scored 0.5012, exactly random.

**Verified non-vacuous by injecting five violations** (wrong inner filename, two rows swapped,
truncation to 420 of 50,000 rows, a duplicated rank, a folder inside the zip); all five exit 1 and
the real file exits 0. **It immediately caught a real bug**, a path in the validator itself that
read `behaviors.parquet` where the bundle nests it under `test/`. A validator that reads a
different file from the writer validates nothing, which is the same family as the vacuous tests in
section 6.

## 9.5 The four unswept constants, measured (2026-09-12 to 09-13)

`FACTS.md` section 16 carries the tables. Three of the four are **isolated-feature**
measurements, the same protocol as the history sweep: per-impression AUC of the one feature
alone. An isolated number cannot be absorbed by a correlated neighbour the way a LightGBM
ablation arm can, which is the point, but it also means a winner there is a candidate for a
ranker-level check rather than a shipped result.

**The causal popularity window is the largest unshipped finding in the project.** Currently
unbounded. A 6 hour window scores 0.7349 against unbounded's 0.6902 in isolation, **+0.0447**,
larger than every per-feature effect in the 13-arm grid except `pop_causal` itself. The curve is
single-peaked: 1 h is too noisy, and past 72 h it converges to unbounded because in a two-day
EB-NeRD window almost every click already falls inside 168 h.

Read plainly, this says the shipped feature measures the wrong thing. "How popular has this
article ever been" is a worse signal for news than "how popular is it right now". Since
`pop_causal` is the feature the whole system leans on, a ranker-level ablation with a paired CI
is required before changing it, and that is in progress.

**The recency half-life does not matter and the sweep says why.** Flat to four decimals from 1 h
to 168 h, a 168x range, because the feature barely ranks at all in isolation: 0.5088 against a
0.5 floor. This agrees with the grid, where `minus_recency` is indistinguishable from zero on both
splits. `build.py` described 24.0 as "a starting value, swept as its own ablation"; the sweep has
now happened and the honest conclusion is that the choice is irrelevant, not that 24 is optimal.

**`info.md` item 4 is supported where item 1 was not.** Filtering history to entries with scroll
completion at or above 90% gains +0.0064 over no filter while discarding 59% of the history, and
the effect is monotonic above a 25% threshold. `info.md` explicitly claimed item 4 "complements
rather than duplicates" read-time weighting, and that distinction now has evidence on both sides:
the weighting was rejected, the quality filter was not. Two qualifications: the dip at a 10%
threshold (0.5521, below no-filter) is unexplained, and keeping the best 41% of 100 items may be
partly the profile-size effect from 9.1's re-run rather than click quality, which needs a
threshold-by-N grid to separate.

**lambdarank beats a binary objective by +0.016**, [+0.0150, +0.0173] val and [+0.0159, +0.0171]
test, both significant, intervals overlapping. This one is a ranker-level result, not isolated.
`train.py` justified lambdarank on the argument that the objective should match the task; that is
now measured rather than asserted. The binary arm's feature importances reorder sharply, with
`recency` and `age_hours` taking the top gain slots ahead of `pop_causal`: a pointwise objective
leans on absolute freshness, a pairwise one on the within-impression contrast that actually
decides the ranking.

