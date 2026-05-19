"""Tests for the quota guard / cost tracking layer (B5)."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm_backends import (  # noqa: E402
    DEFAULT_POLICIES,
    LLMBackendError,
    LLMRequest,
    MockBackend,
    QuotaExhaustedError,
    QuotaGuardedBackend,
    QuotaPolicy,
    QuotaStore,
    RotatingBackend,
    with_quota_guard,
)


@pytest.fixture
def tmp_store() -> QuotaStore:
    """Per-test isolated SQLite quota store."""
    with tempfile.TemporaryDirectory() as tmp:
        store = QuotaStore(db_path=Path(tmp) / "quota.db")
        yield store


# ----- QuotaStore unit -----


def test_store_initial_counts_are_zero(tmp_store: QuotaStore) -> None:
    assert tmp_store.get_user_count("gemini", "u1") == 0
    assert tmp_store.get_provider_total("gemini") == 0
    assert tmp_store.get_provider_cost_usd("gemini") == 0.0


def test_store_increment_returns_new_counts(tmp_store: QuotaStore) -> None:
    user_count, provider_total = tmp_store.increment("gemini", "u1", cost_usd=0.05)
    assert user_count == 1
    assert provider_total == 1
    assert tmp_store.get_user_count("gemini", "u1") == 1
    assert tmp_store.get_provider_total("gemini") == 1
    assert tmp_store.get_provider_cost_usd("gemini") == pytest.approx(0.05)


def test_store_increment_per_user_isolation(tmp_store: QuotaStore) -> None:
    """u1 and u2 each get their own per-user counts; provider total
    aggregates across both."""
    tmp_store.increment("gemini", "u1")
    tmp_store.increment("gemini", "u1")
    tmp_store.increment("gemini", "u2")
    assert tmp_store.get_user_count("gemini", "u1") == 2
    assert tmp_store.get_user_count("gemini", "u2") == 1
    assert tmp_store.get_provider_total("gemini") == 3


def test_store_increment_per_provider_isolation(tmp_store: QuotaStore) -> None:
    """gemini and groq counters don't bleed into each other."""
    tmp_store.increment("gemini", "u1")
    tmp_store.increment("groq", "u1")
    assert tmp_store.get_user_count("gemini", "u1") == 1
    assert tmp_store.get_user_count("groq", "u1") == 1
    assert tmp_store.get_provider_total("gemini") == 1
    assert tmp_store.get_provider_total("groq") == 1


def test_store_cost_accumulates(tmp_store: QuotaStore) -> None:
    tmp_store.increment("anthropic", "u1", cost_usd=0.10)
    tmp_store.increment("anthropic", "u1", cost_usd=0.15)
    tmp_store.increment("anthropic", "u2", cost_usd=0.05)
    assert tmp_store.get_provider_cost_usd("anthropic") == pytest.approx(0.30)


def test_store_reset_all(tmp_store: QuotaStore) -> None:
    tmp_store.increment("gemini", "u1")
    tmp_store.reset_all()
    assert tmp_store.get_user_count("gemini", "u1") == 0
    assert tmp_store.get_provider_total("gemini") == 0


# ----- QuotaGuardedBackend semantics -----


def test_quota_guarded_passes_through_when_under_limit(tmp_store: QuotaStore) -> None:
    inner = MockBackend()
    policy = QuotaPolicy(
        provider="mock", daily_total_limit=10, daily_per_user_limit=3,
    )
    guarded = QuotaGuardedBackend(
        inner=inner, policy=policy, store=tmp_store, user_id="u1",
    )
    resp = guarded.compile(LLMRequest(system_prompt="x", user_message="y"))
    assert resp.provider == "mock"
    # Counter was incremented
    assert tmp_store.get_user_count("mock", "u1") == 1


def test_quota_guarded_blocks_when_per_user_exhausted(tmp_store: QuotaStore) -> None:
    inner = MockBackend()
    policy = QuotaPolicy(
        provider="mock", daily_total_limit=100, daily_per_user_limit=2,
    )
    guarded = QuotaGuardedBackend(
        inner=inner, policy=policy, store=tmp_store, user_id="u1",
    )
    guarded.compile(LLMRequest(system_prompt="x", user_message="y"))
    guarded.compile(LLMRequest(system_prompt="x", user_message="y"))
    with pytest.raises(QuotaExhaustedError) as exc_info:
        guarded.compile(LLMRequest(system_prompt="x", user_message="y"))
    assert exc_info.value.scope == "per_user"
    assert exc_info.value.limit == 2
    assert exc_info.value.retriable is True  # so rotating fallback can try next


def test_quota_guarded_blocks_when_total_exhausted(tmp_store: QuotaStore) -> None:
    inner = MockBackend()
    policy = QuotaPolicy(
        provider="mock", daily_total_limit=2, daily_per_user_limit=100,
    )
    # u1 + u2 each call once → hits total limit
    QuotaGuardedBackend(
        inner=inner, policy=policy, store=tmp_store, user_id="u1",
    ).compile(LLMRequest(system_prompt="x", user_message="y"))
    QuotaGuardedBackend(
        inner=inner, policy=policy, store=tmp_store, user_id="u2",
    ).compile(LLMRequest(system_prompt="x", user_message="y"))
    with pytest.raises(QuotaExhaustedError) as exc_info:
        QuotaGuardedBackend(
            inner=inner, policy=policy, store=tmp_store, user_id="u3",
        ).compile(LLMRequest(system_prompt="x", user_message="y"))
    assert exc_info.value.scope == "total"
    assert exc_info.value.limit == 2


