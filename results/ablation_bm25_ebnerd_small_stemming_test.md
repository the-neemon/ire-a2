# BM25 ablation — ebnerd_small / test

244,647 impressions scored (all-clicked and none-clicked pools carry no ranking signal and are dropped by the harness).

Baseline: **stem**. Every delta below is paired on the same impressions and the same 1,000 bootstrap resamples, so a difference counts only if its 95% CI excludes zero.

## Absolute

| variant | auc | mrr | ndcg@5 | ndcg@10 | recall@50 | recall@100 | recall@200 |
|---|---|---|---|---|---|---|---|
| stem | 0.5107 [0.5094, 0.5120] | 0.3257 [0.3245, 0.3269] | 0.3577 [0.3563, 0.3591] | 0.4409 [0.4397, 0.4421] | 0.0072 [0.0069, 0.0075] | 0.0133 [0.0128, 0.0138] | 0.0247 [0.0241, 0.0253] |
| no_stem | 0.5105 [0.5092, 0.5118] | 0.3261 [0.3249, 0.3272] | 0.3579 [0.3565, 0.3593] | 0.4411 [0.4399, 0.4422] | 0.0070 [0.0067, 0.0073] | 0.0130 [0.0126, 0.0135] | 0.0236 [0.0230, 0.0242] |

## Delta against the baseline

| variant | metric | baseline | variant | delta | 95% CI | significant |
|---|---|---|---|---|---|---|
| no_stem | auc | 0.5107 | 0.5105 | -0.0002 | [-0.0011, +0.0007] | no |
| no_stem | mrr | 0.3257 | 0.3261 | +0.0003 | [-0.0005, +0.0012] | no |
| no_stem | ndcg@5 | 0.3577 | 0.3579 | +0.0002 | [-0.0006, +0.0011] | no |
| no_stem | ndcg@10 | 0.4409 | 0.4411 | +0.0002 | [-0.0005, +0.0009] | no |
| no_stem | recall@50 | 0.0072 | 0.0070 | -0.0002 | [-0.0004, +0.0001] | no |
| no_stem | recall@100 | 0.0133 | 0.0130 | -0.0003 | [-0.0006, +0.0001] | no |
| no_stem | recall@200 | 0.0247 | 0.0236 | -0.0010 | [-0.0016, -0.0005] | yes |

## Cost

Index build only. Neither knob changes query latency or index residency: the same number of distinct queries is scored against the same dense score vector either way.

| variant | articles | vocab | index build (s) | scoring (s) |
|---|---|---|---|---|
| stem | 20,738 | 30,388 | 1.1 | 45.3 |
| no_stem | 20,738 | 43,451 | 1.0 | 50.6 |
