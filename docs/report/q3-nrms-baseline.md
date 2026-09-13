# Q3: the NRMS baseline, reproduced and beaten

*Owner: Naman. Driver `src/models/nrms_oursplit.py`, comparison `src/models/compare_nrms.py`.
Machine: cluster, one u22 node, 16 CPU cores, no GPU. Ledger rows in `docs/FACTS.md` section 14.*

## Reproduction

`ebnerd_nrms_docvec.py` from the EB-NeRD benchmark, run unmodified: `ebnerd_small`,
contrastive_vector document embeddings, history_size 20, title_size 768, npratio 4, batch 32,
seed 16.

| | |
|---|---|
| best val AUC | **0.6484** |
| best epoch | 3 of 10, early-stopped at 7, patience 4 |
| wall time | 54 min 11 s |

TensorFlow is CPU-only here, which is not a limitation at this scale: a full epoch is about 17
minutes on the benchmark's own data volume.

**This number is not comparable to our re-ranker.** The benchmark concatenates the provided
`train` and `validation` blocks, trains on both, then carves its own validation from the last day
of that pool. Against our temporal split that means it trains on our train, our val **and** our
test, and early-stops on a slice of its own training window. It reproduces their setup faithfully,
which is what the first half of Q3 asks, and it answers nothing about relative quality.

## The comparable run

`src/models/nrms_oursplit.py` drives the same model, hyperparameters, document vectors and
dataloader from our `impressions_{train,val,test}.parquet`: trains on our train, early-stops on
our val, scores our test exactly once. Output is written in the re-ranker's flat schema
(`impression_id | candidate | label | score`) so `src.eval.run` reads both identically.

| system | val | test |
|---|---|---|
| stage one (fused retrieval) | 0.5498 | 0.5430 |
| **NRMS baseline** | **0.5969** | **0.5938** |
| our two-stage re-ranker | **0.7489** | **0.7461** |

NRMS beats stage one by about +0.05, and our re-ranker beats NRMS by about **+0.15** on both
splits. A neural news recommender trained end to end on the same data does not reach a
gradient-boosted ranker over ten cheap behavioural features.

## The one principled change

**History size 20 to 50**, one variable, nothing else touched.

The motivation is our own measurement rather than a guess. The history sweep
(`FACTS.md` 15.3) found that the embedding user vector improves **monotonically** with history
length up to N=100 on clean history, reversing the A1 claim that more history makes the profile
worse. NRMS builds its user representation by self-attention over exactly that history, so if
more history helps the pooled vector it should help the attention too.

| | val | test |
|---|---|---|
| NRMS `history_size=20` | 0.5969 | 0.5938 |
| NRMS `history_size=50` | **0.6042** | **0.6032** |
| **difference** | **+0.0072 [+0.0058, +0.0088]** | **+0.0094 [+0.0086, +0.0102]** |

Paired bootstrap, 1,000 resamples, seed 16, over all 64,365 val and 244,647 test impressions.
Both arms score the identical impressions, so the resample is shared and their correlated errors
cancel. **Significant on both splits, and the effect is larger on test than val**, which is the
opposite of an overfit-to-val result.

We stopped at 50 rather than 100. NRMS self-attends over the history, so cost grows quadratically
in that length where the pooled vector's does not, and 50 already captures most of the sweep's
gain. Pushing to 100 is a stated open question, not a result.

## Guards worth recording

Two failure modes here return a plausible number instead of an error, so both are asserted rather
than assumed.

**Article-id coverage.** Our pipeline carries article ids as strings; the document-vector parquet
keys them as `Int32`; the dataloader's `unknown_representation="zeros"` turns every miss into a
zero vector. A dtype mismatch would train on noise and report a believable AUC. The driver
asserts coverage and fails below 95%. Measured **1.0000 on all four checks** (train and val,
candidates and history), and 4,597 distinct history ids at history_size 50 against 3,582 at 20,
confirming the longer history actually reaches the model.

**Score alignment.** Per-impression score lists are asserted to match candidate-list length before
the flat explode, and the label join is asserted to leave no nulls. The paired comparison aligns
on impression id explicitly rather than on row order, and requires the two runs to share their
impression set.

The smoke pass is why these exist: at 2% of train for one epoch it returned **0.5013**, which is
chance. Rather than accept or dismiss it, we checked whether the scores were degenerate: 508,192
distinct values over 703,229 rows, no impression with constant scores. The plumbing was sound and
the model was simply undertrained, which is what a smoke test is for.
