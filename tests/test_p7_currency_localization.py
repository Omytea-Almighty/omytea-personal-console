"""v4.16 P7 — currency localization tests.

Coverage:
- Locale normalization (US default, common aliases)
- detect_locale env-var + Accept-Language fallback chain
- USD canonical conversion via static reference rates
- format_price / format_price_range with locale + flags
- PAY_WILLINGNESS_USD_ANCHORS sanity
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import currency  # noqa: E402
from currency import (  # noqa: E402
    CURRENCY_BY_LOCALE,
    DEFAULT_LOCALE,
    LOCALE_CN,
    LOCALE_EU,
    LOCALE_GB,
    LOCALE_JP,
    LOCALE_US,
    PAY_WILLINGNESS_USD_ANCHORS,
    REFERENCE_RATES,
    SUPPORTED_LOCALES,
    convert_usd,
    detect_locale,
    format_price,
    format_price_range,
    normalize_locale,
)


@pytest.fixture(autouse=True)
def _clean_locale_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each test gets a clean OMYTEA_CONSOLE_LOCALE env."""
    monkeypatch.delenv("OMYTEA_CONSOLE_LOCALE", raising=False)


# ----- Default + structure -----


def test_default_locale_is_us() -> None:
    """Per founder strategic decision: US market is the default."""
    assert DEFAULT_LOCALE == LOCALE_US


def test_supported_locales_includes_5_canonical() -> None:
    assert set(SUPPORTED_LOCALES) == {
        LOCALE_US, LOCALE_CN, LOCALE_EU, LOCALE_GB, LOCALE_JP,
    }


def test_currency_meta_has_all_supported_locales() -> None:
    for loc in SUPPORTED_LOCALES:
        assert loc in CURRENCY_BY_LOCALE
        meta = CURRENCY_BY_LOCALE[loc]
        assert meta.code  # ISO 4217
        assert meta.symbol
        assert meta.decimal_places in (0, 2)
        assert meta.rate_per_usd > 0


def test_reference_rates_mirrors_currency_by_locale() -> None:
    for loc in SUPPORTED_LOCALES:
        assert REFERENCE_RATES[loc] == CURRENCY_BY_LOCALE[loc].rate_per_usd


def test_usd_rate_is_one_to_one() -> None:
    """USD → USD must be exactly 1.0."""
    assert CURRENCY_BY_LOCALE[LOCALE_US].rate_per_usd == 1.0


# ----- normalize_locale -----


def test_normalize_empty_returns_default() -> None:
    assert normalize_locale(None) == DEFAULT_LOCALE
    assert normalize_locale("") == DEFAULT_LOCALE
    assert normalize_locale("   ") == DEFAULT_LOCALE


def test_normalize_canonical_passes_through() -> None:
    for loc in SUPPORTED_LOCALES:
        assert normalize_locale(loc) == loc


def test_normalize_case_insensitive() -> None:
    assert normalize_locale("EN_US") == LOCALE_US
    assert normalize_locale("zh_cn") == LOCALE_CN


def test_normalize_handles_hyphen_form() -> None:
    """Browser navigator.language sends 'en-US' not 'en_US'."""
    assert normalize_locale("en-US") == LOCALE_US
    assert normalize_locale("zh-CN") == LOCALE_CN


def test_normalize_country_aliases() -> None:
    assert normalize_locale("us") == LOCALE_US
    assert normalize_locale("USA") == LOCALE_US
    assert normalize_locale("cn") == LOCALE_CN
    assert normalize_locale("china") == LOCALE_CN
    assert normalize_locale("gb") == LOCALE_GB
    assert normalize_locale("uk") == LOCALE_GB
    assert normalize_locale("jp") == LOCALE_JP
    assert normalize_locale("japanese") == LOCALE_JP


def test_normalize_european_languages_collapse_to_eu() -> None:
    assert normalize_locale("de") == LOCALE_EU
    assert normalize_locale("de_DE") == LOCALE_EU
    assert normalize_locale("fr") == LOCALE_EU
    assert normalize_locale("es_ES") == LOCALE_EU
    assert normalize_locale("nl") == LOCALE_EU


def test_normalize_unknown_falls_back_to_default() -> None:
    assert normalize_locale("klingon") == DEFAULT_LOCALE
    assert normalize_locale("xx_YY") == DEFAULT_LOCALE


# ----- detect_locale -----


def test_detect_locale_default_without_signals() -> None:
    assert detect_locale() == DEFAULT_LOCALE


def test_detect_locale_env_var_wins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OMYTEA_CONSOLE_LOCALE", "zh_CN")
    assert detect_locale() == LOCALE_CN


