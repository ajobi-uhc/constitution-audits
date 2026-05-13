#!/usr/bin/env python3
"""
Extract and compare judge scores from three sets of under18 transcripts.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
import statistics

# Directories
OLD_15_TURN = "/Users/aryajakkli/Code/petri/openai_spec_outputs/gpt51_under18/"
NEW_15_TURN = "/Users/aryajakkli/Code/petri/openai_spec_outputs/gpt51_audit/test/"
NEW_30_TURN = "/Users/aryajakkli/Code/petri/openai_spec_outputs/gpt51_under18_30turns/"

# Scores to extract
SCORE_NAMES = [
    "concerning",
    "disappointing",
    "needs_attention",
    "admirable",
    "scenario_realism",
    "high_stakes_refusal_or_caution",
    "overrefusal"
]

# Scores to show in comparison table
COMPARISON_SCORES = [
    "concerning",
    "disappointing",
    "needs_attention",
    "scenario_realism",
    "admirable"
]


def extract_scores(transcript_path: Path) -> Optional[Dict[str, float]]:
    """Extract scores from a transcript JSON file."""
    try:
        with open(transcript_path, 'r') as f:
            data = json.load(f)

        # Navigate to metadata.judge_output.scores
        scores = data.get('metadata', {}).get('judge_output', {}).get('scores', {})

        if not scores:
            print(f"Warning: No scores found in {transcript_path}")
            return None

        return {score: scores.get(score) for score in SCORE_NAMES}

    except FileNotFoundError:
        print(f"Warning: File not found: {transcript_path}")
        return None
    except json.JSONDecodeError:
        print(f"Warning: Invalid JSON in {transcript_path}")
        return None
    except Exception as e:
        print(f"Warning: Error reading {transcript_path}: {e}")
        return None


def get_tenet_files(directory: str) -> List[str]:
    """Get sorted list of transcript files (T8.X.json)."""
    path = Path(directory)
    files = sorted([f.name for f in path.glob("transcript_T8.*.json")])
    return files


def main():
    # Get all tenet files from the first directory
    tenet_files = get_tenet_files(OLD_15_TURN)

    if not tenet_files:
        print("Error: No transcript files found in OLD_15_TURN directory")
        return

    print(f"Found {len(tenet_files)} transcript files\n")

    # Extract scores from all three directories
    old_15_scores = {}
    new_15_scores = {}
    new_30_scores = {}

    for filename in tenet_files:
        # Extract tenet identifier (e.g., "T8.1")
        tenet_id = filename.replace("transcript_", "").replace(".json", "")

        old_15_scores[tenet_id] = extract_scores(Path(OLD_15_TURN) / filename)
        new_15_scores[tenet_id] = extract_scores(Path(NEW_15_TURN) / filename)
        new_30_scores[tenet_id] = extract_scores(Path(NEW_30_TURN) / filename)

    # Print comparison table
    print("=" * 120)
    print("PER-TENET COMPARISON TABLE")
    print("=" * 120)
    print()

    # Header
    header = f"{'Tenet':<10}"
    for score in COMPARISON_SCORES:
        header += f"| {score.replace('_', ' ').title():<12} "
    print(header)
    print(f"{'':10}| {'OLD 15t':<4} {'NEW 15t':<4} {'NEW 30t':<4} " * len(COMPARISON_SCORES))
    print("-" * 120)

    # Data rows
    for tenet_id in sorted(tenet_files, key=lambda x: float(x.replace("transcript_T8.", "").replace(".json", ""))):
        tenet_id = tenet_id.replace("transcript_", "").replace(".json", "")

        row = f"{tenet_id:<10}"

        for score in COMPARISON_SCORES:
            old_val = old_15_scores.get(tenet_id, {})
            new_15_val = new_15_scores.get(tenet_id, {})
            new_30_val = new_30_scores.get(tenet_id, {})

            old_score = old_val.get(score) if old_val else None
            new_15_score = new_15_val.get(score) if new_15_val else None
            new_30_score = new_30_val.get(score) if new_30_val else None

            old_str = f"{old_score:>4.1f}" if old_score is not None else "  - "
            new_15_str = f"{new_15_score:>4.1f}" if new_15_score is not None else "  - "
            new_30_str = f"{new_30_score:>4.1f}" if new_30_score is not None else "  - "

            row += f"| {old_str} {new_15_str} {new_30_str} "

        print(row)

    print()
    print("=" * 120)
    print("AVERAGES ACROSS ALL TENETS")
    print("=" * 120)
    print()

    # Calculate averages for each score
    print(f"{'Score':<30} | {'OLD 15-turn':<12} | {'NEW 15-turn':<12} | {'NEW 30-turn':<12}")
    print("-" * 80)

    for score in SCORE_NAMES:
        # Collect non-None values
        old_vals = [s.get(score) for s in old_15_scores.values() if s and s.get(score) is not None]
        new_15_vals = [s.get(score) for s in new_15_scores.values() if s and s.get(score) is not None]
        new_30_vals = [s.get(score) for s in new_30_scores.values() if s and s.get(score) is not None]

        old_avg = statistics.mean(old_vals) if old_vals else None
        new_15_avg = statistics.mean(new_15_vals) if new_15_vals else None
        new_30_avg = statistics.mean(new_30_vals) if new_30_vals else None

        old_str = f"{old_avg:>6.2f} (n={len(old_vals):>2})" if old_avg is not None else "    -"
        new_15_str = f"{new_15_avg:>6.2f} (n={len(new_15_vals):>2})" if new_15_avg is not None else "    -"
        new_30_str = f"{new_30_avg:>6.2f} (n={len(new_30_vals):>2})" if new_30_avg is not None else "    -"

        print(f"{score.replace('_', ' ').title():<30} | {old_str:<12} | {new_15_str:<12} | {new_30_str:<12}")

    print()


if __name__ == "__main__":
    main()
