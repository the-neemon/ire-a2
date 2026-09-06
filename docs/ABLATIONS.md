# ABLATIONS

One row per experiment, **including every rejected one**. This file is the direct evidence for the
"ablation rigour" component of the grade and is the first thing the design note draws from.

**Rules.**

- Change **one** thing per row. If two things moved, it is two rows or it is not an ablation.
- Every claimed gain ships a **paired bootstrap 95% CI on shared resamples** that excludes zero.
  Paired, because two systems scored on the same impressions have correlated errors and independent
  intervals are far too conservative.
- **Record the cost, not just the gain.** Build time, index bytes, query latency, peak memory. A gain
  with no stated cost is an incomplete result.
- **A rejected experiment stays in this file.** Deleting it destroys graded work. The negative result
  with a reason is often more interesting than the win.
- Selection happens on val. Test is scored once. Say which split a number came from.

Status values: `planned`, `running`, `shipped`, `rejected`, `inconclusive`.

---

## A2 queue

Ranked by expected value. Each is an ablation to measure, not just a feature to ship: land it behind
a flag and measure it against the system without it.

| # | Hypothesis | Dataset | Delta | 95% CI | Cost | Status |
|---|---|---|---|---|---|---|
| 1 | Causally valid popularity (clicks strictly before impression t) recovers most of the +0.075 the leaky lifetime version buys | both | | | | planned |
| 2 | Geometry correction (centre / abtt:n / whitening) on article vectors fixes the +0.9503 mean pairwise cosine | EB-NeRD | | | | planned |
| 3 | Recency prior: exponential decay on article age at impression time | both | | | | planned |
| 4 | GBDT re-ranker over engineered features beats single-signal ranking (Q2) | both | | | | planned |
| 5 | Hybrid BM25 + semantic with a `history_len` router beats either alone | both | | | | planned |
| 6 | Per-language stemming: Snowball Danish on, English off | MIND | see 6a | | vocab 44,264 -> 60,914; build 5.2 -> 4.1 s | **rejected** |
| 6 | Per-language stemming: Snowball Danish on, English off | EB-NeRD demo | see 6b | | vocab 22,105 -> 31,515; build 0.9 -> 0.6 s | **inconclusive** |
| 6 | Per-language stemming, re-measured at 10x | EB-NeRD small | | | | planned |
| 7 | BM25 documents title-only rather than title + abstract | MIND | see 7a | | vocab 44,264 -> 24,681; build 4.5 -> 1.9 s | **shipped-pending** |
| 7 | BM25 documents title-only rather than title + abstract | EB-NeRD demo | see 7b | | vocab 22,105 -> 10,738; build 0.7 -> 0.5 s | **rejected** |
| 7 | Field choice, re-measured at 10x | EB-NeRD small | | | | planned |
| 9 | Re-sweep `history_len` after 2 and 7 land | both | | | | planned |
| 10 | Better MIND article vectors than 87%-coverage mean-pooled entities | MIND | | | | planned |
| 11 | Q3 required: one principled improvement over the reproduced NRMS baseline | both | | | | planned |

### 6 and 7 in full — BM25 field and stemming, measured 2026-09-04

Both were carried into the A2 queue as *partially* measured: A1 had numbers for each, but on a
different codebase and a different scale, and neither had a paired CI. This is that
re-verification. Every row below comes from `src.eval.ablate_bm25`, which scores both variants on
the identical impressions and reuses the same 1,000 bootstrap resamples for the difference.
Machine: laptop. Reports under `results/ablation_bm25_*`.

**Read the deltas in the stated direction.** Each is `variant - baseline`, and each names its own
baseline, because the two ablations happen to share one.

Two metric families are reported for every cell, and they disagree often enough that quoting only
one would be the mistake:

* **AUC / MRR / nDCG** re-rank the pool the log already showed. Both Codabench competitions score
  this, so it is the metric a shipping decision defaults to.
* **recall@K** is candidate generation from the whole catalogue, ignoring the shown pool. This is
  what Q2's two-stage pipeline consumes: an article the retriever never surfaces cannot be
  re-ranked into the answer no matter how good the re-ranker is.

