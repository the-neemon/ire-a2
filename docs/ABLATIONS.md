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
| 6 | Per-language stemming: Snowball Danish on, English off | EB-NeRD demo | see 6b | | vocab 22,105 -> 31,515; build 0.9 -> 0.6 s | **inconclusive** (underpowered) |
| 6 | Per-language stemming, re-measured at 10x | EB-NeRD small | see 6c | | vocab 30,388 -> 43,451; scoring 19.2 -> 23.6 s | **rejected**, keep stemming on |
| 7 | BM25 documents title-only rather than title + abstract | MIND | see 7a | | vocab 44,264 -> 24,681; build 4.5 -> 1.9 s | **not shipped** |
| 7 | BM25 documents title-only rather than title + abstract | EB-NeRD demo | see 7b | | vocab 22,105 -> 10,738; build 0.7 -> 0.5 s | **rejected** (underpowered) |
| 7 | Field choice, re-measured at 10x | EB-NeRD small | see 7c | | vocab 30,388 -> 15,132; build 1.0 -> 0.6 s | **verdict reversed**: trade-off, AUC-favourable |
| 9 | Re-sweep `history_len` after 2 and 7 land | both | | | | planned |
| 10 | Better MIND article vectors than 87%-coverage mean-pooled entities | MIND | | | | planned |
| 11 | Q3 required: one principled improvement over the reproduced NRMS baseline | both | | | | planned |

### 6 and 7 in full: BM25 field and stemming, measured 2026-09-04

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

#### 6a. English stemming on MIND: **rejected**, keep stemming on

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

#### 6b. Danish stemming on EB-NeRD demo: **inconclusive on accuracy**, kept on cost

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

#### 7a. MIND documents title-only: **measured, not shipped**

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

Not shipped. The AUC gain is real, but the change was held back for the reason in 7c: it costs
the stage-one recall that the re-ranker consumes. The submitted system indexes `title_abstract`
for both datasets.

#### 7b. EB-NeRD demo documents title-only: **rejected**

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

### 6c and 7c: the same two ablations at `ebnerd_small`, 10x scale, measured 2026-09-08

The EB-NeRD verdicts above were demo scale: 11,777 articles, 6,872 val impressions, with
intervals three to five times wider than MIND's. `README.md` excludes demo from reported
numbers, so these are the rows that count. `ebnerd_small` is 20,738 articles and 64,365 val /
244,647 test impressions. Machine: laptop. Reports under `results/ablation_bm25_ebnerd_small_*`.

**The demo rows are kept above, relabelled `underpowered` rather than deleted.** They are the
evidence for the methodological point that follows, and deleting a superseded measurement
destroys that.

#### 7c. EB-NeRD small, documents title-only: **the demo verdict reverses**

Delta of dropping `abstract`, baseline is title + abstract.

| split | AUC | MRR | nDCG@10 | recall@200 |
|---|---|---|---|---|
| val | **+0.0025** [+0.0002, +0.0047] | +0.0019 [-0.0001, +0.0039] | **+0.0021** [+0.0004, +0.0039] | **-0.0024** [-0.0035, -0.0013] |
| test | **+0.0043** [+0.0031, +0.0055] | **+0.0024** [+0.0014, +0.0034] | **+0.0021** [+0.0012, +0.0030] | -0.0005 [-0.0011, +0.0001] |

At demo scale this was **rejected**: AUC +0.0009 [-0.0062, +0.0081], indistinguishable from
zero, against a significant recall loss. Paying real recall for nothing is a bad trade, and
that was the right call on the evidence then available.

At 10x the AUC gain is **+0.0025 and significant**, and the demo interval turns out to have
contained it comfortably. So the demo result was not a different effect, it was the same effect
measured too imprecisely to see. The verdict changes from *rejected* to **a genuine two-sided
trade-off**: on val, every ranking metric gains significantly and recall@100/@200 lose
significantly. On test the ranking gains hold and grow while the recall losses stop being
significant at all.

**This reproduces the A1 EB-NeRD prior to four decimals on both axes at once.** A1 measured
+0.0025 AUC and -0.0024 recall@200; val here gives +0.0025 and -0.0024. Two independent
systems, different codebases, agreeing to that precision on a two-sided trade-off is the
strongest single piece of cross-validation in this file.

*Does EB-NeRD show MIND's AUC/MRR split?* **No.** On MIND, title-only won AUC while
significantly losing MRR (-0.0022 [-0.0039, -0.0005]), contradicting A1's "no measured
downside". On EB-NeRD small, MRR moves the *same* way as AUC: +0.0019 on val (not significant)
and **+0.0024 on test (significant)**. So the MIND MRR loss is a property of MIND, not of
dropping the abstract, and the two datasets differ in *which* metric pays the cost: MIND pays in
MRR, EB-NeRD pays in retrieval recall. Both were invisible without a paired CI per metric.

