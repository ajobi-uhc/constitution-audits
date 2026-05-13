"""Map generated attributes to cluster centroids via embedding similarity.

This module enables re-attribution: when the attribution step generates raw
attributes describing patterns in the replay buffer, these are mapped to
the closest cluster centroids so they can be properly weighted and sampled.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class AttributeClusterMapper:
    """
    Maps attributes to cluster centroids via embedding similarity.

    Loads cluster centroids and summaries, then for any new attribute:
    1. Computes its embedding
    2. Finds the closest cluster centroid
    3. Returns the cluster summary as the mapped attribute
    """

    def __init__(
        self,
        data_dir: str,
        embedding_model: Optional[Any] = None,
    ):
        """
        Initialize the mapper.

        Args:
            data_dir: Directory containing clustering outputs
                - centroids.npy: Cluster centroids
                - cluster_summaries.jsonl: {cluster_id, summary}
                - metadata.json: Includes embedding model info
            embedding_model: Optional pre-loaded EmbeddingComputer instance.
                If not provided, will be loaded lazily when needed.
        """
        self.data_dir = Path(data_dir)
        self._embedding_model = embedding_model

        # Load cluster data
        self.centroids: np.ndarray = self._load_centroids()
        self.summaries: Dict[int, str] = self._load_summaries()
        self.metadata: Dict[str, Any] = self._load_metadata()

        # Normalize centroids for cosine similarity
        norms = np.linalg.norm(self.centroids, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Avoid division by zero
        self.centroids_normalized = self.centroids / norms

        print(f"Loaded {len(self.centroids)} cluster centroids")
        print(f"Loaded {len(self.summaries)} cluster summaries")

    def _load_centroids(self) -> np.ndarray:
        """Load cluster centroids from numpy file."""
        centroids_path = self.data_dir / "centroids.npy"
        if not centroids_path.exists():
            raise FileNotFoundError(f"Centroids not found: {centroids_path}")

        centroids = np.load(centroids_path)
        return centroids.astype(np.float32)

    def _load_summaries(self) -> Dict[int, str]:
        """Load cluster summaries from JSONL."""
        summaries_path = self.data_dir / "cluster_summaries.jsonl"
        if not summaries_path.exists():
            raise FileNotFoundError(f"Cluster summaries not found: {summaries_path}")

        summaries: Dict[int, str] = {}
        with open(summaries_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    record = json.loads(line)
                    summaries[record["cluster_id"]] = record["summary"]

        return summaries

    def _load_metadata(self) -> Dict[str, Any]:
        """Load clustering metadata."""
        metadata_path = self.data_dir / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                return json.load(f)
        return {}

    @property
    def embedding_model_name(self) -> str:
        """Get the embedding model name used for clustering."""
        return self.metadata.get("embedding_model", "unknown")

    def _get_embedding_model(self):
        """Lazily load the embedding model if needed."""
        if self._embedding_model is None:
            from surf.clustering.embeddings import EmbeddingComputer

            model_name = self.embedding_model_name
            if model_name == "unknown":
                raise ValueError(
                    "Cannot load embedding model: unknown model name in metadata. "
                    "Please provide embedding_model explicitly."
                )

            print(f"Loading embedding model for cluster mapping: {model_name}")
            self._embedding_model = EmbeddingComputer(model_name=model_name)

        return self._embedding_model

    def find_closest_cluster(
        self,
        embedding: np.ndarray,
    ) -> Tuple[int, str, float]:
        """
        Find the closest cluster for a single embedding.

        Args:
            embedding: Embedding vector

        Returns:
            Tuple of (cluster_id, summary, similarity)
        """
        # Normalize query embedding
        embedding = np.asarray(embedding, dtype=np.float32)
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        # Compute cosine similarities
        similarities = self.centroids_normalized @ embedding

        # Find best match
        best_idx = int(np.argmax(similarities))
        best_similarity = float(similarities[best_idx])

        # Get summary for this cluster
        summary = self.summaries.get(best_idx, f"Cluster {best_idx}")

        return best_idx, summary, best_similarity

    def find_closest_clusters_batch(
        self,
        embeddings: np.ndarray,
    ) -> List[Tuple[int, str, float]]:
        """
        Find closest clusters for multiple embeddings.

        Args:
            embeddings: Array of shape (n, embedding_dim)

        Returns:
            List of (cluster_id, summary, similarity) tuples
        """
        embeddings = np.asarray(embeddings, dtype=np.float32)

        # Normalize
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1
        embeddings_normalized = embeddings / norms

        # Compute all similarities
        similarities = embeddings_normalized @ self.centroids_normalized.T

        # Find best matches
        best_indices = np.argmax(similarities, axis=1)
        best_similarities = np.max(similarities, axis=1)

        results = []
        for best_idx, best_sim in zip(best_indices, best_similarities):
            summary = self.summaries.get(int(best_idx), f"Cluster {best_idx}")
            results.append((int(best_idx), summary, float(best_sim)))

        return results

    def map_attributes(
        self,
        attributes: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Map raw attributes to cluster summaries via embedding.

        Args:
            attributes: List of raw attribute strings

        Returns:
            List of dicts with:
                - original: The input attribute
                - mapped: The cluster summary (mapped attribute)
                - cluster_id: The cluster ID
                - similarity: Cosine similarity score
        """
        if not attributes:
            return []

        # Get embedding model
        embed_model = self._get_embedding_model()

        # Compute embeddings for all attributes
        print(f"Embedding {len(attributes)} attributes for cluster mapping...")
        embeddings = embed_model.embed_batch(
            attributes,
            batch_size=len(attributes),  # Small batch, process all at once
            show_progress=False,
        )

        # Find closest clusters
        matches = self.find_closest_clusters_batch(embeddings)

        # Build results
        results = []
        for attr, (cluster_id, summary, similarity) in zip(attributes, matches):
            results.append({
                "original": attr,
                "mapped": summary,
                "cluster_id": cluster_id,
                "similarity": similarity,
            })

        return results

    def get_mapped_attributes(
        self,
        attributes: List[str],
    ) -> List[str]:
        """
        Map attributes and return just the mapped strings.

        Convenience method that returns only the cluster summaries.

        Args:
            attributes: List of raw attribute strings

        Returns:
            List of mapped attribute strings (cluster summaries)
        """
        if not attributes:
            return []

        results = self.map_attributes(attributes)
        return [r["mapped"] for r in results]

    def shutdown(self):
        """Shutdown the embedding model if loaded."""
        if self._embedding_model is not None:
            self._embedding_model.shutdown()
            self._embedding_model = None
