"""v4.16 P6 — pricing tier + pre-order interest + entitlements tests.

Covers:
- PricingTier registry shape + tier_id constants
- format_tier_price for subscription / lifetime / hardware
- Currency localization via P7 integration
- Storage round-trip for Entitlement + PreorderInterest
- Aggregation helper (preorder_interest_summary)
- Schema migration v3 → v4
"""

from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import currency  # noqa: E402
import pricing  # noqa: E402
import storage  # noqa: E402


@pytest.fixture
def tmp_db() -> Path:
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp) / "test.db"


# ----- Tier registry -----


def test_tier_id_constants_consistent() -> None:
    assert pricing.TIER_SUBSCRIPTION == "subscription"
    assert pricing.TIER_LIFETIME == "lifetime"
    assert pricing.TIER_HARDWARE_BUNDLE == "hardware_bundle"


def test_pricing_tiers_count_and_ids() -> None:
    ids = pricing.list_tier_ids()
    assert ids == [
        pricing.TIER_SUBSCRIPTION,
        pricing.TIER_LIFETIME,
        pricing.TIER_HARDWARE_BUNDLE,
    ]


def test_get_tier_known_returns_dataclass() -> None:
    t = pricing.get_tier(pricing.TIER_SUBSCRIPTION)
    assert t.tier_id == "subscription"
    assert t.monthly_usd is not None


def test_get_tier_unknown_raises_keyerror() -> None:
    with pytest.raises(KeyError, match="Unknown tier_id"):
        pricing.get_tier("klingon_tier")


def test_subscription_tier_has_monthly_only() -> None:
    t = pricing.get_tier(pricing.TIER_SUBSCRIPTION)
    assert t.is_subscription
    assert not t.is_one_time
    assert t.monthly_usd is not None
    assert t.one_time_usd is None


def test_lifetime_tier_has_one_time_only() -> None:
    t = pricing.get_tier(pricing.TIER_LIFETIME)
    assert t.is_one_time
    assert not t.is_subscription
    assert t.one_time_usd is not None
    assert t.monthly_usd is None


def test_hardware_bundle_has_one_time_plus_monthly() -> None:
    t = pricing.get_tier(pricing.TIER_HARDWARE_BUNDLE)
    assert t.is_hardware_bundle
    assert t.one_time_usd is not None
    assert t.monthly_after_purchase_usd is not None


def test_no_tier_marked_available_now_yet() -> None:
    """Pre-revenue — none of the tiers should claim to be available
    for actual purchase until billing is plumbed."""
    for t in pricing.PRICING_TIERS:
        assert not t.available_now


def test_all_tiers_have_pre_order_enabled() -> None:
    """The whole point of v4.16 P6 is to capture interest, so every
    tier should be pre-order capable."""
    for t in pricing.PRICING_TIERS:
        assert t.pre_order_capture_enabled


# ----- format_tier_price -----


def test_format_subscription_price_usd() -> None:
    t = pricing.get_tier(pricing.TIER_SUBSCRIPTION)
    out = pricing.format_tier_price(t, locale=currency.LOCALE_US)
    assert "/mo" in out
    assert out.startswith("$")


def test_format_lifetime_price_usd() -> None:
    t = pricing.get_tier(pricing.TIER_LIFETIME)
    out = pricing.format_tier_price(t, locale=currency.LOCALE_US)
    assert "once" in out


def test_format_hardware_bundle_price_usd() -> None:
    t = pricing.get_tier(pricing.TIER_HARDWARE_BUNDLE)
    out = pricing.format_tier_price(t, locale=currency.LOCALE_US)
    assert "device" in out
    assert "/mo" in out


def test_format_subscription_in_cny_uses_yuan_symbol() -> None:
    t = pricing.get_tier(pricing.TIER_SUBSCRIPTION)
    out = pricing.format_tier_price(
        t, locale=currency.LOCALE_CN, approx=True,
    )
    assert "¥" in out
    assert "(approx)" in out


def test_format_usd_default_no_approx_label() -> None:
    """USD is canonical — even with approx=True we don't label it."""
    t = pricing.get_tier(pricing.TIER_LIFETIME)
    out = pricing.format_tier_price(
        t, locale=currency.LOCALE_US, approx=True,
    )
    assert "approx" not in out


# ----- Schema migration -----


def test_schema_version_at_least_4(tmp_db: Path) -> None:
    with storage.db_connect(tmp_db) as conn:
        row = conn.execute("PRAGMA user_version").fetchone()
    assert row[0] >= 4


def test_entitlements_table_exists(tmp_db: Path) -> None:
    with storage.db_connect(tmp_db) as conn:
        cur = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='entitlements'"
        )
        assert cur.fetchone() is not None


def test_preorder_interest_table_exists(tmp_db: Path) -> None:
    with storage.db_connect(tmp_db) as conn:
        cur = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='preorder_interest'"
        )
        assert cur.fetchone() is not None


