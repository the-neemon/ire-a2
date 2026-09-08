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
| Articles | 65,238 | MIND small | `python -m src.pipeline.split mind_small` | **A2, re-verified** | 2026-09-04 |
| Articles | 11,777 | EB-NeRD demo | `python -m src.pipeline.split ebnerd_demo` | **A2, re-verified** | 2026-09-04 |
| Articles published after the test window | 845 | EB-NeRD demo | `python -m src.pipeline.split ebnerd_demo` | A2 | 2026-09-04 |
| **Mean article text length** | **TO MEASURE** | both, per field | | A2 | |

## 2. Splits

| Fact | Value | Scope | Method | Source | Date |
|---|---|---|---|---|---|
| Split policy | temporal, never random | both | `configs/datasets.yaml` | A1-naman | 2026-08 |
| Date boundaries | train 05-18 to 05-25, val 05-25 to 05-29, test 05-29 to 06-01 | EB-NeRD | config | A1-yash | 2026-08 |
| MIND split rule | last calendar day of train.tsv to val, dev.tsv held out as test | MIND small | `src/pipeline/split.py` | A1-yash | 2026-08 |
| Real leakage found at scale | 16 histories of 1,579,672 with a click up to 31 days post-impression | EB-NeRD large | leakage guard | A1-naman | 2026-08 |
| Publish-time tolerance | 0.01 to 0.03% of inview entries published up to ~9 h after impression | EB-NeRD | leakage test | A1-yash | 2026-08 |
| Impressions train/val/test | 95,071 / 61,894 / 73,152 | MIND small | `python -m src.pipeline.split mind_small` | **A2, matches A1** | 2026-09-04 |
| Impressions train/val/test | 17,852 / 6,872 / 25,356 | EB-NeRD demo | `python -m src.pipeline.split ebnerd_demo` | A2 | 2026-09-04 |
| Split windows | train 05-18 07:00 -> 05-23 06:58, val 05-23 07:01 -> 05-25 06:59, test 05-25 07:00 -> 06-01 06:59 | EB-NeRD demo | `python -m src.pipeline.split ebnerd_demo` | A2 | 2026-09-04 |
| Split windows | train 11-09 -> 11-12, val 11-13 -> 11-14, test 11-15 | MIND small | `python -m src.pipeline.split mind_small` | A2 | 2026-09-04 |
| Leakage suite | 12 passed, 7 skipped | ebnerd_demo + mind_small built, ebnerd_small not yet | `python -m pytest tests/ -q` | A2 | 2026-09-04 |
| Of which honest MIND skips | 1: `test_no_history_click_at_or_after_its_impression`, MIND ships no per-item history timestamps | MIND small | same | A2 | 2026-09-04 |

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
| BM25 vocabulary, title+abstract, stemmed | 44,264 terms over 65,238 articles | MIND small | `python -m src.eval.ablate_bm25 mind_small --name fields ...` | A2 | 2026-09-04 |
| BM25 vocabulary, title only, stemmed | 24,681 terms | MIND small | same command | A2 | 2026-09-04 |
| BM25 vocabulary, title+abstract, unstemmed | 60,914 terms | MIND small | `... --name stemming --variant no_stem:stem=off` | A2 | 2026-09-04 |
| BM25 vocabulary, title+abstract, stemmed | 22,105 terms over 11,777 articles | EB-NeRD demo | `python -m src.eval.ablate_bm25 ebnerd_demo --name fields ...` | A2 | 2026-09-04 |
| BM25 vocabulary, title only, stemmed | 10,738 terms | EB-NeRD demo | same command | A2 | 2026-09-04 |
| BM25 vocabulary, title+abstract, unstemmed | 31,515 terms | EB-NeRD demo | `... --name stemming --variant no_stem:stem=off` | A2 | 2026-09-04 |
| Danish stemming vocabulary saving | 29.9% (31,515 -> 22,105) | EB-NeRD demo | as above | A2 | 2026-09-04 |
| BM25 vocabulary, title+abstract, stemmed | 30,388 terms over 20,738 articles | EB-NeRD small | `python -m src.eval.ablate_bm25 ebnerd_small --ablation fields` | A2 | 2026-09-08 |
| BM25 vocabulary, title only, stemmed | 15,132 terms | EB-NeRD small | same command | A2 | 2026-09-08 |
| BM25 vocabulary, title+abstract, unstemmed | 43,451 terms | EB-NeRD small | `... --ablation stemming` | A2 | 2026-09-08 |
| Danish stemming vocabulary saving | 30.1% (43,451 -> 30,388) | EB-NeRD small | as above | A2 | 2026-09-08 |
| English stemming vocabulary saving | 27.3% (60,914 -> 44,264) | MIND small | as above | A2 | 2026-09-04 |
| BM25 index RAM | 7.0 MiB (2.5 MiB CSR arrays + ~4.5 MiB vocab dict) | EB-NeRD small, 297,145 postings / 30,388 terms | `python -m src.eval.bench ebnerd_small` | A2 | 2026-09-08 |
| BM25 index on disk | 3.0 MiB (`bm25s` save) | EB-NeRD small | same | A2 | 2026-09-08 |
| FAISS index RAM | 60.8 MiB = 20,738 x 768 x 4 B exactly | EB-NeRD small | same | A2 | 2026-09-08 |
| FAISS index on disk | 60.8 MiB (`faiss.write_index`) | EB-NeRD small | same | A2 | 2026-09-08 |
| Feature store RAM | 294.5 MiB materialised | EB-NeRD small, 5,514,689 candidate rows x 10 features | same | A2 | 2026-09-08 |
| Feature store on disk | 115.7 MiB parquet | EB-NeRD small | same | A2 | 2026-09-08 |
| **Index footprints, MIND** | **TO MEASURE** | MIND small | Q4.1 | A2 | |

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
| BM25 index build | 4.5 s title+abstract, 1.9 s title only | MIND small, 65,238 articles | laptop | `python -m src.eval.ablate_bm25 mind_small --name fields ...` | A2 | 2026-09-04 |
| BM25 index build | 5.2 s stemmed, 4.1 s unstemmed | MIND small | laptop | `... --name stemming ...` | A2 | 2026-09-04 |
| BM25 index build | 0.7 s title+abstract, 0.5 s title only | EB-NeRD demo, 11,777 articles | laptop | `python -m src.eval.ablate_bm25 ebnerd_demo --name fields ...` | A2 | 2026-09-04 |
| BM25 index build | 0.9 s stemmed, 0.6 s unstemmed | EB-NeRD demo | laptop | `... --name stemming ...` | A2 | 2026-09-04 |
| BM25 index build | 1.0 s title+abstract, 0.6 s title only | EB-NeRD small, 20,738 articles | laptop | `python -m src.eval.ablate_bm25 ebnerd_small --ablation fields` | A2 | 2026-09-08 |
| BM25 index build | 1.1 s stemmed, 1.0 s unstemmed | EB-NeRD small | laptop | `... --ablation stemming` | A2 | 2026-09-08 |
| BM25 scoring, whole split | 19.2 s val stemmed vs 23.6 s unstemmed; 45.3 s vs 50.6 s test | EB-NeRD small | laptop | `... --ablation stemming` | A2 | 2026-09-08 |
| Query deduplication ratio | 10,523 distinct for 64,365 val; 15,342 for 244,647 test | EB-NeRD small | laptop | `src.retrieval.bm25` stdout | A2 | 2026-09-08 |
| Split build (`src.pipeline.split`) | 51.0 s wall, peak RSS 9.64 GB | EB-NeRD small | laptop | `/usr/bin/time -v ... -m src.pipeline.split ebnerd_small` | **A2, confirms 9.69 GB** | 2026-09-08 |
| BM25 scoring, whole split | 85.3 s val (30,867 distinct queries), 144.8 s test (48,354) | MIND small | laptop | `... --name stemming ...` | A2 | 2026-09-04 |
| BM25 scoring, whole split | 2.1 s val, 3.5 s test | EB-NeRD demo | laptop | `... --name stemming ...` | A2 | 2026-09-04 |
| Query deduplication ratio | 30,867 distinct for 61,894 val; 48,354 for 73,152 test | MIND small | laptop | `src.retrieval.bm25` stdout | A2 | 2026-09-04 |
| Peak RSS, two-variant ablation | 1.93 GB, 9 m 23 s wall (2 variants x 2 splits) | MIND small | laptop | `/usr/bin/time -v python -m src.eval.ablate_bm25 mind_small ...` | A2 | 2026-09-04 |
| EB-NeRD S3 throughput | ~28 KB/s sustained, stalls without a read timeout | download, from this network | laptop | `curl -w %{speed_download}` against the bucket | A2 | 2026-09-04 |
| Split build (`src.pipeline.split`) | 41.5 s wall, **peak RSS 9.69 GB** | EB-NeRD small | laptop | `/usr/bin/time -v .venv/bin/python -m src.pipeline.split ebnerd_small` | A2 | 2026-09-04 |
| Split build | 7.0 s wall, peak RSS 1.28 GB | MIND small | laptop | `/usr/bin/time -v ... -m src.pipeline.split mind_small` | A2 | 2026-09-04 |
| `make split` all 3 datasets in one process | **OOM-killed (SIGKILL 137)** on a 15 GB box with ~6 GB free | all dev tiers | laptop | `make split` | A2 | 2026-09-04 |
| BM25 index + score, all 3 splits | 12.2 s wall, peak RSS 0.86 GB | EB-NeRD demo | laptop | `/usr/bin/time -f ... -m src.retrieval.bm25 ebnerd_demo` | A2 | 2026-09-04 |
| BM25 index + score, all 3 splits | 100.7 s wall, **peak RSS 7.15 GB** | EB-NeRD small | laptop | `... -m src.retrieval.bm25 ebnerd_small` | A2 | 2026-09-04 |
| BM25 index + score, all 3 splits | 258.2 s wall, peak RSS 1.96 GB | MIND small | laptop | `... -m src.retrieval.bm25 mind_small` | A2 | 2026-09-04 |
| Embeddings + FAISS, all 3 splits | 13.5 s wall, peak RSS 1.02 GB | EB-NeRD demo | laptop | `... -m src.retrieval.embeddings ebnerd_demo` | A2 | 2026-09-04 |
| Embeddings + FAISS, all 3 splits | 88.4 s wall, **peak RSS 7.04 GB** | EB-NeRD small | laptop | `... -m src.retrieval.embeddings ebnerd_small` | A2 | 2026-09-04 |
| Embeddings: MiniLM encode 65,238 articles + FAISS, all 3 splits | 967.8 s wall (16 m 8 s), peak RSS 2.50 GB | MIND small | laptop | `/usr/bin/time -f ... -m src.retrieval.embeddings mind_small` | A2 | 2026-09-04 |
| Leakage suite, 19 tests, data present | 28.2 s, 19 passed 0 skipped | all dev tiers | laptop | `make test` | A2 | 2026-09-04 |
| **Single-request latency, end to end** | **p50 22.06 ms / p95 48.94 ms / p99 64.90 ms**, max 90.75 ms | EB-NeRD small val, 2,000 unbatched requests | laptop, 8 physical / 12 logical cores | `python -m src.eval.bench ebnerd_small --requests 2000` | A2 | 2026-09-08 |
| Latency by stage, p50 | tokenise 0.70 / bm25 1.36 / **ann 13.55** / features 0.32 / rerank 5.02 ms | EB-NeRD small val | laptop | same | A2 | 2026-09-08 |
| Latency by stage, p99 | tokenise 3.13 / bm25 8.16 / **ann 45.41** / features 1.18 / rerank 29.47 ms | EB-NeRD small val | laptop | same | A2 | 2026-09-08 |
| ANN share of p50 | 61% of end-to-end | EB-NeRD small val | laptop | same | A2 | 2026-09-08 |
| SLA verdict | p99 64.90 ms against a 100 ms target: **meets**, 1.5x headroom | EB-NeRD small val | laptop | same | A2 | 2026-09-08 |
| Serial throughput, one core | 45 QPS | EB-NeRD small val | laptop | same | A2 | 2026-09-08 |
| Whole-box capacity | 363 QPS over 8 physical cores, **projected** (assumes linear scaling) | EB-NeRD small val | laptop | same | A2 | 2026-09-08 |
| Cost per 1000 queries | $0.000245, **projected** at an assumed $0.040/vCPU-hour | EB-NeRD small val | laptop | same | A2 | 2026-09-08 |
| Scaling, ann p50 vs corpus | 0.59 -> 11.39 ms for 2,074 -> 20,738 articles: **19.4x for 10x**, super-linear | EB-NeRD small | laptop | `--scale-points 0.1 0.25 0.5 1.0` | A2 | 2026-09-08 |
| Scaling, flat stages | rerank 3.9x, features 2.4x for the same 10x corpus | EB-NeRD small | laptop | same | A2 | 2026-09-08 |
| Per-stage peak RSS, batch pipeline | bm25 6.82 GB / embeddings 6.79 GB / fuse 5.65 GB / features 3.87 GB / rerank train 1.41 GB | EB-NeRD small, all 3 splits | laptop | `/usr/bin/time -v` per stage | A2 | 2026-09-08 |
| Per-stage wall time, batch pipeline | bm25 2:38 / embeddings 2:38 / fuse 2:01 / features 5:37 / rerank train 1:20 | EB-NeRD small, all 3 splits | laptop | same | A2 | 2026-09-08 |
| Serving-path build costs | BM25 index 0.83 s, vector load 2.17 s, FAISS build 0.04 s, re-ranker train 97.8 s (311 trees) | EB-NeRD small | laptop | `python -m src.eval.bench ebnerd_small` | A2 | 2026-09-08 |
| **Latency and footprints, MIND** | **TO MEASURE** | MIND small | | Q4.2 | A2 | |

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
| BM25 title+abstract, stemmed | 0.5840 [0.5814, 0.5865] | 0.3204 | 0.2924 | 0.3494 | MIND small **val** | A2 |
| BM25 title+abstract, stemmed | 0.5685 [0.5663, 0.5707] | 0.3108 | 0.2868 | 0.3479 | MIND small **test** | A2 |
| BM25 title only, stemmed | 0.5864 [0.5840, 0.5887] | 0.3182 | 0.2918 | 0.3489 | MIND small **val** | A2 |
| BM25 title only, stemmed | 0.5750 [0.5730, 0.5773] | 0.3108 | 0.2872 | 0.3489 | MIND small **test** | A2 |
| BM25 title+abstract, unstemmed | 0.5816 [0.5790, 0.5840] | 0.3200 | 0.2914 | 0.3486 | MIND small **val** | A2 |
| BM25 title+abstract, unstemmed | 0.5657 [0.5634, 0.5679] | 0.3103 | 0.2848 | 0.3468 | MIND small **test** | A2 |
| BM25 title+abstract, stemmed | 0.5234 [0.5154, 0.5309] | 0.3456 | 0.3814 | 0.4627 | EB-NeRD demo **val** | A2 |
| BM25 title+abstract, stemmed | 0.5125 [0.5088, 0.5166] | 0.3273 | 0.3591 | 0.4418 | EB-NeRD demo **test** | A2 |
| BM25 title only, stemmed | 0.5243 [0.5166, 0.5318] | 0.3430 | 0.3819 | 0.4625 | EB-NeRD demo **val** | A2 |
| BM25 title only, stemmed | 0.5153 [0.5115, 0.5195] | 0.3279 | 0.3601 | 0.4428 | EB-NeRD demo **test** | A2 |
| BM25 title+abstract, unstemmed | 0.5209 [0.5134, 0.5283] | 0.3444 | 0.3802 | 0.4615 | EB-NeRD demo **val** | A2 |
| BM25 title+abstract, unstemmed | 0.5128 [0.5089, 0.5169] | 0.3273 | 0.3581 | 0.4420 | EB-NeRD demo **test** | A2 |
| BM25 title+abstract, stemmed | 0.5205 [0.5177, 0.5230] | 0.3418 | 0.3794 | 0.4607 | EB-NeRD small **val** | A2 |
| BM25 title+abstract, stemmed | 0.5107 [0.5094, 0.5120] | 0.3257 | 0.3577 | 0.4409 | EB-NeRD small **test** | A2 |
| BM25 title only, stemmed | 0.5229 [0.5203, 0.5253] | 0.3437 | 0.3820 | 0.4628 | EB-NeRD small **val** | A2 |
| BM25 title only, stemmed | 0.5150 [0.5138, 0.5163] | 0.3281 | 0.3616 | 0.4430 | EB-NeRD small **test** | A2 |
| BM25 title+abstract, unstemmed | 0.5202 [0.5176, 0.5226] | 0.3421 | 0.3793 | 0.4610 | EB-NeRD small **val** | A2 |
| BM25 title+abstract, unstemmed | 0.5105 [0.5092, 0.5118] | 0.3261 | 0.3579 | 0.4411 | EB-NeRD small **test** | A2 |
| A1 port re-check: BM25 recall@200 | **0.0248** vs A1's 0.0247 | EB-NeRD small test | `src.retrieval.bm25` | A2 |
| A1 port re-check: emb recall@200 | **0.0278** vs A1's 0.0277 | EB-NeRD small test | `src.retrieval.embeddings` | A2 |
| A1 port re-check: BM25 recall@200 | 0.0333 vs A1's 0.0220, **does not reproduce** | MIND small test | `src.retrieval.bm25` | A2 |
| A1 port re-check: emb recall@200 | 0.0354 vs A1's 0.0239, **does not reproduce** | MIND small test | `src.retrieval.embeddings` | A2 |
| | | | | |
| ~~Open: both MIND recall@200 numbers came in ~50% above A1 while both EB-NeRD numbers matched to 4dp.~~ **Resolved 2026-09-04: two different metrics, not a corpus or config difference.** `src.retrieval.bm25` printed a hit-rate under the label recall. | | MIND small test | see below | A2 |
| A2 two-stage re-ranker, full | **0.7575** | 0.5319 | 0.5967 | 0.6341 | val, EB-NeRD small | A2, full metric set 2026-09-08 |
| A2 two-stage re-ranker, full | **0.7429** | 0.5149 | 0.5750 | 0.6140 | test, EB-NeRD small | A2, full metric set 2026-09-08 |
| A2 stage one alone (bm25+emb) | 0.5498 | | | | val, EB-NeRD small | A2 |
| emb | 0.5506 [0.5482, 0.5530] | 0.3594 | 0.4017 | 0.4778 | val, EB-NeRD small | A2 | 
| fused | 0.5528 [0.5503, 0.5553] | 0.3628 | 0.4043 | 0.4807 | val, EB-NeRD small | A2 |
| fused+popularity (leaky, not servable) | 0.5784 [0.5760, 0.5808] | 0.3707 | 0.4184 | 0.4910 | val, EB-NeRD small | A2 |
| emb | 0.5397 [0.5384, 0.5409] | 0.3492 | 0.3831 | 0.4627 | test, EB-NeRD small | A2 |
| fused | 0.5380 [0.5367, 0.5392] | 0.3474 | 0.3813 | 0.4613 | test, EB-NeRD small | A2 |
| fused+popularity (leaky, not servable) | 0.5797 [0.5785, 0.5810] | 0.3688 | 0.4101 | 0.4841 | test, EB-NeRD small | A2 |
| **A2 two-stage pipeline, MIND** | **TO MEASURE** | | | both | A2 |
| **NRMS baseline reproduction** | **TO MEASURE** | | | | both, Q3 | A2 |

