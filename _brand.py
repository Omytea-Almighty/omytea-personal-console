"""Brand constants for the Omytea Personal Future Console.

Single source of truth for version string, tagline, repo URL, and the
per-mode emoji palette. Imported from ``app.py`` (sidebar footer) and
``streamlit_app.py`` (Streamlit Cloud entry).

Bumping the version: change ``BRAND_VERSION`` and add a row to
``CHANGELOG_TIER2.md`` or whichever changelog the release notes pull
from. The bundle ``omytea-console.spec`` and the GitHub release tag
should match this string.

Master plan compatibility:
  - §15 Rule #11 — externally-visible copy stays provider-neutral and
    omits "fortune" / "oracle" / "算命" framing.
  - §2.6 reference-and-motivation stance — no boast claims about
    competitor performance; the tagline is descriptive only.
"""

from __future__ import annotations

BRAND_NAME: str = "Omytea Personal Future Console"
BRAND_NAME_SHORT: str = "Omytea Console"
BRAND_VERSION: str = "0.3.4"
BRAND_TAGLINE: str = (
    "Probability-calibrated decision support · local-first · open source"
)
BRAND_REPO_URL: str = "https://github.com/Adonyth/omytea-personal-console"
BRAND_PRIVACY_URL: str = (
    "https://github.com/Adonyth/omytea-personal-console/blob/main/PRIVACY_POLICY.md"
)
BRAND_HOMEPAGE: str = "https://console.omyteaai.com"
BRAND_LIVE_DEMO_URL: str = "https://omytea-personal-console.streamlit.app"

# Per-mode emoji palette. Centralised so adding a new mode is a
# one-line change across all surfaces (sidebar, page header, README).
MODE_EMOJI: dict[str, str] = {
    "New prediction": "🔮",
    "Video query": "🎥",
    "Live webcam": "📷",
    "Measurement update": "📐",
    "Calibration history": "📊",
    "Pricing & pre-order": "💳",
}


def footer_markdown() -> str:
    """Return a single-line markdown footer for the sidebar / main pane.

    The footer is the project's *only* place where the version string,
    repo URL, and privacy link converge — every other reference should
    import from this module."""
    return (
        f"**{BRAND_NAME_SHORT}** v{BRAND_VERSION} · "
        f"[GitHub]({BRAND_REPO_URL}) · "
        f"[Privacy]({BRAND_PRIVACY_URL}) · "
        f"[Home]({BRAND_HOMEPAGE})"
    )


def emoji_for(mode: str) -> str:
    """Lookup the canonical emoji for a mode. Falls back to a neutral
    bullet if a mode name isn't recognised — keeps the UI from
    breaking when modes are added before MODE_EMOJI is updated."""
    return MODE_EMOJI.get(mode, "•")


__all__ = [
    "BRAND_NAME",
    "BRAND_NAME_SHORT",
    "BRAND_VERSION",
    "BRAND_TAGLINE",
    "BRAND_REPO_URL",
    "BRAND_PRIVACY_URL",
    "BRAND_HOMEPAGE",
    "BRAND_LIVE_DEMO_URL",
    "MODE_EMOJI",
    "footer_markdown",
    "emoji_for",
]
