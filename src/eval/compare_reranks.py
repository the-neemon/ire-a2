"""Paired comparison of two trained re-rankers on identical impressions.

`src.rerank.train --tag <tag>` writes one flat table per split,

    data/processed/<dataset>/rerank_<tag>_<split>.parquet
        impression_id | candidate | label | score

and this answers "is model B better than model A, and by how much", with the paired bootstrap
95% CI the ledger requires. It exists because the incremental steps of the feature set (10
features, then 17, then 22 with exposure) were each recorded as a point difference in AUC
without an interval, and a claimed gain without an interval is not a result.

Both models must score the same candidates of the same impressions. That is asserted rather
than assumed: the two tables are joined on (impression_id, candidate), the row counts and labels
must agree exactly, and the per-impression vectors are aligned on impression_id, never on row
order.

    python -m src.eval.compare_reranks ebnerd_small ladder10 ladder17
    python -m src.eval.compare_reranks ebnerd_small ladder17 final --splits val test

Writes results/compare_<dataset>_<a>_vs_<b>.json, reporting b - a.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import polars as pl

from src.eval import bootstrap

ROOT = Path(__file__).resolve().parent.parent.parent
PROC = ROOT / "data/processed"
RESULTS = ROOT / "results"


def per_impression_auc(flat: pl.DataFrame, score: str) -> pl.DataFrame:
    """Mann-Whitney AUC inside each impression, ties averaged, for impressions with both classes."""
    ranked = flat.with_columns(
        pl.col(score).rank("average").over("impression_id").alias("_r")
    )
    per = (
        ranked.group_by("impression_id")
        .agg(
            npos=pl.col("label").sum(),
            n=pl.len(),
            rsum=(pl.col("_r") * pl.col("label")).sum(),
        )
        .with_columns(nneg=pl.col("n") - pl.col("npos"))
        .filter((pl.col("npos") > 0) & (pl.col("nneg") > 0))
    )
    return per.select(
        "impression_id",
        ((pl.col("rsum") - pl.col("npos") * (pl.col("npos") + 1) / 2)
         / (pl.col("npos") * pl.col("nneg"))).alias(score),
    )


def compare(dataset: str, a: str, b: str, split: str) -> dict:
    ta = pl.read_parquet(PROC / dataset / f"rerank_{a}_{split}.parquet")
    tb = pl.read_parquet(PROC / dataset / f"rerank_{b}_{split}.parquet")
    assert ta.height == tb.height, f"{a} has {ta.height:,} rows, {b} has {tb.height:,}"

    joined = ta.select("impression_id", "candidate", "label", pl.col("score").alias("score_a")).join(
        tb.select("impression_id", "candidate", pl.col("label").alias("label_b"),
                  pl.col("score").alias("score_b")),
        on=["impression_id", "candidate"], how="inner",
    )
    assert joined.height == ta.height, (
        f"only {joined.height:,} of {ta.height:,} (impression, candidate) rows matched; "
        "the two models did not score the same candidates"
    )
    assert (joined["label"] == joined["label_b"]).all(), "labels disagree between the two tables"

    auc_a = per_impression_auc(joined.rename({"score_a": "a"}), "a")
    auc_b = per_impression_auc(joined.rename({"score_b": "b"}), "b")
    aligned = auc_a.join(auc_b, on="impression_id", how="inner").sort("impression_id")
    assert aligned.height == auc_a.height == auc_b.height, "impression sets differ after filtering"

    va, vb = aligned["a"].to_numpy(), aligned["b"].to_numpy()
    mean, lo, hi, sig = bootstrap.paired(vb, va)
    return {
        "dataset": dataset, "split": split, "a": a, "b": b,
        "n_impressions": int(aligned.height),
        "auc_a": float(va.mean()), "auc_b": float(vb.mean()),
        "b_minus_a": mean, "ci_lo": lo, "ci_hi": hi, "significant": sig,
        "resamples": bootstrap.RESAMPLES, "seed": bootstrap.SEED,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dataset")
    ap.add_argument("a", help="baseline tag")
    ap.add_argument("b", help="variant tag; the report is b - a")
    ap.add_argument("--splits", nargs="+", default=["val", "test"])
    args = ap.parse_args()

    out = {split: compare(args.dataset, args.a, args.b, split) for split in args.splits}
    for split, r in out.items():
        print(f"{args.dataset} {split}: {args.a} {r['auc_a']:.4f} -> {args.b} {r['auc_b']:.4f}  "
              f"{r['b_minus_a']:+.4f} [{r['ci_lo']:+.4f}, {r['ci_hi']:+.4f}]  "
              f"n={r['n_impressions']:,}  {'significant' if r['significant'] else 'not significant'}")
    RESULTS.mkdir(exist_ok=True)
    dest = RESULTS / f"compare_{args.dataset}_{args.a}_vs_{args.b}.json"
    dest.write_text(json.dumps(out, indent=2))
    print(f"  -> {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
