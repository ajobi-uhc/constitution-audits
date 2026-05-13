"""Attribute sampling for the EM loop."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class AttributeFileLoader:
    """
    Loads and samples attributes from a HuggingFace dataset or local JSONL file.

    Supports two source types:
    1. HuggingFace dataset ID (e.g., "seoirsem/CHUNKY-tulu3-SFT-25k-attributes")
    2. Local JSONL file path (e.g., "./data/pseudo_sae_attributes.jsonl")

    Expected format (one JSON object per line or HF dataset row):
    {"prompt": "...", "response": "...", "sae_attributes": ["attr1", "attr2", ...]}

    The default attribute_column is "sae_attributes" which contains cluster
    summaries from the clustering pipeline. Use "attributes" for raw attributes.
    """

    def __init__(self, source: str, attribute_column: str = "sae_attributes"):
        """
        Initialize the loader.

        Args:
            source: HuggingFace dataset ID or path to local JSONL file
            attribute_column: Column name containing attributes
        """
        self.source = source
        self.attribute_column = attribute_column
        self.data: List[Dict[str, Any]] = []
        self._load_data()

    def _load_data(self):
        """Load data from HuggingFace or local file."""
        source_path = Path(self.source)

        # Detect HuggingFace dataset vs local file
        # HF datasets have "/" and don't exist as local paths
        if "/" in self.source and not source_path.exists():
            self._load_from_huggingface()
        else:
            self._load_from_file(source_path)

    def _load_from_huggingface(self):
        """Load from HuggingFace dataset."""
        from datasets import load_dataset

        print(f"Loading from HuggingFace: {self.source}")
        ds = load_dataset(self.source, split="train")

        for row in ds:
            record = dict(row)
            if self.attribute_column in record and record[self.attribute_column]:
                self.data.append(record)

        if not self.data:
            raise ValueError(f"No valid records found in HuggingFace dataset: {self.source}")

        print(f"Loaded {len(self.data)} records from HuggingFace: {self.source}")

    def _load_from_file(self, file_path: Path):
        """Load from local JSONL file."""
        if not file_path.exists():
            raise FileNotFoundError(f"Attribute file not found: {file_path}")

        with open(file_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    if self.attribute_column in record and record[self.attribute_column]:
                        self.data.append(record)
                except json.JSONDecodeError:
                    continue

        if not self.data:
            raise ValueError(f"No valid records found in {file_path}")

        print(f"Loaded {len(self.data)} records from {file_path}")

    def sample_random_entry(self) -> Dict[str, Any]:
        """
        Sample a random entry from the file.

        Returns:
            Dict with prompt, response, attributes, and source_index
        """
        idx = random.randint(0, len(self.data) - 1)
        entry = self.data[idx]
        return {
            "prompt": entry.get("prompt", ""),
            "response": entry.get("response", ""),
            "attributes": entry.get(self.attribute_column, []),
            "source_index": idx,
        }

    def sample_random_attributes(
        self,
        min_attrs: int = 1,
        max_attrs: int = 5,
    ) -> Dict[str, Any]:
        """
        Sample a random subset of attributes from a random entry.

        Args:
            min_attrs: Minimum number of attributes to sample
            max_attrs: Maximum number of attributes to sample

        Returns:
            Dict with attributes, prompt, response, and source_index
        """
        entry = self.sample_random_entry()
        attributes = entry["attributes"]

        # Sample random number of attributes
        num_attrs = min(random.randint(min_attrs, max_attrs), len(attributes))
        sampled_attrs = random.sample(attributes, num_attrs) if num_attrs > 0 else []

        return {
            "prompt": entry["prompt"],
            "response": entry["response"],
            "attributes": sampled_attrs,
            "source_index": entry["source_index"],
        }

    def __len__(self) -> int:
        return len(self.data)


def build_weighted_attribute_pool(
    replay_buffer_entries: List[Dict[str, Any]],
    score_key: str = "reward_score",
) -> Dict[str, float]:
    """
    Build a weighted pool of attributes from replay buffer entries.

    Higher-scoring entries contribute more weight to their attributes.

    Args:
        replay_buffer_entries: List of entries with attributes and scores
        score_key: Key for the score field

    Returns:
        Dict mapping attribute -> cumulative weight
    """
    weights: Dict[str, float] = {}

    for entry in replay_buffer_entries:
        score = entry.get(score_key, 0)
        if score <= 0:
            continue

        # Get attributes from various possible fields
        attrs = []
        for attr_field in ["attributes", "base_attributes", "weighted_attributes", "random_attributes"]:
            attrs.extend(entry.get(attr_field, []))

        for attr in attrs:
            if attr:
                weights[attr] = weights.get(attr, 0) + score

    return weights


def sample_weighted_attributes(
    weights: Dict[str, float],
    k: int,
) -> List[str]:
    """
    Sample k attributes weighted by their cumulative scores.

    Args:
        weights: Dict mapping attribute -> weight
        k: Number of attributes to sample

    Returns:
        List of sampled attributes
    """
    if not weights or k <= 0:
        return []

    attributes = list(weights.keys())
    weight_values = [weights[a] for a in attributes]
    total = sum(weight_values)

    if total <= 0:
        return random.sample(attributes, min(k, len(attributes)))

    # Normalize weights
    probs = [w / total for w in weight_values]

    # Sample without replacement
    k = min(k, len(attributes))
    sampled = []
    remaining_attrs = attributes.copy()
    remaining_probs = probs.copy()

    for _ in range(k):
        if not remaining_attrs:
            break

        # Normalize remaining probs
        total_prob = sum(remaining_probs)
        if total_prob <= 0:
            break
        norm_probs = [p / total_prob for p in remaining_probs]

        # Sample one
        r = random.random()
        cumsum = 0
        for i, p in enumerate(norm_probs):
            cumsum += p
            if r <= cumsum:
                sampled.append(remaining_attrs[i])
                remaining_attrs.pop(i)
                remaining_probs.pop(i)
                break

    return sampled


def sample_attributes_for_candidate(
    weighted_pool: Dict[str, float],
    attribute_loader: AttributeFileLoader,
    max_attributes: int = 5,
    exclusion_prob_by_k: Dict[int, float] = None,
) -> Dict[str, Any]:
    """
    Sample attributes for a candidate using binomial distribution.

    Combines weighted attributes from replay buffer with random attributes from file.

    Args:
        weighted_pool: Weighted attribute pool from replay buffer
        attribute_loader: AttributeFileLoader for random attributes
        max_attributes: Maximum total attributes
        exclusion_prob_by_k: Probability of excluding random attrs by k value

    Returns:
        Dict with sampled attributes and metadata
    """
    if exclusion_prob_by_k is None:
        # Default: more weighted attrs = less random attrs
        exclusion_prob_by_k = {0: 0.0, 1: 0.0, 2: 0.2, 3: 0.4, 4: 0.6, 5: 0.8}

    # Sample k from binomial(5, 0.5) - how many weighted attrs to use
    k = sum(random.random() < 0.5 for _ in range(5))

    # Sample weighted attributes
    weighted_attrs = sample_weighted_attributes(weighted_pool, k) if weighted_pool else []

    # Sample random attributes from file
    random_sample = attribute_loader.sample_random_attributes(min_attrs=1, max_attrs=5)
    random_attrs = random_sample["attributes"]

    # Apply exclusion probability based on k
    exclusion_prob = exclusion_prob_by_k.get(k, 0.0)
    random_attrs = [a for a in random_attrs if random.random() > exclusion_prob]

    # Combine and limit
    remaining_slots = max_attributes - len(weighted_attrs)
    random_attrs = random_attrs[:remaining_slots]

    all_attrs = weighted_attrs + random_attrs
    random.shuffle(all_attrs)
    all_attrs = all_attrs[:max_attributes]

    return {
        "attributes": all_attrs,
        "weighted_attributes": weighted_attrs,
        "random_attributes": random_attrs,
        "source_prompt": random_sample["prompt"],
        "source_index": random_sample["source_index"],
        "k_sampled": k,
        "exclusion_prob_used": exclusion_prob,
    }