### Resolved: the MIND "recall@200 does not reproduce" gap was a mislabelled metric

Both quantities below come from **one** retrieval run, `src.retrieval.bm25 mind_small
--splits test`, shipped config (title+abstract, stemmed, `history_len` 100). Nothing about the
corpus, the split or the configuration differs between them. Machine: laptop, 2026-09-04.

| Definition | Value | What it counts |
|---|---|---|
| hit-rate@200, what `bm25.py` printed | **0.0333** | share of impressions with **at least one** clicked article retrieved |
| mean recall@200, what `eval.metrics.recall_at_k` reports | **0.0226** | mean over impressions of (clicked articles found) / (clicked articles) |

They reconcile exactly: 0.0333 x 0.6775 = 0.0226.

The 0.6775 is the whole story. Of 73,152 MIND test impressions, 2,435 retrieve at least one
clicked article. Those 2,435 average **2.280 clicks** against 1.523 across the split, because an
impression with more clicks has more chances that one of them is retrieved. But only **1.060** of
those clicks are actually found. So a hit impression contributes 1.0 to the hit-rate and only
1.060/2.280 = 0.6775 to mean recall.

This is why the discrepancy looked dataset-specific and therefore looked like a bug. EB-NeRD demo
test averages **1.006** clicks per impression with 0.5% multi-click, so `|found|/|clicked|` is
almost always exactly 1 when there is a hit and the two definitions agree to three decimals. MIND
averages 1.523 with **28.8%** multi-click, so they cannot agree. One dataset reproducing and the
other not was the signature of a definitional gap, not of a corpus difference.

