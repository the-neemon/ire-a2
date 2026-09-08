# BM25 ablation — ebnerd_small / val

64,365 impressions scored (all-clicked and none-clicked pools carry no ranking signal and are dropped by the harness).

Baseline: **title_abstract**. Every delta below is paired on the same impressions and the same 1,000 bootstrap resamples, so a difference counts only if its 95% CI excludes zero.

## Absolute

| variant | auc | mrr | ndcg@5 | ndcg@10 | recall@50 | recall@100 | recall@200 |
|---|---|---|---|---|---|---|---|
| title_abstract | 0.5205 [0.5177, 0.5230] | 0.3418 [0.3393, 0.3443] | 0.3794 [0.3766, 0.3823] | 0.4607 [0.4585, 0.4630] | 0.0052 [0.0047, 0.0058] | 0.0110 [0.0101, 0.0118] | 0.0214 [0.0202, 0.0225] |
| title | 0.5229 [0.5203, 0.5253] | 0.3437 [0.3413, 0.3459] | 0.3820 [0.3795, 0.3844] | 0.4628 [0.4607, 0.4649] | 0.0049 [0.0044, 0.0054] | 0.0098 [0.0091, 0.0105] | 0.0190 [0.0179, 0.0200] |

## Delta against the baseline

| variant | metric | baseline | variant | delta | 95% CI | significant |
|---|---|---|---|---|---|---|
| title | auc | 0.5205 | 0.5229 | +0.0025 | [+0.0002, +0.0047] | yes |
| title | mrr | 0.3418 | 0.3437 | +0.0019 | [-0.0001, +0.0039] | no |
| title | ndcg@5 | 0.3794 | 0.3820 | +0.0025 | [+0.0003, +0.0048] | yes |
| title | ndcg@10 | 0.4607 | 0.4628 | +0.0021 | [+0.0004, +0.0039] | yes |
| title | recall@50 | 0.0052 | 0.0049 | -0.0003 | [-0.0009, +0.0002] | no |
| title | recall@100 | 0.0110 | 0.0098 | -0.0012 | [-0.0019, -0.0004] | yes |
| title | recall@200 | 0.0214 | 0.0190 | -0.0024 | [-0.0035, -0.0013] | yes |

## Cost

Index build only. Neither knob changes query latency or index residency: the same number of distinct queries is scored against the same dense score vector either way.

| variant | articles | vocab | index build (s) | scoring (s) |
|---|---|---|---|---|
| title_abstract | 20,738 | 30,388 | 1.0 | 13.9 |
| title | 20,738 | 15,132 | 0.6 | 13.3 |
