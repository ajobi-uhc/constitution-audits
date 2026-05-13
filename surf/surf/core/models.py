"""Model resources for SURF - supports Anthropic, OpenRouter, vLLM, and custom endpoints."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import anthropic
import openai
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


@dataclass(frozen=True)
class ProviderModel:
    """Encapsulates model name and provider information."""

    provider: str  # "anthropic", "openrouter", "vllm", or URL like "http://localhost:8000/v1"
    model: str
    api_key: Optional[str] = None

    def __post_init__(self):
        # Set default API keys based on provider
        if self.api_key is None:
            object.__setattr__(self, 'api_key', self._get_default_api_key())

    def _get_default_api_key(self) -> Optional[str]:
        if self.provider == "anthropic":
            return os.getenv("ANTHROPIC_API_KEY")
        elif self.provider == "openrouter":
            return os.getenv("OPENROUTER_API_KEY")
        return os.getenv("MODEL_API_KEY", "dummy")


@dataclass
class QueryParams:
    """Parameters for model queries."""

    max_tokens: int = 16384
    temperature: float = 1.0
    stop: Optional[Union[str, List[str]]] = None
    thinking_budget: Optional[int] = None  # For Anthropic extended thinking


def parse_model_string(model_str: str) -> ProviderModel:
    """
    Parse a model string into a ProviderModel.

    Formats:
        - "anthropic:claude-sonnet-4-5-20250929" -> Anthropic API
        - "openrouter:meta-llama/llama-3.1-70b-instruct" -> OpenRouter API
        - "vllm:meta-llama/Llama-3.1-70B-Instruct" -> Auto-managed vLLM server
        - "http://localhost:8000/v1:model-name" -> Custom OpenAI-compatible endpoint
        - "claude-sonnet-4-5-20250929" -> Defaults to Anthropic

    Returns:
        ProviderModel instance
    """
    if ":" not in model_str:
        # Default to anthropic
        return ProviderModel(provider="anthropic", model=model_str)

    # Check for URL-style provider (http:// or https://)
    if model_str.startswith("http://") or model_str.startswith("https://"):
        # Format: http://host:port/v1:model-name
        # Find the last colon that's not part of the URL
        parts = model_str.rsplit(":", 1)
        if len(parts) == 2 and not parts[1].startswith("//"):
            return ProviderModel(provider=parts[0], model=parts[1])
        raise ValueError(f"Invalid URL model format: {model_str}. Expected http://host:port/v1:model-name")

    # Standard format: provider:model
    provider, model = model_str.split(":", 1)
    return ProviderModel(provider=provider, model=model)


def _get_anthropic_client() -> anthropic.AsyncAnthropic:
    """Get an async Anthropic client."""
    return anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def _get_openai_client(base_url: str, api_key: str, timeout: float = 180.0) -> openai.AsyncOpenAI:
    """Get an async OpenAI-compatible client."""
    return openai.AsyncOpenAI(
        base_url=base_url,
        api_key=api_key,
        timeout=timeout,
    )


# Retry decorator for API calls
_retry_decorator = retry(
    retry=retry_if_exception_type((
        anthropic.RateLimitError,
        anthropic.APIConnectionError,
        openai.RateLimitError,
        openai.APIConnectionError,
    )),
    wait=wait_exponential(multiplier=1, min=1, max=60),
    stop=stop_after_attempt(5),
)


@_retry_decorator
async def _call_anthropic(
    model: str,
    messages: List[Dict[str, Any]],
    max_tokens: int = 16384,
    temperature: float = 1.0,
    stop: Optional[List[str]] = None,
    thinking_budget: Optional[int] = None,
) -> Tuple[str, Optional[str]]:
    """Call Anthropic API and return (response_text, thinking_text)."""
    client = _get_anthropic_client()

    kwargs = {}
    if stop:
        kwargs["stop_sequences"] = stop
    if thinking_budget:
        kwargs["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}
    elif temperature is not None:
        kwargs["temperature"] = temperature

    response = await client.messages.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        **kwargs,
    )

    text_parts = []
    thinking_parts = []
    for block in response.content:
        if getattr(block, "type", None) == "thinking":
            thinking = getattr(block, "thinking", None)
            if thinking:
                thinking_parts.append(thinking)
        elif hasattr(block, "text"):
            text_parts.append(block.text)

    return "".join(text_parts), "".join(thinking_parts) if thinking_parts else None


@_retry_decorator
async def _call_openai_compatible(
    base_url: str,
    api_key: str,
    model: str,
    messages: List[Dict[str, Any]],
    max_tokens: int = 16384,
    temperature: float = 1.0,
    stop: Optional[List[str]] = None,
) -> str:
    """Call OpenAI-compatible API and return response text."""
    client = _get_openai_client(base_url, api_key)

    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        stop=stop,
    )

    return response.choices[0].message.content or ""


@dataclass
class ModelResource:
    """
    A model resource with concurrency control.

    Supports Anthropic, OpenRouter, vLLM, and custom OpenAI-compatible endpoints.
    """

    provider_model: ProviderModel
    query_params: QueryParams = field(default_factory=QueryParams)
    max_concurrency: int = 50
    _vllm_manager: Any = field(default=None, repr=False)  # VLLMServerManager reference

    def __post_init__(self):
        self._semaphore = asyncio.Semaphore(self.max_concurrency)
        self._vllm_url: Optional[str] = None
        # Reuse clients to avoid file descriptor exhaustion
        self._anthropic_client: Optional[anthropic.AsyncAnthropic] = None
        self._openai_clients: Dict[str, openai.AsyncOpenAI] = {}

    def _get_anthropic_client(self) -> anthropic.AsyncAnthropic:
        """Get or create a reusable Anthropic client."""
        if self._anthropic_client is None:
            self._anthropic_client = anthropic.AsyncAnthropic(
                api_key=os.getenv("ANTHROPIC_API_KEY")
            )
        return self._anthropic_client

    def _get_openai_client(self, base_url: str, api_key: str) -> openai.AsyncOpenAI:
        """Get or create a reusable OpenAI-compatible client."""
        if base_url not in self._openai_clients:
            self._openai_clients[base_url] = openai.AsyncOpenAI(
                base_url=base_url,
                api_key=api_key,
                timeout=180.0,
            )
        return self._openai_clients[base_url]

    @_retry_decorator
    async def _call_anthropic_impl(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int = 16384,
        temperature: float = 1.0,
        stop: Optional[List[str]] = None,
        thinking_budget: Optional[int] = None,
    ) -> Tuple[str, Optional[str]]:
        """Call Anthropic API using shared client."""
        client = self._get_anthropic_client()

        kwargs = {}
        if stop:
            kwargs["stop_sequences"] = stop
        if thinking_budget:
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}
        elif temperature is not None:
            kwargs["temperature"] = temperature

        response = await client.messages.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            **kwargs,
        )

        text_parts = []
        thinking_parts = []
        for block in response.content:
            if getattr(block, "type", None) == "thinking":
                thinking = getattr(block, "thinking", None)
                if thinking:
                    thinking_parts.append(thinking)
            elif hasattr(block, "text"):
                text_parts.append(block.text)

        return "".join(text_parts), "".join(thinking_parts) if thinking_parts else None

    @_retry_decorator
    async def _call_openai_impl(
        self,
        base_url: str,
        api_key: str,
        messages: List[Dict[str, Any]],
        max_tokens: int = 16384,
        temperature: float = 1.0,
        stop: Optional[List[str]] = None,
    ) -> str:
        """Call OpenAI-compatible API using shared client."""
        client = self._get_openai_client(base_url, api_key)

        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop,
        )

        if not response.choices:
            raise ValueError("API returned empty choices - possible rate limit or error")
        return response.choices[0].message.content or ""

    @classmethod
    def from_string(
        cls,
        model_str: str,
        max_concurrency: int = 50,
        **query_params
    ) -> "ModelResource":
        """Create a ModelResource from a model string."""
        provider_model = parse_model_string(model_str)
        return cls(
            provider_model=provider_model,
            query_params=QueryParams(**query_params),
            max_concurrency=max_concurrency,
        )

    @property
    def provider(self) -> str:
        return self.provider_model.provider

    @property
    def model(self) -> str:
        return self.provider_model.model

    @property
    def is_vllm(self) -> bool:
        return self.provider == "vllm"

    async def _ensure_vllm_server(self) -> str:
        """Ensure vLLM server is running and return its URL."""
        if self._vllm_url is not None:
            return self._vllm_url

        if self._vllm_manager is None:
            from surf.core.vllm_server import VLLMServerManager
            self._vllm_manager = VLLMServerManager()

        self._vllm_url = await self._vllm_manager.get_or_start(self.model)
        return self._vllm_url

    async def call(
        self,
        query: str,
        system: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Call the model with a query.

        Args:
            query: The user query
            system: Optional system prompt
            **kwargs: Override query_params

        Returns:
            Model response text
        """
        # Merge query params with overrides
        params = QueryParams(
            max_tokens=kwargs.get("max_tokens", self.query_params.max_tokens),
            temperature=kwargs.get("temperature", self.query_params.temperature),
            stop=kwargs.get("stop", self.query_params.stop),
            thinking_budget=kwargs.get("thinking_budget", self.query_params.thinking_budget),
        )

        # Build messages
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": query})

        # Convert stop to list
        stop_list = None
        if params.stop:
            stop_list = [params.stop] if isinstance(params.stop, str) else params.stop

        async with self._semaphore:
            if self.provider == "anthropic":
                # Anthropic doesn't use system in messages, use it directly
                if system:
                    messages = [{"role": "user", "content": f"{system}\n\n{query}"}]
                else:
                    messages = [{"role": "user", "content": query}]

                text, _ = await self._call_anthropic_impl(
                    messages=messages,
                    max_tokens=params.max_tokens,
                    temperature=params.temperature,
                    stop=stop_list,
                    thinking_budget=params.thinking_budget,
                )
                return text

            elif self.provider == "openrouter":
                return await self._call_openai_impl(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=self.provider_model.api_key or os.getenv("OPENROUTER_API_KEY", ""),
                    messages=messages,
                    max_tokens=params.max_tokens,
                    temperature=params.temperature,
                    stop=stop_list,
                )

            elif self.provider == "vllm":
                url = await self._ensure_vllm_server()
                return await self._call_openai_impl(
                    base_url=url,
                    api_key="dummy",
                    messages=messages,
                    max_tokens=params.max_tokens,
                    temperature=params.temperature,
                    stop=stop_list,
                )

            else:
                # Custom URL endpoint
                return await self._call_openai_impl(
                    base_url=self.provider,
                    api_key=self.provider_model.api_key or "dummy",
                    messages=messages,
                    max_tokens=params.max_tokens,
                    temperature=params.temperature,
                    stop=stop_list,
                )

    async def call_with_thinking(
        self,
        query: str,
        thinking_budget: int = 10000,
        **kwargs
    ) -> Tuple[str, str]:
        """
        Call with extended thinking (Anthropic only).

        Returns:
            Tuple of (response_text, thinking_text)
        """
        if self.provider != "anthropic":
            raise ValueError("Extended thinking is only supported for Anthropic models")

        messages = [{"role": "user", "content": query}]
        params = QueryParams(
            max_tokens=kwargs.get("max_tokens", self.query_params.max_tokens),
            temperature=1.0,  # Extended thinking requires temperature=1
            stop=kwargs.get("stop", self.query_params.stop),
            thinking_budget=thinking_budget,
        )

        stop_list = None
        if params.stop:
            stop_list = [params.stop] if isinstance(params.stop, str) else params.stop

        async with self._semaphore:
            text, thinking = await self._call_anthropic_impl(
                messages=messages,
                max_tokens=params.max_tokens,
                temperature=params.temperature,
                stop=stop_list,
                thinking_budget=thinking_budget,
            )
            return text, thinking or ""

    async def shutdown(self):
        """Shutdown any managed resources (clients, vLLM servers)."""
        # Close Anthropic client
        if self._anthropic_client is not None:
            await self._anthropic_client.close()
            self._anthropic_client = None

        # Close OpenAI clients
        for client in self._openai_clients.values():
            await client.close()
        self._openai_clients.clear()

        # Shutdown vLLM
        if self._vllm_manager is not None:
            await self._vllm_manager.shutdown_all()
