"""Behavioural features from the click log, one row per (impression, candidate).

A2 Q1. Every feature here must be computable strictly before its impression's own
timestamp; that is the behaviour-window boundary the brief requires, and it is enforced
by construction rather than by care. Where a column exists in both a leaky and a causal
form, only the causal one is read:

    read_time            on behaviors.parquet   describes the impression being predicted
    read_time_fixed      on history.parquet     describes clicks already in the past
    the lifetime totals  on articles.parquet    aggregate the article's whole lifetime
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


def _causal_popularity(cands: list[str], t: np.datetime64, times: dict,
                      window_h: float | None = None) -> np.ndarray:
    """Clicks each candidate received strictly before t, optionally only recent ones.

    searchsorted with side="left" counts entries < t, so a click at exactly t is excluded
    as well as everything after it. That is the boundary the leakage test asserts.

    `window_h` bounds how far back the count reaches. It cannot introduce a leak: a narrower
    window only drops older clicks and never admits newer ones, so the "< t" upper bound is
    untouched. Default None reproduces the original unbounded behaviour exactly.
    """
    if window_h is None:
        return np.array(
            [np.searchsorted(times[c], t, side="left") if c in times else 0 for c in cands],
            dtype=np.float32,
        )
    lo = t - np.timedelta64(int(window_h * 3600), "s")
    out = np.zeros(len(cands), dtype=np.float32)
    for i, c in enumerate(cands):
        arr = times.get(c)
        if arr is not None:
            out[i] = (np.searchsorted(arr, t, side="left")
                      - np.searchsorted(arr, lo, side="left"))
    return out


def _rank_within(values: np.ndarray) -> np.ndarray:
    """Average rank of each value inside its own impression, scaled to [0, 1].

    The metric is per-impression AUC, so "the most popular candidate in THIS impression" is
    what decides a ranking, and an absolute count cannot express it: a popularity of 200 is
    dominant in a quiet impression and unremarkable in a busy one. LightGBM has to learn that
    contrast from absolute splits otherwise, which it cannot do across impressions.
    """
    n = len(values)
    if n == 1:
        return np.array([0.5], dtype=np.float32)
    order = np.argsort(values, kind="stable")
    ranks = np.empty(n, dtype=np.float64)
    ranks[order] = np.arange(n, dtype=np.float64)
    uniq, inv, counts = np.unique(values, return_inverse=True, return_counts=True)
    summed = np.zeros(len(counts))
    np.add.at(summed, inv, ranks)
    ranks = (summed / counts)[inv]
    return (ranks / (n - 1)).astype(np.float32)


def _entity_overlap(cands: list, hist: list, entities_of: dict) -> np.ndarray:
    """Jaccard between the candidate's entities and every entity in the user's history.

    Entities are the people, places and organisations an article is about. Embeddings capture
    topic similarity but blur named entities, so "this user reads about Lindsey Graham" is a
    signal the cosine only partly carries. Fully populated on both datasets and previously
    unused.
    """
    hist_ents: set = set()
    for h in hist:
        e = entities_of.get(h)
        if e:
            hist_ents.update(e)
    out = np.zeros(len(cands), dtype=np.float32)
    if not hist_ents:
        return out
    for i, c in enumerate(cands):
        ce = entities_of.get(c)
        if not ce:
            continue
        ce = set(ce)
        union = len(ce | hist_ents)
        if union:
            out[i] = len(ce & hist_ents) / union
    return out


def _engagement_weights(
    cfg: dict, split: str
) -> dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Per user: (article ids, read seconds, scroll pct) for their past clicks.

    EB-NeRD only. Each block's history.parquet describes clicks strictly before *that
    block's* log period, so it is causally valid only for impressions drawn from the same
    block. Which block a split comes from is read from the same config keys split.py uses,
    so the two cannot drift apart: train and val are carved out of `early_root`, test is
    `test_root`.

    An earlier version looped over both blocks and let the later one overwrite, which for
    the 11,658 users present in both replaced train-block history with validation-block
    history. Since val is carved out of the train block, that is future history for a val
    impression, and it was worth +0.0967 AUC on engage_sim. Never merge the blocks here.
    """
    root = ROOT / (cfg["early_root"] if split in ("train", "val") else cfg["test_root"])
    out: dict[str, tuple] = {}
    path = root / "history.parquet"
    if path.exists():
        h = pl.read_parquet(path)
        cols = set(h.columns)
        if not {"read_time_fixed", "article_id_fixed"} <= cols:
            return out
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


