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
machines are in play, and they are NOT the same box, so the label alone is not enough:
`laptop-naman` (i7-13700H, 14 physical / 20 logical cores, no GPU, 15 GB RAM),
`laptop-yash` (8 physical / 12 logical cores, no GPU, 15.3 GB RAM) and `cluster` (GPU node,
describe the card and core count in the row). A row that says only `laptop` predates this
split and should be read as unverified on either box. Describe hardware, never hostnames,
usernames or paths.

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
| **Single-request latency, end to end** | **p50 22.06 ms / p95 48.94 ms / p99 64.90 ms**, max 90.75 ms | EB-NeRD small val, 2,000 unbatched requests | laptop-yash, 8 physical / 12 logical cores | `python -m src.eval.bench ebnerd_small --requests 2000` | A2 | 2026-09-08 |
| Latency by stage, p50 | tokenise 0.70 / bm25 1.36 / **ann 13.55** / features 0.32 / rerank 5.02 ms | EB-NeRD small val | laptop | same | A2 | 2026-09-08 |
| Latency by stage, p99 | tokenise 3.13 / bm25 8.16 / **ann 45.41** / features 1.18 / rerank 29.47 ms | EB-NeRD small val | laptop | same | A2 | 2026-09-08 |
| ANN share of p50 | 61% of end-to-end | EB-NeRD small val | laptop | same | A2 | 2026-09-08 |
| SLA verdict | p99 64.90 ms against a 100 ms target: **meets**, 1.5x headroom | EB-NeRD small val | laptop | same | A2 | 2026-09-08 |
| Serial throughput, one core | 45 QPS | EB-NeRD small val | laptop | same | A2 | 2026-09-08 |
| Whole-box capacity | 363 QPS over 8 physical cores, **projected** (assumes linear scaling) | EB-NeRD small val | laptop-yash | same | A2 | 2026-09-08 |
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
| **NRMS baseline reproduction (their split)** | val AUC **0.6484**, see section 14 | | | | EB-NeRD small, Q3 | A2 |
| **NRMS on our split (comparable)** | **IN PROGRESS**, see section 14 | | | | EB-NeRD small, Q3 | A2 |

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

## 7. Candidate generation: recall@K, full-corpus retrieval (A2)

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

Full report in `results/bench_ebnerd_small.md`. Machine: **laptop-yash**, 8 physical /
12 logical cores, 15.3 GB RAM, no GPU.

**The environment note was not wrong, the machines differ.** This section originally recorded
a correction saying `CLAUDE.md`'s "20 cores" was wrong and that anything scaled by 20 was
overstated by 2.5x. Checked on laptop-naman: `nproc` reports 20 and `lscpu` reports an
i7-13700H with 14 physical cores (6 P-cores plus 8 E-cores) and 2 threads per P-core, so 20
logical is accurate for that box. The 8 physical / 12 logical reading is laptop-yash. Both
were filed under one `laptop` label, which is what made one look like a correction to the
other. No previously reported figure needs rescaling; the bench numbers here are simply
laptop-yash numbers and are not reproducible on laptop-naman.

Capacity figures here still use 8, the physical count of the machine they ran on, because this
path is dense float work in BLAS and LightGBM where a hyperthread shares an execution port and
adds much less than a real core. That reasoning is sound and unaffected.

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

## 10. Y2a RESOLVED: the emb/sweep gap is future-click leakage, not `history_len` (A2)

`src/features/sweep_history.py`'s uniform arm scores **0.6473** at N=10 while the `emb` feature
scores **0.5506** per impression on the same split. Both are uniform-weighted mean user vectors,
so the gap needed explaining before either could be quoted.

**Cause: the two read different history files.** Not the `history_len: 30` truncation and not a
normalisation difference, which were the two standing suspects. Both are ruled out below.

Confirmed by making one implementation produce both numbers, varying only the history source.
`src.features.sweep_history.user_vectors` and `.score` unchanged, EB-NeRD small val, laptop,
2026-09-08:

| history source | N=10 | N=30 |
|---|---|---|
| `train` + `validation` blocks (what `_engagement_weights` does) | **0.6473** | 0.6250 |
| `train` block only (causally valid for a val impression) | 0.5416 | **0.5506** |

The top-left cell reproduces the sweep exactly and the bottom-right reproduces `emb` exactly.
Once the history source matches, `history_len` explains nothing: the two implementations agree.

**The mechanism.** `_engagement_weights` loops `for block in ("train", "validation")` and assigns
`out[uid] = ...`, so the validation block **overwrites** the train block for the 11,658 users
present in both. EB-NeRD ships one `history.parquet` per block, each describing clicks before
*that block's* log period. Our val split is carved out of the **train** block, so validation-block
history for a val impression is history from the future.

