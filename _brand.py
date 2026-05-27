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
BRAND_VERSION: str = "0.4.2"
BRAND_TAGLINE: str = (
    "Probability-calibrated decision support · local-first · open source"
)
BRAND_REPO_URL: str = "https://github.com/Adonyth/omytea-personal-console"
BRAND_PRIVACY_URL: str = (
    "https://github.com/Adonyth/omytea-personal-console/blob/main/PRIVACY_POLICY.md"
)
BRAND_LIVE_DEMO_URL: str = "https://omytea-personal-console.streamlit.app"
# Iter #20: Streamlit Cloud's ?embed=true URL parameter hides the
# outer-page chrome (the "Manage app" pill, the Streamlit-Cloud
# header) that iter 18's components.html JS hop failed to reach. The
# bottom-bar reduces to a tiny "Built with Streamlit" + "Fullscreen"
# link — much cleaner first-paint for a public demo. Live-verified:
# document.querySelector('[data-testid="manage-app-button"]') →
# NO_PILL on the ?embed=true URL.
#
# BRAND_PUBLIC_URL is what every externally-visible link points at
# (footer Home link, README, GitHub repo homepage). BRAND_LIVE_DEMO_URL
# kept as the bare URL for code that needs the canonical without the
# embed-mode hint (e.g. share links, analytics).
BRAND_PUBLIC_URL: str = f"{BRAND_LIVE_DEMO_URL}/?embed=true"
# P0 (bug-037 audit follow-up): the previous BRAND_HOMEPAGE pointed at
# https://console.omyteaai.com — that subdomain returns a TLS-cert
# mismatch and the apex https://omyteaai.com returns Cloudflare 520.
# Footer Home link now uses the cleaner ?embed=true URL so users who
# click Home land on the chrome-free version.
BRAND_HOMEPAGE: str = BRAND_PUBLIC_URL

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


def footer_html() -> str:
    """Return the footer as an HTML fragment (links + bold rendered).

    ``footer_markdown()`` is correct only when handed to a markdown
    renderer. When the footer is interpolated into a raw ``<div>`` block
    passed to ``st.markdown(..., unsafe_allow_html=True)``, Streamlit does
    not re-parse the markdown — ``**bold**`` and ``[label](url)`` would
    render literally. This variant emits the same content as HTML so the
    sidebar footer renders correctly."""
    return (
        f"<strong>{BRAND_NAME_SHORT}</strong> v{BRAND_VERSION} · "
        f'<a href="{BRAND_REPO_URL}" target="_blank">GitHub</a> · '
        f'<a href="{BRAND_PRIVACY_URL}" target="_blank">Privacy</a> · '
        f'<a href="{BRAND_HOMEPAGE}" target="_blank">Home</a>'
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
    "BRAND_PUBLIC_URL",
    "MODE_EMOJI",
    "footer_markdown",
    "footer_html",
    "emoji_for",
]
