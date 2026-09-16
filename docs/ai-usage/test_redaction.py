"""Check that the transcript redactor removes what it must and nothing else.

Both directions, because a redactor that deletes everything passes a leak test exactly as
easily as a correct one does.

The fixtures below are fabricated. They match the shapes the patterns look for without using
any real hostname, username or node, since a test file lives in the graded repository too.

    python3 docs/ai-usage/test_redaction.py
"""
import os
import re
from pathlib import Path

os.environ.setdefault("PEER_TERMS", "example-peer-system")
src = Path(__file__).with_name("export_transcript.py").read_text().split("rows, stats")[0]
src = src.replace("SRC = sys.argv[1]", "SRC = None").replace("OUT = sys.argv[2]", "OUT = None")
ns: dict = {}
exec(src, ns)
clean = ns["clean"]

MUST_REMOVE = [
    "ssh someone@fake-cluster.example.ac.in and then log in",
    "PYTHONPATH=/home9/someuser/benchmark srun -w node99 --jobid 123",
    "the key at ~/.ssh/id_ed25519_something and ~/.ssh/config",
    "grep for '/home9/' as a bare pattern",
    "mail me at somebody@gmail.com",
    "we compared against example-peer-system, which scored higher",
    # The name written as a regex, which is how it leaked past a strict matcher seven times.
    "PEER = re.compile(r'example-?peer-?system', re.I)",
    "grep -c 'examplepeersystem' notes.md",
]
FORBIDDEN = [r"\.ac\.in", r"/home\d", r"node\d\d", r"id_ed25519", r"\.ssh/", r"@gmail",
             # Loose: the name is legible however the punctuation between its words is written.
             r"example[^a-z0-9]{0,3}peer[^a-z0-9]{0,3}system"]

MUST_KEEP = [
    "a normal line about BM25 and FAISS with no secrets",
    "per-impression AUC rose from 0.7653 to 0.7908 on the test split",
    "the node in the tree, node 5, is not a hostname",
]

leaks = []
for case in MUST_REMOVE:
    out = clean(case)
    for pat in FORBIDDEN:
        if re.search(pat, out):
            leaks.append((pat, case, out))
assert not leaks, f"redaction let something through: {leaks}"

damaged = [(c, clean(c)) for c in MUST_KEEP if clean(c) != c]
assert not damaged, f"redaction altered an innocent line: {damaged}"

# Non-vacuity: the fixtures must actually contain what we claim to be removing, or the first
# assertion passes because there was nothing there in the first place.
for pat in FORBIDDEN:
    assert any(re.search(pat, c) for c in MUST_REMOVE), f"no fixture exercises {pat}"

print(f"redaction verified: {len(MUST_REMOVE)} lines scrubbed, "
      f"{len(MUST_KEEP)} left intact, {len(FORBIDDEN)} patterns exercised")
