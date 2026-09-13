"""N5: scroll completion as a click-quality filter on the user profile.

`info.md` item 4 proposes using `scroll_percentage_fixed` to drop history entries the user barely
engaged with, so the profile is built only from genuine reads. It explicitly "complements rather
than duplicates" read-time weighting, so the weighting result does not settle it and it needs its
own measurement.

Same protocol as sweep_history: per-impression AUC of the similarity feature alone, so the result
is about the user vector and nothing else. One variable, the scroll threshold; history length and
weighting are held fixed.

    python -m src.features.sweep_scroll ebnerd_small --split val
"""

import argparse
import json
from pathlib import Path

import numpy as np
import polars as pl
import yaml

from src.features.build import _article_vectors, _engagement_weights
from src.features.sweep_history import score

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG = ROOT / "configs/datasets.yaml"
PROC = ROOT / "data/processed"
RESULTS = ROOT / "results"

THRESHOLDS = [0.0, 10.0, 25.0, 50.0, 75.0, 90.0]     # 0 = no filter, the current behaviour
HISTORY_N = 100        # the sweep optimum on clean history, so the filter is tested where it matters


def user_vectors_filtered(engage: dict, index: dict, mat: np.ndarray, n: int,
                          min_scroll: float) -> tuple[dict, int, int]:
    """User vector from the most recent n clicks that cleared the scroll threshold.

    Returns the vectors plus how many history entries survived and how many there were, because
    a threshold that drops almost everything will look like a scroll result when it is really a
    sample-size result.
    """
    out, kept_total, seen_total = {}, 0, 0
    for uid, (arts, _read, scroll) in engage.items():
        a_win, s_win = arts[-n:], scroll[-n:]
        seen_total += len(a_win)
        keep = [a for a, s in zip(a_win, s_win)
                if a in index and (min_scroll <= 0 or (not np.isnan(s) and s >= min_scroll))]
        kept_total += len(keep)
        if not keep:
            continue
        rows = [index[a] for a in keep]
        v = mat[rows].sum(0)
        nrm = np.linalg.norm(v)
        if nrm > 0:
            out[uid] = (v / nrm).astype(np.float32)
    return out, kept_total, seen_total


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
    engage = _engagement_weights(cfg, split)
    if not engage:
        raise SystemExit(f"{name}: no engagement columns, this sweep is EB-NeRD only")

    print(f"{name}/{split}: scroll-completion filter on the user profile, N={HISTORY_N}\n")
    print(f"{'min_scroll':>11}  {'auc':>7}  {'users':>7}  {'history kept':>13}")
    rows = []
    for thr in THRESHOLDS:
        uv, kept, seen = user_vectors_filtered(engage, index, mat, HISTORY_N, thr)
        auc = score(imps, uv, index, mat)
        frac = kept / seen if seen else 0.0
        rows.append({"min_scroll": thr, "auc": auc, "users": len(uv), "history_kept": frac})
        print(f"{thr:>11.0f}  {auc:>7.4f}  {len(uv):>7,}  {frac:>12.1%}")

    base = rows[0]
    best = max(rows, key=lambda r: r["auc"])
    print(f"\nno filter {base['auc']:.4f}, best {best['min_scroll']:.0f}% at {best['auc']:.4f} "
          f"({best['auc'] - base['auc']:+.4f})")

    RESULTS.mkdir(exist_ok=True)
    dest = RESULTS / f"sweep_scroll_{name}_{split}.json"
    dest.write_text(json.dumps({"history_n": HISTORY_N, "arms": rows}, indent=2))
    print(f"-> {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
