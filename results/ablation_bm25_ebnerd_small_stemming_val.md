# BM25 ablation — ebnerd_small / val

64,365 impressions scored (all-clicked and none-clicked pools carry no ranking signal and are dropped by the harness).

Baseline: **stem**. Every delta below is paired on the same impressions and the same 1,000 bootstrap resamples, so a difference counts only if its 95% CI excludes zero.

## Absolute

| variant | auc | mrr | ndcg@5 | ndcg@10 | recall@50 | recall@100 | recall@200 |
|---|---|---|---|---|---|---|---|
| stem | 0.5205 [0.5177, 0.5230] | 0.3418 [0.3393, 0.3443] | 0.3794 [0.3766, 0.3823] | 0.4607 [0.4585, 0.4630] | 0.0052 [0.0047, 0.0058] | 0.0110 [0.0101, 0.0118] | 0.0214 [0.0202, 0.0225] |
| no_stem | 0.5202 [0.5176, 0.5226] | 0.3421 [0.3398, 0.3444] | 0.3793 [0.3765, 0.3819] | 0.4610 [0.4589, 0.4632] | 0.0061 [0.0055, 0.0067] | 0.0123 [0.0114, 0.0131] | 0.0234 [0.0222, 0.0246] |

## Delta against the baseline

| variant | metric | baseline | variant | delta | 95% CI | significant |
|---|---|---|---|---|---|---|
| no_stem | auc | 0.5205 | 0.5202 | -0.0003 | [-0.0019, +0.0014] | no |
| no_stem | mrr | 0.3418 | 0.3421 | +0.0004 | [-0.0011, +0.0019] | no |
| no_stem | ndcg@5 | 0.3794 | 0.3793 | -0.0001 | [-0.0017, +0.0014] | no |
| no_stem | ndcg@10 | 0.4607 | 0.4610 | +0.0003 | [-0.0009, +0.0017] | no |
| no_stem | recall@50 | 0.0052 | 0.0061 | +0.0009 | [+0.0004, +0.0014] | yes |
| no_stem | recall@100 | 0.0110 | 0.0123 | +0.0013 | [+0.0006, +0.0021] | yes |
| no_stem | recall@200 | 0.0214 | 0.0234 | +0.0020 | [+0.0011, +0.0030] | yes |

## Cost

Index build only. Neither knob changes query latency or index residency: the same number of distinct queries is scored against the same dense score vector either way.

| variant | articles | vocab | index build (s) | scoring (s) |
|---|---|---|---|---|
| stem | 20,738 | 30,388 | 1.1 | 19.2 |
| no_stem | 20,738 | 43,451 | 1.0 | 23.6 |
