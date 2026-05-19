"""OllamaVisionBackend — local vision-language LLM via Ollama.

Adds image+text multimodal input to the existing OllamaBackend
pattern. Vision LLMs supported via Ollama's /api/chat endpoint
include LLaVA, BakLLaVA, Qwen2-VL, MiniCPM-V, Llama 3.2 vision, etc.
Default ``llava:7b`` because it fits in 8 GB RAM and is the most
broadly compatible.

Why this exists alongside OllamaBackend: vision LLMs are slow on CPU
(seconds per image), so we want a deliberate opt-in. Text-only
calls continue to flow through OllamaBackend at lower latency. The
vision backend is invoked explicitly by `compile_scene_query()` in
``compiler.py`` when the user uploads a video.

Env vars (all optional):
- ``OLLAMA_HOST``  — defaults to ``http://localhost:11434``
- ``OLLAMA_VISION_MODEL`` — defaults to ``llava:7b``

Image input format: list of `bytes` (JPEG / PNG bytes) OR
list of base64-encoded strings. The backend normalizes to base64
before sending to Ollama.

Multi-vendor architectural default: this is one of several vision
backends in the rotation (others would be Gemini Vision via the
gemini_backend with a vision model name; Anthropic Claude with
image content blocks via the anthropic_backend). The default
rotation prefers local Ollama when the user has opted in to vision
processing.
"""

from __future__ import annotations

import base64
import os
import time
from dataclasses import dataclass

from .base import (
    LLMBackend,
    LLMBackendError,
    LLMRequest,
    LLMResponse,
    extract_json_from_text,
)


_DEFAULT_HOST = "http://localhost:11434"
_DEFAULT_VISION_MODEL = "llava:7b"


@dataclass(frozen=True, slots=True)
class OllamaVisionRequest:
    """Vision request — text prompt + one or more image payloads.

    ``images``: list of (bytes | str). Bytes are assumed JPEG/PNG;
    strings are assumed already base64-encoded.

    Why not extend LLMRequest? LLMRequest is text-only and is used
    across the entire backend Protocol. Keeping vision as a
    distinct request type avoids forcing every backend to think
    about image bytes.
    """
    system_prompt: str
    user_message: str
    images: tuple[bytes | str, ...]
    max_tokens: int = 2048
    temperature: float = 0.4  # vision LLMs tend to drift; lower temp


def _to_base64(image: bytes | str) -> str:
    """Normalize image bytes or already-encoded string to base64 str.

    Ollama's /api/chat ``images`` field expects base64 strings (no
    data: prefix, just the raw base64 text)."""
    if isinstance(image, str):
        # Strip data: prefix if user supplied a data URL
        if image.startswith("data:"):
            comma = image.find(",")
            if comma != -1:
                return image[comma + 1:]
        return image
    if isinstance(image, bytes):
        return base64.b64encode(image).decode("ascii")
    raise TypeError(
        f"OllamaVisionBackend: image must be bytes or str (base64), "
        f"got {type(image).__name__}"
    )


