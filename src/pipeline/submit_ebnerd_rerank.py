"""EB-NeRD Codabench submission scored by the re-ranker.

13.5M impressions, ~206M candidate pairs, so nothing is materialised whole except the exposure
index and the article tables. Impressions stream in slices; slice pushdown reaches the parquet
row groups, so a slice at offset 13M costs the same as one at 0.

Sixteen features, matching models/ebnerd_small_submission.txt. The list is read off the booster
so train and serve cannot silently disagree. Click popularity is absent because Codabench
withholds article_ids_clicked; its exposure counterparts replace it. BM25 is absent on cost.

    python -m src.pipeline.submit_ebnerd_rerank --model models/ebnerd_small_submission.txt
"""

import argparse
import zipfile
from pathlib import Path

import lightgbm as lgb
import numpy as np
import polars as pl
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG = ROOT / "configs/datasets.yaml"
INTERIM = ROOT / "data/interim"
OUT = ROOT / "submissions"
BATCH = 25_000   # progress granularity only; scoring is per impression regardless
HISTORY_LEN = 30
RECENCY_HALFLIFE_H = 24.0
POP_WINDOW_H = 6.0


def rank_within(values: np.ndarray) -> np.ndarray:
    n = len(values)
    if n == 1:
        return np.array([0.5], dtype=np.float32)
    order = np.argsort(values, kind="stable")
    ranks = np.empty(n, dtype=np.float64)
    ranks[order] = np.arange(n, dtype=np.float64)
    _, inv, counts = np.unique(values, return_inverse=True, return_counts=True)
    summed = np.zeros(len(counts))
    np.add.at(summed, inv, ranks)
    return ((summed / counts)[inv] / (n - 1)).astype(np.float32)


def ranks_from(scores: np.ndarray) -> np.ndarray:
    order = np.argsort(-scores, kind="stable")
    out = np.empty(len(scores), dtype=np.int64)
    out[order] = np.arange(1, len(scores) + 1)
    return out


