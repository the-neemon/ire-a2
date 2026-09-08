# Q4: serving, cost and what breaks at 10x

*Owner: Yash. All numbers `Machine: laptop-yash`, 8 physical / 12 logical cores, 15.3 GB RAM, no GPU.
Source `results/bench_ebnerd_small.md`, ledger `docs/FACTS.md` section 9. Reproduce with
`make bench`.*

**One machine per comparison.** Every figure in this section came from the same laptop in the
same run. Cluster numbers exist elsewhere in the project and are never mixed into a table here,
because a p99 from one machine and a QPS from another compare nothing.

## Q4.1 Index footprints, RAM and disk measured separately

| Index | Scale | RAM | On disk | RAM/disk |
|---|---|---|---|---|
| BM25 (`bm25s` CSR) | 297,145 postings, 30,388 terms | 7.0 MiB | 3.0 MiB | 2.32x |
| FAISS `IndexFlatIP` | 20,738 x 768-d float32 | 60.8 MiB | 60.8 MiB | 1.00x |
| Feature store (parquet) | 5,514,689 candidate rows | 294.5 MiB | 115.7 MiB | 2.55x |

FAISS is 1.00x because a flat index **is** its raw matrix: nothing is compressed on disk and
nothing is reconstructed on load, so the two numbers are the same bytes. The other two differ
because CSR and parquet both store compressed and expand into memory.

The result that drives everything below: **the dense index is the largest structure despite
covering the fewest objects**. 20,738 articles at 768 float32 dimensions is 60.8 MiB, nearly nine
times the lexical index over the same corpus, because a dense vector spends memory on every
dimension for every article while an inverted index spends it only on terms that actually occur.

## Q4.2 Single-request latency, unbatched

One impression at a time, end to end, which is what a user actually waits for. A1 reported mean
throughput, which is a different quantity and hides the tail.

| Stage | p50 | p95 | **p99** | share of p50 |
|---|---|---|---|---|
| tokenise | 0.70 ms | 1.22 ms | 3.13 ms | 3% |
| bm25 | 1.36 ms | 5.64 ms | 8.16 ms | 6% |
| **ann** | **13.55 ms** | **33.37 ms** | **45.41 ms** | **61%** |
| features | 0.32 ms | 0.53 ms | 1.18 ms | 1% |
| rerank | 5.02 ms | 11.68 ms | 29.47 ms | 23% |
| **total** | **22.06 ms** | **48.94 ms** | **64.90 ms** | |

Broken down per stage rather than end to end, because "p99 is 65 ms" is a number while "p99 is
65 ms of which 45 ms is the exact dense search" is an engineering finding that tells you what to
fix. The tail is worse than the median in a specific place: `rerank` is 23% of p50 but its p99 is
almost 6x its p50, so LightGBM's worst case is disproportionately bad on large candidate pools.

## Q4.3 Cost per 1000 queries at an SLA

Target p99 < 100 ms. **Measured p99 64.90 ms, so the SLA is met with about 1.5x headroom.**

* Serial throughput, one core: **45 QPS, measured.**
* Whole box, 8 physical cores: **363 QPS, projected**, assuming requests are independent and
  scale linearly across cores.
* **$0.000245 per 1000 queries, projected**, at an assumed $0.040 per vCPU-hour.

The price is an assumption and is labelled as such; only the latency it multiplies is measured.
Capacity is priced off **physical** cores, not logical: this path is dense float work in BLAS and
LightGBM, where a hyperthread shares an execution port and adds far less than a real core.

## Q4.4 What breaks first at 10x

The corpus is subsampled and every stage re-timed, rather than extrapolated from one point under
an assumed growth law.

| Corpus | Articles | FAISS RAM | ann p50 | total p50 | total p99 |
|---|---|---|---|---|---|
| 10% | 2,074 | 6.1 MiB | 0.59 ms | 2.53 ms | 4.52 ms |
| 25% | 5,184 | 15.2 MiB | 1.18 ms | 3.29 ms | 5.85 ms |
| 50% | 10,369 | 30.4 MiB | 2.16 ms | 4.58 ms | 8.54 ms |
| 100% | 20,738 | 60.8 MiB | 11.39 ms | 20.06 ms | 33.47 ms |

**`ann` grows 19.4x for a 10x corpus**, which is super-linear where an exact flat scan should be
at worst linear. The excess is the memory hierarchy, not arithmetic: 6.1 MiB of vectors is
cache-resident, 60.8 MiB is not, so each query stops reading from cache and starts streaming from
RAM. **At 10x the catalogue this is a bandwidth problem, not a FLOPs problem**, which is why
buying more cores would not fix it.

### This overturns Assignment 1's answer

A1 concluded the per-impression Python loop was the bottleneck rather than the linear algebra,
and rejected approximate indexes as "10 to 20x faster but exact search was never the bottleneck
at this scale", explicitly flagging a revisit at 10x catalogue. **This is that revisit and it says
the opposite.** With stage two in the path, every Python-side stage is roughly flat in corpus
size, so its share *shrinks* as the catalogue grows. Making the re-ranker faster buys nothing at
scale. The only lever that matters is replacing the exact index with an approximate one.

**ANN is therefore reopened as an outstanding item**, not a closed one. What it would cost in
recall at this catalogue size has not been measured, so the replacement is motivated but
unquantified.

## Limitations, stated rather than buried

**The scaling curve confounds two variables for two of its stages.** Subsampling the corpus also
shortens the query, because the query is built from history titles and a subsampled-out article
contributes none: the mean number of last-30 history items still resolving to a title falls
**29.2 to 2.3** between full corpus and 10%. So the `tokenise` and `bm25` growth factors are
**upper bounds** on the corpus effect, not estimates of it. `ann` is unaffected, since a flat scan
costs vectors x dimensions whatever the query contains, which is why the verdict rests on it.
Isolating the other two needs a bench that holds the query fixed while shrinking only the index.

**Run-to-run variance is large on this machine.** Two full bench runs an hour apart gave
end-to-end p99 of 78.16 ms and 64.90 ms, and re-ranker training of 47.5 s and 97.8 s. The second
is the recorded run. Treat single-run timings from here as good to roughly ±20%.

**Two machines, not one wrong core count.** An earlier draft recorded this as a correction to
the project's environment note, which describes the laptop as 20 cores. The two are different
boxes: the note describes an i7-13700H with 14 physical and 20 logical cores, while every number
in this section ran on a machine reporting 8 physical and 12 logical. Nothing needs rescaling.
What matters for reading this section is that its figures are specific to the 8-core box and do
not transfer to the other one.

**Coverage.** Everything here is EB-NeRD. MIND has no locally built feature store or re-ranker, so
its footprints, latency and cost per 1000 queries are unmeasured rather than estimated.

## Build costs, which are not serving numbers

| Stage | Time |
|---|---|
| BM25 index build | 0.83 s |
| Article vector load | 2.17 s |
| FAISS index build | 0.04 s |
| Re-ranker training (311 trees) | 97.82 s |

Listed separately because they are paid once at deploy time, not per request, and mixing them
into a latency budget would misrepresent both.
