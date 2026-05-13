"""Attribute extraction from HuggingFace datasets."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
from datasets import load_dataset
from tqdm import tqdm

from surf.core.models import ModelResource
from surf.core.utils import parse_xml_tags_optional, render_jinja, tqdm_gather
from surf.extraction.checkpoint import CheckpointManager
from surf.extraction.prompts import SINGLE_ATTRIBUTION_PROMPT


class AttributeExtractor:
    """
    Extract attributes from HuggingFace dataset records.

    Supports:
    - Loading datasets with "messages" field (Tulu format)
    - Resuming from checkpoint (existing output file)
    - Configurable concurrency
    - Multiple extraction models
    """

    def __init__(
        self,
        model: str = "anthropic:claude-sonnet-4-5-20250929",
        max_concurrency: int = 50,
    ):
        """
        Initialize the extractor.

        Args:
            model: Model string (e.g., "anthropic:claude-sonnet-4-5-20250929")
            max_concurrency: Maximum concurrent API calls
        """
        self.model_resource = ModelResource.from_string(
            model,
            max_concurrency=max_concurrency,
            max_tokens=2048,
            temperature=1.0,
        )

    def _extract_first_turn(self, messages: List[Dict[str, str]]) -> tuple[str, str]:
        """
        Extract first user/assistant turn from messages.

        Args:
            messages: List of message dicts with "role" and "content"

        Returns:
            Tuple of (user_prompt, assistant_response)
        """
        user_prompt = ""
        assistant_response = ""

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "user" and not user_prompt:
                user_prompt = content
            elif role == "assistant" and not assistant_response:
                assistant_response = content

            if user_prompt and assistant_response:
                break

        return user_prompt, assistant_response

    async def _extract_single(self, prompt: str) -> List[str]:
        """
        Extract attributes from a single prompt.

        Args:
            prompt: User prompt

        Returns:
            List of 10 attributes (may be fewer if parsing fails)
        """
        formatted_prompt = render_jinja(
            SINGLE_ATTRIBUTION_PROMPT,
            query=prompt,
        )

        model_response = await self.model_resource.call(formatted_prompt)

        # Parse attributes from XML tags <1> through <10>
        attributes = []
        for i in range(1, 11):
            attr = parse_xml_tags_optional(model_response, str(i))
            if attr:
                attributes.append(attr.strip())

        return attributes

    async def _process_record(
        self,
        record: Dict[str, Any],
        record_id: int,
        output_file: aiofiles.threadpool.binary.AsyncBufferedIOBase,
        write_lock: asyncio.Lock,
        checkpoint: CheckpointManager,
    ) -> Optional[Dict[str, Any]]:
        """
        Process a single record and write to output.

        Args:
            record: Dataset record
            record_id: Unique record ID
            output_file: Async file handle for output
            write_lock: Lock for thread-safe writing
            checkpoint: Checkpoint manager

        Returns:
            Result dict or None if error
        """
        try:
            # Extract first turn from messages
            messages = record.get("messages", [])
            if not messages:
                return None

            prompt, response = self._extract_first_turn(messages)
            if not prompt:
                return None

            # Extract attributes (only uses prompt, not response)
            attributes = await self._extract_single(prompt)

            result = {
                "id": record_id,
                "prompt": prompt,
                "response": response,
                "attributes": attributes,
                "source": record.get("source", "unknown"),
            }

            # Write immediately (atomic append)
            async with write_lock:
                await output_file.write(json.dumps(result, ensure_ascii=False) + "\n")
                await output_file.flush()
                checkpoint.mark_processed(record_id)

            return result

        except Exception as e:
            print(f"Error processing record {record_id}: {e}")
            return None

    async def extract_from_dataset(
        self,
        dataset_name: str = "allenai/tulu-3-sft-mixture",
        split: str = "train",
        num_samples: Optional[int] = None,
        output_path: str = "attributes.jsonl",
        batch_size: int = 10000,
    ) -> int:
        """
        Extract attributes from a HuggingFace dataset.

        Args:
            dataset_name: HuggingFace dataset name
            split: Dataset split to use
            num_samples: Maximum samples to process (None for all)
            output_path: Output JSONL file path
            batch_size: Batch size for parallel processing

        Returns:
            Number of records processed
        """
        print(f"Loading dataset: {dataset_name}")
        dataset = load_dataset(dataset_name, split=split)

        # Limit samples if specified
        total_records = len(dataset)
        if num_samples is not None:
            total_records = min(num_samples, total_records)

        print(f"Total records to process: {total_records}")

        # Setup checkpoint
        checkpoint = CheckpointManager(output_path)
        unprocessed = checkpoint.get_unprocessed_indices(total_records)

        if not unprocessed:
            print("All records already processed!")
            return checkpoint.processed_count

        print(f"Records to process: {len(unprocessed)} (skipping {checkpoint.processed_count} already done)")

        # Open output file for appending
        write_lock = asyncio.Lock()
        async with aiofiles.open(output_path, "a") as output_file:
            # Process in batches
            processed = 0
            for batch_start in tqdm(range(0, len(unprocessed), batch_size), desc="Batches"):
                batch_indices = unprocessed[batch_start:batch_start + batch_size]

                # Create tasks for this batch
                tasks = [
                    self._process_record(
                        record=dataset[idx],
                        record_id=idx,
                        output_file=output_file,
                        write_lock=write_lock,
                        checkpoint=checkpoint,
                    )
                    for idx in batch_indices
                ]

                # Process batch
                results = await tqdm_gather(
                    tasks,
                    return_exceptions=True,
                    desc=f"Processing batch",
                )

                # Count successes
                processed += sum(1 for r in results if r is not None and not isinstance(r, Exception))

        total_processed = checkpoint.processed_count
        print(f"Extraction complete: {total_processed} records processed")
        print(f"Output saved to: {output_path}")

        return total_processed


async def extract_attributes(
    dataset_name: str = "allenai/tulu-3-sft-mixture",
    num_samples: Optional[int] = None,
    output_path: str = "attributes.jsonl",
    model: str = "anthropic:claude-sonnet-4-5-20250929",
    concurrency: int = 50,
) -> int:
    """
    Convenience function to extract attributes from a dataset.

    Args:
        dataset_name: HuggingFace dataset name
        num_samples: Maximum samples to process
        output_path: Output file path
        model: Model to use for extraction
        concurrency: Maximum concurrent API calls

    Returns:
        Number of records processed
    """
    extractor = AttributeExtractor(model=model, max_concurrency=concurrency)
    return await extractor.extract_from_dataset(
        dataset_name=dataset_name,
        num_samples=num_samples,
        output_path=output_path,
    )
