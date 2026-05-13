#!/usr/bin/env python3
"""Upload SURF pipeline outputs to HuggingFace Hub.

Usage:
    uv run utils/upload_to_hf.py data/tulu --repo-prefix your-username/tulu

This creates two datasets:
    - {repo-prefix}: Minimal dataset for running SURF (prompt + sae_attributes)
    - {repo-prefix}-full: Complete dataset with all fields + extras (centroids, summaries)

Edit utils/hf_upload_config.py to customize metadata and README templates.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from datasets import Dataset
from dotenv import load_dotenv
from huggingface_hub import HfApi

from hf_upload_config import get_full_readme, get_minimal_readme

# Load .env file for HF_TOKEN
load_dotenv()


def load_jsonl(path: Path) -> list:
    """Load JSONL file."""
    records = []
    with open(path) as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def upload_minimal(data_dir: Path, repo_id: str, token: str = None, private: bool = False):
    """Upload minimal dataset (just what's needed to run SURF).

    Fields: prompt, sae_attributes
    """
    pseudo_sae_file = data_dir / "pseudo_sae_attributes.jsonl"
    if not pseudo_sae_file.exists():
        print(f"  Skipping: {pseudo_sae_file} not found")
        return False

    print(f"  Loading {pseudo_sae_file}...")
    records = load_jsonl(pseudo_sae_file)
    print(f"  Loaded {len(records)} records")

    # Extract only the fields needed for running SURF
    minimal_records = []
    for r in records:
        minimal_records.append({
            "prompt": r.get("prompt", ""),
            "sae_attributes": r.get("sae_attributes", []),
        })

    ds = Dataset.from_list(minimal_records)

    print(f"  Pushing to {repo_id}{' (private)' if private else ''}...")
    ds.push_to_hub(repo_id, token=token, private=private)

    # Add README
    api = HfApi(token=token)
    readme = get_minimal_readme(repo_id)

    readme_path = data_dir / "_tmp_README.md"
    with open(readme_path, "w") as f:
        f.write(readme)

    api.upload_file(
        path_or_fileobj=str(readme_path),
        path_in_repo="README.md",
        repo_id=repo_id,
        repo_type="dataset",
    )
    readme_path.unlink()

    print(f"  Done: https://huggingface.co/datasets/{repo_id}")
    return True


def upload_full(data_dir: Path, repo_id: str, token: str = None, private: bool = False):
    """Upload full dataset with all fields + extras."""
    pseudo_sae_file = data_dir / "pseudo_sae_attributes.jsonl"
    summaries_file = data_dir / "cluster_summaries.jsonl"
    centroids_file = data_dir / "centroids.npy"
    metadata_file = data_dir / "embedding_metadata.json"

    if not pseudo_sae_file.exists():
        print(f"  Skipping: {pseudo_sae_file} not found")
        return False

    print(f"  Loading {pseudo_sae_file}...")
    records = load_jsonl(pseudo_sae_file)
    print(f"  Loaded {len(records)} records")

    ds = Dataset.from_list(records)

    print(f"  Pushing dataset to {repo_id}{' (private)' if private else ''}...")
    ds.push_to_hub(repo_id, token=token, private=private)

    # Upload additional files
    api = HfApi(token=token)

    # Collect info for README
    centroids_shape = None
    embedding_model = None

    # Upload centroids.npy if exists
    if centroids_file.exists():
        print(f"  Uploading centroids.npy...")
        centroids = np.load(centroids_file)
        centroids_shape = centroids.shape
        api.upload_file(
            path_or_fileobj=str(centroids_file),
            path_in_repo="centroids.npy",
            repo_id=repo_id,
            repo_type="dataset",
        )

        # Load embedding model info
        if metadata_file.exists():
            with open(metadata_file) as f:
                embed_info = json.load(f)
                embedding_model = embed_info.get("embedding_model", "unknown")

        # Upload metadata
        meta = {
            "n_clusters": int(centroids.shape[0]),
            "embedding_dim": int(centroids.shape[1]),
            "embedding_model": embedding_model or "unknown",
        }
        meta_path = data_dir / "_tmp_metadata.json"
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

        print(f"  Uploading metadata.json...")
        api.upload_file(
            path_or_fileobj=str(meta_path),
            path_in_repo="metadata.json",
            repo_id=repo_id,
            repo_type="dataset",
        )
        meta_path.unlink()

    # Upload cluster summaries if exists
    has_summaries = False
    if summaries_file.exists():
        has_summaries = True
        print(f"  Uploading cluster_summaries.jsonl...")
        api.upload_file(
            path_or_fileobj=str(summaries_file),
            path_in_repo="cluster_summaries.jsonl",
            repo_id=repo_id,
            repo_type="dataset",
        )

    # Build README using config
    minimal_repo = repo_id.replace("-full", "")
    readme = get_full_readme(
        repo_id=repo_id,
        minimal_repo=minimal_repo,
        centroids_shape=centroids_shape,
        embedding_model=embedding_model,
        has_summaries=has_summaries,
    )

    readme_path = data_dir / "_tmp_README.md"
    with open(readme_path, "w") as f:
        f.write(readme)

    api.upload_file(
        path_or_fileobj=str(readme_path),
        path_in_repo="README.md",
        repo_id=repo_id,
        repo_type="dataset",
    )
    readme_path.unlink()

    print(f"  Done: https://huggingface.co/datasets/{repo_id}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Upload SURF outputs to HuggingFace Hub")
    parser.add_argument("data_dir", type=Path, help="Output directory from prepare-dataset")
    parser.add_argument("--repo-prefix", required=True, help="HuggingFace repo prefix (e.g., username/tulu)")
    parser.add_argument("--token", help="HuggingFace token (or set HF_TOKEN env var)")
    parser.add_argument("--private", action="store_true", help="Create private repositories")
    parser.add_argument("--skip-minimal", action="store_true", help="Skip uploading minimal dataset")
    parser.add_argument("--skip-full", action="store_true", help="Skip uploading full dataset")
    args = parser.parse_args()

    if not args.data_dir.exists():
        print(f"Error: {args.data_dir} does not exist")
        return 1

    visibility = "private" if args.private else "public"
    print(f"Uploading from {args.data_dir} ({visibility})")
    print()

    if not args.skip_minimal:
        print("[1/2] Uploading minimal dataset...")
        upload_minimal(args.data_dir, args.repo_prefix, args.token, args.private)
        print()

    if not args.skip_full:
        print("[2/2] Uploading full dataset...")
        upload_full(args.data_dir, f"{args.repo_prefix}-full", args.token, args.private)
        print()

    print("All done!")
    print()
    print("Usage:")
    print(f"  uv run -m surf.cli.main sweep \\")
    print(f"      --attributes {args.repo_prefix} \\")
    print(f"      --rubric rubrics/rebuttal.yaml \\")
    print(f"      -o results/")
    return 0


if __name__ == "__main__":
    exit(main())
