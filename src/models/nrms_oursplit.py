"""NRMS on OUR temporal split, so the number is comparable to our own re-ranker.

The published benchmark script concatenates the provided train and validation blocks and
carves its own last-day validation out of that. Against our split that means it trains on
our train, our val AND our test, and early-stops on a slice of its own training window.
Its number is a faithful reproduction of their setup but cannot be compared to our
re-ranker's 0.7429 test AUC.

This driver instead: trains on impressions_train, early-stops on impressions_val, scores
impressions_test exactly once. Same model, same hparams, same document vectors, same
dataloader as the benchmark; only the data feed differs.

Output matches the re-ranker's flat schema so the eval harness reads both identically:
    impression_id Int64 | candidate String | label Int8 | score Float64

Run under srun/sbatch only. The login node is Python 3.6 and this venv is 3.10.
"""

import argparse
import datetime as dt
import json
from pathlib import Path

import numpy as np
import polars as pl
import tensorflow as tf

from ebrec.utils._constants import (
    DEFAULT_CLICKED_ARTICLES_COL,
    DEFAULT_HISTORY_ARTICLE_ID_COL,
    DEFAULT_IMPRESSION_ID_COL,
    DEFAULT_IMPRESSION_TIMESTAMP_COL,
    DEFAULT_INVIEW_ARTICLES_COL,
    DEFAULT_LABELS_COL,
    DEFAULT_USER_COL,
)
from ebrec.utils._behaviors import (
    add_prediction_scores,
    create_binary_labels_column,
    sampling_strategy_wu2019,
    truncate_history,
)
from ebrec.utils._articles import create_article_id_to_value_mapping
from ebrec.utils._polars import split_df_chunks
from ebrec.models.newsrec.dataloader import NRMSDataLoader, NRMSDataLoaderPretransform
from ebrec.models.newsrec.model_config import hparams_nrms_docvec, print_hparams
from ebrec.models.newsrec.nrms_docvec import NRMSDocVec


def per_impression_auc(df: pl.DataFrame) -> tuple[float, int, int]:
    """Mann-Whitney AUC inside each impression, averaged over impressions with both classes.

    Pooled AUC systematically overstates any feature that varies across impressions rather
    than within them, so the whole project reports this form.

    Vectorised through polars rather than looped per impression. The loop version took over
    four hours on 244,647 test impressions and had to be killed, while this returns in
    seconds; `rank("average")` also handles ties the same way the manual version did.
    """
    total = df["impression_id"].n_unique()
    d = df.with_columns(
        pl.col("score").rank("average").over("impression_id").alias("_r")
    )
    g = d.group_by("impression_id").agg(
        pl.col("label").sum().alias("_np"),
        pl.len().alias("_n"),
        (pl.col("_r") * pl.col("label")).sum().alias("_rs"),
    )
    g = g.filter((pl.col("_np") > 0) & (pl.col("_np") < pl.col("_n")))
    if not g.height:
        raise SystemExit("FATAL: no impression has both a positive and a negative")
    auc = ((g["_rs"] - g["_np"] * (g["_np"] + 1) / 2)
           / (g["_np"] * (g["_n"] - g["_np"]))).mean()
    return float(auc), g.height, total - g.height


