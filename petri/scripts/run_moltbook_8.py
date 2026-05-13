"""Run 8 moltbook audit tenets across sections."""
import sys
sys.path.insert(0, "src")
sys.path.insert(0, ".")

import look_at_logs; look_at_logs.start()

from inspect_ai import eval as inspect_eval
from moltbook_sim.eval import moltbook_audit

TENETS = "T2.2a,T3.2a,T6.1a,T7.3a,T8.3a,T12.1a,T13.1a,T17.2a"
MODEL = "openrouter/anthropic/claude-sonnet-4.5"
N_EXCHANGES = 10

task = moltbook_audit(
    section="all",
    sample_id=TENETS,
    n_exchanges=N_EXCHANGES,
)

print(f"Running {len(task.dataset)} tenets with {N_EXCHANGES} exchanges each")
print(f"Model: {MODEL} (both auditor and target)")
for s in task.dataset:
    print(f"  {s.id}: {s.input[:100]}...")
print()

results = inspect_eval(
    task,
    model=MODEL,
    model_roles={"auditor": MODEL, "target": MODEL},
)
print("\nDone!")
for r in results:
    print(f"  {r.status}")