@dataclass(frozen=True, slots=True)
class OllamaVisionBackend(LLMBackend):
    """Local Ollama vision-language backend.

    Args:
      host: override default http://localhost:11434
      model: vision model identifier (default ``llava:7b``)
      request_timeout_seconds: HTTP timeout (default 300s; vision
        LLMs on CPU can take 30-90s per image)
      probe_timeout_seconds: short timeout for is_available()
    """

    provider_name: str = "ollama_vision"
    default_model: str = _DEFAULT_VISION_MODEL
    host: str | None = None
    model: str = _DEFAULT_VISION_MODEL
    request_timeout_seconds: float = 600.0  # generous for CPU-only inference
    probe_timeout_seconds: float = 5.0       # busy daemon needs more than 0.5s

    def _get_host(self) -> str:
        return (
            self.host
            or os.environ.get("OLLAMA_HOST", "")
            or _DEFAULT_HOST
        ).strip().rstrip("/")

    def _get_model(self) -> str:
        env_override = os.environ.get("OLLAMA_VISION_MODEL", "").strip()
        return env_override or self.model or self.default_model

    def is_available(self) -> bool:
        """Reachable + the configured vision model is pulled.

        Two-step check: (1) daemon up, (2) listed model present in
        /api/tags. If the user has Ollama installed but hasn't run
        ``ollama pull llava:7b``, we want to fail cleanly with a
        clear message rather than producing an opaque 404 mid-run.
        """
        try:
            import requests
        except ImportError:
            return False
        try:
            resp = requests.get(
                f"{self._get_host()}/api/tags",
                timeout=self.probe_timeout_seconds,
            )
            if resp.status_code != 200:
                return False
            data = resp.json()
            wanted = self._get_model()
            for m in data.get("models", []):
                if m.get("name") == wanted:
                    return True
            return False
        except Exception:
            return False

    def vision_compile(self, request: OllamaVisionRequest) -> LLMResponse:
        """Submit a vision request (text + images) to Ollama.

        Returns LLMResponse with parsed JSON in program_json. JSON
        parsing is best-effort via extract_json_from_text since vision
        LLMs often produce mixed prose + JSON output.
        """
        try:
            import requests
        except ImportError as exc:
            raise LLMBackendError(
                "requests library not installed. Run: pip install requests",
                provider=self.provider_name,
                retriable=False,
            ) from exc

        if not request.images:
            raise LLMBackendError(
                "OllamaVisionBackend.vision_compile called with no "
                "images. Use OllamaBackend (text-only) instead.",
                provider=self.provider_name,
                retriable=False,
            )

        try:
            images_b64 = [_to_base64(img) for img in request.images]
        except TypeError as exc:
            raise LLMBackendError(
                f"Failed to encode images: {exc}",
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
                {
                    "role": "user",
                    "content": request.user_message,
                    "images": images_b64,
                },
            ],
            "stream": False,
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
                f"Ollama vision HTTP call failed ({host}): {exc}",
                provider=self.provider_name,
                retriable=True,
            ) from exc
        latency = time.perf_counter() - t0

        if resp.status_code == 404:
            raise LLMBackendError(
                f"Ollama returned 404 — vision model '{model}' may not "
                f"be pulled. Run: ollama pull {model}",
                provider=self.provider_name,
                retriable=False,
            )
        if resp.status_code >= 400:
            raise LLMBackendError(
                f"Ollama vision HTTP {resp.status_code}: "
                f"{resp.text[:200]}",
                provider=self.provider_name,
                retriable=True,
            )

        try:
            data = resp.json()
        except ValueError as exc:
            raise LLMBackendError(
                f"Ollama vision response not JSON: {exc}",
                provider=self.provider_name,
                retriable=True,
            ) from exc

        msg = data.get("message") or {}
        raw_text = msg.get("content", "")
        if not raw_text:
            raise LLMBackendError(
                "Empty content from Ollama vision response",
                provider=self.provider_name,
                retriable=True,
            )

        # Best-effort JSON extraction. Vision LLMs often produce
        # mixed prose + JSON; do not raise on prose-only response —
        # the caller decides whether prose is acceptable.
        program_json: dict = {}
        try:
            program_json = extract_json_from_text(raw_text)
        except ValueError:
            # Leave program_json empty; caller can read raw_response.
            pass

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

    def compile(self, request: LLMRequest) -> LLMResponse:
        """LLMBackend Protocol-compliant compile.

        Text-only Protocol requests are routed to the underlying
        text completion (without images) — useful when this backend
        is part of a rotation and a text request happens to land on
        it. For dedicated vision use, call ``vision_compile`` with
        an OllamaVisionRequest.
        """
        # Text-only path: convert to vision request with empty images
        # would fail per our own guard; instead synthesize via the
        # standard /api/chat without images field.
        try:
            import requests
        except ImportError as exc:
            raise LLMBackendError(
                "requests library not installed",
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
            "format": "json",
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
                f"Ollama vision text-mode HTTP failed: {exc}",
                provider=self.provider_name,
                retriable=True,
            ) from exc
        latency = time.perf_counter() - t0

        if resp.status_code >= 400:
            raise LLMBackendError(
                f"Ollama vision text-mode HTTP {resp.status_code}",
                provider=self.provider_name,
                retriable=True,
            )

        data = resp.json()
        raw_text = (data.get("message") or {}).get("content", "")
        if not raw_text:
            raise LLMBackendError(
                "Empty Ollama vision text-mode response",
                provider=self.provider_name,
                retriable=True,
            )
        try:
            from .base import validate_belief_program_schema
            program_json = extract_json_from_text(raw_text)
            validate_belief_program_schema(program_json)
        except ValueError as exc:
            raise LLMBackendError(
                f"Vision-backend text-mode parse failed: {exc}",
                provider=self.provider_name,
                retriable=True,
            ) from exc

        return LLMResponse(
            program_json=program_json,
            provider=self.provider_name,
            model=model,
            latency_seconds=latency,
            prompt_tokens=int(data.get("prompt_eval_count", 0)),
            completion_tokens=int(data.get("eval_count", 0)),
            raw_response=raw_text,
        )