Cost, cheaper on both axes: vocabulary 30,388 -> 15,132, index build 1.0 s -> 0.6 s.

**Not shipped**: the submitted system indexes `title_abstract`. The measurement now
supports the change on ranking metrics for both datasets, but it costs stage-one recall on
EB-NeRD val, and Q2's re-ranker consumes exactly that recall. That makes it a pipeline-level
decision rather than a retrieval-level one, and it is the team's to take.

#### 6c. EB-NeRD small, Danish stemming: **the A1 prior does not reproduce, now conclusively**

Delta of turning stemming **off**, baseline is stemming on.

| split | AUC | MRR | nDCG@10 | recall@200 |
|---|---|---|---|---|
| val | -0.0003 [-0.0019, +0.0014] | +0.0004 [-0.0011, +0.0019] | +0.0003 [-0.0009, +0.0017] | **+0.0020** [+0.0011, +0.0030] |
| test | -0.0002 [-0.0011, +0.0007] | +0.0003 [-0.0005, +0.0012] | +0.0002 [-0.0005, +0.0009] | **-0.0010** [-0.0016, -0.0005] |

**On ranking, Danish stemming does nothing.** All four metrics on both splits sit within
±0.0004 of zero, and at this scale the intervals are tight enough that this is a measured
null rather than an absence of evidence: the val AUC interval is ±0.0017 wide, so an effect
even a fifth the size of the field ablation's would have shown.

**On recall, the effect flips sign between val and test, and both are significant.** Turning
stemming off gains +0.0020 recall@200 on val and loses -0.0010 on test. In relative terms
stemming is **-8.5% on val and +4.7% on test**. A significant effect that reverses across a
temporal split boundary is not a property of stemming; it is a property of which articles
happened to be in each window. It should not be quoted as a directional result in either
direction.

*Does the A1 prior of +22 to +36% recall@200 reproduce at `small`?* **No, and this now closes
the question.** Demo gave +1.4%, not significant, and was written up as inconclusive because
demo was underpowered. At 10x, with intervals tight enough to resolve effects an order of
magnitude smaller than the prior, the answer is -8.5% / +4.7% depending on the split. The prior
is not merely unreproduced at low power; it is excluded.

The standing hypothesis from 6b remains the best explanation and remains untested: this pipeline
already applies a Danish stopword list, separately measured in A1 as 0.5035 -> 0.5232 AUC.
Stopwords and stemming compete for the same high-frequency surface variation, so A1's stemming
figure was most likely the combined effect of both against a baseline with neither. Testing that
needs a `stem x stopwords` 2x2, which is a second variable and therefore its own ablation.

**Kept ON**, and now on a cost argument alone rather than an accuracy one: it shrinks the
vocabulary 43,451 -> 30,388 (30%) and *reduces* query scoring time 23.6 s -> 19.2 s on val,
because a smaller vocabulary means shorter posting lists to walk. Free on both axes, neutral
on ranking, so there is no reason to turn it off and a small reason not to.

#### What the scale change teaches, beyond these two rows

Of the four EB-NeRD demo cells, the two that were called `inconclusive` or `rejected` on
statistical grounds resolved in opposite ways at 10x: #7's effect was real and simply
unresolvable, #6's was genuinely absent. **Underpowered is not a synonym for zero**, and the
demo tier cannot distinguish the two. Any future ablation whose interval spans zero at demo
scale should be re-run at `small` before a verdict is recorded, not written off.

#### Scale caveat, stated rather than buried

Sections 6b and 7b are **demo scale**: 11,777 articles, 6,872 val and 25,356 test
impressions, roughly a tenth of `ebnerd_small`, with intervals three to five times wider than
MIND's. That caveat was written before the 10x runs and it proved to be the right one: at
`ebnerd_small` (6c and 7c above) one demo verdict reversed and the other hardened. **Quote 6c
and 7c, not 6b and 7b.** The demo rows are retained as the evidence for that lesson, not as
results.

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

> **SUPERSEDED 2026-09-12.** The table below was measured on features carrying the engagement
> future-click leak (FACTS section 10). It is kept because it is the evidence for what the leak
> was worth. The current numbers are directly beneath it.

**Contaminated, superseded: full model val 0.7575, test 0.7429.**

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

### CURRENT, clean features, 2026-09-12

**Full model: val 0.7489, test 0.7461.** Seed 13 carried forward for continuity with the
superseded run.

