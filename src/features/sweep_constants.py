"""Two unswept constants: the causal popularity window and the recency half-life.

A2 N5. Both were chosen once and never measured. `RECENCY_HALFLIFE_H = 24.0` is documented in
build.py as "a starting value, swept as its own ablation", and the sweep never happened; the
popularity window is currently unbounded, counting every click before t.

Measured on the feature alone rather than through the ranker, the same way sweep_history.py
measures the user vector. A feature that cannot reorder candidates inside an impression scores
0.5 here regardless of how it looks pooled, and an isolated number cannot be absorbed by a
correlated neighbour the way a LightGBM ablation arm can. The trade is that a winner here is a
candidate for a ranker-level check, not a finished result.

    python -m src.features.sweep_constants ebnerd_small --split val
"""

import argparse
import json
from pathlib import Path

import numpy as np
import polars as pl

from src.features.build import _click_events, features_for

ROOT = Path(__file__).resolve().parent.parent.parent
PROC = ROOT / "data/processed"
RESULTS = ROOT / "results"

HALFLIVES_H = [1.0, 3.0, 6.0, 12.0, 24.0, 48.0, 96.0, 168.0]
WINDOWS_H = [1.0, 6.0, 24.0, 72.0, 168.0, None]        # None = unbounded, the current setting


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


def sweep_halflife(feats: pl.DataFrame) -> list[dict]:
    """Recency is a pure transform of age_hours, so no rebuild is needed to vary it."""
    rows = []
    for h in HALFLIVES_H:
        aucs = []
        for (_,), g in feats.group_by(["impression_id"], maintain_order=True):
            age = g["age_hours"].to_numpy()
            decay = np.where(np.isnan(age), 0.0, 0.5 ** (np.clip(age, 0, None) / h))
            a = impression_auc(decay, g["label"].to_numpy())
            if a is not None:
                aucs.append(a)
        rows.append({"halflife_h": h, "auc": float(np.mean(aucs)), "impressions": len(aucs)})
        print(f"{h:>8.1f}  {rows[-1]['auc']:.4f}")
    return rows


def sweep_window(imps: pl.DataFrame, times: dict) -> list[dict]:
    """Count clicks in (t - window, t) rather than everything before t.

    The strict "< t" upper bound is unchanged, so no setting here can leak: a narrower window
    only removes older clicks, never admits newer ones.
    """
    rows = []
    for w in WINDOWS_H:
        aucs = []
        for r in imps.iter_rows(named=True):
            t = np.datetime64(r["timestamp"])
            lo = None if w is None else t - np.timedelta64(int(w * 3600), "s")
            clicked = set(r["clicked"] or [])
            cands = r["candidates"]
            pop = np.empty(len(cands), dtype=np.float32)
            for i, c in enumerate(cands):
                arr = times.get(c)
                if arr is None:
                    pop[i] = 0.0
                    continue
                hi = np.searchsorted(arr, t, side="left")
                pop[i] = hi if lo is None else hi - np.searchsorted(arr, lo, side="left")
            labels = np.fromiter((1 if c in clicked else 0 for c in cands), dtype=np.int8,
                                 count=len(cands))
            a = impression_auc(pop, labels)
            if a is not None:
                aucs.append(a)
        label = "unbounded" if w is None else f"{w:.0f}h"
        rows.append({"window_h": w, "auc": float(np.mean(aucs)), "impressions": len(aucs)})
        print(f"{label:>10}  {rows[-1]['auc']:.4f}")
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dataset", nargs="?", default="ebnerd_small")
    ap.add_argument("--split", default="val")
    args = ap.parse_args()
    name, split = args.dataset, args.split

    # age_hours needs published_time, which MIND does not have, so the half-life sweep is
    # EB-NeRD only. The window sweep below works anywhere, since it needs only click times.
    halflives = []
    if "age_hours" in features_for(name):
        feats = pl.read_parquet(PROC / name / f"features_{split}.parquet",
                                columns=["impression_id", "label", "age_hours"])
        print(f"{name}/{split}: recency half-life, isolated feature AUC\n")
        print(f"{'halflife_h':>8}  {'auc':>6}")
        halflives = sweep_halflife(feats)
        del feats
    else:
        print(f"{name}: no age_hours for this dataset, skipping the half-life sweep")

    imps = pl.read_parquet(PROC / name / f"impressions_{split}.parquet",
                           columns=["impression_id", "timestamp", "candidates", "clicked"])
    times, _ = _click_events(name)
    print(f"\n{name}/{split}: causal popularity window, isolated feature AUC\n")
    print(f"{'window':>10}  {'auc':>6}")
    windows = sweep_window(imps, times)

    best_w = max(windows, key=lambda r: r["auc"])
    if halflives:
        best_h = max(halflives, key=lambda r: r["auc"])
        cur_h = [r for r in halflives if r["halflife_h"] == 24.0][0]["auc"]
        print(f"\nbest half-life {best_h['halflife_h']:.0f} h at {best_h['auc']:.4f} "
              f"(current 24 h at {cur_h:.4f})")
    cur_w = [r for r in windows if r["window_h"] is None][0]
    print(f"best window {best_w['window_h'] or 'unbounded'} at {best_w['auc']:.4f} "
          f"(current unbounded at {cur_w['auc']:.4f})")

    RESULTS.mkdir(exist_ok=True)
    dest = RESULTS / f"sweep_constants_{name}_{split}.json"
    dest.write_text(json.dumps({"halflife": halflives, "window": windows}, indent=2))
    print(f"\n-> {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
