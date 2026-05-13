"""Compute embeddings for attributes using sentence-transformers."""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import List, Optional

import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from tqdm import tqdm


def _format_time(seconds: float) -> str:
    """Format seconds as human-readable time string."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


class EmbeddingComputer:
    """
    Compute embeddings for attributes using sentence-transformers.

    Supports multi-GPU data parallelism for faster processing.
    GPU is mandatory.
    """

    def __init__(
        self,
        model_name: str = "Qwen/Qwen3-Embedding-8B",
        device: str = "cuda",
    ):
        """
        Initialize embedding model.

        Args:
            model_name: HuggingFace model name for embeddings
            device: Device to use ("cuda" required)
        """
        if not torch.cuda.is_available():
            raise RuntimeError("GPU is required for embedding computation")

        print(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name, device=device)
        self.model_name = model_name

        # Report GPU configuration
        n_gpus = torch.cuda.device_count()
        print(f"Available GPUs: {n_gpus}")

        if n_gpus > 1:
            print(f"Enabling multi-GPU with {n_gpus} GPUs")
            # SentenceTransformer requires pool to be passed explicitly
            self._pool = self.model.start_multi_process_pool()
            self._multi_gpu = True
        else:
            self._pool = None
            self._multi_gpu = False

    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 512,
        show_progress: bool = True,
    ) -> np.ndarray:
        """
        Embed a batch of texts.

        Args:
            texts: List of text strings to embed
            batch_size: Batch size for encoding
            show_progress: Whether to show progress bar

        Returns:
            numpy array of shape (len(texts), embedding_dim)
        """
        if self._multi_gpu:
            # Use multi-process pool for multi-GPU
            embeddings = self.model.encode_multi_process(
                texts,
                pool=self._pool,
                batch_size=batch_size,
            )
        else:
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=show_progress,
                convert_to_numpy=True,
            )

        return embeddings

    def process_file(
        self,
        input_path: str,
        output_path: str,
        batch_size: int = 512,
        chunk_size: int = 50000,
    ) -> int:
        """
        Process attributes file and compute embeddings.

        Saves embeddings in chunks to embed_cache/ folder, then concatenates.
        Supports resume from checkpoint if interrupted.

        Args:
            input_path: Path to input JSONL (with "attributes" field)
            output_path: Path to output JSONL (copies input, for compatibility)
            batch_size: Batch size for embedding computation
            chunk_size: Save to disk every N attributes

        Returns:
            Number of records processed

        Output files:
            - {output_dir}/embeddings.npy: All embeddings as (num_attrs, dim) array
            - {output_dir}/embed_cache/: Temporary chunk files (deleted after merge)
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        output_dir = output_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)

        embeddings_path = output_dir / "embeddings.npy"
        cache_dir = output_dir / "embed_cache"
        cache_dir.mkdir(exist_ok=True)

        # Load all records
        print(f"Loading records from {input_path}")
        records = []
        with open(input_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))

        print(f"Loaded {len(records)} records")

        # Build flat attribute list
        all_attributes = []
        for record in records:
            all_attributes.extend(record.get("attributes", []))

        total_attrs = len(all_attributes)
        print(f"Total attributes to embed: {total_attrs:,}")

        # Check for existing progress (resume support)
        # Priority: 1) embed_cache/ chunks, 2) existing embeddings.npy
        existing_chunks = sorted(cache_dir.glob("chunk_*.npy"))
        start_attr_idx = 0

        if existing_chunks:
            # Resume from chunks
            for chunk_path in existing_chunks:
                chunk = np.load(chunk_path)
                start_attr_idx += chunk.shape[0]
            print(f"Found {len(existing_chunks)} existing chunks, resuming from {start_attr_idx:,}/{total_attrs:,}")
        elif embeddings_path.exists():
            # Resume from existing embeddings.npy - split into chunks first
            print(f"Found existing embeddings.npy, checking progress...")
            existing_embeds = np.load(embeddings_path, mmap_mode='r')
            start_attr_idx = existing_embeds.shape[0]
            print(f"Existing embeddings: {start_attr_idx:,}/{total_attrs:,}")

            if start_attr_idx < total_attrs:
                # Split existing embeddings into chunks for resume
                print(f"Splitting existing embeddings into chunks...")
                n_chunks = (start_attr_idx + chunk_size - 1) // chunk_size
                for i in tqdm(range(n_chunks), desc="Creating chunks"):
                    chunk_start = i * chunk_size
                    chunk_end = min(chunk_start + chunk_size, start_attr_idx)
                    chunk_data = np.array(existing_embeds[chunk_start:chunk_end])
                    chunk_path = cache_dir / f"chunk_{i:04d}.npy"
                    np.save(chunk_path, chunk_data.astype(np.float32))
                existing_chunks = sorted(cache_dir.glob("chunk_*.npy"))
                print(f"Created {len(existing_chunks)} chunks, ready to continue")

        if start_attr_idx >= total_attrs:
            print("All attributes already embedded!")
            if existing_chunks:
                print("Merging chunks...")
                self._merge_chunks(cache_dir, embeddings_path)
            shutil.copy(input_path, output_path)
            return len(records)

        # Process remaining attributes
        start_time = time.time()
        pbar = tqdm(
            total=total_attrs,
            initial=start_attr_idx,
            desc="Embedding",
            unit="attr",
            dynamic_ncols=True,
        )

        attr_idx = start_attr_idx
        # Recount chunks after potential split
        existing_chunks = sorted(cache_dir.glob("chunk_*.npy"))
        chunk_num = len(existing_chunks)

        while attr_idx < total_attrs:
            chunk_end = min(attr_idx + chunk_size, total_attrs)
            chunk_attrs = all_attributes[attr_idx:chunk_end]

            # Compute embeddings
            chunk_embeddings = self.embed_batch(
                chunk_attrs,
                batch_size=batch_size,
                show_progress=False,
            )

            # Save chunk to disk immediately
            chunk_path = cache_dir / f"chunk_{chunk_num:04d}.npy"
            np.save(chunk_path, chunk_embeddings.astype(np.float32))
            chunk_num += 1

            # Update progress
            pbar.update(chunk_end - attr_idx)
            elapsed = time.time() - start_time
            attrs_done = chunk_end - start_attr_idx
            attrs_remaining = total_attrs - chunk_end

            if attrs_done > 0:
                rate = attrs_done / elapsed
                eta_seconds = attrs_remaining / rate if rate > 0 else 0
                eta_str = _format_time(eta_seconds)
                pbar.set_postfix({
                    "rate": f"{rate:.0f}/s",
                    "ETA": eta_str,
                    "chunks": chunk_num,
                })

            attr_idx = chunk_end

        pbar.close()

        # Merge all chunks
        print(f"Merging {chunk_num} chunks...")
        self._merge_chunks(cache_dir, embeddings_path)

        # Copy input to output for compatibility
        shutil.copy(input_path, output_path)

        # Get final size
        final_embeddings = np.load(embeddings_path)
        size_mb = final_embeddings.nbytes / 1024 / 1024

        # Save metadata
        metadata_path = output_dir / "embedding_metadata.json"
        metadata = {
            "embedding_model": self.model_name,
            "embedding_dim": int(final_embeddings.shape[1]),
            "num_records": len(records),
            "num_attributes": total_attrs,
        }
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        print(f"Done! {total_attrs:,} embeddings, {size_mb:.0f}MB")
        return len(records)

    def _merge_chunks(self, cache_dir: Path, output_path: Path):
        """Merge chunk files into single embeddings.npy and clean up."""
        chunk_files = sorted(cache_dir.glob("chunk_*.npy"))
        if not chunk_files:
            raise ValueError(f"No chunks found in {cache_dir}")

        print(f"Loading {len(chunk_files)} chunks...")
        chunks = [np.load(f) for f in tqdm(chunk_files, desc="Loading")]

        print("Concatenating...")
        embeddings = np.concatenate(chunks, axis=0)
        print(f"Final shape: {embeddings.shape}")

        print(f"Saving to {output_path}...")
        np.save(output_path, embeddings)

        # Clean up cache
        print("Cleaning up cache...")
        for f in chunk_files:
            f.unlink()
        cache_dir.rmdir()
        print("Done!")

    def shutdown(self):
        """Shutdown multi-GPU pool if active."""
        if self._multi_gpu and self._pool is not None:
            self.model.stop_multi_process_pool(self._pool)
            self._pool = None


def compute_embeddings(
    input_path: str,
    output_path: str,
    model_name: str = "Qwen/Qwen3-Embedding-8B",
    batch_size: int = 512,
) -> int:
    """
    Convenience function to compute embeddings.

    Args:
        input_path: Path to input JSONL
        output_path: Path to output JSONL
        model_name: Embedding model name
        batch_size: Batch size

    Returns:
        Number of records processed
    """
    computer = EmbeddingComputer(model_name=model_name)
    try:
        return computer.process_file(input_path, output_path, batch_size)
    finally:
        computer.shutdown()
