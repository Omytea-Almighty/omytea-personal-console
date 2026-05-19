"""B3 — tests for the three additional LLM backends.

CloudflareWorkersAIBackend / OpenAIBackend / OllamaBackend.

All three are exercised under is_available()=False (no env / no
daemon) and the registry-integration paths. Live HTTP calls are NOT
made — those require real API tokens or a running Ollama daemon and
belong in integration-test land.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm_backends import (  # noqa: E402
    DEFAULT_POLICIES,
    DEFAULT_PRIORITY_CHAIN,
    CloudflareWorkersAIBackend,
    LLMBackend,
    LLMBackendError,
    LLMRequest,
    OllamaBackend,
    OpenAIBackend,
    get_backend,
    list_backends,
    with_quota_guard,
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Per-test env cleanup so a real key in the developer's shell
    doesn't accidentally turn is_available()=True."""
    for var in (
        "CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID",
        "CLOUDFLARE_AI_MODEL",
        "OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_BASE_URL",
        "OLLAMA_HOST", "OLLAMA_MODEL",
    ):
        monkeypatch.delenv(var, raising=False)


# ----- Registry integration -----


def test_three_new_backends_in_registry() -> None:
    backends = list_backends()
    assert "cloudflare_workers_ai" in backends
    assert "openai" in backends
    assert "ollama" in backends


def test_get_backend_constructs_each_new_backend() -> None:
    cf = get_backend("cloudflare_workers_ai")
    assert isinstance(cf, CloudflareWorkersAIBackend)
    oa = get_backend("openai")
    assert isinstance(oa, OpenAIBackend)
    ol = get_backend("ollama")
    assert isinstance(ol, OllamaBackend)


def test_default_priority_chain_includes_new_backends() -> None:
    for name in ("ollama", "cloudflare_workers_ai", "openai"):
        assert name in DEFAULT_PRIORITY_CHAIN


def test_priority_chain_ollama_first_then_free_tier() -> None:
    """Ollama (local, free, private) should rank before paid keys."""
    chain = list(DEFAULT_PRIORITY_CHAIN)
    assert chain[0] == "ollama"
    assert chain.index("ollama") < chain.index("openai")
    assert chain.index("ollama") < chain.index("anthropic")


def test_mock_always_last() -> None:
    chain = list(DEFAULT_PRIORITY_CHAIN)
    assert chain[-1] == "mock"


# ----- Default policies -----


def test_each_new_backend_has_default_policy() -> None:
    for name in ("cloudflare_workers_ai", "openai", "ollama"):
        assert name in DEFAULT_POLICIES
        p = DEFAULT_POLICIES[name]
        assert p.daily_total_limit > 0
        assert p.daily_per_user_limit > 0
        assert p.cost_per_call_usd >= 0


def test_ollama_policy_has_zero_cost() -> None:
    assert DEFAULT_POLICIES["ollama"].cost_per_call_usd == 0.0


def test_cloudflare_policy_has_zero_cost() -> None:
    """Workers AI free tier — zero marginal cost in the policy table."""
    assert DEFAULT_POLICIES["cloudflare_workers_ai"].cost_per_call_usd == 0.0


def test_openai_policy_has_nonzero_cost() -> None:
    """OpenAI is paid; cost_per_call_usd should reflect that."""
    assert DEFAULT_POLICIES["openai"].cost_per_call_usd > 0


# ----- CloudflareWorkersAIBackend -----


def test_cloudflare_unavailable_without_credentials() -> None:
    cf = CloudflareWorkersAIBackend()
    assert cf.is_available() is False


def test_cloudflare_unavailable_with_token_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "x")
    cf = CloudflareWorkersAIBackend()
    assert cf.is_available() is False  # still needs account_id


def test_cloudflare_unavailable_with_account_id_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "acct123")
    cf = CloudflareWorkersAIBackend()
    assert cf.is_available() is False  # still needs token


def test_cloudflare_available_with_both_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "x")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "acct123")
    cf = CloudflareWorkersAIBackend()
    assert cf.is_available() is True


def test_cloudflare_compile_raises_when_unavailable() -> None:
    cf = CloudflareWorkersAIBackend()
    with pytest.raises(LLMBackendError) as exc_info:
        cf.compile(LLMRequest(system_prompt="x", user_message="y"))
    assert "CLOUDFLARE_API_TOKEN" in str(exc_info.value)
    assert exc_info.value.retriable is False


