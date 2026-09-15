"""MIND-large Codabench submission scored by the re-ranker, not by cosine alone.

Runs on the cluster. Inputs are the A1 caches (behaviors with article ids already resolved to
row indices, and the encoded article vectors), plus news.tsv for categories and entities, plus
a compact impression_id/time table because the cached behaviors file dropped the timestamp and
the exposure features need it.

Eleven features, matching models/mind_small_submission.txt exactly. The list is read off the
booster rather than hardcoded, so train and serve cannot silently disagree.

    python -m src.pipeline.submit_mind_rerank --model models/mind_small_submission.txt
    python -m src.pipeline.submit_mind_rerank --model ... --limit 20000   # smoke test
"""

import argparse
import zipfile
from pathlib import Path

import lightgbm as lgb
import numpy as np
import polars as pl

ROOT = Path(__file__).resolve().parent.parent.parent
INTERIM = ROOT / "data/interim"
PROC = ROOT / "data/processed"
OUT = ROOT / "submissions"
BATCH = 100_000
HISTORY_LEN = 30
POP_WINDOW_H = 6.0


def rank_within(values: np.ndarray) -> np.ndarray:
    """Average rank inside one impression scaled to [0,1]. Mirrors features.build._rank_within."""
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
    """1 = best. Ties broken by position, which the scorer treats as arbitrary anyway."""
    order = np.argsort(-scores, kind="stable")
    out = np.empty(len(scores), dtype=np.int64)
    out[order] = np.arange(1, len(scores) + 1)
    return out


def build_exposure(cand_rows: pl.Series, times: np.ndarray, n_articles: int) -> list:
    """Sorted show-times per article row, from the test set's own in-view lists.

    Exposure, not clicks: Codabench withholds article_ids_clicked, so click popularity has no
    source here. Built once over the whole test set because a causal count needs every event
    before t, not only those in the current batch.
    """
    lengths = cand_rows.list.len().to_numpy().astype(np.int64)
    flat = cand_rows.explode().to_numpy().astype(np.int64)
    stamps = np.repeat(times, lengths)
    order = np.argsort(flat, kind="stable")
    flat, stamps = flat[order], stamps[order]
    out = [None] * (n_articles + 1)
    edges = np.flatnonzero(np.r_[True, flat[1:] != flat[:-1], True])
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        out[flat[lo]] = np.sort(stamps[lo:hi])
    return out


def count_before(arr, t, window_h):
    """Events strictly before t, optionally only within window_h. Cannot admit t itself."""
    if arr is None or len(arr) == 0:
        return 0.0
    hi = np.searchsorted(arr, t, side="left")
    if window_h is None:
        return float(hi)
    lo = np.searchsorted(arr, t - np.timedelta64(int(window_h * 3600), "s"), side="left")
    return float(hi - lo)