#### 6a. English stemming on MIND — **rejected**, keep stemming on

Delta of turning stemming **off**, baseline is stemming on.

| split | AUC | nDCG@10 | recall@200 |
|---|---|---|---|
| val | **-0.0023** [-0.0034, -0.0013] | -0.0008 [-0.0018, +0.0001] | **+0.0021** [+0.0013, +0.0028] |
| test | **-0.0028** [-0.0039, -0.0018] | **-0.0011** [-0.0020, -0.0002] | **+0.0009** [+0.0004, +0.0014] |

Selected on **val AUC**, which says keep stemming: turning it off is a significant loss. Test
agrees, and was scored once after the rule was fixed.

The interesting half is that the two metrics point opposite ways and both are significant.
Stemming helps re-ranking and *hurts* retrieval, consistently, on both splits. Collapsing
surface forms merges genuinely distinct English words, which costs precision when the job is to
pick 200 articles out of 65,238; within a pool of a few dozen already-plausible candidates that
same merging instead recovers matches an exact comparison misses. Recorded rather than resolved:
if the Q2 re-ranker ends up bottlenecked on retrieval recall, this decision should be re-opened
for the retrieval stage alone, which the `stem` flag now makes a one-line change.

**Both A1 systems are reproduced, and they were already saying this.** A1-naman measured
+0.0019 AUC and -0.0023 recall@200 for stemming on MIND and shipped it AUC-motivated; this run
gives +0.0023 and -0.0021 on val, on a different codebase. A1-yash measured the recall side as
-3.1% / -2.3% relative; converting this run to relative gives -5.1% on val and -3.4% on test.
Same sign, same order of magnitude, from three independent measurements.

What the A2 queue got wrong was not the measurement but the *conclusion* drawn from it. Item #6
was written as "Snowball Danish on, English off", reading A1-yash's recall loss as a reason to
disable English stemming while A1-naman's AUC gain sat in the same file. Both numbers were right;
they simply answer different questions, and only pairing them per split with a CI makes the
trade-off legible. The hypothesis as stated is what is rejected here, not either A1 number.

#### 6b. Danish stemming on EB-NeRD demo — **inconclusive on accuracy**, kept on cost

Delta of turning stemming **off**, baseline is stemming on.

| split | AUC | nDCG@10 | recall@200 |
|---|---|---|---|
| val | -0.0025 [-0.0077, +0.0025] | -0.0012 [-0.0052, +0.0030] | +0.0006 [-0.0036, +0.0050] |
| test | +0.0003 [-0.0025, +0.0029] | +0.0002 [-0.0020, +0.0024] | -0.0014 [-0.0037, +0.0004] |

Every interval contains zero except test recall@100 (-0.0016 [-0.0031, -0.0002], favouring
stemming). Kept **on**, on the cost side rather than the accuracy side: it is free and it shrinks
the vocabulary 31,515 -> 22,105.

**This is the queue's largest miss against its prior and it is worth stating plainly.** A1
predicted +22 to +36% on recall@200 from Danish stemming. Measured here: +1.4% relative at
demo scale, not significant. The prior is off by more than an order of magnitude.

Ruled out before reporting it, per the pre-registered check that an unexpected direction is a
wiring bug until proven otherwise. The toggle demonstrably works: with it on, `spilleren` ->
`spil`, `håber` -> `håb`, `stadig` -> `stad`, `fortsætte` -> `fortsæt`; with it off the full
forms survive, and the vocabulary moves 22,105 -> 31,515 accordingly. A single stemmer object is
threaded through both `bm25s.tokenize` call sites, so documents and queries can never disagree.
The direction is also not inverted, just tiny, which is a weaker signal of a bug than a sign flip.

The most probable explanation is that this pipeline **already applies a Danish stopword list**,
which A1 separately measured as worth 0.5035 -> 0.5232 AUC. Stopword removal and stemming
compete for the same wins: both collapse high-frequency surface variation, so whichever runs
first takes the credit. A1's stemming number was very likely measured against a baseline that
had no stopword list, making it the *combined* effect of both. Not yet tested directly.
`stem x stopwords` as a 2x2 is the obvious follow-up and is cheap here (four ~1 s index builds),
but it is a second changed variable and therefore a separate ablation, not this row.