def count_before(arr, t, window_h):
    if arr is None or len(arr) == 0:
        return 0.0
    hi = np.searchsorted(arr, t, side="left")
    if window_h is None:
        return float(hi)
    lo = np.searchsorted(arr, t - np.timedelta64(int(window_h * 3600), "s"), side="left")
    return float(hi - lo)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", required=True)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--out", default="ebnerd_predictions.zip")
    args = ap.parse_args()

    booster = lgb.Booster(model_file=args.model)
    names = booster.feature_name()
    print(f"model expects {len(names)} features: {', '.join(names)}", flush=True)

    cfg = yaml.safe_load(CONFIG.read_text())["ebnerd_small"]
    root = INTERIM / "ebnerd_testset/ebnerd_testset"

    arts = pl.read_parquet(root / "articles.parquet",
                           columns=["article_id", "published_time", "category", "ner_clusters"])
    ids = arts["article_id"].to_numpy().astype(np.int64)
    n_art = int(ids.max()) + 1
    art_row = np.full(n_art + 1, -1, dtype=np.int64)
    art_row[ids] = np.arange(len(ids))

    table = pl.read_parquet(ROOT / cfg["embeddings"])
    vec_col = next(c for c in table.columns if c != "article_id")
    dim = len(table[vec_col][0])
    raw = table[vec_col].explode().to_numpy().astype(np.float32).reshape(table.height, dim)
    found = {a: i for i, a in enumerate(table["article_id"].cast(pl.Int64).to_list())}
    vectors = np.zeros((len(ids) + 1, dim), dtype=np.float32)
    for j, a in enumerate(arts["article_id"].cast(pl.Int64).to_list()):
        if a in found:
            vectors[j] = raw[found[a]]
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-9
    unknown = len(vectors) - 1
    art_row[art_row < 0] = unknown
    del raw, table, found
    print(f"{len(ids):,} articles, dim {dim}", flush=True)

    published = np.full(len(ids) + 1, np.datetime64("NaT"), dtype="datetime64[us]")
    published[:len(ids)] = arts["published_time"].to_numpy()
    category = arts["category"].cast(pl.Utf8).fill_null("<unk>").to_list() + ["<unk>"]
    ents = [set(e) if e is not None else set() for e in arts["ner_clusters"].to_list()]
    ents.append(set())
    del arts
    print(f"entities for {sum(1 for s in ents if s):,} articles", flush=True)

    hist = pl.read_parquet(root / "test/history.parquet")
    uids = hist["user_id"].to_numpy().astype(np.int64)
    user_row = np.full(int(uids.max()) + 2, -1, dtype=np.int64)
    user_row[uids] = np.arange(hist.height)
    h_arts = hist["article_id_fixed"].to_list()
    h_read = hist["read_time_fixed"].to_list()
    h_scroll = hist["scroll_percentage_fixed"].to_list()
    del hist, uids
    print(f"{len(h_arts):,} users with history", flush=True)

    scan = pl.scan_parquet(root / "test/behaviors.parquet").select(
        "impression_id", "user_id", "impression_time", "article_ids_inview")
    total = scan.select(pl.len()).collect().item()
    if args.limit:
        total = min(total, args.limit)
    print(f"{total:,} impressions", flush=True)

    print("building exposure index (one pass over every in-view list)", flush=True)
    ex = (pl.scan_parquet(root / "test/behaviors.parquet")
            .select("impression_time", "article_ids_inview")
            .explode("article_ids_inview")
            .drop_nulls("article_ids_inview")
            .sort("article_ids_inview", "impression_time")
            .collect())
    ex_art = ex["article_ids_inview"].to_numpy().astype(np.int64)
    ex_time = ex["impression_time"].to_numpy()
    del ex
    # Sliding-window sweep instead of per-candidate binary search. Exposure events and
    # impressions are both processed in time order, so two pointers per window maintain an
    # exact live count per article: advance the upper pointer over events strictly before t,
    # advance the lower pointer over events that have aged out. Every candidate then reads its
    # count by array indexing.
    #
    # The first version called searchsorted twice per candidate from Python, about 200M calls,
    # and measured 3.1M of 13.5M impressions in 8h41m, projecting to ~38 hours. This is O(N).
    order_ev = np.argsort(ex_time, kind="stable")
    ev_time = ex_time[order_ev]
    ev_art = ex_art[order_ev]
    del ex_time, ex_art, order_ev
    print(f"  {len(ev_time):,} exposure events sorted by time", flush=True)

    count6 = np.zeros(n_art + 2, dtype=np.int32)
    count24 = np.zeros(n_art + 2, dtype=np.int32)
    p_hi = p_lo6 = p_lo24 = 0
    n_ev = len(ev_time)

    OUT.mkdir(exist_ok=True)
    # Name the intermediate after the archive, not a fixed path: otherwise a --limit
    # smoke run overwrites a completed full run's text file. A partial file written to
    # the real upload path is this project's most expensive recorded mistake (0.84% of
    # the test set, scored 0.5012, looked like a valid submission and a bad model).
    txt = OUT / (Path(args.out).stem + "__predictions.txt")
    written = 0

    # The sweep requires time order; the submission requires the test file's own row order.
    # So visit in time order and keep the rendered line against its original position, then
    # write once at the end. A mis-ordered submission scores near chance and looks valid.
    everything = scan.head(total).collect().with_row_index("row_pos")
    everything = everything.sort("impression_time")
    lines = [None] * total
    user_cache = {}
    print("  scoring in time order, writing in file order", flush=True)

    for offset in range(0, total, BATCH):
        batch = everything.slice(offset, min(BATCH, total - offset))
        buf_X, buf_len, buf_pos, buf_id = [], [], [], []
        if True:
            for row in batch.iter_rows(named=True):
                cands = np.asarray(row["article_ids_inview"], dtype=np.int64)
                rows_c = art_row[np.clip(cands, 0, n_art)]
                t = np.datetime64(row["impression_time"])
                n = len(cands)

                # Freshness. published_time is fixed before any impression, so age is causal.
                # Candidate-side, so it cannot be cached per user.
                ages = ((t - published[rows_c]) / np.timedelta64(1, "h")).astype(np.float64)
                with np.errstate(over="ignore", invalid="ignore"):
                    decay = np.where(np.isnan(ages), 0.0,
                                     0.5 ** (np.clip(ages, 0, None) / RECENCY_HALFLIFE_H))

                # Everything derived from history depends only on the user, and each user
                # appears 16.8 times in this file (13,536,710 impressions, 807,677 users).
                # Recomputing it per impression redid all of it ~17x and was the dominant
                # cost: the first full attempt scored under 25,000 impressions in 15 minutes,
                # projecting past 135 hours against an 18 hour wall.
                uid = row["user_id"]
                cached = user_cache.get(uid)
                if cached is None:
                    ur = user_row[uid] if uid < len(user_row) else -1
                    if ur >= 0:
                        ha = np.asarray(h_arts[ur], dtype=np.int64)[-HISTORY_LEN:]
                        hr = np.asarray(h_read[ur], dtype=np.float32)
                        hs = np.asarray(h_scroll[ur], dtype=np.float32)
                    else:
                        ha = np.empty(0, dtype=np.int64)
                        hr = hs = np.empty(0, dtype=np.float32)
                    all_rows = art_row[np.clip(ha, 0, n_art)] if len(ha) else np.empty(0, dtype=np.int64)
                    keep = all_rows != unknown if len(ha) else np.empty(0, dtype=bool)
                    h_rows = all_rows[keep]

                    # Match build.py: NaN becomes 0 before averaging, not skipped. nanmean
                    # would give a different number for the same user, a silent mismatch.
                    hr0 = np.nan_to_num(hr) if len(hr) else hr
                    hs0 = np.nan_to_num(hs) if len(hs) else hs
                    u_read = float(np.log1p(hr0.mean())) if len(hr0) else 0.0
                    u_scroll = float(hs0.mean()) if len(hs0) else 0.0

                    if len(h_rows):
                        uv = vectors[h_rows].mean(axis=0)
                        nrm = np.linalg.norm(uv)
                        uv = uv / nrm if nrm > 0 else uv
                    else:
                        uv = np.zeros(dim, dtype=np.float32)

                    # engage_sim is the same computation with read-time weights rather than
                    # uniform ones, which is what makes the pair a one-variable comparison.
                    if len(h_rows) and len(hr) >= len(ha):
                        w = np.log1p(np.clip(hr0[-HISTORY_LEN:][keep], 0, None))
                        if w.sum() <= 0:
                            w = np.ones(len(h_rows), dtype=np.float32)
                        ev = (vectors[h_rows] * w[:, None]).sum(0)
                        enrm = np.linalg.norm(ev)
                        ev = ev / enrm if enrm > 0 else uv
                    else:
                        ev = uv

                    share = {}
                    for r in h_rows:
                        c = category[r]
                        share[c] = share.get(c, 0) + 1
                    denom = len(h_rows) or 1

                    hset = set()
                    for r in h_rows:
                        hset |= ents[r]

                    cached = (uv, ev, share, denom, hset, u_read, u_scroll, float(len(ha)))
                    user_cache[uid] = cached

                uv, ev, share, denom, hset, u_read, u_scroll, n_hist = cached
                emb = vectors[rows_c] @ uv
                engage = vectors[rows_c] @ ev
                cat_match = np.array([share.get(category[r], 0) / denom for r in rows_c],
                                     dtype=np.float32)
                if hset:
                    ent = np.array([len(ents[r] & hset) / len(ents[r] | hset) if ents[r] else 0.0
                                    for r in rows_c], dtype=np.float32)
                else:
                    ent = np.zeros(n, dtype=np.float32)

                # Advance the sweep to this impression's timestamp.
                while p_hi < n_ev and ev_time[p_hi] < t:
                    a = ev_art[p_hi]
                    count6[a] += 1
                    count24[a] += 1
                    p_hi += 1
                t6 = t - np.timedelta64(int(POP_WINDOW_H * 3600), "s")
                while p_lo6 < p_hi and ev_time[p_lo6] < t6:
                    count6[ev_art[p_lo6]] -= 1
                    p_lo6 += 1
                t24 = t - np.timedelta64(24 * 3600, "s")
                while p_lo24 < p_hi and ev_time[p_lo24] < t24:
                    count24[ev_art[p_lo24]] -= 1
                    p_lo24 += 1
                safe = np.clip(cands, 0, n_art)
                e6 = count6[safe].astype(np.float32)
                e24 = count24[safe].astype(np.float32)

                feats = {
                    "emb": emb.astype(np.float32),
                    "age_hours": np.nan_to_num(ages, nan=-1.0).astype(np.float32),
                    "recency": decay.astype(np.float32),
                    "cat_match": cat_match,
                    "hist_len": np.full(n, n_hist, dtype=np.float32),
                    # build.py stores these as nan_to_num(...) and then takes a plain mean, so
                    # a NaN counts as 0 rather than being skipped. nanmean would skip it and
                    # give a different number for the same user: a silent train/serve mismatch.
                    "user_read": np.full(n, u_read, dtype=np.float32),
                    "user_scroll": np.full(n, u_scroll, dtype=np.float32),
                    "engage_sim": engage.astype(np.float32),
                    "emb_rank": rank_within(emb),
                    "ent_overlap": ent,
                    "n_cands": np.full(n, float(n), dtype=np.float32),
                    "exp_causal": e6,
                    "exp_24h": e24,
                    "exp_velocity": e6 / (e24 + 1.0),
                    "exp_rank": rank_within(e6),
                    "exp_rel_max": e6 / (float(e6.max()) + 1.0),
                }
                # Accumulate; predict once per batch. Calling booster.predict() per impression
                # meant 13.5M separate LightGBM invocations on 15x16 matrices, where per-call
                # overhead dwarfs the arithmetic: the first attempt managed 25,000 impressions
                # in over 10 minutes, projecting past 90 hours.
                buf_X.append(np.column_stack([feats[f] for f in names]))
                buf_len.append(n)
                buf_pos.append(row["row_pos"])
                buf_id.append(row["impression_id"])
                written += 1

            if buf_X:
                X = np.concatenate(buf_X, axis=0)
                all_scores = booster.predict(X)
                off = 0
                for ln, pos, iid in zip(buf_len, buf_pos, buf_id):
                    ranks = ",".join(str(int(r)) for r in ranks_from(all_scores[off:off + ln]))
                    lines[pos] = f"{iid} [{ranks}]\n"
                    off += ln
                buf_X.clear(); buf_len.clear(); buf_pos.clear(); buf_id.clear()
        done = min(offset + BATCH, total)
        print(f"  {done:,}/{total:,} ({100 * done / total:.1f}%)", flush=True)

    assert written == total, f"scored {written} of {total}"
    assert all(l is not None for l in lines), "a row position was never filled"
    with txt.open("w") as fh:
        fh.writelines(lines)
    archive = OUT / args.out
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(txt, arcname="predictions.txt")
    print(f"wrote {archive} ({archive.stat().st_size / 1e6:.1f} MB, {written:,} rows)")


if __name__ == "__main__":
    main()
