"""Stage two: a LightGBM lambdarank re-ranker over the behavioural features.

A2 Q2 Option A. Stage one (BM25 + embeddings) narrows the corpus to a candidate pool;
this orders that pool using features stage one cannot see, chiefly causally-valid
popularity, freshness and engagement-weighted similarity.

lambdarank rather than binary classification because the objective should match the
metric: it weights each candidate pair by how much swapping them would move nDCG, so the
model spends its capacity at the top of the list where the metric is decided.

Selection happens on val. Test is scored once, at the end, and never chosen on.

    python -m src.rerank.train ebnerd_small
    python -m src.rerank.train ebnerd_small --features bm25 emb   # ablation arm
"""

import argparse
import json
from pathlib import Path

import lightgbm as lgb
import numpy as np
import polars as pl

from src.features.build import FEATURES

ROOT = Path(__file__).resolve().parent.parent.parent
PROC = ROOT / "data/processed"
RESULTS = ROOT / "results"

PARAMS = {
    "objective": "lambdarank",
    "metric": "ndcg",
    "ndcg_eval_at": [5, 10],
    "learning_rate": 0.05,
    "num_leaves": 31,
    "min_data_in_leaf": 50,
    "feature_fraction": 0.9,
    "bagging_fraction": 0.9,
    "bagging_freq": 1,
    "verbosity": -1,
    "seed": 13,
}
NUM_ROUNDS = 400
EARLY_STOPPING = 40


def load(name: str, split: str, features: list[str]):
    """Rows must stay grouped by impression: lambdarank ranks within a group, not globally."""
    f = pl.read_parquet(PROC / name / f"features_{split}.parquet").sort("impression_id")
    groups = f.group_by("impression_id", maintain_order=True).len()["len"].to_numpy()
    X = f.select(features).to_numpy().astype(np.float32)
    y = f["label"].to_numpy().astype(np.int8)
    return f, X, y, groups


def per_impression_auc(f: pl.DataFrame, score: np.ndarray) -> float:
    """Mann-Whitney AUC averaged over impressions that contain both classes.

    Per impression, not pooled. A feature that is constant within an impression cannot
    reorder it and must score exactly 0.5; pooling hides that by rewarding variation
    across impressions, which is not what the ranking is judged on.
    """
    d = f.select(["impression_id", "label"]).with_columns(pl.Series("s", score).cast(pl.Float64))
    d = d.with_columns(pl.col("s").rank("average").over("impression_id").alias("r"))
    g = (d.group_by("impression_id")
           .agg(npos=pl.col("label").sum(), n=pl.len(), rsum=(pl.col("r") * pl.col("label")).sum())
           .with_columns(nneg=(pl.col("n") - pl.col("npos")))
           .filter((pl.col("npos") > 0) & (pl.col("nneg") > 0)))
    auc = (g["rsum"] - g["npos"] * (g["npos"] + 1) / 2) / (g["npos"] * g["nneg"])
    return float(auc.mean())


def run(name: str, features: list[str], tag: str) -> dict:
    print(f"\n{name}  [{tag}]  {len(features)} features: {', '.join(features)}")
    ftr, Xtr, ytr, gtr = load(name, "train", features)
    fva, Xva, yva, gva = load(name, "val", features)

    dtr = lgb.Dataset(Xtr, label=ytr, group=gtr, feature_name=features)
    dva = lgb.Dataset(Xva, label=yva, group=gva, feature_name=features, reference=dtr)
    model = lgb.train(
        PARAMS, dtr, num_boost_round=NUM_ROUNDS, valid_sets=[dva], valid_names=["val"],
        callbacks=[lgb.early_stopping(EARLY_STOPPING, verbose=False), lgb.log_evaluation(100)],
    )
    print(f"  best iteration: {model.best_iteration}")

    out = {"tag": tag, "features": features, "best_iteration": model.best_iteration}
    scores = {}
    for split in ("val", "test"):
        f, X, y, _ = load(name, split, features)
        s = model.predict(X, num_iteration=model.best_iteration)
        scores[split] = (f, s)
        out[f"{split}_auc"] = per_impression_auc(f, s)
        print(f"  {split} per-impression AUC: {out[f'{split}_auc']:.4f}")

    gain = model.feature_importance("gain")
    out["importance"] = {k: float(v) for k, v in
                         sorted(zip(features, gain), key=lambda kv: -kv[1])}
    print("  gain: " + ", ".join(f"{k} {v:.0f}" for k, v in out["importance"].items()))

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"rerank_{name}_{tag}.json").write_text(json.dumps(out, indent=2))
    for split, (f, s) in scores.items():
        f.select(["impression_id", "candidate", "label"]).with_columns(
            pl.Series("score", s)
        ).write_parquet(PROC / name / f"rerank_{tag}_{split}.parquet")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("datasets", nargs="*", default=["ebnerd_small"])
    ap.add_argument("--features", nargs="+", default=None)
    ap.add_argument("--tag", default="full")
    args = ap.parse_args()
    for name in args.datasets:
        run(name, args.features or FEATURES, args.tag)


if __name__ == "__main__":
    main()
