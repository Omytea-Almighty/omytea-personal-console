"""CloudflareWorkersAIBackend — Workers AI (Llama / Mistral / DeepSeek).

Tertiary free-tier option for users on Cloudflare's stack. Workers AI
exposes a small but growing catalog of open-source models behind a
single endpoint with a generous free daily allowance (10,000
neurons/day at time of writing).

Required env vars:
  - ``CLOUDFLARE_API_TOKEN`` — token with Workers AI Read+Run scope
  - ``CLOUDFLARE_ACCOUNT_ID`` — your Cloudflare account UUID

Optional:
  - ``CLOUDFLARE_AI_MODEL`` — override default model

Get credentials:
  https://dash.cloudflare.com/profile/api-tokens (token)
  https://dash.cloudflare.com/ → Sidebar → Account ID
"""

from __future__ import annotations

import json
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
class CloudflareWorkersAIBackend(LLMBackend):
    """Cloudflare Workers AI HTTP backend.

    Args:
      api_token: explicit override (else CLOUDFLARE_API_TOKEN env var)
      account_id: explicit override (else CLOUDFLARE_ACCOUNT_ID env var)
      model: model identifier; default `@cf/meta/llama-3.1-8b-instruct`
        — the small Llama 3.1 8B variant which is free-tier friendly.
        Override via env or constructor for larger models.
      request_timeout_seconds: HTTP timeout for the API call.
    """

    provider_name: str = "cloudflare_workers_ai"
    default_model: str = "@cf/meta/llama-3.1-8b-instruct"
    api_token: str | None = None
    account_id: str | None = None
    model: str = "@cf/meta/llama-3.1-8b-instruct"
    request_timeout_seconds: float = 60.0

    def _get_token(self) -> str:
        return (
            self.api_token
            or os.environ.get("CLOUDFLARE_API_TOKEN", "")
        ).strip()

    def _get_account_id(self) -> str:
        return (
            self.account_id
            or os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
        ).strip()

    def _get_model(self) -> str:
        env_override = os.environ.get("CLOUDFLARE_AI_MODEL", "").strip()
        return env_override or self.model or self.default_model

    def is_available(self) -> bool:
        return bool(self._get_token() and self._get_account_id())

    def compile(self, request: LLMRequest) -> LLMResponse:
        if not self.is_available():
            raise LLMBackendError(
                "CloudflareWorkersAIBackend: CLOUDFLARE_API_TOKEN and "
                "CLOUDFLARE_ACCOUNT_ID must both be set. See "
                "https://developers.cloudflare.com/workers-ai/",
                provider=self.provider_name,
                retriable=False,
            )

        try:
            import requests  # stdlib-adjacent; almost-always available
        except ImportError as exc:
            raise LLMBackendError(
                "requests library not installed. Run: pip install requests",
                provider=self.provider_name,
                retriable=False,
            ) from exc

        token = self._get_token()
        account_id = self._get_account_id()
        model = self._get_model()
        url = (
            f"https://api.cloudflare.com/client/v4/accounts/"
            f"{account_id}/ai/run/{model}"
        )
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_message},
            ],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }

        t0 = time.perf_counter()
        try:
            resp = requests.post(
                url, headers=headers, json=payload,
                timeout=self.request_timeout_seconds,
            )
        except Exception as exc:
            raise LLMBackendError(
                f"Cloudflare Workers AI HTTP call failed: {exc}",
                provider=self.provider_name,
                retriable=True,
            ) from exc
        latency = time.perf_counter() - t0

        if resp.status_code == 401 or resp.status_code == 403:
            raise LLMBackendError(
                f"Cloudflare auth failed (status {resp.status_code}). "
                f"Check CLOUDFLARE_API_TOKEN scopes (need Workers AI Run).",
                provider=self.provider_name,
                retriable=False,
            )
        if resp.status_code == 429:
            raise LLMBackendError(
                "Cloudflare Workers AI rate-limited (429). Daily neuron "
                "allowance may be exhausted.",
                provider=self.provider_name,
                retriable=True,
            )
        if resp.status_code >= 400:
            raise LLMBackendError(
                f"Cloudflare Workers AI HTTP {resp.status_code}: "
                f"{resp.text[:200]}",
                provider=self.provider_name,
                retriable=True,
            )

        try:
            data = resp.json()
        except ValueError as exc:
            raise LLMBackendError(
                f"Cloudflare response not JSON: {exc}",
                provider=self.provider_name,
                retriable=True,
            ) from exc

        # Workers AI envelope: {"result": {"response": "<text>"}, "success": true}
        if not data.get("success", False):
            errors = data.get("errors") or []
            err_msg = "; ".join(str(e) for e in errors) or "unknown error"
            raise LLMBackendError(
                f"Cloudflare Workers AI returned success=false: {err_msg}",
                provider=self.provider_name,
                retriable=True,
            )

        raw_text = (
            (data.get("result") or {}).get("response")
            or (data.get("result") or {}).get("content")
            or ""
        )
        if not raw_text:
            raise LLMBackendError(
                "Empty response text from Cloudflare Workers AI",
                provider=self.provider_name,
                retriable=True,
            )

        try:
            program_json = extract_json_from_text(raw_text)
            validate_belief_program_schema(program_json)
        except ValueError as exc:
            raise LLMBackendError(
                f"Cloudflare response parse / validation failed: {exc}",
                provider=self.provider_name,
                retriable=True,
            ) from exc

        # Workers AI doesn't always return token usage; default to 0.
        usage = (data.get("result") or {}).get("usage") or {}
        return LLMResponse(
            program_json=program_json,
            provider=self.provider_name,
            model=model,
            latency_seconds=latency,
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            raw_response=raw_text,
        )
