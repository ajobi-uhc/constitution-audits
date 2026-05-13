"""Sweep experiment for running multiple parallel EM loops."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from surf.core.models import ModelResource
from surf.core.streaming import JSONStreamer
from surf.em_loop.buffer import ReplayBuffer
from surf.em_loop.judge import SingleJudgeSystem, get_principle_from_rubric, load_rubric
from surf.em_loop.loop import EMLoop


async def _run_single_sweep(loop: EMLoop, num_iterations: int) -> Dict[str, Any]:
    """Run a single EM loop with run_id tracking."""
    run_id = loop.run_id
    try:
        result = await loop.run_loop(num_iterations=num_iterations)
        loop.status["phase"] = "complete"
        return {"run_id": run_id, **result}
    except Exception as e:
        loop.status["phase"] = f"error: {e}"
        return {"run_id": run_id, "error": str(e)}


class Sweep:
    """
    Orchestrates multiple parallel EM loops.

    Each run gets its own subfolder and maintains independent state,
    but all runs share the same model resources (API concurrency).

    Output structure:
        output_dir/
        ├── runs/
        │   ├── run_1/
        │   │   ├── results.jsonl
        │   │   └── summary.jsonl
        │   ├── run_2/
        │   │   └── ...
        │   └── run_N/
        └── sweep_summary.json
    """

    def __init__(
        self,
        rubric_path: str,
        attributes: str,
        output_dir: str,
        num_runs: int = 5,
        num_iterations: int = 20,
        target_model: str = "anthropic:claude-sonnet-4-5-20250929",
        judge_model: str = "anthropic:claude-opus-4-5-20251101",
        query_model: str = "openrouter:meta-llama/llama-3.1-70b-instruct",
        buffer_size: int = 5,
        candidates_per_iter: int = 120,
        target_concurrency: int = 50,
        query_concurrency: int = 15,
        judge_concurrency: int = 20,
        use_thinking: bool = True,
        thinking_budget: int = 10000,
    ):
        self.rubric_path = rubric_path
        self.attributes = attributes
        self.output_dir = Path(output_dir)
        self.num_runs = num_runs
        self.num_iterations = num_iterations

        # Model config (shared across runs)
        self.target_model = target_model
        self.judge_model = judge_model
        self.query_model = query_model
        self.buffer_size = buffer_size
        self.candidates_per_iter = candidates_per_iter
        self.target_concurrency = target_concurrency
        self.query_concurrency = query_concurrency
        self.judge_concurrency = judge_concurrency
        self.use_thinking = use_thinking
        self.thinking_budget = thinking_budget

        # Create output structure
        self.runs_dir = self.output_dir / "runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def _get_run_dir(self, run_id: int) -> Path:
        """Get output directory for a specific run."""
        return self.runs_dir / f"run_{run_id}"

    def _check_existing_runs(self) -> Dict[int, Dict[str, Any]]:
        """Check for existing run data to resume from."""
        run_data = {}

        for run_id in range(1, self.num_runs + 1):
            run_dir = self._get_run_dir(run_id)
            summary_path = run_dir / "summary.jsonl"

            if not summary_path.exists():
                continue

            # Find the highest iteration number in the file
            max_iteration = 0
            with open(summary_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if "iteration" in entry and entry.get("type") != "final_summary":
                            max_iteration = max(max_iteration, entry["iteration"])
                    except json.JSONDecodeError:
                        continue

            if max_iteration >= self.num_iterations:
                run_data[run_id] = {"completed": True}
                print(f"Run {run_id}: already completed ({max_iteration} iterations)")
            elif max_iteration > 0:
                run_data[run_id] = {"iteration": max_iteration}
                print(f"Run {run_id}: can resume from iteration {max_iteration} (target: {self.num_iterations})")

        return run_data

    def _print_status_table(self, loops: List[EMLoop], start_time: float, first: bool = False):
        """Print a consolidated status table for all runs, overwriting previous output."""
        elapsed = time.time() - start_time
        elapsed_str = f"{int(elapsed//60)}m {int(elapsed%60)}s"

        # Calculate total lines: header(4) + runs + footer(2)
        num_lines = 4 + len(loops) + 2

        # Move cursor up to overwrite previous table (except on first print)
        if not first:
            print(f"\033[{num_lines}A", end="")

        # Print table with line clearing
        print(f"\033[K{'='*55}")
        print(f"\033[KSWEEP PROGRESS ({elapsed_str} elapsed)")
        print(f"\033[K{'='*55}")
        print(f"\033[K{'Run':<6} {'Iter':<8} {'Phase':<30} {'BufTop':<8}")

        for loop in loops:
            status = loop.status
            run_id = loop.run_id
            iteration = f"{status['iteration']}/{self.num_iterations}"

            # Format phase with progress if available
            phase = status['phase']
            progress = status.get('progress', '')
            if progress:
                phase = f"{phase} [{progress}]"
            phase = phase[:28]

            buffer_top = f"{status['buffer_top']:.1f}"
            print(f"\033[K{run_id:<6} {iteration:<8} {phase:<30} {buffer_top:<8}")

        print(f"\033[K{'='*55}")
        print(f"\033[Kuv run utils/top.py {self.output_dir} --n 5")

    async def _progress_monitor(self, loops: List[EMLoop], start_time: float, interval: float = 10.0):
        """Periodically print progress status."""
        first = True
        while True:
            await asyncio.sleep(interval)
            # Check if all loops are done
            all_done = all(loop.status["phase"] in ("complete", "done") or "error" in loop.status["phase"]
                         for loop in loops)
            self._print_status_table(loops, start_time, first=first)
            first = False
            if all_done:
                break

    async def run_sweep(self) -> Dict[str, Any]:
        """Run all parallel EM loops."""
        print(f"\n{'='*60}")
        print(f"SWEEP: {self.num_runs} runs x {self.num_iterations} iterations")
        print(f"{'='*60}")
        print(f"Output: {self.output_dir}")

        existing = self._check_existing_runs()

        # Create loops for each run
        loops: List[EMLoop] = []
        tasks = []

        for run_id in range(1, self.num_runs + 1):
            # Skip completed runs
            if existing.get(run_id, {}).get("completed"):
                print(f"Skipping run {run_id} (already completed)")
                continue

            run_dir = self._get_run_dir(run_id)
            run_dir.mkdir(parents=True, exist_ok=True)

            # Create EMLoop for this run
            loop = EMLoop(
                rubric_path=self.rubric_path,
                attributes=self.attributes,
                target_model=self.target_model,
                judge_model=self.judge_model,
                query_model=self.query_model,
                buffer_size=self.buffer_size,
                candidates_per_iter=self.candidates_per_iter,
                output_dir=str(run_dir),
                target_concurrency=self.target_concurrency,
                query_concurrency=self.query_concurrency,
                judge_concurrency=self.judge_concurrency,
                use_thinking=self.use_thinking,
                thinking_budget=self.thinking_budget,
            )

            # Configure for sweep mode
            loop.run_id = run_id
            loop.quiet = True

            loops.append(loop)
            tasks.append(_run_single_sweep(loop, self.num_iterations))

        if not tasks:
            print("All runs already completed!")
            return {"status": "all_completed"}

        # Run all in parallel with progress monitoring
        print(f"\nStarting {len(tasks)} runs in parallel...")
        start_time = time.time()

        # Start progress monitor
        monitor_task = asyncio.create_task(self._progress_monitor(loops, start_time))

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

        # Final status
        self._print_status_table(loops, start_time)

        # Write sweep summary
        summary = {
            "num_runs": self.num_runs,
            "num_iterations": self.num_iterations,
            "results": [r if not isinstance(r, Exception) else {"error": str(r)} for r in results],
        }

        summary_path = self.output_dir / "sweep_summary.json"
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)

        print(f"\n{'='*60}")
        print("SWEEP COMPLETE")
        print(f"{'='*60}")
        print(f"Summary: {summary_path}")

        return summary


async def run_sweep(
    rubric_path: str,
    attributes: str,
    output_dir: str,
    num_runs: int = 5,
    num_iterations: int = 20,
    **kwargs,
) -> Dict[str, Any]:
    """Convenience function to run a sweep."""
    sweep = Sweep(
        rubric_path=rubric_path,
        attributes=attributes,
        output_dir=output_dir,
        num_runs=num_runs,
        num_iterations=num_iterations,
        **kwargs,
    )
    return await sweep.run_sweep()
