"""GroqBackend — Llama 3.3 via Groq Cloud free tier.

Secondary free-tier fallback. Groq is famously fast (~300 tok/s on
70B models thanks to LPU hardware) and has a generous free tier
(14,400 req/day on llama-3.3-70b-versatile as of 2026).

Why Groq:
  - Free tier doesn't require credit card
  - Open-source Llama models (Apache 2.0 license; no vendor lock)
  - 5-10× faster than other free tiers — improves UX

Required env var: `GROQ_API_KEY`

Get a key:
  https://console.groq.com/keys → Create API key
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

from .base import (
    LLMBackend,
    LLMBackendError,
    LLMRequest,
    LLMResponse,
    extract_json_from_text,
    validate_belief_program_schema,
)


@dataclass(frozen=True, slots=True)
class GroqBackend(LLMBackend):
    """Groq Cloud Llama backend.

    Args:
      api_key: explicit override (else reads GROQ_API_KEY)
      model: Groq model identifier (default `llama-3.3-70b-versatile`)
    """

    provider_name: str = "groq"
    default_model: str = "llama-3.3-70b-versatile"
    api_key: str | None = None
    model: str = "llama-3.3-70b-versatile"

    def _get_key(self) -> str:
        return (self.api_key or os.environ.get("GROQ_API_KEY", "")).strip()

    def is_available(self) -> bool:
        return bool(self._get_key())

    def compile(self, request: LLMRequest) -> LLMResponse:
        if not self.is_available():
            raise LLMBackendError(
                "GroqBackend: GROQ_API_KEY not set. Get one free at "
                "https://console.groq.com/keys",
                provider=self.provider_name,
                retriable=False,
            )

        try:
            from groq import Groq
        except ImportError as exc:
            raise LLMBackendError(
                "groq SDK not installed. Run: pip install groq",
                provider=self.provider_name,
                retriable=False,
            ) from exc

        api_key = self._get_key()
        client = Groq(api_key=api_key)

        t0 = time.perf_counter()
        try:
            resp = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": request.system_prompt},
                    {"role": "user", "content": request.user_message},
                ],
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            raise LLMBackendError(
                f"Groq API call failed: {exc}",
                provider=self.provider_name,
                retriable=True,
            ) from exc

        latency = time.perf_counter() - t0

        choices = getattr(resp, "choices", None) or []
        if not choices:
            raise LLMBackendError(
                "Empty response from Groq API",
                provider=self.provider_name,
                retriable=True,
            )

        raw_text = choices[0].message.content or ""
        if not raw_text:
            raise LLMBackendError(
                "Empty content in Groq response",
                provider=self.provider_name,
                retriable=True,
            )

        try:
            program_json = extract_json_from_text(raw_text)
            validate_belief_program_schema(program_json)
        except ValueError as exc:
            raise LLMBackendError(
                f"Groq response parse / validation failed: {exc}",
                provider=self.provider_name,
                retriable=True,
            ) from exc

        usage = getattr(resp, "usage", None)
        return LLMResponse(
            program_json=program_json,
            provider=self.provider_name,
            model=self.model,
            latency_seconds=latency,
            prompt_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
            raw_response=raw_text,
        )
