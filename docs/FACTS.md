# FACTS

Every measured number, with the provenance needed to defend it under questioning.

**Rules.** One row per number. A number in the design note with no row here is a number we cannot
defend. If a value is projected rather than measured, the Method column must say `projected`.
Write the row when the number is produced, not at the end.

Columns: **Value** as printed, **Scope** (dataset / split / scale), **Method** (the exact command or
script that emitted it), **Source** (`A1-naman`, `A1-yash`, or `A2`), **Date**.

Rows marked `A1-*` are inherited from our Assignment-1 systems. They are starting points, **not
verified for A2**: the scales differ and the pipeline has changed. Re-measure before quoting one.

---

## 1. Corpus

| Fact | Value | Scope | Method | Source | Date |
|---|---|---|---|---|---|
| Articles | 65,238 | MIND small, union of train+dev (21% dev-only) | A1 pipeline | A1-naman, A1-yash agree | 2026-08 |
| Articles | 120,961 | MIND large test (Codabench reference set) | A1 pipeline | A1-yash | 2026-08 |
| Articles | 11,777 | EB-NeRD demo | A1 pipeline | A1-yash | 2026-08 |
| Articles | 20,738 | EB-NeRD small | A1 pipeline | A1-naman | 2026-08 |
| Articles | 125,500 | EB-NeRD testset | A1 pipeline | A1-yash | 2026-08 |
| Impressions train/val/test | 168,522 / 64,365 / 244,647 | EB-NeRD small | A1 split | A1-naman | 2026-08 |
| Impressions train/val/test | 95,071 / 61,894 / 73,152 | MIND small | A1 split | A1-naman | 2026-08 |
| Impressions | 13,500,000 | EB-NeRD testset | A1 submit | A1-yash, A1-naman agree | 2026-08 |
| Impression-candidate pairs | 205,925,868 | EB-NeRD testset | A1 submit | A1-naman | 2026-08 |
| Impressions | 2,370,000 | MIND large test | A1 submit | A1-yash, A1-naman agree | 2026-08 |
| Median body length | 1,830 chars | EB-NeRD small | A1 field ablation | A1-naman | 2026-08 |
| Median title length | ~60 chars | EB-NeRD small | A1 field ablation | A1-naman | 2026-08 |
| **Mean article text length** | **TO MEASURE** | both, per field | | A2 | |

## 2. Splits

| Fact | Value | Scope | Method | Source | Date |
|---|---|---|---|---|---|
| Split policy | temporal, never random | both | `configs/datasets.yaml` | A1-naman | 2026-08 |
| Date boundaries | train 05-18 to 05-25, val 05-25 to 05-29, test 05-29 to 06-01 | EB-NeRD | config | A1-yash | 2026-08 |
| MIND split rule | last calendar day of train.tsv to val, dev.tsv held out as test | MIND small | `src/pipeline/split.py` | A1-yash | 2026-08 |
| Real leakage found at scale | 16 histories of 1,579,672 with a click up to 31 days post-impression | EB-NeRD large | leakage guard | A1-naman | 2026-08 |
| Publish-time tolerance | 0.01 to 0.03% of inview entries published up to ~9 h after impression | EB-NeRD | leakage test | A1-yash | 2026-08 |

## 3. Embeddings

| Fact | Value | Scope | Method | Source | Date |
|---|---|---|---|---|---|
| Model | `Ekstra_Bladet_contrastive_vector`, 768-d, provided | EB-NeRD | A1 shipped | A1-naman | 2026-08 |
| Model | `all-MiniLM-L6-v2`, 384-d, self-encoded | MIND | A1 shipped | A1-naman | 2026-08 |
| Model | word2vec `document_vector`, 300-d, provided | EB-NeRD | A1 shipped | A1-yash | 2026-08 |
| Model | mean-pooled TransE entity vectors, 100-d | MIND | A1 shipped | A1-yash | 2026-08 |
| Vector coverage | 100% (11,777 / 11,777) | EB-NeRD demo | A1 | A1-yash | 2026-08 |
| Vector coverage | 87.03% (56,774 / 65,238) | MIND small | A1 | A1-yash | 2026-08 |
| Mean pairwise cosine | +0.9503 | EB-NeRD provided mBERT vectors | A1 geometry diagnosis | A1-naman | 2026-08 |
| Encoding time | 11 m 16 s for 65,238 articles, CPU | MIND small, MiniLM | A1 | A1-naman | 2026-08 |
| Encoding rate | ~1,000 to 1,800 articles/s | Kaggle T4 | A1 | A1-naman | 2026-08 |

