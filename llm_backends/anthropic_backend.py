"""AnthropicBackend — Claude via Anthropic SDK (user-supplied key only).

Per project strategy: this backend is NOT used as a server-side default.
It's available for power users who bring their own ANTHROPIC_API_KEY
(via UI input or env var). The default free-tier path uses
GeminiBackend / GroqBackend.

Required env var: `ANTHROPIC_API_KEY` (or passed via constructor)
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

from .base import (
    LLMBackend,
    LLMBackendError,
    LLMRequest,
    LLMResponse,
    extract_json_from_text,
    validate_belief_program_schema,
)


@dataclass(frozen=True, slots=True)
class AnthropicBackend(LLMBackend):
    """Anthropic Claude backend (user-supplied API key).

    Args:
      api_key: explicit override (else reads from ANTHROPIC_API_KEY env)
      model: Claude model identifier (default `claude-opus-4-5`)
    """

    provider_name: str = "anthropic"
    default_model: str = "claude-opus-4-5"
    api_key: str | None = None
    model: str = "claude-opus-4-5"

    def is_available(self) -> bool:
        key = self.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        return bool(key.strip())

    def compile(self, request: LLMRequest) -> LLMResponse:
        if not self.is_available():
            raise LLMBackendError(
                "AnthropicBackend: ANTHROPIC_API_KEY not set (either pass "
                "api_key= or set env var). Use a different backend for the "
                "default free path.",
                provider=self.provider_name,
                retriable=False,
            )

        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise LLMBackendError(
                "anthropic SDK not installed. Run: pip install anthropic",
                provider=self.provider_name,
                retriable=False,
            ) from exc

        api_key = self.api_key or os.environ["ANTHROPIC_API_KEY"]
        client = Anthropic(api_key=api_key)

        t0 = time.perf_counter()
        try:
            resp = client.messages.create(
                model=self.model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                system=request.system_prompt,
                messages=[{"role": "user", "content": request.user_message}],
            )
        except Exception as exc:
            raise LLMBackendError(
                f"Anthropic API call failed: {exc}",
                provider=self.provider_name,
                retriable=True,
            ) from exc

        latency = time.perf_counter() - t0

        if not resp.content:
            raise LLMBackendError(
                "Empty response from Anthropic API",
                provider=self.provider_name,
                retriable=True,
            )

        raw_text = resp.content[0].text

        try:
            program_json = extract_json_from_text(raw_text)
            validate_belief_program_schema(program_json)
        except ValueError as exc:
            raise LLMBackendError(
                f"Anthropic response parse / validation failed: {exc}",
                provider=self.provider_name,
                retriable=True,
            ) from exc

        usage = getattr(resp, "usage", None)
        return LLMResponse(
            program_json=program_json,
            provider=self.provider_name,
            model=self.model,
            latency_seconds=latency,
            prompt_tokens=getattr(usage, "input_tokens", 0) if usage else 0,
            completion_tokens=getattr(usage, "output_tokens", 0) if usage else 0,
            raw_response=raw_text,
        )
