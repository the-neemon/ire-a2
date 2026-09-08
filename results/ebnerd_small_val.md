# ebnerd_small — val

64,365 impressions, 64,365 scored (the rest are all-clicked or none-clicked and carry no ranking signal).

## Accuracy (mean [95% bootstrap CI])

| system | AUC | MRR | nDCG@5 | nDCG@10 |
|---|---|---|---|---|
| bm25 | 0.5205 [0.5180, 0.5231] | 0.3418 [0.3395, 0.3440] | 0.3794 [0.3767, 0.3821] | 0.4607 [0.4586, 0.4629] |
| emb | 0.5506 [0.5482, 0.5530] | 0.3594 [0.3572, 0.3617] | 0.4017 [0.3991, 0.4044] | 0.4778 [0.4757, 0.4801] |
| fused | 0.5528 [0.5503, 0.5553] | 0.3628 [0.3604, 0.3652] | 0.4043 [0.4016, 0.4071] | 0.4807 [0.4785, 0.4830] |
| rerank | 0.7575 [0.7555, 0.7594] | 0.5319 [0.5291, 0.5344] | 0.5967 [0.5941, 0.5993] | 0.6341 [0.6318, 0.6361] |
| fused+popularity | 0.5784 [0.5760, 0.5808] | 0.3707 [0.3684, 0.3731] | 0.4184 [0.4159, 0.4210] | 0.4910 [0.4889, 0.4932] |

## Beyond accuracy (top-10)

| system | diversity | novelty | coverage |
|---|---|---|---|
| bm25 | 0.8039 | 16.3525 | 0.1142 |
| emb | 0.7906 | 16.3992 | 0.1130 |
| fused | 0.7916 | 16.3909 | 0.1131 |
| rerank | 0.8006 | 16.4824 | 0.1030 |
| fused+popularity | 0.7963 | 16.3572 | 0.1099 |

## AUC by slice

cold = history length <= 42; head = clicked article with >= 379 train clicks

| slice | n | bm25 | emb | fused | rerank | fused+popularity |
|---|---|---|---|---|---|---|
| cold | 6,463 | 0.5281 [0.5201, 0.5362] | 0.5567 [0.5491, 0.5645] | 0.5612 [0.5535, 0.5690] | 0.7836 [0.7777, 0.7898] | 0.5843 [0.5771, 0.5920] |
| warm | 57,902 | 0.5196 [0.5170, 0.5222] | 0.5499 [0.5472, 0.5526] | 0.5518 [0.5491, 0.5547] | 0.7545 [0.7525, 0.7565] | 0.5778 [0.5751, 0.5805] |
| head | 1,094 | 0.5091 [0.4912, 0.5278] | 0.6855 [0.6684, 0.7027] | 0.6638 [0.6467, 0.6800] | 0.7046 [0.6867, 0.7230] | 0.7192 [0.7048, 0.7341] |
| tail | 63,271 | 0.5207 [0.5181, 0.5234] | 0.5483 [0.5459, 0.5507] | 0.5509 [0.5485, 0.5534] | 0.7584 [0.7565, 0.7604] | 0.5760 [0.5737, 0.5783] |

## Candidate generation — recall@K (full-corpus retrieval)

Share of an impression's clicked articles found in the top K drawn from the whole catalogue, not the pool the log showed. Cold-start impressions retrieve nothing and score 0 rather than being excluded.

| system | recall@50 | recall@100 | recall@200 |
|---|---|---|---|
| bm25 | 0.0052 [0.0047, 0.0058] | 0.0110 [0.0102, 0.0118] | 0.0214 [0.0202, 0.0226] |
| emb | 0.0045 [0.0040, 0.0051] | 0.0097 [0.0090, 0.0105] | 0.0198 [0.0187, 0.0209] |

### recall@200 by slice

Which retriever wins is not the same on every slice — see `emb - bm25`, paired within the slice.

| slice | n | bm25 | emb | emb - bm25 | significant |
|---|---|---|---|---|---|
| cold | 6,463 | 0.0284 [0.0243, 0.0326] | 0.0256 [0.0218, 0.0292] | -0.0028 [-0.0083, +0.0024] | no |
| warm | 57,902 | 0.0206 [0.0195, 0.0218] | 0.0191 [0.0181, 0.0202] | -0.0015 [-0.0031, +0.0001] | no |
| head | 1,094 | 0.0229 [0.0146, 0.0320] | 0.0311 [0.0219, 0.0421] | +0.0082 [-0.0037, +0.0210] | no |
| tail | 63,271 | 0.0214 [0.0203, 0.0225] | 0.0196 [0.0185, 0.0207] | -0.0018 [-0.0033, -0.0004] | yes |

## Paired bootstrap comparisons

A difference counts only if its 95% CI excludes zero.

| comparison | difference | significant |
|---|---|---|
| emb - bm25 (auc) | +0.0301 [+0.0269, +0.0335] | yes |
| emb - bm25 (ndcg@10) | +0.0171 [+0.0148, +0.0196] | yes |
| fused - emb (auc) | +0.0022 [+0.0010, +0.0034] | yes |
| fused - emb (ndcg@10) | +0.0029 [+0.0017, +0.0042] | yes |
| fused - bm25 (auc) | +0.0323 [+0.0296, +0.0351] | yes |
| fused - bm25 (ndcg@10) | +0.0200 [+0.0181, +0.0220] | yes |
| rerank - bm25 (auc) | +0.2370 [+0.2339, +0.2402] | yes |
| rerank - bm25 (ndcg@10) | +0.1734 [+0.1707, +0.1760] | yes |
| rerank - emb (auc) | +0.2068 [+0.2039, +0.2095] | yes |
| rerank - emb (ndcg@10) | +0.1562 [+0.1538, +0.1587] | yes |
| rerank - fused (auc) | +0.2047 [+0.2018, +0.2076] | yes |
| rerank - fused (ndcg@10) | +0.1534 [+0.1509, +0.1558] | yes |
| fused+popularity - fused (auc) | +0.0257 [+0.0239, +0.0273] | yes |
| fused+popularity - fused (ndcg@10) | +0.0103 [+0.0088, +0.0117] | yes |
| emb - bm25 (recall@50) | -0.0008 [-0.0015, -0.0000] | yes |
| emb - bm25 (recall@100) | -0.0013 [-0.0023, -0.0002] | yes |
| emb - bm25 (recall@200) | -0.0016 [-0.0031, -0.0002] | yes |

## Serving-availability

`fused+popularity` adds article lifetime popularity (`total_inviews`), a corpus-wide aggregate that embeds the future and is unavailable at serving time. Every other row uses only features computable strictly before the impression. The paired comparison `fused+popularity - fused` above is the cost of honesty.
