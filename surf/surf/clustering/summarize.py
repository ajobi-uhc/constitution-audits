"""Summarize clusters using Claude Opus 4.5."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from tqdm import tqdm

from surf.core.models import ModelResource
from surf.core.utils import render_jinja, tqdm_gather


SUMMARIZE_PROMPT = '''Here are the top attributes that describe queries in a cluster:

<attributes>
{% for attr in attributes %}
- {{ attr }}
{% endfor %}
</attributes>

Summarize these into a single sentence starting with "The query" that captures the common theme. The summary should be concise and capture the essential shared characteristic of these attributes.

Respond with only the summary sentence, nothing else.'''


class ClusterSummarizer:
    """
    Summarize clusters using Claude Opus 4.5.

    Takes the top attributes per cluster and generates a single summary
    sentence that captures the common theme.
    """

    def __init__(
        self,
        model: str = "anthropic:claude-opus-4-5-20251101",
        max_concurrency: int = 100,
    ):
        """
        Initialize the summarizer.

        Args:
            model: Model string for summarization
            max_concurrency: Maximum concurrent API calls
        """
        self.model_resource = ModelResource.from_string(
            model,
            max_concurrency=max_concurrency,
            max_tokens=256,
            temperature=0.0,
        )

    async def _summarize_single(
        self,
        cluster_id: int,
        attributes: List[str],
    ) -> Optional[Dict[str, Any]]:
        """
        Summarize a single cluster.

        Args:
            cluster_id: Cluster ID
            attributes: Top attributes for this cluster

        Returns:
            Dict with cluster_id and summary, or None if error
        """
        if not attributes:
            return None

        try:
            prompt = render_jinja(SUMMARIZE_PROMPT, attributes=attributes)
            response = await self.model_resource.call(prompt)

            # Clean up response
            summary = response.strip()

            # Ensure it starts with "The query"
            if not summary.lower().startswith("the query"):
                summary = "The query " + summary

            return {
                "cluster_id": cluster_id,
                "summary": summary,
                "num_attributes": len(attributes),
            }

        except Exception as e:
            print(f"Error summarizing cluster {cluster_id}: {e}")
            return None

    async def summarize_clusters(
        self,
        input_path: str,
        output_path: str,
        batch_size: int = 10000,
    ) -> int:
        """
        Summarize all clusters.

        Args:
            input_path: Path to top_attributes.jsonl
            output_path: Output path for cluster_summaries.jsonl
            batch_size: Batch size for parallel processing

        Returns:
            Number of clusters summarized
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Load clusters
        print(f"Loading clusters from {input_path}...")
        clusters: List[Dict[str, Any]] = []
        with open(input_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    clusters.append(json.loads(line))

        print(f"Loaded {len(clusters)} clusters to summarize")

        # Process in batches
        summaries: List[Dict[str, Any]] = []

        for batch_start in tqdm(range(0, len(clusters), batch_size), desc="Summarizing batches"):
            batch = clusters[batch_start:batch_start + batch_size]

            tasks = [
                self._summarize_single(
                    cluster_id=c["cluster_id"],
                    attributes=c.get("attributes", []),
                )
                for c in batch
            ]

            results = await tqdm_gather(
                tasks,
                return_exceptions=True,
                desc="Processing batch",
            )

            for result in results:
                if result is not None and not isinstance(result, Exception):
                    summaries.append(result)

        # Sort by cluster_id and save
        summaries.sort(key=lambda x: x["cluster_id"])

        with open(output_path, "w") as f:
            for summary in summaries:
                f.write(json.dumps(summary) + "\n")

        print(f"Saved {len(summaries)} cluster summaries to {output_path}")
        return len(summaries)


async def summarize_clusters(
    input_path: str,
    output_path: str,
    model: str = "anthropic:claude-opus-4-5-20251101",
    max_concurrency: int = 100,
) -> int:
    """
    Convenience function to summarize clusters.

    Args:
        input_path: Path to top_attributes.jsonl
        output_path: Output path for cluster_summaries.jsonl
        model: Model for summarization
        max_concurrency: Maximum concurrent API calls

    Returns:
        Number of clusters summarized
    """
    summarizer = ClusterSummarizer(model=model, max_concurrency=max_concurrency)
    return await summarizer.summarize_clusters(input_path, output_path)
