"""Generate the design note's tables and number macros from results/*.json.

No number in the PDF is typed by hand. Every table is written here as a LaTeX fragment under
tables/, and every number quoted in running text is a macro in tables/numbers.tex, both read
straight from the results file the pipeline wrote. A transcribed number can drift from its
source; a generated one cannot.

Two guards keep stale results out. The evaluation reports are used only if they were produced
for the shipped re-ranker (`rerank_tag == "final"`), and the serving bench only if it timed the
persisted final model. Anything missing becomes a visible red placeholder rather than a silent
old value.

    python docs/design-note/make_tables.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS = ROOT / "results"
OUT = Path(__file__).resolve().parent / "tables"
PENDING = r"\pend{pending}"

DATASETS = {"ebnerd_small": ("EB", r"\eb{}"), "mind_small": ("MD", r"\mind{}")}
SYSTEM_LABEL = {
    "bm25": "BM25 (stage one)",
    "emb": "embeddings (stage one)",
    "fused": "fused (stage one)",
    "rerank": "two-stage re-ranker",
    "fused+popularity": "fused + lifetime popularity$^\\ast$",
}
METRICS = [("auc", "AUC"), ("mrr", "MRR"), ("mrr_all", "MRR, all clicks"),
           ("ndcg@5", "nDCG@5"), ("ndcg@10", "nDCG@10")]


# ------------------------------------------------------------------------ helpers

def load(name: str) -> dict | None:
    p = RESULTS / name
    return json.loads(p.read_text()) if p.exists() else None


def sgn(x: float, nd: int = 4) -> str:
    s = f"{abs(x):.{nd}f}"
    return f"$+${s}" if x >= 0 else f"$-${s}"


def ci(lo: float, hi: float) -> str:
    return f"[{sgn(lo)}, {sgn(hi)}]"


def tex_name(arm: str) -> str:
    return arm.replace("_", r"\_")


def write(name: str, body: str) -> None:
    OUT.mkdir(exist_ok=True)
    (OUT / f"{name}.tex").write_text(body)
    print(f"  wrote tables/{name}.tex")


def final_report(dataset: str, split: str) -> dict | None:
    """The harness report for the shipped model, or None if absent or produced for another tag."""
    r = load(f"{dataset}_{split}.json")
    if r is None or r.get("rerank_tag") != "final":
        return None
    return r


def cell(stat: dict, bold: bool = False) -> str:
    macro = r"\cellcib" if bold else r"\cellci"
    return f"{macro}{{{stat['mean']:.4f}}}{{{stat['lo']:.4f}}}{{{stat['hi']:.4f}}}"


# ------------------------------------------------------------------ number macros

def numbers() -> str:
    m: dict[str, str] = {}

    for dataset, (p, _) in DATASETS.items():
        for split, sp in (("val", "Val"), ("test", "Test")):
            r = final_report(dataset, split)
            if r is None:
                for name in (f"{p}Final{sp}", f"{p}Fused{sp}", f"{p}Gain{sp}", f"{p}Leaky{sp}",
                             f"{p}ColdThr{sp}", f"{p}HeadThr{sp}"):
                    m[name] = PENDING
                m[f"{p}Gain{sp}CI"] = ""
                continue
            m[f"{p}Final{sp}"] = f"{r['overall']['rerank']['auc']['mean']:.4f}"
            m[f"{p}Fused{sp}"] = f"{r['overall']['fused']['auc']['mean']:.4f}"
            c = r["comparisons"]["rerank - fused (auc)"]
            m[f"{p}Gain{sp}"] = sgn(c["mean"])
            m[f"{p}Gain{sp}CI"] = ci(c["lo"], c["hi"])
            if "fused+popularity" in r["overall"]:
                m[f"{p}Leaky{sp}"] = f"{r['overall']['fused+popularity']['auc']['mean']:.4f}"
            m[f"{p}ColdThr{sp}"] = f"{r['cold_threshold_history_len']:.0f}"
            m[f"{p}HeadThr{sp}"] = f"{r['head_threshold_train_clicks']:.0f}"

    for key, fname in (("Seven", "compare_ebnerd_small_ladder10_vs_ladder17.json"),
                       ("Exp", "compare_ebnerd_small_ladder17_vs_final.json"),
                       ("ExpMind", "compare_mind_small_ladder12_vs_final.json")):
        r = load(fname)
        for split, sp in (("val", "Val"), ("test", "Test")):
            if r is None or split not in r:
                m[f"Ladder{key}{sp}"], m[f"Ladder{key}{sp}CI"] = PENDING, ""
                m[f"Ladder{key}{sp}From"] = m[f"Ladder{key}{sp}To"] = PENDING
                continue
            s = r[split]
            m[f"Ladder{key}{sp}"] = sgn(s["b_minus_a"])
            m[f"Ladder{key}{sp}CI"] = ci(s["ci_lo"], s["ci_hi"])
            m[f"Ladder{key}{sp}From"] = f"{s['auc_a']:.4f}"
            m[f"Ladder{key}{sp}To"] = f"{s['auc_b']:.4f}"

    pool = load("pool_size_ebnerd_small.json")
    if pool:
        lo, hi = pool["scales"][0], pool["scales"][-1]
        m.update(
            PoolSmall=f"{lo['pool_mean']:.0f}", PoolFull=f"{hi['pool_mean']:.0f}",
            PoolGrowth=f"{hi['pool_mean'] / lo['pool_mean']:.2f}",
            TokSmall=f"{lo['query_tokens_mean']:.1f}", TokFull=f"{hi['query_tokens_mean']:.1f}",
            TokGrowth=f"{hi['query_tokens_mean'] / lo['query_tokens_mean']:.1f}",
            HistSmall=f"{lo['history_items_resolving_mean']:.1f}",
            HistFull=f"{hi['history_items_resolving_mean']:.1f}",
        )
    else:
        for k in ("PoolSmall", "PoolFull", "PoolGrowth", "TokSmall", "TokFull", "TokGrowth",
                  "HistSmall", "HistFull"):
            m[k] = PENDING

    q9 = load("q9_ebnerd_small_val.json")
    if q9:
        m.update(QnineCausal=f"{q9['causal_auc']:.4f}", QnineLeaky=f"{q9['leaky_auc']:.4f}",
                 QnineDelta=sgn(q9["delta"]), QnineCI=ci(q9["ci_lo"], q9["ci_hi"]))
    else:
        m.update(QnineCausal=PENDING, QnineLeaky=PENDING, QnineDelta=PENDING, QnineCI="")

    b = bench_final()
    if b:
        lat, cost, sc = b["latency"], b["cost"], b["scaling"]
        small, full = sc[0], sc[-1]
        m.update(
            BenchPfifty=f"{lat['total']['p50_ms']:.1f}",
            BenchPninetyfive=f"{lat['total']['p95_ms']:.1f}",
            BenchPninetynine=f"{lat['total']['p99_ms']:.1f}",
            BenchAnnShare=f"{100 * lat['ann']['p50_ms'] / lat['total']['p50_ms']:.0f}",
            BenchRerankShare=f"{100 * lat['rerank']['p50_ms'] / lat['total']['p50_ms']:.0f}",
            BenchRerankPninetynine=f"{lat['rerank']['p99_ms']:.1f}",
            BenchAnnPninetynine=f"{lat['ann']['p99_ms']:.1f}",
            BenchHeadroom=f"{cost['headroom_x']:.1f}",
            BenchSerialQPS=f"{cost['serial_qps_one_core']:.0f}",
            BenchCapacityQPS=f"{cost['capacity_qps_all_cores_projected']:.0f}",
            BenchCost=f"{cost['usd_per_1000_queries_projected']:.6f}",
            BenchCores=f"{cost['cores']}",
            BenchRequests=f"{b['requests']:,}",
            BenchTrees=f"{b['build']['rerank_trees']}",
            BenchFeatures=f"{b['build'].get('rerank_features', '')}",
            BenchCorpusGrowth=f"{full['articles'] / small['articles']:.1f}",
            BenchAnnGrowth=f"{full['ann_p50_ms'] / small['ann_p50_ms']:.1f}",
            BenchBmGrowth=f"{full['bm25_p50_ms'] / small['bm25_p50_ms']:.1f}",
            BenchRerankGrowth=f"{full['rerank_p50_ms'] / small['rerank_p50_ms']:.1f}",
            BenchTokGrowth=f"{full['tokenise_p50_ms'] / small['tokenise_p50_ms']:.1f}",
            BenchFeatGrowth=f"{full['features_p50_ms'] / small['features_p50_ms']:.1f}",
            BenchFaissSmall=f"{small['faiss_ram_bytes'] / 2**20:.1f}",
            BenchFaissFull=f"{full['faiss_ram_bytes'] / 2**20:.1f}",
        )
    else:
        for k in ("Pfifty", "Pninetyfive", "Pninetynine", "AnnShare", "RerankShare",
                  "RerankPninetynine", "AnnPninetynine", "Headroom", "SerialQPS",
                  "CapacityQPS", "Cost", "Cores", "Requests", "Trees", "Features",
                  "CorpusGrowth", "AnnGrowth", "BmGrowth", "RerankGrowth", "TokGrowth",
                  "FeatGrowth", "FaissSmall", "FaissFull"):
            m[f"Bench{k}"] = PENDING

    return "\n".join(rf"\newcommand{{\{k}}}{{{v}}}" for k, v in sorted(m.items())) + "\n"


# ------------------------------------------------------------ accuracy tables (Q2, Q5)

def overall(split: str) -> str | None:
    rows, any_data = [], False
    for dataset, (_, label) in DATASETS.items():
        r = final_report(dataset, split)
        rows.append(rf"\multicolumn{{6}}{{@{{}}l}}{{\textit{{{label} small, {split}}}}} \\")
        if r is None:
            rows.append(rf"\multicolumn{{6}}{{@{{}}l}}{{{PENDING}}} \\")
            continue
        any_data = True
        for system in ("bm25", "emb", "fused", "rerank", "fused+popularity"):
            if system not in r["overall"]:
                continue
            cells = " & ".join(cell(r["overall"][system][k], bold=(system == "rerank"))
                               for k, _ in METRICS)
            rows.append(f"{SYSTEM_LABEL[system]} & {cells}" + r" \\[2pt]")
        rows.append(r"\midrule")
    if not any_data:
        return None
    if rows[-1] == r"\midrule":
        rows.pop()
    head = " & ".join(h for _, h in METRICS)
    return (r"\begin{tabular}{@{}lccccc@{}}" "\n" r"\toprule" "\n"
            f"system & {head}" r" \\" "\n" r"\midrule" "\n" + "\n".join(rows) + "\n"
            r"\bottomrule" "\n" r"\end{tabular}" "\n")


def slices(split: str) -> str | None:
    rows, any_data = [], False
    for dataset, (_, label) in DATASETS.items():
        r = final_report(dataset, split)
        if r is None:
            rows.append(rf"{label} & \multicolumn{{5}}{{l}}{{{PENDING}}} \\")
            continue
        any_data = True
        thr = (f"cold: history $\\le$ {r['cold_threshold_history_len']:.0f} clicks; "
               f"head: clicked article with $\\ge$ {r['head_threshold_train_clicks']:.0f} train clicks")
        rows.append(rf"\multicolumn{{6}}{{@{{}}l}}{{\textit{{{label} small, {split}}} \quad {{\scriptsize {thr}}}}} \\")
        for name in ("cold", "warm", "zero_history", "head", "tail"):
            if name not in r["slices"]:
                continue
            s = r["slices"][name]
            leaky = cell(s["fused+popularity"]) if "fused+popularity" in s else "--"
            rows.append(f"{tex_name(name)} & {s['n']:,} & {cell(s['fused'])} & {cell(s['rerank'], bold=True)} & "
                        f"{sgn(s['rerank']['mean'] - s['fused']['mean'])} & {leaky}" r" \\[2pt]")
        rows.append(r"\midrule")
    if not any_data:
        return None
    if rows[-1] == r"\midrule":
        rows.pop()
    return (r"\begin{tabular}{@{}lrcccc@{}}" "\n" r"\toprule" "\n"
            r"slice & impressions & fused (stage one) & two-stage re-ranker & gain & fused + lifetime pop.$^\ast$ \\" "\n"
            r"\midrule" "\n" + "\n".join(rows) + "\n" r"\bottomrule" "\n" r"\end{tabular}" "\n")


def beyond(split: str) -> str | None:
    rows, any_data = [], False
    for dataset, (_, label) in DATASETS.items():
        r = final_report(dataset, split)
        rows.append(rf"\multicolumn{{4}}{{@{{}}l}}{{\textit{{{label} small, {split}}}}} \\")
        if r is None:
            rows.append(rf"\multicolumn{{4}}{{@{{}}l}}{{{PENDING}}} \\")
            continue
        any_data = True
        for system in ("bm25", "emb", "fused", "rerank"):
            b = r["beyond_accuracy"][system]
            cells = []
            for key in ("diversity", "novelty", "coverage"):
                fmt = "{:.3f}" if key == "novelty" else "{:.4f}"
                bold = system == "rerank"
                if key == "coverage":
                    # No interval: the bootstrap cannot interval a distinct-article count, and
                    # printing the resample spread as one would be a wrong number, not a wide one.
                    value = fmt.format(b[key])
                    cells.append(rf"\textbf{{{value}}}" if bold else value)
                    continue
                lo, hi = b.get(f"{key}_ci", [float("nan"), float("nan")])
                macro = r"\cellcib" if bold else r"\cellci"
                cells.append(f"{macro}{{{fmt.format(b[key])}}}{{{fmt.format(lo)}}}{{{fmt.format(hi)}}}")
            rows.append(f"{SYSTEM_LABEL[system]} & " + " & ".join(cells) + r" \\[2pt]")
        rows.append(r"\midrule")
    if not any_data:
        return None
    if rows[-1] == r"\midrule":
        rows.pop()
    return (r"\begin{tabular}{@{}lccc@{}}" "\n" r"\toprule" "\n"
            r"system & diversity & novelty (bits) & coverage \\" "\n" r"\midrule" "\n"
            + "\n".join(rows) + "\n" r"\bottomrule" "\n" r"\end{tabular}" "\n")


# ------------------------------------------------------------------ serving bench (Q4)

def bench_final() -> dict | None:
    b = load("bench_ebnerd_small.json")
    if b is None or "final" not in str(b.get("build", {}).get("rerank_model", "")):
        return None
    return b


def bench_footprint() -> str | None:
    b = bench_final()
    if b is None:
        return None
    mib = lambda x: f"{x / 2**20:.1f}"
    fs = b["feature_store"]["total"]
    bm, fa = b["bm25"], b["faiss"]
    rows = [
        f"BM25 (sparse matrix) & {bm['postings']:,} postings, {bm['vocab_terms']:,} terms & "
        f"{mib(bm['ram_total_bytes'])} & {mib(bm['disk_bytes'])} & {bm['ram_total_bytes'] / bm['disk_bytes']:.2f}$\\times$",
        f"FAISS flat index & {fa['vectors']:,} $\\times$ {fa['dim']} float32 & "
        f"{mib(fa['ram_bytes'])} & {mib(fa['disk_bytes'])} & {fa['ram_bytes'] / fa['disk_bytes']:.2f}$\\times$",
        f"feature store & {fs['rows']:,} candidate rows & {mib(fs['ram_bytes'])} & {mib(fs['disk_bytes'])} & "
        f"{fs['ram_bytes'] / fs['disk_bytes']:.2f}$\\times$",
    ]
    return (r"\begin{tabular}{@{}llrrr@{}}" "\n" r"\toprule" "\n"
            r"index & size & RAM (MiB) & disk (MiB) & RAM / disk \\" "\n" r"\midrule" "\n"
            + " \\\\\n".join(rows) + r" \\" "\n" r"\bottomrule" "\n" r"\end{tabular}" "\n")


def bench_latency() -> str | None:
    b = bench_final()
    if b is None:
        return None
    lat = b["latency"]
    total50 = lat["total"]["p50_ms"]
    rows = []
    for stage, label in (("tokenise", "tokenise query"), ("bm25", "BM25 top 200"),
                         ("ann", "embedding top 200 (exact)"), ("features", "assemble features"),
                         ("rerank", "LightGBM predict"), ("total", r"\textbf{total}")):
        s = lat[stage]
        share = "" if stage == "total" else f"{100 * s['p50_ms'] / total50:.0f}\\%"
        bold = (lambda v: rf"\textbf{{{v}}}") if stage == "total" else (lambda v: v)
        p50, p95, p99 = (bold("{:.2f}".format(s[k])) for k in ("p50_ms", "p95_ms", "p99_ms"))
        rows.append(f"{label} & {p50} & {p95} & {p99} & {share}")
    return (r"\begin{tabular}{@{}lrrrr@{}}" "\n" r"\toprule" "\n"
            r"stage & p50 (ms) & p95 (ms) & p99 (ms) & share of p50 \\" "\n" r"\midrule" "\n"
            + " \\\\\n".join(rows) + r" \\" "\n" r"\bottomrule" "\n" r"\end{tabular}" "\n")


def bench_scaling_plot() -> str | None:
    b = bench_final()
    if b is None:
        return None
    sc = b["scaling"]
    series = [("ann", "exact embedding search", "red!70!black", "*"),
              ("rerank", "LightGBM predict", "blue!70!black", "square*"),
              ("bm25", "BM25", "green!50!black", "triangle*"),
              ("total", "total", "black", "o")]
    plots = []
    for key, label, colour, mark in series:
        coords = " ".join(f"({row['articles']},{row[f'{key}_p50_ms']:.3f})" for row in sc)
        plots.append(rf"\addplot[color={colour}, mark={mark}, thick] coordinates {{{coords}}};"
                     "\n" rf"\addlegendentry{{{label}}}")
    ticks = ",".join(str(row["articles"]) for row in sc)
    labels = ",".join(f"{row['articles'] / 1000:.1f}k" for row in sc)
    return (r"\begin{tikzpicture}" "\n"
            r"\begin{axis}[width=0.62\linewidth, height=5.4cm, xmode=log, ymode=log," "\n"
            r"  xlabel={articles in the corpus}, ylabel={p50 latency (ms)}, log basis x=10," "\n"
            rf"  xtick={{{ticks}}}, xticklabels={{{labels}}}, xticklabel style={{font=\scriptsize}}," "\n"
            r"  legend style={font=\scriptsize, fill opacity=0.85, text opacity=1}," "\n"
            r"  legend pos=south east, tick label style={font=\scriptsize}," "\n"
            r"  label style={font=\small}, grid=major, grid style={gray!20}]" "\n"
            + "\n".join(plots) + "\n" r"\end{axis}" "\n" r"\end{tikzpicture}" "\n")


def bench_scaling() -> str | None:
    b = bench_final()
    if b is None:
        return None
    rows = [f"{row['fraction']:.0%}".replace("%", r"\%") + f" & {row['articles']:,} & "
            f"{row['faiss_ram_bytes'] / 2**20:.1f} & {row['bm25_p50_ms']:.2f} & {row['ann_p50_ms']:.2f} & "
            f"{row['rerank_p50_ms']:.2f} & {row['total_p50_ms']:.2f} & {row['total_p99_ms']:.2f}"
            for row in b["scaling"]]
    return (r"\begin{tabular}{@{}rrrrrrrr@{}}" "\n" r"\toprule" "\n"
            r"corpus & articles & FAISS MiB & BM25 p50 & exact kNN p50 & rerank p50 & total p50 & total p99 \\" "\n"
            r"\midrule" "\n" + " \\\\\n".join(rows) + r" \\" "\n" r"\bottomrule" "\n" r"\end{tabular}" "\n")


# ------------------------------------------------------------------ ablation grids

def ablation_grid(dataset: str) -> str | None:
    val, test = (load(f"ablation_rerank_{dataset}_{s}.json") for s in ("val", "test"))
    if not (val and test):
        return None
    by_test = {a["arm"]: a for a in test["arms"]}

    def delta(r: dict) -> str:
        d = sgn(r["full_minus_arm"])
        return (rf"\textbf{{{d}}}" if r["significant"] else d) + " " + ci(r["ci_lo"], r["ci_hi"])

    rows = [f"{tex_name(a['arm'])} & {a['auc']:.4f} & {delta(a)} & "
            + (delta(by_test[a["arm"]]) if a["arm"] in by_test else "n/a") + r" \\"
            for a in val["arms"]]
    return (r"\begin{tabular}{@{}lccc@{}}" "\n" r"\toprule" "\n"
            r"arm & val AUC & full $-$ arm, val [95\% CI] & full $-$ arm, test [95\% CI] \\" "\n"
            r"\midrule" "\n"
            + f"full model & {val['full_auc']:.4f} & & test AUC {test['full_auc']:.4f}" + r" \\" "\n"
            + "\n".join(rows) + "\n" r"\bottomrule" "\n" r"\end{tabular}" "\n")


# ------------------------------------------------------------------ isolated sweeps

def sweeps() -> str | None:
    eb, mind = load("sweep_constants_ebnerd_small_val.json"), load("sweep_constants_mind_small_val.json")
    scroll = load("sweep_scroll_ebnerd_small_val.json")
    if not (eb and mind and scroll):
        return None
    lab = lambda h: "unbounded" if h is None else f"{h:g} h"
    mind_by = {w["window_h"]: w["auc"] for w in mind["window"]}
    win = "\n".join(f"{lab(w['window_h'])} & {w['auc']:.4f} & {mind_by.get(w['window_h'], float('nan')):.4f}" + r" \\"
                    for w in eb["window"])
    half = " & ".join(f"{h['auc']:.4f}" for h in eb["halflife"])
    half_head = " & ".join(f"{h['halflife_h']:g}\\,h" for h in eb["halflife"])
    scr = "\n".join(f"{a['min_scroll']:g}\\% & {a['auc']:.4f} & {100 * a['history_kept']:.1f}\\%" + r" \\"
                    for a in scroll["arms"])
    return (r"\begin{tabular}[t]{@{}lcc@{}}" "\n" r"\toprule" "\n"
            r"popularity window & \eb{} & \mind{} \\" "\n" r"\midrule" "\n" + win + "\n"
            r"\bottomrule" "\n" r"\end{tabular}\hfill" "\n"
            r"\begin{tabular}[t]{@{}lcc@{}}" "\n" r"\toprule" "\n"
            r"min.\ scroll depth & AUC & history kept \\" "\n" r"\midrule" "\n" + scr + "\n"
            r"\bottomrule" "\n" r"\end{tabular}" "\n\n" r"\medskip" "\n"
            r"\begin{tabular}{@{}l" + "c" * len(eb["halflife"]) + r"@{}}" "\n" r"\toprule" "\n"
            r"recency half-life & " + half_head + r" \\" "\n" r"\midrule" "\n"
            r"\eb{} AUC & " + half + r" \\" "\n" r"\bottomrule" "\n" r"\end{tabular}" "\n")


def sweep_history() -> str | None:
    h = load("sweep_history_ebnerd_small_val.json")
    if not h:
        return None
    head = " & ".join(str(r["n"]) for r in h)
    uni = " & ".join(f"{r['uniform']:.4f}" for r in h)
    eng = " & ".join(f"{r['engagement']:.4f}" for r in h)
    return (r"\begin{tabular}{@{}l" + "c" * len(h) + r"@{}}" "\n" r"\toprule" "\n"
            r"history clicks & " + head + r" \\" "\n" r"\midrule" "\n"
            r"uniform user vector & " + uni + r" \\" "\n"
            r"read-time weighted & " + eng + r" \\" "\n" r"\bottomrule" "\n" r"\end{tabular}" "\n")


BUILDERS = {
    "numbers": numbers,
    "q5_overall_test": lambda: overall("test"),
    "q5_overall_val": lambda: overall("val"),
    "q5_slices_test": lambda: slices("test"),
    "q5_beyond_test": lambda: beyond("test"),
    "bench_footprint": bench_footprint,
    "bench_latency": bench_latency,
    "bench_scaling": bench_scaling,
    "bench_scaling_plot": bench_scaling_plot,
    "ablation_ebnerd": lambda: ablation_grid("ebnerd_small"),
    "ablation_mind": lambda: ablation_grid("mind_small"),
    "sweeps": sweeps,
    "sweep_history": sweep_history,
}


def main() -> None:
    for name, fn in BUILDERS.items():
        body = fn()
        if body is None:
            write(name, rf"\begin{{center}}{PENDING}: \texttt{{{tex_name(name)}}} not generated yet\end{{center}}" "\n")
            print(f"    ({name}: inputs not in results/ yet, placeholder written)")
        else:
            write(name, body)


if __name__ == "__main__":
    main()