| arm | val AUC | full - arm | 95% CI | sig | test delta | sig |
|---|---|---|---|---|---|---|
| stage1_only (bm25 + emb) | 0.5498 | **+0.1991** | [+0.1963, +0.2020] | yes | **+0.2031** | yes |
| pop_only (pop_causal alone) | 0.6954 | +0.0535 | [+0.0517, +0.0553] | yes | +0.0605 | yes |
| minus pop_causal | 0.7126 | +0.0363 | [+0.0346, +0.0379] | yes | +0.0403 | yes |
| minus cat_match | 0.7451 | +0.0038 | [+0.0027, +0.0048] | yes | +0.0047 | yes |
| minus bm25 | 0.7480 | +0.0009 | [+0.0004, +0.0015] | yes | +0.0008 | yes |
| minus engage_sim | 0.7487 | +0.0002 | [-0.0004, +0.0009] | **no** | +0.0012 | yes |
| minus hist_len | 0.7489 | +0.0000 | [-0.0004, +0.0004] | **no** | +0.0006 | yes |
| minus emb | 0.7490 | -0.0001 | [-0.0006, +0.0004] | **no** | +0.0010 | yes |
| minus age_hours | 0.7491 | -0.0002 | [-0.0008, +0.0003] | **no** | +0.0012 | yes |
| minus user_scroll | 0.7493 | -0.0004 | [-0.0009, +0.0001] | **no** | +0.0009 | yes |
| minus recency | 0.7493 | -0.0004 | [-0.0010, +0.0001] | **no** | -0.0001 | no |
| minus user_read | 0.7496 | **-0.0006** | [-0.0012, -0.0002] | **yes, negative** | +0.0002 | no |

Test rose from 0.7429 to 0.7461 even though val fell, because test features were always correct
(the test split is drawn from the same block its history comes from) and only the model changed.
`stage1_only` and `pop_only` are bit-identical across the two runs, since neither reads an
engagement feature, which localises the fix to exactly the arms it should have touched.

### What the table says

**The behavioural axis is worth +0.1991 AUC on val and +0.2031 on test, over stage one alone.**
That is larger than every Assignment-1 result combined and it is the answer to "what did adding
click-log signal buy". The val and test intervals overlap, so it generalises.

**Causally valid popularity is most of it, and more so than before.** Alone it reaches 0.6954,
above any complete A1 system. Removing it from the full set costs 0.0363 val and 0.0403 test, the
largest single-feature contribution by a wide margin. The +0.075 that *leaky* lifetime popularity
bought in A1 therefore largely survives the causal restriction, which was the open question that
motivated the feature.

**WITHDRAWN: "engagement weighting beats uniform pooling".** This claim stood on `engage_sim`
being worth +0.0085 and standalone scoring 0.5774 against `emb`'s 0.5506. Both numbers came from
leaked history. On clean features the ranker-level effect is +0.0002 [-0.0004, +0.0009], not
significant, and the standalone gap disappears once both sides read the same history source. The
read-time-weighted user vector does not beat the uniform one in the ranker. See the re-run sweep
below, which finds a small positive weighting effect on the isolated feature but no ranker-level
survival, and which reverses a different A1 claim in the process.

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


## Q9: what the serving-unavailable features would buy (EB-NeRD small, val)

Required by the brief: report metrics with and without features unavailable at serving time.
Both arms are the same lambdarank model on the same rows in the same order; the only
difference is which columns it may see. Paired bootstrap, 1000 resamples, seed 13.

| arm | val AUC |
|---|---|
| causal only, **this is what ships** | 0.7575 |
| + article lifetime aggregates | 0.7796 |
| **difference** | **+0.0222** [+0.0207, +0.0235], significant |

The leaky arm adds `total_inviews`, `total_pageviews` and `total_read_time`, which aggregate
an article's whole lifetime including time after the impression being predicted, so they
cannot be computed at serving time.

**The interesting part is how small +0.0222 is.** A1 measured the same class of feature at
+0.042 on EB-NeRD small and +0.075 on the demo split, both far larger. The difference is that
A1 compared leaky popularity against a system with **no** popularity signal at all, whereas
here it is competing with `pop_causal`, which counts clicks strictly before the impression.
So most of what lifetime popularity was providing is legitimately obtainable, and the honest
reconstruction captures it. That was the open question when the feature was proposed, and the
answer is that roughly two thirds to three quarters of the leaky advantage survives causal
restriction.

Stated the other way: cheating here is worth +0.0222, against the +0.2077 that the whole
behavioural axis buys legitimately. The gap that matters is not the one being declined.

**Guard.** `tests/test_leakage.py::test_no_scorer_reads_a_serving_unavailable_column` fails if
any scoring module names these columns. `src/features/leaky.py` is allow-listed because
producing this row is its only purpose, and `src/pipeline/` is out of scope because carrying
the columns into the corpus is what lets the comparison exist.

