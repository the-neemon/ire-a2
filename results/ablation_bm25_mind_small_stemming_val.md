# BM25 ablation — mind_small / val

61,894 impressions scored (all-clicked and none-clicked pools carry no ranking signal and are dropped by the harness).

Baseline: **stem**. Every delta below is paired on the same impressions and the same 1,000 bootstrap resamples, so a difference counts only if its 95% CI excludes zero.

## Absolute

| variant | auc | mrr | ndcg@5 | ndcg@10 | recall@50 | recall@100 | recall@200 |
|---|---|---|---|---|---|---|---|
| stem | 0.5840 [0.5814, 0.5865] | 0.3204 [0.3177, 0.3230] | 0.2924 [0.2897, 0.2954] | 0.3494 [0.3468, 0.3522] | 0.0157 [0.0148, 0.0167] | 0.0247 [0.0236, 0.0258] | 0.0371 [0.0357, 0.0384] |
| no_stem | 0.5816 [0.5790, 0.5840] | 0.3200 [0.3174, 0.3227] | 0.2914 [0.2888, 0.2943] | 0.3486 [0.3459, 0.3513] | 0.0159 [0.0150, 0.0169] | 0.0260 [0.0248, 0.0271] | 0.0391 [0.0378, 0.0405] |

## Delta against the baseline

| variant | metric | baseline | variant | delta | 95% CI | significant |
|---|---|---|---|---|---|---|
| no_stem | auc | 0.5840 | 0.5816 | -0.0023 | [-0.0034, -0.0013] | yes |
| no_stem | mrr | 0.3204 | 0.3200 | -0.0005 | [-0.0015, +0.0007] | no |
| no_stem | ndcg@5 | 0.2924 | 0.2914 | -0.0010 | [-0.0021, +0.0001] | no |
| no_stem | ndcg@10 | 0.3494 | 0.3486 | -0.0008 | [-0.0018, +0.0001] | no |
| no_stem | recall@50 | 0.0157 | 0.0159 | +0.0002 | [-0.0003, +0.0007] | no |
| no_stem | recall@100 | 0.0247 | 0.0260 | +0.0013 | [+0.0006, +0.0019] | yes |
| no_stem | recall@200 | 0.0371 | 0.0391 | +0.0021 | [+0.0013, +0.0028] | yes |

## Cost

Index build only. Neither knob changes query latency or index residency: the same number of distinct queries is scored against the same dense score vector either way.

| variant | articles | vocab | index build (s) | scoring (s) |
|---|---|---|---|---|
| stem | 65,238 | 44,264 | 4.7 | 87.3 |
| no_stem | 65,238 | 60,914 | 4.0 | 78.4 |
