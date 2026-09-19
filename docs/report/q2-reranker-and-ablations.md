# Q2: the re-ranker and the ablation grid

*Owner: Naman. Grid in `src/rerank/ablate.py`, results in
`results/ablation_rerank_ebnerd_small_{val,test}.json`. Every figure here is measured on clean
features, after the 2026-09-08 engagement leak fix.*

## Headline

| | val | test |
|---|---|---|
| full re-ranker | **0.7489** | **0.7461** |
| stage one alone | 0.5498 | 0.5430 |
| **gain** | **+0.1991 [+0.1963, +0.2020]** | **+0.2031 [+0.2016, +0.2047]** |

Per-impression AUC over 64,365 val and 244,647 test impressions. Paired bootstrap on shared
resamples, 1,000 draws: both arms are scored on the same resampled impressions so their
correlated errors cancel. Comparing two independent intervals instead would be far too
conservative and would hide real differences.

Stage two is worth about **+0.20 AUC**, and the val and test intervals overlap, so the result
generalises across the split boundary. That is the central quantitative claim of the assignment.

## The grid

One arm per feature removed, single-variable by construction, plus two reference points.

| arm | val delta | sig | test delta | sig |
|---|---|---|---|---|
| `stage1_only` | +0.1991 | yes | +0.2031 | yes |
| `pop_only` | +0.0535 | yes | +0.0605 | yes |
| `minus_pop_causal` | +0.0363 | yes | +0.0403 | yes |
| `minus_cat_match` | +0.0038 | yes | +0.0047 | yes |
| `minus_bm25` | +0.0009 | yes | +0.0008 | yes |
| `minus_emb` | -0.0001 | no | +0.0010 | yes |
| `minus_engage_sim` | +0.0002 | no | +0.0012 | yes |
| `minus_age_hours` | -0.0002 | no | +0.0012 | yes |
| `minus_hist_len` | +0.0000 | no | +0.0006 | yes |
| `minus_user_scroll` | -0.0004 | no | +0.0009 | yes |
| `minus_user_read` | -0.0006 | **yes, negative** | +0.0002 | no |
| `minus_recency` | -0.0004 | no | -0.0001 | no |

**`pop_causal` carries the system.** Removing it costs more than removing everything else
combined, and `pop_only` on its own recovers most of the gain. The two-stage advantage is
substantially a causal-popularity story, which is also why the re-ranker is better on cold users
than warm ones: its strongest feature needs no history at all.

**Most features are individually near-zero.** That is expected in a gradient-boosted ensemble
with correlated inputs: removing one lets the others absorb its signal. The correct reading is
that `pop_causal` and `cat_match` carry distinct signal and the rest are largely redundant, not
that eight features are useless.

**Val and test disagree on the small effects, and the disagreement is systematic.** Almost every
arm is significant on test and not on val, because test has 3.8x the impressions and therefore
much tighter intervals. Where the sign is stable and only the significance changes, the honest
reading is underpowered on val, not absent.

`minus_user_read` is the one real conflict: significantly **negative** on val (removing it helps
by 0.0006) and not significant on test. It is a candidate for removal, but on this evidence the
case rests on a val-only effect smaller than the val/test gap, so it is kept in the submitted
model rather than dropped on that evidence.

## What the leak fix changed

The engagement leak (FACTS section 10) put future clicks into `engage_sim`, `user_read` and
`user_scroll` on train and val. Re-running the grid on clean features moved three things:

| | contaminated | clean |
|---|---|---|
| full, val | 0.7575 | 0.7489 |
| full, test | 0.7429 | **0.7461** |
| `minus_engage_sim`, val | +0.0085, significant | +0.0002 [-0.0004, +0.0009], **not significant** |
| `stage1_only`, val | +0.2077 | +0.1991 |

**`engage_sim`'s entire published value was the leak.** Its +0.0085 was the single largest
per-feature effect after popularity and category, and on clean history the interval straddles
zero. The read-time-weighted user vector does not beat the uniform one inside the ranker, which
was the whole question that feature existed to answer.

**Test performance went up, not down.** Test features were already correct, since the test split
is drawn from the same block its history comes from. The only thing that changed is the model,
which now trains on clean features. Removing the leak therefore improved genuine generalisation
by +0.0032, which is the opposite of the usual "the number was inflated" story and worth saying
plainly.

