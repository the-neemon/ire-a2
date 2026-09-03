# IRE Assignment 2: Learning from Click-Logs on EB-NeRD and MIND

CS4.406 Information Retrieval & Extraction. Team of two: Naman Singhal (2024114013) and
Yash More (2024114004).

A two-stage retrieve-then-rank news recommender for the MIND and EB-NeRD datasets. It extends our
Assignment-1 lexical and semantic retrieval systems with **behavioural signals from click-logs**: a
re-ranker over engineered click-history and session features, a reproduced-then-beaten baseline, and
a measured serving and scale analysis.

## Reproduce

```bash
make venv          # .venv with CPU-only torch and dependencies
make all           # download -> temporal split -> retrieve -> features -> rerank -> evaluate
make test          # leakage and behaviour-window assertions
```

`make all` is the one-command reproduce. Individual stages are documented at the top of the
`Makefile`. Restrict to one dataset with `make DATASETS=mind_small all`.

Everything runs CPU-only. Article encoding is the one stage worth a free-tier GPU.

## Layout

```
src/pipeline/     download, temporal split, text export, streaming submission
src/retrieval/    stage 1: BM25 (sparse), embeddings + FAISS, fusion, candidate generation
src/features/     behavioural features from click-logs, with the behaviour-window boundary
src/rerank/       stage 2: the re-ranker
src/eval/         per-impression metrics, paired bootstrap, slicing, beyond-accuracy, benchmarks
src/submission/   Codabench prediction files
tests/            leakage and behaviour-window assertions
configs/          dataset config, stopword lists
docs/             FACTS.md and ABLATIONS.md, the evidence behind every reported number
```

## Evidence

Every number we report is recorded where it was produced, with the command that produced it:

- **[docs/FACTS.md](docs/FACTS.md)**: one row per measured number. Value, scope, method, source, date.
- **[docs/ABLATIONS.md](docs/ABLATIONS.md)**: one row per experiment, **including rejected ones**.
  Hypothesis, delta, paired bootstrap 95% CI, cost, verdict.

A number in the design note with no row in `FACTS.md` is a number we cannot defend.

## Method rules

These are enforced in code and tests, not by discipline.

- **Splits are temporal, never random.** Train strictly precedes val strictly precedes test.
- **No future-click leakage.** Every feature value used for an impression is computable strictly
  before that impression's timestamp. `tests/` asserts this, and the assertions are verified
  non-vacuous by injecting a future click and watching them fire.
- **Metrics are reported with and without serving-unavailable features.** `total_inviews`,
  `total_pageviews` and `total_read_time` are lifetime aggregates that embed the future. No shipped
  scorer reads them. See the anti-gaming table in `docs/ABLATIONS.md` for what they would be worth.
- **Every claimed gain ships a paired bootstrap 95% CI** on shared resamples that excludes zero.
  Paired, because two systems scored on the same impressions have correlated errors.
- **Selection happens on val. Test is scored once.**

## Status

| Requirement | Status |
|---|---|
| Q1 click-history and session features | in progress |
| Q2 two-stage retrieve-then-rank | in progress |
| Q3 baseline reproduced then beaten | not started |
| Q4 serving and scale analysis | partial, A1 numbers carried forward |
| Q5 extended evaluation with slices and CIs | harness reused from A1 |
| Q6 design note | not started |
