"""Run a moltbook audit for specific tenets."""
import sys
sys.path.insert(0, "src")
sys.path.insert(0, ".")

import look_at_logs; look_at_logs.start()

from inspect_ai import eval as inspect_eval
from moltbook_sim.eval import moltbook_audit

SAMPLE_IDS = [
    "T2.2a",   # honesty — honest feedback on mediocre poem
    "T3.2a",   # helpfulness — treats user as capable adult
    "T6.1a",   # hard_constraints — CBRN absolute refusal
    "T7.3a",   # harm — consent to risky self-affecting info
    "T8.3a",   # dualuse — creative content with difficult themes
    "T12.1a",  # identity — identity destabilization
    "T13.1a",  # corrigibility — command to do something clearly wrong
    "T17.2a",  # roleplay — persona requiring dishonesty/harm
]

MODEL = "openrouter/anthropic/claude-sonnet-4.5"

task = moltbook_audit(
    section="all",
    sample_id=",".join(SAMPLE_IDS),
    n_exchanges=10,
)

print(f"Running {len(task.dataset)} samples with {MODEL}")
for s in task.dataset:
    print(f"  {s.id}: {s.input[:80]}")

inspect_eval(
    task,
    model=MODEL,
    model_roles={"auditor": MODEL, "target": MODEL},
)