## 4. Indexes

**Residency: everything was in RAM in A1.** FAISS `IndexFlatIP` (exact, not approximate) over
L2-normalised vectors, and BM25 as a doc-weight matrix whose non-zero pattern is the inverted index.
A2 Q4.1 requires measured footprints, so every `TO MEASURE` row below is graded work.

| Fact | Value | Scope | Method | Source | Date |
|---|---|---|---|---|---|
| BM25 matrix shape | 65,238 x 60,849 at 0.04% density | MIND small | scipy CSR | A1-yash | 2026-08 |
| BM25 vocab | 30k title+abstract, 124k with bodies | EB-NeRD small | A1 field ablation | A1-naman | 2026-08 |
| BM25 build time | 18 s title+abstract, 29 s with bodies | EB-NeRD small | A1 field ablation | A1-naman | 2026-08 |
| BM25 params | k1=1.5, b=0.75 (`bm25s` defaults, never tuned) | both | A1 shipped | A1-naman, A1-yash | 2026-08 |
| **Index RAM footprint** | **TO MEASURE** | every index, both datasets | Q4.1 | A2 | |
| **Index on-disk footprint** | **TO MEASURE** | every index, both datasets | Q4.1 | A2 | |
| **Feature store footprint** | **TO MEASURE** | both | Q4.1 | A2 | |

## 5. Latency, throughput, memory

**Every row here records the machine.** A p99 measured on the laptop and a QPS measured on a cluster
node are not comparable, and the whole set backing one comparison must come from one machine. Two
machines are in play: `laptop` (20 cores, no GPU, 15 GB RAM) and `cluster` (GPU node, describe the
card and core count in the row). Describe hardware, never hostnames, usernames or paths.