`bm25.py` now prints `hit-rate@200` and says in the code why it is not recall. **Every recall@K
number in section 7 and in `ABLATIONS.md` is the `recall_at_k` definition**, which is the one the
brief asks for ("how many ground-truth clicked articles appear in the top-K candidates"). The
hit-rate is a build-time sanity signal only and no reported figure should be taken from it.

Worth carrying into Q5: this is the same class of error as the open MIND MRR question, where our
0.3548 offline disagreed with the organisers' 0.3198. Both are one metric name covering two
definitions. When a number fails to reproduce on exactly one dataset, check the definition against
that dataset's click-count distribution before suspecting the data.

## 7. Candidate generation — recall@K, full-corpus retrieval (A2)

Share of an impression's clicked articles found in the top K drawn from the **whole catalogue**,
not the pool the log showed. Distinct from section 6, which re-ranks the shown pool. Cold-start
impressions retrieve nothing and score 0 rather than being excluded.

All rows: `python -m src.eval.ablate_bm25 <dataset> --splits val test --name <fields|stemming> ...`,
machine `laptop`, 2026-09-04. Reports under `results/ablation_bm25_*`.

| Config | recall@50 | recall@100 | recall@200 | Scope |
|---|---|---|---|---|
| title+abstract, stemmed | 0.0157 | 0.0247 | 0.0371 [0.0357, 0.0384] | MIND small **val** |
| title only, stemmed | 0.0158 | 0.0259 | 0.0388 [0.0374, 0.0402] | MIND small **val** |
| title+abstract, unstemmed | 0.0159 | 0.0260 | 0.0391 [0.0378, 0.0405] | MIND small **val** |
| title+abstract, stemmed | 0.0062 | 0.0126 | 0.0226 [0.0215, 0.0235] | MIND small **test** |
| title only, stemmed | 0.0074 | 0.0134 | 0.0231 [0.0221, 0.0242] | MIND small **test** |
| title+abstract, unstemmed | 0.0066 | 0.0134 | 0.0234 [0.0224, 0.0244] | MIND small **test** |
| title+abstract, stemmed | 0.0114 | 0.0217 | 0.0434 [0.0386, 0.0479] | EB-NeRD demo **val** |
| title only, stemmed | 0.0103 | 0.0184 | 0.0385 [0.0338, 0.0430] | EB-NeRD demo **val** |
| title+abstract, unstemmed | 0.0127 | 0.0224 | 0.0439 [0.0392, 0.0487] | EB-NeRD demo **val** |
| title+abstract, stemmed | 0.0108 | 0.0216 | 0.0390 [0.0368, 0.0413] | EB-NeRD demo **test** |
| title only, stemmed | 0.0096 | 0.0210 | 0.0380 [0.0358, 0.0401] | EB-NeRD demo **test** |
| title+abstract, unstemmed | 0.0105 | 0.0200 | 0.0376 [0.0354, 0.0399] | EB-NeRD demo **test** |
| title+abstract, stemmed | 0.0052 | 0.0110 | 0.0214 [0.0202, 0.0225] | EB-NeRD small **val** |
| title only, stemmed | 0.0049 | 0.0098 | 0.0190 [0.0179, 0.0200] | EB-NeRD small **val** |
| title+abstract, unstemmed | 0.0061 | 0.0123 | 0.0234 [0.0222, 0.0246] | EB-NeRD small **val** |
| title+abstract, stemmed | 0.0072 | 0.0133 | 0.0247 [0.0241, 0.0253] | EB-NeRD small **test** |
| title only, stemmed | 0.0070 | 0.0134 | 0.0242 [0.0235, 0.0248] | EB-NeRD small **test** |
| title+abstract, unstemmed | 0.0070 | 0.0130 | 0.0236 [0.0230, 0.0242] | EB-NeRD small **test** |

