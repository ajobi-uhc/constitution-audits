"""
Moltbook Audit — Red-team testing via simulated social platform.

The auditor (Petri) probes the target (Wren) through Moltbook comments,
using the same tenet dataset as soul_doc_audit.py.

Usage:
    inspect eval moltbook_sim/eval.py \
        --model-role auditor=openrouter/anthropic/claude-opus-4 \
        --model-role target=openrouter/anthropic/claude-sonnet-4.5 \
        -T section=honesty -T n_exchanges=15

    # With custom feed:
    inspect eval moltbook_sim/eval.py \
        --model-role auditor=openrouter/anthropic/claude-opus-4 \
        --model-role target=openrouter/anthropic/claude-sonnet-4.5 \
        -T section=priority -T feed_path=path/to/feed.json
"""

import copy
import json
import sys
from datetime import datetime
from pathlib import Path

import look_at_logs; look_at_logs.start()

# Ensure the project root is importable (for claude_soul_doc_audits)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from inspect_ai import Task, task
from inspect_ai.solver import TaskState

from claude_soul_doc_audits.soul_doc_audit import SECTION_MAP
from moltbook_sim.solver import moltbook_auditor
from moltbook_sim.scorer import moltbook_scorer


def _save_moltbook_transcripts(save_dir: str):
    """Cleanup function that saves moltbook conversation transcripts to disk."""

    async def cleanup(state: TaskState) -> None:
        result = state.metadata.get("moltbook_result")
        if not result:
            return

        out = Path(save_dir)
        out.mkdir(parents=True, exist_ok=True)

        sample_id = state.sample_id or "unknown"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = out / f"moltbook_{sample_id}_{ts}.json"
        path.write_text(json.dumps(result, indent=2, default=str))
        print(f"Saved moltbook transcript: {path}")

    return cleanup


@task
def moltbook_audit(
    section: str = "all",
    sample_id: str | None = None,
    n_exchanges: int = 25,
    feed_path: str | None = None,
    n_posts: int = 5,
    seed: int = 42,
    transcript_save_dir: str = "./moltbook_outputs",
):
    """
    Moltbook Audit — Red-team testing via simulated social platform.

    Args:
        section: Which tenet section to test (same as soul_doc_audit).
        sample_id: Run specific samples by ID. Comma-separated for multiple (e.g. "T2.2a,T6.1a,T12.1a").
        n_exchanges: Number of conversation rounds between agents.
        feed_path: Path to feed JSON. Uses bundled default if not provided.
        n_posts: Number of posts to sample from feed.
        seed: Random seed for reproducibility.
        transcript_save_dir: Directory to save conversation transcripts.

    Model Roles:
        auditor: The model that conducts the audit (Petri)
        target: The model being evaluated (Wren)
    """
    if section not in SECTION_MAP:
        raise ValueError(
            f"Unknown section: {section}. Valid: {list(SECTION_MAP.keys())}"
        )

    dataset = copy.deepcopy(SECTION_MAP[section])

    if sample_id:
        ids = [s.strip() for s in sample_id.split(",")]
        dataset = [s for s in dataset if s.id in ids]
        if not dataset:
            all_ids = [s.id for s in SECTION_MAP[section]]
            raise ValueError(
                f"No samples found for '{sample_id}' in section '{section}'. "
                f"Available: {all_ids[:10]}..."
            )

    return Task(
        dataset=dataset,
        solver=moltbook_auditor(
            n_exchanges=n_exchanges,
            feed_path=feed_path,
            n_posts=n_posts,
            seed=seed,
        ),
        scorer=moltbook_scorer(),
        cleanup=_save_moltbook_transcripts(transcript_save_dir),
    )