Measured directly, by comparing each impression's timestamp against the maximum
`impression_time_fixed` of the validation-block history joined to it:

| split | impressions | matched to validation-block history | with history at/after the impression |
|---|---|---|---|
| train | 168,522 | 144,087 | **143,998 (99.9%)** |
| val | 64,365 | 61,026 | **60,901 (99.8%)** |
| test | 244,647 | 244,647 | 0 (0.0%) |

**Test is clean and train/val are not**, which follows from the split: test comes from the
validation block, so validation-block history genuinely precedes it. The isolated size of the
leak on this feature is **+0.0967 AUC** (0.5506 -> 0.6473).

### What this invalidates, and what survives

**Invalidated: the sweep's headline.** With leaked history the curve peaks at N=10 and falls
away; with causally valid history the order **reverses**, N=30 (0.5506) beating N=10 (0.5416).
The "peak at N=10" is an artefact of the leak, so the claim in `REPORT-NOTES.md` section 9 that
the semantic degradation at large N "is real" is **not supported by this sweep**. The underlying
EB-NeRD N=1 anomaly from A1 remains open and unexplained; this sweep cannot speak to it.

**Also affected: three shipped re-ranker features.** `src/features/build.py::build` calls
`_engagement_weights(name)` with no split argument, so `engage_sim`, `user_read` and
`user_scroll` are built from the same overwritten history on every split. On train and val those
three are not causally valid. `hist_len` is unaffected, being derived from the impressions'
own `history` column, as are all six stage-one and popularity features.

**What survives, stated so this is not over-claimed.** The headline two-stage result is
reproduced on **test**, where the features are clean: `rerank - fused` is **+0.2049**
[+0.2034, +0.2064] on test against +0.2047 on val, and test `rerank` AUC is 0.7429. So the
conclusion that the behavioural axis is worth about +0.20 AUC does not rest on the leak. What
does rest on it is every **val-selected** figure: the 13-arm ablation grid, `engage_sim`'s
+0.0085, LightGBM's early-stopping iteration count, and Q9's +0.0222, all of which are val
numbers computed on contaminated features and all of which need re-running.

**FIXED, 2026-09-08.** `_engagement_weights(cfg, split)` now reads a single block, chosen from
the same `early_root` / `test_root` config keys `split.py` uses so the two cannot drift apart:
train and val take `early_root`, test takes `test_root`. The merge loop is gone.

Confirmed by making the two paths produce their numbers side by side on EB-NeRD small val:

| history source | matched impressions | with history at/after the impression |
|---|---|---|
| `early_root` block (the fix) | 64,365 | **0 (0.0%)** |
| `validation` block (what the merge selected) | 61,026 | **60,901 (99.8%)** |

The 99.8% reproduces the independently measured figure above exactly.

**Why the existing leakage test did not catch it.** `tests/test_leakage.py` checks the
*impressions'* `history_timestamps`, which are correct, and `tests/test_features_leakage.py`
checks the feature builder's popularity window. Neither compares the engagement arrays against
the impression timestamp, which is the assertion that would have fired. That is a fifth vacuous-
coverage case in the same family as the four already recorded: the guard existed, but not over
this path.

**Now covered.** `tests/test_features_leakage.py` gains
`test_engagement_history_is_strictly_before_its_impressions`, which joins each split's
impressions against the history block that split actually reads and asserts no click falls at or
after the impression using it, plus a companion injection test. The block-per-split rule is
restated in the test rather than imported from `build.py`, so a regression there cannot silently
take the test with it. Non-vacuity is asserted on both the join cardinality and the null count,
because an empty join is exactly how the MIND history assertion reported green over 95,071 rows
while checking none of them. The module docstring's claim that non-popularity features "come from
history arrays that are past by construction" was the false premise that let this through and has
been corrected: that holds within a block, not across two.

## 11. Y2b RESOLVED: MIND MRR is first-click against all-clicks (A2)

Our offline MRR read **0.3548** where the MIND leaderboard returned **0.3198** for the same A1
system, while AUC and both nDCGs rose. Third instance of one metric name covering two
definitions, after hit-rate/recall (section on the MIND recall gap) and the Y2a history source.

**Cause: the organisers average over every clicked article; we credited only the best-placed
one.** MIND's official scorer is `sum(1/rank for each positive) / n_positives`. Our
`eval.metrics.mrr` is `1 / min(rank over positives)`.