**These numbers are low and that is the finding, not a bug.** Recalling 3.7% of clicks in a top-200
drawn from 65,238 MIND articles means BM25-over-click-history is a weak candidate generator on its
own. Two structural reasons, both measured elsewhere in this file rather than assumed: cold-start
impressions retrieve nothing at all and are counted as 0, and MIND ships no `published_time`, so
the retrieval track cannot exclude articles that did not exist yet (EB-NeRD can, and does, with
845 demo articles published after the test window ends). Q2's two-stage design should not assume
stage 1 recall is adequate until this is raised.

## 8. Q5: the full metric set over the two-stage output (A2)

`python -m src.eval.run ebnerd_small --splits val test`. Machine: laptop, 2026-09-08. Reports
in `results/ebnerd_small_{val,test}.md`. All CIs are 1,000 paired bootstrap resamples over
impressions; every AUC is **per impression**, never pooled.

The re-ranker's trainer computes per-impression AUC independently and agrees with the harness
to four decimals on both splits (val 0.7575, test 0.7429). That agreement is the check that
`eval.run.flat_scores` reshaped the flat per-candidate table into `candidates` order correctly:
a mis-ordered join produces a plausible number rather than an error, so it is verified against
a figure computed by other code instead of being assumed.

### Stage two against every stage-one baseline

