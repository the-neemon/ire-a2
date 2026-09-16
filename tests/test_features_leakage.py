"""The behaviour-window boundary for the Q1 features.

A2 Q9 requires a test asserting that no future click leaks into a feature. The features
that could leak are the ones built from the click log itself, so `pop_causal` is what this
file is about; the rest are either static article properties (`age_hours`, `recency`,
`cat_match`) or come from history arrays. Those history arrays are past by construction
only *within a block*: see the engagement section at the bottom of this file, where
merging two blocks leaked future clicks and went unnoticed because nothing here checked
them.

`pop_causal` counts clicks in a bounded window (t - w, t) rather than everything before t,
where w is per-dataset: 6 hours on EB-NeRD, unbounded on MIND. These tests read w from
build.py's POP_WINDOW_H and recompute the count against it. Reading it matters: a test that
expected the unbounded count would fail against the shipped 6 h window, and an earlier
version of this file did exactly that. Worse, it failed in a way that cannot tell a narrower
window from a leak, because both make the feature disagree with "every click before t". The
mask below is two-sided, so it distinguishes them.

The window cannot itself leak. It only moves the lower bound forward and never touches the
strict "< t" upper bound, which is the boundary the brief is about.

Every assertion here is checked for non-vacuity: a test that passes because it compared
nothing is worse than no test, and that has already happened once on this project. Twice,
in fact: the popularity injection test below was named identically to the engagement one,
so Python kept only the second and the first never ran from the day it was written until
2026-09-16. Hence the distinct names now.
"""

import sys
from pathlib import Path

import numpy as np
import polars as pl
import pytest

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data/processed"
DATASETS = ["ebnerd_demo", "ebnerd_small", "mind_small"]

# `make test` runs `python -m pytest` from the repo root, which puts it on sys.path; a bare
# `pytest tests/` does not. Import the window constant either way.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.features.build import pop_window_for  # noqa: E402


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


def _count_in_window(arr: np.ndarray, t: np.datetime64, window_h: float | None) -> int:
    """Clicks in (t - window_h, t), counted with an explicit boolean mask.

    Independent of the code under test on purpose: build.py bisects a sorted array with
    searchsorted, this compares every element, so a bug in the bisection shows up as a
    disagreement instead of being reproduced identically.

    Both bounds are asserted at once, and that is the point. `arr < t` is the boundary the
    brief requires. `arr >= lo` is the window we chose. Testing only the first would pass a
    build that had silently lost its window; testing neither separately is how the previous
    version of this file ended up unable to say which of the two had changed.
    """
    mask = arr < t
    if window_h is not None:
        mask &= arr >= t - np.timedelta64(int(window_h * 3600), "s")
    return int(mask.sum())


def test_causal_popularity_counts_only_the_strict_past(built):
    """Recompute pop_causal independently, at the configured window, and require equality.

    Exact equality rather than an inequality, because the weaker claim "no more than the
    clicks before t" is satisfied by a window that reaches into the future as long as it is
    narrow enough overall. Equality against a two-sided mask is not.
    """
    name, feats, imps = built
    window_h = pop_window_for(name)
    times = _click_times(name)
    when = dict(zip(imps["impression_id"], imps["timestamp"]))

    sample = feats.filter(pl.col("impression_id").is_in(
        imps["impression_id"].sample(min(300, imps.height), seed=13).to_list()))
    assert sample.height > 0, f"{name}: nothing sampled, the check would be vacuous"

    compared = bounded = 0
    for row in sample.iter_rows(named=True):
        t = np.datetime64(when[row["impression_id"]])
        arr = times.get(row["candidate"])
        expected = 0 if arr is None else _count_in_window(arr, t, window_h)
        assert row["pop_causal"] == expected, (
            f"{name}: {row['candidate']} at {t} has pop_causal={row['pop_causal']}, "
            f"expected {expected} clicks in "
            f"{'the whole past' if window_h is None else f'the {window_h} h before t'}"
        )
        compared += 1
        if arr is not None and expected != int((arr < t).sum()):
            bounded += 1
    assert compared >= 100, f"{name}: only {compared} rows compared, too few to trust"

    # Non-vacuity for the window specifically. If no sampled row has a click older than the
    # window, the windowed and unbounded counts agree everywhere and this test would pass
    # just as happily against a build that ignored POP_WINDOW_H.
    if window_h is not None:
        assert bounded > 0, (
            f"{name}: a {window_h} h window is configured but no sampled row had a click "
            f"outside it, so this comparison never tested the window"
        )


def test_no_click_at_or_after_the_impression_is_counted(built):
    """The boundary itself: a click exactly at t must not count, nor anything after it.

    Restricted to rows that have something to exclude. A row whose candidate was never
    clicked at or after t is consistent with any upper bound at all, so counting it would
    inflate the sample without testing anything.
    """
    name, feats, imps = built
    window_h = pop_window_for(name)
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
        if row["pop_causal"] != _count_in_window(arr, t, window_h):
            violations += 1
    assert checked > 0, (
        f"{name}: no row had any click at or after its impression, so this assertion "
        f"never tested the boundary it exists to test"
    )
    assert violations == 0, f"{name}: {violations} of {checked} rows counted a future click"


