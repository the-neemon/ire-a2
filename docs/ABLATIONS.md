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
| 6 | Per-language stemming: Snowball Danish on, English off | both | | | | planned |
| 7 | Queries built from titles + abstracts rather than titles only | both | | | | planned |
| 8 | MIND BM25 documents title-only | MIND | | | | planned |
| 9 | Re-sweep `history_len` after 2 and 7 land | both | | | | planned |
| 10 | Better MIND article vectors than 87%-coverage mean-pooled entities | MIND | | | | planned |
| 11 | Q3 required: one principled improvement over the reproduced NRMS baseline | both | | | | planned |

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
