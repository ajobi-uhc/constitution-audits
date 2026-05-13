"""Re-parse UNKNOWN verdicts and handle missed R1 transcripts."""
import json
import re
import asyncio
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

import look_at_logs; look_at_logs.start()

load_dotenv()

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)
HAIKU_MODEL = "anthropic/claude-haiku-4.5"

def extract_verdict(text):
    """More robust verdict extraction."""
    patterns = [
        r'\*\*Verdict:\*\*\s*(CONFIRMED|BORDERLINE|FALSE_POSITIVE)',
        r'##\s*Verdict:\s*\*?\*?(CONFIRMED|BORDERLINE|FALSE_POSITIVE)',
        r'##\s*Decision:\s*\*?\*?(CONFIRMED|BORDERLINE|FALSE_POSITIVE)',
        r'Verdict:\s*\*?\*?(CONFIRMED|BORDERLINE|FALSE_POSITIVE)',
        r'Decision:\s*\*?\*?(CONFIRMED|BORDERLINE|FALSE_POSITIVE)',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1).upper()
    return "UNKNOWN"


def main():
    with open('scripts/lax_validation_sonnet45_results.json') as f:
        data = json.load(f)

    # Rebuild from raw data
    all_items = {}
    for tid, info in data.get('confirmed', {}).items():
        all_items[tid] = info
    for tid, info in data.get('false_positives', {}).items():
        all_items[tid] = info

    # Re-parse all verdicts
    confirmed = {}
    false_positives = {}
    still_unknown = {}

    for tid, info in all_items.items():
        resp = info.get('response', '')
        new_verdict = extract_verdict(resp)

        if new_verdict == 'CONFIRMED':
            confirmed[tid] = {**info, 'verdict': 'CONFIRMED'}
        elif new_verdict == 'FALSE_POSITIVE':
            false_positives[tid] = {**info, 'verdict': 'FALSE_POSITIVE'}
        elif new_verdict == 'BORDERLINE':
            # Shouldn't happen after R2 but just in case
            still_unknown[tid] = {**info, 'verdict': 'BORDERLINE'}
        else:
            still_unknown[tid] = info

    # Also check borderline_resolved
    for tid, info in data.get('borderline_resolved', {}).items():
        r2_resp = info.get('r2_response', '')
        new_verdict = extract_verdict(r2_resp)
        if new_verdict == 'CONFIRMED':
            confirmed[tid] = {'verdict': 'CONFIRMED', 'tenet_id': info['tenet_id'],
                            'tags': info['tags'], 'response': r2_resp}
        elif new_verdict == 'FALSE_POSITIVE':
            false_positives[tid] = {'verdict': 'FALSE_POSITIVE', 'tenet_id': info['tenet_id'],
                                   'tags': info['tags'], 'response': r2_resp}

    print("=== RE-PARSED RESULTS ===\n")
    print(f"Confirmed: {len(confirmed)}")
    for tid in sorted(confirmed):
        print(f"  {tid} — {', '.join(confirmed[tid].get('tags', []))}")

    print(f"\nFalse Positives: {len(false_positives)}")
    for tid in sorted(false_positives):
        print(f"  {tid} — {', '.join(false_positives[tid].get('tags', []))}")

    if still_unknown:
        print(f"\nStill Unknown: {len(still_unknown)}")
        for tid in sorted(still_unknown):
            resp = still_unknown[tid].get('response', '')
            print(f"  {tid}: {resp[:200]}")

    # Now check: which R1 transcripts were ERROR/UNKNOWN and never processed?
    with open('scripts/lax_phase0_sonnet45_output.json') as f:
        phase0 = json.load(f)

    all_flagged_ids = {item['tenet_id'] for item in phase0['newly_flagged']}
    processed_ids = set(confirmed.keys()) | set(false_positives.keys()) | set(still_unknown.keys())
    missed_ids = all_flagged_ids - processed_ids

    print(f"\n=== MISSED TRANSCRIPTS (R1 errors, never processed) ===")
    print(f"Count: {len(missed_ids)}")
    for tid in sorted(missed_ids):
        item = next(i for i in phase0['newly_flagged'] if i['tenet_id'] == tid)
        print(f"  {tid} — {', '.join(item['tags'])} — Core: {item['core_scores']}")

    # Save corrected results
    output = {
        "confirmed": confirmed,
        "false_positives": false_positives,
        "still_unknown": still_unknown,
        "missed_ids": sorted(missed_ids),
    }
    with open('scripts/lax_reparsed_results.json', 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved to scripts/lax_reparsed_results.json")


if __name__ == "__main__":
    main()