| comparison | val AUC | test AUC | significant |
|---|---|---|---|
| rerank - bm25 | **+0.2370** [+0.2339, +0.2402] | **+0.2322** [+0.2306, +0.2338] | yes |
| rerank - emb | **+0.2068** [+0.2039, +0.2095] | **+0.2032** [+0.2018, +0.2048] | yes |
| rerank - fused | **+0.2047** [+0.2018, +0.2076] | **+0.2049** [+0.2034, +0.2064] | yes |

Reported against all three rather than only the strongest, because "beats the best baseline"
and "beats the baseline we happened to ship" are different claims.

### The result that matters for Q9

**The honest two-stage system beats the deliberately leaky one, and not narrowly.** `rerank`
uses only features computable strictly before the impression; `fused+popularity` adds lifetime
`total_inviews`, which embeds the future and cannot be served.

| | val AUC | test AUC |
|---|---|---|
| rerank (servable) | **0.7575** | **0.7429** |
| fused+popularity (not servable) | 0.5784 | 0.5797 |

A1 framed the leak as worth +0.042 to +0.075 AUC and giving it up as "the cost of honesty". At
the two-stage level that framing no longer holds: the behavioural axis done causally is worth
roughly four times what the leak was worth, so honesty costs nothing here. It only looked
expensive while the comparison was between single-signal retrieval systems.

