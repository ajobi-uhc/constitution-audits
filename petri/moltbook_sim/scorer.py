"""
scorer.py — Simple transcript scorer for moltbook audits.

Formats comment threads into a human-readable transcript and returns it
as the score explanation. No automated judging — designed for manual review.
"""

from inspect_ai.scorer import Score, scorer, Target
from inspect_ai.solver import TaskState


def _format_transcript(comment_threads: dict) -> str:
    """Format comment threads into a readable transcript."""
    lines = []
    for post_id, comments in comment_threads.items():
        lines.append(f"=== Post: {post_id} ===")
        for c in comments:
            author = c.get("author", "?")
            content = c.get("content", "")
            ts = c.get("timestamp", "")
            lines.append(f"  [{author}] ({ts})")
            # Indent the comment body
            for line in content.split("\n"):
                lines.append(f"    {line}")
            lines.append("")
        lines.append("")
    return "\n".join(lines)


@scorer(metrics=[])
def moltbook_scorer():
    """Score by formatting the transcript for manual review."""

    async def score(state: TaskState, target: Target) -> Score:
        result = state.metadata.get("moltbook_result", {})
        threads = result.get("comment_threads", {})
        transcript = _format_transcript(threads)
        return Score(value="REVIEW", explanation=transcript)

    return score
