"""Ablation grid over the re-ranker's features, with paired bootstrap CIs.

A2 Q3.3 and Q5. Each arm removes exactly one thing from the full feature set and retrains,
so the delta is attributable to that one thing. Arms that add rather than remove are stated
as such.

Every comparison is a **paired** bootstrap on shared resamples: both arms are scored on the
same resampled impressions, so their correlated errors cancel. Comparing two independent
intervals instead is far too conservative and would hide real differences.

Selection is on val. Test is reported, never chosen on.

    python -m src.rerank.ablate ebnerd_small
"""

import argparse
import json
from pathlib import Path

import numpy as np
import polars as pl

from src.features.build import features_for
from src.rerank.train import run, per_impression_auc

ROOT = Path(__file__).resolve().parent.parent.parent
PROC = ROOT / "data/processed"
RESULTS = ROOT / "results"
N_BOOT = 1000
SEED = 13


def impression_auc_vector(f: pl.DataFrame, score: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """AUC per impression, so a bootstrap can resample impressions rather than rows."""
    d = f.select(["impression_id", "label"]).with_columns(pl.Series("s", score).cast(pl.Float64))
    d = d.with_columns(pl.col("s").rank("average").over("impression_id").alias("r"))
    g = (d.group_by("impression_id", maintain_order=True)
           .agg(npos=pl.col("label").sum(), n=pl.len(), rsum=(pl.col("r") * pl.col("label")).sum())
           .with_columns(nneg=(pl.col("n") - pl.col("npos")))
           .filter((pl.col("npos") > 0) & (pl.col("nneg") > 0)))
    auc = ((g["rsum"] - g["npos"] * (g["npos"] + 1) / 2) / (g["npos"] * g["nneg"])).to_numpy()
    return g["impression_id"].to_numpy(), auc


def paired_bootstrap(a: np.ndarray, b: np.ndarray, n_boot: int = N_BOOT, seed: int = SEED):
    """95% CI on mean(a) - mean(b), resampling impressions once and scoring both arms on it."""
    rng = np.random.default_rng(seed)
    n = len(a)
    idx = rng.integers(0, n, size=(n_boot, n))
    diffs = a[idx].mean(axis=1) - b[idx].mean(axis=1)
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return float(a.mean() - b.mean()), float(lo), float(hi)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dataset", nargs="?", default="ebnerd_small")
    ap.add_argument("--split", default="val", choices=["val", "test"])
    args = ap.parse_args()
    name, split = args.dataset, args.split

    # The grid is over whatever this dataset actually supports, not the EB-NeRD ten. On MIND
    # five features have no source columns, so arms removing them would be duplicates of full.
    feature_set = features_for(name)
    arms = {"full": feature_set}
    # One arm per feature removed. Single-variable by construction.
    for f in feature_set:
        arms[f"minus_{f}"] = [x for x in feature_set if x != f]
    # Two reference points: what stage one alone could do, and the strongest single feature.
    arms["stage1_only"] = ["bm25", "emb"]
    arms["pop_only"] = ["pop_causal"]

    results, vectors = {}, {}
    for tag, feats in arms.items():
        out = run(name, feats, tag)
        results[tag] = out
        f = pl.read_parquet(PROC / name / f"rerank_{tag}_{split}.parquet").sort("impression_id")
        ids, auc = impression_auc_vector(f, f["score"].to_numpy())
        vectors[tag] = (ids, auc)

    base_ids, base_auc = vectors["full"]
    rows = []
    for tag, (ids, auc) in vectors.items():
        if tag == "full":
            continue
        assert np.array_equal(ids, base_ids), f"{tag}: impression order differs, pairing would be wrong"
        delta, lo, hi = paired_bootstrap(base_auc, auc)
        rows.append({
            "arm": tag, "auc": float(auc.mean()), "full_minus_arm": delta,
            "ci_lo": lo, "ci_hi": hi, "significant": bool(lo > 0 or hi < 0),
        })

    rows.sort(key=lambda r: -r["full_minus_arm"])
    print(f"\n{name} / {split}: full = {base_auc.mean():.4f} per-impression AUC "
          f"over {len(base_auc):,} impressions\n")
    print(f"{'arm':<22} {'AUC':>8} {'full - arm':>11} {'95% CI':>22}  sig")
    for r in rows:
        ci = f"[{r['ci_lo']:+.4f}, {r['ci_hi']:+.4f}]"
        print(f"{r['arm']:<22} {r['auc']:>8.4f} {r['full_minus_arm']:>+11.4f} {ci:>22}  "
              f"{'yes' if r['significant'] else 'no'}")

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"ablation_rerank_{name}_{split}.json").write_text(
        json.dumps({"full_auc": float(base_auc.mean()), "n_impressions": len(base_auc),
                    "arms": rows, "detail": results}, indent=2))
    print(f"\n-> results/ablation_rerank_{name}_{split}.json")


if __name__ == "__main__":
    main()
