# BM25 ablation — ebnerd_demo / val

6,872 impressions scored (all-clicked and none-clicked pools carry no ranking signal and are dropped by the harness).

Baseline: **stem**. Every delta below is paired on the same impressions and the same 1,000 bootstrap resamples, so a difference counts only if its 95% CI excludes zero.

## Absolute

| variant | auc | mrr | ndcg@5 | ndcg@10 | recall@50 | recall@100 | recall@200 |
|---|---|---|---|---|---|---|---|
| stem | 0.5234 [0.5154, 0.5309] | 0.3456 [0.3387, 0.3526] | 0.3814 [0.3736, 0.3897] | 0.4627 [0.4564, 0.4694] | 0.0114 [0.0090, 0.0138] | 0.0217 [0.0185, 0.0250] | 0.0434 [0.0386, 0.0479] |
| no_stem | 0.5209 [0.5134, 0.5283] | 0.3444 [0.3374, 0.3510] | 0.3802 [0.3725, 0.3880] | 0.4615 [0.4549, 0.4680] | 0.0127 [0.0102, 0.0151] | 0.0224 [0.0191, 0.0258] | 0.0439 [0.0392, 0.0487] |

## Delta against the baseline

| variant | metric | baseline | variant | delta | 95% CI | significant |
|---|---|---|---|---|---|---|
| no_stem | auc | 0.5234 | 0.5209 | -0.0025 | [-0.0077, +0.0025] | no |
| no_stem | mrr | 0.3456 | 0.3444 | -0.0012 | [-0.0058, +0.0035] | no |
| no_stem | ndcg@5 | 0.3814 | 0.3802 | -0.0012 | [-0.0059, +0.0039] | no |
| no_stem | ndcg@10 | 0.4627 | 0.4615 | -0.0012 | [-0.0052, +0.0030] | no |
| no_stem | recall@50 | 0.0114 | 0.0127 | +0.0013 | [-0.0007, +0.0032] | no |
| no_stem | recall@100 | 0.0217 | 0.0224 | +0.0007 | [-0.0020, +0.0035] | no |
| no_stem | recall@200 | 0.0434 | 0.0439 | +0.0006 | [-0.0036, +0.0050] | no |

## Cost

Index build only. Neither knob changes query latency or index residency: the same number of distinct queries is scored against the same dense score vector either way.

| variant | articles | vocab | index build (s) | scoring (s) |
|---|---|---|---|---|
| stem | 11,777 | 22,105 | 0.9 | 2.1 |
| no_stem | 11,777 | 31,515 | 0.6 | 1.5 |