#### 7a. MIND documents title-only — **shipped-pending**, one decision short

Delta of dropping `abstract` from the indexed document, baseline is title + abstract.

| split | AUC | MRR | recall@200 |
|---|---|---|---|
| val | **+0.0024** [+0.0006, +0.0041] | **-0.0022** [-0.0039, -0.0005] | **+0.0017** [+0.0007, +0.0028] |
| test | **+0.0065** [+0.0047, +0.0083] | +0.0000 [-0.0017, +0.0016] | +0.0006 [-0.0003, +0.0014] |

Reproduces the A1 prior almost exactly: A1 measured +0.0024 AUC and +0.0017 recall@200; this run
gives +0.0024 and +0.0017 on val, to four decimals, on a different codebase. That is the
strongest cross-system agreement anywhere in this file and it is what makes the rest of the row
trustworthy.

A1 recorded "no measured downside". There is one, and it took a paired CI to see: **val MRR
falls -0.0022, significant**. Dropping the abstract wins on average pair ordering while losing on
where the first clicked article lands, so it moves a click that was already ranked well slightly
further down. Small, but it is a cost, and the rule here is that a gain reported without one is
an incomplete result.

Cheaper on every axis: vocabulary 44,264 -> 24,681, index build 4.5 s -> 1.9 s.

Left as `shipped-pending` rather than shipped. The measurement supports the change; changing what
ships is a decision for the team, not one to apply unilaterally from an ablation result, so
`configs/datasets.yaml` still carries `title_abstract` for both datasets.

#### 7b. EB-NeRD demo documents title-only — **rejected**

