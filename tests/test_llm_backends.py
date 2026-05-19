"""Tests for the llm_backends abstraction layer.

Covers:
- LLMBackend Protocol contract
- MockBackend deterministic output + schema validation
- AnthropicBackend / GeminiBackend / GroqBackend availability detection
  (without making real API calls — we just check the gate logic)
- RotatingBackend fallback semantics
- get_default_backend selection from priority chain
- extract_json_from_text + validate_belief_program_schema helpers
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm_backends import (  # noqa: E402
    AnthropicBackend,
    GeminiBackend,
    GroqBackend,
    LLMBackend,
    LLMBackendError,
    LLMRequest,
    LLMResponse,
    MockBackend,
    RotatingBackend,
    extract_json_from_text,
    get_backend,
    get_default_backend,
    list_backends,
    validate_belief_program_schema,
)


# ----- MockBackend -----


def test_mock_backend_always_available() -> None:
    b = MockBackend()
    assert b.is_available() is True


def test_mock_backend_returns_valid_belief_program() -> None:
    b = MockBackend()
    req = LLMRequest(system_prompt="x", user_message="y")
    resp = b.compile(req)
    assert isinstance(resp, LLMResponse)
    assert resp.provider == "mock"
    assert "branches" in resp.program_json
    assert len(resp.program_json["branches"]) >= 6  # P1 schema requires 6-8


def test_mock_backend_branches_sum_to_one() -> None:
    b = MockBackend()
    resp = b.compile(LLMRequest(system_prompt="x", user_message="y"))
    probs = [b["probability_prior"] for b in resp.program_json["branches"]]
    assert abs(sum(probs) - 1.0) < 1e-6


def test_mock_backend_includes_wishful_and_worst_anchors() -> None:
    """P1 anchor invariant must hold in the mock."""
    b = MockBackend()
    resp = b.compile(LLMRequest(system_prompt="x", user_message="y"))
    types = [br.get("branch_type") for br in resp.program_json["branches"]]
    assert types.count("wishful") == 1
    assert types.count("worst") == 1


# ----- AnthropicBackend availability -----


def test_anthropic_backend_unavailable_without_key(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    b = AnthropicBackend()
    assert b.is_available() is False


def test_anthropic_backend_available_with_key(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    b = AnthropicBackend()
    assert b.is_available() is True


def test_anthropic_backend_explicit_key_overrides_env(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    b = AnthropicBackend(api_key="sk-ant-explicit")
    assert b.is_available() is True


def test_anthropic_backend_raises_clearly_without_key(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    b = AnthropicBackend()
    with pytest.raises(LLMBackendError) as exc_info:
        b.compile(LLMRequest(system_prompt="x", user_message="y"))
    assert exc_info.value.retriable is False
    assert "ANTHROPIC_API_KEY" in str(exc_info.value)


# ----- GeminiBackend availability -----


def test_gemini_backend_unavailable_without_key(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    b = GeminiBackend()
    assert b.is_available() is False


def test_gemini_backend_accepts_gemini_api_key(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "gem-test")
    b = GeminiBackend()
    assert b.is_available() is True


def test_gemini_backend_accepts_google_api_key_alias(monkeypatch) -> None:
    """GOOGLE_API_KEY env var name is the alias accepted as well."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "ga-test")
    b = GeminiBackend()
    assert b.is_available() is True


# ----- GroqBackend availability -----


def test_groq_backend_unavailable_without_key(monkeypatch) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    b = GroqBackend()
    assert b.is_available() is False


