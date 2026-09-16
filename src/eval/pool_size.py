"""How the candidate pool and the query grow with the corpus, measured not assumed.

The Q4.4 scaling curve shows every stage slowing down between half the corpus and all of it,
including two whose work cannot depend on corpus size: feature assembly and the LightGBM
predict, which both touch only the candidate pool. Either the pool is growing, or the stages are
doing the same work more slowly. This separates those.

It also quantifies the confound already disclosed for the lexical stages: subsampling the corpus
removes articles from users' histories, so the query built from history titles gets shorter, and
`tokenise` and `bm25` are then measured on a smaller input as well as a smaller index.

Counts only, no timings, so it is unaffected by what else the machine is doing.

    python -m src.eval.pool_size ebnerd_small

Writes results/pool_size_<dataset>.json.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import polars as pl
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG = ROOT / "configs/datasets.yaml"
PROC = ROOT / "data/processed"
RESULTS = ROOT / "results"


def measure(name: str, cfg: dict, fractions: list[float], n_requests: int, seed: int = 0) -> list[dict]:
    import bm25s
    import faiss

    from src.retrieval.bm25 import TOP_K, build_index, stopwords_for
    from src.retrieval.embeddings import load_vectors

    articles = pl.read_parquet(PROC / name / "articles.parquet")
    impressions = pl.read_parquet(PROC / name / "impressions_val.parquet")
    vectors = load_vectors(name, cfg, articles)
    rng = np.random.default_rng(seed)
    rows = rng.choice(impressions.height, size=min(n_requests, impressions.height), replace=False)
    histories = impressions["history"].to_list()
    history_len = cfg["history_len"]

    out = []
    for frac in fractions:
        k = max(int(round(articles.height * frac)), 1000)
        keep = (np.arange(articles.height) if frac >= 1.0
                else np.sort(rng.choice(articles.height, size=min(k, articles.height), replace=False)))
        sub, sub_vectors = articles[keep], np.ascontiguousarray(vectors[keep])
        index, stemmer = build_index(sub, cfg, ("title", "abstract"))
        faiss_index = faiss.IndexFlatIP(sub_vectors.shape[1])
        faiss_index.add(sub_vectors)
        title_of = dict(zip(sub["article_id"], sub["title"]))
        position = {a: i for i, a in enumerate(sub["article_id"])}

        pools, tokens, resolved = [], [], []
        for row in rows:
            history = histories[row][-history_len:]
            resolved.append(sum(1 for a in history if a in title_of))
            query = " ".join(title_of.get(a, "") for a in history)
            toks = bm25s.tokenize([query], stopwords=stopwords_for(cfg), stemmer=stemmer,
                                  return_ids=False, show_progress=False)[0]
            tokens.append(len(toks))

            lexical = np.empty(0, dtype=np.int64)
            if toks:
                scores = index.get_scores(toks)
                top = np.argpartition(-scores, min(TOP_K, len(scores)) - 1)[:TOP_K]
                lexical = top[np.argsort(-scores[top])]
            idx = [position[a] for a in history if a in position]
            dense = np.empty(0, dtype=np.int64)
            if idx:
                q = sub_vectors[idx].mean(axis=0)
                norm = np.linalg.norm(q)
                q = (q / norm if norm > 0 else q).astype(np.float32)[None, :]
                dense = faiss_index.search(q, TOP_K)[1][0]
            pools.append(int(len(np.union1d(lexical, dense))))

        out.append({
            "fraction": frac, "articles": int(sub.height), "requests": len(rows),
            "pool_mean": float(np.mean(pools)), "pool_median": float(np.median(pools)),
            "query_tokens_mean": float(np.mean(tokens)),
            "history_items_resolving_mean": float(np.mean(resolved)),
        })
        print(f"  {frac:>5.0%} {sub.height:>7,} articles   pool {out[-1]['pool_mean']:6.1f}   "
              f"query tokens {out[-1]['query_tokens_mean']:6.1f}   "
              f"history items {out[-1]['history_items_resolving_mean']:5.1f}")
        del index, faiss_index, sub_vectors
    return out


def main() -> None:
    config = yaml.safe_load(CONFIG.read_text())
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dataset")
    ap.add_argument("--fractions", type=float, nargs="+", default=[0.1, 0.25, 0.5, 1.0])
    ap.add_argument("--requests", type=int, default=300)
    args = ap.parse_args()

    rows = measure(args.dataset, config[args.dataset], args.fractions, args.requests)
    RESULTS.mkdir(exist_ok=True)
    dest = RESULTS / f"pool_size_{args.dataset}.json"
    dest.write_text(json.dumps({"dataset": args.dataset, "scales": rows}, indent=2))
    growth = rows[-1]["pool_mean"] / rows[0]["pool_mean"]
    tok = rows[-1]["query_tokens_mean"] / rows[0]["query_tokens_mean"]
    print(f"\nacross {rows[-1]['articles'] / rows[0]['articles']:.1f}x corpus: "
          f"pool grows {growth:.2f}x, query grows {tok:.1f}x")
    print(f"  -> {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
