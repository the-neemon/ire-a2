"""Behavioural features from the click log, one row per (impression, candidate).

A2 Q1. Every feature here must be computable strictly before its impression's own
timestamp; that is the behaviour-window boundary the brief requires, and it is enforced
by construction rather than by care. Where a column exists in both a leaky and a causal
form, only the causal one is read:

    read_time            on behaviors.parquet   describes the impression being predicted
    read_time_fixed      on history.parquet     describes clicks already in the past
    total_inviews etc.   on articles.parquet    aggregate the article's whole lifetime
    published_time       on articles.parquet    fixed before any impression sees it

Emits data/processed/<dataset>/features_<split>.parquet.

    python -m src.features.build ebnerd_small
    python -m src.features.build ebnerd_small --splits val test
"""

import argparse
from pathlib import Path

import numpy as np
import polars as pl
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG = ROOT / "configs/datasets.yaml"
PROC = ROOT / "data/processed"
INTERIM = ROOT / "data/interim"

# Article age is turned into a decay rather than fed raw, because clicks fall off sharply
# in the first hours and a linear age lets a month-old article sit numerically close to a
# day-old one. 24 h is a starting value, swept as its own ablation.
RECENCY_HALFLIFE_H = 24.0


def _click_events(name: str) -> tuple[dict[str, np.ndarray], set]:
    """Every (article, click time) in the dataset, grouped by article and sorted.

    Read from all splits on purpose. Popularity for an impression at time t means every
    click that had already happened by t, which is what a live system would know; the
    split a click happens to sit in is an artefact of our evaluation, not of time. The
    strict "< t" cut is applied at lookup, so no click at or after t can ever contribute.
    """
    frames = []
    for split in ("train", "val", "test"):
        p = PROC / name / f"impressions_{split}.parquet"
        if p.exists():
            frames.append(
                pl.read_parquet(p, columns=["timestamp", "clicked"])
                .explode("clicked")
                .drop_nulls("clicked")
            )
    events = pl.concat(frames)
    times: dict[str, np.ndarray] = {}
    for article, grp in events.group_by("clicked"):
        key = article[0] if isinstance(article, tuple) else article
        times[key] = np.sort(grp["timestamp"].to_numpy())
    return times, set(times)


def _causal_popularity(cands: list[str], t: np.datetime64, times: dict) -> np.ndarray:
    """Clicks each candidate received strictly before t.

    searchsorted with side="left" counts entries < t, so a click at exactly t is excluded
    as well as everything after it. That is the boundary the leakage test asserts.
    """
    return np.array(
        [np.searchsorted(times[c], t, side="left") if c in times else 0 for c in cands],
        dtype=np.float32,
    )


