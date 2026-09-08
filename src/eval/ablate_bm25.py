"""Paired A/B comparison of two BM25 configurations, on identical impressions.

The eval harness in `src.eval.run` answers "how good is the shipped system"; this answers
"is variant B different from variant A, and by how much" — which is the question
docs/ABLATIONS.md is a ledger of. It exists as its own entry point because a paired
bootstrap needs both systems' *per-impression* metric vectors at once, and `run` only ever
holds one configuration of BM25 and only reports aggregates.

What it does, per variant: build the index (timed), score the split, then reduce the
scores to one number per impression per metric and throw the scores away. Only those
vectors are held to the end, so comparing N variants costs N index builds but roughly one
variant's memory.

Two metric families, because they answer different questions and have disagreed before:

  re-rank    AUC / MRR / nDCG@k over the candidate pool the log actually showed.
             This is what the leaderboards score.
  retrieval  recall@K over the whole catalogue, ignoring the pool.
             This is what candidate generation is judged on, and a change can move it
             the opposite way to AUC — a smaller index can rank a shown pool better while
             surfacing fewer of the right articles from 20k.

    python -m src.eval.ablate_bm25 mind_small --ablation fields   --splits val test
    python -m src.eval.ablate_bm25 mind_small --ablation stemming --splits val test

`--ablation` names a pair defined in ABLATIONS below; `--variant` builds one ad hoc:

    python -m src.eval.ablate_bm25 ebnerd_small --variant stem:stem=on \
        --variant no_stem:stem=off

The FIRST variant named is the baseline; every later one is reported as a delta against
it. Writes results/ablation_bm25_<dataset>_<split>.{md,json}.
"""

import argparse
import json
import shutil
from pathlib import Path

import numpy as np
import polars as pl
import yaml

from src.eval import bootstrap, metrics
from src.retrieval import bm25 as bm25_stage

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG = ROOT / "configs/datasets.yaml"
PROC = ROOT / "data/processed"
RESULTS = ROOT / "results"

RANK_METRICS = ("auc", "mrr", "ndcg@5", "ndcg@10")
RECALL_KS = (50, 100, 200)


# The two ablations the A2 queue actually asks for (docs/ABLATIONS.md #6 and #7), as named
# pairs. Spelling them out here rather than retyping --variant twice means the baseline and
# the arm cannot drift apart between runs, and that a re-run months later reproduces the same
# comparison from one word. --variant stays for anything ad hoc.
ABLATIONS = {
    "fields": ["title_abstract:fields=title_abstract", "title:fields=title"],
    "stemming": ["stem:stem=on", "no_stem:stem=off"],
}


def parse_variant(spec: str) -> tuple[str, dict]:
    """`name:key=value,key=value` -> (name, overrides). Only the two ablated knobs."""
    name, _, rest = spec.partition(":")
    overrides = {}
    for item in filter(None, rest.split(",")):
        key, _, value = item.partition("=")
        if key == "fields":
            if value not in bm25_stage.FIELDS:
                raise SystemExit(f"unknown fields {value!r}; pick from {list(bm25_stage.FIELDS)}")
            overrides["fields"] = value
        elif key == "stem":
            if value not in ("on", "off"):
                raise SystemExit(f"stem must be on or off, got {value!r}")
            overrides["stem"] = value == "on"
        else:
            raise SystemExit(f"unknown variant key {key!r}; expected fields or stem")
    return name, overrides


def score_variant(dataset: str, cfg: dict, name: str, overrides: dict,
                  splits: list[str]) -> tuple[dict, dict]:
    """Run one configuration end to end. Returns (per-split metric vectors, cost)."""
    variant_cfg = {**cfg, **{k: v for k, v in overrides.items() if k != "fields"}}
    fields = bm25_stage.FIELDS[overrides.get("fields", "title_abstract")]
    out_dir = PROC / dataset / "ablation" / name

    timings = bm25_stage.run(dataset, variant_cfg, fields, splits, out_dir)

    per_split = {}
    for split in splits:
        impressions = pl.read_parquet(PROC / dataset / f"impressions_{split}.parquet")
        # Join rather than trust row order: the parquet was written by a separate stage and
        # a silent misalignment would score one user's ranking against another's clicks.
        scored = impressions.join(
            pl.read_parquet(out_dir / f"bm25_{split}.parquet"), on="impression_id"
        ).join(
            pl.read_parquet(out_dir / f"retrieval_{split}.parquet"), on="impression_id"
        )
        labels = [
            np.fromiter((c in set(k) for c in cand), bool, len(cand))
            for cand, k in zip(scored["candidates"].to_list(), scored["clicked"].to_list())
        ]
        scores = [np.asarray(v, dtype=np.float64) for v in scored["bm25"].to_list()]
        values, keep = metrics.per_impression(scores, labels)
        # `retrieved` stays a Polars Series all the way into recall_at_k: materialising
        # 245k x 200 ids as Python lists peaks at ~5 GB and OOMs this machine.
        values.update({
            f"recall@{k}": vals
            for k, vals in metrics.recall_at_k(
                scored["retrieved"], scored["clicked"], RECALL_KS, keep
            ).items()
        })
        per_split[split] = {
            "values": values,
            "impression_ids": scored["impression_id"].to_numpy()[keep],
        }
    return per_split, timings