def load_split(path: Path, history_size: int) -> pl.DataFrame:
    """Our processed impressions -> the column names and dtypes ebrec's dataloader wants.

    Article ids are String in our pipeline and Int32 in the document-vector parquet. The
    cast is the whole reason this function exists: `unknown_representation="zeros"` means a
    dtype mismatch would silently give every article a zero vector and train on noise
    without raising, which is exactly the class of vacuous result this project has already
    been bitten by four times.
    """
    df = pl.read_parquet(path).rename(
        {
            "timestamp": DEFAULT_IMPRESSION_TIMESTAMP_COL,
            "candidates": DEFAULT_INVIEW_ARTICLES_COL,
            "clicked": DEFAULT_CLICKED_ARTICLES_COL,
            "history": DEFAULT_HISTORY_ARTICLE_ID_COL,
        }
    )
    df = df.with_columns(
        pl.col(DEFAULT_INVIEW_ARTICLES_COL).list.eval(pl.element().cast(pl.Int32)),
        pl.col(DEFAULT_CLICKED_ARTICLES_COL).list.eval(pl.element().cast(pl.Int32)),
        pl.col(DEFAULT_HISTORY_ARTICLE_ID_COL).list.eval(pl.element().cast(pl.Int32)),
    )
    df = df.select(
        DEFAULT_IMPRESSION_ID_COL,
        DEFAULT_USER_COL,
        DEFAULT_IMPRESSION_TIMESTAMP_COL,
        DEFAULT_HISTORY_ARTICLE_ID_COL,
        DEFAULT_INVIEW_ARTICLES_COL,
        DEFAULT_CLICKED_ARTICLES_COL,
    ).pipe(
        truncate_history,
        column=DEFAULT_HISTORY_ARTICLE_ID_COL,
        history_size=history_size,
        padding_value=0,
        enable_warning=False,
    )
    return df


def assert_coverage(df: pl.DataFrame, mapping: dict, name: str, min_frac: float) -> None:
    """Hard-fail if the article ids do not actually hit the embedding table."""
    keys = set(mapping.keys())
    for col in (DEFAULT_INVIEW_ARTICLES_COL, DEFAULT_HISTORY_ARTICLE_ID_COL):
        ids = df[col].explode().drop_nulls().unique().to_list()
        ids = [i for i in ids if i != 0]
        if not ids:
            raise SystemExit(f"FATAL {name}/{col}: no article ids at all")
        hit = sum(1 for i in ids if i in keys)
        frac = hit / len(ids)
        print(f"  coverage {name}/{col}: {hit}/{len(ids)} = {frac:.4f}")
        if frac < min_frac:
            raise SystemExit(
                f"FATAL {name}/{col}: only {frac:.4f} of article ids are in the embedding "
                f"table (need >= {min_frac}). Every miss becomes a zero vector, so this "
                f"would train on noise and report a plausible wrong number."
            )


