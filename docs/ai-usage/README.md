# AI usage log

A2 Q7.4 asks for three things: all prompts, chat history exports, and a marking of AI-generated
against human-written code. This directory holds all three.

Three sessions were used to build this assignment and all three are exported here. Files are
named `transcript-<owner>-<session>.md`: the sessions overlap in date, so the date alone does not
identify one, and the session id is what the raw log is named, which keeps each file traceable
back to its source.

| file | owner | dates | prompts | replies | tool calls |
|---|---|---|---|---|---|
| [transcript-yash-8940d1d4.md](transcript-yash-8940d1d4.md) | Yash | 09-04 to 09-16 | 14 | 251 | 619 |
| [transcript-naman-5f1e2a9d.md](transcript-naman-5f1e2a9d.md) | Naman | 09-08 to 09-16 | 108 | 432 | 701 |
| [transcript-naman-6a2b339e.md](transcript-naman-6a2b339e.md) | Naman | 09-03 to 09-16 | 54 | 306 | 417 |

Session `6a2b339e` is the earliest and ran across the first week: the A1 port and its three path
bugs, the Q1 feature builder, the Q2 re-ranker and its ablation grid, Q9, the vacuous-test audit,
and the cluster environment work, before handing off. Totals across all three: **176 prompts,
989 assistant replies, 1,737 tool calls.**

| file | what it is |
|---|---|
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

Across 61 commits: **38 carry an AI trailer, 23 do not.** By area, counting commits that touched
each path:

| area | AI-assisted | no trailer |
|---|---|---|
| `src/eval/` | 10 | 0 |
| `src/retrieval/` | 5 | 1 |
| `src/pipeline/` | 8 | 3 |
| `src/features/` | 1 | 8 |
| `src/rerank/` | 1 | 5 |
| `src/models/` | 0 | 2 |
| `src/baseline/` | 1 | 0 |
| `tests/` | 3 | 3 |
| `docs/design-note/` | 3 | 0 |
| `docs/FACTS.md` | 18 | 6 |

**This table understates AI involvement, and it does so worst exactly where involvement was
highest. Read the numbers with that correction applied.**

`src/features/`, `src/rerank/`, `src/models/` and `src/baseline/` show mostly "no trailer", which
reads as hand-written. That is wrong. All of that code was generated in conversation with Claude
Code, in session `6a2b339e`: the feature builder, the leaky-feature arm for Q9, the lambdarank
re-ranker, the ablation grid and the history sweep were written by the model and reviewed by
Naman, not the other way round. Those commits simply did not carry the trailer, because the
convention was adopted partway through and was applied unevenly after that.

So the trailer is a **lower bound on AI involvement, not a measure of it**, and the honest summary
is that essentially all of `src/` was AI-written and human-reviewed. The evaluation harness, the
serving benchmark and the design note happen to carry the trailer; the feature and re-ranker code
does not, and the difference records which session logged it rather than who wrote it.

**One further caveat.** The unit is the commit, not the line, so a commit that is one AI-written
function beside twenty hand-edited lines counts the same as one that is entirely generated. The
three transcripts are the primary evidence here; this table is a summary of the git history, and
where the two disagree the transcripts are what actually happened.

Nothing in `src/` was accepted without being run. The leakage tests in `tests/` are the strongest
version of that claim, because each one was verified by injecting a violation and watching it fail
before it was trusted.

## What is redacted, and why

The transcript is redacted before it enters this repository. Three categories, all required by our
own working rules:

| redaction | yash-8940d1d4 | naman-5f1e2a9d | naman-6a2b339e | why |
|---|---|---|---|---|
| `[REDACTED LINE: ...]` | 12 | 6 | 7 | the line referred to a **classmate's** Assignment-1 system, discussed in our private notes as a comparison. It is a third party's work and none of it is ours to publish. |
| `/[CLUSTER-HOME]` | 7 | 43 | 29 | home paths on shared university infrastructure |
| `[SSH-CREDENTIAL]` | 2 | 2 | 3 | key paths |
| `[CLUSTER-HOST]` | 0 | 5 | 1 | hostname |
| `[CLUSTER-ACCOUNT]` | 0 | 0 | 1 | account |
| `[GPU-NODE]` | 0 | 19 | 19 | compute node names |
| `[EMAIL]` | 1 | 0 | 1 | personal addresses |

Counts differ by session because the sessions did different work: `5f1e2a9d` and `6a2b339e` drove
the cluster heavily, so they carry most of the path and node redactions, while `8940d1d4` did more
of the comparison against our private notes and carries most of the peer-line drops.

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

A naive grep of the three transcripts turns up three apparent survivors, and they are worth naming
so nobody has to wonder:

| file | line | the string | what it actually is |
|---|---|---|---|
| `transcript-yash-8940d1d4.md` | 7088 | a hostname-shaped pattern | the argument to a verification loop that proves nothing leaked |
| `transcript-yash-8940d1d4.md` | 7159 | `\.ssh/` and `@gmail` | the literal regex patterns in the audit command, not a key path and not an address |
| `transcript-naman-6a2b339e.md` | 7076 | `.ac.in`, `/home\d`, `id_ed25519`, `gnode\d` | a prompt listing the patterns to re-scan for after exporting |

All three are **search patterns inside the audit of the redaction itself**. The redactor's host
rule requires a label before the dot, so a bare `.ac.in` written as a pattern does not match, which
is correct behaviour rather than a miss. We left them rather than scrub the evidence that the audit
happened.

## Tool results are not included

The export carries prompts, replies, reasoning and tool **calls**. It omits tool **results**: 3.8 MB
of command output, file contents and test logs. Every artifact they produced is tracked in this
repository already, so including them would duplicate the repo inside a log of how the repo was
made. Long tool arguments are truncated with the omitted character count shown.

## Regenerating

```bash
OWNER='<name>' PEER_TERMS='<term>' python3 docs/ai-usage/export_transcript.py \
    <session>.jsonl docs/ai-usage/transcript-<owner>-<session>.md
python3 docs/ai-usage/test_redaction.py
```

The raw session logs live outside this repository, under Claude Code's own project directory. They
are **not committed**: they are unredacted.