def test_migration_from_v3_adds_p6_tables(tmp_db: Path) -> None:
    p = tmp_db
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    # Minimal v3 schema mock (just the version marker — full schema
    # would require all earlier tables, but we only care about the
    # ALTER/CREATE IF NOT EXISTS migration paths).
    cur.execute("PRAGMA user_version = 3")
    conn.commit()
    conn.close()
    # Reopen — P6 tables should be created.
    with storage.db_connect(tmp_db) as conn:
        for tbl in ("entitlements", "preorder_interest"):
            cur = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name=?", (tbl,),
            )
            assert cur.fetchone() is not None


# ----- Entitlement round-trip -----


def test_save_and_list_entitlement(tmp_db: Path) -> None:
    rec = storage.Entitlement(
        entitlement_id=storage.new_entitlement_id(),
        user_id="u1",
        tier_id=pricing.TIER_LIFETIME,
        granted_at=storage.now_unix(),
        expires_at=None,
        source="manual",
        notes="Founder grant",
    )
    storage.save_entitlement(rec, db_path=tmp_db)
    out = storage.list_user_entitlements("u1", db_path=tmp_db)
    assert len(out) == 1
    assert out[0].tier_id == pricing.TIER_LIFETIME
    assert out[0].expires_at is None


def test_list_entitlements_empty_when_no_user(tmp_db: Path) -> None:
    assert storage.list_user_entitlements("nobody", db_path=tmp_db) == []


def test_active_entitlement_perpetual_returns_true(tmp_db: Path) -> None:
    rec = storage.Entitlement(
        entitlement_id="e1", user_id="u1",
        tier_id=pricing.TIER_LIFETIME,
        granted_at=100.0, expires_at=None,
    )
    storage.save_entitlement(rec, db_path=tmp_db)
    assert storage.user_has_active_entitlement(
        "u1", pricing.TIER_LIFETIME,
        now_unix_ts=1000.0, db_path=tmp_db,
    )


def test_active_entitlement_expired_returns_false(tmp_db: Path) -> None:
    rec = storage.Entitlement(
        entitlement_id="e1", user_id="u1",
        tier_id=pricing.TIER_SUBSCRIPTION,
        granted_at=100.0, expires_at=200.0,
    )
    storage.save_entitlement(rec, db_path=tmp_db)
    assert not storage.user_has_active_entitlement(
        "u1", pricing.TIER_SUBSCRIPTION,
        now_unix_ts=1000.0, db_path=tmp_db,
    )


def test_active_entitlement_not_yet_expired_returns_true(tmp_db: Path) -> None:
    rec = storage.Entitlement(
        entitlement_id="e1", user_id="u1",
        tier_id=pricing.TIER_SUBSCRIPTION,
        granted_at=100.0, expires_at=2000.0,
    )
    storage.save_entitlement(rec, db_path=tmp_db)
    assert storage.user_has_active_entitlement(
        "u1", pricing.TIER_SUBSCRIPTION,
        now_unix_ts=1000.0, db_path=tmp_db,
    )


def test_active_entitlement_wrong_tier_returns_false(tmp_db: Path) -> None:
    """Holding a lifetime should not also grant subscription
    entitlement (and vice versa)."""
    rec = storage.Entitlement(
        entitlement_id="e1", user_id="u1",
        tier_id=pricing.TIER_LIFETIME,
        granted_at=100.0, expires_at=None,
    )
    storage.save_entitlement(rec, db_path=tmp_db)
    assert not storage.user_has_active_entitlement(
        "u1", pricing.TIER_SUBSCRIPTION,
        now_unix_ts=1000.0, db_path=tmp_db,
    )


# ----- PreorderInterest round-trip -----


def _interest(
    tmp_db: Path,
    user_id: str = "u1",
    tier_id: str = pricing.TIER_LIFETIME,
    amount: float = 99.0,
    ts: float | None = None,
) -> storage.PreorderInterest:
    return storage.PreorderInterest(
        interest_id=storage.new_interest_id(),
        user_id=user_id,
        tier_id=tier_id,
        expressed_at=ts if ts is not None else storage.now_unix(),
        willing_to_pay_usd=amount,
    )


def test_save_and_list_preorder_interest(tmp_db: Path) -> None:
    rec = _interest(tmp_db, amount=49.0)
    storage.save_preorder_interest(rec, db_path=tmp_db)
    out = storage.list_preorder_interest(db_path=tmp_db)
    assert len(out) == 1
    assert out[0].willing_to_pay_usd == 49.0


def test_list_preorder_filtered_by_tier(tmp_db: Path) -> None:
    storage.save_preorder_interest(
        _interest(tmp_db, tier_id=pricing.TIER_LIFETIME, amount=100.0),
        db_path=tmp_db,
    )
    storage.save_preorder_interest(
        _interest(tmp_db, tier_id=pricing.TIER_SUBSCRIPTION, amount=10.0),
        db_path=tmp_db,
    )
    out = storage.list_preorder_interest(
        tier_id=pricing.TIER_LIFETIME, db_path=tmp_db,
    )
    assert len(out) == 1
    assert out[0].tier_id == pricing.TIER_LIFETIME


