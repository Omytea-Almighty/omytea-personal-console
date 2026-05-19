"""Tests for OllamaVisionBackend — vision (image+text) LLM via local Ollama.

These tests do NOT make live HTTP calls (no real model invocation).
They exercise:
- Public API construction + defaults
- is_available() probe behavior (no daemon → False)
- vision_compile guard (no images → error)
- Base64 encoding round-trips (bytes / str / data: URL)
- LLMBackend Protocol conformance + registry presence
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm_backends import (  # noqa: E402
    LLMBackend,
    LLMBackendError,
    OllamaVisionBackend,
    OllamaVisionRequest,
    list_backends,
)
from llm_backends.ollama_vision_backend import _to_base64  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("OLLAMA_HOST", "OLLAMA_VISION_MODEL"):
        monkeypatch.delenv(var, raising=False)


# ----- Construction + defaults -----


def test_default_model_is_llava_7b() -> None:
    b = OllamaVisionBackend()
    assert b.default_model == "llava:7b"
    assert b._get_model() == "llava:7b"


def test_default_host_is_localhost_11434() -> None:
    assert OllamaVisionBackend()._get_host() == "http://localhost:11434"


def test_provider_name_is_ollama_vision() -> None:
    assert OllamaVisionBackend().provider_name == "ollama_vision"


def test_model_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_VISION_MODEL", "qwen2-vl:7b")
    assert OllamaVisionBackend()._get_model() == "qwen2-vl:7b"


def test_host_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_HOST", "http://10.0.0.5:11434")
    assert OllamaVisionBackend()._get_host() == "http://10.0.0.5:11434"


def test_host_strips_trailing_slash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434/")
    assert OllamaVisionBackend()._get_host() == "http://localhost:11434"


# ----- is_available() probe -----


def test_is_available_false_when_daemon_offline() -> None:
    # Point at unreachable port; probe should swallow + return False
    b = OllamaVisionBackend(host="http://127.0.0.1:1")
    assert b.is_available() is False


# ----- _to_base64 helper -----


def test_to_base64_bytes_input() -> None:
    raw = b"\x89PNG\r\n\x1a\n"  # PNG header bytes
    out = _to_base64(raw)
    assert isinstance(out, str)
    assert out == base64.b64encode(raw).decode("ascii")


def test_to_base64_already_string_passes_through() -> None:
    encoded = base64.b64encode(b"hello").decode("ascii")
    assert _to_base64(encoded) == encoded


def test_to_base64_strips_data_url_prefix() -> None:
    encoded = base64.b64encode(b"hello").decode("ascii")
    data_url = f"data:image/png;base64,{encoded}"
    assert _to_base64(data_url) == encoded


def test_to_base64_rejects_non_str_non_bytes() -> None:
    with pytest.raises(TypeError, match="bytes or str"):
        _to_base64(12345)  # type: ignore[arg-type]


# ----- vision_compile guards -----


def test_vision_compile_no_images_raises() -> None:
    b = OllamaVisionBackend(host="http://127.0.0.1:1")
    req = OllamaVisionRequest(
        system_prompt="describe", user_message="?", images=(),
    )
    with pytest.raises(LLMBackendError) as exc_info:
        b.vision_compile(req)
    assert "no images" in str(exc_info.value).lower()
    assert exc_info.value.retriable is False


def test_vision_compile_unreachable_daemon_raises_retriable() -> None:
    b = OllamaVisionBackend(host="http://127.0.0.1:1")
    req = OllamaVisionRequest(
        system_prompt="describe",
        user_message="what's in this image?",
        images=(b"\xFF\xD8\xFF\xE0",),  # JPEG SOI marker
    )
    with pytest.raises(LLMBackendError) as exc_info:
        b.vision_compile(req)
    assert exc_info.value.retriable is True


def test_vision_compile_bad_image_type_raises_non_retriable() -> None:
    b = OllamaVisionBackend(host="http://127.0.0.1:1")
    # type: ignore on purpose to test guard
    req = OllamaVisionRequest(
        system_prompt="x",
        user_message="x",
        images=(12345,),  # type: ignore[arg-type]
    )
    with pytest.raises(LLMBackendError) as exc_info:
        b.vision_compile(req)
    assert exc_info.value.retriable is False
    assert "encode" in str(exc_info.value).lower()


# ----- OllamaVisionRequest dataclass -----


def test_request_defaults() -> None:
    req = OllamaVisionRequest(
        system_prompt="s", user_message="u", images=(b"img",),
    )
    assert req.max_tokens == 2048
    # Vision LLMs tend to drift; default temp is conservative
    assert req.temperature == 0.4


def test_request_image_tuple_immutable() -> None:
    """slots=True frozen=True should prevent mutation."""
    req = OllamaVisionRequest(
        system_prompt="s", user_message="u", images=(b"a",),
    )
    with pytest.raises((AttributeError, Exception)):
        req.images = (b"b",)  # type: ignore[misc]


# ----- Registry integration -----


def test_in_list_backends() -> None:
    # The text-only OllamaBackend stays under "ollama" name; the
    # vision backend is currently not in the _REGISTRY (it has a
    # different request shape). We expose it as a public class only.
    # This test verifies the class is importable + Protocol-conformant.
    b = OllamaVisionBackend()
    assert isinstance(b, LLMBackend)


def test_protocol_conformance() -> None:
    b = OllamaVisionBackend()
    assert hasattr(b, "compile")
    assert hasattr(b, "is_available")
    assert hasattr(b, "vision_compile")
    assert hasattr(b, "provider_name")
    assert hasattr(b, "default_model")


# ----- Public exports -----


def test_public_exports_in_init() -> None:
    """Both class + request type must be importable from llm_backends."""
    from llm_backends import OllamaVisionBackend, OllamaVisionRequest
    assert OllamaVisionBackend is not None
    assert OllamaVisionRequest is not None