Measured on MIND small test, BM25 title+abstract, 73,152 impressions, laptop, 2026-09-08
(`python -m src.retrieval.bm25 mind_small --splits test --out-subdir mrrcheck`):

| definition | MRR |
|---|---|
| first clicked article only (ours) | **0.3108** |
| mean over all clicked articles (MIND official) | **0.2693** |
| difference | **-0.0415** [-0.0423, -0.0405], paired |

**The signature matches exactly.** AUC (0.5685) and nDCG@10 (0.3479) are *identical* under both,
because neither reads which click came first, so only MRR moves. That is the reported pattern:
MRR fell while AUC and both nDCGs rose.

**It is entirely a multi-click effect.** The 71.2% of impressions with one click score
identically under both definitions, maximum absolute difference exactly 0.0. The whole gap comes
from the 28.8% with more than one, where 0.3095 becomes 0.1657. The same property explains the
recall/hit-rate gap, and EB-NeRD is immune to both at 0.5% multi-click.

**Exact reconciliation is not possible and should not be attempted**, because the two numbers
are on different corpora: 0.3548 was offline on MIND small test, 0.3198 was the leaderboard on
MIND **large** test, whose click distribution we cannot observe. Our measured ratio is 0.867
against the observed 0.901, the same direction and magnitude, with the residual attributable to
that difference. **The mechanism is confirmed; the arithmetic cannot be closed and the report
should say so** rather than implying the two were reconciled.

**Fix: both are now reported, and neither is silently swapped.** `eval.metrics.mrr_all`
implements the official definition and `src.eval.run` prints both columns. They answer different
questions, `mrr` how fast the user finds something they wanted and `mrr_all` how well the whole
clicked set is placed, so replacing one with the other would trade one wrong comparison for
another. **When quoting against a MIND leaderboard number, use `mrr_all`.**

## 12. Y3: slice thresholds verified, the head/tail trap does not fire (A2)

`CLAUDE.md` warns that over 90% of MIND articles have zero train clicks, so a 90th-percentile
head/tail threshold would be 0 and `>=` would classify every impression as head. **Checked
directly; it does not happen**, because `eval.slicing.by_article_popularity` takes the percentile
over articles *actually seen in train* rather than over the whole catalogue. Machine: laptop,
2026-09-08, test split of each dataset.

| dataset | articles with 0 train clicks | head threshold | head | tail | cold threshold | cold | warm |
|---|---|---|---|---|---|---|---|
| MIND small | 60,192/65,238 (92.3%) | 152 clicks | 860 (1.2%) | 72,292 (98.8%) | 3 | 7,529 | 65,623 |
| EB-NeRD small | 19,272/20,738 (92.9%) | 349 clicks | 803 (0.3%) | 243,844 (99.7%) | 34 | 25,105 | 219,542 |

The zero-click share is confirmed at 92-93% on **both** datasets, so the hazard is real and the
guard is what defuses it. Had the threshold been taken over the full catalogue it would have been
0 on both and every impression would have landed in head.

**The head slice is small and its intervals are correspondingly wide**: 860 and 803 impressions,
just above the harness's 30-impression floor for reporting a slice at all. Head-slice differences
should be read as indicative. This is why slice sizes are printed in every table rather than only
the metric, and it is the direct answer to a viva question about what "head" meant here.

MIND additionally has a `zero_history` slice of 2,214 impressions, users with no prior clicks at
all. EB-NeRD small has none, its cold decile starting at 34 clicks, which is why the cold/warm
threshold is per-dataset and reported rather than fixed.

## 13. Q7: what was actually submitted to each leaderboard (A2)

**The uploaded system is the embeddings-only scorer, not the reported two-stage system.**
Recorded here explicitly so no reader can mistake the leaderboard number for the headline one.
Machine: laptop, 2026-09-08.

| | MIND (Codabench 13967) | EB-NeRD (RecSys 2024) |
|---|---|---|
| impressions written | **2,370,727** | **13,536,710** |
| articles | 120,961 | 125,500 |
| scorer | MiniLM 384-d + entity blend a=0.20 | `contrastive_vector` 768-d |
| archive | `mind_prediction.zip`, 107.3 MB | `ebnerd_predictions.zip`, 230.0 MB |
| inner filename | `prediction.txt` (singular) | `predictions.txt` (plural) |
| validated | **yes**, all checks | **yes**, all checks |

Build cost, EB-NeRD full test set, laptop: **6 m 28 s wall, peak RSS 5.90 GB** for 13,536,710
impressions, about 34,900 impressions/s. Peak RSS stays flat against dataset size because the
stream reads in slices; the 5.90 GB is dominated by the 125,500 x 768 float32 article matrix,
not by the impressions. A1 measured 13 m 30 s for the same set with 768-d vectors, so this is
roughly 2x faster on the same machine.

