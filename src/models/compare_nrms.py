"""Paired bootstrap between two NRMS runs scored on the same split.

A2 Q3. Reproducing the baseline is half the question; the other half is beating it with one
principled change, and "0.61 beats 0.60" is not an answer without an interval. Both runs score
the identical impressions, so the comparison is paired on shared resamples and their correlated
errors cancel. Comparing two independent intervals instead is far too conservative.

    python -m src.models.compare_nrms baseline.parquet variant.parquet
"""

import argparse

import numpy as np
import polars as pl

N_BOOT = 1000
SEED = 16


def impression_auc_vector(df: pl.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Per-impression AUC, and the impression ids in the same order.

    Returned as a vector rather than a mean so the bootstrap can resample impressions, which
    is the unit the metric is defined over.
    """
    ids, aucs = [], []
    for (imp,), g in df.group_by(["impression_id"], maintain_order=True):
        y = g["label"].to_numpy()
        s = g["score"].to_numpy()
        n_pos = int(y.sum())
        n_neg = len(y) - n_pos
        if n_pos == 0 or n_neg == 0:
            continue
        order = np.argsort(s, kind="stable")
        ranks = np.empty(len(s), dtype=np.float64)
        ranks[order] = np.arange(1, len(s) + 1)
        _, inv, counts = np.unique(s, return_inverse=True, return_counts=True)
        summed = np.zeros(len(counts))
        np.add.at(summed, inv, ranks)
        ranks = (summed / counts)[inv]
        ids.append(imp)
        aucs.append((ranks[y == 1].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))
    return np.asarray(ids), np.asarray(aucs)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("baseline")
    ap.add_argument("variant")
    ap.add_argument("--name-baseline", default="baseline")
    ap.add_argument("--name-variant", default="variant")
    args = ap.parse_args()

    ids_a, auc_a = impression_auc_vector(pl.read_parquet(args.baseline))
    ids_b, auc_b = impression_auc_vector(pl.read_parquet(args.variant))

    # Pairing on position would silently compare different impressions if either run dropped
    # any, so align on the id explicitly rather than trusting the order.
    if not np.array_equal(ids_a, ids_b):
        order_b = {imp: i for i, imp in enumerate(ids_b)}
        common = [imp for imp in ids_a if imp in order_b]
        if not common:
            raise SystemExit("FATAL: the two runs share no impressions")
        print(f"  aligning on {len(common):,} shared impressions "
              f"({len(ids_a):,} and {len(ids_b):,} scored)")
        idx_a = {imp: i for i, imp in enumerate(ids_a)}
        auc_a = auc_a[[idx_a[i] for i in common]]
        auc_b = auc_b[[order_b[i] for i in common]]

    n = len(auc_a)
    delta = float(auc_b.mean() - auc_a.mean())
    rng = np.random.default_rng(SEED)
    boots = np.empty(N_BOOT)
    for i in range(N_BOOT):
        pick = rng.integers(0, n, n)          # one resample, both arms, so errors cancel
        boots[i] = auc_b[pick].mean() - auc_a[pick].mean()
    lo, hi = np.percentile(boots, [2.5, 97.5])

    print(f"\n{args.name_baseline:28s} {auc_a.mean():.4f}")
    print(f"{args.name_variant:28s} {auc_b.mean():.4f}")
    print(f"{'difference':28s} {delta:+.4f}  95% CI [{lo:+.4f}, {hi:+.4f}]  "
          f"{'significant' if lo > 0 or hi < 0 else 'not significant'}")
    print(f"\nover {n:,} paired impressions, {N_BOOT} bootstrap resamples, seed {SEED}")


if __name__ == "__main__":
    main()
