# Stage one: lexical and semantic candidate generation

*Owner: Yash. Design-note section. Numbers trace to `docs/FACTS.md` and `docs/ABLATIONS.md`.*

## What stage one is for

Stage one narrows the whole catalogue to a few hundred candidates that stage two can afford to
score carefully. Two independent retrievers run over the same corpus:

**BM25** (`bm25s`, k1=1.5, b=0.75), a lexical scorer: it ranks an article highly when it shares
rare words with the query. The query is the concatenated titles of the user's last `history_len`
clicked articles, so "what this user recently read" becomes an ordinary text query and
recommendation becomes ad-hoc retrieval.

**Semantic retrieval** (FAISS `IndexFlatIP`), which compares meaning rather than words. Each
article is a vector; the user is the mean of their history's vectors, renormalised; the score is
the cosine between them. `IndexFlatIP` is exact, not approximate, which at 20,738 articles is
affordable and removes approximation error as a variable.

Both return top-200 with `OVERFETCH = 3` before the publication-date filter, which drops articles
published after the impression. Both indexes are held in RAM.

## The two tracks, and why the distinction matters

Every stage-one number is reported on two tracks that answer different questions:

* **Re-rank**: score the candidate pool the log actually showed. This is what both Codabench
  competitions score, and what AUC, MRR and nDCG are computed over.
* **Retrieval**: ignore the pool and pull the top-K from the whole catalogue. This is what
  recall@K measures, and it is what stage two consumes.

They disagree often enough that quoting one alone is misleading, and the two ablations below are
the clearest demonstration.

## Ablation #7: which fields go in the BM25 document

Dropping the abstract, leaving title only. Paired bootstrap, 1,000 shared resamples, selection on
val.

| dataset | val AUC | val MRR | val recall@200 | verdict |
|---|---|---|---|---|
| MIND small | **+0.0024** [+0.0006, +0.0041] | **-0.0022** [-0.0039, -0.0005] | **+0.0017** [+0.0007, +0.0028] | wins on AUC |
| EB-NeRD small | **+0.0025** [+0.0002, +0.0047] | +0.0019 [-0.0001, +0.0039] | **-0.0024** [-0.0035, -0.0013] | two-sided trade-off |

Three things worth stating:

**It reproduces the Assignment-1 prior to four decimals on both axes at once.** A1 measured
+0.0025 AUC and -0.0024 recall@200 on EB-NeRD; this run gives +0.0025 and -0.0024. Two
independent systems on different codebases agreeing to that precision on a two-sided trade-off is
the strongest cross-validation in the project.

**A1's claim of "no measured downside" on MIND was wrong, and only a per-metric paired CI shows
it.** MIND's val MRR falls significantly. Reporting AUC alone would have recorded a free win.

**The two datasets pay in different currencies.** MIND pays in MRR, EB-NeRD pays in retrieval
recall. So the MIND MRR loss is a property of MIND rather than of dropping the abstract, and the
knob is worth making per-dataset rather than global.

Cost falls on both: MIND vocabulary 44,264 to 24,681 and build 4.5 s to 1.9 s; EB-NeRD 30,388 to
15,132 and 1.0 s to 0.6 s.

**Status: not shipped.** The measurement supports it on ranking metrics for both datasets, but it
costs exactly the stage-one recall that stage two feeds on, which makes it a pipeline-level
decision rather than a retrieval-level one.

## Ablation #6: per-language stemming

Stemming collapses inflected forms to a stem, so `spilleren` and `spiller` both become `spil`.
The plan's premise was "Danish on, English off". **Measurement rejects that premise and keeps it
on for both.**

**English, MIND.** Turning stemming off costs **-0.0023** [-0.0034, -0.0013] val AUC, significant,
so it stays on, selected on val AUC. But recall@200 moves the *other* way, +0.0021 [+0.0013,
+0.0028], also significant. Stemming helps re-ranking a shown pool and hurts retrieval from
65,238 articles: merging surface forms costs precision when picking 200 from the whole catalogue,
while inside a pool of a few dozen plausible candidates the same merging recovers matches an
exact comparison misses. Both A1 systems had already measured these two halves separately and
been read as contradicting each other.

**Danish, EB-NeRD small.** Ranking is flat: all four metrics within ±0.0004 on both splits, with
the val AUC interval only ±0.0017 wide, so an effect a fifth the size of #7's would have shown.
recall@200 *is* significant but **flips sign across the split boundary**, -8.5% on val and +4.7%
on test, which makes it a property of which articles fell in each window rather than of stemming.
**A1's prior of +22 to +36% recall@200 is excluded, not merely unconfirmed.**

Kept on for cost alone: vocabulary 43,451 to 30,388 and val scoring 23.6 s to 19.2 s, because a
smaller vocabulary means shorter posting lists. The standing explanation for the missing gain is
that the pipeline already applies a Danish stopword list, separately measured in A1 as
0.5035 to 0.5232 AUC; stopwords and stemming compete for the same high-frequency variation, so
A1's figure was probably the combined effect of both. Testing that needs a `stem x stopwords`
2x2, which is a second variable and therefore its own ablation.

## The methodological result: underpowered is not zero

Both ablations were first run at `ebnerd_demo` scale (11,777 articles, 6,872 val impressions) and
two cells spanned zero. Re-run at `ebnerd_small`, those two resolved in **opposite** directions:

* #7's effect was **real and simply unresolvable**: +0.0009 [-0.0062, +0.0081] became
  +0.0025 [+0.0002, +0.0047], and the demo interval had contained the true value comfortably.
* #6's effect was **genuinely absent**, at intervals tight enough to have seen a fifth of it.

Writing both up as "inconclusive" would have been true and useless. The operational rule adopted:
any ablation whose interval spans zero at demo scale is re-run at `small` before a verdict is
recorded, never written off.

## What is not settled

The EB-NeRD BM25 recall@200 anomaly from A1, more than 2x better at history N=1 than at any
larger N while MIND improves monotonically, is **still unexplained**. A semantic history sweep
appeared to confirm a peak at small N, but that sweep was later found to be scoring on
future-click-contaminated history (`FACTS.md` section 10) and its conclusion does not stand. The
anomaly is open.
