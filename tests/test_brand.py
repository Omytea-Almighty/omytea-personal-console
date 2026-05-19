"""Tests for the brand-constants module.

Smoke checks that the single source of truth is wired and that
externally-visible copy stays compliant with master plan §15 Rule #11
(provider-neutral) + §2.9 negative scope (no fortune / oracle framing).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import _brand


def test_brand_constants_are_nonempty_strings() -> None:
    for name in (
        "BRAND_NAME", "BRAND_NAME_SHORT", "BRAND_VERSION",
        "BRAND_TAGLINE", "BRAND_REPO_URL", "BRAND_PRIVACY_URL",
        "BRAND_HOMEPAGE",
    ):
        val = getattr(_brand, name)
        assert isinstance(val, str) and val.strip(), f"{name} must be non-empty"


def test_version_string_is_semver_ish() -> None:
    """Version should match major.minor.patch with optional -tag suffix."""
    assert re.match(
        r"^\d+\.\d+\.\d+(-[A-Za-z0-9.]+)?$", _brand.BRAND_VERSION
    ), f"version '{_brand.BRAND_VERSION}' is not semver-shaped"


def test_repo_url_points_to_public_repo() -> None:
    assert "Adonyth/omytea-personal-console" in _brand.BRAND_REPO_URL


def test_footer_markdown_includes_version_and_links() -> None:
    md = _brand.footer_markdown()
    assert _brand.BRAND_VERSION in md
    assert "GitHub" in md
    assert "Privacy" in md


def test_mode_emoji_covers_all_modes() -> None:
    expected_modes = {
        "New prediction", "Video query", "Live webcam",
        "Measurement update", "Calibration history",
        "Pricing & pre-order",
    }
    assert set(_brand.MODE_EMOJI.keys()) >= expected_modes, (
        "Every sidebar mode must have a registered emoji"
    )


def test_emoji_for_unknown_mode_returns_neutral_fallback() -> None:
    assert _brand.emoji_for("nonexistent mode") == "•"


def test_no_forbidden_copy_in_tagline() -> None:
    """Master plan §2.9 negative scope: no oracle / fortune / 算命
    framing in external copy."""
    tagline = _brand.BRAND_TAGLINE.lower()
    forbidden = ("oracle", "fortune", "算命", "命運", "运势")
    for word in forbidden:
        assert word.lower() not in tagline, (
            f"Tagline must not include '{word}'"
        )


def test_no_provider_lockin_in_tagline() -> None:
    """Master plan §15 Rule #11: external copy should not lock in a
    single LLM vendor."""
    tagline = _brand.BRAND_TAGLINE.lower()
    forbidden_vendors = ("openai", "claude", "gemini-only", "groq-only")
    for word in forbidden_vendors:
        assert word not in tagline, f"Tagline must not lock to '{word}'"
