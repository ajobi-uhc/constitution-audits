"""
CLI entry point: python -m moltbook_sim

Minimal — the real interface is the functions.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import look_at_logs; look_at_logs.start()

from .agents import AgentConfig, WREN_CONFIG, KESTREL_CONFIG, WREN_IDENTITY, KESTREL_IDENTITY, KESTREL_SOUL
from .runner import run_conversation


def main():
    parser = argparse.ArgumentParser(description="Multi-agent Moltbook sim")
    parser.add_argument("--exchanges", type=int, default=25)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--feed", type=str, required=True,
                        help="Path to feed JSON (list of {id, author_name, submolt_name, title, content, upvotes})")
    parser.add_argument("--posts", type=int, default=5,
                        help="Number of posts to sample from feed")
    parser.add_argument("--model", type=str, default="anthropic/claude-sonnet-4")
    parser.add_argument("--auditor-prompt", type=str, default=None,
                        help="Path to custom system prompt for auditor agent")
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    import random
    feed_path = Path(args.feed)
    with open(feed_path) as f:
        all_posts = json.load(f)
    rng = random.Random(args.seed)
    feed_posts = rng.sample(all_posts, min(args.posts, len(all_posts)))

    wren = AgentConfig(name="Wren", model=args.model, emoji="🐦", identity_md=WREN_IDENTITY)

    if args.auditor_prompt:
        prompt_text = Path(args.auditor_prompt).read_text()
        auditor = AgentConfig(name="Petri", model=args.model, emoji="🧫", system_prompt_override=prompt_text)
    else:
        auditor = AgentConfig(name="Kestrel", model=args.model, emoji="🪶", identity_md=KESTREL_IDENTITY, soul_md=KESTREL_SOUL)

    run_id = look_at_logs.new_run_id()
    look_at_logs.set_run(run_id, name=f"{wren.name} vs {auditor.name}")

    result = run_conversation(
        agents=[wren, auditor],
        feed_posts=feed_posts,
        seed=args.seed,
        n_exchanges=args.exchanges,
    )

    look_at_logs.set_run()

    out_path = args.output or f"moltbook_sim_seed{args.seed}.json"
    Path(out_path).write_text(json.dumps(result, indent=2, default=str))
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
