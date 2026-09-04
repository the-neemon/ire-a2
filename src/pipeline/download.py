"""Download and extract the raw EB-NeRD and MIND bundles.

Idempotent: a bundle is skipped if its extract directory already holds a .done marker,
so re-running costs nothing.

    python -m src.pipeline.download
    python -m src.pipeline.download ebnerd_small
"""

import argparse
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent.parent / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"

EBNERD_BASE = "https://ebnerd-dataset.s3.eu-west-1.amazonaws.com"
EBNERD_BUNDLES = ("ebnerd_demo", "ebnerd_small", "ebnerd_testset", "articles_large_only")
# Article embeddings ship separately from the impression bundles, under an artifacts/ prefix,
# and each one covers the full article set (so they apply to demo as well as large).
EBNERD_ARTIFACTS = (
    "Ekstra_Bladet_contrastive_vector",
    "Ekstra_Bladet_word2vec",
    "Ekstra_Bladet_image_embeddings",
    "FacebookAI_xlm_roberta_base",
    "google_bert_base_multilingual_cased",
)

MIND_REPO = "yjw1029/MIND"
MIND_BUNDLES = (
    "MINDsmall_train",
    "MINDsmall_dev",
    "MINDlarge_train",
    "MINDlarge_dev",
    "MINDlarge_test",
)
MIND_GATE_URL = f"https://huggingface.co/datasets/{MIND_REPO}"

# Seconds without a byte arriving before a fetch is treated as dead rather than slow.
READ_TIMEOUT = 60

# Both EB-NeRD encoders the assignment names: word2vec is what the pipeline uses,
# bert_base_multilingual_cased is needed only to reproduce the ablation that chose it.
DEFAULT_BUNDLES = (
    "ebnerd_demo",
    "Ekstra_Bladet_word2vec",
    "google_bert_base_multilingual_cased",
    "MINDsmall_train",
    "MINDsmall_dev",
)


# One TCP connection to the EB-NeRD bucket is slow, and from some hosts it stalls at
# 0 B/s indefinitely. Measured 2026-09-04: 15.6 KB/s single-stream from the compute
# cluster, against megabytes/s from a laptop on a home connection. The bucket does
# honour Range requests, and throughput scales close to linearly with the number of
# concurrent ranges, so the fix is to ask for many slices at once rather than to retry
# a single stream that is not actually failing, just crawling.
PARALLEL_CONNECTIONS = 16
_MIN_PARALLEL_BYTES = 8 * 1024 * 1024   # below this the setup cost is not worth it


def _supports_ranges(url: str) -> "tuple[bool, int]":
    """Ask for one byte. A server that honours Range answers 206 with a Content-Range."""
    req = urllib.request.Request(url, headers={"Range": "bytes=0-0"})
    try:
        with urllib.request.urlopen(req, timeout=READ_TIMEOUT) as r:
            if r.status != 206:
                return False, 0
            # Content-Range looks like "bytes 0-0/84135301"; the total is after the slash.
            total = int(r.headers["Content-Range"].split("/")[1])
            return True, total
    except Exception:
        return False, 0


def _download_range(url: str, start: int, end: int, path: Path, index: int) -> int:
    req = urllib.request.Request(url, headers={"Range": f"bytes={start}-{end}"})
    with urllib.request.urlopen(req, timeout=READ_TIMEOUT) as r, open(path, "wb") as fh:
        shutil.copyfileobj(r, fh)
    return index


