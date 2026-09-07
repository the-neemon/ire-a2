"""Q9: the same ranker with and without features unavailable at serving time.

The brief requires reporting both. The honest system uses `pop_causal`, which counts only
clicks strictly before the impression. The leaky arm adds the article lifetime aggregates,
which include the future relative to any impression and cannot exist at serving time.

The gap between the two is the number to state plainly: it is what we are declining to take.

    python -m src.rerank.q9 ebnerd_small
"""

import argparse
import json
from pathlib import Path

import numpy as np
import polars as pl

from src.features.build import FEATURES
from src.features.leaky import LEAKY_FEATURES
from src.rerank.train import run
from src.rerank.ablate import impression_auc_vector, paired_bootstrap

ROOT = Path(__file__).resolve().parent.parent.parent
PROC = ROOT / "data/processed"
RESULTS = ROOT / "results"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dataset", nargs="?", default="ebnerd_small")
    ap.add_argument("--split", default="val", choices=["val", "test"])
    args = ap.parse_args()
    name, split = args.dataset, args.split

    # Both arms read the leaky file so the rows and their order are identical; the only
    # difference is which columns the model is allowed to see. Reading different files would
    # risk a different row order and silently break the pairing.
    arms = {
        "q9_causal": FEATURES,
        "q9_leaky": FEATURES + LEAKY_FEATURES,
    }
    vecs = {}
    for tag, feats in arms.items():
        run(name, feats, tag, source="features_leaky")
        f = pl.read_parquet(PROC / name / f"rerank_{tag}_{split}.parquet").sort("impression_id")
        vecs[tag] = impression_auc_vector(f, f["score"].to_numpy())

    (ids_c, auc_c), (ids_l, auc_l) = vecs["q9_causal"], vecs["q9_leaky"]
    assert np.array_equal(ids_c, ids_l), "impression order differs; the pairing would be wrong"
    delta, lo, hi = paired_bootstrap(auc_l, auc_c)

    print(f"\n{name} / {split}: what the serving-unavailable features would buy\n")
    print(f"  causal only (shipped)     {auc_c.mean():.4f}")
    print(f"  + lifetime aggregates     {auc_l.mean():.4f}")
    print(f"  difference                {delta:+.4f}  95% CI [{lo:+.4f}, {hi:+.4f}]"
          f"  {'significant' if lo > 0 or hi < 0 else 'not significant'}")
    print(f"\n  over {len(auc_c):,} impressions. The shipped scorer reads none of these columns.")

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"q9_{name}_{split}.json").write_text(json.dumps({
        "causal_auc": float(auc_c.mean()), "leaky_auc": float(auc_l.mean()),
        "delta": delta, "ci_lo": lo, "ci_hi": hi, "n_impressions": len(auc_c),
        "leaky_features": LEAKY_FEATURES,
    }, indent=2))


if __name__ == "__main__":
    main()