def test_cloudflare_model_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLOUDFLARE_AI_MODEL", "@cf/mistralai/mistral-7b-instruct-v0.2")
    cf = CloudflareWorkersAIBackend()
    assert cf._get_model() == "@cf/mistralai/mistral-7b-instruct-v0.2"


def test_cloudflare_default_model() -> None:
    cf = CloudflareWorkersAIBackend()
    assert cf._get_model().startswith("@cf/")


# ----- OpenAIBackend -----


def test_openai_unavailable_without_key() -> None:
    oa = OpenAIBackend()
    assert oa.is_available() is False


def test_openai_available_with_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-xxx")
    oa = OpenAIBackend()
    assert oa.is_available() is True


def test_openai_compile_raises_when_unavailable() -> None:
    oa = OpenAIBackend()
    with pytest.raises(LLMBackendError) as exc_info:
        oa.compile(LLMRequest(system_prompt="x", user_message="y"))
    assert "OPENAI_API_KEY" in str(exc_info.value)
    assert exc_info.value.retriable is False


def test_openai_model_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    oa = OpenAIBackend()
    assert oa._get_model() == "gpt-4o"


def test_openai_base_url_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    oa = OpenAIBackend()
    assert oa._get_base_url() == "https://openrouter.ai/api/v1"


def test_openai_default_model_is_gpt_4o_mini() -> None:
    oa = OpenAIBackend()
    assert oa._get_model() == "gpt-4o-mini"


# ----- OllamaBackend -----


def test_ollama_default_host() -> None:
    ol = OllamaBackend()
    assert ol._get_host() == "http://localhost:11434"


def test_ollama_host_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OLLAMA_HOST", "http://192.168.1.42:11434")
    ol = OllamaBackend()
    assert ol._get_host() == "http://192.168.1.42:11434"


def test_ollama_host_strips_trailing_slash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434/")
    ol = OllamaBackend()
    assert ol._get_host() == "http://localhost:11434"


def test_ollama_default_model() -> None:
    ol = OllamaBackend()
    assert ol._get_model() == "llama3.1:8b"


def test_ollama_model_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:7b")
    ol = OllamaBackend()
    assert ol._get_model() == "qwen2.5:7b"


def test_ollama_is_available_returns_false_when_daemon_offline() -> None:
    """Probe an unreachable host; is_available should swallow + return
    False so the RotatingBackend can skip cleanly."""
    ol = OllamaBackend(host="http://127.0.0.1:1")  # nothing on port 1
    assert ol.is_available() is False


def test_ollama_quota_policy_high_request_cap() -> None:
    """Local cap should be order-of-magnitude higher than free-tier
    cloud providers because the limit is local compute not external
    quota."""
    assert (
        DEFAULT_POLICIES["ollama"].daily_total_limit
        > DEFAULT_POLICIES["gemini"].daily_total_limit
    )


# ----- with_quota_guard integration for new backends -----


def test_with_quota_guard_picks_cloudflare_policy() -> None:
    guarded = with_quota_guard(CloudflareWorkersAIBackend(), user_id="u1")
    assert guarded.policy.provider == "cloudflare_workers_ai"


def test_with_quota_guard_picks_openai_policy() -> None:
    guarded = with_quota_guard(OpenAIBackend(), user_id="u1")
    assert guarded.policy.provider == "openai"


def test_with_quota_guard_picks_ollama_policy() -> None:
    guarded = with_quota_guard(OllamaBackend(), user_id="u1")
    assert guarded.policy.provider == "ollama"


# ----- Backend Protocol conformance -----


def test_new_backends_implement_protocol() -> None:
    for cls in (
        CloudflareWorkersAIBackend, OpenAIBackend, OllamaBackend,
    ):
        instance = cls()
        assert isinstance(instance, LLMBackend)
        assert hasattr(instance, "compile")
        assert hasattr(instance, "is_available")
        assert hasattr(instance, "provider_name")
        assert hasattr(instance, "default_model")


def test_new_backends_have_distinct_provider_names() -> None:
    names = {
        CloudflareWorkersAIBackend().provider_name,
        OpenAIBackend().provider_name,
        OllamaBackend().provider_name,
    }
    assert len(names) == 3  # all distinct
    assert names == {"cloudflare_workers_ai", "openai", "ollama"}
