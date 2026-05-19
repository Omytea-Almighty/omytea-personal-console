"""OllamaBackend — local LLM via Ollama (zero cost, zero quota).

Ollama runs LLMs locally (typically on the user's laptop). For
privacy-first / cost-zero / offline-capable users this is the
preferred backend.

Setup:
  1. Install Ollama: https://ollama.com/download
  2. Pull a model: ``ollama pull llama3.1:8b``
  3. The Ollama daemon listens on ``http://localhost:11434`` by
     default; this backend hits the ``/api/chat`` endpoint.

Env vars (all optional):
  - ``OLLAMA_HOST`` — override default ``http://localhost:11434``
  - ``OLLAMA_MODEL`` — override default ``llama3.1:8b``

No API key. ``is_available()`` short-circuits to False if the
daemon isn't reachable, so this backend slots cleanly into the
RotatingBackend chain without crashing when Ollama isn't running.
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


_DEFAULT_HOST = "http://localhost:11434"


@dataclass(frozen=True, slots=True)
class OllamaBackend(LLMBackend):
    """Local Ollama HTTP backend.

    Args:
      host: override default ``http://localhost:11434``
      model: model identifier (default ``llama3.1:8b``)
      request_timeout_seconds: HTTP timeout (default 120s since local
        models can be slow on smaller hardware)
      probe_timeout_seconds: short timeout used by ``is_available()``
        to check whether the daemon is up.
    """

    provider_name: str = "ollama"
    default_model: str = "llama3.1:8b"
    host: str | None = None
    model: str = "llama3.1:8b"
    request_timeout_seconds: float = 120.0
    probe_timeout_seconds: float = 0.5

    def _get_host(self) -> str:
        return (
            self.host
            or os.environ.get("OLLAMA_HOST", "")
            or _DEFAULT_HOST
        ).strip().rstrip("/")

    def _get_model(self) -> str:
        env_override = os.environ.get("OLLAMA_MODEL", "").strip()
        return env_override or self.model or self.default_model

    def is_available(self) -> bool:
        """Probe the Ollama daemon with a short-timeout GET to
        ``/api/tags``. Returns False if the daemon isn't reachable,
        which lets the RotatingBackend skip Ollama gracefully when
        the user has it stopped or never installed."""
        try:
            import requests
        except ImportError:
            return False
        try:
            resp = requests.get(
                f"{self._get_host()}/api/tags",
                timeout=self.probe_timeout_seconds,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def compile(self, request: LLMRequest) -> LLMResponse:
        try:
            import requests
        except ImportError as exc:
            raise LLMBackendError(
                "requests library not installed. Run: pip install requests",
                provider=self.provider_name,
                retriable=False,
            ) from exc

        host = self._get_host()
        model = self._get_model()
        url = f"{host}/api/chat"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_message},
            ],
            "stream": False,
            "format": "json",  # native JSON-mode hint
            "options": {
                "num_predict": request.max_tokens,
                "temperature": request.temperature,
            },
        }

        t0 = time.perf_counter()
        try:
            resp = requests.post(
                url, json=payload,
                timeout=self.request_timeout_seconds,
            )
        except Exception as exc:
            raise LLMBackendError(
                f"Ollama HTTP call failed ({host}): {exc}",
                provider=self.provider_name,
                retriable=True,
            ) from exc
        latency = time.perf_counter() - t0

        if resp.status_code == 404:
            raise LLMBackendError(
                f"Ollama returned 404 — model '{model}' may not be "
                f"pulled. Run: ollama pull {model}",
                provider=self.provider_name,
                retriable=False,
            )
        if resp.status_code >= 400:
            raise LLMBackendError(
                f"Ollama HTTP {resp.status_code}: {resp.text[:200]}",
                provider=self.provider_name,
                retriable=True,
            )

        try:
            data = resp.json()
        except ValueError as exc:
            raise LLMBackendError(
                f"Ollama response not JSON: {exc}",
                provider=self.provider_name,
                retriable=True,
            ) from exc

        # /api/chat envelope: {"message": {"role": "assistant", "content": "..."}, "done": true, ...}
        msg = data.get("message") or {}
        raw_text = msg.get("content", "")
        if not raw_text:
            raise LLMBackendError(
                "Empty response content from Ollama",
                provider=self.provider_name,
                retriable=True,
            )

        try:
            program_json = extract_json_from_text(raw_text)
            validate_belief_program_schema(program_json)
        except ValueError as exc:
            raise LLMBackendError(
                f"Ollama response parse / validation failed: {exc}",
                provider=self.provider_name,
                retriable=True,
            ) from exc

        prompt_eval = int(data.get("prompt_eval_count", 0) or 0)
        eval_count = int(data.get("eval_count", 0) or 0)
        return LLMResponse(
            program_json=program_json,
            provider=self.provider_name,
            model=model,
            latency_seconds=latency,
            prompt_tokens=prompt_eval,
            completion_tokens=eval_count,
            raw_response=raw_text,
        )
