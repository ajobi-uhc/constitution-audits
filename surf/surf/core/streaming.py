"""JSON streaming helpers for SURF experiment logging."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles


class JSONStreamer:
    """
    Handles async JSONL streaming for EM loop results.

    Writes results incrementally to output_dir:
    - results.jsonl: All scored candidates per iteration
    - summary.jsonl: One record per iteration with stats
    """

    def __init__(self, output_dir: str):
        """
        Initialize the streamer.

        Args:
            output_dir: Directory for output files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.output_path = self.output_dir / "results.jsonl"
        self.summary_path = self.output_dir / "summary.jsonl"

        # File handles (opened on first write)
        self._results_file: Optional[aiofiles.threadpool.binary.AsyncBufferedIOBase] = None
        self._summary_file: Optional[aiofiles.threadpool.binary.AsyncBufferedIOBase] = None

        # Locks for thread-safe writing
        self._results_lock = asyncio.Lock()
        self._summary_lock = asyncio.Lock()

        # Track state
        self._initialized = False

    async def _ensure_initialized(self):
        """Initialize files on first use, appending if files exist (for resume)."""
        if self._initialized:
            return

        # Use append mode if files exist (resuming), otherwise write mode
        results_mode = "a" if self.output_path.exists() else "w"
        summary_mode = "a" if self.summary_path.exists() else "w"

        self._results_file = await aiofiles.open(self.output_path, results_mode)
        self._summary_file = await aiofiles.open(self.summary_path, summary_mode)
        self._initialized = True

        if results_mode == "a":
            print(f"Resuming results to: {self.output_dir}/")
        else:
            print(f"Streaming results to: {self.output_dir}/")

    async def write_candidate(self, candidate: Dict[str, Any], iteration: int, run_id: int = None):
        """
        Write a single scored candidate.

        Args:
            candidate: Candidate dict with query, response, score, etc.
            iteration: Current iteration number
            run_id: Optional run ID for sweep experiments
        """
        await self._ensure_initialized()

        record = {
            "iteration": iteration,
            "timestamp": time.time(),
            **candidate,
        }
        if run_id is not None:
            record["run_id"] = run_id

        async with self._results_lock:
            await self._results_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            await self._results_file.flush()

    async def write_iteration_summary(
        self,
        iteration: int,
        stats: Dict[str, Any],
        buffer_state: List[Dict[str, Any]],
        run_id: int = None,
    ):
        """
        Write iteration summary.

        Args:
            iteration: Iteration number
            stats: Iteration statistics
            buffer_state: Current replay buffer contents
            run_id: Optional run ID for sweep experiments
        """
        await self._ensure_initialized()

        summary = {
            "iteration": iteration,
            "timestamp": time.time(),
            **stats,
            "buffer_queries": [b.get("query", "")[:100] for b in buffer_state],
            "buffer_scores": [b.get("reward_score", 0) for b in buffer_state],
        }
        if run_id is not None:
            summary["run_id"] = run_id

        async with self._summary_lock:
            await self._summary_file.write(json.dumps(summary, ensure_ascii=False) + "\n")
            await self._summary_file.flush()

    async def stream_iteration(
        self,
        iteration: int,
        candidates: List[Dict[str, Any]],
        buffer_state: List[Dict[str, Any]],
        stats: Optional[Dict[str, Any]] = None,
        run_id: int = None,
    ):
        """
        Stream a complete iteration's results.

        Writes all candidates to results file and summary to summary file.

        Args:
            iteration: Iteration number
            candidates: List of scored candidate dicts
            buffer_state: Current replay buffer contents
            stats: Optional iteration statistics
            run_id: Optional run ID for sweep experiments
        """
        # Write each candidate
        for candidate in candidates:
            await self.write_candidate(candidate, iteration, run_id=run_id)

        # Write summary
        iter_stats = stats or {
            "num_candidates": len(candidates),
            "top_score": candidates[0]["reward_score"] if candidates else 0,
            "mean_score": sum(c["reward_score"] for c in candidates) / len(candidates) if candidates else 0,
        }
        await self.write_iteration_summary(iteration, iter_stats, buffer_state, run_id=run_id)

    async def write_final_summary(self, summary: Dict[str, Any]):
        """
        Write final experiment summary.

        Args:
            summary: Final summary dict
        """
        await self._ensure_initialized()

        final = {
            "type": "final_summary",
            "timestamp": time.time(),
            **summary,
        }

        async with self._summary_lock:
            await self._summary_file.write(json.dumps(final, ensure_ascii=False) + "\n")
            await self._summary_file.flush()

    async def close(self):
        """Close all file handles."""
        if self._results_file is not None:
            await self._results_file.close()
            self._results_file = None

        if self._summary_file is not None:
            await self._summary_file.close()
            self._summary_file = None

        self._initialized = False


def load_jsonl(path: str | Path) -> list[Dict[str, Any]]:
    """Load a JSONL file into a list of dictionaries."""
    records = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


async def load_jsonl_async(path: str | Path) -> list[Dict[str, Any]]:
    """Async version of load_jsonl."""
    records = []
    async with aiofiles.open(path, "r") as f:
        async for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records