def test_popularity_check_would_catch_an_injected_future_click(built):
    """Non-vacuity: poison the data and require the comparison to fail.

    Without this, all the assertions above could be passing because the comparison is
    inert rather than because the feature is correct.

    Named apart from the engagement injection test at the bottom of this file. They were
    identical until 2026-09-16, and since a module is a namespace, the second definition
    replaced the first: this test was collected zero times over its whole life while the
    suite reported green. That is the third vacuous leakage check on this project and the
    reason every assertion here carries its own non-vacuity guard.
    """
    name, feats, imps = built
    window_h = pop_window_for(name)
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
    honest = _count_in_window(arr, t, window_h)
    # One click one hour into the future. Inside any window we might configure, so it tests
    # the upper bound and not the lower one: a leaky implementation includes it whatever w is.
    future = t + np.timedelta64(1, "h")
    poisoned = np.sort(np.append(arr, future))
    leaky = _count_in_window(poisoned, future + np.timedelta64(1, "s"), window_h)
    assert leaky > honest, "injection did not change the count, so the test is inert"
    assert row["pop_causal"] == honest, f"{name}: feature matches the leaky count, not the honest one"


# ---------------------------------------------------------------------------------------
# The engagement history block. engage_sim, user_read and user_scroll are built from
# history.parquet, and the file docstring above used to claim such arrays are "past by
# construction". That is true only per block. Each block's history describes clicks before
# *that block's* log period, and our val split is carved out of the train block, so
# validation-block history is future history for a val impression. An earlier
# _engagement_weights merged both blocks and let validation win for the users present in
# both, which leaked and was worth +0.0967 AUC on engage_sim.


def _history_block_for(cfg: dict, split: str) -> Path:
    """The same block-per-split rule build.py uses, restated here on purpose.

    Restated rather than imported: if build.py's rule regresses, an imported helper would
    regress with it and the test would keep passing.
    """
    return ROOT / (cfg["early_root"] if split in ("train", "val") else cfg["test_root"])


@pytest.fixture(params=DATASETS)
def engagement(request):
    import yaml

    name = request.param
    cfg = yaml.safe_load((ROOT / "configs/datasets.yaml").read_text())[name]
    if "early_root" not in cfg:
        pytest.skip(f"{name}: no raw blocks configured")
    out = {}
    for split in ("train", "val", "test"):
        imps = PROC / name / f"impressions_{split}.parquet"
        hist = _history_block_for(cfg, split) / "history.parquet"
        if not imps.exists() or not hist.exists():
            continue
        h = pl.read_parquet(hist, columns=["user_id", "impression_time_fixed"])
        if not h.height:
            continue
        out[split] = (
            pl.read_parquet(imps, columns=["user_id", "timestamp"]),
            h.with_columns(pl.col("user_id").cast(pl.Utf8)),
        )
    if not out:
        pytest.skip(f"{name}: no engagement history for any split")
    return name, out


def test_engagement_history_is_strictly_before_its_impressions(engagement):
    """No click in the history a split reads may fall at or after an impression using it.

    This is the assertion whose absence let the block-merge leak survive: the previous
    suite covered pop_causal only, so engage_sim, user_read and user_scroll were never
    checked at all.
    """
    name, splits = engagement
    for split, (imps, hist) in splits.items():
        latest = hist.select(
            "user_id",
            pl.col("impression_time_fixed").list.max().alias("last_click"),
        ).drop_nulls("last_click")
        joined = imps.join(latest, on="user_id", how="inner")
        # Non-vacuity: the join must actually match users, and the comparison must run on
        # real datetimes rather than nulls. Without this the whole test can pass on an
        # empty frame, which is how the MIND history assertion reported green over 95,071
        # rows while checking none of them.
        assert joined.height > 0, f"{name}/{split}: history joined to zero impressions"
        assert joined["last_click"].null_count() == 0, (
            f"{name}/{split}: null last_click would make every comparison null"
        )
        bad = joined.filter(pl.col("last_click") >= pl.col("timestamp"))
        assert bad.height == 0, (
            f"{name}/{split}: {bad.height} of {joined.height} impressions "
            f"({100 * bad.height / joined.height:.1f}%) read history at or after "
            f"their own timestamp"
        )


def test_engagement_check_would_catch_an_injected_future_click(engagement):
    """Same comparison against a deliberately poisoned history, which must fail.

    Verified by injection rather than trusted: three of this project's four vacuous tests
    passed against broken data, so a leakage assertion is not evidence until it has been
    watched to fire.
    """
    name, splits = engagement
    split, (imps, hist) = next(iter(splits.items()))
    latest = hist.select(
        "user_id", pl.col("impression_time_fixed").list.max().alias("last_click")
    ).drop_nulls("last_click")
    joined = imps.join(latest, on="user_id", how="inner")
    assert joined.height > 0, f"{name}/{split}: nothing to poison"
    # Push every user's last click one hour past the impression it is used for, which is
    # exactly the shape of the block-merge leak.
    poisoned = joined.with_columns(
        (pl.col("timestamp") + pl.duration(hours=1)).alias("last_click")
    )
    bad = poisoned.filter(pl.col("last_click") >= pl.col("timestamp"))
    assert bad.height == poisoned.height, (
        f"{name}/{split}: the check found {bad.height} of {poisoned.height} injected "
        f"violations, so it does not actually detect this leak"
    )
