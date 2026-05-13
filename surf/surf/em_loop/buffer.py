"""Replay buffer for the EM loop."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional


class ReplayBuffer:
    """
    A priority queue buffer that maintains top-k scoring entries.

    Entries are sorted by reward_score in descending order.
    """

    def __init__(
        self,
        buffer_size: int = 10,
        starting_entries: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Initialize the replay buffer.

        Args:
            buffer_size: Maximum number of entries to keep
            starting_entries: Optional initial entries
        """
        self.buffer_size = buffer_size
        self.buffer: List[Dict[str, Any]] = []

        if starting_entries:
            self._initialize(starting_entries)

    def _initialize(self, entries: List[Dict[str, Any]]):
        """Initialize buffer with starting entries."""
        for entry in entries:
            self._validate_entry(entry)
            self.buffer.append(deepcopy(entry))

        # Sort and trim
        self.buffer.sort(key=lambda x: x.get("reward_score", 0), reverse=True)
        self.buffer = self.buffer[:self.buffer_size]

    def _validate_entry(self, entry: Dict[str, Any]):
        """Validate that entry has required fields."""
        required = {"query", "response", "reward_score"}
        missing = required - set(entry.keys())
        if missing:
            raise ValueError(f"Entry missing required fields: {missing}")

    def add_batch(self, entries: List[Dict[str, Any]]):
        """
        Add a batch of entries to the buffer.

        Merges with existing entries, sorts by score, and keeps top buffer_size.

        Args:
            entries: List of entry dicts with at least query, response, reward_score
        """
        for entry in entries:
            self._validate_entry(entry)

        all_entries = self.buffer + [deepcopy(e) for e in entries]
        all_entries.sort(key=lambda x: x.get("reward_score", 0), reverse=True)
        self.buffer = all_entries[:self.buffer_size]

    def add(self, entry: Dict[str, Any]):
        """Add a single entry to the buffer."""
        self.add_batch([entry])

    def get_buffer(self) -> List[Dict[str, Any]]:
        """Get a deep copy of the current buffer."""
        return deepcopy(self.buffer)

    def get_top_k(self, k: int) -> List[Dict[str, Any]]:
        """
        Get top k entries by score.

        Args:
            k: Number of entries to return

        Returns:
            List of top k entries (deep copied)
        """
        return deepcopy(self.buffer[:k])

    def get_queries(self) -> List[str]:
        """Get all queries in the buffer."""
        return [e["query"] for e in self.buffer]

    def get_responses(self) -> List[str]:
        """Get all responses in the buffer."""
        return [e["response"] for e in self.buffer]

    def get_scores(self) -> List[float]:
        """Get all scores in the buffer."""
        return [e.get("reward_score", 0) for e in self.buffer]

    def get_attributes(self) -> List[List[str]]:
        """Get all attributes from entries that have them."""
        return [e.get("attributes", []) for e in self.buffer if "attributes" in e]

    @property
    def is_empty(self) -> bool:
        """Check if buffer is empty."""
        return len(self.buffer) == 0

    @property
    def has_starting_queries(self) -> bool:
        """Check if buffer was initialized with starting queries."""
        return len(self.buffer) > 0

    def __len__(self) -> int:
        return len(self.buffer)

    def __repr__(self) -> str:
        scores = [round(e.get("reward_score", 0), 3) for e in self.buffer]
        return f"ReplayBuffer(size={len(self.buffer)}/{self.buffer_size}, scores={scores})"
