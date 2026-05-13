"""Core utility functions for SURF."""

from __future__ import annotations

import asyncio
import re
from typing import Any, List, Tuple

from jinja2 import Template
from tqdm.asyncio import tqdm_asyncio


class ParseResponseError(Exception):
    """Raised when XML tag parsing fails."""
    pass


def render_jinja(template: str, **kwargs) -> str:
    """Render a Jinja2 template with the given keyword arguments."""
    return Template(template).render(**kwargs)


def parse_xml_tags(text: str, *tags) -> Tuple[str, ...] | str:
    """
    Extract content from XML tags in text.

    Args:
        text: The text containing XML tags
        *tags: Tag names to extract (e.g., "1", "2", "score")

    Returns:
        Single string if one tag, tuple of strings if multiple tags

    Raises:
        ParseResponseError: If any tag is not found

    Example:
        >>> parse_xml_tags("<score>42</score><reason>good</reason>", "score", "reason")
        ('42', 'good')
    """
    results = []
    for tag in tags:
        pattern = f"<{tag}>(.*?)</{tag}>"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            results.append(match.group(1).strip())
        else:
            raise ParseResponseError(f"Tag <{tag}> not found in text.")
    return tuple(results) if len(results) > 1 else results[0]


def parse_xml_tags_optional(text: str, *tags) -> Tuple[str | None, ...] | str | None:
    """
    Extract content from XML tags, returning None for missing tags.

    Same as parse_xml_tags but doesn't raise on missing tags.
    """
    results = []
    for tag in tags:
        pattern = f"<{tag}>(.*?)</{tag}>"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            results.append(match.group(1).strip())
        else:
            results.append(None)
    return tuple(results) if len(results) > 1 else results[0]


async def tqdm_gather(
    tasks: List[Any],
    return_exceptions: bool = False,
    notebook: bool = False,
    on_progress: callable = None,
    **kwargs
) -> List[Any]:
    """
    Gather async tasks with a progress bar.

    Args:
        tasks: List of coroutines or tasks
        return_exceptions: If True, return exceptions instead of raising
        notebook: If True, use notebook-friendly progress bar
        on_progress: Optional callback(completed, total) called on each completion
        **kwargs: Additional arguments passed to tqdm

    Returns:
        List of results in the same order as input tasks
    """
    total = len(tasks)

    if notebook or on_progress is not None:
        # Use as_completed approach for progress callback support
        from tqdm.notebook import tqdm as notebook_tqdm

        async def wrap_with_index(index: int, coro):
            try:
                result = await coro
                return index, result, None
            except Exception as e:
                if return_exceptions:
                    return index, e, None
                raise

        indexed_tasks = [
            asyncio.create_task(wrap_with_index(i, t))
            for i, t in enumerate(tasks)
        ]
        results = [None] * total

        if notebook:
            pbar = notebook_tqdm(total=total, **kwargs)
        else:
            from tqdm import tqdm
            pbar = tqdm(total=total, **kwargs) if not kwargs.get("disable") else None

        completed = 0
        for completed_task in asyncio.as_completed(indexed_tasks):
            index, result, _ = await completed_task
            results[index] = result
            completed += 1
            if pbar:
                pbar.update(1)
            if on_progress:
                on_progress(completed, total)

        if pbar:
            pbar.close()

        return results
    else:
        if not return_exceptions:
            return await tqdm_asyncio.gather(*tasks, **kwargs)

        async def wrap(coro):
            try:
                return await coro
            except Exception as e:
                return e

        return await tqdm_asyncio.gather(*[wrap(t) for t in tasks], **kwargs)
