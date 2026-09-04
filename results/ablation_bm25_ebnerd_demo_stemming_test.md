# BM25 ablation — ebnerd_demo / test

25,356 impressions scored (all-clicked and none-clicked pools carry no ranking signal and are dropped by the harness).

Baseline: **stem**. Every delta below is paired on the same impressions and the same 1,000 bootstrap resamples, so a difference counts only if its 95% CI excludes zero.

## Absolute

| variant | auc | mrr | ndcg@5 | ndcg@10 | recall@50 | recall@100 | recall@200 |
|---|---|---|---|---|---|---|---|
| stem | 0.5125 [0.5088, 0.5166] | 0.3273 [0.3241, 0.3308] | 0.3591 [0.3551, 0.3632] | 0.4418 [0.4387, 0.4453] | 0.0108 [0.0095, 0.0122] | 0.0216 [0.0199, 0.0234] | 0.0390 [0.0368, 0.0413] |
| no_stem | 0.5128 [0.5089, 0.5169] | 0.3273 [0.3240, 0.3311] | 0.3581 [0.3539, 0.3624] | 0.4420 [0.4387, 0.4455] | 0.0105 [0.0092, 0.0118] | 0.0200 [0.0184, 0.0217] | 0.0376 [0.0354, 0.0399] |

## Delta against the baseline

| variant | metric | baseline | variant | delta | 95% CI | significant |
|---|---|---|---|---|---|---|
| no_stem | auc | 0.5125 | 0.5128 | +0.0003 | [-0.0025, +0.0029] | no |
| no_stem | mrr | 0.3273 | 0.3273 | -0.0000 | [-0.0025, +0.0025] | no |
| no_stem | ndcg@5 | 0.3591 | 0.3581 | -0.0010 | [-0.0037, +0.0016] | no |
| no_stem | ndcg@10 | 0.4418 | 0.4420 | +0.0002 | [-0.0020, +0.0024] | no |
| no_stem | recall@50 | 0.0108 | 0.0105 | -0.0004 | [-0.0014, +0.0006] | no |
| no_stem | recall@100 | 0.0216 | 0.0200 | -0.0016 | [-0.0031, -0.0002] | yes |
| no_stem | recall@200 | 0.0390 | 0.0376 | -0.0014 | [-0.0037, +0.0004] | no |

## Cost

Index build only. Neither knob changes query latency or index residency: the same number of distinct queries is scored against the same dense score vector either way.

| variant | articles | vocab | index build (s) | scoring (s) |
|---|---|---|---|---|
| stem | 11,777 | 22,105 | 0.9 | 3.5 |
| no_stem | 11,777 | 31,515 | 0.6 | 3.3 |
