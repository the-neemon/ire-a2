# System design: the two-stage architecture

*Owner: Naman. Stage one in `src/retrieval/`, stage two in `src/rerank/`. Numbers trace to
`docs/FACTS.md` and `docs/ABLATIONS.md`.*

## Shape

Retrieve a few hundred candidates cheaply, then spend real computation only on those.

```
impression (user history, timestamp)
        |
  +-----+-----------------------------+
  |                                   |
BM25 over history text        embedding kNN, IndexFlatIP
  |                                   |
  +-----------> fuse <----------------+
                 |     z-normalised within each pool,
                 |     score = alpha*emb_z + (1-alpha)*bm25_z
                 |
          TOP_K = 200 candidates
                 |
        LightGBM lambdarank over 10 features
                 |
           ranked candidates
```

Both stages are trained and selected on **val**, and test is scored once. Splits are temporal,
never random: train precedes val precedes test, asserted in `split.py` rather than assumed.

## Why two stages

The brief asks for a few hundred candidates, and the shape falls out of the cost asymmetry.
Stage one touches the whole corpus and must stay cheap per article. Stage two touches 200
candidates and can afford per-candidate features that would be impossible corpus-wide.

The measured payoff is large: the re-ranker beats the fused retriever by **+0.2049 test AUC
[+0.2034, +0.2064]**. That gap is the central quantitative result of the assignment, and it is
about four times the size of the leak the Q9 arm declines to take, which is why honesty costs
effectively nothing here.

## Stage one

`TOP_K = 200`, with `OVERFETCH = 3` so the publication-date filter still leaves 200 after it
thins the pool. Two retrievers:

- **BM25** over the user's history text. Danish stemming is on for EB-NeRD, kept on cost rather
  than quality grounds: it moves no ranking metric on either split, but cuts the vocabulary from
  43,451 to 30,388 terms and val scoring from 23.6 s to 19.2 s.
- **Embedding kNN**, `IndexFlatIP` over L2-normalised document vectors, so the inner product is
  a cosine and search is exact.

Fusion z-normalises **within each candidate pool** rather than globally, because BM25 and cosine
have different scales and BM25's depends on query length. `alpha` is swept over 21 grid points on
val and applied unchanged to test.

Fusion's own contribution is small and does not generalise: **+0.0022 val, -0.0017 test**, both
significant, a clean sign flip across the split boundary. That is an honest negative result and
it is reported rather than buried. It is also moot next to stage two, which is worth a hundred
times more.

## Stage two

LightGBM `lambdarank`, chosen over binary classification because the objective should match the
task: the metric is a ranking inside an impression, not a global click probability. Rows stay
grouped by impression, since lambdarank ranks within a group.

`learning_rate` 0.05, `num_leaves` 31, `min_data_in_leaf` 50, `feature_fraction` and
`bagging_fraction` 0.9, up to 400 rounds with early stopping at 40 on val nDCG.

Ten features, of which five exist only on EB-NeRD. See `q1-features-and-availability.md`; the
per-dataset split is explicit in `DATASET_FEATURES` rather than left to whatever the columns
happen to contain.

## What the architecture assumes, and where that is fragile

- **Recall is a ceiling.** Stage two can only reorder what stage one returned, so any relevant
  article outside the 200 is unrecoverable. This is why ablation #7 is shipped-pending: it gains
  ranking AUC while costing recall@200, and the recall is what stage two consumes.
- **Stage one dominates at scale.** The Q4 bench found the ANN is what breaks first at a 10x
  corpus, growing 19.4x where exact search should be at worst linear, because 60.8 MiB of vectors
  stops fitting in cache. Every Python-side stage is flat in corpus size. Making the re-ranker
  cheaper therefore buys nothing at scale, which overturns the A1 conclusion that the
  per-impression loop was the bottleneck.
- **The behavioural axis is EB-NeRD-specific.** Half the features do not exist on MIND, so the
  same architecture is expected to be worth substantially less there.
