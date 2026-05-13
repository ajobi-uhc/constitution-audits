"""Build pseudo-SAE attributes from clustering results."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tqdm import tqdm


class PseudoSAEBuilder:
    """
    Build pseudo-SAE attributes from clustering results.

    Maps original attributes to cluster summaries and computes
    distance-based weights for sampling.
    """

    def __init__(self):
        """Initialize the builder."""
        pass

    def _load_cluster_summaries(
        self,
        summaries_path: Path,
    ) -> Dict[int, str]:
        """
        Load cluster summaries.

        Returns:
            Dict mapping cluster_id -> summary string
        """
        summaries: Dict[int, str] = {}
        with open(summaries_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    record = json.loads(line)
                    summaries[record["cluster_id"]] = record["summary"]
        return summaries

    def _load_cluster_stats(
        self,
        stats_path: Path,
    ) -> Dict[int, Dict[str, float]]:
        """
        Load cluster statistics (for max_distance).

        Returns:
            Dict mapping cluster_id -> stats dict
        """
        stats: Dict[int, Dict[str, float]] = {}
        with open(stats_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    record = json.loads(line)
                    stats[record["cluster_id"]] = {
                        "max_distance": record.get("max_distance", 1.0),
                        "mean_distance": record.get("mean_distance", 0.5),
                    }
        return stats

    def _load_assignments(
        self,
        assignments_path: Path,
    ) -> Dict[Any, Dict[str, List]]:
        """
        Load cluster assignments.

        Returns:
            Dict mapping record_id -> {cluster_ids: [...], distances: [...]}
        """
        assignments: Dict[Any, Dict[str, List]] = {}
        with open(assignments_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    record = json.loads(line)
                    assignments[record["id"]] = {
                        "cluster_ids": record["cluster_ids"],
                        "distances": record["distances"],
                    }
        return assignments

    def _load_clustering_metadata(
        self,
        clustering_dir: Path,
    ) -> Dict[str, Any]:
        """Load clustering metadata (includes embedding model info)."""
        metadata_path = clustering_dir / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                return json.load(f)
        return {}

    def _compute_weight(
        self,
        distance: float,
        max_distance: float,
    ) -> float:
        """
        Compute weight from distance.

        Uses formula: weight = (max_dist - dist) / max_dist
        Closer to centroid = higher weight.

        Args:
            distance: Distance to centroid
            max_distance: Maximum distance in cluster

        Returns:
            Normalized weight in [0, 1]
        """
        if max_distance <= 0:
            return 1.0

        weight = (max_distance - distance) / max_distance
        # Clamp to [0, 1]
        return max(0.0, min(1.0, weight))

    def build(
        self,
        attributes_path: str,
        clustering_dir: str,
        output_path: str,
    ) -> int:
        """
        Build pseudo-SAE attributes file.

        For each record:
        1. Look up cluster assignments
        2. Map each attribute -> cluster summary
        3. Compute weight based on distance

        Args:
            attributes_path: Path to original attributes.jsonl
            clustering_dir: Directory with clustering outputs
            output_path: Output path for pseudo_sae_attributes.jsonl

        Returns:
            Number of records processed
        """
        attributes_path = Path(attributes_path)
        clustering_dir = Path(clustering_dir)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print("Loading clustering data...")

        # Load cluster summaries
        summaries = self._load_cluster_summaries(
            clustering_dir / "cluster_summaries.jsonl"
        )
        print(f"  Loaded {len(summaries)} cluster summaries")

        # Load cluster stats
        stats = self._load_cluster_stats(
            clustering_dir / "cluster_stats.jsonl"
        )
        print(f"  Loaded {len(stats)} cluster stats")

        # Load assignments
        assignments = self._load_assignments(
            clustering_dir / "assignments.jsonl"
        )
        print(f"  Loaded {len(assignments)} record assignments")

        # Process each record
        print(f"\nProcessing records from {attributes_path}...")
        processed = 0
        skipped = 0

        with open(attributes_path, "r") as f_in, open(output_path, "w") as f_out:
            for line in tqdm(f_in, desc="Building pseudo-SAE"):
                line = line.strip()
                if not line:
                    continue

                record = json.loads(line)
                record_id = record.get("id")

                # Get assignments for this record
                if record_id not in assignments:
                    skipped += 1
                    continue

                record_assignments = assignments[record_id]
                cluster_ids = record_assignments["cluster_ids"]
                distances = record_assignments["distances"]
                original_attrs = record.get("attributes", [])

                # Build SAE attributes and weights
                sae_attributes: List[str] = []
                normalized_weights: List[float] = []

                for i, (cluster_id, distance) in enumerate(zip(cluster_ids, distances)):
                    # Get summary for this cluster
                    summary = summaries.get(cluster_id)
                    if summary is None:
                        # Fallback to original attribute if no summary
                        if i < len(original_attrs):
                            summary = original_attrs[i]
                        else:
                            continue

                    # Compute weight
                    cluster_stat = stats.get(cluster_id, {})
                    max_dist = cluster_stat.get("max_distance", 1.0)
                    weight = self._compute_weight(distance, max_dist)

                    sae_attributes.append(summary)
                    normalized_weights.append(weight)

                # Build output record
                output_record = {
                    "id": record_id,
                    "prompt": record.get("prompt", ""),
                    "response": record.get("response", ""),
                    "attributes": original_attrs,
                    "sae_attributes": sae_attributes,
                    "normalized_weights": normalized_weights,
                    "source": record.get("source", "unknown"),
                }

                f_out.write(json.dumps(output_record, ensure_ascii=False) + "\n")
                processed += 1

        # Load clustering metadata and save pseudo-SAE metadata
        clustering_meta = self._load_clustering_metadata(clustering_dir)

        pseudo_sae_metadata = {
            "embedding_model": clustering_meta.get("embedding_model", "unknown"),
            "n_clusters": clustering_meta.get("n_clusters"),
            "num_records": processed,
            "num_cluster_summaries": len(summaries),
        }

        metadata_path = output_path.parent / "pseudo_sae_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(pseudo_sae_metadata, f, indent=2)

        print(f"\nBuilt pseudo-SAE attributes for {processed} records")
        if skipped > 0:
            print(f"Skipped {skipped} records with no assignments")
        print(f"Output saved to {output_path}")
        print(f"Metadata saved to {metadata_path}")

        return processed


def build_pseudo_sae(
    attributes_path: str,
    clustering_dir: str,
    output_path: str,
) -> int:
    """
    Convenience function to build pseudo-SAE attributes.

    Args:
        attributes_path: Path to original attributes.jsonl
        clustering_dir: Directory with clustering outputs
        output_path: Output path for pseudo_sae_attributes.jsonl

    Returns:
        Number of records processed
    """
    builder = PseudoSAEBuilder()
    return builder.build(attributes_path, clustering_dir, output_path)
