"""LLM backend registry + factory + default selection logic.

Public API:
  - get_backend(name) → LLMBackend instance for the named provider
  - get_default_backend() → server-side default; picks first available
    from priority chain (free tier first, paid last)
  - RotatingBackend → wraps multiple backends with automatic fallback

Usage:
  from llm_backends import get_default_backend, RotatingBackend

  # Server-side default (free tier rotation):
  backend = get_default_backend()
  response = backend.compile(request)

  # Explicit selection (user brings own key):
  from llm_backends import get_backend
  backend = get_backend("anthropic", api_key=user_key)

  # Custom rotation chain:
  backend = RotatingBackend([
      GeminiBackend(),
      GroqBackend(),
      MockBackend(),  # always-succeeds last-resort
  ])
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any

from .base import (
    LLMBackend,
    LLMBackendError,
    LLMRequest,
    LLMResponse,
    extract_json_from_text,
    validate_belief_program_schema,
)
from .anthropic_backend import AnthropicBackend
from .cloudflare_backend import CloudflareWorkersAIBackend
from .gemini_backend import GeminiBackend
from .groq_backend import GroqBackend
from .mock_backend import MockBackend
from .ollama_backend import OllamaBackend
from .ollama_vision_backend import (
    OllamaVisionBackend,
    OllamaVisionRequest,
)
from .openai_backend import OpenAIBackend
from .quota import (
    DEFAULT_POLICIES,
    QuotaExhaustedError,
    QuotaGuardedBackend,
    QuotaPolicy,
    QuotaStore,
    with_quota_guard,
)


# Registry of available backends. Add new providers here.
_REGISTRY: dict[str, type[LLMBackend]] = {
    "mock": MockBackend,
    "anthropic": AnthropicBackend,
    "gemini": GeminiBackend,
    "groq": GroqBackend,
    "cloudflare_workers_ai": CloudflareWorkersAIBackend,
    "openai": OpenAIBackend,
    "ollama": OllamaBackend,
}


# Server-side default priority chain.
# First available (i.e. has API key configured / probe succeeds) wins.
# Order: local (ollama) → free tier (gemini/groq/cloudflare) →
# paid user-key (openai/anthropic) → mock last-resort.
DEFAULT_PRIORITY_CHAIN = (
    "ollama",                # zero cost, fully private, fast on local hw
    "gemini",                # free tier — Google AI Studio
    "groq",                  # free tier — Groq Cloud
    "cloudflare_workers_ai", # free tier — Cloudflare Workers AI
    "openai",                # user-supplied paid key
    "anthropic",             # user-supplied paid key
    "mock",                  # last-resort always-succeeds stub
)


def get_backend(name: str, **kwargs: Any) -> LLMBackend:
    """Construct a backend by name with optional kwargs.

    Raises KeyError if name is unknown.
    """
    if name not in _REGISTRY:
        raise KeyError(
            f"Unknown LLM backend '{name}'. Available: {list(_REGISTRY.keys())}"
        )
    return _REGISTRY[name](**kwargs)


def list_backends() -> list[str]:
    """All registered backend names."""
    return list(_REGISTRY.keys())


def get_default_backend(*, force_mock: bool | None = None) -> LLMBackend:
    """Server-side default — automatic selection from priority chain.

    Selection logic:
      1. If OMYTEA_CONSOLE_MOCK=1 OR force_mock=True → MockBackend
      2. If OMYTEA_LLM_BACKEND env var is set → use that backend
      3. Otherwise iterate DEFAULT_PRIORITY_CHAIN, return first available

    Returns:
      A RotatingBackend if 2+ providers are available (for resilience),
      else the single available backend.
    """
    if force_mock is None:
        force_mock = os.environ.get("OMYTEA_CONSOLE_MOCK") == "1"
    if force_mock:
        return MockBackend()

    explicit = os.environ.get("OMYTEA_LLM_BACKEND", "").strip()
    if explicit and explicit in _REGISTRY:
        b = get_backend(explicit)
        if not b.is_available() and explicit != "mock":
            # User explicitly chose a backend but it's not configured —
            # fail loud rather than silently falling back
            raise LLMBackendError(
                f"OMYTEA_LLM_BACKEND='{explicit}' but that backend is not "
                f"available (missing API key?). Set the required env var "
                f"or unset OMYTEA_LLM_BACKEND.",
                provider=explicit,
                retriable=False,
            )
        return b

    # Auto-discover: collect all available from priority chain
    chain: list[LLMBackend] = []
    for name in DEFAULT_PRIORITY_CHAIN:
        b = get_backend(name)
        if b.is_available():
            chain.append(b)

    if not chain:
        # Nothing configured. Mock so callers can at least run.
        return MockBackend()
    if len(chain) == 1:
        return chain[0]
    return RotatingBackend(backends=tuple(chain))


@dataclass(frozen=True, slots=True)
class RotatingBackend(LLMBackend):
    """Wraps multiple backends with sequential fallback on failure.

    Tries each backend in order. If a backend raises LLMBackendError
    with retriable=True (rate limit / quota / timeout / parse failure),
    falls through to the next backend. retriable=False errors propagate
    immediately (e.g. missing dependency).

    Construct via:
        RotatingBackend(backends=(GeminiBackend(), GroqBackend(), MockBackend()))
    """

    provider_name: str = "rotating"
    default_model: str = "auto"
    backends: tuple[LLMBackend, ...] = field(default_factory=tuple)

    def compile(self, request: LLMRequest) -> LLMResponse:
        if not self.backends:
            raise LLMBackendError(
                "RotatingBackend has no backends configured",
                provider=self.provider_name,
                retriable=False,
            )
        last_error: LLMBackendError | None = None
        for b in self.backends:
            if not b.is_available():
                continue
            try:
                resp = b.compile(request)
                # Annotate response with rotating-provider lineage for audit
                return LLMResponse(
                    program_json=resp.program_json,
                    provider=f"rotating::{resp.provider}",
                    model=resp.model,
                    latency_seconds=resp.latency_seconds,
                    prompt_tokens=resp.prompt_tokens,
                    completion_tokens=resp.completion_tokens,
                    raw_response=resp.raw_response,
                )
            except LLMBackendError as exc:
                last_error = exc
                if not exc.retriable:
                    # Non-retriable: re-raise immediately
                    raise
                # Retriable: try next backend
                continue
        # Exhausted all backends
        if last_error is not None:
            raise LLMBackendError(
                f"All rotating backends failed. Last error from "
                f"{last_error.provider}: {last_error}",
                provider="rotating",
                retriable=False,
            ) from last_error
        raise LLMBackendError(
            "No available backends in rotation (all returned is_available=False)",
            provider="rotating",
            retriable=False,
        )

    def is_available(self) -> bool:
        return any(b.is_available() for b in self.backends)


__all__ = [
    "LLMBackend",
    "LLMBackendError",
    "LLMRequest",
    "LLMResponse",
    "MockBackend",
    "AnthropicBackend",
    "GeminiBackend",
    "GroqBackend",
    "CloudflareWorkersAIBackend",
    "OpenAIBackend",
    "OllamaBackend",
    "OllamaVisionBackend",
    "OllamaVisionRequest",
    "RotatingBackend",
    "QuotaExhaustedError",
    "QuotaGuardedBackend",
    "QuotaPolicy",
    "QuotaStore",
    "DEFAULT_POLICIES",
    "with_quota_guard",
    "extract_json_from_text",
    "validate_belief_program_schema",
    "get_backend",
    "get_default_backend",
    "list_backends",
    "DEFAULT_PRIORITY_CHAIN",
]
