"""OpenAIBackend — power-user backend using a user-supplied OpenAI key.

Why this exists alongside the free-tier defaults: some users already
hold an OpenAI subscription (ChatGPT Plus / Team / pay-as-you-go API)
and want their existing key + favorite model used. This is opt-in
only — no server-side OpenAI key is shipped and the default backend
rotation never reaches OpenAI unless the user explicitly sets the
env var.

Required env var: ``OPENAI_API_KEY``

Optional:
  - ``OPENAI_MODEL`` — override default model
  - ``OPENAI_BASE_URL`` — pointed at a compatible endpoint
    (Azure OpenAI / OpenRouter / vLLM / etc.)

Default model: ``gpt-4o-mini`` — cheap, JSON-mode capable, fast.
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
class OpenAIBackend(LLMBackend):
    """OpenAI Chat Completions backend (also supports compatible endpoints
    via OPENAI_BASE_URL — OpenRouter, Azure OpenAI, vLLM, etc.)."""

    provider_name: str = "openai"
    default_model: str = "gpt-4o-mini"
    api_key: str | None = None
    model: str = "gpt-4o-mini"
    base_url: str | None = None

    def _get_key(self) -> str:
        return (self.api_key or os.environ.get("OPENAI_API_KEY", "")).strip()

    def _get_model(self) -> str:
        env_override = os.environ.get("OPENAI_MODEL", "").strip()
        return env_override or self.model or self.default_model

    def _get_base_url(self) -> str | None:
        explicit = self.base_url or os.environ.get("OPENAI_BASE_URL", "")
        return explicit.strip() or None

    def is_available(self) -> bool:
        return bool(self._get_key())

    def compile(self, request: LLMRequest) -> LLMResponse:
        if not self.is_available():
            raise LLMBackendError(
                "OpenAIBackend: OPENAI_API_KEY not set. The default "
                "backend rotation prefers free-tier providers; set "
                "this env var only if you want to spend your own key.",
                provider=self.provider_name,
                retriable=False,
            )

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMBackendError(
                "openai SDK not installed. Run: pip install openai",
                provider=self.provider_name,
                retriable=False,
            ) from exc

        client_kwargs: dict = {"api_key": self._get_key()}
        base = self._get_base_url()
        if base:
            client_kwargs["base_url"] = base
        client = OpenAI(**client_kwargs)
        model = self._get_model()

        t0 = time.perf_counter()
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": request.system_prompt},
                    {"role": "user", "content": request.user_message},
                ],
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            # Distinguish quota / rate-limit (retriable) from other.
            msg = str(exc).lower()
            retriable = any(k in msg for k in (
                "rate", "limit", "429", "timeout", "quota",
            ))
            raise LLMBackendError(
                f"OpenAI API call failed: {exc}",
                provider=self.provider_name,
                retriable=retriable,
            ) from exc

        latency = time.perf_counter() - t0

        choices = getattr(resp, "choices", None) or []
        if not choices:
            raise LLMBackendError(
                "Empty response from OpenAI API",
                provider=self.provider_name,
                retriable=True,
            )

        raw_text = choices[0].message.content or ""
        if not raw_text:
            raise LLMBackendError(
                "Empty content in OpenAI response",
                provider=self.provider_name,
                retriable=True,
            )

        try:
            program_json = extract_json_from_text(raw_text)
            validate_belief_program_schema(program_json)
        except ValueError as exc:
            raise LLMBackendError(
                f"OpenAI response parse / validation failed: {exc}",
                provider=self.provider_name,
                retriable=True,
            ) from exc

        usage = getattr(resp, "usage", None)
        return LLMResponse(
            program_json=program_json,
            provider=self.provider_name,
            model=model,
            latency_seconds=latency,
            prompt_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
            completion_tokens=(
                getattr(usage, "completion_tokens", 0) if usage else 0
            ),
            raw_response=raw_text,
        )
