# BM25 ablation — ebnerd_demo / test

25,356 impressions scored (all-clicked and none-clicked pools carry no ranking signal and are dropped by the harness).

Baseline: **title_abstract**. Every delta below is paired on the same impressions and the same 1,000 bootstrap resamples, so a difference counts only if its 95% CI excludes zero.

## Absolute

| variant | auc | mrr | ndcg@5 | ndcg@10 | recall@50 | recall@100 | recall@200 |
|---|---|---|---|---|---|---|---|
| title_abstract | 0.5125 [0.5088, 0.5166] | 0.3273 [0.3241, 0.3308] | 0.3591 [0.3551, 0.3632] | 0.4418 [0.4387, 0.4453] | 0.0108 [0.0095, 0.0122] | 0.0216 [0.0199, 0.0234] | 0.0390 [0.0368, 0.0413] |
| title | 0.5153 [0.5115, 0.5195] | 0.3279 [0.3243, 0.3316] | 0.3601 [0.3561, 0.3645] | 0.4428 [0.4393, 0.4462] | 0.0096 [0.0084, 0.0108] | 0.0210 [0.0193, 0.0228] | 0.0380 [0.0358, 0.0401] |

## Delta against the baseline

| variant | metric | baseline | variant | delta | 95% CI | significant |
|---|---|---|---|---|---|---|
| title | auc | 0.5125 | 0.5153 | +0.0028 | [-0.0005, +0.0064] | no |
| title | mrr | 0.3273 | 0.3279 | +0.0006 | [-0.0026, +0.0035] | no |
| title | ndcg@5 | 0.3591 | 0.3601 | +0.0010 | [-0.0025, +0.0043] | no |
| title | ndcg@10 | 0.4418 | 0.4428 | +0.0010 | [-0.0017, +0.0035] | no |
| title | recall@50 | 0.0108 | 0.0096 | -0.0012 | [-0.0025, -0.0001] | yes |
| title | recall@100 | 0.0216 | 0.0210 | -0.0006 | [-0.0023, +0.0011] | no |
| title | recall@200 | 0.0390 | 0.0380 | -0.0010 | [-0.0032, +0.0010] | no |

## Cost

Index build only. Neither knob changes query latency or index residency: the same number of distinct queries is scored against the same dense score vector either way.

| variant | articles | vocab | index build (s) | scoring (s) |
|---|---|---|---|---|
| title_abstract | 11,777 | 22,105 | 0.7 | 3.4 |
| title | 11,777 | 10,738 | 0.5 | 3.6 |