Delta of dropping `abstract` (EB-NeRD's `subtitle`), baseline is title + abstract.

| split | AUC | recall@100 | recall@200 |
|---|---|---|---|
| val | +0.0009 [-0.0062, +0.0081] | **-0.0033** [-0.0065, -0.0001] | **-0.0049** [-0.0094, -0.0002] |
| test | +0.0028 [-0.0005, +0.0064] | -0.0006 [-0.0023, +0.0011] | -0.0010 [-0.0032, +0.0010] |

Rejected on val, which is where selection happens: AUC is indistinguishable from zero on both
splits, and recall@100 and recall@200 are both significant **losses**. Paying real retrieval
recall for an AUC gain that no interval separates from zero is not a trade worth making, and it
is the wrong direction for a pipeline whose stage 2 depends on stage 1 recall.

This reproduces the A1 EB-NeRD finding in shape (+0.0025 AUC, -0.0024 recall@200) and confirms
its central claim, which is the one that keeps recurring across both A1 systems and now this one:
**more text helps retrieval and hurts re-ranking.** The two datasets want opposite settings for
the same knob, which is precisely why the field is worth making per-dataset rather than global.

#### Scale caveat, stated rather than buried

Every EB-NeRD row above is **demo scale**: 11,777 articles, 6,872 val and 25,356 test
impressions. That is roughly a tenth of `ebnerd_small` and it shows in the intervals, which are
three to five times wider than MIND's. Several EB-NeRD cells are inconclusive *because the split
is small*, not because the effect is zero. `ebnerd_small` re-runs are queued as separate rows and
neither EB-NeRD verdict should be treated as settled until they land.

## A1 results carried forward

Inherited from our Assignment-1 systems. **Not verified at A2 scale or against the A2 pipeline.**
Re-measure before quoting. Kept here because they define what is already known and what not to redo.

### Shipped

| Change | Effect | Dataset | Cost | Source |
|---|---|---|---|---|
| Danish stopword list (`bm25s` ships none) | 0.5035 to 0.5232 AUC | EB-NeRD | none | A1-naman |
| `contrastive_vector` over `word2vec` | +0.0408 val AUC | EB-NeRD | none, both provided | A1-naman |
| `contrastive_vector` over own XLM-R | +0.0197 val AUC | EB-NeRD | avoids self-encoding | A1-naman |
| `history_len` 30 to 100 | +0.0030 emb, +0.0039 bm25 | MIND | longer queries | A1-naman |
| Entity-overlap blend, a=0.20 | val +0.0023, test +0.0022 | MIND | one extra signal | A1-naman |
| Stemming | +0.0019 AUC, **-0.0023 recall@200** | MIND | tradeoff, AUC-motivated | A1-naman |
| Sparse-matrix BM25 over `rank_bm25` | 782x faster (MIND), 497x (EB-NeRD) | both | none | A1-yash |
| Candidates-only restricted scoring | numerically identical, max diff 1.8e-7 | both | none | A1-yash |
| Column-pruned batched parquet reads | peak RSS 10.5 GB to 1.7 GB | both | none | A1-yash |
| Stable `argsort` over `argpartition` | fixes cross-machine nondeterminism | both | slower than partition | A1-yash |

### Rejected. Do not re-run.

| Change | Effect | Dataset | Reason | Source |
|---|---|---|---|---|
| Body text in the BM25 index | **-0.0166 AUC**, vocab 30k to 124k, build 18 s to 29 s | EB-NeRD | large loss; median body 1,830 chars swamps a 60-char title | A1-naman |
| Danish compound splitting | -0.0040 EB-NeRD, -0.0013 MIND, both significant | both | | A1-naman |
| Max-similarity pooling | -0.0030 val AUC, significant | EB-NeRD | **confirmed twice on independent systems** | A1-naman |
| Raw multilingual BERT as encoder | 0.4857 val AUC, below random | EB-NeRD | masked-LM cosine is not topical similarity | A1-naman |
| `bge-base-en-v1.5` | 0.5899 val AUC, -0.0457 vs MiniLM | MIND | | A1-naman |
| `e5-base-v2` | 0.6067 val AUC, -0.0289 vs MiniLM | MIND | | A1-naman |
| `mpnet-base-v2` | -0.0012, not significant | MIND | **rejected on cost**: 2x index size, 2x query time | A1-naman |
| Fusion on EB-NeRD | wins val, significantly loses test (-0.0017) | EB-NeRD | alpha did not generalise | A1-naman |
| RRF instead of linear fusion | lost at every k | both | discarding scores stops it expressing that one parent is worse | A1-naman |
| Time and position decay on click weighting | neutral to harmful at every constant, monotonically worse as decay sharpened | both | | A1-naman |
| BM25 k1/b grid search | +0.001 | both | not where the wins are | A1-naman |
| `rank_bm25` library | 782x / 497x slower | both | | A1-yash |
| ANN indexes (IVF, HNSW) | 10 to 20x faster at >90% recall vs exact | both | exact search was never the bottleneck at this scale; revisit at 10x catalogue | A1-yash |
| English stemming | -3.1% A@200, -2.3% B@200 | MIND | language-dependent, see queue #6 | A1-yash |
| Cold-start popularity fallback | +0.0049, CI [-0.0075, +0.0180] | EB-NeRD | **inconclusive**, underpowered at 1,503 impressions | A1-naman |

### Anti-gaming ablation (Q9, keep reporting both ways)

| Config | AUC | Delta | Dataset | Source |
|---|---|---|---|---|
| clean | 0.5380 | baseline | EB-NeRD small test | A1-naman |
| + lifetime popularity | 0.5797 | **+0.0417** [+0.0408, +0.0426] | EB-NeRD small test | A1-naman |
| BM25 clean | 0.5009 | baseline | EB-NeRD | A1-yash |
| BM25 + lifetime popularity | 0.5760 | **+0.075** | EB-NeRD | A1-yash |
| BM25 + post-interaction | 1.0000 | perfect, obviously leaky | EB-NeRD | A1-yash |
| train-click popularity alone | 0.4498 [0.4485, 0.4510] | **below random** | EB-NeRD test | A1-naman |

`total_inviews`, `total_pageviews` and `total_read_time` are lifetime aggregates over the whole
collection period, so they embed the future and cannot be computed at serving time. No shipped scorer
reads them. The last row is the counterintuitive companion result: the pool the log showed is already
popularity-filtered, so within it, being popular is mildly anti-predictive.


---

## Q1 + Q2: behavioural features and the two-stage re-ranker (EB-NeRD small)

LightGBM lambdarank over 10 per-candidate features, stage one unchanged. Selection on val,
test scored once. Metric is **per-impression AUC**, averaged over the 64,365 val impressions
that contain both classes; pooled AUC is not used and the reason is a row below. Each arm
removes exactly one feature and retrains. CIs are paired bootstrap, 1000 resamples, shared
across arms, seed 13.

**Full model: val 0.7575, test 0.7429.**

| arm | val AUC | full - arm | 95% CI | significant |
|---|---|---|---|---|
| stage1_only (bm25 + emb) | 0.5498 | **+0.2077** | [+0.2048, +0.2107] | yes |
| pop_only (pop_causal alone) | 0.6954 | +0.0620 | [+0.0602, +0.0639] | yes |
| minus pop_causal | 0.7228 | +0.0346 | [+0.0330, +0.0363] | yes |
| minus engage_sim | 0.7489 | +0.0085 | [+0.0075, +0.0096] | yes |
| minus emb | 0.7532 | +0.0043 | [+0.0035, +0.0050] | yes |
| minus cat_match | 0.7537 | +0.0038 | [+0.0028, +0.0048] | yes |
| minus hist_len | 0.7555 | +0.0019 | [+0.0014, +0.0025] | yes |
| minus bm25 | 0.7561 | +0.0014 | [+0.0008, +0.0020] | yes |
| minus user_scroll | 0.7565 | +0.0009 | [+0.0005, +0.0014] | yes |
| minus user_read | 0.7567 | +0.0007 | [+0.0002, +0.0013] | yes |
| minus age_hours | 0.7572 | +0.0003 | [-0.0002, +0.0007] | **no** |
| minus recency | 0.7574 | +0.0001 | [-0.0003, +0.0006] | **no** |

### What the table says

**The behavioural axis is worth +0.2077 AUC over stage one alone.** That is larger than every
Assignment-1 result combined and it is the answer to "what did adding click-log signal buy".

**Causally valid popularity is most of it.** Alone it reaches 0.6954, above any complete A1
system. Removing it from the full set costs 0.0346, the largest single-feature contribution.
The +0.075 that *leaky* lifetime popularity bought in A1 therefore largely survives the causal
restriction, which was the open question that motivated the feature.

**Engagement weighting beats uniform pooling.** `engage_sim` (history embeddings weighted by
`log1p(read_time_fixed)`) is worth +0.0085 over the full set, and standalone it scores 0.5774
against `emb`'s 0.5506 on identical rows. Same computation, different weights, so it is a clean
one-variable comparison. Neither A1 system used the read-time column at all.

**Gain is not contribution, and this is the row to remember.** `recency` has the third-highest
LightGBM gain (161,327, behind only pop_causal and engage_sim) yet removing it changes the
metric by +0.0001, CI [-0.0003, +0.0006], indistinguishable from zero. `age_hours` is the same
story. The model does split on them, but the information is available elsewhere (a fresh article
has had less time to accumulate clicks, so `pop_causal` already encodes most of it). Reporting
importance instead of an ablation delta would have claimed a contribution that is not there.

**Pooled AUC systematically overstates features that vary across impressions rather than within
them.** Measured on val: `recency` reads 0.5861 pooled but 0.5087 per impression; `user_read`
and `hist_len` are constant within an impression and score exactly 0.5000 per impression while
reading 0.4868 and 0.5154 pooled. Candidates inside one impression are all roughly the same age,
so the pooled number was measuring cross-impression variation, which the ranking is not judged
on. Same class as the hit-rate vs recall gap: one metric name, two definitions.

### Not yet done

MIND has no `published_time`, no per-click history timestamps and no engagement columns, so
`recency`, `age_hours`, `engage_sim`, `user_read` and `user_scroll` cannot be computed there.
Per `info.md`'s fairness note the two datasets get explicitly separate feature sets rather than
one system quietly running with zeros on half its inputs. The MIND arm is a separate row, unrun.
