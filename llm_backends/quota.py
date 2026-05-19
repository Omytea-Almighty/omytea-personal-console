"""Per-provider + per-user quota tracking and cost estimation.

Why this exists:
  Without quota guards, a deployed console can:
    a) Burn through free-tier daily limits silently — Gemini Flash
       caps at ~1500/day; one abusive session could exhaust this for
       all other users
    b) If user-key path is used, runaway calls can hit budget cap
       only AFTER the bill spikes
    c) No per-user attribution = no fairness ("one user spamming
       hurts everyone")

Architecture:
  - QuotaPolicy: declarative limits per provider (daily call cap +
    per-user daily cap + estimated $/call)
  - QuotaStore: SQLite-backed counter; survives container restart
    when the SQLite path is on persistent volume; otherwise resets
    daily anyway
  - QuotaGuardedBackend: wraps an inner LLMBackend, increments
    counters before call, raises QuotaExhaustedError when over
  - Default policies match each free tier's published limits with
    safety buffer

When a quota is hit:
  - QuotaExhaustedError extends LLMBackendError with retriable=True
  - RotatingBackend automatically tries next provider
  - If ALL providers exhausted, user sees actionable message:
    "free tier exhausted for today; please bring your own API key
    or try again tomorrow"

Sanitization note: this module is public-deploy-clean.
"""

from __future__ import annotations

import os
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Iterator

from .base import (
    LLMBackend,
    LLMBackendError,
    LLMRequest,
    LLMResponse,
)


DEFAULT_QUOTA_DB_PATH = Path(
    os.environ.get(
        "OMYTEA_QUOTA_DB",
        str(Path.home() / ".omytea-personal-console" / "quota.db"),
    )
)


@dataclass(frozen=True, slots=True)
class QuotaPolicy:
    """Declarative limits for one provider.

    Defaults are conservative — set well below the actual free-tier
    cap so multiple users can share without hitting hard ceiling.

    Args:
      provider: provider name (must match the LLMBackend.provider_name)
      daily_total_limit: max calls per day across all users
      daily_per_user_limit: max calls per user per day
      cost_per_call_usd: estimated cost per call (for $0 free-tier
        providers this is 0; for user-key paid providers this informs
        UI cost display + total spend cap)
    """

    provider: str
    daily_total_limit: int
    daily_per_user_limit: int
    cost_per_call_usd: float = 0.0


# Built-in policies for known providers.
# Numbers match each provider's published free tier with ~50% safety buffer.
# These are tunable via environment or constructor-passed override.
DEFAULT_POLICIES: dict[str, QuotaPolicy] = {
    "mock": QuotaPolicy(
        provider="mock",
        daily_total_limit=999_999,        # mock has no real limit
        daily_per_user_limit=999_999,
        cost_per_call_usd=0.0,
    ),
    "gemini": QuotaPolicy(
        # Gemini 2.0 Flash free tier ≈ 1500 RPD; cap at 800 conservatively
        provider="gemini",
        daily_total_limit=800,
        daily_per_user_limit=8,
        cost_per_call_usd=0.0,
    ),
    "groq": QuotaPolicy(
        # Groq Llama-3.3-70b-versatile free tier ≈ 14400 RPD; cap at 5000
        provider="groq",
        daily_total_limit=5000,
        daily_per_user_limit=15,
        cost_per_call_usd=0.0,
    ),
    "anthropic": QuotaPolicy(
        # User-supplied paid key; per-user cap protects against runaway,
        # cost estimate informs UI display
        provider="anthropic",
        daily_total_limit=200,            # global runaway-guard
        daily_per_user_limit=10,
        cost_per_call_usd=0.05,           # ~Sonnet rate-ish
    ),
    "cloudflare_workers_ai": QuotaPolicy(
        # Workers AI free tier = 10k neurons/day; cap conservatively
        # at 1000 requests/day to leave room for retries.
        provider="cloudflare_workers_ai",
        daily_total_limit=1000,
        daily_per_user_limit=20,
        cost_per_call_usd=0.0,
    ),
    "openai": QuotaPolicy(
        # User-supplied paid key (gpt-4o-mini ~ $0.15/1M input tokens).
        # Each BeliefProgram compile uses ~2-3k input + ~1k output → very
        # roughly $0.001/call; conservative cap to prevent runaway.
        provider="openai",
        daily_total_limit=300,
        daily_per_user_limit=15,
        cost_per_call_usd=0.001,
    ),
    "ollama": QuotaPolicy(
        # Local — no cost, no upstream quota. Cap on requests is purely
        # a sanity-check against runaway loops (local CPU/GPU is the
        # actual scarce resource).
        provider="ollama",
        daily_total_limit=10_000,
        daily_per_user_limit=200,
        cost_per_call_usd=0.0,
    ),
}


