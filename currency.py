"""Currency localization utility — v4.16 P7.

Centralizes price/currency formatting so the UI, docs, and self-test
materials all converge on the same default (USD for the US market) and
the same opt-in path for other locales (CNY for early Chinese-language
testers, EUR / GBP / JPY for EU+UK+JP).

Why this exists: H4 data point #1 (founder, 2026-05-18) flagged that
v4.15 MVP self-test materials referenced "RMB/month" pay-willingness
amounts while the actual target market is the US. The fix is bigger
than search-and-replace: any future pricing UI (P6 buy-out + lifetime)
needs locale-aware formatting from day one, not a retrofit.

Public API
----------
- ``Locale`` enum-ish constants
- ``detect_locale()``: best-effort locale detection (env / browser /
  default)
- ``format_price(usd_amount, locale=None)``: USD canonical → localized
  string with symbol + thousands separator + decimals
- ``convert_usd(usd_amount, locale)``: USD → local-unit float (uses
  conservative reference rates; intentionally not live FX)
- ``REFERENCE_RATES``: dict[locale → multiplier vs USD]

The reference rates are intentionally static + conservative — this is
not a forex service, just a localization aid. UI should label
displayed-non-USD amounts as "approximate" so users know the canonical
SaaS pricing is USD.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


# Canonical locale codes. UI may accept lower-case / alt forms via
# normalize_locale().
LOCALE_US = "en_US"
LOCALE_CN = "zh_CN"
LOCALE_EU = "en_EU"
LOCALE_GB = "en_GB"
LOCALE_JP = "ja_JP"

SUPPORTED_LOCALES: tuple[str, ...] = (
    LOCALE_US, LOCALE_CN, LOCALE_EU, LOCALE_GB, LOCALE_JP,
)

DEFAULT_LOCALE = LOCALE_US  # US market — per founder strategic decision.


# ----- Currency metadata per locale -----


@dataclass(frozen=True, slots=True)
class CurrencyMeta:
    """Per-locale currency display metadata."""
    code: str            # ISO 4217 (USD / CNY / EUR / GBP / JPY)
    symbol: str          # $ / ¥ / € / £ / ¥
    decimal_places: int  # 2 for most, 0 for JPY
    name_en: str         # "US Dollar" / "Chinese Yuan" / etc.
    rate_per_usd: float  # 1 USD ≈ N local-unit (conservative reference)


# Conservative static reference rates — NOT live FX. Rounded for
# readability. Update via a periodic vendor refresh if/when SaaS
# pricing actually goes multi-currency; until then these are display
# aids and the canonical billing currency stays USD.
CURRENCY_BY_LOCALE: dict[str, CurrencyMeta] = {
    LOCALE_US: CurrencyMeta(
        code="USD", symbol="$", decimal_places=2,
        name_en="US Dollar", rate_per_usd=1.00,
    ),
    LOCALE_CN: CurrencyMeta(
        code="CNY", symbol="¥", decimal_places=2,
        name_en="Chinese Yuan", rate_per_usd=7.20,
    ),
    LOCALE_EU: CurrencyMeta(
        code="EUR", symbol="€", decimal_places=2,
        name_en="Euro", rate_per_usd=0.92,
    ),
    LOCALE_GB: CurrencyMeta(
        code="GBP", symbol="£", decimal_places=2,
        name_en="British Pound", rate_per_usd=0.79,
    ),
    LOCALE_JP: CurrencyMeta(
        code="JPY", symbol="¥", decimal_places=0,
        name_en="Japanese Yen", rate_per_usd=155.0,
    ),
}


# Backward-compat reference table (keeps "REFERENCE_RATES" public name).
REFERENCE_RATES: dict[str, float] = {
    locale: meta.rate_per_usd
    for locale, meta in CURRENCY_BY_LOCALE.items()
}


# ----- Locale normalization + detection -----


def normalize_locale(raw: str | None) -> str:
    """Coerce a free-form locale string into one of SUPPORTED_LOCALES.

    Falls back to DEFAULT_LOCALE on unrecognized input. Handles common
    variations: ``"en-US"`` / ``"en_us"`` / ``"US"`` / ``"USA"`` /
    ``"zh"`` / ``"chinese"`` / ``"de_DE"`` / ``"fr"`` / ``"jp"`` etc.
    """
    if not raw:
        return DEFAULT_LOCALE
    s = raw.strip().lower().replace("-", "_")

    # Exact match against supported set (case-insensitive).
    for canonical in SUPPORTED_LOCALES:
        if s == canonical.lower():
            return canonical

    # Country-code shortcuts.
    country_aliases = {
        "us": LOCALE_US, "usa": LOCALE_US, "en": LOCALE_US,
        "cn": LOCALE_CN, "zh": LOCALE_CN, "chinese": LOCALE_CN,
        "china": LOCALE_CN, "zh_cn": LOCALE_CN, "zh_hans": LOCALE_CN,
        "eu": LOCALE_EU, "de": LOCALE_EU, "fr": LOCALE_EU,
        "es": LOCALE_EU, "it": LOCALE_EU, "nl": LOCALE_EU, "pt": LOCALE_EU,
        "de_de": LOCALE_EU, "fr_fr": LOCALE_EU, "es_es": LOCALE_EU,
        "gb": LOCALE_GB, "uk": LOCALE_GB, "en_gb": LOCALE_GB,
        "jp": LOCALE_JP, "ja": LOCALE_JP, "ja_jp": LOCALE_JP,
        "japanese": LOCALE_JP,
    }
    if s in country_aliases:
        return country_aliases[s]

    # Try the "lang_country" → "country" shortcut.
    if "_" in s:
        country = s.split("_", 1)[1]
        if country in country_aliases:
            return country_aliases[country]

    return DEFAULT_LOCALE


def detect_locale(
    accept_language: str | None = None,
    env_var_name: str = "OMYTEA_CONSOLE_LOCALE",
) -> str:
    """Best-effort locale detection.

    Priority order:
      1. Explicit env var ``OMYTEA_CONSOLE_LOCALE`` (operator override)
      2. ``accept_language`` (HTTP header / browser navigator.language)
      3. DEFAULT_LOCALE (en_US — the US market default)

    Returns a value from SUPPORTED_LOCALES.
    """
    explicit = os.environ.get(env_var_name, "").strip()
    if explicit:
        return normalize_locale(explicit)
    if accept_language:
        # Accept-Language header may carry quality scores ("en-US,en;q=0.9").
        # Take the first language token.
        first = accept_language.split(",", 1)[0]
        first = first.split(";", 1)[0]
        return normalize_locale(first)
    return DEFAULT_LOCALE


# ----- Formatting -----


def convert_usd(usd_amount: float, locale: str | None = None) -> float:
    """Convert a USD amount to the locale's currency unit.

    Uses static REFERENCE_RATES. Not for billing — display aid only.
    """
    loc = normalize_locale(locale)
    rate = CURRENCY_BY_LOCALE[loc].rate_per_usd
    return usd_amount * rate


def format_price(
    usd_amount: float,
    locale: str | None = None,
    *,
    include_code: bool = False,
    approx: bool = False,
) -> str:
    """Format a USD amount as a locale-appropriate price string.

    Args:
      usd_amount: canonical USD value (we always store + reason in USD).
      locale: target locale; defaults to detect_locale() (typically
        ``en_US``).
      include_code: append ISO code (e.g. ``"$10.00 USD"``) — useful in
        marketing copy where ambiguity has cost.
      approx: prefix with ``"≈"`` and suffix with ``"(approx)"`` — for
        non-USD displays where the rate is a static reference, not live.

    Returns the formatted string. JPY drops decimals; all other
    locales use two decimals.
    """
    loc = normalize_locale(locale)
    meta = CURRENCY_BY_LOCALE[loc]
    converted = usd_amount * meta.rate_per_usd

    if meta.decimal_places == 0:
        # Yen-style: integer rounding, thousands separator.
        body = f"{meta.symbol}{converted:,.0f}"
    else:
        body = f"{meta.symbol}{converted:,.{meta.decimal_places}f}"

    if include_code:
        body = f"{body} {meta.code}"

    if approx and loc != LOCALE_US:
        body = f"≈ {body} (approx)"

    return body


def format_price_range(
    usd_low: float, usd_high: float,
    locale: str | None = None,
    *,
    include_code: bool = False,
    approx: bool = False,
) -> str:
    """Format a USD low–high range. Calls format_price() twice + joins
    with a single en-dash; locale + flags apply to both ends."""
    low = format_price(usd_low, locale,
                       include_code=False, approx=False)
    # For the high end, drop the duplicate symbol and add code if asked.
    meta = CURRENCY_BY_LOCALE[normalize_locale(locale)]
    converted_high = usd_high * meta.rate_per_usd
    if meta.decimal_places == 0:
        high_body = f"{converted_high:,.0f}"
    else:
        high_body = f"{converted_high:,.{meta.decimal_places}f}"
    body = f"{low}–{meta.symbol}{high_body}"
    if include_code:
        body = f"{body} {meta.code}"
    if approx and normalize_locale(locale) != LOCALE_US:
        body = f"≈ {body} (approx)"
    return body


# Canonical USD self-test pay-willingness anchor amounts. These are the
# values self-test materials should reference. Anchored to typical
# personal-productivity SaaS ($5-$20/month) + lifetime ($99-$199).
PAY_WILLINGNESS_USD_ANCHORS: tuple[float, ...] = (
    0.0,    # not willing
    1.50,   # token amount (was 10 RMB)
    5.00,   # entry SaaS (was 30 RMB)
    10.00,  # mid SaaS (was 50 RMB)
    20.00,  # premium SaaS (was 100 RMB)
    50.00,  # power-user SaaS (was 200 RMB)
    75.0,   # power-user+ (was 500 RMB)
)


__all__ = [
    "LOCALE_US", "LOCALE_CN", "LOCALE_EU", "LOCALE_GB", "LOCALE_JP",
    "SUPPORTED_LOCALES", "DEFAULT_LOCALE",
    "CurrencyMeta", "CURRENCY_BY_LOCALE", "REFERENCE_RATES",
    "normalize_locale", "detect_locale",
    "convert_usd", "format_price", "format_price_range",
    "PAY_WILLINGNESS_USD_ANCHORS",
]
