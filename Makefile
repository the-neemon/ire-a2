# One command rebuilds everything from raw files.
#
#   make venv                 create .venv and install dependencies (CPU-only torch)
#   make data                 raw archives -> temporal split -> feature store
#   make retrieve             stage 1: BM25 + embedding candidate generation
#   make features             stage 1.5: behavioural features from click-logs   (A2, Q1)
#   make rerank               stage 2: train and apply the re-ranker            (A2, Q2)
#   make baseline             reproduce NRMS, then the improved variant         (A2, Q3)
#   make results              full evaluation: metrics, slices, bootstrap CIs   (A2, Q5)
#   make bench                serving measurements: memory, p99, QPS            (A2, Q4)
#   make ablation             every ablation in docs/ABLATIONS.md
#   make test                 leakage and behaviour-window assertions           (A2, Q9)
#   make submissions          Codabench leaderboard files (downloads the test sets)
#   make all                  data + retrieve + features + rerank + results

PY := .venv/bin/python
DATASETS ?= ebnerd_demo ebnerd_small mind_small
BUNDLES ?= ebnerd_demo ebnerd_small Ekstra_Bladet_word2vec \
	google_bert_base_multilingual_cased MINDsmall_train MINDsmall_dev

.PHONY: all venv data download split retrieve features rerank baseline results bench \
	ablation test submissions clean-processed

all: results

venv:
	uv venv --python 3.11 .venv
	# CPU-only torch first: the default resolves to CUDA wheels (~2.5GB) that this
	# machine cannot use, and pulling them stalls the install.
	VIRTUAL_ENV=.venv uv pip install torch --index-url https://download.pytorch.org/whl/cpu
	VIRTUAL_ENV=.venv uv pip install polars pyarrow bm25s PyStemmer faiss-cpu \
		sentence-transformers huggingface_hub numpy scipy scikit-learn lightgbm \
		tqdm pyyaml pytest

data: split

download:
	$(PY) -m src.pipeline.download $(BUNDLES)

split: download
	$(PY) -m src.pipeline.split $(DATASETS)

retrieve: split
	$(PY) -m src.retrieval.bm25 $(DATASETS)
	$(PY) -m src.retrieval.embeddings $(DATASETS)
	$(PY) -m src.retrieval.fuse $(DATASETS)

# A2 Q1. Click-history, session and article features, with the behaviour-window
# boundary enforced in code rather than by discipline.
features: retrieve
	@echo "TODO: src/features not implemented yet"

# A2 Q2. Two-stage retrieve-then-rank over the top-K from `retrieve`.
rerank: features
	@echo "TODO: src/rerank not implemented yet"

# A2 Q3. Reproduce the official baseline, then beat it with one principled change.
baseline: features
	@echo "TODO: NRMS reproduction not implemented yet"

results: rerank
	$(PY) -m src.eval.run $(DATASETS)

# A2 Q4. Index memory, p99 single-request latency, cost/QPS at an SLA. Every number
# this emits belongs in docs/FACTS.md with the command that produced it.
bench:
	@echo "TODO: src/eval/bench not implemented yet"

# A2 Q3.3. Every ablation, each isolating one change, each with a paired bootstrap
# 95% CI. Results go to docs/ABLATIONS.md whether they win or lose.
ablation:
	@echo "TODO: ablation runner not implemented yet"

test:
	$(PY) -m pytest tests/ -v

# Codabench leaderboard files. Separate from `all` because these score the competitions'
# held-out test sets (EB-NeRD 13.5M impressions, MIND-large 2.4M), not our splits.
# Rate limits: MIND 1 submission/day, EB-NeRD 5/day. Validate structurally offline first.
submissions:
	$(PY) -m src.pipeline.download ebnerd_testset MINDlarge_test
	$(PY) -m src.pipeline.submit ebnerd
	$(PY) -m src.pipeline.submit mind

clean-processed:
	rm -rf data/processed results
