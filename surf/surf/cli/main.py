"""CLI entry point for SURF."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import click
import numpy as np
from datasets import load_dataset
from dotenv import load_dotenv

from surf.clustering.cluster import AttributeClusterer
from surf.clustering.embeddings import EmbeddingComputer
from surf.clustering.pseudo_sae import PseudoSAEBuilder
from surf.clustering.summarize import ClusterSummarizer
from surf.em_loop.judge import get_principle_from_rubric, load_rubric
from surf.em_loop.loop import EMLoop
from surf.em_loop.sweep import Sweep
from surf.extraction.batch import BatchExtractor
from surf.extraction.extractor import extract_attributes

# Load environment variables
load_dotenv()


# Helper functions for prepare_dataset
def _count_jsonl_records(path: Path) -> int:
    """Count records in a JSONL file."""
    if not path.exists():
        return 0
    count = 0
    with open(path, "r") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def _count_total_attributes(path: Path) -> int:
    """Count total attributes across all records in JSONL."""
    if not path.exists():
        return 0
    total = 0
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                record = json.loads(line)
                total += len(record.get("attributes", []))
    return total


def _get_embeddings_count(path: Path) -> int:
    """Get number of embeddings in embeddings.npy."""
    if not path.exists():
        return 0
    embeds = np.load(path, mmap_mode='r')
    return embeds.shape[0]


def _get_clustering_metadata(path: Path) -> dict:
    """Load metadata.json to check clustering state."""
    metadata_path = path / "metadata.json"
    if not metadata_path.exists():
        return {}
    with open(metadata_path, "r") as f:
        return json.load(f)


@click.group()
@click.version_option(version="0.1.0", prog_name="surf")
def cli():
    """SURF: Self-contained Unified Red-teaming Framework.

    A tool for automated red-teaming of language models using the EM algorithm.
    """
    pass


@cli.command()
@click.option(
    "--dataset",
    default="allenai/tulu-3-sft-mixture",
    help="HuggingFace dataset name",
)
@click.option(
    "--split",
    default="train",
    help="Dataset split to use",
)
@click.option(
    "--num-samples",
    type=int,
    default=None,
    help="Maximum number of samples to process (default: all)",
)
@click.option(
    "--output",
    "-o",
    default="attributes.jsonl",
    help="Output JSONL file path",
)
@click.option(
    "--model",
    default="anthropic:claude-opus-4-5-20251101",
    help="Model for attribute extraction (provider:model format)",
)
@click.option(
    "--concurrency",
    type=int,
    default=50,
    help="Maximum concurrent API calls (ignored with --batch)",
)
@click.option(
    "--no-batch",
    is_flag=True,
    help="Use async API instead of Batch API (faster but 2x cost)",
)
def extract(
    dataset: str,
    split: str,
    num_samples: int | None,
    output: str,
    model: str,
    concurrency: int,
    no_batch: bool,
):
    """Extract attributes from a HuggingFace dataset.

    Processes records from the dataset, extracting 10 attributes per record
    that describe the query in terms of content, style, formatting, etc.

    Supports checkpoint/resume: if the output file exists, already-processed
    records will be skipped.

    Examples:

        # Extract from default dataset (Tulu-3)
        surf extract --output attributes.jsonl

        # Extract 1000 samples with higher concurrency
        surf extract --num-samples 1000 --concurrency 100 --output attrs.jsonl

        # Use async API instead of batch (faster)
        surf extract --no-batch --output attrs.jsonl
    """
    click.echo(f"Extracting attributes from {dataset}")
    click.echo(f"Model: {model}")
    click.echo(f"Output: {output}")

    if num_samples:
        click.echo(f"Max samples: {num_samples}")

    if not no_batch:
        # Batch API mode (default)
        click.echo("Using Anthropic Batch API")

        # Load dataset
        click.echo("Loading dataset...")
        ds = load_dataset(dataset, split=split)
        if num_samples:
            ds = ds.select(range(min(num_samples, len(ds))))

        # Convert to records
        records = []
        for i, row in enumerate(ds):
            records.append({
                "id": i,
                "prompt": row.get("prompt", row.get("messages", [{}])[0].get("content", "")),
                "response": row.get("response", row.get("messages", [{}])[-1].get("content", "") if len(row.get("messages", [])) > 1 else ""),
                "source": dataset,
            })

        click.echo(f"Loaded {len(records)} records")

        # Extract model name from provider:model format
        model_name = model.split(":")[-1] if ":" in model else model

        # Run batch extraction
        output_dir = Path(output).parent / "batch_cache"
        extractor = BatchExtractor(
            model=model_name,
            output_dir=str(output_dir),
        )

        records = extractor.extract(records)

        # Write output
        click.echo(f"Writing {len(records)} records to {output}")
        with open(output, "w") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        click.echo(f"\nExtraction complete: {len(records)} records")

    else:
        # Async API mode
        click.echo(f"Concurrency: {concurrency}")

        try:
            processed = asyncio.run(
                extract_attributes(
                    dataset_name=dataset,
                    num_samples=num_samples,
                    output_path=output,
                    model=model,
                    concurrency=concurrency,
                )
            )
            click.echo(f"\nExtraction complete: {processed} records processed")

        except KeyboardInterrupt:
            click.echo("\nInterrupted by user")
            sys.exit(1)
        except Exception as e:
            click.echo(f"\nError: {e}", err=True)
            sys.exit(1)


@cli.command()
@click.option(
    "--input",
    "-i",
    required=True,
    type=click.Path(exists=True),
    help="Path to attributes.jsonl from extract command",
)
@click.option(
    "--output-dir",
    "-o",
    required=True,
    help="Directory for clustering outputs",
)
@click.option(
    "--n-clusters",
    type=int,
    default=25000,
    help="Number of clusters for K-Means",
)
@click.option(
    "--embedding-model",
    default="Qwen/Qwen3-Embedding-8B",
    help="HuggingFace embedding model",
)
@click.option(
    "--summarize-model",
    default="anthropic:claude-opus-4-5-20251101",
    help="Model for cluster summarization",
)
@click.option(
    "--batch-size",
    type=int,
    default=512,
    help="Batch size for embeddings",
)
@click.option(
    "--summarize-concurrency",
    type=int,
    default=100,
    help="Max concurrent calls for summarization",
)
@click.option(
    "--skip-embeddings",
    is_flag=True,
    help="Skip embedding computation (use existing)",
)
@click.option(
    "--skip-clustering",
    is_flag=True,
    help="Skip clustering (use existing)",
)
@click.option(
    "--skip-summarize",
    is_flag=True,
    help="Skip cluster summarization (use existing)",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Show verbose sklearn output for clustering",
)
def cluster(
    input: str,
    output_dir: str,
    n_clusters: int,
    embedding_model: str,
    summarize_model: str,
    batch_size: int,
    summarize_concurrency: int,
    skip_embeddings: bool,
    skip_clustering: bool,
    skip_summarize: bool,
    verbose: bool,
):
    """Run the full clustering pipeline (GPU required).

    This pipeline transforms raw attributes into semantically-grouped
    pseudo-SAE attributes for the EM loop:

    \b
    1. Compute embeddings (sentence-transformers, multi-GPU)
    2. K-Means clustering
    3. Summarize clusters with Claude
    4. Build pseudo-SAE attributes with weights

    Output files in output-dir:
    \b
    - attributes_with_embeddings.jsonl
    - centroids.npy
    - assignments.jsonl
    - cluster_stats.jsonl
    - top_attributes.jsonl
    - cluster_summaries.jsonl
    - pseudo_sae_attributes.jsonl  <- Use this for run-em

    Examples:

        # Full pipeline with 10K clusters
        uv run -m surf.cli.main cluster \\
            --input attributes.jsonl \\
            --output-dir clustering_10k \\
            --n-clusters 10000

        # Resume from embeddings (skip that step)
        uv run -m surf.cli.main cluster \\
            --input attributes.jsonl \\
            --output-dir clustering_10k \\
            --skip-embeddings

        # Use different embedding model
        uv run -m surf.cli.main cluster \\
            --input attributes.jsonl \\
            --output-dir clustering_10k \\
            --embedding-model sentence-transformers/all-MiniLM-L6-v2
    """
    from pathlib import Path

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    embeddings_file = output_path / "attributes_with_embeddings.jsonl"
    top_attrs_file = output_path / "top_attributes.jsonl"
    summaries_file = output_path / "cluster_summaries.jsonl"
    pseudo_sae_file = output_path / "pseudo_sae_attributes.jsonl"

    click.echo(f"{'='*60}")
    click.echo("CLUSTERING PIPELINE")
    click.echo(f"{'='*60}")
    click.echo(f"Input: {input}")
    click.echo(f"Output directory: {output_dir}")
    click.echo(f"Clusters: {n_clusters:,}")
    click.echo(f"Embedding model: {embedding_model}")
    click.echo(f"Summarize model: {summarize_model}")
    click.echo(f"{'='*60}")

    try:
        # Step 1: Compute embeddings
        if not skip_embeddings:
            click.echo(f"\n[1/4] Computing embeddings...")
            computer = EmbeddingComputer(model_name=embedding_model)
            try:
                computer.process_file(
                    input_path=input,
                    output_path=str(embeddings_file),
                    batch_size=batch_size,
                )
            finally:
                computer.shutdown()
        else:
            click.echo(f"\n[1/4] Skipping embeddings (--skip-embeddings)")

        # Step 2: Run clustering
        if not skip_clustering:
            click.echo(f"\n[2/4] Running K-Means clustering...")
            clusterer = AttributeClusterer(n_clusters=n_clusters, verbose=verbose)
            clusterer.cluster(
                input_path=str(embeddings_file),
                output_dir=str(output_path),
            )
        else:
            click.echo(f"\n[2/4] Skipping clustering (--skip-clustering)")

        # Step 3: Summarize clusters
        if not skip_summarize:
            click.echo(f"\n[3/4] Summarizing clusters...")
            summarizer = ClusterSummarizer(
                model=summarize_model,
                max_concurrency=summarize_concurrency,
            )
            asyncio.run(
                summarizer.summarize_clusters(
                    input_path=str(top_attrs_file),
                    output_path=str(summaries_file),
                )
            )
        else:
            click.echo(f"\n[3/4] Skipping summarization (--skip-summarize)")

        # Step 4: Build pseudo-SAE attributes
        click.echo(f"\n[4/4] Building pseudo-SAE attributes...")
        builder = PseudoSAEBuilder()
        builder.build(
            attributes_path=input,
            clustering_dir=str(output_path),
            output_path=str(pseudo_sae_file),
        )

        click.echo(f"\n{'='*60}")
        click.echo("CLUSTERING COMPLETE")
        click.echo(f"{'='*60}")
        click.echo(f"Pseudo-SAE attributes saved to: {pseudo_sae_file}")
        click.echo(f"\nUse for EM loop:")
        click.echo(f"  uv run -m surf.cli.main run-em \\")
        click.echo(f"      --rubric rubrics/rebuttal.yaml \\")
        click.echo(f"      --attributes {pseudo_sae_file}")

    except KeyboardInterrupt:
        click.echo("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        click.echo(f"\nError: {e}", err=True)
        raise


@cli.command("prepare-dataset")
@click.option(
    "--dataset",
    default="allenai/tulu-3-sft-mixture",
    help="HuggingFace dataset name",
)
@click.option(
    "--num-samples",
    type=int,
    default=None,
    help="Maximum number of samples to process (default: all)",
)
@click.option(
    "--output-dir",
    "-o",
    required=True,
    help="Output directory for all artifacts",
)
@click.option(
    "--n-clusters",
    type=int,
    default=25000,
    help="Number of clusters for K-Means",
)
@click.option(
    "--extract-model",
    default="anthropic:claude-opus-4-5-20251101",
    help="Model for attribute extraction",
)
@click.option(
    "--embedding-model",
    default="Qwen/Qwen3-Embedding-8B",
    help="HuggingFace embedding model",
)
@click.option(
    "--summarize-model",
    default="anthropic:claude-opus-4-5-20251101",
    help="Model for cluster summarization",
)
@click.option(
    "--extract-concurrency",
    type=int,
    default=50,
    help="Max concurrent calls for extraction",
)
@click.option(
    "--summarize-concurrency",
    type=int,
    default=100,
    help="Max concurrent calls for summarization",
)
@click.option(
    "--batch-size",
    type=int,
    default=512,
    help="Batch size for embeddings",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force re-run all steps (ignore existing files)",
)
def prepare_dataset(
    dataset: str,
    num_samples: int | None,
    output_dir: str,
    n_clusters: int,
    extract_model: str,
    embedding_model: str,
    summarize_model: str,
    extract_concurrency: int,
    summarize_concurrency: int,
    batch_size: int,
    force: bool,
):
    """Prepare dataset: extract attributes + cluster (auto-skips completed steps).

    This is the main entry point for dataset preparation. It runs:

    \b
    1. Extract 10 attributes per query from HuggingFace dataset
    2. Compute embeddings (sentence-transformers, multi-GPU)
    3. K-Means clustering
    4. Summarize clusters with Claude
    5. Build pseudo-SAE attributes

    Each step checks for existing output files and skips if already done.
    Use --force to re-run all steps.

    Output structure:
    \b
    {output-dir}/
    ├── attributes.jsonl              <- Step 1
    ├── attributes_with_embeddings.jsonl  <- Step 2
    ├── centroids.npy                 <- Step 3
    ├── assignments.jsonl             <- Step 3
    ├── cluster_stats.jsonl           <- Step 3
    ├── top_attributes.jsonl          <- Step 3
    ├── cluster_summaries.jsonl       <- Step 4
    └── pseudo_sae_attributes.jsonl   <- Step 5 (use for run-em)

    Examples:

        # Prepare dataset (10K samples, 10K clusters by default)
        uv run -m surf.cli.main prepare-dataset \\
            --output-dir data/tulu_10k

        # Resume interrupted run (auto-skips completed steps)
        uv run -m surf.cli.main prepare-dataset \\
            --output-dir data/tulu_10k

        # Use more samples
        uv run -m surf.cli.main prepare-dataset \\
            --num-samples 50000 \\
            --output-dir data/tulu_50k

        # Force re-run everything
        uv run -m surf.cli.main prepare-dataset \\
            --output-dir data/tulu_10k \\
            --force
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Define all output files
    attributes_file = output_path / "attributes.jsonl"
    embeddings_file = output_path / "attributes_with_embeddings.jsonl"
    embedding_metadata_file = output_path / "embedding_metadata.json"
    centroids_file = output_path / "centroids.npy"
    top_attrs_file = output_path / "top_attributes.jsonl"
    summaries_file = output_path / "cluster_summaries.jsonl"
    pseudo_sae_file = output_path / "pseudo_sae_attributes.jsonl"

    click.echo(f"{'='*60}")
    click.echo("PREPARE DATASET")
    click.echo(f"{'='*60}")
    click.echo(f"Dataset: {dataset}")
    if num_samples:
        click.echo(f"Samples: {num_samples:,}")
    else:
        click.echo(f"Samples: all")
    click.echo(f"Output: {output_dir}")
    click.echo(f"Clusters: {n_clusters:,}")
    click.echo(f"{'='*60}")

    try:
        # Stage 1: Extract attributes
        ds = load_dataset(dataset, split="train")
        target_count = min(num_samples, len(ds)) if num_samples else len(ds)
        existing_count = _count_jsonl_records(attributes_file)
        need_extraction = force or existing_count < target_count

        if need_extraction:
            click.echo(f"\n[1/5] Extraction: {existing_count:,}/{target_count:,}")
            asyncio.run(extract_attributes(
                dataset_name=dataset,
                num_samples=num_samples,
                output_path=str(attributes_file),
                model=extract_model,
                concurrency=extract_concurrency,
            ))
        else:
            click.echo(f"\n[1/5] Extraction: skipped ({existing_count:,} complete)")

        # Stage 2: Compute embeddings
        embeddings_path = output_path / "embeddings.npy"
        total_attrs = _count_total_attributes(attributes_file)
        embeddings_count = _get_embeddings_count(embeddings_path)

        if embeddings_count > total_attrs:
            raise ValueError(f"Data mismatch: {embeddings_count:,} embeddings > {total_attrs:,} attributes")

        need_embeddings = force or embeddings_count < total_attrs

        if need_embeddings:
            click.echo(f"\n[2/5] Embeddings: {embeddings_count:,}/{total_attrs:,}")
            computer = EmbeddingComputer(model_name=embedding_model)
            try:
                computer.process_file(
                    input_path=str(attributes_file),
                    output_path=str(embeddings_file),
                    batch_size=batch_size,
                )
            finally:
                computer.shutdown()
        else:
            click.echo(f"\n[2/5] Embeddings: skipped ({embeddings_count:,} complete)")

        # Stage 3: Clustering
        cluster_meta = _get_clustering_metadata(output_path)
        current_embeds = _get_embeddings_count(embeddings_path)
        clustered_embeds = cluster_meta.get("num_embeddings_clustered", 0)
        need_clustering = force or not centroids_file.exists() or clustered_embeds != current_embeds

        if need_clustering:
            click.echo(f"\n[3/5] Clustering: {current_embeds:,} embeddings -> {n_clusters:,} clusters")
            clusterer = AttributeClusterer(n_clusters=n_clusters)
            clusterer.cluster(
                input_path=str(embeddings_file),
                output_dir=str(output_path),
            )
        else:
            click.echo(f"\n[3/5] Clustering: skipped ({cluster_meta.get('non_empty_clusters', 0):,} clusters)")

        # Stage 4: Summarization
        need_summarization = force or need_clustering or not summaries_file.exists()

        if need_summarization:
            click.echo(f"\n[4/5] Summarization: running...")
            summarizer = ClusterSummarizer(
                model=summarize_model,
                max_concurrency=summarize_concurrency,
            )
            asyncio.run(summarizer.summarize_clusters(
                input_path=str(top_attrs_file),
                output_path=str(summaries_file),
            ))
        else:
            click.echo(f"\n[4/5] Summarization: skipped ({_count_jsonl_records(summaries_file):,} summaries)")

        # Stage 5: Pseudo-SAE
        need_pseudo_sae = force or need_clustering or not pseudo_sae_file.exists()

        if need_pseudo_sae:
            click.echo(f"\n[5/5] Pseudo-SAE: building...")
            builder = PseudoSAEBuilder()
            builder.build(
                attributes_path=str(attributes_file),
                clustering_dir=str(output_path),
                output_path=str(pseudo_sae_file),
            )
        else:
            click.echo(f"\n[5/5] Pseudo-SAE: skipped ({_count_jsonl_records(pseudo_sae_file):,} records)")

        click.echo(f"\n{'='*60}")
        click.echo("DATASET PREPARATION COMPLETE")
        click.echo(f"{'='*60}")
        click.echo(f"Output: {pseudo_sae_file}")
        click.echo(f"\nRun sweep (multiple parallel EM loops):")
        click.echo(f"  uv run -m surf.cli.main sweep \\")
        click.echo(f"      --rubric rubrics/rebuttal.yaml \\")
        click.echo(f"      --attributes {pseudo_sae_file} \\")
        click.echo(f"      --output-dir {output_dir}/sweep_results \\")
        click.echo(f"      --num-runs 5 \\")
        click.echo(f"      --iterations 20")

    except KeyboardInterrupt:
        click.echo("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        click.echo(f"\nError: {e}", err=True)
        raise


@cli.command("run-em")
@click.option(
    "--rubric",
    "-r",
    required=True,
    type=click.Path(exists=True),
    help="Path to YAML rubric file with scoring guidelines",
)
@click.option(
    "--attributes",
    "-a",
    default="seoirsem/CHUNKY-tulu3-SFT-25k-attributes",
    help="HuggingFace dataset ID or path to local JSONL file",
)
@click.option(
    "--target-model",
    default="anthropic:claude-sonnet-4-5-20250929",
    help="Model being red-teamed (provider:model format)",
)
@click.option(
    "--judge-model",
    default="anthropic:claude-opus-4-5-20251101",
    help="Model for judging responses (provider:model format)",
)
@click.option(
    "--query-model",
    default="openrouter:meta-llama/llama-3.1-70b-instruct",
    help="Model for query generation (provider:model format)",
)
@click.option(
    "--iterations",
    "-n",
    type=int,
    default=20,
    help="Number of iterations to run",
)
@click.option(
    "--buffer-size",
    type=int,
    default=5,
    help="Replay buffer size (top-k entries)",
)
@click.option(
    "--candidates",
    type=int,
    default=120,
    help="Candidates to generate per iteration",
)
@click.option(
    "--output-dir",
    "-o",
    required=True,
    help="Output directory for results (results.jsonl, summary.jsonl)",
)
@click.option(
    "--target-concurrency",
    type=int,
    default=50,
    help="Max concurrent calls to target model",
)
@click.option(
    "--query-concurrency",
    type=int,
    default=50,
    help="Max concurrent calls to query model",
)
@click.option(
    "--judge-concurrency",
    type=int,
    default=20,
    help="Max concurrent calls to judge model",
)
@click.option(
    "--no-thinking",
    is_flag=True,
    help="Disable extended thinking for judge",
)
@click.option(
    "--thinking-budget",
    type=int,
    default=10000,
    help="Token budget for extended thinking",
)
def run_em(
    rubric: str,
    attributes: str,
    target_model: str,
    judge_model: str,
    query_model: str,
    iterations: int,
    buffer_size: int,
    candidates: int,
    output_dir: str,
    target_concurrency: int,
    query_concurrency: int,
    judge_concurrency: int,
    no_thinking: bool,
    thinking_budget: int,
):
    """Run the EM loop for red-teaming.

    The EM loop iteratively:
    1. Samples attributes from file + weighted pool
    2. Generates queries using the query model
    3. Gets responses from the target model
    4. Scores responses with the judge
    5. Updates the replay buffer with high-scoring entries
    6. Runs attribution to extract new attributes

    Model formats:
        - anthropic:model-name     Anthropic API (Claude models)
        - openrouter:model-name    OpenRouter API
        - vllm:model-name          Auto-managed local vLLM server
        - http://host:port/v1:model  Custom OpenAI-compatible server

    Examples:

        # Basic usage with HuggingFace dataset
        surf run-em --rubric rubrics/rebuttal.yaml --attributes seoirsem/CHUNKY-tulu3-SFT-25k-attributes

        # Use local file
        surf run-em --rubric rubrics/rebuttal.yaml --attributes data/tulu/pseudo_sae_attributes.jsonl

        # Use vLLM for query generation
        surf run-em \\
            --rubric rubrics/rebuttal.yaml \\
            --attributes seoirsem/CHUNKY-tulu3-SFT-25k-attributes \\
            --query-model vllm:meta-llama/Llama-3.1-70B-Instruct

        # More iterations with larger buffer
        surf run-em \\
            --rubric rubrics/rebuttal.yaml \\
            --attributes seoirsem/CHUNKY-tulu3-SFT-25k-attributes \\
            --iterations 50 \\
            --buffer-size 20
    """
    click.echo(f"Running EM loop")
    click.echo(f"Rubric: {rubric}")
    click.echo(f"Attributes: {attributes}")
    click.echo(f"Target model: {target_model}")
    click.echo(f"Judge model: {judge_model}")
    click.echo(f"Query model: {query_model}")
    click.echo(f"Iterations: {iterations}")
    click.echo(f"Buffer size: {buffer_size}")
    click.echo(f"Candidates per iteration: {candidates}")
    click.echo(f"Output dir: {output_dir}")

    try:
        loop = EMLoop(
            rubric_path=rubric,
            attributes=attributes,
            target_model=target_model,
            judge_model=judge_model,
            query_model=query_model,
            buffer_size=buffer_size,
            candidates_per_iter=candidates,
            output_dir=output_dir,
            target_concurrency=target_concurrency,
            query_concurrency=query_concurrency,
            judge_concurrency=judge_concurrency,
            use_thinking=not no_thinking,
            thinking_budget=thinking_budget,
        )

        summary = asyncio.run(loop.run_loop(num_iterations=iterations))

        click.echo(f"\n{'='*60}")
        click.echo("EM Loop Complete")
        click.echo(f"{'='*60}")
        click.echo(f"Total iterations: {summary['total_iterations']}")
        click.echo(f"Final buffer size: {summary['final_buffer_size']}")
        click.echo(f"Final buffer scores: {[round(s, 3) for s in summary['final_buffer_scores']]}")
        click.echo(f"Results saved to: {output_dir}/")

    except KeyboardInterrupt:
        click.echo("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        click.echo(f"\nError: {e}", err=True)
        raise
        sys.exit(1)


@cli.command("sweep")
@click.option(
    "--rubric",
    "-r",
    required=True,
    type=click.Path(exists=True),
    help="Path to YAML rubric file with scoring guidelines",
)
@click.option(
    "--attributes",
    "-a",
    default="seoirsem/CHUNKY-tulu3-SFT-25k-attributes",
    help="HuggingFace dataset ID or path to local JSONL file",
)
@click.option(
    "--output-dir",
    "-o",
    required=True,
    help="Output directory for sweep results",
)
@click.option(
    "--num-runs",
    type=int,
    default=5,
    help="Number of parallel runs",
)
@click.option(
    "--iterations",
    "-n",
    type=int,
    default=20,
    help="Number of iterations per run",
)
@click.option(
    "--target-model",
    default="anthropic:claude-sonnet-4-5-20250929",
    help="Model being red-teamed",
)
@click.option(
    "--judge-model",
    default="anthropic:claude-opus-4-5-20251101",
    help="Model for judging responses",
)
@click.option(
    "--query-model",
    default="openrouter:meta-llama/llama-3.1-70b-instruct",
    help="Model for query generation",
)
@click.option(
    "--buffer-size",
    type=int,
    default=5,
    help="Replay buffer size per run",
)
@click.option(
    "--candidates",
    type=int,
    default=120,
    help="Candidates per iteration",
)
def sweep(
    rubric: str,
    attributes: str,
    output_dir: str,
    num_runs: int,
    iterations: int,
    target_model: str,
    judge_model: str,
    query_model: str,
    buffer_size: int,
    candidates: int,
):
    """Run multiple parallel EM loops (sweep experiment).

    Each run gets its own subfolder with independent state but shares
    compute resources (API concurrency) with other runs.

    Output structure:
    \b
    output-dir/
    ├── runs/
    │   ├── run_1/results.jsonl, summary.jsonl
    │   ├── run_2/...
    │   └── run_N/...
    └── sweep_summary.json

    Examples:

        # Run 5 parallel experiments with HuggingFace dataset
        surf sweep --rubric rubrics/rebuttal.yaml --attributes seoirsem/CHUNKY-tulu3-SFT-25k-attributes -o sweep_out

        # Run with local file
        surf sweep --rubric rubrics/rebuttal.yaml --attributes data/tulu/pseudo_sae_attributes.jsonl -o sweep_out

        # Run 10 experiments with 30 iterations each
        surf sweep --rubric rubrics/rebuttal.yaml --attributes seoirsem/CHUNKY-tulu3-SFT-25k-attributes \\
            -o sweep_out --num-runs 10 --iterations 30
    """
    click.echo(f"Running sweep: {num_runs} runs x {iterations} iterations")
    click.echo(f"Output: {output_dir}")

    try:
        sweep_exp = Sweep(
            rubric_path=rubric,
            attributes=attributes,
            output_dir=output_dir,
            num_runs=num_runs,
            num_iterations=iterations,
            target_model=target_model,
            judge_model=judge_model,
            query_model=query_model,
            buffer_size=buffer_size,
            candidates_per_iter=candidates,
        )

        summary = asyncio.run(sweep_exp.run_sweep())
        click.echo(f"\nSweep complete. Results in {output_dir}/")

    except KeyboardInterrupt:
        click.echo("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        click.echo(f"\nError: {e}", err=True)
        raise


@cli.command()
@click.option(
    "--rubric",
    "-r",
    required=True,
    type=click.Path(exists=True),
    help="Path to YAML rubric file",
)
def show_rubric(rubric: str):
    """Display the contents of a rubric file.

    Shows the principle and scoring guidelines from a YAML rubric.
    """
    rubric_data = load_rubric(rubric)
    principle = get_principle_from_rubric(rubric_data)

    click.echo(f"Rubric: {rubric}")
    click.echo(f"{'='*60}")

    if "exp_name" in rubric_data:
        click.echo(f"Experiment: {rubric_data['exp_name']}")

    click.echo(f"\nPrinciple Details:")
    click.echo(f"{'-'*60}")
    click.echo(principle)


@cli.command()
def list_models():
    """List example model configurations.

    Shows examples of model specifications for different providers.
    """
    click.echo("Model Provider Formats:")
    click.echo(f"{'='*60}")
    click.echo()
    click.echo("Anthropic API (requires ANTHROPIC_API_KEY):")
    click.echo("  anthropic:claude-sonnet-4-5-20250929")
    click.echo("  anthropic:claude-opus-4-5-20251101")
    click.echo()
    click.echo("OpenRouter API (requires OPENROUTER_API_KEY):")
    click.echo("  openrouter:meta-llama/llama-3.1-70b-instruct")
    click.echo("  openrouter:anthropic/claude-3.5-sonnet")
    click.echo("  openrouter:google/gemini-pro-1.5")
    click.echo()
    click.echo("vLLM (auto-managed local server):")
    click.echo("  vllm:meta-llama/Llama-3.1-70B-Instruct")
    click.echo("  vllm:Qwen/Qwen2.5-72B-Instruct")
    click.echo()
    click.echo("Custom OpenAI-compatible server:")
    click.echo("  http://localhost:8000/v1:model-name")
    click.echo()
    click.echo("Environment Variables:")
    click.echo("  ANTHROPIC_API_KEY    - Required for anthropic: models")
    click.echo("  OPENROUTER_API_KEY   - Required for openrouter: models")


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
