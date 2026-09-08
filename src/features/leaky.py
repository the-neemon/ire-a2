"""The serving-unavailable arm, built only so Q9 can report what it would have bought.

A2 Q9 requires metrics with and without features unavailable at serving time. This module
is the "with" side and **nothing shipped may import it**. It is named in the allow-list of
tests/test_leakage.py::test_no_scorer_reads_a_serving_unavailable_column precisely so that
any *other* module touching these columns fails that test.

The columns are `total_inviews`, `total_pageviews` and `total_read_time` on articles.parquet.
They aggregate an article's entire lifetime, including time after any given impression, so
they cannot be computed at serving time and using them silently borrows the future. A1
measured them as worth +0.042 to +0.075 AUC, which is more than the whole semantic axis; the
point of measuring them here is to state that number honestly rather than to benefit from it.

Contrast with `pop_causal` in build.py, which counts only clicks strictly before the
impression and is legitimate.

    python -m src.features.leaky ebnerd_small --splits val test
"""

import argparse
from pathlib import Path

import numpy as np
import polars as pl

ROOT = Path(__file__).resolve().parent.parent.parent
PROC = ROOT / "data/processed"

LEAKY_FEATURES = ["leak_inviews", "leak_pageviews", "leak_readtime"]


def build(name: str, split: str) -> None:
    feats = PROC / name / f"features_{split}.parquet"
    if not feats.exists():
        print(f"  {split}: features not built, skipping")
        return
    f = pl.read_parquet(feats)
    arts = pl.read_parquet(PROC / name / "articles.parquet")

    if arts["total_inviews"].null_count() == arts.height:
        print(f"  {split}: no lifetime aggregates for this dataset, skipping")
        return

    # log1p because these are heavy-tailed counts spanning several orders of magnitude, the
    # same treatment pop_causal gets, so the comparison isolates causality and not scaling.
    lookup = arts.select(
        pl.col("article_id").alias("candidate"),
        pl.col("total_inviews").cast(pl.Float64).log1p().alias("leak_inviews"),
        pl.col("total_pageviews").cast(pl.Float64).log1p().alias("leak_pageviews"),
        pl.col("total_read_time").cast(pl.Float64).log1p().alias("leak_readtime"),
    )
    out = f.join(lookup, on="candidate", how="left").with_columns(
        [pl.col(c).fill_null(0.0).cast(pl.Float32) for c in LEAKY_FEATURES]
    )
    assert out.height == f.height, "join changed the row count; candidate ids are not unique"
    dest = PROC / name / f"features_leaky_{split}.parquet"
    out.write_parquet(dest)
    nz = int((out["leak_inviews"] > 0).sum())
    print(f"    {out.height:,} rows, {nz:,} with a lifetime count -> {dest.name}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("datasets", nargs="*", default=["ebnerd_small"])
    ap.add_argument("--splits", nargs="+", default=["train", "val", "test"])
    args = ap.parse_args()
    for name in args.datasets:
        print(f"\n{name}")
        for split in args.splits:
            build(name, split)


if __name__ == "__main__":
    main()
