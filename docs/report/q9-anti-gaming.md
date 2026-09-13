# Q9: what the system declines to take

*Owner: Naman. Comparison in `src/rerank/q9.py`, results in
`results/q9_ebnerd_small_val.json`. Measured on clean features.*

## The comparison

The brief asks what the system would gain from features it cannot have at serving time. Both arms
are the same ranker on the same rows in the same order; the only difference is which columns the
model may read.

- **Causal arm, shipped.** Uses `pop_causal`, which counts only clicks strictly before the
  impression.
- **Leaky arm, not shipped.** Adds the article lifetime aggregates `total_inviews`,
  `total_pageviews` and `total_read_time`. These summarise an article's entire lifetime, so
  relative to any impression they include the future and cannot exist at serving time.

| | val per-impression AUC |
|---|---|
| causal only, shipped | 0.7489 |
| plus lifetime aggregates | 0.7753 |
| **difference** | **+0.0264 [+0.0249, +0.0277]**, significant |

Both arms read the same file, so the rows and their order are identical. Reading different files
would risk a different row order and silently break the pairing.

## Why the small number is the interesting part

A1 framed lifetime popularity as worth +0.042 to +0.075 AUC and treated giving it up as the real
cost of building an honest system. At single-retriever level that was true.

At two-stage level it is not. The leak buys **+0.0264**, while stage two over stage one buys
**+0.1991** on the same split. The causal behavioural axis is worth about **7.5 times** the leak.

So the honest system is not paying a meaningful price. The leak only looked expensive when the
comparison was between single-signal retrievers, where there was nothing else carrying the
ranking. Once a re-ranker with causal popularity exists, the future-looking columns are close to
redundant with what can be computed legitimately.

That is the answer to give in a viva: we decline the leak, and we can say exactly what declining
costs, and it is small for a reason that is structural rather than lucky.

## The number moved when the leak was fixed, and moved the right way

This figure was +0.0222 before the engagement leak fix. It is now +0.0264, a wider gap.

The reason is worth stating because it looks backwards. Fixing the leak **lowered** the honest
arm, from 0.7575 to 0.7489, since part of its measured quality had been future clicks in
`engage_sim`, `user_read` and `user_scroll`. The leaky arm fell less, because it still has the
lifetime aggregates. So the gap between honest and leaky widened even though the system as a
whole became more honest.

The conclusion is unchanged and slightly stronger: even at +0.0264, the leak is a small fraction
of what the causal system already achieves.

## MIND cannot run this comparison

`total_inviews`, `total_pageviews` and `total_read_time` are **100% null across all 65,238 MIND
articles**. The leaky arm has no source columns there, so this is an EB-NeRD result and is
reported as one. `q9.py` refuses to run on a dataset with no leaky feature file rather than
silently comparing a model against itself.