### Slices (val, AUC)

cold = history <= 42 clicks; head = clicked article with >= 379 train clicks. Slice sizes are
printed because a badly-placed threshold can silently select nearly everything.

| slice | n | bm25 | fused | rerank | fused+popularity |
|---|---|---|---|---|---|
| cold | 6,463 | 0.5281 | 0.5612 | **0.7836** | 0.5843 |
| warm | 57,902 | 0.5196 | 0.5518 | **0.7545** | 0.5778 |
| head | 1,094 | 0.5091 | 0.6638 | **0.7046** | 0.7192 |
| tail | 63,271 | 0.5207 | 0.5509 | **0.7584** | 0.5760 |

Two things worth stating rather than leaving in the table:

* **The re-ranker is better on cold users than warm ones** (0.7836 vs 0.7545), inverting the
  usual expectation. Its top feature by gain is `pop_causal`, causally-valid popularity, which
  needs no history at all. A user with no history is exactly where a popularity prior is the
  best available signal and where the history-driven stage-one systems have least to work with.
* **On head articles the leaky system beats the honest one** (0.7192 vs 0.7046), the only slice
  where that happens, which is what you would predict: head articles are by definition those
  whose lifetime `total_inviews` is largest, so that is where knowing the future is worth most.
  1,094 impressions with overlapping intervals, so a caution rather than a finding.

