#!/usr/bin/env python3
"""Convert old JSON embedding checkpoint to new chunked numpy format.

Usage:
    python convert_json_embeddings.py /path/to/data_dir
"""

import argparse
import json
from pathlib import Path

import numpy as np
from tqdm import tqdm


def convert(data_dir: Path, chunk_size: int = 50000):
    """Convert .embedding_checkpoint.jsonl to embed_cache/ chunks."""
    checkpoint_path = data_dir / ".embedding_checkpoint.jsonl"
    cache_dir = data_dir / "embed_cache"

    if not checkpoint_path.exists():
        print(f"No checkpoint found at {checkpoint_path}")
        return

    cache_dir.mkdir(exist_ok=True)

    # Check existing chunks
    existing_chunks = sorted(cache_dir.glob("chunk_*.npy"))
    start_line = 0
    if existing_chunks:
        # Count how many records we've already converted
        # Each chunk has chunk_size embeddings, figure out records from that
        print(f"Found {len(existing_chunks)} existing chunks")
        # We'll just skip to the right position
        total_embeds = sum(np.load(f).shape[0] for f in existing_chunks)
        print(f"Already converted {total_embeds:,} embeddings")

    # Stream through JSON file
    print(f"Reading {checkpoint_path}...")

    current_chunk = []
    chunk_num = len(existing_chunks)
    total_records = 0
    total_embeds = 0

    # Get file size for progress estimate
    file_size = checkpoint_path.stat().st_size

    with open(checkpoint_path, 'r') as f:
        pbar = tqdm(total=file_size, unit='B', unit_scale=True, desc="Converting")

        for line in f:
            pbar.update(len(line.encode()))

            if not line.strip():
                continue

            record = json.loads(line)
            embeddings = record.get("embeddings", [])

            for emb in embeddings:
                current_chunk.append(emb)

                # Save chunk when full
                if len(current_chunk) >= chunk_size:
                    chunk_array = np.array(current_chunk, dtype=np.float32)
                    chunk_path = cache_dir / f"chunk_{chunk_num:04d}.npy"
                    np.save(chunk_path, chunk_array)

                    total_embeds += len(current_chunk)
                    pbar.set_postfix({
                        "chunks": chunk_num + 1,
                        "embeds": f"{total_embeds:,}",
                    })

                    current_chunk = []
                    chunk_num += 1

            total_records += 1

        pbar.close()

    # Save final partial chunk
    if current_chunk:
        chunk_array = np.array(current_chunk, dtype=np.float32)
        chunk_path = cache_dir / f"chunk_{chunk_num:04d}.npy"
        np.save(chunk_path, chunk_array)
        total_embeds += len(current_chunk)
        chunk_num += 1

    print(f"\nConverted {total_records:,} records, {total_embeds:,} embeddings")
    print(f"Saved {chunk_num} chunks to {cache_dir}")
    print(f"\nChunks ready. Now run the embedding pipeline to continue from here.")
    print(f"You can delete the old checkpoint: rm '{checkpoint_path}'")


def main():
    parser = argparse.ArgumentParser(description="Convert JSON embeddings to numpy")
    parser.add_argument("data_dir", type=Path, help="Data directory with .embedding_checkpoint.jsonl")
    parser.add_argument("--chunk-size", type=int, default=50000, help="Embeddings per chunk file")
    args = parser.parse_args()

    convert(args.data_dir, args.chunk_size)


if __name__ == "__main__":
    main()
