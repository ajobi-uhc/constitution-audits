"""Run a single moltbook audit tenet (T2.2a) directly, bypassing inspect_ai."""
import sys
sys.path.insert(0, "src")
sys.path.insert(0, ".")

import json
from pathlib import Path
from datetime import datetime

import look_at_logs; look_at_logs.start()

from moltbook_sim.agents import AgentConfig, WREN_IDENTITY
from moltbook_sim.auditor_prompt import build_auditor_system_prompt
from moltbook_sim.solver import _run_audit_conversation, _load_feed

# Get the seed instructions for T2.2a from the dataset
from claude_soul_doc_audits.soul_doc_audit import SECTION_MAP

dataset = SECTION_MAP["all"]
sample = next(s for s in dataset if s.id == "T2.2a")
seed_instructions = sample.input

print(f"Tenet T2.2a: {seed_instructions[:120]}...", flush=True)

MODEL = "anthropic/claude-sonnet-4.5"

auditor = AgentConfig(
    name="Petri",
    model=MODEL,
    emoji="🧫",
    system_prompt_override=build_auditor_system_prompt(
        seed_instructions,
        target_name="Wren",
        target_model=MODEL,
    ),
)
target = AgentConfig(
    name="Wren",
    model=MODEL,
    emoji="🐦",
    identity_md=WREN_IDENTITY,
)

feed_posts = _load_feed(None, 5, 42)

run_id = look_at_logs.new_run_id()
look_at_logs.set_run(run_id, name="moltbook T2.2a direct")

print(f"\nStarting audit: Petri vs Wren, 5 exchanges", flush=True)
print(f"Model: {MODEL}", flush=True)
print(flush=True)

result = _run_audit_conversation(
    auditor,
    target,
    feed_posts,
    seed=42,
    n_exchanges=5,
)

look_at_logs.set_run()

# Save result
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
out_path = Path(f"results/moltbook/moltbook_T2.2a_{ts}.json")
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(result, indent=2, default=str))
print(f"\nSaved to {out_path}")
