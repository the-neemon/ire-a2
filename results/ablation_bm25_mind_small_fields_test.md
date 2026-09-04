# BM25 ablation — mind_small / test

73,152 impressions scored (all-clicked and none-clicked pools carry no ranking signal and are dropped by the harness).

Baseline: **title_abstract**. Every delta below is paired on the same impressions and the same 1,000 bootstrap resamples, so a difference counts only if its 95% CI excludes zero.

## Absolute

| variant | auc | mrr | ndcg@5 | ndcg@10 | recall@50 | recall@100 | recall@200 |
|---|---|---|---|---|---|---|---|
| title_abstract | 0.5685 [0.5663, 0.5707] | 0.3108 [0.3086, 0.3134] | 0.2868 [0.2843, 0.2895] | 0.3479 [0.3456, 0.3505] | 0.0062 [0.0057, 0.0068] | 0.0126 [0.0119, 0.0133] | 0.0226 [0.0215, 0.0235] |
| title | 0.5750 [0.5730, 0.5773] | 0.3108 [0.3085, 0.3133] | 0.2872 [0.2847, 0.2900] | 0.3489 [0.3467, 0.3514] | 0.0074 [0.0068, 0.0080] | 0.0134 [0.0127, 0.0142] | 0.0231 [0.0221, 0.0242] |

## Delta against the baseline

| variant | metric | baseline | variant | delta | 95% CI | significant |
|---|---|---|---|---|---|---|
| title | auc | 0.5685 | 0.5750 | +0.0065 | [+0.0047, +0.0083] | yes |
| title | mrr | 0.3108 | 0.3108 | +0.0000 | [-0.0017, +0.0016] | no |
| title | ndcg@5 | 0.2868 | 0.2872 | +0.0005 | [-0.0012, +0.0020] | no |
| title | ndcg@10 | 0.3479 | 0.3489 | +0.0011 | [-0.0003, +0.0023] | no |
| title | recall@50 | 0.0062 | 0.0074 | +0.0011 | [+0.0006, +0.0016] | yes |
| title | recall@100 | 0.0126 | 0.0134 | +0.0009 | [+0.0002, +0.0015] | yes |
| title | recall@200 | 0.0226 | 0.0231 | +0.0006 | [-0.0003, +0.0014] | no |

## Cost

Index build only. Neither knob changes query latency or index residency: the same number of distinct queries is scored against the same dense score vector either way.

| variant | articles | vocab | index build (s) | scoring (s) |
|---|---|---|---|---|
| title_abstract | 65,238 | 44,264 | 6.2 | 147.3 |
| title | 65,238 | 24,681 | 2.2 | 111.3 |