def _engagement_weights(name: str) -> dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Per user: (article ids, read seconds, scroll pct) for their past clicks.

    EB-NeRD only. These arrays live on history.parquet, which describes clicks strictly
    before the log period, so all three are causally valid. Neither A1 system used the
    read-time or scroll columns at all.
    """
    out: dict[str, tuple] = {}
    for block in ("train", "validation"):
        p = INTERIM / name / block / "history.parquet"
        if not p.exists():
            continue
        h = pl.read_parquet(p)
        cols = set(h.columns)
        if not {"read_time_fixed", "article_id_fixed"} <= cols:
            continue
        for row in h.iter_rows(named=True):
            uid = str(row["user_id"])
            arts = np.asarray(row["article_id_fixed"], dtype=object).astype(str)
            read = np.asarray(row["read_time_fixed"], dtype=np.float32)
            scroll = np.asarray(
                row["scroll_percentage_fixed"] if "scroll_percentage_fixed" in cols
                else np.zeros(len(arts)), dtype=np.float32
            )
            out[uid] = (arts, np.nan_to_num(read), np.nan_to_num(scroll))
    return out


def _article_vectors(cfg: dict) -> tuple[dict[str, int], np.ndarray] | tuple[None, None]:
    """Article embeddings, L2-normalised, so a dot product is a cosine."""
    rel = cfg.get("embeddings")
    if not rel or not (ROOT / rel).exists():
        return None, None
    df = pl.read_parquet(ROOT / rel)
    id_col, vec_col = df.columns[0], df.columns[-1]
    ids = df[id_col].cast(pl.Utf8).to_list()
    # explode().to_numpy() rather than np.vstack(col.to_list()): the latter boxes every
    # row into Python objects and peaked at 5.8 GB for a 385 MB array during A1.
    n, d = df.height, len(df[vec_col][0])
    mat = df[vec_col].explode().to_numpy().astype(np.float32).reshape(n, d)
    mat /= np.linalg.norm(mat, axis=1, keepdims=True).clip(1e-9)
    return {a: i for i, a in enumerate(ids)}, mat


def _engagement_user_vectors(engage: dict, index: dict, mat: np.ndarray) -> dict[str, np.ndarray]:
    """User vector as a read-time-weighted mean of past clicked articles.

    The plain `emb` feature is the same computation with uniform weights, so the pair is a
    clean one-variable ablation: does weighting a click by how long it was actually read
    beat counting every click equally? Weights are log1p(seconds) so one very long read
    cannot dominate the profile. Both A1 systems used uniform weights and both found that
    averaging more history made the user vector worse, which is what you would expect if
    low-quality clicks are diluting it.
    """
    out: dict[str, np.ndarray] = {}
    for uid, (arts, read, _scroll) in engage.items():
        rows = [index[a] for a in arts if a in index]
        if not rows:
            continue
        w = np.log1p(np.clip(read[[i for i, a in enumerate(arts) if a in index]], 0, None))
        if w.sum() <= 0:
            w = np.ones(len(rows), dtype=np.float32)
        v = (mat[rows] * w[:, None]).sum(0)
        norm = np.linalg.norm(v)
        if norm > 0:
            out[uid] = (v / norm).astype(np.float32)
    return out


def build(name: str, cfg: dict, split: str) -> None:
    imps = pl.read_parquet(PROC / name / f"impressions_{split}.parquet")
    arts = pl.read_parquet(PROC / name / "articles.parquet")

    bm25 = pl.read_parquet(PROC / name / f"bm25_{split}.parquet")
    emb = pl.read_parquet(PROC / name / f"emb_{split}.parquet")
    imps = imps.join(bm25, on="impression_id", how="left").join(emb, on="impression_id", how="left")

    category_of = dict(zip(arts["article_id"], arts["category"]))
    published = dict(zip(arts["article_id"], arts["published_time"]))

    print(f"  {split}: {imps.height:,} impressions")
    times, _ = _click_events(name)
    print(f"    click history for {len(times):,} articles")
    engage = _engagement_weights(name)
    print(f"    engagement arrays for {len(engage):,} users"
          if engage else "    no engagement columns for this dataset")
    index, mat = _article_vectors(cfg)
    uvecs = _engagement_user_vectors(engage, index, mat) if index is not None and engage else {}
    print(f"    engagement-weighted user vectors for {len(uvecs):,} users")

    rows_imp, rows_cand, rows_lab = [], [], []
    f_bm25, f_emb, f_pop, f_age, f_rec = [], [], [], [], []
    f_cat, f_hist, f_read, f_scroll, f_esim = [], [], [], [], []

    for r in imps.iter_rows(named=True):
        cands = r["candidates"]
        clicked = set(r["clicked"] or [])
        t = np.datetime64(r["timestamp"])
        n = len(cands)

        rows_imp.extend([r["impression_id"]] * n)
        rows_cand.extend(cands)
        rows_lab.extend([1 if c in clicked else 0 for c in cands])

        f_bm25.extend(r["bm25"] if r["bm25"] is not None else [0.0] * n)
        f_emb.extend(r["emb"] if r["emb"] is not None else [0.0] * n)
        f_pop.extend(_causal_popularity(cands, t, times).tolist())

        # Freshness. published_time is fixed before any impression, so age is causal.
        ages = []
        for c in cands:
            p = published.get(c)
            ages.append(np.nan if p is None else (t - np.datetime64(p)) / np.timedelta64(1, "h"))
        ages = np.asarray(ages, dtype=np.float64)
        f_age.extend(np.nan_to_num(ages, nan=-1.0).tolist())
        with np.errstate(over="ignore"):
            decay = np.where(np.isnan(ages), 0.0, 0.5 ** (np.clip(ages, 0, None) / RECENCY_HALFLIFE_H))
        f_rec.extend(decay.tolist())

        # How much of this user's history sits in the candidate's category.
        hist = r["history"] or []
        f_hist.extend([float(len(hist))] * n)
        if hist:
            hist_cats = [category_of.get(h) for h in hist]
            total = sum(1 for c in hist_cats if c is not None) or 1
            share = {}
            for c in hist_cats:
                if c is not None:
                    share[c] = share.get(c, 0) + 1
            f_cat.extend([share.get(category_of.get(c), 0) / total for c in cands])
        else:
            f_cat.extend([0.0] * n)

        # User-level engagement quality, from strictly past clicks. These are constant
        # across an impression's candidates so they cannot rank on their own; they are
        # here for the ranker to interact with (trust emb less when history is thin).
        ent = engage.get(str(r["user_id"]))
        if ent is None or len(ent[1]) == 0:
            f_read.extend([0.0] * n)
            f_scroll.extend([0.0] * n)
        else:
            f_read.extend([float(np.log1p(np.mean(ent[1])))] * n)
            f_scroll.extend([float(np.mean(ent[2]))] * n)

        # Engagement-weighted similarity. Unlike the three above this varies per candidate,
        # so it can actually reorder them.
        uv = uvecs.get(str(r["user_id"]))
        if uv is None or index is None:
            f_esim.extend([0.0] * n)
        else:
            rows_ix = [index.get(c, -1) for c in cands]
            sims = np.zeros(n, dtype=np.float32)
            ok = [i for i, ix in enumerate(rows_ix) if ix >= 0]
            if ok:
                sims[ok] = mat[[rows_ix[i] for i in ok]] @ uv
            f_esim.extend(sims.tolist())

    out = pl.DataFrame({
        "impression_id": rows_imp,
        "candidate": rows_cand,
        "label": np.asarray(rows_lab, dtype=np.int8),
        "bm25": np.asarray(f_bm25, dtype=np.float32),
        "emb": np.asarray(f_emb, dtype=np.float32),
        "pop_causal": np.asarray(f_pop, dtype=np.float32),
        "age_hours": np.asarray(f_age, dtype=np.float32),
        "recency": np.asarray(f_rec, dtype=np.float32),
        "cat_match": np.asarray(f_cat, dtype=np.float32),
        "hist_len": np.asarray(f_hist, dtype=np.float32),
        "user_read": np.asarray(f_read, dtype=np.float32),
        "user_scroll": np.asarray(f_scroll, dtype=np.float32),
        "engage_sim": np.asarray(f_esim, dtype=np.float32),
    })
    dest = PROC / name / f"features_{split}.parquet"
    out.write_parquet(dest)
    print(f"    {out.height:,} candidate rows, {len(out.columns) - 3} features -> {dest.name}")


FEATURES = ["bm25", "emb", "pop_causal", "age_hours", "recency", "cat_match",
            "hist_len", "user_read", "user_scroll", "engage_sim"]


def main() -> None:
    config = yaml.safe_load(CONFIG.read_text())
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("datasets", nargs="*", default=list(config))
    ap.add_argument("--splits", nargs="+", default=["train", "val", "test"])
    args = ap.parse_args()
    for name in args.datasets:
        print(f"\n{name}")
        for split in args.splits:
            build(name, config[name], split)


if __name__ == "__main__":
    main()