Article encoding for MIND large test: 120,961 articles, MiniLM on CPU, cached to
`data/processed/mindlarge_test_embeddings.npy` so a rebuild does not re-encode. Entity blend
active on 106,919/120,961 articles (88.4%).

**Offline, this is not our best system.** On EB-NeRD small test the embeddings-only scorer reads
0.5397 AUC against `fused` 0.5380, `bm25` 0.5107 and the two-stage `rerank` **0.7429**. So the
leaderboard entry is roughly 0.20 AUC below the system the report describes.

The gap is structural rather than an oversight: the re-ranker's features need `pop_causal` and
the engagement columns, which the held-out test sets do not ship in a form the feature builder
consumes. BM25 was excluded for a separate practical reason, measured at roughly 1.6 h for
MIND-large's 2M distinct histories. **Reported as two different systems rather than letting the
better offline number stand in for the uploaded one.**

### Validation before upload, and why it is structural

`src.submission.validate` checks inner filename, zip contents, row count, row order and that
every row is a permutation of 1..n, offline, before any upload. MIND allows one submission per
day and EB-NeRD scoring takes hours, so a malformed file costs a day rather than a retry.

Row order is the check that earns its keep: ranks are **positional** against the test file's
candidate order, so a correctly-ranked but reordered file scores as a plausible bad model rather
than erroring. A previous submission on this project covered 0.84% of the test set and scored
0.5012, exactly random, because a smoke test was written to the real upload path. `--limit` now
writes to a `SMOKE-` prefix that cannot occupy the submission filename.

**Verified non-vacuous by injection**, per the rule adopted after four vacuous checks were found
here: wrong inner filename, two rows swapped, truncation to 420 of 50,000 rows, a duplicated
rank, and a folder inside the zip. All five fail with exit 1; the real file exits 0.

## 14. Q3: the NRMS baseline, and why one run is not comparable to ours (A2)

Machine: **cluster**, one u22 node, 16 CPU cores, no GPU used. TensorFlow is CPU-only here, which
is not a limitation for this model at this scale: a full epoch is about 17 minutes.

### 14.1 Faithful reproduction, the benchmark's own split

`ebnerd_nrms_docvec.py` unmodified, `ebnerd_small`, contrastive_vector document embeddings,
history_size 20, title_size 768, npratio 4, batch 32, seed 16.

| Fact | Value |
|---|---|
| Best val AUC | **0.6484** |
| Best epoch | 3 of 10, early-stopped at 7 (patience 4) |
| Wall time | 54 min 11 s |
| Peak RSS | 2.87 GB at the 5% timing probe |

**This number is not comparable to our re-ranker's 0.7429.** The benchmark concatenates the
provided `train` and `validation` blocks, trains on both, then carves its own validation out of
the last day of that pool. Against our temporal split that means it trains on our train, our val
*and* our test, and early-stops on a slice of its own training window. It reproduces their setup
faithfully, which is what Q3 part one asks for, and it answers no question about relative quality.

### 14.2 The comparable run, our temporal split

`src/models/nrms_oursplit.py` (also staged on the cluster) drives the same model, hparams,
document vectors and dataloader from `impressions_{train,val,test}.parquet`: trains on our train,
early-stops on our val, scores our test exactly once. Output is written in the re-ranker's flat
schema, `impression_id | candidate | label | score`, so `src.eval.run` reads both identically.

Status: smoke pass running at the time of writing; the full run has not been recorded.

Two guards in that driver are worth keeping, both aimed at failures that return a plausible
number rather than an error:

- **Article-id coverage.** Our pipeline carries article ids as strings, the document-vector
  parquet keys them as Int32, and the dataloader's `unknown_representation="zeros"` turns every
  miss into a zero vector. A dtype mismatch would therefore train on noise and report a
  believable AUC. The driver asserts coverage and fails below 95%. Measured at the smoke pass:
  **1.0000 on all four checks** (train and val, candidates and history).
- **Score alignment.** Per-impression score lists are asserted to match the candidate list
  length before the flat explode, and the label join is asserted to leave no nulls.

### 14.3 The split history is clean, unlike the engagement history

Checked directly, since section 10's leak made the question live: in
`impressions_{train,val,test}.parquet`, **0.0% of impressions on all three splits** have any
history timestamp at or after their own timestamp. `split.py` takes history from the correct
block. The section 10 leak is confined to `_engagement_weights` in `src/features/build.py` and
does not touch the NRMS feed.

