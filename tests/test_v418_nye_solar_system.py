"""Nye Clock 玄学 view (OMY-V415 / M2 / Acceptance #54, REBUILT for #64).

The dense unified astrolabe (founder verdict "不知所云") is replaced by a
faithful static-SVG recreation of the founder's real Nye Clock.

Acceptance #64 REBUILT this view (4th attempt) to faithfully match the
canonical final Nye Clock — ``~/Downloads/UCSB/Adonyth/tw_.html``. The
founder rejected the earlier Earth-centred, tight-busy-coin-wheel
composition as "太乱" (wrong composition). The tw_.html-faithful layout
is a STATIC visual style: a deep-black, spacious deep-space scene; a
LARGE glowing Sun with several concentric translucent corona shells
dominating the upper-right; a SMALL blue Earth tucked into the
lower-left corner with a thin orbital ring, a small Moon and a TIGHT
cluster of small 五行-tinted 干支 coin tokens; and large but faint 干支
glyphs floating sparsely across the black field.

These tests pin: (1) the view is the tw_.html Nye Clock, not the old
astrolabe; (2) it is GPU-free static SVG; (3) the composition is
Sun-dominant with the Earth in a corner; (4) the 八字 / 占星 data maps
onto it legibly; (5) the geometry helpers are correct.
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

def test_bazi_sexagenary_rails_are_ganzhi_coin_rings() -> None:
    """The 八字 movement is two concentric rings of 干支 COIN tokens
    in a TIGHT cluster around the small corner Earth — the tw_.html
    layout (Acceptance #64).

    Each coin is a 五行-tinted bezel ring + the character. There are 22
    coins total: an inner ring of 12 地支 + an outer ring of 10 天干.
    """
    rb, ra = _readings()
    svg = _render(rb, ra)
    # the per-五行 coin gradients are referenced
    assert "url(#tw-coin-" in svg
    # all 22 coin tokens (12 地支 + 10 天干) render
    assert svg.count("url(#tw-coin-") == 22


def test_ganzhi_characters_render_on_the_coins() -> None:
    """Every 天干 and 地支 character appears on its coin."""
    rb, ra = _readings()
    svg = _render(rb, ra)
    for ch in mp.HEAVENLY_STEMS:
        assert ch in svg, f"missing 天干 {ch}"
    for ch in mp.EARTHLY_BRANCHES:
        assert ch in svg, f"missing 地支 {ch}"


def test_view_is_not_oblique() -> None:
    """The tw_.html 玄学 view uses an upright deep-space frame — NOT
    the old superseded 20-degree oblique solar-system frame."""
    rb, ra = _readings()
    svg = _render(rb, ra)
    # the old wrong-reference renderer tilted the whole scene 20°
    assert "rotate(20" not in svg
    # the 干支 coin cluster is part of the new structure
    assert "url(#tw-coin-" in svg


def test_four_pillars_render_as_jewelled_markers() -> None:
    """All four 八字 pillars (year/month/day/hour) render — small
    jewelled 干支 markers in a column clear of the dominant Sun."""
    rb, ra = _readings()
    svg = _render(rb, ra)
    for name in ("YEAR", "MONTH", "DAY", "HOUR"):
        assert name in svg
    # the soft glyph-glow filter is applied
    assert "url(#tw-glyph-glow)" in svg


def test_readout_carries_model_and_consensus() -> None:
    """The MODEL value and the 玄学-consensus value both render."""
    rb, ra = _readings()
    svg = _render(rb, ra)
    assert "62%" in svg
    assert "55%" in svg
    assert "MODEL" in svg


def test_view_reflects_the_birth_chart() -> None:
    """Different birth charts → a different rendered scene. The 占星
    Sun sign tints the Sun's engraved ring + the Earth halo, and the
    八字 day pillar lights different 干支 coins, so two distinct charts
    must yield distinct SVGs (the view is genuinely data-driven, read
    from the verified _metaphysics engine)."""
    # Pick two dates several months apart — different Sun signs.
    rb1, ra1 = _readings(1993, 1, 10, 8)
    rb2, ra2 = _readings(1993, 7, 10, 8)
    # Sanity: the two charts genuinely have different Sun signs.
    assert ra1.natal.sun != ra2.natal.sun
    svg1 = _render(rb1, ra1)
    svg2 = _render(rb2, ra2)
    assert svg1 != svg2


# --------------------------------------------------------------------
# the rebuilt composition — Sun-dominant, Earth in a corner, sparse
# 干支 (Acceptance #64 — faithful to tw_.html)
# --------------------------------------------------------------------

def test_composition_is_sun_dominant_earth_in_corner() -> None:
    """The view's composition matches the real tw_.html: a LARGE Sun
    dominating the upper area, a SMALL Earth tucked into a lower
    corner. Pin the layout constants so the rejected centred-Earth
    composition cannot return.
    """
    # the Earth is small and the Sun is the big body
    assert _clock._TW_EARTH_R <= 70, "the corner Earth must stay small"
    # the Earth sits in the lower-left quadrant of the 1000x920 frame
    assert _clock._TW_EARTH_CX < _clock._NYE_VB_W * 0.42
    assert _clock._TW_EARTH_CY > _clock._NYE_VB_H * 0.55
    # the Sun sits in the upper-right region, well clear of the Earth
    assert _clock._TW_SUN_CX > _clock._NYE_VB_W * 0.55
    assert _clock._TW_SUN_CY < _clock._NYE_VB_H * 0.5
    # the coin cluster hugs the small Earth (tight rings)
    assert _clock._TW_STEM_RING_R < 180, "coin cluster must stay tight"
    assert _clock._TW_COIN_R <= 16, "干支 coins must be small tokens"


def test_sun_has_concentric_corona_shells() -> None:
    """The Sun carries several big concentric translucent corona /
    atmosphere shells — the dominant nested-sphere look of tw_.html."""
    rb, ra = _readings()
    svg = _render(rb, ra)
    # the soft corona-shell gradient is defined and used
    assert 'id="nye-sun-shell"' in svg
    assert svg.count("url(#nye-sun-shell)") >= 3


def test_sparse_floating_ganzhi_glyphs_scatter_the_field() -> None:
    """Large faint 干支 glyphs float sparsely across the black field
    — the drifting characters of the real tw_.html scene."""
    rb, ra = _readings()
    svg = _render(rb, ra)
    # the float-glyph layout table is sane: several, generously sized
    glyphs = _clock._TW_FLOAT_GLYPHS
    assert 6 <= len(glyphs) <= 12, "sparse — a handful, not a crowd"
    for _x, _y, size, kind in glyphs:
        assert size >= 36, "the floating glyphs are large"
        assert kind in ("stem", "branch")
    # they render dim (faint), not at full opacity
    assert 'fill-opacity="0.30"' in svg


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


# --------------------------------------------------------------------
# Acceptance #61 — rebuilt from the canonical tw_.html
# --------------------------------------------------------------------

def test_tw_wuxing_palette_is_five_elements() -> None:
    """The tw_.html 五行 coin palette has all five elements, each with a
    rim + a deep tone for a real radial-gradient coin."""
    assert len(_clock._TW_WUXING) == 5
    for rim, deep in _clock._TW_WUXING:
        assert rim.startswith("#") and deep.startswith("#")


def test_tw_coin_renders_bezel_ring_and_character() -> None:
    """A 干支 coin token is a 五行-tinted bezel ring + the character."""
    coin = _clock._tw_coin(100.0, 100.0, "甲", 0)
    assert coin.startswith("<g ") and coin.endswith("</g>")
    assert "甲" in coin
    # the coin face uses a per-五行 coin gradient
    assert "url(#tw-coin-0)" in coin
    # a circular token
    assert "<circle" in coin


def test_tw_coin_active_state_lights_up() -> None:
    """The active (day-pillar) coin is enlarged + glowing vs an idle one."""
    idle = _clock._tw_coin(0.0, 0.0, "乙", 1, active=False)
    active = _clock._tw_coin(0.0, 0.0, "乙", 1, active=True)
    assert idle != active
    # the active coin gets the soft-glow filter
    assert "url(#nye-soft-glow)" in active
    assert "url(#nye-soft-glow)" not in idle


def test_tw_coin_pillar_state_marks_a_jewel() -> None:
    """A coin carrying one of the four 八字 pillars gets a jewel dot."""
    plain = _clock._tw_coin(0.0, 0.0, "丙", 1, pillar=False)
    pillar = _clock._tw_coin(0.0, 0.0, "丙", 1, pillar=True)
    assert plain != pillar
    # the jewel dot is gold
    assert _clock._GAL_GOLD in pillar


def test_tw_defs_emits_a_coin_gradient_per_element() -> None:
    """_tw_defs defines one coin gradient per 五行 + the glyph-glow."""
    defs = _clock._tw_defs()
    for i in range(5):
        assert f'id="tw-coin-{i}"' in defs
    assert 'id="tw-glyph-glow"' in defs


def test_nye_view_is_gpu_free_static_svg() -> None:
    """CRITICAL — the rebuilt view is still GPU-free static SVG.

    The founder vetoed embedding the real 3-D Three.js clock; the 玄学
    view must be a lightweight static SVG that embeds verbatim.
    """
    rb, ra = _readings()
    svg = _render(rb, ra).lower()
    for forbidden in (
        "<script", "<canvas", "webgl", "three.js", "three.min",
        "requestanimationframe", "<iframe", "<animate",
    ):
        assert forbidden not in svg, f"view must be GPU-free: {forbidden}"


def test_nye_view_has_earth_sun_moon_bodies() -> None:
    """The Earth (heart), the off-axis Sun, and the Moon all render."""
    rb, ra = _readings()
    svg = _render(rb, ra)
    # Earth — ocean / land / atmosphere
    assert "url(#nye-earth-ocean)" in svg
    assert "url(#nye-earth-land)" in svg
    # Sun — layered core / corona
    assert "url(#nye-sun-core)" in svg
    assert "url(#nye-sun-corona)" in svg
    # Moon — surface
    assert "url(#nye-moon-surf)" in svg


def test_nye_view_coins_are_colour_coded_by_wuxing() -> None:
    """Different 干支 land on different 五行 coin gradients — the wheel
    is genuinely 五行-colour-coded, not monochrome."""
    rb, ra = _readings()
    svg = _render(rb, ra)
    used = {i for i in range(5) if f"url(#tw-coin-{i})" in svg}
    # the 60-cycle spans every element, so all five gradients appear
    assert used == {0, 1, 2, 3, 4}


def test_tw_layout_constants_present() -> None:
    """The tw_.html-canonical layout constants exist and are sane."""
    assert _clock._TW_EARTH_R > 0
    # the coin rings sit OUTSIDE the Earth globe
    assert _clock._TW_BRANCH_RING_R > _clock._TW_EARTH_R
    assert _clock._TW_STEM_RING_R > _clock._TW_BRANCH_RING_R