def build(name: str, cfg: dict, split: str, pop_window_h: float | None = None,
          suffix: str = "") -> None:
    imps = pl.read_parquet(PROC / name / f"impressions_{split}.parquet")
    arts = pl.read_parquet(PROC / name / "articles.parquet")

    bm25 = pl.read_parquet(PROC / name / f"bm25_{split}.parquet")
    emb = pl.read_parquet(PROC / name / f"emb_{split}.parquet")
    imps = imps.join(bm25, on="impression_id", how="left").join(emb, on="impression_id", how="left")

    category_of = dict(zip(arts["article_id"], arts["category"]))
    published = dict(zip(arts["article_id"], arts["published_time"]))
    # A polars List column yields Series, not lists, so `if e` raises rather than testing
    # emptiness. Materialise to python lists first and test length explicitly.
    entities_of = {
        a: set(e)
        for a, e in zip(arts["article_id"].to_list(), arts["entities"].to_list())
        if e is not None and len(e) > 0
    }

    print(f"  {split}: {imps.height:,} impressions")
    times, _ = _click_events(name)
    print(f"    click history for {len(times):,} articles")
    engage = _engagement_weights(cfg, split)
    print(f"    engagement arrays for {len(engage):,} users"
          if engage else "    no engagement columns for this dataset")
    index, mat = _article_vectors(cfg)
    uvecs = _engagement_user_vectors(engage, index, mat) if index is not None and engage else {}
    print(f"    engagement-weighted user vectors for {len(uvecs):,} users")

    rows_imp, rows_cand, rows_lab = [], [], []
    f_bm25, f_emb, f_pop, f_age, f_rec = [], [], [], [], []
    f_cat, f_hist, f_read, f_scroll, f_esim = [], [], [], [], []
    f_poprank, f_embrank, f_ent, f_pop24, f_vel = [], [], [], [], []
    f_ncand, f_poprel = [], []

    for r in imps.iter_rows(named=True):
        cands = r["candidates"]
        clicked = set(r["clicked"] or [])
        t = np.datetime64(r["timestamp"])
        n = len(cands)

        rows_imp.extend([r["impression_id"]] * n)
        rows_cand.extend(cands)
        rows_lab.extend([1 if c in clicked else 0 for c in cands])

        bm25_v = np.asarray(r["bm25"] if r["bm25"] is not None else [0.0] * n, dtype=np.float32)
        emb_v = np.asarray(r["emb"] if r["emb"] is not None else [0.0] * n, dtype=np.float32)
        pop_v = _causal_popularity(cands, t, times, pop_window_h)
        f_bm25.extend(bm25_v.tolist())
        f_emb.extend(emb_v.tolist())
        f_pop.extend(pop_v.tolist())

        # Within-impression contrast. See _rank_within: the ranking is decided inside one
        # impression, so the ranker needs each candidate's standing among its actual rivals,
        # not only its absolute value.
        f_poprank.extend(_rank_within(pop_v).tolist())
        f_embrank.extend(_rank_within(emb_v).tolist())
        f_ncand.extend([float(n)] * n)
        pop_max = float(pop_v.max())
        f_poprel.extend((pop_v / (pop_max + 1.0)).tolist())

        # Popularity velocity. 6h beats 24h beats unbounded in isolation (FACTS 16.1), which
        # says recency of attention matters; the ratio expresses "trending now" as opposed to
        # "steadily popular", which no single window can.
        pop24 = _causal_popularity(cands, t, times, 24.0)
        f_pop24.extend(pop24.tolist())
        f_vel.extend((pop_v / (pop24 + 1.0)).tolist())

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
        f_ent.extend(_entity_overlap(cands, hist, entities_of).tolist())

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
        "pop_rank": np.asarray(f_poprank, dtype=np.float32),
        "emb_rank": np.asarray(f_embrank, dtype=np.float32),
        "ent_overlap": np.asarray(f_ent, dtype=np.float32),
        "pop_24h": np.asarray(f_pop24, dtype=np.float32),
        "pop_velocity": np.asarray(f_vel, dtype=np.float32),
        "n_cands": np.asarray(f_ncand, dtype=np.float32),
        "pop_rel_max": np.asarray(f_poprel, dtype=np.float32),
    })
    keep = ["impression_id", "candidate", "label"] + features_for(name)
    dropped = [c for c in out.columns if c not in keep]
    out = out.select(keep)

    # A feature that is "available" but constant carries no information, and a column of
    # zeros looks exactly like a real feature to LightGBM. Emitting one silently is how
    # five MIND columns would have become nulls without anyone noticing, so make it an
    # error instead.
    for f in features_for(name):
        if out[f].null_count() == out.height or out[f].n_unique() <= 1:
            raise SystemExit(
                f"FATAL {name}/{split}: feature '{f}' is declared available but is "
                f"constant or all-null. Either the source columns are missing for this "
                f"dataset, in which case remove it from DATASET_FEATURES, or the builder "
                f"is broken."
            )

    dest = PROC / name / f"features{suffix}_{split}.parquet"
    out.write_parquet(dest)
    print(f"    {out.height:,} candidate rows, {len(features_for(name))} features "
          f"-> {dest.name}" + (f" (dropped {', '.join(dropped)})" if dropped else ""))


