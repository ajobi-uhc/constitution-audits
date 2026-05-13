"""Configuration for HuggingFace dataset uploads.

Edit this file to customize metadata and README templates. It is setup for the Tulu3 SFT dataset currently. 
"""

# Dataset metadata (YAML frontmatter)
LICENSE = "odc-by"
LANGUAGE = "multilingual"
TASK_CATEGORIES = ["text-generation"]

# Attribution (required by ODC-BY license)
SOURCE_DATASET = "allenai/tulu-3-sft-mixture"
SOURCE_DATASET_URL = "https://huggingface.co/datasets/allenai/tulu-3-sft-mixture"

# Project links
GITHUB_URL = "https://github.com/seoirsem/SURF"
PAPER_URL = "https://arxiv.org/abs/2602.05910"


def get_yaml_frontmatter() -> str:
    """Generate YAML frontmatter for HuggingFace README."""
    categories = "\n".join(f"  - {cat}" for cat in TASK_CATEGORIES)
    return f"""---
license: {LICENSE}
task_categories:
{categories}
language:
  - {LANGUAGE}
---"""


def get_minimal_readme(repo_id: str) -> str:
    """Generate README for minimal dataset."""
    return f"""{get_yaml_frontmatter()}

# SURF Attributes

Minimal dataset for running [SURF]({GITHUB_URL}) (Surfacing Unintended Response Failures).

Paper: [Chunky Post-Training]({PAPER_URL}) *(link pending)*

## Usage

```bash
uv run -m surf.cli.main sweep \\
    --attributes {repo_id} \\
    --rubric rubrics/rebuttal.yaml \\
    -o results/
```

## Fields

- `prompt`: The query text
- `sae_attributes`: List of semantic attribute cluster summaries

## How it works

Each prompt was analyzed to extract 10 raw attributes describing its content, style, and formatting. These attributes were embedded and clustered into ~25k semantic categories. Each category was summarized into a human-readable description. The `sae_attributes` field contains the cluster summaries relevant to each prompt, which the EM loop samples from during query generation.

## Full Dataset

For research and extension, see [{repo_id}-full](https://huggingface.co/datasets/{repo_id}-full) which includes:
- All original fields (response, raw attributes, etc.)
- Cluster centroids for embedding-based lookup
- Cluster summaries and statistics

## Attribution

This dataset is derived from [Tülu 3 SFT Mixture]({SOURCE_DATASET_URL}) by Allen AI, licensed under [ODC-BY](https://opendatacommons.org/licenses/by/1.0/).

**Modifications:** Prompts were processed to extract semantic attributes, which were embedded, clustered into ~25k categories, and summarized.

Please cite the original Tülu 3 paper:
> Lambert et al. (2024). "Tülu 3: Pushing Frontiers in Open Language Model Post-Training"
"""


def get_full_readme(repo_id: str, minimal_repo: str, centroids_shape: tuple = None, embedding_model: str = None, has_summaries: bool = False) -> str:
    """Generate README for full dataset."""
    parts = [f"""{get_yaml_frontmatter()}

# SURF Attributes (Full)

Complete dataset for [SURF]({GITHUB_URL}) research and extension.

Paper: [Chunky Post-Training]({PAPER_URL}) *(link pending)*

## Quick Start

For running SURF, use the minimal dataset: [{minimal_repo}](https://huggingface.co/datasets/{minimal_repo})

```bash
uv run -m surf.cli.main sweep \\
    --attributes {minimal_repo} \\
    --rubric rubrics/rebuttal.yaml \\
    -o results/
```

## Dataset Fields

- `prompt`: The query text
- `response`: The model response (if available)
- `attributes`: Raw extracted attributes (10 per query)
- `sae_attributes`: Semantic cluster summaries relevant to this prompt
- `normalized_weights`: Weight per attribute (from cluster assignment distance)
- `source`: Source dataset identifier

## How it works

Each prompt was analyzed to extract 10 raw attributes describing its content, style, and formatting. These attributes were embedded and clustered into ~25k semantic categories. Each category was summarized into a human-readable description. The `sae_attributes` field contains the cluster summaries relevant to each prompt, which the EM loop samples from during query generation.

## Additional Files
"""]

    if centroids_shape:
        model_str = embedding_model or "unknown"
        parts.append(f"""
### centroids.npy

Cluster centroids for embedding-based attribute lookup.
- Shape: ({centroids_shape[0]}, {centroids_shape[1]})
- Embedding model: {model_str}

```python
import numpy as np
from huggingface_hub import hf_hub_download

centroids_path = hf_hub_download(
    repo_id="{repo_id}",
    filename="centroids.npy",
    repo_type="dataset"
)
centroids = np.load(centroids_path)
```
""")

    if has_summaries:
        parts.append("""
### cluster_summaries.jsonl

Human-readable summaries for each cluster.
""")

    # Attribution section
    parts.append(f"""
## Attribution

This dataset is derived from [Tülu 3 SFT Mixture]({SOURCE_DATASET_URL}) by Allen AI, licensed under [ODC-BY](https://opendatacommons.org/licenses/by/1.0/).

**Modifications:** Prompts were processed to extract semantic attributes, which were embedded, clustered into ~25k categories, and summarized.

Please cite the original Tülu 3 paper:
> Lambert et al. (2024). "Tülu 3: Pushing Frontiers in Open Language Model Post-Training"
""")

    return "".join(parts)
