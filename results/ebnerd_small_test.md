# ebnerd_small — test

244,647 impressions, 244,647 scored (the rest are all-clicked or none-clicked and carry no ranking signal).

## Accuracy (mean [95% bootstrap CI])

| system | AUC | MRR (first click) | MRR (all clicks) | nDCG@5 | nDCG@10 |
|---|---|---|---|---|---|
| bm25 | 0.5107 [0.5094, 0.5120] | 0.3257 [0.3245, 0.3269] | 0.3253 [0.3241, 0.3264] | 0.3577 [0.3563, 0.3591] | 0.4409 [0.4397, 0.4420] |
| emb | 0.5397 [0.5384, 0.5409] | 0.3492 [0.3480, 0.3503] | 0.3487 [0.3475, 0.3498] | 0.3831 [0.3818, 0.3845] | 0.4627 [0.4616, 0.4638] |
| fused | 0.5380 [0.5367, 0.5392] | 0.3474 [0.3463, 0.3486] | 0.3470 [0.3458, 0.3481] | 0.3813 [0.3800, 0.3827] | 0.4613 [0.4602, 0.4624] |
| rerank | 0.7908 [0.7898, 0.7918] | 0.5685 [0.5671, 0.5699] | 0.5678 [0.5665, 0.5693] | 0.6330 [0.6318, 0.6344] | 0.6650 [0.6639, 0.6662] |
| fused+popularity | 0.5797 [0.5785, 0.5810] | 0.3688 [0.3677, 0.3700] | 0.3684 [0.3672, 0.3696] | 0.4101 [0.4088, 0.4115] | 0.4841 [0.4830, 0.4852] |

## Beyond accuracy (top-10)

| system | diversity | novelty | coverage |
|---|---|---|---|
| bm25 | 0.7968 [0.7961, 0.7974] | 16.9664 [16.9636, 16.9688] | 0.2067 [0.1875, 0.1920] |
| emb | 0.7803 [0.7796, 0.7809] | 17.0072 [17.0044, 17.0096] | 0.2050 [0.1859, 0.1903] |
| fused | 0.7820 [0.7814, 0.7826] | 16.9992 [16.9964, 17.0015] | 0.2051 [0.1860, 0.1902] |
| rerank | 0.7901 [0.7895, 0.7907] | 17.0841 [17.0815, 17.0865] | 0.2026 [0.1830, 0.1876] |
| fused+popularity | 0.7882 [0.7876, 0.7888] | 17.0144 [17.0116, 17.0170] | 0.1975 [0.1790, 0.1832] |

## AUC by slice

cold = history length <= 34; head = clicked article with >= 349 train clicks

| slice | n | bm25 | emb | fused | rerank | fused+popularity |
|---|---|---|---|---|---|---|
| cold | 25,105 | 0.5103 [0.5064, 0.5140] | 0.5481 [0.5438, 0.5522] | 0.5449 [0.5407, 0.5488] | 0.7910 [0.7879, 0.7942] | 0.5906 [0.5865, 0.5945] |
| warm | 219,542 | 0.5108 [0.5093, 0.5122] | 0.5387 [0.5373, 0.5402] | 0.5372 [0.5358, 0.5386] | 0.7908 [0.7897, 0.7917] | 0.5785 [0.5771, 0.5798] |
| head | 803 | 0.5852 [0.5651, 0.6072] | 0.6191 [0.5971, 0.6395] | 0.6353 [0.6143, 0.6574] | 0.5530 [0.5316, 0.5728] | 0.6921 [0.6700, 0.7129] |
| tail | 243,844 | 0.5105 [0.5091, 0.5117] | 0.5394 [0.5381, 0.5407] | 0.5377 [0.5364, 0.5390] | 0.7916 [0.7906, 0.7925] | 0.5793 [0.5781, 0.5806] |

## Candidate generation — recall@K (full-corpus retrieval)

Share of an impression's clicked articles found in the top K drawn from the whole catalogue, not the pool the log showed. Cold-start impressions retrieve nothing and score 0 rather than being excluded.

| system | recall@50 | recall@100 | recall@200 |
|---|---|---|---|
| bm25 | 0.0072 [0.0068, 0.0075] | 0.0133 [0.0129, 0.0138] | 0.0247 [0.0241, 0.0253] |
| emb | 0.0073 [0.0070, 0.0076] | 0.0144 [0.0139, 0.0148] | 0.0277 [0.0270, 0.0283] |

### recall@200 by slice

Which retriever wins is not the same on every slice — see `emb - bm25`, paired within the slice.

| slice | n | bm25 | emb | emb - bm25 | significant |
|---|---|---|---|---|---|
| cold | 25,105 | 0.0257 [0.0237, 0.0276] | 0.0292 [0.0269, 0.0313] | +0.0035 [+0.0010, +0.0062] | yes |
| warm | 219,542 | 0.0245 [0.0239, 0.0252] | 0.0275 [0.0268, 0.0282] | +0.0030 [+0.0020, +0.0039] | yes |
| head | 803 | 0.0791 [0.0604, 0.0984] | 0.0461 [0.0324, 0.0598] | -0.0330 [-0.0535, -0.0112] | yes |
| tail | 243,844 | 0.0245 [0.0239, 0.0251] | 0.0276 [0.0270, 0.0283] | +0.0031 [+0.0023, +0.0040] | yes |

## Paired bootstrap comparisons

A difference counts only if its 95% CI excludes zero.

| comparison | difference | significant |
|---|---|---|
| emb - bm25 (auc) | +0.0289 [+0.0272, +0.0307] | yes |
| emb - bm25 (ndcg@10) | +0.0218 [+0.0205, +0.0231] | yes |
| fused - emb (auc) | -0.0017 [-0.0023, -0.0010] | yes |
| fused - emb (ndcg@10) | -0.0014 [-0.0021, -0.0008] | yes |
| fused - bm25 (auc) | +0.0273 [+0.0259, +0.0287] | yes |
| fused - bm25 (ndcg@10) | +0.0204 [+0.0193, +0.0214] | yes |
| rerank - bm25 (auc) | +0.2801 [+0.2786, +0.2816] | yes |
| rerank - bm25 (ndcg@10) | +0.2241 [+0.2228, +0.2254] | yes |
| rerank - emb (auc) | +0.2511 [+0.2496, +0.2527] | yes |
| rerank - emb (ndcg@10) | +0.2023 [+0.2010, +0.2037] | yes |
| rerank - fused (auc) | +0.2528 [+0.2514, +0.2543] | yes |
| rerank - fused (ndcg@10) | +0.2037 [+0.2025, +0.2051] | yes |
| fused+popularity - fused (auc) | +0.0417 [+0.0408, +0.0426] | yes |
| fused+popularity - fused (ndcg@10) | +0.0228 [+0.0221, +0.0236] | yes |
| emb - bm25 (recall@50) | +0.0001 [-0.0003, +0.0006] | no |
| emb - bm25 (recall@100) | +0.0011 [+0.0005, +0.0017] | yes |
| emb - bm25 (recall@200) | +0.0030 [+0.0022, +0.0038] | yes |

## Serving-availability

`fused+popularity` adds article lifetime popularity (`total_inviews`), a corpus-wide aggregate that embeds the future and is unavailable at serving time. Every other row uses only features computable strictly before the impression. The paired comparison `fused+popularity - fused` above is the cost of honesty.
