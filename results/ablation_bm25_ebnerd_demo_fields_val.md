# BM25 ablation — ebnerd_demo / val

6,872 impressions scored (all-clicked and none-clicked pools carry no ranking signal and are dropped by the harness).

Baseline: **title_abstract**. Every delta below is paired on the same impressions and the same 1,000 bootstrap resamples, so a difference counts only if its 95% CI excludes zero.

## Absolute

| variant | auc | mrr | ndcg@5 | ndcg@10 | recall@50 | recall@100 | recall@200 |
|---|---|---|---|---|---|---|---|
| title_abstract | 0.5234 [0.5154, 0.5309] | 0.3456 [0.3387, 0.3526] | 0.3814 [0.3736, 0.3897] | 0.4627 [0.4564, 0.4694] | 0.0114 [0.0090, 0.0138] | 0.0217 [0.0185, 0.0250] | 0.0434 [0.0386, 0.0479] |
| title | 0.5243 [0.5166, 0.5318] | 0.3430 [0.3355, 0.3503] | 0.3819 [0.3737, 0.3901] | 0.4625 [0.4557, 0.4694] | 0.0103 [0.0080, 0.0127] | 0.0184 [0.0154, 0.0215] | 0.0385 [0.0338, 0.0430] |

## Delta against the baseline

| variant | metric | baseline | variant | delta | 95% CI | significant |
|---|---|---|---|---|---|---|
| title | auc | 0.5234 | 0.5243 | +0.0009 | [-0.0062, +0.0081] | no |
| title | mrr | 0.3456 | 0.3430 | -0.0025 | [-0.0089, +0.0036] | no |
| title | ndcg@5 | 0.3814 | 0.3819 | +0.0005 | [-0.0063, +0.0074] | no |
| title | ndcg@10 | 0.4627 | 0.4625 | -0.0002 | [-0.0062, +0.0051] | no |
| title | recall@50 | 0.0114 | 0.0103 | -0.0010 | [-0.0033, +0.0012] | no |
| title | recall@100 | 0.0217 | 0.0184 | -0.0033 | [-0.0065, -0.0001] | yes |
| title | recall@200 | 0.0434 | 0.0385 | -0.0049 | [-0.0094, -0.0002] | yes |

## Cost

Index build only. Neither knob changes query latency or index residency: the same number of distinct queries is scored against the same dense score vector either way.

| variant | articles | vocab | index build (s) | scoring (s) |
|---|---|---|---|---|
| title_abstract | 11,777 | 22,105 | 0.7 | 1.9 |
| title | 11,777 | 10,738 | 0.5 | 1.6 |
