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

| system | AUC | MRR | nDCG@5 | nDCG@10 |
|---|---|---|---|---|
| bm25 | 0.5205 | 0.3418 | 0.3794 | 0.4607 |
| emb | 0.5506 | 0.3594 | 0.4017 | 0.4778 |
| fused | 0.5528 | 0.3628 | 0.4043 | 0.4807 |
| **rerank** | **0.7575** | **0.5319** | **0.5967** | **0.6341** |
| fused+popularity | 0.5784 | 0.3707 | 0.4184 | 0.4910 |

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

**One metric name, two definitions, twice.** `bm25.py` printed a **hit-rate@200** (share of
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

### 7.1 Measured, laptop (**8 physical / 12 logical cores**, no GPU, 15.3 GB RAM)

**Correction.** `CLAUDE.md` describes this machine as "20 cores". `psutil` and `nproc` both
report 12 logical and 8 physical. Capacity below is priced off 8, the physical count, because
this path is dense float work in BLAS and LightGBM where a hyperthread shares an execution port
and adds much less than a real core. **Anything previously scaled by 20 is overstated by 2.5x.**

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
approximate one — the ANN row A1 measured and rejected as "10 to 20x faster but exact search was
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
