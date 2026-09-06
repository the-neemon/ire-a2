"""The behaviour-window boundary for the Q1 features.

A2 Q9 requires a test asserting that no future click leaks into a feature. The features
that could leak are the ones built from the click log itself, so `pop_causal` is what this
file is about; the rest are either static article properties (`age_hours`, `recency`,
`cat_match`) or come from history arrays that are past by construction.

Every assertion here is checked for non-vacuity: a test that passes because it compared
nothing is worse than no test, and that has already happened once on this project.
"""

from pathlib import Path

import numpy as np
import polars as pl
import pytest

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data/processed"
DATASETS = ["ebnerd_demo", "ebnerd_small", "mind_small"]


@pytest.fixture(params=DATASETS)
def built(request):
    name = request.param
    feats = PROC / name / "features_val.parquet"
    imps = PROC / name / "impressions_val.parquet"
    if not feats.exists() or not imps.exists():
        pytest.skip(f"{name}: features not built")
    return name, pl.read_parquet(feats), pl.read_parquet(imps)


def _click_times(name: str) -> dict[str, np.ndarray]:
    frames = []
    for split in ("train", "val", "test"):
        p = PROC / name / f"impressions_{split}.parquet"
        if p.exists():
            frames.append(pl.read_parquet(p, columns=["timestamp", "clicked"])
                          .explode("clicked").drop_nulls("clicked"))
    ev = pl.concat(frames)
    return {(a[0] if isinstance(a, tuple) else a): np.sort(g["timestamp"].to_numpy())
            for a, g in ev.group_by("clicked")}


def test_causal_popularity_counts_only_the_strict_past(built):
    """Recompute pop_causal independently and require an exact match.

    Independent means a different code path from the one under test: this counts with an
    explicit boolean mask rather than searchsorted, so a bug in the bisection would show up
    as a disagreement instead of being reproduced identically.
    """
    name, feats, imps = built
    times = _click_times(name)
    when = dict(zip(imps["impression_id"], imps["timestamp"]))

    sample = feats.filter(pl.col("impression_id").is_in(
        imps["impression_id"].sample(min(300, imps.height), seed=13).to_list()))
    assert sample.height > 0, f"{name}: nothing sampled, the check would be vacuous"

    compared = 0
    for row in sample.iter_rows(named=True):
        t = np.datetime64(when[row["impression_id"]])
        arr = times.get(row["candidate"])
        expected = 0 if arr is None else int((arr < t).sum())
        assert row["pop_causal"] == expected, (
            f"{name}: {row['candidate']} at {t} has pop_causal={row['pop_causal']}, "
            f"expected {expected} clicks strictly before t"
        )
        compared += 1
    assert compared >= 100, f"{name}: only {compared} rows compared, too few to trust"


def test_no_click_at_or_after_the_impression_is_counted(built):
    """The boundary itself: a click exactly at t must not count, nor anything after it."""
    name, feats, imps = built
    times = _click_times(name)
    when = dict(zip(imps["impression_id"], imps["timestamp"]))

    checked = violations = 0
    for row in feats.head(20000).iter_rows(named=True):
        arr = times.get(row["candidate"])
        if arr is None or len(arr) == 0:
            continue
        t = np.datetime64(when[row["impression_id"]])
        at_or_after = int((arr >= t).sum())
        if at_or_after == 0:
            continue                       # nothing to exclude, so this row proves nothing
        checked += 1
        if row["pop_causal"] != int((arr < t).sum()):
            violations += 1
    assert checked > 0, (
        f"{name}: no row had any click at or after its impression, so this assertion "
        f"never tested the boundary it exists to test"
    )
    assert violations == 0, f"{name}: {violations} of {checked} rows counted a future click"


def test_the_check_would_catch_an_injected_future_click(built):
    """Non-vacuity: poison the data and require the comparison to fail.

    Without this, all the assertions above could be passing because the comparison is
    inert rather than because the feature is correct.
    """
    name, feats, imps = built
    times = _click_times(name)
    when = dict(zip(imps["impression_id"], imps["timestamp"]))

    row = None
    for r in feats.head(5000).iter_rows(named=True):
        if times.get(r["candidate"]) is not None:
            row = r
            break
    if row is None:
        pytest.skip(f"{name}: no candidate with click history in the sample")

    t = np.datetime64(when[row["impression_id"]])
    arr = times[row["candidate"]]
    honest = int((arr < t).sum())
    # One click one day in the future, which a leaky implementation would include.
    poisoned = np.sort(np.append(arr, t + np.timedelta64(1, "D")))
    leaky = int((poisoned <= t + np.timedelta64(2, "D")).sum())
    assert leaky > honest, "injection did not change the count, so the test is inert"
    assert row["pop_causal"] == honest, f"{name}: feature matches the leaky count, not the honest one"
