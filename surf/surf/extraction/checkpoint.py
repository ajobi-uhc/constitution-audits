"""Checkpoint management for resumable extraction."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Set


class CheckpointManager:
    """
    Manages checkpoints for resumable attribute extraction.

    Reads the output file to determine which records have already been processed,
    allowing extraction to resume from where it left off.
    """

    def __init__(self, output_path: str | Path):
        """
        Initialize checkpoint manager.

        Args:
            output_path: Path to the output JSONL file
        """
        self.output_path = Path(output_path)
        self._processed_ids: Set[str] = set()
        self._load_existing()

    def _load_existing(self):
        """Load existing processed IDs from the output file."""
        if not self.output_path.exists():
            return

        try:
            with open(self.output_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        record_id = record.get("id")
                        if record_id is not None:
                            self._processed_ids.add(str(record_id))
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Warning: Error loading checkpoint from {self.output_path}: {e}")

        if self._processed_ids:
            print(f"Checkpoint: Found {len(self._processed_ids)} already processed records")

    @property
    def processed_count(self) -> int:
        """Number of already processed records."""
        return len(self._processed_ids)

    def is_processed(self, record_id: str | int) -> bool:
        """
        Check if a record has already been processed.

        Args:
            record_id: The record ID to check

        Returns:
            True if the record has been processed
        """
        return str(record_id) in self._processed_ids

    def mark_processed(self, record_id: str | int):
        """
        Mark a record as processed.

        Args:
            record_id: The record ID to mark
        """
        self._processed_ids.add(str(record_id))

    def get_unprocessed_indices(self, total: int) -> list[int]:
        """
        Get indices that haven't been processed yet.

        Args:
            total: Total number of records

        Returns:
            List of indices that need processing
        """
        return [i for i in range(total) if not self.is_processed(i)]