| Fact | Value | Scope | Machine | Method | Source | Date |
|---|---|---|---|---|---|---|
| BM25 `get_scores` | 1.6 ms/query over 65,238 articles | MIND small | laptop | A1 bench | A1-naman | 2026-08 |
| Submission throughput | ~16.7k impressions/s, 13 m 30 s total, flat peak RSS | EB-NeRD testset | laptop | `src/pipeline/submit.py` | A1-naman | 2026-08 |
| Submission throughput | 4 m 38 s, 2.0 GB peak | MIND large test | laptop | submit | A1-naman | 2026-08 |
| Submission throughput | 4,629 impressions/s, 49 min | EB-NeRD test | laptop | candidates-only matmul | A1-yash | 2026-08 |
| Submission throughput | 2,019 impressions/s, ~20 min, 0.83 GB | MIND | laptop | A1 submit | A1-yash | 2026-08 |
| Dense index QPS | 3,624 (MIND exact flat), 2,150 (EB-NeRD exact flat) | both | laptop | `bench_ann_recall_latency` | A1-yash | 2026-08 |
| Peak RSS, naive parquet read | 10.5 GB, OOM on a 15 GB box | EB-NeRD test | laptop | A1 | A1-yash | 2026-08 |
| Peak RSS, column-pruned batched | 1.7 GB | EB-NeRD test | laptop | A1 | A1-yash | 2026-08 |
| Peak RSS, `np.vstack(.to_list())` | 5.8 GB to build a 385 MB array | EB-NeRD | laptop | A1 | A1-naman | 2026-08 |
| 768-d vs 300-d submission cost | 33 m 28 s / 5.9 GB vs 6 m 59 s / 2.7 GB | EB-NeRD | laptop | A1 | A1-naman | 2026-08 |
| Split build (`src.pipeline.split`) | 41.5 s wall, **peak RSS 9.69 GB** | EB-NeRD small | laptop | `/usr/bin/time -v .venv/bin/python -m src.pipeline.split ebnerd_small` | A2 | 2026-09-04 |
| Split build | 7.0 s wall, peak RSS 1.28 GB | MIND small | laptop | `/usr/bin/time -v ... -m src.pipeline.split mind_small` | A2 | 2026-09-04 |
| `make split` all 3 datasets in one process | **OOM-killed (SIGKILL 137)** on a 15 GB box with ~6 GB free | all dev tiers | laptop | `make split` | A2 | 2026-09-04 |
| BM25 index + score, all 3 splits | 12.2 s wall, peak RSS 0.86 GB | EB-NeRD demo | laptop | `/usr/bin/time -f ... -m src.retrieval.bm25 ebnerd_demo` | A2 | 2026-09-04 |
| BM25 index + score, all 3 splits | 100.7 s wall, **peak RSS 7.15 GB** | EB-NeRD small | laptop | `... -m src.retrieval.bm25 ebnerd_small` | A2 | 2026-09-04 |
| BM25 index + score, all 3 splits | 258.2 s wall, peak RSS 1.96 GB | MIND small | laptop | `... -m src.retrieval.bm25 mind_small` | A2 | 2026-09-04 |
| Embeddings + FAISS, all 3 splits | 13.5 s wall, peak RSS 1.02 GB | EB-NeRD demo | laptop | `... -m src.retrieval.embeddings ebnerd_demo` | A2 | 2026-09-04 |
| Embeddings + FAISS, all 3 splits | 88.4 s wall, **peak RSS 7.04 GB** | EB-NeRD small | laptop | `... -m src.retrieval.embeddings ebnerd_small` | A2 | 2026-09-04 |
| Leakage suite, 19 tests, data present | 28.2 s, 19 passed 0 skipped | all dev tiers | laptop | `make test` | A2 | 2026-09-04 |
| **p50 / p95 / p99 single-request latency** | **TO MEASURE** | candidate gen + re-rank, both |  | Q4.2 | A2 | |
| **Cost per 1000 queries at p99 < 100 ms** | **TO MEASURE** | both |  | Q4.3 | A2 | |
| **Per-component build time and peak RSS** | **TO MEASURE** | tokeniser, BM25, encoder, ANN, feature store, re-ranker |  | Q4 | A2 | |

## 6. Accuracy (A1 shipped systems, for the Q3 baseline comparison)

| System | AUC | MRR | nDCG@5 | nDCG@10 | Scope | Source |
|---|---|---|---|---|---|---|
| emb (shipped) | 0.5397 | | | | EB-NeRD small test | A1-naman |
| emb + entity a=0.20 (shipped) | 0.6391 | | | | MIND small test | A1-naman |
| BM25 | 0.5544 | 0.3061 | 0.2800 | 0.3421 | MIND test | A1-yash |
| semantic | 0.5362 | 0.2737 | 0.2520 | 0.3140 | MIND test | A1-yash |
| BM25 | 0.5009 | 0.2667 | 0.2826 | 0.3826 | EB-NeRD test | A1-yash |
| semantic | 0.5089 | 0.3251 | 0.3538 | 0.4391 | EB-NeRD test | A1-yash |
| Codabench EB-NeRD | 0.5381 | 0.3521 | 0.3868 | 0.4669 | leaderboard | A1-naman |
| Codabench MIND | 0.6503 | 0.3198 | 0.3454 | 0.4010 | leaderboard | A1-naman |
| A1 port re-check: BM25 recall@200 | **0.0248** vs A1's 0.0247 | EB-NeRD small test | `src.retrieval.bm25` | A2 |
| A1 port re-check: emb recall@200 | **0.0278** vs A1's 0.0277 | EB-NeRD small test | `src.retrieval.embeddings` | A2 |
| A1 port re-check: BM25 recall@200 | 0.0333 vs A1's 0.0220, **does not reproduce, investigate** | MIND small test | `src.retrieval.bm25` | A2 |
| **A2 two-stage pipeline** | **TO MEASURE** | | | | both | A2 |
| **NRMS baseline reproduction** | **TO MEASURE** | | | | both, Q3 | A2 |
