# BM25 ablation — mind_small / test

73,152 impressions scored (all-clicked and none-clicked pools carry no ranking signal and are dropped by the harness).

Baseline: **stem**. Every delta below is paired on the same impressions and the same 1,000 bootstrap resamples, so a difference counts only if its 95% CI excludes zero.

## Absolute

| variant | auc | mrr | ndcg@5 | ndcg@10 | recall@50 | recall@100 | recall@200 |
|---|---|---|---|---|---|---|---|
| stem | 0.5685 [0.5663, 0.5707] | 0.3108 [0.3086, 0.3134] | 0.2868 [0.2843, 0.2895] | 0.3479 [0.3456, 0.3505] | 0.0062 [0.0057, 0.0068] | 0.0126 [0.0119, 0.0133] | 0.0226 [0.0215, 0.0235] |
| no_stem | 0.5657 [0.5634, 0.5679] | 0.3103 [0.3080, 0.3128] | 0.2848 [0.2822, 0.2876] | 0.3468 [0.3444, 0.3493] | 0.0066 [0.0061, 0.0071] | 0.0134 [0.0127, 0.0142] | 0.0234 [0.0224, 0.0244] |

## Delta against the baseline

| variant | metric | baseline | variant | delta | 95% CI | significant |
|---|---|---|---|---|---|---|
| no_stem | auc | 0.5685 | 0.5657 | -0.0028 | [-0.0039, -0.0018] | yes |
| no_stem | mrr | 0.3108 | 0.3103 | -0.0005 | [-0.0016, +0.0006] | no |
| no_stem | ndcg@5 | 0.2868 | 0.2848 | -0.0019 | [-0.0030, -0.0009] | yes |
| no_stem | ndcg@10 | 0.3479 | 0.3468 | -0.0011 | [-0.0020, -0.0002] | yes |
| no_stem | recall@50 | 0.0062 | 0.0066 | +0.0004 | [+0.0000, +0.0007] | yes |
| no_stem | recall@100 | 0.0126 | 0.0134 | +0.0009 | [+0.0004, +0.0013] | yes |
| no_stem | recall@200 | 0.0226 | 0.0234 | +0.0009 | [+0.0004, +0.0014] | yes |

## Cost

Index build only. Neither knob changes query latency or index residency: the same number of distinct queries is scored against the same dense score vector either way.

| variant | articles | vocab | index build (s) | scoring (s) |
|---|---|---|---|---|
| stem | 65,238 | 44,264 | 4.7 | 149.4 |
| no_stem | 65,238 | 60,914 | 4.0 | 133.7 |