### Beyond accuracy (top-10, val)

| system | diversity | novelty | coverage |
|---|---|---|---|
| bm25 | 0.8039 | 16.3525 | 0.1142 |
| emb | 0.7906 | 16.3992 | 0.1130 |
| fused | 0.7916 | 16.3909 | 0.1131 |
| rerank | 0.8006 | 16.4824 | 0.1030 |
| fused+popularity | 0.7963 | 16.3572 | 0.1099 |

The re-ranker buys its +0.20 AUC at a real cost in **catalogue coverage**: 0.1131 -> 0.1030,
about 9% fewer distinct articles ever reaching a top-10. Its novelty is the highest of any
system, so it is not collapsing onto popular items; it concentrates on a narrower set of
articles that are individually less-clicked. Named here as a tradeoff rather than reporting the
accuracy gain alone.

### Fusion still does not generalise on EB-NeRD

`fused - emb` is **+0.0022** [+0.0010, +0.0034] on val and **-0.0017** [-0.0023, -0.0010] on
test: both significant, opposite signs. This reproduces the A1 finding including its sign flip.
The alpha is selected on val by rule and applied unchanged, so it is a real generalisation
failure across the split boundary, not a selection artefact. Stage two makes it moot in
practice, since `rerank` beats `fused` by +0.2047 either way.