def test_detect_locale_env_var_beats_accept_language(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OMYTEA_CONSOLE_LOCALE", "ja_JP")
    # Accept-Language says EN-US, but env override wins.
    assert detect_locale(accept_language="en-US,en;q=0.9") == LOCALE_JP


def test_detect_locale_accept_language_first_token() -> None:
    assert detect_locale(accept_language="en-US,en;q=0.9") == LOCALE_US
    assert detect_locale(accept_language="zh-CN,zh;q=0.9,en;q=0.5") == LOCALE_CN
    assert detect_locale(accept_language="de-DE,de;q=0.9") == LOCALE_EU


def test_detect_locale_empty_env_falls_through() -> None:
    """An empty env var should not override accept_language."""
    os.environ["OMYTEA_CONSOLE_LOCALE"] = "   "  # whitespace
    try:
        assert detect_locale(accept_language="ja_JP") == LOCALE_JP
    finally:
        del os.environ["OMYTEA_CONSOLE_LOCALE"]


# ----- convert_usd -----


def test_convert_usd_to_usd_is_identity() -> None:
    assert convert_usd(10.00, LOCALE_US) == 10.00


def test_convert_usd_to_cny_uses_reference_rate() -> None:
    expected = 10.00 * CURRENCY_BY_LOCALE[LOCALE_CN].rate_per_usd
    assert convert_usd(10.00, LOCALE_CN) == pytest.approx(expected)


def test_convert_usd_handles_zero() -> None:
    for loc in SUPPORTED_LOCALES:
        assert convert_usd(0.0, loc) == 0.0


def test_convert_usd_default_locale_when_none() -> None:
    assert convert_usd(5.00, None) == 5.00


# ----- format_price -----


def test_format_price_usd_basic() -> None:
    assert format_price(10.00, LOCALE_US) == "$10.00"
    assert format_price(0.99, LOCALE_US) == "$0.99"


def test_format_price_thousands_separator() -> None:
    assert format_price(1234.50, LOCALE_US) == "$1,234.50"


def test_format_price_cny_uses_yuan_symbol() -> None:
    out = format_price(10.00, LOCALE_CN)
    assert out.startswith("¥")
    # 10 USD ≈ 72 CNY (rate 7.20)
    assert "72.00" in out


def test_format_price_jpy_drops_decimals() -> None:
    out = format_price(10.00, LOCALE_JP)
    assert "." not in out
    assert out.startswith("¥")


def test_format_price_include_code() -> None:
    assert format_price(10.00, LOCALE_US, include_code=True) == "$10.00 USD"
    out = format_price(10.00, LOCALE_CN, include_code=True)
    assert out.endswith("CNY")


def test_format_price_approx_flag_prefixes_for_non_usd() -> None:
    out = format_price(10.00, LOCALE_CN, approx=True)
    assert out.startswith("≈ ")
    assert out.endswith("(approx)")


def test_format_price_approx_flag_noop_for_usd() -> None:
    """USD is canonical — never label it 'approx'."""
    out = format_price(10.00, LOCALE_US, approx=True)
    assert "approx" not in out
    assert not out.startswith("≈")


def test_format_price_default_locale_when_none() -> None:
    """No locale argument → US default."""
    assert format_price(10.00) == "$10.00"


def test_format_price_negative_amount_renders() -> None:
    """Negative numbers are valid (refunds / deltas)."""
    out = format_price(-5.00, LOCALE_US)
    assert "5.00" in out
    assert out.startswith("$-") or out.startswith("-$")


# ----- format_price_range -----


def test_format_price_range_usd_basic() -> None:
    out = format_price_range(5.00, 10.00, LOCALE_US)
    assert out == "$5.00–$10.00"


def test_format_price_range_jpy_drops_decimals_both_sides() -> None:
    out = format_price_range(5.00, 10.00, LOCALE_JP)
    assert "." not in out
    assert "–" in out


def test_format_price_range_with_code_appended_once() -> None:
    out = format_price_range(5.00, 10.00, LOCALE_US, include_code=True)
    # The code should only appear once, at the end.
    assert out.count("USD") == 1
    assert out.endswith("USD")


def test_format_price_range_approx_flag() -> None:
    out = format_price_range(5.00, 10.00, LOCALE_CN, approx=True)
    assert out.startswith("≈ ")
    assert out.endswith("(approx)")


# ----- PAY_WILLINGNESS_USD_ANCHORS -----


def test_pay_willingness_anchors_are_usd() -> None:
    """Anchors must be ordered + reasonable for US SaaS personal-tool
    pricing range."""
    assert PAY_WILLINGNESS_USD_ANCHORS[0] == 0.0
    assert PAY_WILLINGNESS_USD_ANCHORS[-1] >= 50.0
    # Strictly increasing.
    for i in range(len(PAY_WILLINGNESS_USD_ANCHORS) - 1):
        assert (PAY_WILLINGNESS_USD_ANCHORS[i]
                < PAY_WILLINGNESS_USD_ANCHORS[i + 1])


def test_pay_willingness_anchors_formattable() -> None:
    """Every anchor formats cleanly in US locale."""
    for amount in PAY_WILLINGNESS_USD_ANCHORS:
        s = format_price(amount, LOCALE_US)
        assert s.startswith("$")
        assert "." in s  # decimal places


# ----- Module exports -----


def test_currency_module_exports_public_api() -> None:
    """The advertised __all__ must cover every public name the rest of
    the codebase depends on."""
    expected = {
        "LOCALE_US", "LOCALE_CN", "LOCALE_EU", "LOCALE_GB", "LOCALE_JP",
        "SUPPORTED_LOCALES", "DEFAULT_LOCALE",
        "CurrencyMeta", "CURRENCY_BY_LOCALE", "REFERENCE_RATES",
        "normalize_locale", "detect_locale",
        "convert_usd", "format_price", "format_price_range",
        "PAY_WILLINGNESS_USD_ANCHORS",
    }
    assert expected.issubset(set(currency.__all__))
