# Q1: the feature set, and what each dataset can actually support

*Owner: Naman. Feature definitions in `src/features/build.py`, availability enforced by
`DATASET_FEATURES` in the same file. Ledger rows in `docs/FACTS.md`.*

## The ten features

All ten are computable strictly before their impression's own timestamp. That boundary is
enforced by construction rather than by care, and asserted in `tests/test_features_leakage.py`.

| feature | source | what it measures |
|---|---|---|
| `bm25` | stage-one retrieval score | lexical match between the user's history text and the candidate |
| `emb` | document embeddings | cosine between a uniform-weighted user vector and the candidate |
| `pop_causal` | click log, strict `< t` cut | how many clicks the candidate had already received |
| `age_hours` | `published_time` | hours between publication and the impression |
| `recency` | `published_time` | `age_hours` as a 24 h half-life decay rather than raw |
| `cat_match` | article category | whether the candidate's category appears in the user's history |
| `hist_len` | impression history | how much history the user has, a confidence proxy |
| `user_read` | `read_time_fixed` | mean seconds the user spent on past clicks |
| `user_scroll` | `scroll_percentage_fixed` | mean scroll completion on past clicks |
| `engage_sim` | history plus embeddings | cosine to a read-time-weighted user vector |

`recency` exists separately from `age_hours` because clicks fall off sharply in the first hours,
and a linear age lets a month-old article sit numerically close to a day-old one. The half-life
is a chosen constant, not a swept one, and is listed as such in the open-questions section.

## Availability is not the same on both datasets

**Five of the ten cannot exist on MIND.** This is a property of the corpus, not a gap in the
implementation, and it is stated per dataset rather than left to whatever the columns happen to
contain. `info.md` section 5 is the spec: any behavioural feature widens the gap between what the
two systems can do, so the two configurations are kept explicitly separate and reported, rather
than presented as one system that is quietly two different models.

| feature | EB-NeRD | MIND | why not |
|---|---|---|---|
| `bm25` | yes | yes | |
| `emb` | yes | yes | |
| `pop_causal` | yes | yes | derived from the click log itself, which both have |
| `cat_match` | yes | yes | MIND categories are fully populated, 0 of 65,238 null |
| `hist_len` | yes | yes | history article ids are present |
| `age_hours` | yes | **no** | `published_time` is 100% null on all 65,238 MIND articles |
| `recency` | yes | **no** | same, it is a transform of `age_hours` |
| `user_read` | yes | **no** | MIND has no `history.parquet` and no read-time column |
| `user_scroll` | yes | **no** | same, and no scroll column exists in MIND at all |
| `engage_sim` | yes | **no** | needs read-time weights, so it degenerates to `emb` |

Two consequences worth stating in the viva rather than hiding:

1. **The Q9 leaky arm cannot exist on MIND either.** The lifetime aggregates
   (`total_inviews`, `total_pageviews`, `total_read_time`) are also 100% null there, so the
   "what we decline to take" comparison is an EB-NeRD result and cannot be reproduced on MIND.
2. **Expect the behavioural axis to be worth far less on MIND.** EB-NeRD's two-stage gain of
   +0.2049 test AUC rests heavily on features MIND does not have. A smaller gain on a dataset
   with less signal is a measured contrast, not a failure.

## The failure mode this guards against

The natural implementation emits all ten columns everywhere and lets the five unavailable ones
fill with nulls or zeros. LightGBM cannot tell a column of zeros from a real feature, so the
MIND system would silently train on five dead inputs and report a plausible number.

`build.py` now selects `features_for(dataset)` and then asserts that every feature it claims to
emit is neither all-null nor constant, failing loudly if one is. The assertion is checked against
EB-NeRD, where all ten are non-constant with zero nulls.

One MIND-specific trap is worth recording because it defeats the obvious check.
`history_timestamps` on MIND is a **null list** of dtype `List(Datetime)`, not an empty list and
not `Null`. So `.list.len()` returns null rather than 0, and a filter for `list.len() == 0`
matches nothing and looks like healthy data. That is the exact shape that let an earlier MIND
leakage test report green over 95,071 rows while checking none of them.