def score_split(model, df: pl.DataFrame, mapping: dict, batch_size: int,
                n_chunks: int) -> pl.DataFrame:
    """Score every candidate, eval_mode, and return the flat re-ranker schema.

    Labels are exploded positionally alongside candidates and scores rather than joined
    back on (impression_id, candidate): a join would fan out wherever a candidate repeats
    within an impression, and would silently produce more rows than candidates.
    """
    df = df.pipe(create_binary_labels_column)
    out = []
    for i, chunk in enumerate(split_df_chunks(df, n_chunks=n_chunks), start=1):
        print(f"    chunk {i}/{n_chunks}", flush=True)
        loader = NRMSDataLoader(
            behaviors=chunk,
            article_dict=mapping,
            unknown_representation="zeros",
            history_column=DEFAULT_HISTORY_ARTICLE_ID_COL,
            eval_mode=True,
            batch_size=batch_size,
        )
        scores = model.scorer.predict(loader, verbose=0)
        # In eval_mode the loader flattens every candidate in the batch, so predict returns
        # one score per candidate over the whole chunk. Check that count directly: an
        # earlier version compared list lengths after regrouping, which silently passed
        # because a null list length compares as null and the filter drops the row.
        n_expected = int(chunk[DEFAULT_INVIEW_ARTICLES_COL].list.len().sum())
        n_got = int(np.asarray(scores).reshape(-1).shape[0])
        if n_got != n_expected:
            raise SystemExit(
                f"FATAL chunk {i}: predict returned {n_got} scores for {n_expected} "
                f"candidates over {chunk.height} impressions"
            )
        scored = add_prediction_scores(chunk, np.asarray(scores).reshape(-1).tolist())
        null_scores = scored.filter(pl.col("scores").is_null()).height
        misaligned = scored.filter(
            pl.col("scores").list.len().fill_null(-1)
            != pl.col(DEFAULT_INVIEW_ARTICLES_COL).list.len()
        ).height
        if null_scores or misaligned:
            raise SystemExit(
                f"FATAL chunk {i}: {null_scores} null score lists, {misaligned} misaligned"
            )
        lens = scored.select(
            pl.col(DEFAULT_INVIEW_ARTICLES_COL).list.len().alias("n_inview"),
            pl.col(DEFAULT_LABELS_COL).list.len().alias("n_labels"),
            pl.col("scores").list.len().alias("n_scores"),
        )
        off = lens.filter(
            (pl.col("n_inview") != pl.col("n_labels"))
            | (pl.col("n_inview") != pl.col("n_scores"))
        )
        if off.height:
            raise SystemExit(
                f"FATAL chunk {i}: {off.height} rows with unequal list lengths\n"
                f"{off.head(5)}\ntotals: inview={lens['n_inview'].sum()} "
                f"labels={lens['n_labels'].sum()} scores={lens['n_scores'].sum()}"
            )
        # Explode each column as its own Series rather than a multi-column explode:
        # polars 0.20 rejects the multi-column form here even though every row's three
        # lists are the same length (asserted above) and rechunking does not help.
        n = scored[DEFAULT_INVIEW_ARTICLES_COL].list.len()
        flat = pl.DataFrame(
            {
                DEFAULT_IMPRESSION_ID_COL: scored.select(
                    pl.col(DEFAULT_IMPRESSION_ID_COL)
                    .repeat_by(pl.col(DEFAULT_INVIEW_ARTICLES_COL).list.len())
                    .explode()
                ).to_series(),
                "candidate": scored[DEFAULT_INVIEW_ARTICLES_COL].explode().cast(pl.Utf8),
                "label": scored[DEFAULT_LABELS_COL].explode().cast(pl.Int8),
                "score": scored["scores"].explode().cast(pl.Float64),
            }
        )
        if flat.height != int(n.sum()):
            raise SystemExit(
                f"FATAL chunk {i}: flattened to {flat.height} rows, expected {int(n.sum())}"
            )
        out.append(flat)
        tf.keras.backend.clear_session()
    return pl.concat(out).select(DEFAULT_IMPRESSION_ID_COL, "candidate", "label", "score")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--processed", required=True, help="data/processed/<dataset>")
    p.add_argument("--doc-vectors", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--seed", type=int, default=16)
    p.add_argument("--history-size", type=int, default=20)
    p.add_argument("--title-size", type=int, default=768)
    p.add_argument("--npratio", type=int, default=4)
    p.add_argument("--epochs", type=int, default=10)
    p.add_argument("--bs-train", type=int, default=32)
    p.add_argument("--bs-eval", type=int, default=32)
    p.add_argument("--n-chunks", type=int, default=10)
    p.add_argument("--train-fraction", type=float, default=1.0)
    p.add_argument("--min-coverage", type=float, default=0.95)
    p.add_argument("--score-test", action="store_true",
                   help="Score the test split. Omit while selecting; the rule is score test once.")
    args = p.parse_args()

    tf.keras.utils.set_random_seed(args.seed)
    proc = Path(args.processed)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    print("=== document vectors ===", flush=True)
    df_articles = pl.read_parquet(args.doc_vectors)
    mapping = create_article_id_to_value_mapping(
        df=df_articles, value_col=df_articles.columns[-1]
    )
    print(f"  {len(mapping)} articles, dim {len(next(iter(mapping.values())))}")

    print("=== splits ===", flush=True)
    splits = {}
    for name in ("train", "val", "test"):
        splits[name] = load_split(proc / f"impressions_{name}.parquet", args.history_size)
        ts = splits[name][DEFAULT_IMPRESSION_TIMESTAMP_COL]
        print(f"  {name}: {splits[name].height} impressions, {ts.min()} .. {ts.max()}")

    # Splits are temporal, never random: train strictly precedes val strictly precedes test.
    t_max = splits["train"][DEFAULT_IMPRESSION_TIMESTAMP_COL].max()
    v_min = splits["val"][DEFAULT_IMPRESSION_TIMESTAMP_COL].min()
    v_max = splits["val"][DEFAULT_IMPRESSION_TIMESTAMP_COL].max()
    s_min = splits["test"][DEFAULT_IMPRESSION_TIMESTAMP_COL].min()
    if not (t_max < v_min and v_max < s_min):
        raise SystemExit(f"FATAL: splits overlap in time: train<={t_max}, val {v_min}..{v_max}, test>={s_min}")
    print("  temporal order asserted: train < val < test")

    for name in ("train", "val"):
        assert_coverage(splits[name], mapping, name, args.min_coverage)

    # Train and early-stopping sets both use Wu2019 negative sampling, as the benchmark
    # does, so the loss and the monitored val_auc stay comparable to theirs.
    df_train = (
        splits["train"]
        .sample(fraction=args.train_fraction, shuffle=True, seed=args.seed)
        .pipe(sampling_strategy_wu2019, npratio=args.npratio, shuffle=True,
              with_replacement=True, seed=args.seed)
        .pipe(create_binary_labels_column)
    )
    df_es = (
        splits["val"]
        .pipe(sampling_strategy_wu2019, npratio=args.npratio, shuffle=True,
              with_replacement=True, seed=args.seed)
        .pipe(create_binary_labels_column)
    )
    print(f"  after sampling: train {df_train.height}, early-stop {df_es.height}", flush=True)

    hp = hparams_nrms_docvec
    hp.title_size = args.title_size
    hp.history_size = args.history_size
    print_hparams(hp)

    weights = out / "weights.weights.h5"
    model = NRMSDocVec(hparams=hp, seed=args.seed)
    model.model.compile(optimizer=model.model.optimizer, loss=model.model.loss, metrics=["AUC"])

    train_loader = NRMSDataLoaderPretransform(behaviors=df_train, article_dict=mapping,
                                  unknown_representation="zeros",
                                  history_column=DEFAULT_HISTORY_ARTICLE_ID_COL,
                                  eval_mode=False, batch_size=args.bs_train)
    es_loader = NRMSDataLoaderPretransform(behaviors=df_es, article_dict=mapping,
                               unknown_representation="zeros",
                               history_column=DEFAULT_HISTORY_ARTICLE_ID_COL,
                               eval_mode=False, batch_size=args.bs_train)

    print("=== training ===", flush=True)
    model.model.fit(
        train_loader,
        validation_data=es_loader,
        epochs=args.epochs,
        callbacks=[
            tf.keras.callbacks.EarlyStopping(monitor="val_auc", mode="max", patience=4,
                                             restore_best_weights=True),
            tf.keras.callbacks.ModelCheckpoint(filepath=str(weights), monitor="val_auc",
                                               mode="max", save_best_only=True,
                                               save_weights_only=True, verbose=1),
            tf.keras.callbacks.ReduceLROnPlateau(monitor="val_auc", mode="max", factor=0.2,
                                                 patience=2, min_lr=1e-6),
        ],
    )
    model.model.load_weights(str(weights))

    results = {"seed": args.seed, "history_size": args.history_size,
               "train_fraction": args.train_fraction, "npratio": args.npratio}
    to_score = ["val"] + (["test"] if args.score_test else [])
    for name in to_score:
        print(f"=== scoring {name} (full, no negative sampling) ===", flush=True)
        flat = score_split(model, splits[name], mapping, args.bs_eval, args.n_chunks)
        dest = out / f"nrms_full_{name}.parquet"
        flat.write_parquet(dest)
        auc, n_scored, n_skipped = per_impression_auc(flat)
        results[name] = {"per_impression_auc": auc, "impressions_scored": n_scored,
                         "impressions_skipped_single_class": n_skipped, "rows": flat.height}
        print(f"  {name} per-impression AUC = {auc:.4f} "
              f"({n_scored} scored, {n_skipped} skipped single-class)", flush=True)
        print(f"  wrote {dest}")

    (out / "nrms_results.json").write_text(json.dumps(results, indent=2, default=str))
    print(json.dumps(results, indent=2, default=str))
    print("NRMS_OURSPLIT_DONE")


if __name__ == "__main__":
    main()
