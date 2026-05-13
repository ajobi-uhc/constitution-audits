"""K-Means clustering for attribute embeddings using PyTorch GPU."""

from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import torch
from tqdm import tqdm




class AttributeClusterer:
    """
    Cluster attribute embeddings using cuML GPU K-Means.

    Produces:
    - centroids.npy: Cluster centroids
    - assignments.jsonl: Per-record cluster assignments
    - cluster_stats.jsonl: Per-cluster statistics
    - top_attributes.jsonl: Top 100 attributes per cluster
    """

    def __init__(
        self,
        n_clusters: int = 10000,
        random_state: int = 42,
        max_iter: int = 20,
    ):
        """
        Initialize the clusterer.

        Args:
            n_clusters: Number of clusters
            random_state: Random seed for reproducibility
            max_iter: Maximum iterations for K-means
        """
        self.n_clusters = n_clusters
        self.random_state = random_state
        self.max_iter = max_iter

    def _load_and_flatten(
        self,
        input_path: Path,
    ) -> Tuple[List[Dict[str, Any]], np.ndarray]:
        """
        Load embeddings and build per-attribute items list.

        Expects:
        - {dir}/embeddings.npy: All embeddings as (num_attrs, dim)
        - {dir}/attributes.jsonl: Records with attributes

        Returns:
            items: List of dicts with {id, attr_idx, attribute}
            embeddings: numpy array of shape (n_items, embedding_dim)
        """
        input_dir = input_path.parent
        embeddings_path = input_dir / "embeddings.npy"

        print(f"Loading embeddings from {embeddings_path}...")
        embeddings = np.load(embeddings_path)
        print(f"Embeddings shape: {embeddings.shape}")

        print(f"Loading records from {input_path}...")
        items: List[Dict[str, Any]] = []
        attr_idx_global = 0

        with open(input_path, "r") as f:
            for line in tqdm(f, desc="Loading records"):
                line = line.strip()
                if not line:
                    continue

                record = json.loads(line)
                rec_id = record.get("id")
                attributes = record.get("attributes", [])

                for attr_idx, attr_text in enumerate(attributes):
                    items.append({
                        "id": rec_id,
                        "prompt": record.get("prompt", ""),
                        "attr_idx": attr_idx,
                        "attribute": attr_text,
                    })
                    attr_idx_global += 1

        print(f"Loaded {len(items):,} attributes")

        if len(items) != embeddings.shape[0]:
            raise ValueError(f"Mismatch: {len(items)} attributes vs {embeddings.shape[0]} embeddings")

        return items, embeddings

    def _run_kmeans(
        self,
        embeddings: np.ndarray,
        batch_size: int = 65536,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Run K-Means clustering using PyTorch GPU with mini-batches.

        Uses mini-batch k-means for memory efficiency with large datasets.

        Returns:
            cluster_labels: Array of cluster assignments
            distances: Array of distances to assigned centroids
            centroids: Cluster centroids
        """
        torch.manual_seed(self.random_state)
        n_samples, dim = embeddings.shape

        print(f"\nRunning PyTorch GPU K-Means with {self.n_clusters:,} clusters...")
        print(f"  Data shape: {embeddings.shape}")
        print(f"  Data size: {embeddings.nbytes / 1e9:.2f} GB")
        print(f"  Max iterations: {self.max_iter}")
        print(f"  Batch size: {batch_size:,}")
        print(f"  Input dtype: {embeddings.dtype}")

        device = torch.device("cuda:0")
        print(f"  Using GPU: {torch.cuda.get_device_name(0)}")

        # Convert to tensor (keep on CPU, move batches to GPU)
        X = torch.from_numpy(embeddings).float()

        # Initialize centroids (random subset)
        print("  Initializing centroids...")
        perm = torch.randperm(n_samples)[:self.n_clusters]
        centroids = X[perm].to(device)

        # Training loop
        print("  Training...")
        start_time = time.time()
        prev_inertia = float('inf')

        for iteration in range(self.max_iter):
            iter_start = time.time()

            # Accumulate new centroids and track inertia
            new_centroids = torch.zeros_like(centroids)
            counts = torch.zeros(self.n_clusters, device=device)
            total_inertia = 0.0

            n_batches = (n_samples + batch_size - 1) // batch_size
            pbar = tqdm(range(0, n_samples, batch_size),
                       desc=f"    Iter {iteration + 1}/{self.max_iter}",
                       total=n_batches, leave=False)

            for i in pbar:
                batch = X[i:i + batch_size].to(device)
                batch_n = batch.shape[0]

                # Compute distances: ||x - c||^2 = ||x||^2 + ||c||^2 - 2*x.c
                x_norm = (batch ** 2).sum(dim=1, keepdim=True)
                c_norm = (centroids ** 2).sum(dim=1, keepdim=True).T
                dists = x_norm + c_norm - 2 * batch @ centroids.T

                # Assign to nearest centroid
                min_dists, assignments = dists.min(dim=1)
                total_inertia += min_dists.sum().item()

                # Accumulate using scatter_add
                new_centroids.scatter_add_(0, assignments.unsqueeze(1).expand(batch_n, dim), batch)
                counts.scatter_add_(0, assignments, torch.ones(batch_n, device=device))

            # Update centroids
            mask = counts > 0
            new_centroids[mask] = new_centroids[mask] / counts[mask].unsqueeze(1)
            new_centroids[~mask] = centroids[~mask]  # Keep old for empty clusters
            centroids = new_centroids

            # Log progress with convergence info
            iter_time = time.time() - iter_start
            inertia_change = (prev_inertia - total_inertia) / prev_inertia if prev_inertia != float('inf') else 0
            n_empty = (~mask).sum().item()
            print(f"    Iter {iteration + 1:2d}/{self.max_iter}: "
                  f"inertia={total_inertia:.4e}, "
                  f"Δ={inertia_change:+.4f}, "
                  f"empty={n_empty}, "
                  f"time={iter_time:.1f}s")

            # Early stopping if converged (less than 0.1% change)
            if 0 < inertia_change < 0.001:
                print(f"    Converged at iteration {iteration + 1} (Δ < 0.1%)")
                break

            prev_inertia = total_inertia

        train_time = time.time() - start_time
        print(f"  Training complete in {train_time:.1f}s ({train_time/60:.1f} min)")

        # Final assignment pass
        print("  Computing final assignments...")
        all_labels = []
        all_distances = []

        for i in tqdm(range(0, n_samples, batch_size), desc="  Assigning"):
            batch = X[i:i + batch_size].to(device)

            x_norm = (batch ** 2).sum(dim=1, keepdim=True)
            c_norm = (centroids ** 2).sum(dim=1, keepdim=True).T
            dists = x_norm + c_norm - 2 * batch @ centroids.T

            min_dists, assignments = dists.min(dim=1)
            all_labels.append(assignments.cpu())
            all_distances.append(torch.sqrt(min_dists.clamp(min=0)).cpu())

        cluster_labels = torch.cat(all_labels).numpy().astype(np.int32)
        distances = torch.cat(all_distances).numpy().astype(np.float32)
        centroids = centroids.cpu().numpy().astype(np.float32)

        n_nonempty = len(np.unique(cluster_labels))
        print(f"  Clustering complete. {n_nonempty:,} non-empty clusters.")

        return cluster_labels, distances, centroids

    def _save_centroids(
        self,
        centroids: np.ndarray,
        output_dir: Path,
    ):
        """Save cluster centroids."""
        # Save as numpy for fast loading
        np.save(output_dir / "centroids.npy", centroids)
        print(f"Saved centroids.npy ({centroids.shape})")

        # Also save as JSONL for portability
        with open(output_dir / "centroids.jsonl", "w") as f:
            for cluster_id, centroid in enumerate(centroids):
                record = {
                    "cluster_id": cluster_id,
                    "centroid": centroid.tolist(),
                }
                f.write(json.dumps(record) + "\n")
        print(f"Saved centroids.jsonl")

    def _save_assignments(
        self,
        items: List[Dict[str, Any]],
        cluster_labels: np.ndarray,
        distances: np.ndarray,
        output_dir: Path,
    ):
        """
        Save per-record cluster assignments.

        Groups items back by record ID and saves cluster assignments per record.
        """
        # Group by record ID
        record_assignments: Dict[Any, Dict] = {}

        for item, cluster_id, distance in zip(items, cluster_labels, distances):
            rec_id = item["id"]
            if rec_id not in record_assignments:
                record_assignments[rec_id] = {
                    "id": rec_id,
                    "cluster_ids": [],
                    "distances": [],
                }
            record_assignments[rec_id]["cluster_ids"].append(int(cluster_id))
            record_assignments[rec_id]["distances"].append(float(distance))

        # Save
        with open(output_dir / "assignments.jsonl", "w") as f:
            for record in record_assignments.values():
                f.write(json.dumps(record) + "\n")

        print(f"Saved assignments.jsonl ({len(record_assignments):,} records)")

    def _save_cluster_stats(
        self,
        cluster_labels: np.ndarray,
        distances: np.ndarray,
        output_dir: Path,
    ):
        """Save per-cluster statistics."""
        # Compute stats per cluster
        cluster_stats: Dict[int, Dict] = {}

        for cluster_id in range(self.n_clusters):
            mask = cluster_labels == cluster_id
            cluster_distances = distances[mask]

            if len(cluster_distances) == 0:
                continue

            cluster_stats[cluster_id] = {
                "cluster_id": cluster_id,
                "count": int(len(cluster_distances)),
                "max_distance": float(cluster_distances.max()),
                "min_distance": float(cluster_distances.min()),
                "mean_distance": float(cluster_distances.mean()),
                "std_distance": float(cluster_distances.std()),
            }

        # Save
        with open(output_dir / "cluster_stats.jsonl", "w") as f:
            for stats in sorted(cluster_stats.values(), key=lambda x: x["cluster_id"]):
                f.write(json.dumps(stats) + "\n")

        print(f"Saved cluster_stats.jsonl ({len(cluster_stats):,} non-empty clusters)")

    def _save_top_attributes(
        self,
        items: List[Dict[str, Any]],
        cluster_labels: np.ndarray,
        distances: np.ndarray,
        output_dir: Path,
        top_k: int = 100,
    ):
        """
        Save top-k closest attributes per cluster.

        Used for cluster summarization.
        """
        # Group by cluster
        clusters: Dict[int, List[Tuple[str, float]]] = defaultdict(list)

        for item, cluster_id, distance in zip(items, cluster_labels, distances):
            attr = item.get("attribute", "")
            if attr:
                clusters[int(cluster_id)].append((attr, float(distance)))

        # Save top attributes for each cluster
        with open(output_dir / "top_attributes.jsonl", "w") as f:
            for cluster_id in tqdm(range(self.n_clusters), desc="Saving top attributes"):
                cluster_attrs = clusters.get(cluster_id, [])
                if not cluster_attrs:
                    continue

                # Sort by distance (closest first) and take top k
                cluster_attrs.sort(key=lambda x: x[1])
                top_attrs = [attr for attr, _ in cluster_attrs[:top_k]]

                record = {
                    "cluster_id": cluster_id,
                    "attributes": top_attrs,
                    "total_in_cluster": len(cluster_attrs),
                }
                f.write(json.dumps(record) + "\n")

        non_empty = sum(1 for c in clusters.values() if c)
        print(f"Saved top_attributes.jsonl ({non_empty:,} clusters with top {top_k} attrs)")

    def _load_embedding_metadata(self, output_dir: Path) -> Dict[str, Any]:
        """Load embedding metadata if available."""
        metadata_path = output_dir / "embedding_metadata.json"
        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                return json.load(f)
        return {}

    def _save_metadata(
        self,
        items: List[Dict[str, Any]],
        embeddings: np.ndarray,
        cluster_labels: np.ndarray,
        output_dir: Path,
    ):
        """Save clustering metadata, including embedding model info."""
        unique_records = len(set(item["id"] for item in items))
        non_empty_clusters = len(set(cluster_labels))

        # Load embedding metadata
        embedding_meta = self._load_embedding_metadata(output_dir)

        metadata = {
            "n_clusters": self.n_clusters,
            "non_empty_clusters": non_empty_clusters,
            "total_items": len(items),
            "unique_records": unique_records,
            "embedding_dim": int(embeddings.shape[1]),
            "num_embeddings_clustered": int(embeddings.shape[0]),
            "embedding_model": embedding_meta.get("embedding_model", "unknown"),
            "random_state": self.random_state,
        }

        with open(output_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        print(f"Saved metadata.json")

    def cluster(
        self,
        input_path: str,
        output_dir: str,
        top_k: int = 100,
    ) -> Dict[str, Any]:
        """
        Run the full clustering pipeline.

        Args:
            input_path: Path to attributes_with_embeddings.jsonl
            output_dir: Output directory for clustering results
            top_k: Number of top attributes to save per cluster

        Returns:
            Metadata dict
        """
        input_path = Path(input_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        print("=" * 60)
        print("ATTRIBUTE CLUSTERING")
        print("=" * 60)
        print(f"Input: {input_path}")
        print(f"Output: {output_dir}")
        print(f"Clusters: {self.n_clusters:,}")
        print("=" * 60)

        # Load and flatten
        items, embeddings = self._load_and_flatten(input_path)

        # Run clustering
        cluster_labels, distances, centroids = self._run_kmeans(embeddings)

        # Save all outputs
        print("\nSaving outputs...")
        self._save_centroids(centroids, output_dir)
        self._save_assignments(items, cluster_labels, distances, output_dir)
        self._save_cluster_stats(cluster_labels, distances, output_dir)
        self._save_top_attributes(items, cluster_labels, distances, output_dir, top_k)
        self._save_metadata(items, embeddings, cluster_labels, output_dir)

        print("\n" + "=" * 60)
        print("CLUSTERING COMPLETE")
        print("=" * 60)

        return {
            "n_clusters": self.n_clusters,
            "total_items": len(items),
            "output_dir": str(output_dir),
        }


def cluster_attributes(
    input_path: str,
    output_dir: str,
    n_clusters: int = 10000,
) -> Dict[str, Any]:
    """
    Convenience function to cluster attributes.

    Args:
        input_path: Path to attributes_with_embeddings.jsonl
        output_dir: Output directory
        n_clusters: Number of clusters

    Returns:
        Metadata dict
    """
    clusterer = AttributeClusterer(n_clusters=n_clusters)
    return clusterer.cluster(input_path, output_dir)
