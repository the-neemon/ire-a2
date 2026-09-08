"""Structural validation of a Codabench submission zip, offline, before upload.

MIND allows one submission per day and EB-NeRD's scoring takes hours, so a malformed file
costs a day rather than a retry. Everything checkable without labels is checked here.

The failure this exists to prevent is not a crash. It is a file that is well-formed and
*wrong*: ranks are positional against the test file's candidate order, so a submission whose
rows are correctly ranked but ordered differently, or whose per-row length disagrees with the
pool it describes, scores as a plausible bad model rather than erroring. A previous submission
on this project covered 0.84% of the test set and scored 0.5012, exactly random.

    python -m src.submission.validate mind submissions/mind_prediction.zip
    python -m src.submission.validate ebnerd submissions/SMOKE-50000-ebnerd_predictions.zip

Exit code is non-zero if any check fails, so it can gate an upload from a Makefile.
"""

import argparse
import sys
import zipfile
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parent.parent.parent
INTERIM = ROOT / "data/interim"
PROC = ROOT / "data/processed"

# The inner filename differs between the two competitions and nothing else does.
EXPECTED_NAME = {"mind": "prediction.txt", "ebnerd": "predictions.txt"}


def truth_rows(target: str) -> tuple[list[int], list[int]]:
    """(impression_id, candidate count) per row of the official test file, in file order."""
    if target == "mind":
        cache = PROC / "mindlarge_test_behaviors.parquet"
        if cache.exists():
            df = pl.read_parquet(cache)
            ids = df["impression_id"].cast(pl.Int64).to_list()
            col = "impressions" if "impressions" in df.columns else df.columns[-1]
            n = [len(str(s).split()) for s in df[col].to_list()]
            return ids, n
        path = INTERIM / "MINDlarge_test/MINDlarge_test/behaviors.tsv"
        df = pl.read_csv(path, separator="\t", has_header=False, quote_char=None,
                         new_columns=["impression_id", "user_id", "time", "history", "impressions"])
        return (df["impression_id"].cast(pl.Int64).to_list(),
                [len(s.split()) for s in df["impressions"].to_list()])

    # behaviors.parquet is nested under test/ in this bundle, matching what
    # src.pipeline.submit.stream_ebnerd reads. Kept in step with it deliberately: a
    # validator that reads a different file from the writer validates nothing.
    root = INTERIM / "ebnerd_testset/ebnerd_testset"
    df = pl.read_parquet(root / "test/behaviors.parquet",
                         columns=["impression_id", "article_ids_inview"])
    return (df["impression_id"].cast(pl.Int64).to_list(),
            df["article_ids_inview"].list.len().to_list())


def check(target: str, zip_path: Path, limit: int | None) -> list[str]:
    problems: list[str] = []
    inner = EXPECTED_NAME[target]

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        if names != [inner]:
            problems.append(
                f"zip contains {names!r}; the guidelines require exactly ['{inner}'] "
                "with no folders and no __MACOSX"
            )
        member = inner if inner in names else (names[0] if names else None)
        if member is None:
            return problems + ["zip is empty"]
        body = zf.read(member).decode()

    lines = [ln for ln in body.split("\n") if ln.strip()]
    ids, counts = truth_rows(target)
    if limit:
        ids, counts = ids[:limit], counts[:limit]

    if len(lines) != len(ids):
        problems.append(f"{len(lines):,} rows written against {len(ids):,} in the test file")

    # Row order is the trap: ranks are positional against the test file, so a correct
    # ranking in the wrong order is silently wrong rather than invalid.
    mismatched = bad_len = bad_perm = 0
    first_bad = None
    for i, line in enumerate(lines[:len(ids)]):
        head, _, rest = line.partition(" ")
        try:
            got_id = int(head)
        except ValueError:
            problems.append(f"row {i}: impression id {head!r} is not an integer")
            break
        if got_id != ids[i]:
            mismatched += 1
            first_bad = first_bad if first_bad is not None else (i, got_id, ids[i])
            continue
        ranks = rest.strip().strip("[]")
        parts = [p for p in ranks.split(",") if p != ""]
        if len(parts) != counts[i]:
            bad_len += 1
            continue
        try:
            values = sorted(int(p) for p in parts)
        except ValueError:
            bad_perm += 1
            continue
        # Every rank in 1..n exactly once. A repeated or skipped rank is not a ranking.
        if values != list(range(1, counts[i] + 1)):
            bad_perm += 1

    if mismatched:
        i, got, want = first_bad
        problems.append(
            f"{mismatched:,} rows have the wrong impression id, first at row {i} "
            f"(wrote {got}, test file has {want}). Row ORDER must match the test file."
        )
    if bad_len:
        problems.append(f"{bad_len:,} rows have a rank count that disagrees with the candidate pool")
    if bad_perm:
        problems.append(f"{bad_perm:,} rows are not a permutation of 1..n")
    return problems


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("target", choices=list(EXPECTED_NAME))
    ap.add_argument("zip_path", type=Path)
    ap.add_argument("--limit", type=int,
                    help="validate against the first N test rows (for a --limit smoke file)")
    args = ap.parse_args()

    print(f"validating {args.zip_path.name} against the {args.target} test file")
    problems = check(args.target, args.zip_path, args.limit)
    if problems:
        print("\nFAILED:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    print("  OK: filename, zip contents, row count, row order, rank permutations all valid")


if __name__ == "__main__":
    main()