def compare(baseline: str, variants: dict, split: str) -> dict:
    """Every variant against the baseline, paired on the impressions both scored."""
    base = variants[baseline][split]
    rows = {}
    for name, data in variants.items():
        if name == baseline:
            continue
        # Both variants score the same impressions in the same order — same split file,
        # same `keep` rule — but assert it rather than assume, because a paired bootstrap
        # on misaligned vectors returns a confident and meaningless interval.
        assert np.array_equal(base["impression_ids"], data[split]["impression_ids"]), (
            f"{name} and {baseline} scored different impressions on {split}; "
            "the paired comparison would be meaningless"
        )
        rows[name] = {}
        for metric in RANK_METRICS + tuple(f"recall@{k}" for k in RECALL_KS):
            a, b = data[split]["values"][metric], base["values"][metric]
            mean, lo, hi, sig = bootstrap.paired(a, b)
            rows[name][metric] = {
                "baseline": float(b.mean()), "variant": float(a.mean()),
                "delta": mean, "lo": lo, "hi": hi, "significant": sig,
            }
    return rows


def render(report: dict) -> str:
    out = [f"# BM25 ablation — {report['dataset']} / {report['split']}", "",
           f"{report['n_impressions']:,} impressions scored (all-clicked and none-clicked "
           "pools carry no ranking signal and are dropped by the harness).", "",
           f"Baseline: **{report['baseline']}**. Every delta below is paired on the same "
           "impressions and the same 1,000 bootstrap resamples, so a difference counts "
           "only if its 95% CI excludes zero.", ""]

    out += ["## Absolute", "", "| variant | " + " | ".join(report["metrics"]) + " |",
            "|---" * (len(report["metrics"]) + 1) + "|"]
    for name, vals in report["absolute"].items():
        cells = [bootstrap.fmt(**vals[m]) for m in report["metrics"]]
        out.append(f"| {name} | " + " | ".join(cells) + " |")

    out += ["", "## Delta against the baseline", "",
            "| variant | metric | baseline | variant | delta | 95% CI | significant |",
            "|---|---|---|---|---|---|---|"]
    for name, by_metric in report["comparisons"].items():
        for metric, c in by_metric.items():
            out.append(
                f"| {name} | {metric} | {c['baseline']:.4f} | {c['variant']:.4f} | "
                f"{c['delta']:+.4f} | [{c['lo']:+.4f}, {c['hi']:+.4f}] | "
                f"{'yes' if c['significant'] else 'no'} |"
            )

    out += ["", "## Cost", "",
            "Index build only. Neither knob changes query latency or index residency: the "
            "same number of distinct queries is scored against the same dense score vector "
            "either way.", "",
            "| variant | articles | vocab | index build (s) | scoring (s) |",
            "|---|---|---|---|---|"]
    for name, cost in report["cost"].items():
        out.append(f"| {name} | {cost['articles']:,} | {cost['vocab']:,} | "
                   f"{cost['build_seconds']:.1f} | "
                   f"{cost['score_seconds'].get(report['split'], float('nan')):.1f} |")
    return "\n".join(out) + "\n"


def main() -> None:
    config = yaml.safe_load(CONFIG.read_text())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset")
    parser.add_argument("--ablation", choices=list(ABLATIONS),
                        help="run a named ablation from ABLATIONS (the usual case)")
    parser.add_argument("--variant", action="append",
                        help="name:fields=<f>,stem=<on|off>; the first is the baseline")
    parser.add_argument("--splits", nargs="+", default=["val", "test"])
    parser.add_argument("--name", default=None,
                        help="label for the output files; defaults to the variant names")
    parser.add_argument("--keep-scores", action="store_true",
                        help="leave data/processed/<dataset>/ablation/ in place afterwards")
    args = parser.parse_args()

    if bool(args.ablation) == bool(args.variant):
        raise SystemExit("pass exactly one of --ablation or --variant")
    specs = [parse_variant(v) for v in (args.variant or ABLATIONS[args.ablation])]
    args.name = args.name or args.ablation or "_vs_".join(name for name, _ in specs)
    if len(specs) < 2:
        raise SystemExit("need at least two variants: a baseline and something to compare")
    cfg = config[args.dataset]

    variants, cost = {}, {}
    for name, overrides in specs:
        variants[name], cost[name] = score_variant(
            args.dataset, cfg, name, overrides, args.splits
        )

    baseline = specs[0][0]
    metric_names = list(RANK_METRICS) + [f"recall@{k}" for k in RECALL_KS]
    RESULTS.mkdir(exist_ok=True)
    for split in args.splits:
        report = {
            "dataset": args.dataset, "split": split, "baseline": baseline,
            "variants": {name: dict(over) for name, over in specs},
            "metrics": metric_names,
            "n_impressions": len(variants[baseline][split]["impression_ids"]),
            "absolute": {
                name: {
                    m: dict(zip(("mean", "lo", "hi"), bootstrap.ci(data[split]["values"][m])))
                    for m in metric_names
                }
                for name, data in variants.items()
            },
            "comparisons": compare(baseline, variants, split),
            "cost": cost,
        }
        # Named after the variants, not just the dataset and split: two different
        # ablations on the same split would otherwise write to one path and the second
        # would silently destroy the first one's evidence.
        stem = f"ablation_bm25_{args.dataset}_{args.name}_{split}"
        (RESULTS / f"{stem}.json").write_text(json.dumps(report, indent=2))
        (RESULTS / f"{stem}.md").write_text(render(report))
        print(f"  -> results/{stem}.md")

    if not args.keep_scores:
        # These are a byproduct of the measurement, not an input to anything downstream,
        # and at ebnerd_small they are hundreds of MB per variant.
        shutil.rmtree(PROC / args.dataset / "ablation", ignore_errors=True)


if __name__ == "__main__":
    main()
