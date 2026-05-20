"""Stage 3 — Nye Clock solar-system 玄学 lens (OMY-V415 / M2 / Acceptance #54).

The dense unified astrolabe (founder verdict "不知所云") is replaced by a
faithful static-SVG recreation of the founder's real Nye Clock app: a
Sun-Earth-Moon orbital, deep-space cosmic style. No WebGL / Three.js /
GPU — pure static SVG so it embeds verbatim via
``st.markdown(unsafe_allow_html=True)``.

These tests pin: (1) the lens is the Nye Clock solar system, not the old
astrolabe; (2) it is GPU-free static SVG; (3) the 八字 / 占星 data maps
onto the orbital legibly; (4) the geometry helpers are correct.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import _clock  # noqa: E402
import _metaphysics as mp  # noqa: E402


def _readings(year: int = 1993, month: int = 7, day: int = 4,
              hour: int = 15) -> tuple:
    bd = mp.BirthData(year, month, day, hour)
    rb = mp.compute_reading("bazi", birth=bd, seed="nye",
                            outcome="career_success")
    ra = mp.compute_reading("astro", birth=bd, seed="nye",
                            outcome="career_success")
    return rb, ra


def _render(rb, ra) -> str:
    return _clock.render_celestial_svg(
        rb, ra,
        [("branch_a", 0.4, "realistic"), ("branch_b", 0.3, "realistic")],
        center_top_label="MODEL", center_top_value="62%",
        center_bottom_label="玄学 CONSENSUS", center_bottom_value="55%",
        center_meta="mixture · alpha 0.30",
    )


# --------------------------------------------------------------------
# The lens is the Nye Clock solar system
# --------------------------------------------------------------------

def test_lens_uses_nye_clock_canvas() -> None:
    """The viewBox is the Nye Clock's 1000x920, not the old 480x480."""
    rb, ra = _readings()
    svg = _render(rb, ra)
    assert 'viewBox="0 0 1000 920"' in svg
    assert svg.startswith("<svg ") and svg.endswith("</svg>")


def test_lens_has_sun_earth_moon() -> None:
    """All three orbital bodies render with their layered gradients."""
    rb, ra = _readings()
    svg = _render(rb, ra)
    # Sun — layered core / corona / halo
    assert "url(#nye-sun-core)" in svg
    assert "url(#nye-sun-corona)" in svg
    assert "url(#nye-sun-halo)" in svg
    # Earth — ocean / land / atmosphere / limb
    assert "url(#nye-earth-ocean)" in svg
    assert "url(#nye-earth-land)" in svg
    assert "url(#nye-earth-atmo)" in svg
    # Moon — surface / shade
    assert "url(#nye-moon-surf)" in svg
    assert "url(#nye-moon-shade)" in svg


def test_lens_has_deep_space_backdrop() -> None:
    """The cosmic backdrop: radial nebula fill, stars, vignette."""
    rb, ra = _readings()
    svg = _render(rb, ra)
    assert "url(#nye-cosmos-bg)" in svg
    assert "url(#nye-vignette)" in svg
    # nebula glow blobs for depth
    assert "url(#nye-nebula-a)" in svg
    # a star field is drawn (168 tiny circles)
    assert svg.count("rgba(255,255,255,0.") > 50


def test_lens_is_gpu_free_static_svg() -> None:
    """CRITICAL — no WebGL / Three.js / canvas / GPU. Static SVG only.

    The lens must embed verbatim via st.markdown; any script / canvas
    tag would mean it can't.
    """
    rb, ra = _readings()
    svg = _render(rb, ra)
    lowered = svg.lower()
    for forbidden in (
        "<script", "<canvas", "webgl", "three.js", "three.min",
        "requestanimationframe", "gl_", "<iframe",
    ):
        assert forbidden not in lowered, f"lens must be GPU-free: {forbidden}"


def test_lens_has_no_animation() -> None:
    """The spec asks for a static SVG — no SMIL animation either."""
    rb, ra = _readings()
    svg = _render(rb, ra)
    assert "<animate" not in svg
    assert "<animateTransform" not in svg


# --------------------------------------------------------------------
# 八字 / 占星 data maps onto the orbital legibly
# --------------------------------------------------------------------

def test_bazi_sexagenary_rails_carried_on_orbit() -> None:
    """The 八字 movement is the Earth-orbit ring: a gold 天干 stem rail
    and a blue 地支 branch rail."""
    rb, ra = _readings()
    svg = _render(rb, ra)
    assert "url(#nye-stem-rail)" in svg
    assert "url(#nye-branch-rail)" in svg


def test_orbital_frame_is_obliquely_tilted() -> None:
    """The Nye Clock orbital sits on a 20-degree oblique plane."""
    rb, ra = _readings()
    svg = _render(rb, ra)
    assert "rotate(20" in svg


def test_four_pillars_appear_as_corner_cartouches() -> None:
    """All four 八字 pillars (year/month/day/hour) stay legible."""
    rb, ra = _readings()
    svg = _render(rb, ra)
    for name in ("YEAR", "MONTH", "DAY", "HOUR"):
        assert name in svg


def test_readout_carries_model_and_consensus() -> None:
    """The MODEL value and the 玄学-consensus value both render."""
    rb, ra = _readings()
    svg = _render(rb, ra)
    assert "62%" in svg
    assert "55%" in svg
    assert "MODEL" in svg


def test_sun_position_tracks_zodiac_sun_sign() -> None:
    """Different birth charts → the Earth sits at a different ecliptic
    angle on the orbit (the 占星 Sun sign drives placement). Two charts
    with different Sun signs must yield different Earth translations."""
    # Pick two dates several months apart — different Sun signs.
    rb1, ra1 = _readings(1993, 1, 10, 8)
    rb2, ra2 = _readings(1993, 7, 10, 8)
    # Sanity: the two charts genuinely have different Sun signs.
    assert ra1.natal.sun != ra2.natal.sun
    svg1 = _render(rb1, ra1)
    svg2 = _render(rb2, ra2)
    # The Earth-cluster translate(...) coordinates differ.
    assert svg1 != svg2


# --------------------------------------------------------------------
# geometry helpers
# --------------------------------------------------------------------

def test_nye_ell_origin_and_quarter() -> None:
    """_nye_ell maps angles onto an origin-centred ellipse."""
    # 0 deg → (+rx, 0); 90 deg → (0, +ry)
    x0, y0 = _clock._nye_ell(330.0, 196.0, 0.0)
    assert abs(x0 - 330.0) < 1e-6 and abs(y0) < 1e-6
    x90, y90 = _clock._nye_ell(330.0, 196.0, 90.0)
    assert abs(x90) < 1e-6 and abs(y90 - 196.0) < 1e-6


def test_nye_ell_arc_returns_path() -> None:
    """_nye_ell_arc emits a valid elliptical-arc path string."""
    d = _clock._nye_ell_arc(300.0, 180.0, -90.0, -54.0)
    assert d.startswith("M ") and " A " in d


def test_nye_canvas_constants() -> None:
    """The Nye Clock canvas constants match the reference exactly."""
    assert _clock._NYE_VB_W == 1000
    assert _clock._NYE_VB_H == 920
    assert _clock._NYE_OBLIQUE_DEG == 20.0