## 15. The 2026-09-12 re-runs on clean features, and the first MIND system (A2)

Everything below was regenerated after the section 10 engagement leak fix. Machine: laptop-naman.
Every val-selected figure that section 10 flagged is now re-measured; nothing contaminated
remains in a reported position.

### 15.1 The 13-arm grid, EB-NeRD small

Full model **0.7489** val (64,365 impressions), **0.7461** test (244,647).

| | contaminated | clean | note |
|---|---|---|---|
| full, val | 0.7575 | **0.7489** | |
| full, test | 0.7429 | **0.7461** | went **up**, see below |
| `stage1_only` gap, val | +0.2077 | **+0.1991** [+0.1963, +0.2020] | headline survives |
| `stage1_only` gap, test | +0.2049 | **+0.2031** [+0.2016, +0.2047] | |
| `minus engage_sim`, val | +0.0085 sig | **+0.0002** [-0.0004, +0.0009] **not sig** | effect was the leak |
| `minus user_read`, val | +0.0007 sig | **-0.0006** [-0.0012, -0.0002] **sig negative** | removing it helps |
| `minus pop_causal`, val | +0.0346 | **+0.0363** [+0.0346, +0.0379] | still dominant |

**`engage_sim` does not survive.** Its +0.0085 was the largest per-feature effect after
popularity and category, and on clean history the interval straddles zero. The read-time-weighted
user vector does not beat the uniform one inside the ranker.

**Test performance improved by +0.0032.** Test features were already correct, since the test split
is drawn from the same block its history comes from, so only the model changed. Removing the leak
improved genuine generalisation rather than deflating an inflated number.

**Consistency check.** `stage1_only` (0.5498) and `pop_only` (0.6954) are bit-identical to the
contaminated run, since neither reads an engagement feature. The fix moved exactly the arms it
should have.

### 15.2 Q9 re-measured

| arm | val AUC |
|---|---|
| causal only, ships | **0.7489** |
| plus lifetime aggregates | **0.7753** |
| difference | **+0.0264** [+0.0249, +0.0277], significant |

Previously +0.0222. The gap widened because the honest arm fell while the leaky arm held, so the
system became more honest and the measured price of honesty rose. Against the +0.1991 two-stage
gain, the leak is worth about one seventh as much.

### 15.3 The history sweep, re-run: the A1 claim is reversed

`results/sweep_history_ebnerd_small_val.json`, per-impression AUC of the similarity feature alone.

| N | uniform | read-time weighted | delta |
|---|---|---|---|
| 1 | 0.5221 | 0.5221 | +0.0000 |
| 5 | 0.5368 | 0.5362 | -0.0006 |
| 10 | 0.5416 | 0.5434 | +0.0018 |
| 20 | 0.5483 | 0.5495 | +0.0011 |
| 50 | 0.5528 | 0.5554 | +0.0026 |
| 100 | **0.5545** | **0.5570** | +0.0025 |

**Both curves rise monotonically and peak at N=100**, the largest value tested. On contaminated
history the curve peaked at N=10.

Two A1 claims fall. "Averaging more history makes the user vector worse", reported by both A1
systems and used as the premise for `info.md`'s read-time hypothesis, is **false on clean
history**: more history is monotonically better across the whole range. And read-time weighting is
not worse than uniform; it is positive at every N above 5, though small.

Caveat: this sweep reports no confidence intervals, and +0.0025 is too small to call real without
one. The monotonic-N finding is large and unambiguous; the weighting comparison is not yet
defensible. Note it does not contradict 15.1, where `engage_sim` as a ranker feature is not
significant: a small gain in the isolated feature need not survive alongside `pop_causal`.

**Consequence for a config we do not own.** `configs/datasets.yaml` sets `history_len: 30` with a
comment citing this sweep as verification. That justification is withdrawn, and N=100 now looks
better. `configs/` is Yash's lane, so this is flagged rather than changed.

### 15.4 First MIND A2 system

Five of ten features, per 15.5. Same trainer, same protocol, same paired bootstrap.

| | EB-NeRD val | MIND val |
|---|---|---|
| full re-ranker | 0.7489 | **0.6512** |
| stage one alone | 0.5498 | 0.6372 |
| two-stage gain | +0.1991 | **+0.0140** [+0.0120, +0.0159] |
| `pop_only` alone | 0.6954 | 0.5475 |
| dominant feature | `pop_causal`, +0.0363 | `emb`, +0.0313 |

MIND test per-impression AUC **0.6539**.

