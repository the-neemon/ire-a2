# BM25 ablation — mind_small / val

61,894 impressions scored (all-clicked and none-clicked pools carry no ranking signal and are dropped by the harness).

Baseline: **title_abstract**. Every delta below is paired on the same impressions and the same 1,000 bootstrap resamples, so a difference counts only if its 95% CI excludes zero.

## Absolute

| variant | auc | mrr | ndcg@5 | ndcg@10 | recall@50 | recall@100 | recall@200 |
|---|---|---|---|---|---|---|---|
| title_abstract | 0.5840 [0.5814, 0.5865] | 0.3204 [0.3177, 0.3230] | 0.2924 [0.2897, 0.2954] | 0.3494 [0.3468, 0.3522] | 0.0157 [0.0148, 0.0167] | 0.0247 [0.0236, 0.0258] | 0.0371 [0.0357, 0.0384] |
| title | 0.5864 [0.5840, 0.5887] | 0.3182 [0.3157, 0.3209] | 0.2918 [0.2891, 0.2947] | 0.3489 [0.3464, 0.3515] | 0.0158 [0.0148, 0.0167] | 0.0259 [0.0248, 0.0271] | 0.0388 [0.0374, 0.0402] |

## Delta against the baseline

| variant | metric | baseline | variant | delta | 95% CI | significant |
|---|---|---|---|---|---|---|
| title | auc | 0.5840 | 0.5864 | +0.0024 | [+0.0006, +0.0041] | yes |
| title | mrr | 0.3204 | 0.3182 | -0.0022 | [-0.0039, -0.0005] | yes |
| title | ndcg@5 | 0.2924 | 0.2918 | -0.0006 | [-0.0023, +0.0011] | no |
| title | ndcg@10 | 0.3494 | 0.3489 | -0.0005 | [-0.0020, +0.0011] | no |
| title | recall@50 | 0.0157 | 0.0158 | +0.0000 | [-0.0007, +0.0007] | no |
| title | recall@100 | 0.0247 | 0.0259 | +0.0012 | [+0.0004, +0.0021] | yes |
| title | recall@200 | 0.0371 | 0.0388 | +0.0017 | [+0.0007, +0.0028] | yes |

## Cost

Index build only. Neither knob changes query latency or index residency: the same number of distinct queries is scored against the same dense score vector either way.

| variant | articles | vocab | index build (s) | scoring (s) |
|---|---|---|---|---|
| title_abstract | 65,238 | 44,264 | 6.2 | 88.7 |
| title | 65,238 | 24,681 | 2.2 | 63.9 |
