# Report source notes

Everything the Q6 design note will draw on, in one place: what we built, every measured number
with its provenance, what worked, what did not, the tradeoffs, and the open questions.

**Status: living document, updated as results land.** Anything marked TO MEASURE is a known gap,
not an oversight. Every number here also exists in `FACTS.md` (measurements) or `ABLATIONS.md`
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

---

## 3. Ablations: what worked

### 3.1 The A2 re-ranker (paired bootstrap, 1000 resamples, shared, seed 13)

Each arm removes exactly one feature and retrains. Full model = 0.7575 on 64,365 val impressions.

| arm | val AUC | full - arm | 95% CI | significant |
|---|---|---|---|---|
| stage1_only | 0.5498 | **+0.2077** | [+0.2048, +0.2107] | yes |
| pop_only | 0.6954 | +0.0620 | [+0.0602, +0.0639] | yes |
| minus `pop_causal` | 0.7228 | +0.0346 | [+0.0330, +0.0363] | yes |
| minus `engage_sim` | 0.7489 | +0.0085 | [+0.0075, +0.0096] | yes |
| minus `emb` | 0.7532 | +0.0043 | [+0.0035, +0.0050] | yes |
| minus `cat_match` | 0.7537 | +0.0038 | [+0.0028, +0.0048] | yes |
| minus `hist_len` | 0.7555 | +0.0019 | [+0.0014, +0.0025] | yes |
| minus `bm25` | 0.7561 | +0.0014 | [+0.0008, +0.0020] | yes |
| minus `user_scroll` | 0.7565 | +0.0009 | [+0.0005, +0.0014] | yes |
| minus `user_read` | 0.7567 | +0.0007 | [+0.0002, +0.0013] | yes |
| minus `age_hours` | 0.7572 | +0.0003 | [-0.0002, +0.0007] | **no** |
| minus `recency` | 0.7574 | +0.0001 | [-0.0003, +0.0006] | **no** |

**Causally valid popularity is the single biggest win.** Removing it costs 0.0346; alone it
reaches 0.6954. This was the highest-ranked item on the A2 plan and it delivered.

**`engage_sim` contributes +0.0085**, CI [+0.0075, +0.0096]. Neither A1 system used the
read-time column at all. **But do not describe this as "engagement weighting beats uniform
pooling".** A dedicated sweep (section 4) shows read-time weighting is *worse* than uniform at
every history length from 5 to 50. `engage_sim` pools over the user's entire history while
`emb` uses `history_len: 30`, so the two differ in two variables and the gain is attributable to
the pooling length, not the weights.

### 3.2 Stage-one ablations (Yash, MIND and EB-NeRD demo)

**BM25 field choice, MIND**: title-only wins on AUC, val +0.0024 [+0.0006, +0.0041], test
+0.0065 [+0.0047, +0.0083], reproducing the A1 number to four decimals. **But A1's claim of "no
measured downside" was wrong**: val MRR falls -0.0022 [-0.0039, -0.0005]. Left unshipped pending
a team decision.

**BM25 field choice, EB-NeRD demo**: rejected. AUC indistinguishable from zero, recall@200
-0.0049 [-0.0094, -0.0002]. Goes the opposite way to MIND, which is the two-track finding again.

**Stemming**: keep it **on for both** datasets. The plan's premise ("Danish on, English off") is
rejected: turning it off costs MIND -0.0023 [-0.0034, -0.0013] val AUC. Danish is inconclusive at
demo scale and A1's +22 to +36% recall@200 prior does **not** reproduce (+1.4%, not significant).
Best guess is the Danish stopword list already captures those wins; untested and a separate
variable.

---

## 4. Ablations: what did not work

| change | measured effect | verdict |
|---|---|---|
| `recency` as a ranker feature | +0.0001 [-0.0003, +0.0006] | **no measurable contribution** despite third-highest gain |
| `age_hours` as a ranker feature | +0.0003 [-0.0002, +0.0007] | same |
| BM25 title-only on EB-NeRD | recall@200 -0.0049 [-0.0094, -0.0002] | rejected, opposite sign to MIND |
| Disabling English stemming | -0.0023 [-0.0034, -0.0013] AUC | rejected, the plan's premise was wrong |
| Read-time weighting of the user vector | worse than uniform at N=5,10,20,50; +0.0013 only at N=100 | **`info.md`'s prediction rejected** |

**Carried from A1, still true, do not re-run:** body text in the BM25 index (-0.0166 AUC),
Danish compound splitting (-0.0040), max-similarity pooling (-0.0030, confirmed independently on
both A1 systems), RRF instead of linear fusion (lost at every k), time and position decay on
click weighting (neutral to harmful at every constant), BM25 k1/b grid search (+0.001),
`rank_bm25` (782x slower than a sparse matmul), raw multilingual BERT as an encoder (below
random), ANN indexes (10 to 20x faster but exact search was never the bottleneck at this scale).

---

## 5. Q9, anti-gaming: with and without serving-unavailable features