The gain is **14x smaller on MIND**, which is the expected consequence of the availability table
rather than a failure. Feature importance inverts: `emb` dominates on MIND where `pop_causal`
dominates on EB-NeRD, and causal popularity alone is barely above chance on MIND. Stage one is
also stronger on MIND in absolute terms, 0.6372 against 0.5498, so there is less headroom to
begin with.

### 15.5 Feature availability is now enforced, not assumed

`build.py` gains `DATASET_FEATURES` and `features_for(dataset)`. Measured on mind_small:

| source column | MIND state | features lost |
|---|---|---|
| `published_time` | 100% null, all 65,238 articles | `age_hours`, `recency` |
| `total_inviews` / `pageviews` / `read_time` | 100% null | the entire Q9 leaky arm |
| `history.parquet` | absent | `user_read`, `user_scroll`, `engage_sim` |

Five of ten features cannot exist on MIND. They are now dropped explicitly rather than emitted as
null columns, and `build.py` **fails loudly** if a feature it claims to emit is all-null or
constant, because LightGBM cannot tell a column of zeros from a real feature. `train.py`,
`ablate.py` and `q9.py` all read `features_for(dataset)`, and `q9.py` refuses outright on a
dataset with no leaky feature file.

**A MIND trap worth keeping.** `history_timestamps` on MIND is a **null list** of dtype
`List(Datetime)`, not an empty list and not `Null`. So `.list.len()` returns null rather than 0,
and a filter for `list.len() == 0` matches nothing and looks like healthy data. That is the exact
shape that let an earlier MIND leakage test pass over 95,071 rows while checking none of them.
The engagement assertion added in section 10 guards against it with an explicit null check.

The leakage suite now covers MIND: 8 passed, 4 skipped, where the skips are `ebnerd_demo`
(features not built) and MIND's engagement tests (no history to check). Both MIND assertions carry
non-vacuity guards (`checked > 0`, `compared >= 100`) and the injection test asserts the poisoned
count exceeds the honest one.

### 15.6 MIND test split

Full **0.6539** over 73,152 test impressions, against 0.6512 val. The two-stage gain is
**+0.0166** [+0.0149, +0.0184] test against +0.0140 [+0.0120, +0.0159] val, so the intervals
overlap and the EB-NeRD/MIND contrast is stable across the split boundary.

| MIND arm | test AUC | full - arm | 95% CI | sig |
|---|---|---|---|---|
| `pop_only` | 0.5710 | +0.0830 | [+0.0809, +0.0850] | yes |
| `minus_emb` | 0.6263 | +0.0276 | [+0.0263, +0.0290] | yes |
| `stage1_only` | 0.6373 | +0.0166 | [+0.0149, +0.0184] | yes |
| `minus_pop_causal` | 0.6473 | +0.0066 | [+0.0050, +0.0085] | yes |
| `minus_cat_match` | 0.6484 | +0.0056 | [+0.0049, +0.0063] | yes |
| `minus_bm25` | 0.6493 | +0.0046 | [+0.0038, +0.0053] | yes |
| `minus_hist_len` | 0.6526 | +0.0013 | [+0.0008, +0.0018] | yes |

`emb` dominates on both MIND splits and `pop_causal` on both EB-NeRD splits, so the inversion of
feature importance between datasets is not a val artefact.

## 16. Q3 complete: NRMS reproduced, and beaten (A2)

Machine: cluster, u22 node, 16 CPU cores, no GPU. Seed 16.

### 16.1 The numbers

| system | val | test |
|---|---|---|
| NRMS, benchmark script on **their** split protocol | 0.6484 | not scored |
| NRMS, our temporal split (`history_size` 20) | **0.5969** | **0.5938** |
| NRMS, our split, `history_size` 50 | **0.6042** | pending |
| our two-stage re-ranker | **0.7489** | **0.7461** |

**The two-stage system beats NRMS by +0.1520 val and +0.1523 test** on identical impressions.

The reason is not "trees beat attention". NRMS reads article text and click sequence only; it has
no causal popularity, which is our single most valuable feature (removing it costs 0.0363 val).
Our own text-and-embedding-only arm, `stage1_only`, scores 0.5498, close to NRMS's 0.5969. The
comparison is between a model with the click log and one without it.

### 16.2 The one principled change: history_size 20 to 50

| | val per-impression AUC |
|---|---|
| `history_size` 20, benchmark default | 0.5969 |
| `history_size` 50 | 0.6042 |
| **difference** | **+0.0072 [+0.0058, +0.0088]**, significant |

Paired bootstrap, 1,000 resamples, 64,365 shared impressions, aligned on `impression_id` rather
than row position. Seed 16.

