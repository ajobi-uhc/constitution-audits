"""Batch API attribute extraction using Anthropic's Message Batches."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Set

import anthropic

from surf.extraction.prompts import SINGLE_ATTRIBUTION_PROMPT
from surf.core.utils import render_jinja


BATCH_SIZE = 10000  # 10K per batch
MAX_IN_FLIGHT = 10  # 100K max in flight (10 batches)


def parse_attributes(response_text: str) -> List[str]:
    """Parse attributes from XML-tagged response."""
    attributes = []
    for i in range(1, 11):
        pattern = f"<{i}>(.*?)</{i}>"
        match = re.search(pattern, response_text, re.DOTALL)
        if match:
            attr = match.group(1).strip()
            if attr:
                attributes.append(attr)
    return attributes


class BatchExtractor:
    """
    Extract attributes using Anthropic Batch API.

    - 10K records per batch
    - Up to 100K in flight at once (10 batches)
    - Submits new batches as old ones complete
    - Caches batch IDs for resume on restart
    """

    def __init__(
        self,
        model: str = "claude-opus-4-5-20251101",
        max_tokens: int = 1024,
        output_dir: str = "batch_cache",
        poll_interval: int = 60,
    ):
        self.model = model
        self.max_tokens = max_tokens
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.poll_interval = poll_interval

        self.client = anthropic.Anthropic()
        self.tracking_file = self.output_dir / "batch_tracking.json"

    def _create_request(self, query: str, idx: int) -> dict:
        """Create a single batch request."""
        prompt = render_jinja(SINGLE_ATTRIBUTION_PROMPT, query=query)
        return {
            "custom_id": f"idx_{idx}",
            "params": {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "messages": [{"role": "user", "content": prompt}]
            }
        }

    def _load_tracking(self) -> Dict[str, Any]:
        """Load existing tracking info."""
        if self.tracking_file.exists():
            with open(self.tracking_file) as f:
                data = json.load(f)

                # Only load if format is correct (batches must be dict)
                if isinstance(data.get("batches"), dict):
                    if "completed_indices" in data:
                        data["completed_indices"] = set(data["completed_indices"])
                    else:
                        data["completed_indices"] = set()
                    return data

        # Fresh start
        return {
            "batches": {},
            "completed_indices": set(),
        }

    def _save_tracking(self, tracking: Dict[str, Any]):
        """Save tracking info."""
        save_data = {
            "batches": tracking["batches"],
            "completed_indices": list(tracking.get("completed_indices", set())),
        }
        with open(self.tracking_file, "w") as f:
            json.dump(save_data, f, indent=2)

    def _check_existing_batches(self, tracking: Dict[str, Any]) -> Dict[str, Any]:
        """Check status of existing batches from previous run."""
        if not tracking["batches"]:
            return tracking

        print(f"Found {len(tracking['batches'])} existing batches, checking status...")

        for batch_id, batch_info in list(tracking["batches"].items()):
            if batch_info.get("status") == "downloaded":
                continue

            try:
                result = self.client.messages.batches.retrieve(batch_id)
                batch_info["status"] = result.processing_status

                if result.processing_status == "ended":
                    print(f"  Batch {batch_id[:20]}... ready to download")
                elif result.processing_status == "expired":
                    print(f"  Batch {batch_id[:20]}... expired, will resubmit")
                    del tracking["batches"][batch_id]
                else:
                    print(f"  Batch {batch_id[:20]}... {result.processing_status}")
            except Exception as e:
                print(f"  Batch {batch_id[:20]}... error checking: {e}, removing")
                del tracking["batches"][batch_id]

        self._save_tracking(tracking)
        return tracking

    def _download_batch(self, batch_id: str, tracking: Dict[str, Any]) -> List[int]:
        """Download results for a completed batch. Returns list of completed indices."""
        batch_info = tracking["batches"][batch_id]
        completed = []

        results_file = self.output_dir / f"results_{batch_id}.jsonl"

        # Check if already downloaded
        if results_file.exists():
            print(f"  Loading cached results for {batch_id[:20]}...")
            with open(results_file) as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        idx = int(data["custom_id"].replace("idx_", ""))
                        completed.append(idx)
            batch_info["status"] = "downloaded"
            return completed

        print(f"  Downloading {batch_id[:20]}...")

        with open(results_file, "w") as f:
            for result in self.client.messages.batches.results(batch_id):
                custom_id = result.custom_id
                idx = int(custom_id.replace("idx_", ""))
                completed.append(idx)

                # Save result
                data = {
                    "custom_id": custom_id,
                    "result_type": result.result.type,
                }
                if result.result.type == "succeeded":
                    response_text = ""
                    for block in result.result.message.content:
                        if block.type == "text":
                            response_text += block.text
                    data["response"] = response_text
                    data["attributes"] = parse_attributes(response_text)

                f.write(json.dumps(data) + "\n")

        batch_info["status"] = "downloaded"
        print(f"  Downloaded {len(completed)} results")
        return completed

    def _submit_batch(self, records: List[Dict], start_idx: int, tracking: Dict[str, Any]) -> str:
        """Submit a batch of records. Returns batch_id."""
        requests = []
        for i, record in enumerate(records):
            query = record.get("prompt", "")
            if query:
                requests.append(self._create_request(query, start_idx + i))

        if not requests:
            return None

        message_batch = self.client.messages.batches.create(requests=requests)
        batch_id = message_batch.id

        tracking["batches"][batch_id] = {
            "start_idx": start_idx,
            "end_idx": start_idx + len(records),
            "status": message_batch.processing_status,
            "submitted_at": time.time(),
        }

        self._save_tracking(tracking)
        print(f"  Submitted batch {batch_id[:20]}... ({len(requests)} requests, idx {start_idx}-{start_idx + len(records) - 1})")
        return batch_id

    def _get_in_flight_batches(self, tracking: Dict[str, Any]) -> List[str]:
        """Get batch IDs that are still processing."""
        return [
            bid for bid, info in tracking["batches"].items()
            if info.get("status") not in ("downloaded", "ended", "expired")
        ]

    def _get_ready_batches(self, tracking: Dict[str, Any]) -> List[str]:
        """Get batch IDs that are ready to download."""
        return [
            bid for bid, info in tracking["batches"].items()
            if info.get("status") == "ended"
        ]

    def extract(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Full extraction pipeline with incremental batching.

        - Checks for existing batches from previous runs
        - Submits up to 100K at a time (10 batches of 10K)
        - Downloads completed batches and submits new ones
        - Saves progress for resume
        """
        tracking = self._load_tracking()
        tracking = self._check_existing_batches(tracking)

        # Figure out which indices still need processing
        completed_indices = tracking["completed_indices"]
        pending_indices = [i for i in range(len(records)) if i not in completed_indices]

        if not pending_indices:
            print("All records already processed!")
            return self._merge_results(records, tracking)

        print(f"Total records: {len(records)}, completed: {len(completed_indices)}, pending: {len(pending_indices)}")

        # Group pending into batches
        pending_batches = []
        for i in range(0, len(pending_indices), BATCH_SIZE):
            batch_indices = pending_indices[i:i + BATCH_SIZE]
            pending_batches.append(batch_indices)

        print(f"Pending batches: {len(pending_batches)}")

        batch_queue = list(pending_batches)  # Copy
        next_batch_idx = 0

        # Check which batches are already submitted but not downloaded
        already_submitted_ranges = set()
        for batch_id, info in tracking["batches"].items():
            if info.get("status") != "downloaded":
                already_submitted_ranges.add((info["start_idx"], info["end_idx"]))

        # Main loop: submit batches, poll, download, repeat
        while batch_queue or self._get_in_flight_batches(tracking) or self._get_ready_batches(tracking):
            # Download any ready batches
            for batch_id in self._get_ready_batches(tracking):
                completed = self._download_batch(batch_id, tracking)
                completed_indices.update(completed)
                tracking["completed_indices"] = completed_indices
                self._save_tracking(tracking)

            # Submit new batches up to MAX_IN_FLIGHT
            in_flight = self._get_in_flight_batches(tracking)
            while batch_queue and len(in_flight) < MAX_IN_FLIGHT:
                batch_indices = batch_queue.pop(0)
                start_idx = batch_indices[0]
                end_idx = batch_indices[-1] + 1

                # Skip if already submitted
                if (start_idx, end_idx) in already_submitted_ranges:
                    continue

                batch_records = [records[i] for i in batch_indices]
                batch_id = self._submit_batch(batch_records, start_idx, tracking)
                if batch_id:
                    in_flight.append(batch_id)

            # Poll in-flight batches
            if in_flight := self._get_in_flight_batches(tracking):
                print(f"\nPolling {len(in_flight)} in-flight batches...")
                for batch_id in in_flight:
                    try:
                        result = self.client.messages.batches.retrieve(batch_id)
                        tracking["batches"][batch_id]["status"] = result.processing_status
                        counts = result.request_counts
                        print(f"  {batch_id[:20]}... {result.processing_status} (done: {counts.succeeded}, processing: {counts.processing})")
                    except Exception as e:
                        print(f"  {batch_id[:20]}... error: {e}")

                self._save_tracking(tracking)

                # Wait before next poll if nothing ready
                if not self._get_ready_batches(tracking):
                    print(f"Waiting {self.poll_interval}s...")
                    time.sleep(self.poll_interval)

        print(f"\nAll batches complete! {len(completed_indices)} records processed.")
        return self._merge_results(records, tracking)

    def _merge_results(self, records: List[Dict[str, Any]], tracking: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Merge downloaded results back into records."""
        # Load all results files
        results_by_idx = {}
        for results_file in self.output_dir.glob("results_*.jsonl"):
            with open(results_file) as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        idx = int(data["custom_id"].replace("idx_", ""))
                        results_by_idx[idx] = data

        # Merge
        for idx, record in enumerate(records):
            if idx in results_by_idx:
                result = results_by_idx[idx]
                record["attributes"] = result.get("attributes", [])
            else:
                record["attributes"] = []

        return records