def entity_sets(root: Path, n_rows: int) -> list:
    """Entity surface forms per article row, parsed as pipeline/split.py does."""
    import json
    news = pl.read_csv(
        root / "news.tsv", separator="\t", has_header=False, quote_char=None,
        new_columns=["article_id", "category", "subcategory", "title", "abstract",
                     "url", "title_entities", "abstract_entities"],
    )
    sets = [set() for _ in range(n_rows + 1)]
    for i, (te, ae) in enumerate(zip(news["title_entities"], news["abstract_entities"])):
        found = set()
        for blob in (te, ae):
            if not blob or blob == "[]":
                continue
            try:
                for e in json.loads(blob):
                    label = e.get("Label")
                    if label:
                        found.add(label)
            except Exception:
                continue
        sets[i] = found
    return sets, news


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", required=True)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--out", default="mind_prediction.zip")
    args = ap.parse_args()

    booster = lgb.Booster(model_file=args.model)
    feature_names = booster.feature_name()
    print(f"model expects {len(feature_names)} features: {', '.join(feature_names)}")

    root = INTERIM / "MINDlarge_test/MINDlarge_test"
    vectors = np.load(PROC / "mindlarge_test_embeddings.npy").astype(np.float32)
    dim = vectors.shape[1]
    vectors = np.vstack([vectors, np.zeros((1, dim), dtype=np.float32)])
    unknown = len(vectors) - 1
    print(f"{len(vectors) - 1:,} articles, dim {dim}")

    ents, news = entity_sets(root, unknown)
    category = news["category"].to_list() + ["<unk>"]
    print(f"entities for {sum(1 for s in ents if s):,} articles")

    behaviors = pl.read_parquet(PROC / "mindlarge_test_behaviors.parquet")
    times_tbl = pl.read_parquet(PROC / "mind_times.parquet")
    behaviors = behaviors.join(times_tbl, on="impression_id", how="left")
    assert behaviors["time"].null_count() == 0, "some impressions have no timestamp"
    if args.limit:
        behaviors = behaviors.head(args.limit)
    total = behaviors.height
    print(f"{total:,} impressions")

    all_times = behaviors["time"].to_numpy()
    print("building exposure index over the whole test set")
    exposure = build_exposure(behaviors["cand_rows"], all_times, unknown)
    print(f"  exposure for {sum(1 for a in exposure if a is not None):,} articles")

    OUT.mkdir(exist_ok=True)
    # Name the intermediate after the archive, not a fixed path: otherwise a --limit
    # smoke run overwrites a completed full run's text file. A partial file written to
    # the real upload path is this project's most expensive recorded mistake (0.84% of
    # the test set, scored 0.5012, looked like a valid submission and a bad model).
    txt = OUT / (Path(args.out).stem + "__prediction.txt")
    written = 0
    with txt.open("w") as fh:
        for offset in range(0, total, BATCH):
            batch = behaviors.slice(offset, min(BATCH, total - offset))
            for row in batch.iter_rows(named=True):
                cands = np.asarray(row["cand_rows"], dtype=np.int64)
                hist = np.asarray(row["history_rows"], dtype=np.int64)
                hist = hist[hist != unknown][-HISTORY_LEN:]
                t = np.datetime64(row["time"])
                n = len(cands)

                if len(hist):
                    uv = vectors[hist].mean(axis=0)
                    nrm = np.linalg.norm(uv)
                    uv = uv / nrm if nrm > 0 else uv
                else:
                    uv = np.zeros(dim, dtype=np.float32)
                emb = vectors[cands] @ uv

                hist_cats = [category[h] for h in hist]
                share = {}
                for c in hist_cats:
                    share[c] = share.get(c, 0) + 1
                denom = len(hist_cats) or 1
                cat_match = np.array([share.get(category[c], 0) / denom for c in cands],
                                     dtype=np.float32)

                hist_ents = set()
                for h in hist:
                    hist_ents |= ents[h]
                if hist_ents:
                    ent = np.array([
                        len(ents[c] & hist_ents) / len(ents[c] | hist_ents)
                        if ents[c] else 0.0 for c in cands], dtype=np.float32)
                else:
                    ent = np.zeros(n, dtype=np.float32)

                exp6 = np.array([count_before(exposure[c], t, POP_WINDOW_H) for c in cands],
                                dtype=np.float32)
                exp24 = np.array([count_before(exposure[c], t, 24.0) for c in cands],
                                 dtype=np.float32)

                feats = {
                    "emb": emb.astype(np.float32),
                    "cat_match": cat_match,
                    "hist_len": np.full(n, float(len(hist)), dtype=np.float32),
                    "emb_rank": rank_within(emb),
                    "ent_overlap": ent,
                    "n_cands": np.full(n, float(n), dtype=np.float32),
                    "exp_causal": exp6,
                    "exp_24h": exp24,
                    "exp_velocity": exp6 / (exp24 + 1.0),
                    "exp_rank": rank_within(exp6),
                    "exp_rel_max": exp6 / (float(exp6.max()) + 1.0),
                }
                X = np.column_stack([feats[f] for f in feature_names])
                scores = booster.predict(X)
                # Format is "<impression_id> [r1,r2,...]": one space after the id, no spaces
                # inside the list. numpy scalars must be cast, or numpy 2 writes
                # "np.int64(3)" into the file and the whole submission is rejected.
                ranks = ",".join(str(int(r)) for r in ranks_from(scores))
                fh.write(f"{row['impression_id']} [{ranks}]\n")
                written += 1
            print(f"  {min(offset + BATCH, total):,}/{total:,}", flush=True)

    assert written == total, f"wrote {written} of {total} rows"
    archive = OUT / args.out
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(txt, arcname="prediction.txt")
    print(f"wrote {archive} ({archive.stat().st_size / 1e6:.1f} MB, {written:,} rows)")


if __name__ == "__main__":
    main()