class QuotaExhaustedError(LLMBackendError):
    """Raised when a quota is hit. Always retriable=True so the
    rotating wrapper falls through to the next provider."""

    def __init__(
        self,
        provider: str,
        *,
        scope: str,           # "total" or "per_user"
        limit: int,
        current: int,
    ) -> None:
        msg = (
            f"Quota exhausted for {provider} ({scope}): "
            f"used {current}/{limit} today"
        )
        super().__init__(msg, provider=provider, retriable=True)
        self.scope = scope
        self.limit = limit
        self.current = current


class QuotaStore:
    """SQLite-backed counters for daily provider + user call counts.

    Schema:
      llm_usage (
        usage_date TEXT,         -- YYYY-MM-DD
        provider TEXT,
        user_id TEXT,            -- session id / cookie / "anonymous"
        call_count INTEGER,
        last_updated REAL,
        PRIMARY KEY (usage_date, provider, user_id)
      )

      llm_provider_totals (
        usage_date TEXT,
        provider TEXT,
        total_calls INTEGER,
        total_cost_usd REAL,
        PRIMARY KEY (usage_date, provider)
      )

    SQLite is single-writer; if multiple Streamlit threads write
    concurrently we may hit lock contention. For self-test phase
    (≤20 users) this is fine. For higher concurrency, migrate to
    Postgres per DEPLOYMENT_GUIDE recommendation.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or DEFAULT_QUOTA_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS llm_usage (
                    usage_date     TEXT NOT NULL,
                    provider       TEXT NOT NULL,
                    user_id        TEXT NOT NULL,
                    call_count     INTEGER DEFAULT 0,
                    last_updated   REAL DEFAULT 0,
                    PRIMARY KEY (usage_date, provider, user_id)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS llm_provider_totals (
                    usage_date     TEXT NOT NULL,
                    provider       TEXT NOT NULL,
                    total_calls    INTEGER DEFAULT 0,
                    total_cost_usd REAL DEFAULT 0,
                    PRIMARY KEY (usage_date, provider)
                )
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_usage_lookup "
                "ON llm_usage(usage_date, provider, user_id)"
            )
            conn.commit()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def today(self) -> str:
        return date.today().isoformat()

    def get_user_count(self, provider: str, user_id: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT call_count FROM llm_usage "
                "WHERE usage_date = ? AND provider = ? AND user_id = ?",
                (self.today(), provider, user_id),
            ).fetchone()
        return int(row["call_count"]) if row else 0

    def get_provider_total(self, provider: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT total_calls FROM llm_provider_totals "
                "WHERE usage_date = ? AND provider = ?",
                (self.today(), provider),
            ).fetchone()
        return int(row["total_calls"]) if row else 0

    def get_provider_cost_usd(self, provider: str) -> float:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT total_cost_usd FROM llm_provider_totals "
                "WHERE usage_date = ? AND provider = ?",
                (self.today(), provider),
            ).fetchone()
        return float(row["total_cost_usd"]) if row else 0.0

    def increment(
        self, provider: str, user_id: str, cost_usd: float = 0.0,
    ) -> tuple[int, int]:
        """Atomically increment user + provider counters; return
        (new_user_count, new_provider_total)."""
        today = self.today()
        with self._connect() as conn:
            cur = conn.cursor()
            # UPSERT per-user
            cur.execute(
                """
                INSERT INTO llm_usage (usage_date, provider, user_id, call_count, last_updated)
                VALUES (?, ?, ?, 1, ?)
                ON CONFLICT(usage_date, provider, user_id)
                DO UPDATE SET call_count = call_count + 1, last_updated = excluded.last_updated
                """,
                (today, provider, user_id, time.time()),
            )
            # UPSERT provider totals
            cur.execute(
                """
                INSERT INTO llm_provider_totals (usage_date, provider, total_calls, total_cost_usd)
                VALUES (?, ?, 1, ?)
                ON CONFLICT(usage_date, provider)
                DO UPDATE SET
                    total_calls = total_calls + 1,
                    total_cost_usd = total_cost_usd + excluded.total_cost_usd
                """,
                (today, provider, cost_usd),
            )
            conn.commit()
            # Read back
            user_row = conn.execute(
                "SELECT call_count FROM llm_usage WHERE usage_date = ? "
                "AND provider = ? AND user_id = ?",
                (today, provider, user_id),
            ).fetchone()
            tot_row = conn.execute(
                "SELECT total_calls FROM llm_provider_totals "
                "WHERE usage_date = ? AND provider = ?",
                (today, provider),
            ).fetchone()
        return (
            int(user_row["call_count"]) if user_row else 1,
            int(tot_row["total_calls"]) if tot_row else 1,
        )

    def reset_all(self) -> None:
        """Test helper — wipe all quota state."""
        with self._connect() as conn:
            conn.execute("DELETE FROM llm_usage")
            conn.execute("DELETE FROM llm_provider_totals")
            conn.commit()


@dataclass(frozen=True, slots=True)
class QuotaGuardedBackend(LLMBackend):
    """Wraps any LLMBackend with quota + cost enforcement.

    Args:
      inner: the LLMBackend to delegate compile() calls to
      policy: QuotaPolicy for the inner backend's provider
      store: shared QuotaStore (one per app, normally)
      user_id: identifier for per-user accounting (Streamlit
        session_id or "anonymous" if no session)

    Pre-call check:
      - Look up today's per-user count for this provider; if at limit,
        raise QuotaExhaustedError(scope="per_user")
      - Look up today's provider total; if at limit, raise
        QuotaExhaustedError(scope="total")

    Post-call:
      - Increment both counters with the policy's cost_per_call_usd

    If inner backend raises a non-quota error, do NOT increment counters
    (we only count successful calls).
    """

    provider_name: str = "quota-guarded"
    default_model: str = "delegated"
    inner: LLMBackend = field(default_factory=lambda: None)  # type: ignore[assignment]
    policy: QuotaPolicy = field(
        default_factory=lambda: QuotaPolicy("unknown", 100, 5, 0.0)
    )
    store: QuotaStore = field(default_factory=QuotaStore)
    user_id: str = "anonymous"

    def is_available(self) -> bool:
        if self.inner is None:
            return False
        if not self.inner.is_available():
            return False
        # Also unavailable if today's total quota is already exhausted
        if self.store.get_provider_total(self.policy.provider) >= self.policy.daily_total_limit:
            return False
        return True

    def compile(self, request: LLMRequest) -> LLMResponse:
        if self.inner is None:
            raise LLMBackendError(
                "QuotaGuardedBackend has no inner backend",
                provider=self.provider_name,
                retriable=False,
            )
        provider = self.policy.provider

        # Pre-call check
        user_count = self.store.get_user_count(provider, self.user_id)
        if user_count >= self.policy.daily_per_user_limit:
            raise QuotaExhaustedError(
                provider=provider,
                scope="per_user",
                limit=self.policy.daily_per_user_limit,
                current=user_count,
            )
        total_count = self.store.get_provider_total(provider)
        if total_count >= self.policy.daily_total_limit:
            raise QuotaExhaustedError(
                provider=provider,
                scope="total",
                limit=self.policy.daily_total_limit,
                current=total_count,
            )

        # Delegate
        resp = self.inner.compile(request)

        # Post-call increment (only on success)
        self.store.increment(provider, self.user_id, self.policy.cost_per_call_usd)
        return resp


def with_quota_guard(
    backend: LLMBackend,
    user_id: str = "anonymous",
    policy: QuotaPolicy | None = None,
    store: QuotaStore | None = None,
) -> QuotaGuardedBackend:
    """Convenience wrapper — picks policy from DEFAULT_POLICIES by
    provider name if not explicitly provided."""
    provider = getattr(backend, "provider_name", "unknown")
    p = policy or DEFAULT_POLICIES.get(
        provider,
        QuotaPolicy(provider=provider, daily_total_limit=100, daily_per_user_limit=5),
    )
    s = store or QuotaStore()
    return QuotaGuardedBackend(inner=backend, policy=p, store=s, user_id=user_id)
