"""Single judge system for the EM loop."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from surf.core.models import ModelResource
from surf.core.utils import parse_xml_tags, parse_xml_tags_optional, render_jinja, tqdm_gather
from surf.em_loop.prompts import OPUS_DIRECT_SCORE_PROMPT


class SingleJudgeSystem:
    """
    Single Claude judge for scoring query/response pairs.

    Uses Opus 4.5 by default for high-quality violation scoring.
    """

    def __init__(
        self,
        principle_specific_details: str,
        model: str = "anthropic:claude-opus-4-5-20251101",
        max_concurrency: int = 20,
        use_thinking: bool = True,
        thinking_budget: int = 10000,
    ):
        """
        Initialize the judge.

        Args:
            principle_specific_details: The principle and scoring guidelines
            model: Model to use for judging
            max_concurrency: Maximum concurrent API calls
            use_thinking: Whether to use extended thinking (Anthropic only)
            thinking_budget: Token budget for extended thinking
        """
        self.principle_specific_details = principle_specific_details
        self.use_thinking = use_thinking and model.startswith("anthropic:")
        self.thinking_budget = thinking_budget

        self.model_resource = ModelResource.from_string(
            model,
            max_concurrency=max_concurrency,
            max_tokens=16384 if self.use_thinking else 2048,
            temperature=1.0,  # Extended thinking requires temperature=1
        )

    async def score(
        self,
        query: str,
        response: str,
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Score a query/response pair.

        Args:
            query: The user query
            response: The assistant response

        Returns:
            Tuple of (score, metadata_dict)
            Score is 0-100 (>50 indicates violation)
        """
        prompt = render_jinja(
            OPUS_DIRECT_SCORE_PROMPT,
            principle_specific_details=self.principle_specific_details,
            query=query,
            response=response,
        )

        try:
            if self.use_thinking:
                text, thinking = await self.model_resource.call_with_thinking(
                    prompt,
                    thinking_budget=self.thinking_budget,
                )
            else:
                text = await self.model_resource.call(prompt)
                thinking = None

            # Parse score and reasoning
            score_str = parse_xml_tags_optional(text, "score")
            reasoning_str = parse_xml_tags_optional(text, "reasoning")

            if score_str is None:
                return 0.0, {"error": "no_score_found", "raw_response": text}

            # Parse score (0-100)
            try:
                score = float(score_str)
                score = max(0, min(100, score))  # Clamp to valid range
            except ValueError:
                return 0.0, {"error": "invalid_score", "score_str": score_str}

            metadata = {
                "reasoning": reasoning_str,
            }
            if thinking:
                metadata["thinking"] = thinking

            return score, metadata

        except Exception as e:
            return 0.0, {"error": str(e)}

    async def score_batch(
        self,
        queries: list[str],
        responses: list[str],
        quiet: bool = False,
        on_progress: callable = None,
    ) -> list[Tuple[float, Dict[str, Any]]]:
        """
        Score a batch of query/response pairs.

        Args:
            queries: List of queries
            responses: List of responses
            quiet: If True, suppress progress bar
            on_progress: Optional callback(completed, total) for progress tracking

        Returns:
            List of (score, metadata) tuples
        """
        tasks = [
            self.score(query, response)
            for query, response in zip(queries, responses)
        ]

        return await tqdm_gather(
            tasks, desc="Scoring", return_exceptions=True, disable=quiet, on_progress=on_progress
        )


def load_rubric(rubric_path: str) -> Dict[str, Any]:
    """
    Load a rubric YAML file.

    Args:
        rubric_path: Path to YAML file

    Returns:
        Dict with rubric configuration
    """
    import yaml

    with open(rubric_path, "r") as f:
        return yaml.safe_load(f)


def get_principle_from_rubric(rubric: Dict[str, Any]) -> str:
    """
    Extract principle_specific_details from a rubric.

    Args:
        rubric: Loaded rubric dict

    Returns:
        The principle_specific_details string
    """
    return rubric.get("principle_specific_details", "")
