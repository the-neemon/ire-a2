"""Does more history help the user vector? Measured from the impressions' own history.

A2 N5, cross-dataset. `sweep_history.py` builds the user vector from `history.parquet`'s
per-user engagement arrays, which only EB-NeRD has. This builds it per impression from the
`history` column that every dataset carries, so the same question can be asked on MIND.

The question is A1's claim, repeated by both A1 systems and used as the premise for info.md's
read-time hypothesis: averaging *more* history makes the embedding user vector *worse*. On
EB-NeRD with clean history that reversed, and the curve rose monotonically to N=100. MIND is an
independent corpus, so it is a real test of whether the reversal is a property of the method or
of the dataset.

Uniform weights only. Read-time weighting cannot be asked here: MIND has no read-time column.

Metric is per-impression AUC of the similarity feature alone, so the result is about the user
vector and nothing else.

    python -m src.features.sweep_history_impression mind_small --split val
"""

import argparse
import json
from pathlib import Path

import numpy as np
import polars as pl
import yaml

from src.features.build import _article_vectors

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG = ROOT / "configs/datasets.yaml"
PROC = ROOT / "data/processed"
RESULTS = ROOT / "results"

N_VALUES = [1, 5, 10, 20, 50, 100]


def impression_auc(scores: np.ndarray, labels: np.ndarray) -> float | None:
    """Mann-Whitney AUC inside one impression, average ranks for ties."""
    n_pos = int(labels.sum())
    n_neg = len(labels) - n_pos
    if n_pos == 0 or n_neg == 0:
        return None
    order = np.argsort(scores, kind="stable")
    ranks = np.empty(len(scores), dtype=np.float64)
    ranks[order] = np.arange(1, len(scores) + 1)
    _, inv, counts = np.unique(scores, return_inverse=True, return_counts=True)
    summed = np.zeros(len(counts))
    np.add.at(summed, inv, ranks)
    ranks = (summed / counts)[inv]
    return (ranks[labels == 1].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)


def score_at_n(imps: pl.DataFrame, index: dict, mat: np.ndarray, n: int) -> tuple[float, int]:
    """Mean per-impression AUC using the most recent n history items of that impression.

    The history column is the impression's own, and split.py's history is causally clean:
    0% of impressions on any split carry a history timestamp at or after their own.
    """
    aucs = []
    for r in imps.iter_rows(named=True):
        hist = r["history"]
        if hist is None or len(hist) == 0:
            continue
        rows = [index[a] for a in hist[-n:] if a in index]
        if not rows:
            continue
        v = mat[rows].sum(0)
        nrm = np.linalg.norm(v)
        if nrm <= 0:
            continue
        v = v / nrm
        cands = r["candidates"]
        c_rows = [index.get(c, -1) for c in cands]
        sims = np.zeros(len(cands), dtype=np.float32)
        ok = [i for i, ix in enumerate(c_rows) if ix >= 0]
        if not ok:
            continue
        sims[ok] = mat[[c_rows[i] for i in ok]] @ v
        clicked = set(r["clicked"] or [])
        labels = np.fromiter((1 if c in clicked else 0 for c in cands), dtype=np.int8,
                             count=len(cands))
        a = impression_auc(sims, labels)
        if a is not None:
            aucs.append(a)
    return float(np.mean(aucs)), len(aucs)


def main() -> None:
    config = yaml.safe_load(CONFIG.read_text())
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dataset", nargs="?", default="mind_small")
    ap.add_argument("--split", default="val")
    args = ap.parse_args()
    name, split = args.dataset, args.split

    index, mat = _article_vectors(config[name])
    if index is None:
        raise SystemExit(f"{name}: no article vectors configured")
    imps = pl.read_parquet(PROC / name / f"impressions_{split}.parquet",
                           columns=["impression_id", "history", "candidates", "clicked"])

    print(f"{name}/{split}: {imps.height:,} impressions, uniform user vector\n")
    print(f"{'N':>5}  {'auc':>8}  {'scored':>9}")
    rows = []
    for n in N_VALUES:
        auc, scored = score_at_n(imps, index, mat, n)
        rows.append({"n": n, "auc": auc, "impressions": scored})
        print(f"{n:>5}  {auc:>8.4f}  {scored:>9,}")

    best = max(rows, key=lambda r: r["auc"])
    print(f"\nbest N={best['n']} at {best['auc']:.4f}")

    RESULTS.mkdir(exist_ok=True)
    dest = RESULTS / f"sweep_history_impression_{name}_{split}.json"
    dest.write_text(json.dumps({"weighting": "uniform", "arms": rows}, indent=2))
    print(f"-> {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