Justified by our own re-run sweep (15.3), which finds the user vector improves monotonically with
history length and peaks at N=100. The benchmark default of 20 sits well below that. 50 rather
than 100 because NRMS self-attends over the history, so cost grows faster than linearly, and the
sweep shows most of the gain is reached by 50. The **previous** sweep would have argued for the
opposite change; it ran on leaked history and is withdrawn.

Protocol: the variant scored val only, so test was not used to choose. A separate run scores the
winner on test once.

### 16.3 A driver defect worth recording

`per_impression_auc` originally looped per impression in Python. On 244,647 test impressions it
ran for over four hours without finishing and the job was killed. The parquet is written before
the metric is computed, so the scores survived and the AUC was recovered separately.

Replaced with a vectorised polars form using `rank("average").over("impression_id")`, which
returns in seconds and handles ties identically. The lesson is the ordinary one: a per-group
Python loop over a quarter of a million groups is not a metric implementation, it is a hang.

## 17. N5: the two unswept constants (A2)

`results/sweep_constants_ebnerd_small_val.json`. Isolated feature AUC, EB-NeRD small val, the same
protocol as the history sweep: a feature that cannot reorder candidates inside an impression
scores 0.5 here regardless of how it looks pooled.

### 17.1 The recency half-life does not matter at all

| half-life | 1 h | 6 h | 24 h | 48 h | 168 h |
|---|---|---|---|---|---|
| AUC | 0.5088 | 0.5087 | **0.5087** | 0.5088 | 0.5088 |

Flat to four decimals across a 168x range. `RECENCY_HALFLIFE_H = 24.0` is documented in build.py
as "a starting value, swept as its own ablation"; the sweep is now done and the constant is
irrelevant. This also explains the grid: `minus recency` is one of the few arms that never reaches
significance on either split, because the feature carries almost no within-impression signal at
any setting. **No change recommended**, and the open question is closed rather than left open.

### 17.2 The causal popularity window is badly suboptimal

| window | 1 h | **6 h** | 24 h | 72 h | 168 h | unbounded |
|---|---|---|---|---|---|---|
| AUC | 0.7082 | **0.7349** | 0.7254 | 0.7045 | 0.6902 | **0.6902** |

**A 6 hour window scores 0.7349 against the shipped unbounded 0.6902, +0.0447 on the isolated
feature.** The curve is single-peaked: too narrow loses signal, too wide dilutes recent
popularity with stale counts. Unbounded and 168 h are identical, which is the tell that almost
all the useful signal sits inside the first week and the tail adds only noise.

This matters more than the size of the number suggests, because `pop_causal` is the dominant
feature of the whole system.

No leak is possible from this change: a narrower window only drops older clicks and never admits
newer ones, so the strict "< t" upper bound the leakage test asserts is untouched.
`--pop-window-h` is wired into `build.py` with a default of None, which reproduces the shipped
unbounded behaviour exactly, and `--suffix` lets a variant feature store be built without
overwriting the shipped one.

### 17.3 The 6 h window confirmed at ranker level

The isolated-feature result above is a candidate, not a verdict, so it was re-checked through the
full re-ranker. Same features, same trainer, same seed; only the popularity window differs.

| split | unbounded (ships) | 6 h window | difference |
|---|---|---|---|
| val | 0.7489 | **0.7523** | **+0.0034 [+0.0026, +0.0043]**, significant |
| test | 0.7461 | **0.7523** | **+0.0062 [+0.0058, +0.0067]**, significant |

Significant on both splits, same sign, and the test effect is the larger of the two. `pop_causal`
gain rises from 455,098 to 649,523, so the model leans on it harder once the counts stop being
diluted by stale clicks.

The two splits landing on 0.7523 to four decimals is a coincidence, not a wiring bug: the
underlying files differ as expected (703,229 rows over 64,365 impressions against 2,928,942 over
244,647, with different score means).

**Recommendation: ship the 6 h window.** It is the largest single improvement available in this
lane, it is significant on both splits, it cannot leak, and it costs nothing at serving time.
Not applied here because changing it moves every number in sections 15 and 16, which is a
decision to take deliberately rather than as a side effect of a sweep. The variant feature store
is built and kept as `features_pop6h_*.parquet`.

**Caveat on the size of the isolated number.** The isolated feature gained +0.0447 while the
ranker gained +0.0034 val and +0.0062 test. That gap is the ordinary ensemble story: other
features partially cover for a weaker `pop_causal`, so the isolated measurement is an upper
bound on what the system can gain, not an estimate of it. Quote the ranker numbers.

## 16. N5: the four unswept constants (A2)

All four measured on EB-NeRD small val, clean features. Machine: laptop-naman.