def test_list_preorder_filtered_by_user(tmp_db: Path) -> None:
    storage.save_preorder_interest(
        _interest(tmp_db, user_id="a"), db_path=tmp_db,
    )
    storage.save_preorder_interest(
        _interest(tmp_db, user_id="b"), db_path=tmp_db,
    )
    out = storage.list_preorder_interest(user_id="a", db_path=tmp_db)
    assert len(out) == 1
    assert out[0].user_id == "a"


def test_list_preorder_newest_first(tmp_db: Path) -> None:
    storage.save_preorder_interest(
        _interest(tmp_db, amount=10.0, ts=100.0), db_path=tmp_db,
    )
    storage.save_preorder_interest(
        _interest(tmp_db, amount=20.0, ts=200.0), db_path=tmp_db,
    )
    out = storage.list_preorder_interest(db_path=tmp_db)
    assert out[0].willing_to_pay_usd == 20.0  # newest
    assert out[1].willing_to_pay_usd == 10.0


def test_multiple_interest_per_user_allowed(tmp_db: Path) -> None:
    """User can update mind / express interest in multiple tiers;
    no uniqueness constraint should reject."""
    storage.save_preorder_interest(
        _interest(tmp_db, user_id="u1", amount=10.0), db_path=tmp_db,
    )
    storage.save_preorder_interest(
        _interest(tmp_db, user_id="u1", amount=50.0), db_path=tmp_db,
    )
    out = storage.list_preorder_interest(user_id="u1", db_path=tmp_db)
    assert len(out) == 2


# ----- preorder_interest_summary -----


def test_summary_empty_when_no_records(tmp_db: Path) -> None:
    assert storage.preorder_interest_summary(
        pricing.TIER_LIFETIME, db_path=tmp_db,
    ) == {}


def test_summary_single_record(tmp_db: Path) -> None:
    storage.save_preorder_interest(
        _interest(tmp_db, amount=99.0), db_path=tmp_db,
    )
    s = storage.preorder_interest_summary(
        pricing.TIER_LIFETIME, db_path=tmp_db,
    )
    assert s["n"] == 1
    assert s["mean_usd"] == 99.0
    assert s["median_usd"] == 99.0
    assert s["max_usd"] == 99.0
    assert s["min_usd"] == 99.0


def test_summary_odd_count_median(tmp_db: Path) -> None:
    for amt in (10.0, 50.0, 200.0):
        storage.save_preorder_interest(
            _interest(tmp_db, amount=amt), db_path=tmp_db,
        )
    s = storage.preorder_interest_summary(
        pricing.TIER_LIFETIME, db_path=tmp_db,
    )
    assert s["n"] == 3
    assert s["median_usd"] == 50.0
    assert s["mean_usd"] == pytest.approx((10 + 50 + 200) / 3.0)
    assert s["max_usd"] == 200.0
    assert s["min_usd"] == 10.0


def test_summary_even_count_median_averages(tmp_db: Path) -> None:
    for amt in (10.0, 50.0, 80.0, 200.0):
        storage.save_preorder_interest(
            _interest(tmp_db, amount=amt), db_path=tmp_db,
        )
    s = storage.preorder_interest_summary(
        pricing.TIER_LIFETIME, db_path=tmp_db,
    )
    assert s["n"] == 4
    assert s["median_usd"] == 65.0  # (50 + 80) / 2


def test_summary_scoped_to_tier(tmp_db: Path) -> None:
    storage.save_preorder_interest(
        _interest(tmp_db, tier_id=pricing.TIER_LIFETIME, amount=100.0),
        db_path=tmp_db,
    )
    storage.save_preorder_interest(
        _interest(tmp_db, tier_id=pricing.TIER_SUBSCRIPTION, amount=10.0),
        db_path=tmp_db,
    )
    life = storage.preorder_interest_summary(
        pricing.TIER_LIFETIME, db_path=tmp_db,
    )
    sub = storage.preorder_interest_summary(
        pricing.TIER_SUBSCRIPTION, db_path=tmp_db,
    )
    assert life["mean_usd"] == 100.0
    assert sub["mean_usd"] == 10.0


# ----- Public API surface -----


def test_pricing_module_exports() -> None:
    expected = {
        "TIER_SUBSCRIPTION", "TIER_LIFETIME", "TIER_HARDWARE_BUNDLE",
        "PricingTier", "PRICING_TIERS",
        "get_tier", "list_tier_ids", "format_tier_price",
    }
    assert expected.issubset(set(pricing.__all__))


def test_pricing_module_helpers_callable() -> None:
    """Smoke check: every advertised callable is importable + callable."""
    assert callable(pricing.get_tier)
    assert callable(pricing.list_tier_ids)
    assert callable(pricing.format_tier_price)