def _fetch_parallel(url: str, tmp: Path, total: int, connections: int) -> None:
    """Fetch `total` bytes as `connections` concurrent ranges, then concatenate in order."""
    import concurrent.futures

    parts_dir = tmp.parent / f"{tmp.name}.parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    size = -(-total // connections)          # ceiling division
    spans = [
        (i, i * size, min((i + 1) * size - 1, total - 1))
        for i in range(connections)
        if i * size < total
    ]
    if not spans:
        raise ValueError(f"nothing to fetch: total={total}, connections={connections}")
    print(f"  {total / 1e6:.0f} MB over {len(spans)} parallel ranges")
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(spans)) as pool:
            futures = [
                pool.submit(_download_range, url, a, b, parts_dir / f"{i:04d}", i)
                for i, a, b in spans
            ]
            done = 0
            for f in concurrent.futures.as_completed(futures):
                f.result()                    # re-raise inside the main thread
                done += 1
                print(f"\r  ranges complete: {done}/{len(spans)}", end="", flush=True)
        print()
        # Concatenate in index order. Order matters and as_completed does not preserve it.
        with open(tmp, "wb") as out:
            for i, _, _ in spans:
                with open(parts_dir / f"{i:04d}", "rb") as chunk:
                    shutil.copyfileobj(chunk, out)
        got = tmp.stat().st_size
        if got != total:
            raise OSError(f"assembled {got} bytes, expected {total}")
    finally:
        shutil.rmtree(parts_dir, ignore_errors=True)


def _fetch_ebnerd(name: str) -> Path:
    dest = RAW / "ebnerd" / f"{name}.zip"
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    prefix = "artifacts/" if name in EBNERD_ARTIFACTS else ""
    url = f"{EBNERD_BASE}/{prefix}{name}.zip"
    print(f"  downloading {url}")
    # Download to .part and rename only on success. rename is atomic, so an interrupted
    # download can never leave a truncated file that looks complete on the next run.
    tmp = dest.with_suffix(".zip.part")

    # Two independent failure modes on this bucket, so two fixes, kept together.
    # Throughput: one connection crawls (15.6 KB/s measured from the compute cluster),
    # and ranges scale close to linearly, so ask for many slices at once.
    # Liveness: a stalled connection never errors, it just stops, so every request
    # carries a per-read timeout and a dead transfer fails instead of hanging.
    ranged, total = _supports_ranges(url)
    if ranged and total >= _MIN_PARALLEL_BYTES:
        _fetch_parallel(url, tmp, total, PARALLEL_CONNECTIONS)
    else:
        with urllib.request.urlopen(url, timeout=READ_TIMEOUT) as response, open(tmp, "wb") as fh:
            # copyfileobj streams in chunks, so a 1.6 GB bundle never sits in memory at once.
            shutil.copyfileobj(response, fh)

    tmp.rename(dest)
    return dest


def _fetch_mind(name: str) -> Path:
    from huggingface_hub import hf_hub_download
    from huggingface_hub.errors import GatedRepoError, HfHubHTTPError

    print(f"  downloading {MIND_REPO}/{name}.zip")
    try:
        return Path(
            hf_hub_download(
                repo_id=MIND_REPO,
                repo_type="dataset",
                filename=f"{name}.zip",
                cache_dir=RAW / "mind",
            )
        )
    except (GatedRepoError, HfHubHTTPError) as exc:
        raise SystemExit(
            f"Could not fetch {name}.zip from the gated repo {MIND_REPO}.\n"
            f"Log in with `huggingface-cli login`, then open {MIND_GATE_URL} and click\n"
            f'"Agree and access repository" — access is granted automatically.\n'
            f"Original error: {exc}"
        ) from exc


def _extract(archive: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(dest)
    # The marker is written last, so it can only exist if extraction finished. This is what
    # `fetch` checks, which is what makes "one command rebuilds from raw" cheap to re-run.
    (dest / ".done").touch()


def fetch(name: str, force: bool = False) -> None:
    dest = INTERIM / name
    if (dest / ".done").exists() and not force:
        print(f"{name}: already extracted, skipping")
        return

    print(f"{name}:")
    if name in EBNERD_BUNDLES or name in EBNERD_ARTIFACTS:
        archive = _fetch_ebnerd(name)
    elif name in MIND_BUNDLES:
        archive = _fetch_mind(name)
    else:
        raise SystemExit(f"unknown bundle {name!r}")

    print(f"  extracting to {dest}")
    _extract(archive, dest)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundles", nargs="*", default=list(DEFAULT_BUNDLES))
    parser.add_argument("--force", action="store_true", help="re-extract even if done")
    args = parser.parse_args()

    for name in args.bundles:
        fetch(name, force=args.force)


if __name__ == "__main__":
    sys.exit(main())
