"""
Update anthropic_constitution.md tenet descriptions with expanded inputs from soul_doc_audit.py.

Parses the eval script to extract Sample id -> input mappings, then replaces
the brief description after '— ' in each tenet line with the full expanded input.
"""

import ast
import os
import re
import sys


def extract_samples_from_eval(eval_path: str) -> dict[str, str]:
    """Parse the eval script and extract all Sample(id=..., input=...) mappings."""
    with open(eval_path) as f:
        source = f.read()

    tree = ast.parse(source)

    samples = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Check if this is a Sample() call
            func = node.func
            if isinstance(func, ast.Name) and func.id == "Sample":
                sample_id = None
                sample_input = None

                for kw in node.keywords:
                    if kw.arg == "id" and isinstance(kw.value, ast.Constant):
                        sample_id = kw.value.value
                    elif kw.arg == "input" and isinstance(kw.value, ast.Constant):
                        sample_input = kw.value.value

                if sample_id and sample_input:
                    samples[sample_id] = sample_input

    return samples


def normalize_tenet_id(tenet_id: str) -> str:
    """Normalize a tenet ID from the markdown format to the eval format.

    Markdown uses IDs like T11a, T12b, T210a etc (no dots).
    Eval uses IDs like T1.1a, T1.2b, T2.10a etc (with dots).
    The bold text in markdown uses the dotted format like **T1.1a**.
    """
    return tenet_id


def update_markdown(md_path: str, samples: dict[str, str], output_path: str):
    """Update tenet lines in the markdown file with expanded descriptions."""
    with open(md_path) as f:
        lines = f.readlines()

    # Pattern to match tenet lines:
    # - **T1.1a** <a id="T11a"></a> `tag1`, `tag2` · constitutions/anthropic_soul_doc.md:XXX-YYY — DESCRIPTION
    tenet_pattern = re.compile(
        r'^(- \*\*(?P<tenet_id>T[\d.]+[a-z]?)\*\* .+? — )(.+)$'
    )

    updated_lines = []
    matched = 0
    unmatched = []

    for line in lines:
        m = tenet_pattern.match(line.rstrip('\n'))
        if m:
            tenet_id = m.group('tenet_id')
            prefix = m.group(1)

            if tenet_id in samples:
                # Replace the description with the expanded input
                # Convert newlines to spaces for single-line markdown
                expanded = samples[tenet_id].replace('\n', ' ')
                # Collapse multiple spaces
                expanded = re.sub(r'  +', ' ', expanded)
                updated_lines.append(prefix + expanded + '\n')
                matched += 1
            else:
                unmatched.append(tenet_id)
                updated_lines.append(line)
        else:
            updated_lines.append(line)

    with open(output_path, 'w') as f:
        f.writelines(updated_lines)

    print(f"Updated {matched} tenet descriptions")
    if unmatched:
        print(f"WARNING: {len(unmatched)} tenets in markdown had no matching sample:")
        for tid in unmatched:
            print(f"  - {tid}")

    return matched


def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    eval_path = os.path.join(base, "claude_soul_doc_audits/soul_doc_audit.py")
    md_path = os.path.join(base, "tenets/anthropic_constitution.md")
    output_path = md_path  # overwrite in place

    print("Extracting samples from eval script...")
    samples = extract_samples_from_eval(eval_path)
    print(f"Found {len(samples)} samples")

    # Show a few sample IDs for verification
    sample_ids = sorted(samples.keys())
    print(f"Sample IDs: {sample_ids[:5]} ... {sample_ids[-5:]}")

    print(f"\nUpdating markdown file: {md_path}")
    matched = update_markdown(md_path, samples, output_path)

    # Verify a few entries
    print("\n--- Verification ---")
    for tenet_id in ["T1.1a", "T2.1a", "T5.1a"]:
        if tenet_id in samples:
            desc = samples[tenet_id][:120]
            print(f"\n{tenet_id} input starts with: {desc}...")


if __name__ == "__main__":
    main()