FEATURES = ["bm25", "emb", "pop_causal", "age_hours", "recency", "cat_match",
            "hist_len", "user_read", "user_scroll", "engage_sim",
            # Added 2026-09-14. All seven are computable on both datasets: they need only
            # click times, categories and entities, never published_time or engagement.
            "pop_rank", "emb_rank", "ent_overlap", "pop_24h", "pop_velocity",
            "n_cands", "pop_rel_max"]

# Which features each dataset can actually support, stated per dataset rather than left to
# whatever the columns happen to contain. info.md section 5 is the spec: MIND has no
# behavioural columns, so any behavioural feature widens the gap between what the two
# systems can do, and the two configurations must be kept explicitly separate and reported
# rather than presented as one system that is quietly two different models.
#
# Measured on mind_small, 65,238 articles and 61,894 val impressions:
#   published_time      100% null  -> age_hours, recency cannot be computed
#   total_* lifetime    100% null  -> the Q9 leaky arm cannot exist on MIND either
#   history.parquet     absent     -> user_read, user_scroll, engage_sim have no source
#   history_timestamps  100% null lists, dtype List(Datetime) not Null, so `.list.len()`
#                       returns null rather than 0 and an equality test against 0 matches
#                       nothing. This is the shape that let an earlier MIND leakage test
#                       pass over 95,071 rows while checking none of them.
DATASET_FEATURES = {
    "mind_small": ["bm25", "emb", "pop_causal", "cat_match", "hist_len",
                   "pop_rank", "emb_rank", "ent_overlap", "pop_24h", "pop_velocity",
                   "n_cands", "pop_rel_max"],
}


# How far back `pop_causal` counts, per dataset. Measured on EB-NeRD small: a 6 hour window
# beats unbounded by +0.0034 [+0.0026, +0.0043] val and +0.0062 [+0.0058, +0.0067] test at
# ranker level, paired bootstrap, significant on both. "How popular is this right now" is a
# better news signal than "how popular has it ever been". See FACTS.md 16.1.
#
# MIND is left unbounded on purpose. Its popularity is derived from impression timestamps
# rather than per-click history, its corpus spans a different window, and the sweep was never
# run there. Shipping an EB-NeRD constant to a dataset it was not measured on is the kind of
# single global setting info.md section 5 warns against.
POP_WINDOW_H = {
    "ebnerd_demo": 6.0,
    "ebnerd_small": 6.0,
}


def pop_window_for(name: str) -> float | None:
    """Hours of history `pop_causal` counts for one dataset. None means unbounded."""
    return POP_WINDOW_H.get(name)


def features_for(name: str) -> list[str]:
    """The feature set for one dataset. Defaults to all of them where nothing is missing."""
    return DATASET_FEATURES.get(name, FEATURES)


def main() -> None:
    config = yaml.safe_load(CONFIG.read_text())
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("datasets", nargs="*", default=list(config))
    ap.add_argument("--splits", nargs="+", default=["train", "val", "test"])
    ap.add_argument("--pop-window-h", type=float, default=None,
                    help="Override the per-dataset causal-popularity window, in hours. "
                         "Default is POP_WINDOW_H for the dataset. Cannot leak: a window "
                         "only drops older clicks, never admits newer ones.")
    ap.add_argument("--suffix", default="",
                    help="Write features<suffix>_<split>.parquet, for building an ablation "
                         "variant without overwriting the shipped feature store.")
    args = ap.parse_args()
    for name in args.datasets:
        print(f"\n{name}")
        for split in args.splits:
            window = args.pop_window_h if args.pop_window_h is not None else pop_window_for(name)
            build(name, config[name], split, window, args.suffix)


if __name__ == "__main__":
    main()
