"""GeminiBackend — Google Gemini Flash via Google AI Studio API.

This is the PRIMARY default free-tier backend per project strategy.

Why Gemini Flash:
  - Free tier exists at Google AI Studio (1500 req/day for Gemini 2.0 Flash)
  - No credit card required to start
  - Fast + decent quality for structured-output tasks
  - Doesn't require Anthropic dependency

Required env var: `GEMINI_API_KEY` (server-side; set by deployment owner)
  Optional alias: `GOOGLE_API_KEY`

Get a key:
  https://aistudio.google.com/app/apikey → Create API key
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
class GeminiBackend(LLMBackend):
    """Google Gemini Flash via Google AI Studio.

    Args:
      api_key: explicit override (else reads GEMINI_API_KEY or GOOGLE_API_KEY)
      model: Gemini model identifier (default `gemini-2.0-flash-exp`)
    """

    provider_name: str = "gemini"
    default_model: str = "gemini-2.0-flash-exp"
    api_key: str | None = None
    model: str = "gemini-2.0-flash-exp"

    def _get_key(self) -> str:
        key = (
            self.api_key
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
            or ""
        )
        return key.strip()

    def is_available(self) -> bool:
        return bool(self._get_key())

    def compile(self, request: LLMRequest) -> LLMResponse:
        if not self.is_available():
            raise LLMBackendError(
                "GeminiBackend: GEMINI_API_KEY / GOOGLE_API_KEY not set. "
                "Get one free at https://aistudio.google.com/app/apikey",
                provider=self.provider_name,
                retriable=False,
            )

        try:
            # google-genai is the newer unified Python SDK
            from google import genai
        except ImportError as exc:
            raise LLMBackendError(
                "google-genai SDK not installed. Run: pip install google-genai",
                provider=self.provider_name,
                retriable=False,
            ) from exc

        api_key = self._get_key()
        client = genai.Client(api_key=api_key)

        # Gemini concatenates system + user; we put system_prompt as
        # `system_instruction` config and user message as content.
        t0 = time.perf_counter()
        try:
            resp = client.models.generate_content(
                model=self.model,
                contents=request.user_message,
                config={
                    "system_instruction": request.system_prompt,
                    "max_output_tokens": request.max_tokens,
                    "temperature": request.temperature,
                    "response_mime_type": "application/json",
                },
            )
        except Exception as exc:
            raise LLMBackendError(
                f"Gemini API call failed: {exc}",
                provider=self.provider_name,
                retriable=True,
            ) from exc

        latency = time.perf_counter() - t0

        raw_text = resp.text or ""
        if not raw_text:
            raise LLMBackendError(
                "Empty response from Gemini API",
                provider=self.provider_name,
                retriable=True,
            )

        try:
            program_json = extract_json_from_text(raw_text)
            validate_belief_program_schema(program_json)
        except ValueError as exc:
            raise LLMBackendError(
                f"Gemini response parse / validation failed: {exc}",
                provider=self.provider_name,
                retriable=True,
            ) from exc

        # Gemini usage metadata
        usage = getattr(resp, "usage_metadata", None)
        return LLMResponse(
            program_json=program_json,
            provider=self.provider_name,
            model=self.model,
            latency_seconds=latency,
            prompt_tokens=getattr(usage, "prompt_token_count", 0) if usage else 0,
            completion_tokens=getattr(usage, "candidates_token_count", 0) if usage else 0,
            raw_response=raw_text,
        )