def test_groq_backend_available_with_key(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test")
    b = GroqBackend()
    assert b.is_available() is True


# ----- RotatingBackend semantics -----


class _AlwaysFailRetriableBackend(LLMBackend):
    """Fake backend for testing — always fails with retriable=True."""

    provider_name: str = "fail-retriable"
    default_model: str = "fail"

    def compile(self, request: LLMRequest) -> LLMResponse:
        raise LLMBackendError("always fails", provider="fail-retriable", retriable=True)

    def is_available(self) -> bool:
        return True


class _AlwaysFailNonRetriableBackend(LLMBackend):
    """Fake backend for testing — always fails with retriable=False."""

    provider_name: str = "fail-nonretriable"
    default_model: str = "fail"

    def compile(self, request: LLMRequest) -> LLMResponse:
        raise LLMBackendError(
            "broken dependency", provider="fail-nonretriable", retriable=False
        )

    def is_available(self) -> bool:
        return True


def test_rotating_backend_falls_through_to_next_on_retriable() -> None:
    """If first backend fails retriably, rotating should try next."""
    rot = RotatingBackend(
        backends=(_AlwaysFailRetriableBackend(), MockBackend())
    )
    resp = rot.compile(LLMRequest(system_prompt="x", user_message="y"))
    # MockBackend should have succeeded
    assert resp.provider == "rotating::mock"


def test_rotating_backend_propagates_nonretriable_immediately() -> None:
    """If first backend fails non-retriably (e.g. missing dep), don't try next."""
    rot = RotatingBackend(
        backends=(_AlwaysFailNonRetriableBackend(), MockBackend())
    )
    with pytest.raises(LLMBackendError) as exc_info:
        rot.compile(LLMRequest(system_prompt="x", user_message="y"))
    assert exc_info.value.retriable is False


def test_rotating_backend_raises_when_all_fail() -> None:
    rot = RotatingBackend(backends=(_AlwaysFailRetriableBackend(),))
    with pytest.raises(LLMBackendError):
        rot.compile(LLMRequest(system_prompt="x", user_message="y"))


def test_rotating_backend_skips_unavailable() -> None:
    """An unavailable backend should be silently skipped, not raise."""
    # Use an Anthropic without key (unavailable) + mock (available)
    rot = RotatingBackend(backends=(AnthropicBackend(), MockBackend()))
    resp = rot.compile(LLMRequest(system_prompt="x", user_message="y"))
    assert resp.provider == "rotating::mock"


# ----- get_default_backend selection -----


def test_get_default_backend_returns_mock_in_mock_mode(monkeypatch) -> None:
    monkeypatch.setenv("OMYTEA_CONSOLE_MOCK", "1")
    monkeypatch.delenv("OMYTEA_LLM_BACKEND", raising=False)
    b = get_default_backend()
    assert isinstance(b, MockBackend)


def test_get_default_backend_force_mock_kwarg(monkeypatch) -> None:
    monkeypatch.delenv("OMYTEA_CONSOLE_MOCK", raising=False)
    b = get_default_backend(force_mock=True)
    assert isinstance(b, MockBackend)


def test_get_default_backend_falls_back_to_mock_with_no_keys(monkeypatch) -> None:
    monkeypatch.delenv("OMYTEA_CONSOLE_MOCK", raising=False)
    monkeypatch.delenv("OMYTEA_LLM_BACKEND", raising=False)
    for key in (
        "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY",
        "GROQ_API_KEY", "OPENAI_API_KEY",
        "CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID",
    ):
        monkeypatch.delenv(key, raising=False)
    # OllamaBackend.is_available() does an HTTP probe; on developer
    # machines a daemon may be running. Force probe-fail so we
    # actually test the "no provider available" path.
    from llm_backends.ollama_backend import OllamaBackend
    monkeypatch.setattr(
        OllamaBackend, "is_available", lambda self: False,
    )
    b = get_default_backend()
    assert isinstance(b, MockBackend)


def test_get_default_backend_respects_explicit_env_var(monkeypatch) -> None:
    monkeypatch.delenv("OMYTEA_CONSOLE_MOCK", raising=False)
    monkeypatch.setenv("OMYTEA_LLM_BACKEND", "mock")
    b = get_default_backend()
    assert isinstance(b, MockBackend)


def test_get_default_backend_fails_loud_on_unconfigured_explicit(monkeypatch) -> None:
    """If user sets OMYTEA_LLM_BACKEND=anthropic but no key, should raise."""
    monkeypatch.delenv("OMYTEA_CONSOLE_MOCK", raising=False)
    monkeypatch.setenv("OMYTEA_LLM_BACKEND", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(LLMBackendError):
        get_default_backend()


def test_get_default_backend_returns_rotating_when_multiple_available(monkeypatch) -> None:
    """If 2+ providers are configured, default returns a RotatingBackend."""
    monkeypatch.delenv("OMYTEA_CONSOLE_MOCK", raising=False)
    monkeypatch.delenv("OMYTEA_LLM_BACKEND", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "gem-test")
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test")
    b = get_default_backend()
    assert isinstance(b, RotatingBackend)


# ----- get_backend factory -----


def test_get_backend_returns_correct_type() -> None:
    assert isinstance(get_backend("mock"), MockBackend)
    assert isinstance(get_backend("anthropic"), AnthropicBackend)
    assert isinstance(get_backend("gemini"), GeminiBackend)
    assert isinstance(get_backend("groq"), GroqBackend)


def test_get_backend_unknown_raises_keyerror() -> None:
    with pytest.raises(KeyError, match="Unknown LLM backend"):
        get_backend("nonexistent_provider_xyz")


def test_list_backends_contains_expected_providers() -> None:
    names = list_backends()
    assert "mock" in names
    assert "anthropic" in names
    assert "gemini" in names
    assert "groq" in names


# ----- JSON extraction helpers -----


def test_extract_json_from_text_plain_json() -> None:
    out = extract_json_from_text('{"a": 1, "b": 2}')
    assert out == {"a": 1, "b": 2}


def test_extract_json_from_text_with_markdown_fence() -> None:
    text = '```json\n{"x": 42}\n```'
    assert extract_json_from_text(text) == {"x": 42}


def test_extract_json_from_text_with_prose_before() -> None:
    text = 'Here is the JSON:\n{"y": "ok"}'
    assert extract_json_from_text(text) == {"y": "ok"}


def test_extract_json_from_text_raises_on_no_json() -> None:
    with pytest.raises(ValueError, match="No JSON object found"):
        extract_json_from_text("just some prose without any braces")


# ----- Schema validation -----


def test_validate_belief_program_schema_accepts_valid() -> None:
    valid = {
        "branches": [
            {"label": "a", "probability_prior": 0.5, "narrative": "x"},
            {"label": "b", "probability_prior": 0.3, "narrative": "y"},
            {"label": "c", "probability_prior": 0.2, "narrative": "z"},
        ],
    }
    # Should not raise
    validate_belief_program_schema(valid)


def test_validate_belief_program_schema_rejects_bad_sum() -> None:
    """3 branches present, but probs sum to 0.5 not 1 — must reject."""
    invalid = {
        "branches": [
            {"label": "a", "probability_prior": 0.2, "narrative": "x"},
            {"label": "b", "probability_prior": 0.2, "narrative": "y"},
            {"label": "c", "probability_prior": 0.1, "narrative": "z"},
        ],
    }
    with pytest.raises(ValueError, match="sum to 1"):
        validate_belief_program_schema(invalid)


def test_validate_belief_program_schema_rejects_missing_branches() -> None:
    with pytest.raises(ValueError, match="missing required field"):
        validate_belief_program_schema({})
