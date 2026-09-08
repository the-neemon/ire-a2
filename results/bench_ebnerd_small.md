# Q4 serving and scale bench — ebnerd_small / val

**Machine:** 8 physical cores (12 logical), 15.3 GB RAM, linux x86_64, no GPU. Every number below came from this one machine; a latency from here and a latency from a cluster node are not comparable and must not appear in one comparison.

2,000 requests timed **one at a time**, never batched.

## Q4.1 Index footprints

RAM and serialised on-disk bytes reported separately, because they differ by large and different factors per index and the viva asked for both.

| Index | Scale | RAM | On disk | RAM/disk |
|---|---|---|---|---|
| BM25 (bm25s CSR) | 297,145 postings, 30,388 terms | 7.0 MiB | 3.0 MiB | 2.32x |
| FAISS IndexFlatIP | 20,738 x 768-d float32 | 60.8 MiB | 60.8 MiB | 1.00x |
| Feature store (parquet) | 5,514,689 candidate rows | 294.5 MiB | 115.7 MiB | 2.55x |

BM25's RAM splits into 2.5 MiB of CSR arrays and ~4.5 MiB of Python vocabulary dict. Only the arrays are a measured buffer size; the dict figure is an approximation from string lengths plus per-entry overhead, and it is the part that scales worst.

FAISS is exact (`IndexFlatIP`), so its RAM is exactly vectors x dim x 4 bytes with no structure on top, and RAM and disk agree to within a header. That is the number an approximate index would have to beat.

## Q4.2 Single-request latency

p99, not the mean. A1 reported mean throughput over a whole split; batching amortises per-call overhead a real request cannot, so that number flatters the tail. Stages are in the order a request meets them.

| Stage | p50 | p95 | **p99** | max | share of p50 |
|---|---|---|---|---|---|
| tokenise | 0.70 ms | 1.22 ms | **3.13 ms** | 12.72 ms | 3% |
| bm25 | 1.36 ms | 5.64 ms | **8.16 ms** | 19.98 ms | 6% |
| ann | 13.55 ms | 33.37 ms | **45.41 ms** | 61.75 ms | 61% |
| features | 0.32 ms | 0.53 ms | **1.18 ms** | 19.61 ms | 1% |
| rerank | 5.02 ms | 11.68 ms | **29.47 ms** | 38.06 ms | 23% |
| **total** | 22.06 ms | 48.94 ms | **64.90 ms** | 90.75 ms |  |

## Q4.3 Cost per 1000 queries at the SLA

SLA: p99 < 100 ms. Measured p99 **64.90 ms** -> **MEETS** it, with 1.5x headroom.

- Serial throughput, one core: **45 QPS**, measured.
- Whole box, 8 physical cores: 363 QPS, **projected**, assuming requests are independent and scale linearly across cores. Physical cores, not logical: this path is dense float work in BLAS and LightGBM, and a hyperthread sharing an execution port adds far less than a real core.
- **$0.000245 per 1000 queries**, **projected** at an assumed $0.040/vCPU-hour. The price is an assumption, not a measurement; only the latency it multiplies is measured.

## Q4.4 Scaling: what breaks first

The corpus is subsampled and every stage re-timed, rather than extrapolated from one point under an assumed growth law.

| Corpus | Articles | BM25 build | BM25 RAM | FAISS RAM | tokenise p50 | bm25 p50 | ann p50 | rerank p50 | total p50 | total p99 |
|---|---|---|---|---|---|---|---|---|---|---|
| 10% | 2,074 | 0.09 s | 0.3 MiB | 6.1 MiB | 0.25 | 0.18 | 0.59 | 1.26 | 2.53 | 4.52 |
| 25% | 5,184 | 0.26 s | 0.7 MiB | 15.2 MiB | 0.31 | 0.29 | 1.18 | 1.26 | 3.29 | 5.85 |
| 50% | 10,369 | 0.44 s | 1.3 MiB | 30.4 MiB | 0.39 | 0.49 | 2.16 | 1.30 | 4.58 | 8.54 |
| 100% | 20,738 | 0.77 s | 2.5 MiB | 60.8 MiB | 0.78 | 1.54 | 11.39 | 4.90 | 20.06 | 33.47 |

Corpus grew 10.0x across the measured points. Per-stage p50 growth: `tokenise` 3.13x, `bm25` 8.42x, `ann` 19.39x, `features` 2.43x, `rerank` 3.89x.

**`ann` is what breaks first.** It both grows with the corpus and dominates the total at full scale, and its growth is *super*-linear: 19.4x for a 10x corpus. `IndexFlatIP` is O(vectors x dim) per query, so linear is the most it should be. The excess is the memory hierarchy, not the algorithm: at the smallest scale the whole vector matrix fits in cache and at full scale it does not, so each query moves from cache-resident to streaming from RAM. That is exactly the regime where an approximate index earns its keep, and it says the 10x answer is a bandwidth problem rather than a FLOPs problem.

**A1's answer no longer holds.** A1 found the per-impression Python loop was the bottleneck rather than the linear algebra. With the re-ranker in the path that is no longer true: the Python-side stages (`tokenise`, `features`, `rerank` over a fixed-size candidate pool) are all roughly flat in corpus size, so their share of the total shrinks as the catalogue grows. Making stage two cheaper buys nothing at scale; replacing the exact index with an approximate one is the only lever that matters.

**Caveat on `tokenise` and `bm25`, stated because it changes how those two rows should be read.** Subsampling the corpus also shortens the query: the query is built from the titles of the user's history, and a history article dropped from the subsample contributes no title. Measured, the mean number of last-30 history items that still resolve to a title falls from 29.2 at full corpus to 2.3 at 10%. So those two rows conflate corpus size with query length and their growth factors are upper bounds on the true corpus effect, not estimates of it. `ann` is unaffected: a FAISS scan costs vectors x dim regardless of what the query vector contains, so the stage the verdict rests on is measured cleanly. Fixing this properly needs the query held fixed while only the index shrinks, which is a separate bench.

## Build costs (not serving numbers)

| Stage | Time |
|---|---|
| bm25_index_build_s | 0.83 s |
| article_vector_load_s | 2.17 s |
| faiss_index_build_s | 0.04 s |
| rerank_train_s | 97.82 s |
| rerank_trees | 311 |