**Scope caveat, stated once and applying to 16.1 to 16.3.** These are **isolated-feature**
measurements: per-impression AUC of the one feature, the same protocol `sweep_history.py` uses.
That is deliberate, since an isolated number cannot be absorbed by a correlated neighbour the way
a LightGBM ablation arm can. It also means a winner here is a **candidate** for a ranker-level
check, not a shipped result. None of 16.1 to 16.3 has been confirmed through the ranker.

### 16.1 Causal popularity window: the largest unshipped win found so far

Currently unbounded, counting every click before `t`. Narrowing the lower bound cannot leak,
since the strict `< t` upper bound is unchanged and a narrower window only drops older clicks.

| window | isolated AUC |
|---|---|
| 1 h | 0.7082 |
| **6 h** | **0.7349** |
| 24 h | 0.7254 |
| 72 h | 0.7045 |
| 168 h | 0.6902 |
| unbounded (current) | 0.6902 |

**A 6 hour window is worth +0.0447 over unbounded**, which is larger than every per-feature effect
in the 13-arm grid except `pop_causal` itself. The curve is single-peaked: 1 h is too noisy,
beyond 72 h it converges to unbounded, because in a two-day EB-NeRD window almost every click is
already inside 168 h.

This says the feature is currently measuring the wrong thing. "How popular has this article ever
been" is a worse signal than "how popular is it right now", which is what a news recommender
should want. **Not shipped**: it needs a ranker-level ablation with a paired CI first, and that
changes a feature the whole system leans on.

### 16.2 Recency half-life: flat, and the feature is near useless alone

| half-life | 1 h | 3 h | 6 h | 12 h | 24 h | 48 h | 96 h | 168 h |
|---|---|---|---|---|---|---|---|---|
| isolated AUC | 0.5088 | 0.5087 | 0.5087 | 0.5088 | 0.5087 | 0.5088 | 0.5088 | 0.5088 |

**Completely flat to four decimals across a 168x range.** The constant does not matter because
the feature barely ranks at all: 0.5088 is a whisker above chance. This agrees with the grid,
where `minus_recency` is indistinguishable from zero on both splits.

`build.py` documents 24.0 as "a starting value, swept as its own ablation". The sweep has now
happened and the answer is that the choice is irrelevant. Left at 24.0; there is no reason to
change it and no reason to tune it.

### 16.3 Scroll completion as a click-quality filter: info.md item 4 is SUPPORTED

`info.md` item 4 proposes dropping history entries the user barely engaged with, and notes it
"complements rather than duplicates" read-time weighting, so the weighting rejection does not
settle it. Held at N=100, the clean-history optimum.

| min scroll % | isolated AUC | history kept |
|---|---|---|
| 0, no filter (current) | 0.5545 | 100.0% |
| 10 | 0.5521 | 88.5% |
| 25 | 0.5559 | 78.5% |
| 50 | 0.5590 | 58.4% |
| 75 | 0.5606 | 46.7% |
| **90** | **0.5609** | **41.1%** |

**Monotonic above 25%, worth +0.0064 at a 90% threshold while discarding 59% of the history.**
Item 4 is supported where item 1 (read-time weighting) was not, which is the distinction
`info.md` itself drew and is worth reporting as such.

Two honest qualifications. The dip at 10% (0.5521, below no-filter) is unexplained and means the
curve is not simply monotonic. And keeping the best 41% of 100 items is roughly 41 items, so part
of this may be the profile-size effect from 15.3 rather than quality per se; separating them needs
a threshold-by-N grid that has not been run.

### 16.4 lambdarank versus binary objective: the choice was right

Same ten features, same rows, same order, same seed. Only the objective differs, so the binary
arm also drops `ndcg` as its early-stopping metric (group structure is irrelevant to its loss)
and uses `auc` instead.

| | val | test |
|---|---|---|
| lambdarank (ships) | **0.7489** | **0.7461** |
| binary | 0.7328 | 0.7295 |
| **lambdarank - binary** | **+0.0161** [+0.0150, +0.0173] | **+0.0165** [+0.0159, +0.0171] |

Significant on both splits, and the two intervals overlap, so it generalises. `train.py`'s
docstring justified lambdarank on the argument that the objective should match the task, since
the metric is a ranking inside an impression rather than a global click probability. That argument
is now measured rather than asserted, and it is worth about +0.016.

Worth noting for the viva: the binary arm's feature importances reorder sharply, with `recency`
and `age_hours` taking the top two gain slots ahead of `pop_causal`. A pointwise objective leans
on absolute-freshness features, while the pairwise one leans on the within-impression contrast
that actually decides the ranking.

