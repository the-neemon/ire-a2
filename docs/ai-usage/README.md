# AI usage log

A2 Q7.4 asks for three things: all prompts, chat history exports, and a marking of AI-generated
against human-written code. This directory holds all three.

| file | what it is |
|---|---|
| [transcript-yash.md](transcript-yash.md) | Yash's full session: 14 prompts verbatim, 251 assistant replies, 619 tool calls |
| `transcript-naman.md` | **pending.** Naman's session log, to be added and merged |
| [export_transcript.py](export_transcript.py) | the exporter, so the transcript can be regenerated from the raw session log |
| [test_redaction.py](test_redaction.py) | proves the redaction rules fire, and that they leave ordinary text alone |

## How AI was used

Both of us used **Claude Code** as a pair programmer throughout, not as a code generator we
accepted blind. The working pattern was consistent: we specified the experiment, it implemented and
ran it, and we checked the result against the ledgers before it was recorded. The measurements
themselves were never produced by the model. Every number in
[FACTS.md](../FACTS.md) was printed by code that ran on real data, and where a value is projected
rather than measured it is labelled as projected at the point of use.

It was most useful for the things this assignment is actually graded on: building the ablation
harness, keeping the paired-bootstrap discipline consistent across two datasets, and catching
inconsistencies between numbers recorded at different times. It was least reliable exactly where
you would expect, and the repository records those failures rather than hiding them:

- It proposed a bootstrap confidence interval for catalogue coverage that was **invalid**, and the
  invalidity only surfaced because the point estimate fell outside its own interval. The design
  note now reports coverage as a point estimate and uses the failure as a methodology note.
- It asserted that "every Python-side stage is flat in corpus size" in a draft of the Q4 section.
  The bench contradicted it. The claim was replaced with a measurement of the candidate pool.
- It diagnosed a failing anti-gaming test as needing an allow-list entry for `src/rerank/q9.py`.
  That diagnosis was **wrong**: the module never reads the columns, it only names them in a
  comment. Acting on it would have silently weakened the guard.

All three are written up in `FACTS.md` sections 19 and 20 as findings, because a wrong turn that
was caught and corrected is evidence about the process.

## Marking AI-generated against human-written code

Commits made with AI assistance carry a `Co-Authored-By: Claude` trailer, so the marking is
recoverable from the history itself rather than asserted here:

```bash
git log --format='%H %an' | while read h a; do
  git log -1 --format='%B' "$h" | grep -qi 'Co-Authored-By: Claude' \
    && echo "AI-assisted $a" || echo "human-only  $a"
done | sort | uniq -c
```

Across 59 commits: **37 AI-assisted, 22 without the trailer.** By area, counting commits that
touched each path:

| area | AI-assisted | no trailer |
|---|---|---|
| `src/eval/` | 10 | 0 |
| `src/retrieval/` | 5 | 1 |
| `src/pipeline/` | 8 | 3 |
| `src/features/` | 1 | 8 |
| `src/rerank/` | 1 | 5 |
| `tests/` | 4 | 3 |
| `docs/design-note/` | 3 | 0 |
| `docs/FACTS.md` | 18 | 6 |

Read that as a rough split of labour rather than a precise attribution. The evaluation harness, the
serving benchmark and the design note were written with heavy AI involvement. The feature builder
and the re-ranker were mostly hand-written by Naman, with AI used for review rather than authorship.

**Two honest caveats about this table.** First, the trailer is a **lower bound**: a commit without
it was not necessarily written without assistance, only without the trailer being added, and the
convention was adopted partway through. Naman's log will settle his side. Second, the unit is the
commit, not the line, so a commit that is one AI-written function beside twenty hand-edited lines
counts the same as one that is entirely generated.

Nothing in `src/` was accepted without being run. The leakage tests in `tests/` are the strongest
version of that claim, because each one was verified by injecting a violation and watching it fail
before it was trusted.

## What is redacted, and why

The transcript is redacted before it enters this repository. Three categories, all required by our
own working rules:

| redaction | count | why |
|---|---|---|
| `[REDACTED LINE: ...]` | 12 | the line referred to a **classmate's** Assignment-1 system, discussed in our private notes as a comparison. It is a third party's work and none of it is ours to publish. |
| `/[CLUSTER-HOME]` | 14 | home paths on shared university infrastructure |
| `[SSH-CREDENTIAL]` | 5 | key paths |
| `[EMAIL]` | 2 | personal addresses |
| `[CLUSTER-HOST]`, `[CLUSTER-ACCOUNT]`, `[GPU-NODE]` | 3 | hostname, account and compute node |

Redaction is applied **per line**, so one offending sentence costs one line rather than a whole
message. Prompts are otherwise reproduced in full and are never truncated.

`test_redaction.py` checks both directions, because a redactor that deletes everything passes a
leak test just as easily as a correct one:

```bash
python3 docs/ai-usage/test_redaction.py
```

It asserts three things: that six fabricated lines containing a hostname, a cluster path, a key
path, an address and a peer reference come back with none of them; that three ordinary lines
including one about BM25 and FAISS come back **unchanged**; and that each of the seven forbidden
patterns is actually present in some fixture, so the first assertion cannot pass by having nothing
to find. Its fixtures are invented, since a test file lives in the graded repository too.

### The redactor names nothing real

A redactor has to know what it is removing, so the obvious implementation hardcodes the hostname,
the usernames and the classmate's system name. That would **put all three back into the graded
repository**, which is exactly what the rule forbids. So the patterns here are generic: they match
`*.ac.in` rather than our host, `/home<N>/` rather than our home, and `id_ed25519` rather than our
key. Grep the two scripts for any real identifier and there are none.

The peer system's name cannot be generalised, because it is just a name, so it is **not in the repo
at all**. It is supplied at export time instead:

```bash
PEER_TERMS='<term>' python3 docs/ai-usage/export_transcript.py <session>.jsonl docs/ai-usage/transcript-yash.md
```

Re-exporting without `PEER_TERMS` reproduces everything except the peer-line redaction, so it must
be passed. The committed transcript was produced with it.

Two strings survive a naive grep of the transcript, at lines 7086 and 7157, and they are worth
naming so nobody has to wonder. They are the literal regex patterns `\.ssh/` and `@gmail` **inside
the verification commands that prove nothing leaked**. They are search patterns, not a key path and
not an address. We left them rather than scrub the evidence of the audit itself.

## Tool results are not included

The export carries prompts, replies, reasoning and tool **calls**. It omits tool **results**: 3.8 MB
of command output, file contents and test logs. Every artifact they produced is tracked in this
repository already, so including them would duplicate the repo inside a log of how the repo was
made. Long tool arguments are truncated with the omitted character count shown.

## Regenerating

```bash
PEER_TERMS='<term>' python3 docs/ai-usage/export_transcript.py <session>.jsonl docs/ai-usage/transcript-yash.md
python3 docs/ai-usage/test_redaction.py
```

The raw session logs live outside this repository, under Claude Code's own project directory. They
are **not committed**: they are unredacted.
