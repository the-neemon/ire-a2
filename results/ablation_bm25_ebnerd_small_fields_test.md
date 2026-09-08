# BM25 ablation — ebnerd_small / test

244,647 impressions scored (all-clicked and none-clicked pools carry no ranking signal and are dropped by the harness).

Baseline: **title_abstract**. Every delta below is paired on the same impressions and the same 1,000 bootstrap resamples, so a difference counts only if its 95% CI excludes zero.

## Absolute

| variant | auc | mrr | ndcg@5 | ndcg@10 | recall@50 | recall@100 | recall@200 |
|---|---|---|---|---|---|---|---|
| title_abstract | 0.5107 [0.5094, 0.5120] | 0.3257 [0.3245, 0.3269] | 0.3577 [0.3563, 0.3591] | 0.4409 [0.4397, 0.4421] | 0.0072 [0.0069, 0.0075] | 0.0133 [0.0128, 0.0138] | 0.0247 [0.0241, 0.0253] |
| title | 0.5150 [0.5138, 0.5163] | 0.3281 [0.3270, 0.3292] | 0.3616 [0.3603, 0.3630] | 0.4430 [0.4420, 0.4441] | 0.0070 [0.0067, 0.0074] | 0.0134 [0.0129, 0.0139] | 0.0242 [0.0235, 0.0248] |

## Delta against the baseline

| variant | metric | baseline | variant | delta | 95% CI | significant |
|---|---|---|---|---|---|---|
| title | auc | 0.5107 | 0.5150 | +0.0043 | [+0.0031, +0.0055] | yes |
| title | mrr | 0.3257 | 0.3281 | +0.0024 | [+0.0014, +0.0034] | yes |
| title | ndcg@5 | 0.3577 | 0.3616 | +0.0039 | [+0.0029, +0.0051] | yes |
| title | ndcg@10 | 0.4409 | 0.4430 | +0.0021 | [+0.0012, +0.0030] | yes |
| title | recall@50 | 0.0072 | 0.0070 | -0.0002 | [-0.0005, +0.0002] | no |
| title | recall@100 | 0.0133 | 0.0134 | +0.0001 | [-0.0004, +0.0005] | no |
| title | recall@200 | 0.0247 | 0.0242 | -0.0005 | [-0.0011, +0.0001] | no |

## Cost

Index build only. Neither knob changes query latency or index residency: the same number of distinct queries is scored against the same dense score vector either way.

| variant | articles | vocab | index build (s) | scoring (s) |
|---|---|---|---|---|
| title_abstract | 20,738 | 30,388 | 1.0 | 38.1 |
| title | 20,738 | 15,132 | 0.6 | 35.9 |
