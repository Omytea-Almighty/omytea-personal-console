"""Regression tests for the Console-side 玄学 / Nye-clock modules.

Keeps the 八字 derivation deterministic, the 五行 share normalized,
the combination math bounded, and the SVG instrument structurally
complete (5 outer sectors + 4 pillar labels + a non-empty centre).
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import _metaphysics as mp  # noqa: E402
from _clock import render_nye_clock_svg  # noqa: E402


# ---------------------------------------------------------------------------
# Metaphysics — derivation invariants
# ---------------------------------------------------------------------------


def test_bazi_from_birth_is_deterministic() -> None:
    bd = mp.BirthData(year=2002, month=10, day=2, hour=14)
    a = mp.bazi_from_birth(bd)
    b = mp.bazi_from_birth(bd)
    assert a == b


def test_wuxing_balance_sums_to_one() -> None:
    bd = mp.BirthData(year=1990, month=3, day=15, hour=7)
    bz = mp.bazi_from_birth(bd)
    bal = mp.wuxing_balance(bz)
    assert set(bal.keys()) == set(mp.WUXING_KEYS)
    assert abs(sum(bal.values()) - 1.0) < 1e-9


def test_dominant_and_yongshen_pick_extremes() -> None:
    bd = mp.BirthData(year=2000, month=6, day=15, hour=8)
    bz = mp.bazi_from_birth(bd)
    bal = mp.wuxing_balance(bz)
    dom = mp.dominant_element(bal)
    yong = mp.yongshen(bal)
    assert dom in mp.WUXING_KEYS
    assert yong in mp.WUXING_KEYS
    # The max-share key must equal dominant; the min-share key must
    # equal yongshen (ties broken consistently by max/min).
    assert bal[dom] == max(bal.values())
    assert bal[yong] == min(bal.values())


def test_outcome_prior_is_in_unit_interval() -> None:
    bd = mp.BirthData(year=1995, month=7, day=20, hour=10)
    bz = mp.bazi_from_birth(bd)
    for outcome in mp.OUTCOME_CATEGORIES:
        p = mp.outcome_prior(bz, outcome)
        assert 0.0 <= p <= 1.0


def test_combine_modes_respect_bounds_and_off_passthrough() -> None:
    # off-mode and α=0 both must be model-only no-ops.
    assert mp.combine_with_model(0.4, 0.7, "off", 0.5) == 0.4
    assert mp.combine_with_model(0.4, 0.7, "mixture", 0.0) == 0.4
    # mixture interpolates linearly.
    assert abs(mp.combine_with_model(0.4, 0.7, "mixture", 0.5)
               - (0.5 * 0.7 + 0.5 * 0.4)) < 1e-9
    # bayesian returns un-normalized product (caller renormalizes).
    assert abs(mp.combine_with_model(0.4, 0.7, "bayesian", 0.5)
               - 0.4 * 0.7) < 1e-9
    # All combined values are clipped to [0, 1] in mixture/off paths.
    for mode in ("mixture", "off"):
        v = mp.combine_with_model(0.4, 0.7, mode, 0.5)
        assert 0.0 <= v <= 1.0


def test_pillar_text_returns_two_hanzi() -> None:
    bd = mp.BirthData(year=2000, month=1, day=1, hour=0)
    bz = mp.bazi_from_birth(bd)
    s = mp.pillar_text(bz.year_pillar)
    assert len(s) == 2  # 天干 + 地支
    assert s[0] in mp.HEAVENLY_STEMS
    assert s[1] in mp.EARTHLY_BRANCHES


# ---------------------------------------------------------------------------
# Clock — SVG structural invariants
# ---------------------------------------------------------------------------


def test_clock_svg_has_five_wuxing_sectors() -> None:
    bd = mp.BirthData(year=2002, month=10, day=2, hour=14)
    bz = mp.bazi_from_birth(bd)
    bal = mp.wuxing_balance(bz)
    svg = render_nye_clock_svg(
        bz, bal,
        [("A", 0.4, "realistic"),
         ("B", 0.3, "wishful"),
         ("C", 0.2, "realistic"),
         ("D", 0.1, "worst")],
        "Career success", "52% combined", "WOOD-DOMINANT · α=0.30",
    )
    # 5 outer sectors as <path d="..."> arcs
    assert svg.count('<path d="M') >= 5
    # The four 八字 pillar headers must be visible
    assert "YEAR" in svg
    assert "MONTH" in svg
    assert "DAY" in svg
    assert "HOUR" in svg
    # Inner ring uses branch-color coding (lavender / teal / coral)
    assert "139,140,255" in svg  # realistic / lavender
    assert "88,197,180" in svg   # wishful  / teal
    assert "255,94,110" in svg   # worst    / coral
    # Centre disc + headline + meta
    assert "Career success" in svg
    assert "52%" in svg
    assert "WOOD-DOMINANT" in svg


def test_clock_svg_handles_empty_branches() -> None:
    """When the user has not run a prediction yet, the inner ring is
    empty but the outer ring + centre still renders without raising.
    """
    bd = mp.BirthData(year=1990, month=3, day=15, hour=7)
    bz = mp.bazi_from_birth(bd)
    bal = mp.wuxing_balance(bz)
    svg = render_nye_clock_svg(
        bz, bal,
        [],
        "Waiting", "—", "EARTH-DOMINANT",
    )
    assert svg.startswith("<svg ")
    assert svg.endswith("</svg>")
    # Outer ring must still show 5 sectors
    assert svg.count('<path d="M') >= 5
