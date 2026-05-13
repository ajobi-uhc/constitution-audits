#!/usr/bin/env python3
"""Show top scoring results from an EM run or sweep."""

import argparse
import json
from pathlib import Path


def load_results(path: Path) -> list:
    """Load results from a file or directory (handles sweep structure)."""
    entries = []

    if path.is_file():
        entries = [json.loads(line) for line in open(path) if line.strip()]
    elif path.is_dir():
        # Check for sweep structure: runs/run_*/results.jsonl
        runs_dir = path / "runs"
        if runs_dir.exists():
            for run_dir in sorted(runs_dir.iterdir()):
                results_file = run_dir / "results.jsonl"
                if results_file.exists():
                    for line in open(results_file):
                        if line.strip():
                            e = json.loads(line)
                            e.setdefault("run_id", run_dir.name)
                            entries.append(e)
        # Check for single run: results.jsonl
        elif (path / "results.jsonl").exists():
            entries = [json.loads(line) for line in open(path / "results.jsonl") if line.strip()]

    return entries


def parse_args():
    parser = argparse.ArgumentParser(description="Show top scoring results from an EM run or sweep")
    parser.add_argument("path", type=Path, help="Results directory or file")
    parser.add_argument("--n", type=int, default=10, help="Number of top results to show (default: 10)")
    parser.add_argument("--full", action="store_true", help="Print full prompts and responses (no truncation)")
    return parser.parse_args()


def main(path: Path, n: int, full: bool):
    entries = load_results(path)
    if not entries:
        print(f"No results found in: {path}")
        return 1

    entries.sort(key=lambda x: x.get("reward_score", 0), reverse=True)

    print(f"{'='*80}")
    print(f"TOP {n} of {len(entries)} | {path}")

    for i, e in enumerate(entries[:n], 1):
        score = e.get("reward_score", 0)
        run_id = e.get("run_id", "")
        run_str = f" | Run: {run_id}" if run_id else ""

        if full:
            query = e.get("query", "")
            response = e.get("response", "")
        else:
            query = e.get("query", "")[:300]
            response = e.get("response", "")[:300]

        reasoning = e.get("score_metadata", {}).get("reasoning", "")

        # Header with ==== separator
        print(f"\n{'='*80}")
        print(f"#{i} | Score: {score:.0f} | Iter: {e.get('iteration', '?')}{run_str}")

        # User query
        print("-" * 80)
        print(f"[User]")
        print(f"{query}{'...' if not full and len(e.get('query', '')) > 300 else ''}")

        # Assistant response
        print("-" * 80)
        print(f"[Assistant]")
        print(f"{response}{'...' if not full and len(e.get('response', '')) > 300 else ''}")

        # Judge reasoning
        if reasoning:
            print("-" * 80)
            print(f"[Judge]")
            print(f"{reasoning}")

    print(f"\n{'='*80}")
    return 0


if __name__ == "__main__":
    args = parse_args()
    exit(main(args.path, args.n, args.full))
