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

## Datasets

Development runs on the small tiers; both leaderboards score the large ones only.

| dataset | development | submission |
|---|---|---|
| EB-NeRD | `ebnerd_small` (20,738 articles) | `ebnerd_testset` (125,500 articles, 13.5M impressions) |
| MIND | `MINDsmall_train` + `MINDsmall_dev` (65,238 articles) | `MINDlarge_test` (120,961 articles, 2.37M impressions) |

`ebnerd_demo` is used only as a smoke test that the pipeline runs end to end. No reported number
comes from it: its head slice is too small to carry a confidence interval.

Article vectors default to `Ekstra_Bladet_contrastive_vector` (768-d, provided) for EB-NeRD and
`all-MiniLM-L6-v2` (384-d, self-encoded) for MIND, both chosen by measurement. Alternatives are run
as ablations rather than swapped in silently, and each has a row in
[docs/ABLATIONS.md](docs/ABLATIONS.md).

Split boundaries and seeds live in [configs/datasets.yaml](configs/datasets.yaml). Splits are
temporal, so changing a boundary changes every number downstream of it.

`make download` fetches everything. MIND is a gated HuggingFace repo and needs both an accepted
licence on the dataset page and a bearer token.

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
- **[docs/REPORT-NOTES.md](docs/REPORT-NOTES.md)**: the narrative view the design note draws
  from. Same numbers as the two ledgers, organised as an argument rather than a log. If it
  disagrees with a ledger, the ledger wins.

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

All measured numbers below are per-impression AUC on the EB-NeRD small **test** split, selected on
val and scored once. Every one has a row in [docs/FACTS.md](docs/FACTS.md).

| Requirement | Status | Where |
|---|---|---|
| Q1 click-history and session features | **done**, 22 features on EB-NeRD, 17 on MIND | [docs/report/q1-features-and-availability.md](docs/report/q1-features-and-availability.md) |
| Q2 two-stage retrieve-then-rank | **done**, +0.2528 [+0.2514, +0.2543] over fused retrieval | [docs/report/q2-reranker-and-ablations.md](docs/report/q2-reranker-and-ablations.md) |
| Q3 baseline reproduced then beaten | **done** on EB-NeRD, NRMS 0.5938, ours 0.7908 | [docs/report/q3-nrms-baseline.md](docs/report/q3-nrms-baseline.md) |
| Q4 serving and scale analysis | **done**, re-measured on the shipped model | [docs/report/q4-serving-and-scale.md](docs/report/q4-serving-and-scale.md) |
| Q5 extended evaluation with slices and CIs | **done**, both datasets, both splits | [docs/report/q5-metrics-and-methodology.md](docs/report/q5-metrics-and-methodology.md) |
| Q6 design note | **done** | [docs/design-note/design-note.pdf](docs/design-note/design-note.pdf) |
| Q7 deliverables | **done**; MIND scored and screenshotted, EB-NeRD uploaded but unscorable (no Codabench worker available) | [docs/report/q7-leaderboard-submissions.md](docs/report/q7-leaderboard-submissions.md) |
| Q8 commit policy | **honoured**, incremental commits carrying their measured result | `git log` |
| Q9 anti-gaming and leakage | **done**, tests fire on injection | [docs/report/q9-anti-gaming.md](docs/report/q9-anti-gaming.md) |

`make test` is 32 passed, 3 skipped, 0 failed with EB-NeRD demo and small and MIND small all built.
The skip count depends on which datasets are present, since each missing dataset skips its own
assertions; the three that remain are assertions that do not apply to MIND, which ships no
per-item history timestamps and no engagement data.

Known gaps, stated rather than left to be discovered:

- **There is no EB-NeRD leaderboard screenshot, and we cannot produce one.** The file was
  uploaded, but Codabench runs the RecSys 2024 competition on volunteered compute workers, none
  were available, and the queue is first-come-first-served, so offering a machine would not
  guarantee our own submission runs. MIND scored: **0.6473 AUC**, rank 54, screenshot in
  [docs/report/screenshots/](docs/report/screenshots/). Every EB-NeRD number in this report comes
  from our own labelled test split rather than the leaderboard, so nothing depends on it.
- **The baseline covers one dataset.** NRMS was reproduced and beaten on EB-NeRD only.
- **Approximate search is motivated but unmeasured.** Q4 shows the exact index is what breaks at
  10x; we did not measure the recall an IVF or HNSW index would cost.

## Prediction files

The Codabench prediction files are **deliberately not in this repository**. `ebnerd_predictions.zip`
is 230 MB and `mind_prediction.zip` 107 MB, against Q8's rule that no large files go in git, so
`submissions/` and `*.zip` are both in [.gitignore](.gitignore). They are submitted through Moodle
instead. Rebuild them from a trained model with:

```bash
python -m src.pipeline.submit_ebnerd_rerank --model models/ebnerd_small_submission.txt
python -m src.pipeline.submit_mind_rerank   --model models/mind_small_submission.txt
python -m src.submission.validate ebnerd submissions/ebnerd_predictions.zip
```

The uploaded model is **not** the reported one and the difference is documented rather than
smoothed over: Codabench withholds `article_ids_clicked`, so the five click-popularity features
have no source on the test period and the exposure features replace them. That costs 0.7908 to
0.7351 on our own labelled test split. Both numbers appear in the design note, never one standing
in for the other.

## AI usage

Per Q7.4, the AI usage log, the full prompt history and the marking of AI-generated against
human-written code are in **[docs/ai-usage/](docs/ai-usage/)**.