| arm | val AUC |
|---|---|
| causal only, **ships** | 0.7575 |
| + article lifetime aggregates | 0.7796 |
| **difference** | **+0.0222** [+0.0207, +0.0235], significant |

The leaky columns are `total_inviews`, `total_pageviews`, `total_read_time`, which aggregate an
article's whole lifetime including time after the impression.

**The story is how small +0.0222 is.** A1 measured the same class of feature at +0.042 (EB-NeRD
small) and +0.075 (demo). A1 was comparing leaky popularity against a system with **no**
popularity signal; here it competes with `pop_causal`. So most of what lifetime popularity
provided is legitimately obtainable. Cheating is worth +0.0222; the honest behavioural axis is
worth +0.2077.

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

**One metric name, two definitions, twice.** `bm25.py` printed a **hit-rate@200** (share of
impressions with at least one clicked article retrieved) labelled as recall@200 (mean of
found/clicked). They reconcile exactly: 0.0333 x 0.6775 = 0.0226. They agree only when
impressions have one click, and MIND is 28.8% multi-click against EB-NeRD demo's 0.5%, which is
why the number failed to reproduce on exactly one dataset. The same shape is still open for MRR:
official 0.3198 against our offline 0.3548, likely first-click versus all-clicks.

**Four vacuous tests found in this codebase.** A test that passes without asserting anything is
worse than no test. (1) The MIND history-time leakage assertion guarded on dtype, but MIND's
empty timestamp lists come back as `List(Datetime)` not `Null`, so it never skipped, every
`list.max()` was null, `null >= t` is null, the filter dropped every row and it reported green
over 95,071 of 95,071 rows. (2) The Q9 serving-unavailable guard globbed paths that stopped
existing at the A1-to-`src/` port and scanned **zero files**. (3) An install script recorded
`TF_OK=1` from pip's exit code while `import tensorflow` was broken throughout. (4) A job waiter
used `pgrep -f` with a pattern that matched its own command line, so it reported a finished build
as still running. **Every assertion now states what it checked and fails if that count is zero**,
and both leakage guards are verified by injecting a violation and confirming they fire.

---

## 7. Serving and scale (Q4)

### 7.1 Measured, laptop (20 cores, no GPU, 15 GB RAM)

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

### 7.3 Still to measure

- **Index memory**: RAM and serialised on-disk footprint, separately, for the BM25 index, the
  FAISS index and the feature store, per dataset. TO MEASURE.
- **p50 / p95 / p99 latency** for a single user request, candidate generation plus re-ranking.
  A1 measured mean throughput only, which is not what Q4 asks. TO MEASURE.
- **Cost per 1000 queries** at a target SLA, e.g. p99 < 100 ms. TO MEASURE.
- **What breaks at 10x.** A1's answer was the per-impression Python loop rather than the linear
  algebra; needs re-checking now that a re-ranker is in the path. TO MEASURE.

### 7.4 Carried from A1, useful for the scaling argument

Submission at full scale: EB-NeRD testset, 13.5M impressions / 205,925,868 pairs, 13 m 30 s at
~16.7k impressions/s with flat peak RSS; MIND large test, 2.37M impressions, 4 m 38 s at 2.0 GB.
Streaming in 200k-impression slices keeps peak RSS flat against dataset size; slice pushdown
reaches the parquet row groups, so an offset-13M slice costs the same as one at offset 0. CSV has
no slice pushdown, which is why MIND needed a one-off TSV to parquet conversion.

---

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

**Yash's EB-NeRD ablation verdicts are demo-scale** (11,777 articles, 6,872 val impressions) and
their intervals are 3 to 5x wider than MIND's, so several cells are inconclusive because the
split is small rather than because the effect is zero. The `ebnerd_small` re-runs are queued.

**Q3 is not done.** NRMS reproduction is in progress; the environment took five attempts because
`ebnerd-benchmark` is TensorFlow with pins that conflict with our pipeline, and the cluster has no
usable PyPI access.

**Open, unexplained.** EB-NeRD BM25 recall@200 was more than 2x better at history N=1 than at any
larger N in A1, while MIND improves monotonically with more history. The N sweep has now been run
for the *semantic* user vector and shows a peak at N=10 falling away to N=100, so the degradation
is real, but read-time weighting does not explain or fix it. The mechanism is still unknown, and
the low-quality-click hypothesis from `info.md` is not supported by the weighting result.

**Open, and it needs resolving before the report.** The sweep's uniform arm scores 0.6473 at
N=10, while the `emb` feature from the A1 retrieval path scores 0.5506 per impression on the same
split. Both are uniform-weighted mean user vectors, so they should be closer than that. The
likely causes are the truncation (`history_len: 30` vs the sweep's explicit N) and a different
normalisation in `src/retrieval/embeddings.py`. Until this is understood, do not quote the two
numbers side by side as if they measure the same thing.

**Open, definitional.** MIND official MRR 0.3198 against our offline 0.3548, while AUC and both
nDCGs rose. Likely first-click versus all-clicks reciprocal rank. Resolve before quoting either.
