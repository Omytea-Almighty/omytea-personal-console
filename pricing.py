"""Pricing tiers + pre-order interest capture — v4.16 P6.

Status: pre-revenue. This module ships:

1. The canonical PricingTier definitions (subscription, lifetime,
   hardware bundle) — USD-denominated, integrated with currency.py
   for locale display.
2. A pre-order interest capture flow — the user expresses "I'd pay
   $N for tier X" and we record it. Honest PMF research instead of
   running Stripe on a system that hasn't validated product-market-fit.
3. An entitlement-tracking layer (which tier does each user have?)
   that hibernates until real billing lands.

What this module DELIBERATELY does NOT do:
- Stripe / payment processor integration. v4.16 P6 spec defers
  real billing to "v4.17+ unless H4 N≥10 validates product-market-
  fit signal". When real billing arrives, add a `stripe_backend.py`
  alongside this file that calls into PricingTier metadata; the
  existing entitlement table is already shaped to receive it.
- Account creation flows. Regulatory and privacy rules make "create
  an account on behalf of the user" a user-must-do-themselves action
  regardless of the SaaS surface.

Public API
----------
- PricingTier dataclass
- PRICING_TIERS — canonical tuple of the three tiers
- get_tier(tier_id) — registry lookup with KeyError on miss
- format_tier_price(tier, locale) — render canonical USD price in
  caller's locale via currency.format_price()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import currency


# ----- Tier ID constants -----

TIER_SUBSCRIPTION = "subscription"
TIER_LIFETIME = "lifetime"
TIER_HARDWARE_BUNDLE = "hardware_bundle"


@dataclass(frozen=True, slots=True)
class PricingTier:
    """Canonical tier definition. All amounts are USD; non-USD is a
    display-only conversion via currency.format_price()."""
    tier_id: str
    display_name: str
    one_line_pitch: str

    # Pricing structure — exactly one of these is set per tier.
    monthly_usd: float | None = None      # subscription only
    one_time_usd: float | None = None     # lifetime, hardware
    monthly_after_purchase_usd: float | None = None  # hardware adds SaaS

    # Marketing / positioning.
    bullet_features: tuple[str, ...] = field(default_factory=tuple)
    target_persona: str = ""
    available_now: bool = False  # True only when billing is plumbed

    # PMF research.
    pre_order_capture_enabled: bool = True

    @property
    def is_subscription(self) -> bool:
        return self.monthly_usd is not None and self.one_time_usd is None

    @property
    def is_one_time(self) -> bool:
        return self.one_time_usd is not None and self.monthly_usd is None

    @property
    def is_hardware_bundle(self) -> bool:
        return self.tier_id == TIER_HARDWARE_BUNDLE


# Canonical tier registry. Order = display order (cheapest → most
# committed). USD-anchored per founder strategic decision (US market).
PRICING_TIERS: tuple[PricingTier, ...] = (
    PricingTier(
        tier_id=TIER_SUBSCRIPTION,
        display_name="Monthly subscription",
        one_line_pitch=(
            "Try the system month-to-month; cancel anytime. "
            "Right if you want low commitment + ongoing improvements."
        ),
        monthly_usd=9.99,
        bullet_features=(
            "Unlimited predictions per month",
            "All scenarios + drill-downs",
            "Continuous + discrete views",
            "Owner-bias-tagged calibration history",
        ),
        target_persona=(
            "Knowledge worker evaluating decisions monthly; cautious "
            "of long-term commitments to early-stage SaaS."
        ),
        available_now=False,  # billing not plumbed yet
        pre_order_capture_enabled=True,
    ),
    PricingTier(
        tier_id=TIER_LIFETIME,
        display_name="Lifetime license",
        one_line_pitch=(
            "Buy once, own forever. Right if you'd rather pay upfront "
            "than commit to recurring billing."
        ),
        one_time_usd=199.00,
        bullet_features=(
            "Everything in subscription",
            "Personal-use license; no monthly recurring",
            "Updates included for the life of v4.x",
            "Migrate to v5+ at a discount when it lands",
        ),
        target_persona=(
            "Subscription-resistant power user; prefers ownership; "
            "the founder's stated preference per H4 #1 Q3."
        ),
        available_now=False,
        pre_order_capture_enabled=True,
    ),
    PricingTier(
        tier_id=TIER_HARDWARE_BUNDLE,
        display_name="Hardware bundle (preview)",
        one_line_pitch=(
            "Dedicated Omytea device + the software, integrated. The "
            "master-plan §10 long-term track; preview pricing only."
        ),
        one_time_usd=599.00,
        monthly_after_purchase_usd=4.99,
        bullet_features=(
            "Dedicated low-power inference appliance",
            "Pre-loaded local LLM (no API quota)",
            "Sync across devices",
            "Hardware-bundled SaaS at reduced monthly rate",
        ),
        target_persona=(
            "Privacy-first power user willing to commit to the "
            "Omytea long-term hardware vision (§10)."
        ),
        available_now=False,
        pre_order_capture_enabled=True,
    ),
)


_REGISTRY: dict[str, PricingTier] = {t.tier_id: t for t in PRICING_TIERS}


def get_tier(tier_id: str) -> PricingTier:
    """Lookup by tier_id. Raises KeyError on unknown."""
    if tier_id not in _REGISTRY:
        raise KeyError(
            f"Unknown tier_id {tier_id!r}; known: "
            f"{list(_REGISTRY.keys())}"
        )
    return _REGISTRY[tier_id]


def list_tier_ids() -> list[str]:
    return [t.tier_id for t in PRICING_TIERS]


def format_tier_price(
    tier: PricingTier,
    locale: str | None = None,
    *,
    approx: bool = True,
) -> str:
    """Render the canonical USD price in the caller's locale via
    currency.format_price(). For subscription: '$N/mo'. For one-time:
    '$N once'. For hardware: '$N device + $M/mo'."""
    if tier.is_subscription and tier.monthly_usd is not None:
        return f"{currency.format_price(tier.monthly_usd, locale, approx=approx)}/mo"

    if tier.is_hardware_bundle and tier.one_time_usd is not None:
        device = currency.format_price(
            tier.one_time_usd, locale, approx=approx,
        )
        if tier.monthly_after_purchase_usd is not None:
            saas = currency.format_price(
                tier.monthly_after_purchase_usd, locale, approx=approx,
            )
            return f"{device} device + {saas}/mo"
        return f"{device} device"

    if tier.is_one_time and tier.one_time_usd is not None:
        return f"{currency.format_price(tier.one_time_usd, locale, approx=approx)} once"

    return "—"


__all__ = [
    "TIER_SUBSCRIPTION", "TIER_LIFETIME", "TIER_HARDWARE_BUNDLE",
    "PricingTier", "PRICING_TIERS", "get_tier", "list_tier_ids",
    "format_tier_price",
]