def test_quota_guarded_does_not_increment_on_inner_failure(tmp_store: QuotaStore) -> None:
    """If inner.compile() raises, counters should NOT increment —
    we only count successful calls."""
    from llm_backends import AnthropicBackend  # known unavailable without key

    # Ensure no key in env for this test
    if "ANTHROPIC_API_KEY" in os.environ:
        old = os.environ.pop("ANTHROPIC_API_KEY")
    else:
        old = None
    try:
        inner = AnthropicBackend()  # is_available=False → raises on compile
        policy = QuotaPolicy(
            provider="anthropic", daily_total_limit=10, daily_per_user_limit=5,
        )
        guarded = QuotaGuardedBackend(
            inner=inner, policy=policy, store=tmp_store, user_id="u1",
        )
        with pytest.raises(LLMBackendError):
            guarded.compile(LLMRequest(system_prompt="x", user_message="y"))
        # No increment
        assert tmp_store.get_user_count("anthropic", "u1") == 0
        assert tmp_store.get_provider_total("anthropic") == 0
    finally:
        if old is not None:
            os.environ["ANTHROPIC_API_KEY"] = old


def test_quota_guarded_is_available_false_when_total_exhausted(tmp_store: QuotaStore) -> None:
    inner = MockBackend()
    policy = QuotaPolicy(
        provider="mock", daily_total_limit=1, daily_per_user_limit=100,
    )
    guarded = QuotaGuardedBackend(
        inner=inner, policy=policy, store=tmp_store, user_id="u1",
    )
    assert guarded.is_available() is True
    guarded.compile(LLMRequest(system_prompt="x", user_message="y"))
    # Now total = 1 = limit → should report unavailable
    guarded2 = QuotaGuardedBackend(
        inner=inner, policy=policy, store=tmp_store, user_id="u2",
    )
    assert guarded2.is_available() is False


# ----- with_quota_guard helper -----


def test_with_quota_guard_uses_default_policy_for_known_provider(tmp_store: QuotaStore) -> None:
    """When wrapping a known backend (mock/gemini/groq/anthropic),
    helper should pick DEFAULT_POLICIES entry by provider name."""
    guarded = with_quota_guard(MockBackend(), user_id="u1", store=tmp_store)
    assert guarded.policy.provider == "mock"
    assert guarded.policy.daily_total_limit == DEFAULT_POLICIES["mock"].daily_total_limit


def test_with_quota_guard_explicit_policy_override(tmp_store: QuotaStore) -> None:
    custom = QuotaPolicy(provider="mock", daily_total_limit=42, daily_per_user_limit=7)
    guarded = with_quota_guard(
        MockBackend(), user_id="u1", policy=custom, store=tmp_store,
    )
    assert guarded.policy.daily_total_limit == 42


# ----- Integration with RotatingBackend -----


def test_rotating_skips_quota_exhausted_provider(tmp_store: QuotaStore) -> None:
    """When a quota-guarded provider hits limit, rotating should
    fall through to next available provider."""
    # Make Gemini-like mock with quota=1; after first call, exhausted.
    inner1 = MockBackend()
    policy1 = QuotaPolicy(
        provider="gemini-fake", daily_total_limit=1, daily_per_user_limit=1,
    )
    guarded1 = QuotaGuardedBackend(
        inner=inner1, policy=policy1, store=tmp_store, user_id="u1",
    )
    # Fallback: regular mock, no quota
    backup = MockBackend()

    rotating = RotatingBackend(backends=(guarded1, backup))

    # First call → guarded1 succeeds (response provider reflects the
    # INNER MockBackend.provider_name, not the wrapper — quota guard
    # is purely a control layer, doesn't show up as a provider)
    resp1 = rotating.compile(LLMRequest(system_prompt="x", user_message="y"))
    assert resp1.provider == "rotating::mock"
    # Counter incremented for the gemini-fake policy
    assert tmp_store.get_provider_total("gemini-fake") == 1

    # Second call → guarded1.is_available() now False because total
    # reached limit → rotating skips it and uses unguarded backup
    resp2 = rotating.compile(LLMRequest(system_prompt="x", user_message="y"))
    assert resp2.provider == "rotating::mock"
    # gemini-fake counter unchanged (skipped)
    assert tmp_store.get_provider_total("gemini-fake") == 1


# ----- DEFAULT_POLICIES sanity -----


def test_default_policies_has_known_providers() -> None:
    for name in ("mock", "gemini", "groq", "anthropic"):
        assert name in DEFAULT_POLICIES
        p = DEFAULT_POLICIES[name]
        assert p.daily_total_limit > 0
        assert p.daily_per_user_limit > 0
        assert p.cost_per_call_usd >= 0


def test_default_policies_gemini_cap_under_publicized_free_tier() -> None:
    """Gemini Flash free tier is ~1500 RPD; our cap should be ≤1500."""
    assert DEFAULT_POLICIES["gemini"].daily_total_limit <= 1500


def test_default_policies_groq_cap_under_publicized_free_tier() -> None:
    """Groq Llama-3.3-70b free tier is ~14400 RPD; our cap ≤14400."""
    assert DEFAULT_POLICIES["groq"].daily_total_limit <= 14400


def test_default_policies_paid_providers_have_cost(tmp_store: QuotaStore) -> None:
    """Paid providers (anthropic) should have nonzero cost estimate."""
    assert DEFAULT_POLICIES["anthropic"].cost_per_call_usd > 0


def test_default_policies_free_providers_have_zero_cost() -> None:
    assert DEFAULT_POLICIES["gemini"].cost_per_call_usd == 0
    assert DEFAULT_POLICIES["groq"].cost_per_call_usd == 0
    assert DEFAULT_POLICIES["mock"].cost_per_call_usd == 0