**That guard had been vacuous.** It globbed `ROOT/retrieval` and `ROOT/eval`, paths that
stopped existing when the A1 port moved everything under `src/`, so from that commit until
2026-09-07 it scanned zero files and passed without checking anything. It now scans the
scoring packages recursively, asserts it saw at least ten files, and was verified by injecting
a violation and confirming it fails. Third vacuous test found in this project.


## History length x weighting sweep: BOTH VERDICTS REVERSED on clean history

> **The version of this sweep that "REJECTED" info.md's prediction ran on leaked history.** Its
> table is kept below the current one because it is the evidence for what the leak did to the
> shape of the curve.

`info.md` predicted that read-time weighting "may recover the benefit of large N that uniform
mean-pooling throws away". Measured on EB-NeRD small val, 64,365 impressions. Per-impression AUC
of the similarity feature alone, so the result is about the user vector and nothing else. Both
arms use the same code path and the same N; only the weights differ.

### CURRENT, clean history, 2026-09-12

| N | uniform | read-time weighted | weighted - uniform |
|---|---|---|---|
| 1 | 0.5221 | 0.5221 | +0.0000 |
| 5 | 0.5368 | 0.5362 | -0.0006 |
| 10 | 0.5416 | 0.5434 | +0.0018 |
| 20 | 0.5483 | 0.5495 | +0.0011 |
| 50 | 0.5528 | 0.5554 | +0.0026 |
| 100 | **0.5545** | **0.5570** | +0.0025 |

**Claim 1 is now REJECTED, having previously been confirmed.** Performance is **monotonically
increasing** in N across the whole range and peaks at N=100, the largest value tested. There is
no degradation anywhere. Both A1 systems reported that averaging more history makes the user
vector worse, and `info.md` built its read-time hypothesis on that premise; on clean history the
premise is false.

The leak explains the old shape. With future clicks in the profile, a short window concentrated
the leaked signal, so the curve peaked early at N=10 and fell away as genuine history diluted it.
Removing the leak removes the peak.

**Claim 2 is no longer rejected, but it is not confirmed either.** Read-time weighting is
positive at every N above 5, best at +0.0026. That is the direction `info.md` predicted, but this
sweep reports no confidence intervals and an effect of 0.0026 is too small to call real without
one. Treat it as unresolved rather than supported.

Note this does not contradict the ranker-level result above, where `minus engage_sim` is not
significant. A small gain in an isolated feature need not survive alongside `pop_causal`, which
dominates the ensemble.

**Consequence for a config in another lane.** `configs/datasets.yaml` sets `history_len: 30` and
cites this sweep as verification. That justification is withdrawn and N=100 now looks better.
`configs/` is Yash's lane, so this is flagged, not changed.

### SUPERSEDED: the same sweep on leaked history

| N | uniform | read-time weighted | weighted - uniform |
|---|---|---|---|
| 1 | 0.5584 | 0.5584 | +0.0000 |
| 5 | 0.6333 | 0.6237 | **-0.0096** |
| 10 | **0.6473** | **0.6397** | -0.0076 |
| 20 | 0.6362 | 0.6329 | -0.0033 |
| 50 | 0.6093 | 0.6092 | -0.0000 |
| 100 | 0.5906 | 0.5919 | +0.0013 |

Every AUC here is inflated by roughly 0.10 relative to the clean run, which is the measured size
of the leak on this feature (+0.0967).

### This corrects an earlier claim in this file

An earlier entry reported "engagement weighting beats uniform pooling" on the basis that
`engage_sim` scored 0.5774 against `emb`'s 0.5506 standalone, and that removing `engage_sim`
cost 0.0085 in the ranker. **That comparison was confounded and the causal reading was wrong.**
`_engagement_user_vectors` pools over the user's *entire* history, while `emb` comes from the A1
retrieval path with `history_len: 30`. So the two differed in **two** variables at once,
weighting and history length, and the sweep above shows the weighting is not the one that helps.

The ablation delta for `engage_sim` (+0.0085, CI [+0.0075, +0.0096]) is still real: the feature
does contribute. But it contributes as a *differently pooled* user vector, not as a
*better-weighted* one, and the report must not claim the latter.

**Best N is 10, not the 30 currently configured**, on this metric. That is a separate finding
and a candidate change, but it is a stage-one config value in Yash's lane, so it is logged here
rather than applied.

**Still untested:** the scroll-completion *filter* (`info.md` item 4), which drops low-engagement
history entries rather than down-weighting them. That is a different mechanism and this result
does not speak to it.
