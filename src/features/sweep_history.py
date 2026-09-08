"""Does engagement weighting rescue long histories? A history-length x weighting sweep.

`info.md` makes a specific, testable prediction. Both Assignment-1 systems found that
averaging **more** history made the embedding user vector **worse**, and it argues this is
what you would expect if low-quality clicks dilute the profile, so weighting each click by how
long it was actually read "may recover the benefit of large N that uniform mean-pooling throws
away".

That is two claims:
  1. uniform pooling degrades as N grows            (replicates A1)
  2. read-time weighting degrades less, or improves (new, and the interesting one)

This measures the similarity feature on its own rather than through the ranker, so the result
is about the user vector and nothing else. Metric is per-impression AUC, since a feature that
cannot reorder candidates within an impression scores 0.5 there regardless of how it looks
pooled.

    python -m src.features.sweep_history ebnerd_small --split val
"""

import argparse
import json
from pathlib import Path

import numpy as np
import polars as pl
import yaml

from src.features.build import _article_vectors, _engagement_weights

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG = ROOT / "configs/datasets.yaml"
PROC = ROOT / "data/processed"
RESULTS = ROOT / "results"

N_VALUES = [1, 5, 10, 20, 50, 100]


def user_vectors(engage: dict, index: dict, mat: np.ndarray, n: int, weighting: str) -> dict:
    """User vector from the most recent n clicks, uniformly or read-time weighted."""
    out = {}
    for uid, (arts, read, _scroll) in engage.items():
        keep = [(a, r) for a, r in zip(arts[-n:], read[-n:]) if a in index]
        if not keep:
            continue
        rows = [index[a] for a, _ in keep]
        if weighting == "uniform":
            w = np.ones(len(rows), dtype=np.float32)
        else:
            # log1p so a single very long read cannot dominate the profile.
            w = np.log1p(np.clip(np.array([r for _, r in keep], dtype=np.float32), 0, None))
            if w.sum() <= 0:
                w = np.ones(len(rows), dtype=np.float32)
        v = (mat[rows] * w[:, None]).sum(0)
        nrm = np.linalg.norm(v)
        if nrm > 0:
            out[uid] = (v / nrm).astype(np.float32)
    return out


def score(imps: pl.DataFrame, uvecs: dict, index: dict, mat: np.ndarray) -> float:
    """Per-impression AUC of the similarity feature alone."""
    ids, labels, sims = [], [], []
    for r in imps.iter_rows(named=True):
        uv = uvecs.get(str(r["user_id"]))
        cands, clicked = r["candidates"], set(r["clicked"] or [])
        lab = [1 if c in clicked else 0 for c in cands]
        if min(lab) == max(lab):
            continue                       # no both-class impression, AUC undefined
        if uv is None:
            s = np.zeros(len(cands), dtype=np.float32)
        else:
            rows = [index.get(c, -1) for c in cands]
            s = np.zeros(len(cands), dtype=np.float32)
            ok = [i for i, ix in enumerate(rows) if ix >= 0]
            if ok:
                s[ok] = mat[[rows[i] for i in ok]] @ uv
        ids.extend([r["impression_id"]] * len(cands))
        labels.extend(lab)
        sims.extend(s.tolist())

    d = pl.DataFrame({"impression_id": ids, "label": labels, "s": sims})
    d = d.with_columns(pl.col("s").cast(pl.Float64).rank("average").over("impression_id").alias("r"))
    g = (d.group_by("impression_id")
           .agg(npos=pl.col("label").sum(), n=pl.len(), rsum=(pl.col("r") * pl.col("label")).sum())
           .with_columns(nneg=(pl.col("n") - pl.col("npos"))))
    auc = (g["rsum"] - g["npos"] * (g["npos"] + 1) / 2) / (g["npos"] * g["nneg"])
    return float(auc.mean())


def main() -> None:
    config = yaml.safe_load(CONFIG.read_text())
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dataset", nargs="?", default="ebnerd_small")
    ap.add_argument("--split", default="val")
    args = ap.parse_args()
    name, split = args.dataset, args.split
    cfg = config[name]

    imps = pl.read_parquet(PROC / name / f"impressions_{split}.parquet")
    index, mat = _article_vectors(cfg)
    if index is None:
        raise SystemExit(f"{name}: no article vectors configured")
    engage = _engagement_weights(name)
    if not engage:
        raise SystemExit(f"{name}: no engagement columns, this sweep is EB-NeRD only")
    print(f"{name}/{split}: {imps.height:,} impressions, {len(engage):,} users with history\n")

    rows = []
    print(f"{'N':>5}  {'uniform':>9}  {'read-time':>10}  {'weighted - uniform':>19}")
    for n in N_VALUES:
        r = {"n": n}
        for weighting in ("uniform", "engagement"):
            uv = user_vectors(engage, index, mat, n, weighting)
            r[weighting] = score(imps, uv, index, mat)
        r["delta"] = r["engagement"] - r["uniform"]
        rows.append(r)
        print(f"{n:>5}  {r['uniform']:>9.4f}  {r['engagement']:>10.4f}  {r['delta']:>+19.4f}")

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"sweep_history_{name}_{split}.json").write_text(json.dumps(rows, indent=2))
    u = [r["uniform"] for r in rows]
    e = [r["engagement"] for r in rows]
    print(f"\nuniform    best N={N_VALUES[int(np.argmax(u))]} at {max(u):.4f}")
    print(f"engagement best N={N_VALUES[int(np.argmax(e))]} at {max(e):.4f}")
    print(f"\n-> results/sweep_history_{name}_{split}.json")


if __name__ == "__main__":
    main()
