"""Regression tests for the Console-side 玄学 database + instruments.

Covers all four divination systems (八字 / 紫微 / 易经 / 塔罗): keeps
derivations deterministic, priors + auspice bounded in [0, 1], the
per-branch Bayesian reweight conservative, and every SVG instrument
structurally complete.
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import _metaphysics as mp  # noqa: E402
from _clock import render_nye_clock_svg, render_reading_svg  # noqa: E402


_SAMPLE_BRANCHES = [
    ("Take the offer",    0.32, "realistic"),
    ("Stay & negotiate",  0.27, "realistic"),
    ("Pivot to research", 0.18, "wishful"),
    ("Wait one quarter",  0.15, "realistic"),
    ("Withdraw entirely", 0.08, "worst"),
]


# ---------------------------------------------------------------------------
# 八字 — derivation invariants
# ---------------------------------------------------------------------------


def test_bazi_from_birth_is_deterministic() -> None:
    bd = mp.BirthData(year=2002, month=10, day=2, hour=14)
    assert mp.bazi_from_birth(bd) == mp.bazi_from_birth(bd)


def test_wuxing_balance_sums_to_one() -> None:
    bz = mp.bazi_from_birth(mp.BirthData(1990, 3, 15, 7))
    bal = mp.wuxing_balance(bz)
    assert set(bal.keys()) == set(mp.WUXING_KEYS)
    assert abs(sum(bal.values()) - 1.0) < 1e-9


def test_dominant_and_yongshen_pick_extremes() -> None:
    bz = mp.bazi_from_birth(mp.BirthData(2000, 6, 15, 8))
    bal = mp.wuxing_balance(bz)
    assert bal[mp.dominant_element(bal)] == max(bal.values())
    assert bal[mp.yongshen(bal)] == min(bal.values())


def test_outcome_prior_in_unit_interval() -> None:
    bz = mp.bazi_from_birth(mp.BirthData(1995, 7, 20, 10))
    for outcome in mp.OUTCOME_CATEGORIES:
        assert 0.0 <= mp.outcome_prior(bz, outcome) <= 1.0


def test_pillar_text_two_hanzi() -> None:
    bz = mp.bazi_from_birth(mp.BirthData(2000, 1, 1, 0))
    s = mp.pillar_text(bz.year_pillar)
    assert len(s) == 2
    assert s[0] in mp.HEAVENLY_STEMS and s[1] in mp.EARTHLY_BRANCHES


# ---------------------------------------------------------------------------
# combination math + per-branch Bayesian reweight
# ---------------------------------------------------------------------------


def test_combine_modes_bounds_and_passthrough() -> None:
    assert mp.combine_with_model(0.4, 0.7, "off", 0.5) == 0.4
    assert mp.combine_with_model(0.4, 0.7, "mixture", 0.0) == 0.4
    assert abs(mp.combine_with_model(0.4, 0.7, "mixture", 0.5)
               - (0.5 * 0.7 + 0.5 * 0.4)) < 1e-9
    assert abs(mp.combine_with_model(0.4, 0.7, "bayesian", 0.5)
               - 0.4 * 0.7) < 1e-9


def test_apply_lens_to_branches_conserves_mass_and_alpha0_noop() -> None:
    # alpha = 0 → exact no-op
    out0 = mp.apply_lens_to_branches(_SAMPLE_BRANCHES, auspice=0.9, alpha=0.0)
    assert out0 == _SAMPLE_BRANCHES
    # any reweight renormalizes to 1
    for auspice in (0.1, 0.5, 0.95):
        out = mp.apply_lens_to_branches(_SAMPLE_BRANCHES, auspice, alpha=0.6)
        assert abs(sum(p for _, p, _ in out) - 1.0) < 1e-9


def test_apply_lens_favourable_lifts_wishful() -> None:
    # A favourable reading should raise the wishful branch's share and
    # lower the worst branch's share.
    base = {t: p for _, p, t in _SAMPLE_BRANCHES}
    out = mp.apply_lens_to_branches(_SAMPLE_BRANCHES, auspice=0.95, alpha=0.7)
    after = {t: p for _, p, t in out}
    assert after["wishful"] > base["wishful"]
    assert after["worst"] < base["worst"]


# ---------------------------------------------------------------------------
# 紫微 — 12-palace placement
# ---------------------------------------------------------------------------


def test_ziwei_places_all_14_stars() -> None:
    chart = mp.ziwei_chart(mp.BirthData(2000, 6, 15, 12))
    placed = sum(len(v) for v in chart.palace_stars.values())
    assert placed == 14
    assert 0 <= chart.ming_index < 12
    assert set(chart.palace_stars.keys()) == set(mp.ZIWEI_PALACES)


def test_ziwei_prior_and_auspice_bounded() -> None:
    chart = mp.ziwei_chart(mp.BirthData(1998, 11, 3, 21))
    for outcome in mp.OUTCOME_CATEGORIES:
        assert 0.0 <= mp.ziwei_outcome_prior(chart, outcome) <= 1.0
    assert 0.0 <= mp.ziwei_auspice(chart) <= 1.0


# ---------------------------------------------------------------------------
# 易经 — hexagram cast
# ---------------------------------------------------------------------------


def test_iching_cast_is_deterministic() -> None:
    assert mp.cast_hexagram("pred-123") == mp.cast_hexagram("pred-123")


def test_iching_hexagram_well_formed() -> None:
    hx = mp.cast_hexagram("some-seed")
    assert 1 <= hx.number <= 64
    assert hx.name == mp.HEXAGRAM_NAMES[hx.number]
    assert len(hx.lines) == 6
    assert all(c in range(6) for c in hx.changing)
    for outcome in mp.OUTCOME_CATEGORIES:
        assert 0.0 <= mp.hexagram_outcome_prior(hx, outcome) <= 1.0
    assert 0.0 <= mp.hexagram_auspice(hx) <= 1.0


# ---------------------------------------------------------------------------
# 塔罗 — 3-card draw
# ---------------------------------------------------------------------------


def test_tarot_draw_is_deterministic_and_distinct() -> None:
    a = mp.draw_tarot("pred-xyz")
    b = mp.draw_tarot("pred-xyz")
    assert a.cards == b.cards and a.reversed == b.reversed
    # 3 distinct cards (drawn without replacement)
    assert len({c.number for c in a.cards}) == 3


def test_tarot_prior_and_auspice_bounded() -> None:
    draw = mp.draw_tarot("another-seed")
    for outcome in mp.OUTCOME_CATEGORIES:
        assert 0.0 <= mp.tarot_outcome_prior(draw, outcome) <= 1.0
    assert 0.0 <= mp.tarot_auspice(draw) <= 1.0


# ---------------------------------------------------------------------------
# unified compute_reading
# ---------------------------------------------------------------------------


def test_compute_reading_all_systems() -> None:
    bd = mp.BirthData(2000, 6, 15, 12)
    for system in mp.SYSTEMS:
        r = mp.compute_reading(system, birth=bd, seed="seed-1",
                               outcome="career_success")
        assert r.system == system
        assert 0.0 <= r.prior <= 1.0
        assert 0.0 <= r.auspice <= 1.0
    # each system populates exactly its own payload
    assert mp.compute_reading("bazi", birth=bd, seed="s",
                              outcome="career_success").bazi is not None
    assert mp.compute_reading("ziwei", birth=bd, seed="s",
                              outcome="career_success").ziwei is not None
    assert mp.compute_reading("iching", birth=bd, seed="s",
                              outcome="career_success").hexagram is not None
    assert mp.compute_reading("tarot", birth=bd, seed="s",
                              outcome="career_success").tarot is not None


# ---------------------------------------------------------------------------
# instrument renderers — structural invariants
# ---------------------------------------------------------------------------


def test_render_reading_svg_all_systems_valid() -> None:
    bd = mp.BirthData(2002, 10, 2, 14)
    for system in mp.SYSTEMS:
        reading = mp.compute_reading(system, birth=bd, seed="cast-seed",
                                     outcome="career_success")
        svg = render_reading_svg(
            reading, _SAMPLE_BRANCHES,
            center_top_label="MODEL", center_top_value="34.2%",
            center_bottom_label="COMBINED", center_bottom_value="41.0%",
            center_meta=f"{system.upper()} - alpha=0.30",
        )
        assert svg.startswith("<svg ") and svg.endswith("</svg>")
        assert 'viewBox="0 0 480 480"' in svg
        assert "<defs>" in svg


def test_bazi_dial_structure() -> None:
    bd = mp.BirthData(2002, 10, 2, 14)
    reading = mp.compute_reading("bazi", birth=bd, seed="s",
                                 outcome="career_success")
    svg = render_reading_svg(
        reading, _SAMPLE_BRANCHES,
        center_top_label="MODEL", center_top_value="34.2%",
        center_bottom_label="COMBINED", center_bottom_value="52.1%",
        center_meta="BAZI",
    )
    # 5 五行 wedge gradients referenced
    for key in mp.WUXING_KEYS:
        assert f"url(#wx-{key})" in svg
    # graduated rings + the four 八字 cartouches
    assert "YEAR" in svg and "MONTH" in svg
    assert "DAY" in svg and "HOUR" in svg
    assert "34.2%" in svg and "52.1%" in svg


def test_iching_renderer_shows_hexagram() -> None:
    bd = mp.BirthData(2000, 6, 15, 12)
    reading = mp.compute_reading("iching", birth=bd, seed="hex-seed",
                                 outcome="career_success")
    svg = render_reading_svg(
        reading, _SAMPLE_BRANCHES,
        center_top_label="MODEL", center_top_value="30%",
        center_bottom_label="COMBINED", center_bottom_value="44%",
        center_meta="ICHING",
    )
    assert "HEXAGRAM" in svg
    assert "url(#bronze)" in svg  # the carved-line gradient


def test_tarot_renderer_shows_three_cards() -> None:
    bd = mp.BirthData(2000, 6, 15, 12)
    reading = mp.compute_reading("tarot", birth=bd, seed="tarot-seed",
                                 outcome="career_success")
    svg = render_reading_svg(
        reading, _SAMPLE_BRANCHES,
        center_top_label="MODEL", center_top_value="30%",
        center_bottom_label="COMBINED", center_bottom_value="44%",
        center_meta="TAROT",
    )
    assert "PAST" in svg and "PRESENT" in svg and "FUTURE" in svg


def test_back_compat_shim_renders() -> None:
    bd = mp.BirthData(1990, 3, 15, 7)
    bz = mp.bazi_from_birth(bd)
    svg = render_nye_clock_svg(
        bz, mp.wuxing_balance(bz), _SAMPLE_BRANCHES,
        center_top_label="MODEL", center_top_value="—",
        center_bottom_label="COMBINED", center_bottom_value="—",
        center_meta="EARTH",
    )
    assert svg.startswith("<svg ") and svg.endswith("</svg>")