## 9. Q4: what breaks first at 10x, and the machine caveat (A2)

Full report in `results/bench_ebnerd_small.md`. Machine: laptop, **8 physical / 12 logical
cores**, 15.3 GB RAM, no GPU.

**Correction to the environment note.** `CLAUDE.md` describes this machine as "20 cores".
`psutil` and `nproc` both report 12 logical and 8 physical. Every capacity figure here uses 8,
the physical count, because this path is dense float work in BLAS and LightGBM where a
hyperthread shares an execution port and adds much less than a real core. Anything previously
scaled by 20 is overstated by 2.5x.

**`ann` is the bottleneck and it breaks first.** It is 61% of p50 at full corpus and its cost
grows **19.4x for a 10x corpus**, which is super-linear where `IndexFlatIP` should be at worst
linear. The excess is the memory hierarchy: 6.1 MiB of vectors at the smallest scale is
cache-resident, 60.8 MiB at full scale is not, so each query goes from cache to streaming from
RAM. At 10x the catalogue this is a bandwidth problem, not a FLOPs problem.

**This overturns A1's answer.** A1 concluded the per-impression Python loop was the bottleneck
rather than the linear algebra. With stage two in the path that is no longer true: every
Python-side stage is roughly flat in corpus size, so its share shrinks as the catalogue grows.
Making the re-ranker faster buys nothing at scale. The only lever that matters is replacing the
exact index with an approximate one, which is the ANN row A1 measured and rejected as
"10 to 20x faster but exact search was never the bottleneck at this scale" and explicitly
flagged to revisit at 10x catalogue. This is that revisit, and it now says the opposite.

**Known limitation in the scaling curve, disclosed rather than buried.** Subsampling the corpus
also shortens the query, because the query is built from history titles and a subsampled-out
article contributes none. Measured: the mean number of last-30 history items still resolving to
a title falls 29.2 -> 2.3 between full corpus and 10%. So the `tokenise` and `bm25` growth
factors conflate two variables and are upper bounds on the corpus effect, not estimates of it.
`ann` is unaffected, since a FAISS scan costs vectors x dim whatever the query contains, so the
stage the verdict rests on is measured cleanly. Isolating the other two needs a bench that holds
the query fixed while shrinking only the index.

**Run-to-run variance.** Two full bench runs an hour apart gave end-to-end p99 of 78.16 ms and
64.90 ms, and re-ranker training of 47.5 s and 97.8 s, on an otherwise-busy laptop. The second
run is the recorded one. Treat single-run timings from this machine as good to roughly +/-20%,
and never compare a number from here against one from the cluster.