**A consistency check worth recording.** `stage1_only` (0.5498) and `pop_only` (0.6954) came back
bit-identical to the contaminated run, because neither arm reads an engagement feature. The fix
changed exactly the arms it should have and nothing else.

## MIND: the same architecture, worth fourteen times less

MIND supports five of the ten features (see `q1-features-and-availability.md`). The same grid,
same trainer, same protocol:

| | EB-NeRD val | MIND val |
|---|---|---|
| full re-ranker | 0.7489 | 0.6512 |
| stage one alone | 0.5498 | 0.6372 |
| **two-stage gain** | **+0.1991 [+0.1963, +0.2020]** | **+0.0140 [+0.0120, +0.0159]** |

| MIND arm | val AUC | full - arm | 95% CI | sig |
|---|---|---|---|---|
| `pop_only` | 0.5475 | +0.1037 | [+0.1014, +0.1062] | yes |
| `minus_emb` | 0.6198 | +0.0313 | [+0.0298, +0.0329] | yes |
| `stage1_only` | 0.6372 | +0.0140 | [+0.0120, +0.0159] | yes |
| `minus_pop_causal` | 0.6434 | +0.0078 | [+0.0061, +0.0097] | yes |
| `minus_bm25` | 0.6466 | +0.0046 | [+0.0038, +0.0055] | yes |
| `minus_cat_match` | 0.6467 | +0.0045 | [+0.0036, +0.0054] | yes |
| `minus_hist_len` | 0.6505 | +0.0007 | [+0.0001, +0.0012] | yes |

Three contrasts, all of them results rather than disappointments:

**The two-stage gain is 14x smaller on MIND.** +0.0140 against +0.1991. This is the expected
consequence of the availability table: the EB-NeRD gain rests on behavioural features that MIND
does not have. Reporting a smaller number on a dataset with less signal is the measured contrast,
not a failure to reproduce.

**Feature importance inverts.** On EB-NeRD `pop_causal` dominates and `emb` is redundant; on MIND
`emb` dominates and `pop_causal` is worth a quarter as much. `pop_only` reaches 0.6954 on EB-NeRD
and only 0.5475 on MIND, barely above chance. Causal popularity is a strong signal in Danish news
over a two-day window and a weak one in MIND's corpus.

**Stage one is much stronger on MIND in absolute terms**, 0.6372 against 0.5498, so the re-ranker
has less headroom to begin with. The two effects compound: more of the achievable ranking is
already done by retrieval, and fewer features exist to improve on it.

## The 2026-09-14 feature round, and a methodological correction

Seven features added: within-impression transforms (`pop_rank`, `emb_rank`, `pop_rel_max`),
`ent_overlap`, `pop_24h` with `pop_velocity`, and `n_cands`.

| | EB-NeRD val | EB-NeRD test | MIND val | MIND test |
|---|---|---|---|---|
| 10 / 5 features | 0.7523 | 0.7523 | 0.6512 | 0.6539 |
| 17 / 12 features | **0.7636** | **0.7653** | 0.6539 | 0.6666 |

The headline two-stage gain is now **+0.2223 [+0.2209, +0.2238]** on EB-NeRD test and **+0.0293
[+0.0274, +0.0313]** on MIND test.

**On MIND none of the seven is significant on either split.** Reported as a result: the gains are
specific to EB-NeRD's corpus, not to the method.

**`n_cands` scores exactly 0.5000 as an isolated feature and is the second-most valuable feature
in the set** (+0.0066 test). Constant within an impression, so it cannot rank anything by itself;
it earns its place purely by letting the ranker calibrate how crowded an impression is.

### Leave-one-out cannot choose a feature set

The val grid marks `pop_causal` and `user_read` as significantly harmful individually. Removing
both together is significantly **worse** on both splits (-0.0005 val, -0.0007 test), and a
six-feature set built from only the significantly-positive features is worse by 0.024 test.

The two features are mutually substitutable: each compensates for the other's absence, so each
looks redundant alone and neither is. A leave-one-out ablation answers "what does this add given
everything else"; choosing what to keep needs whole-subset arms. Both were run and they disagree,
so this is a measured contradiction rather than a principle.

All 17 features ship. The prune candidates were selected on val only; consulting the test grid to
pick them would have made the reported test figure selection on its own data.

