"""Divination instrument renderers — four hand-drawn SVG instruments.

Founder critique 2026-05-19: the first dial was "太简笔画" (too crude /
stick-figure). This module rebuilds it as a proper instrument and adds
three more, one authentic visual form per tradition:

  • 八字  → "The Five-Phase Astrolabe" — concentric graduated rings,
            gradient-filled 五行 wedges, a starfield backdrop, an
            engraved core with a dual MODEL / COMBINED readout.
  • 易经  → a carved 6-line hexagram with its two trigrams, changing
            lines marked, rendered in warm bronze on the dark card.
  • 塔罗  → a 3-card past / present / future spread, each card a
            framed plate with a drawn emblem; reversed cards inverted.
  • 紫微  → a 12-palace chart (the classic 4×4 ring-of-cells), the
            14 主星 placed, 命宫 highlighted, a centre summary plate.

All four share the v10 palette (canvas #0a0c11, surface #11141b,
hairline #232834, lavender #8b8cff, teal #58c5b4, coral #ff5e6e,
amber #d8a657, Cormorant Garamond serif for numbers that matter).
Static SVG only — no JS — but with real depth: radial/linear
gradients, Gaussian-blur glows, drop shadows, graduated tick rings.

One public entry point: `render_reading_svg(reading, branches, …)`
dispatches on `reading.system`.
"""

from __future__ import annotations

import html as _html
import math
from typing import Any

from _metaphysics import (
    ASTRO_ELEMENT_COLOR,
    EARTHLY_BRANCHES,
    HEAVENLY_STEMS,
    HEXAGRAM_NAMES,
    TAROT_POSITIONS,
    TRIGRAM_HANZI,
    TRIGRAM_SYMBOL,
    WUXING_COLOR,
    WUXING_COLOR_DEEP,
    WUXING_HANZI,
    WUXING_KEYS,
    WUXING_OF_BRANCH,
    WUXING_OF_STEM,
    ZIWEI_PALACE_HANZI,
    ZIWEI_PALACES,
    ZIWEI_STARS,
    ZODIAC,
    BaZiPattern,
    Hexagram,
    LensReading,
    NatalChart,
    TarotDraw,
    ZiWeiChart,
    dominant_element,
    pillar_text,
    ziwei_star_hanzi,
)

# Star-nature map (吉 +1 / 中 0 / 凶 −1) for 紫微 colour coding.
_STAR_NATURE: dict[str, int] = {k: n for k, _h, n in ZIWEI_STARS}

# ----------------------------------------------------------------------
# Palette — a disciplined surface + hairline ladder (per the Linear
# design study: carry depth with stepped surfaces + graded hairlines,
# reserve the glow for the single focal element, never decorate).
# ----------------------------------------------------------------------
_CANVAS   = "#0a0c11"
_SURFACE  = "#11141b"   # surface-1 — default card
_SURFACE2 = "#181c25"   # surface-2 — lifted tile
_SURFACE3 = "#1f2530"   # surface-3 — nested / hovered
_HAIRLINE = "#232834"   # structural divider
_HAIR_SOFT   = "#1a1e26"  # faint nested hairline
_HAIR_STRONG = "#343a47"  # emphasis hairline
_INK0     = "#f0f2f5"
_INK1     = "#b9bfc8"
_INK2     = "#76808d"
_INK3     = "#4b525d"
_ACCENT   = "#8b8cff"
_TEAL     = "#58c5b4"
_CORAL    = "#ff5e6e"
_AMBER    = "#d8a657"

# Galaxy palette — borrowed verbatim from the founder's Nye Clock
# (the sexagenary-cycle celestial instrument). 天干 ticks render gold,
# 地支 ticks render cyan, so the 10-stem and 12-branch tick systems
# visibly "mesh" like two gears (LCM 10,12 = 60). Used by the 八字
# Sexagenary Engine + the 占星 orbital wheel.
_GAL_GOLD   = "#f7c940"   # 天干 / Heavenly Stems
_GAL_CYAN   = "#44ecff"   # 地支 / Earthly Branches
_GAL_BLUE   = "#6b8fff"   # orbital paths
_GAL_VIOLET = "#b47eff"   # nebula accents

_SERIF = "'Cormorant Garamond',Georgia,serif"
_MONO  = "ui-monospace,SFMono-Regular,Menlo,monospace"

_VB = 480
_CX = _VB / 2
_CY = _VB / 2


# ----------------------------------------------------------------------
# Geometry helpers
# ----------------------------------------------------------------------

def _polar(cx: float, cy: float, r: float, theta_deg: float) -> tuple[float, float]:
    """Polar → Cartesian. theta=0 at 12 o'clock, clockwise positive."""
    t = math.radians(theta_deg - 90.0)
    return cx + r * math.cos(t), cy + r * math.sin(t)


def _arc_path(cx: float, cy: float, r_out: float, r_in: float,
              a0: float, a1: float) -> str:
    """SVG annulus-sector path."""
    if a1 - a0 <= 1e-3:
        return ""
    large = 1 if (a1 - a0) > 180 else 0
    x0o, y0o = _polar(cx, cy, r_out, a0)
    x1o, y1o = _polar(cx, cy, r_out, a1)
    x0i, y0i = _polar(cx, cy, r_in, a0)
    x1i, y1i = _polar(cx, cy, r_in, a1)
    return (
        f"M {x0o:.2f} {y0o:.2f} "
        f"A {r_out:.2f} {r_out:.2f} 0 {large} 1 {x1o:.2f} {y1o:.2f} "
        f"L {x1i:.2f} {y1i:.2f} "
        f"A {r_in:.2f} {r_in:.2f} 0 {large} 0 {x0i:.2f} {y0i:.2f} Z"
    )


def _open_arc(cx: float, cy: float, r: float, a0: float, a1: float) -> str:
    """A single-radius open arc path (for stroked arcs with round caps)."""
    large = 1 if (a1 - a0) > 180 else 0
    x0, y0 = _polar(cx, cy, r, a0)
    x1, y1 = _polar(cx, cy, r, a1)
    return f"M {x0:.2f} {y0:.2f} A {r:.2f} {r:.2f} 0 {large} 1 {x1:.2f} {y1:.2f}"


def _esc(s: str, n: int = 64) -> str:
    return _html.escape(str(s))[:n]


# ----------------------------------------------------------------------
# Shared SVG fragments
# ----------------------------------------------------------------------

def _starfield(seed: int = 7, n: int = 40) -> str:
    """A faint procedural starfield — gives the dark card depth."""
    dots: list[str] = []
    s = seed
    for _ in range(n):
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        x = 14 + (s % 1000) / 1000.0 * (_VB - 28)
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        y = 14 + (s % 1000) / 1000.0 * (_VB - 28)
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        r = 0.35 + (s % 100) / 100.0 * 1.05
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        op = 0.07 + (s % 100) / 100.0 * 0.34
        dots.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}" '
            f'fill="{_INK1}" opacity="{op:.2f}"></circle>'
        )
    return "".join(dots)


def _common_defs() -> str:
    """Gradients + filters reused across all instruments."""
    parts = [
        '<defs>',
        # backdrop glow
        '<radialGradient id="bg-glow" cx="50%" cy="46%" r="62%">'
        f'<stop offset="0%" stop-color="rgba(139,140,255,0.13)"/>'
        f'<stop offset="55%" stop-color="rgba(139,140,255,0.03)"/>'
        f'<stop offset="100%" stop-color="rgba(139,140,255,0)"/>'
        '</radialGradient>',
        # core recessed plate
        '<radialGradient id="core-grad" cx="50%" cy="42%" r="60%">'
        f'<stop offset="0%" stop-color="#1b2030"/>'
        f'<stop offset="100%" stop-color="#0d0f15"/>'
        '</radialGradient>',
        # soft glow filter
        '<filter id="soft-glow" x="-60%" y="-60%" width="220%" height="220%">'
        '<feGaussianBlur stdDeviation="3.4" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>'
        '</filter>',
        # number glow (tighter)
        '<filter id="num-glow" x="-50%" y="-50%" width="200%" height="200%">'
        '<feGaussianBlur stdDeviation="1.6" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>'
        '</filter>',
        # drop shadow for floating elements — restrained (depth comes
        # mostly from the surface + hairline ladder, not heavy shadow)
        '<filter id="drop" x="-40%" y="-40%" width="180%" height="180%">'
        '<feDropShadow dx="0" dy="2" stdDeviation="3" '
        'flood-color="#000000" flood-opacity="0.40"/>'
        '</filter>',
        # nested-cell vertical gradient (surface-2 → slightly deeper)
        '<linearGradient id="cell-grad" x1="0%" y1="0%" x2="0%" y2="100%">'
        f'<stop offset="0%" stop-color="#1a1f2a"/>'
        f'<stop offset="100%" stop-color="#13161e"/>'
        '</linearGradient>',
        # tarot card face (top-lit)
        '<linearGradient id="card-face" x1="0%" y1="0%" x2="0%" y2="100%">'
        f'<stop offset="0%" stop-color="#20242f"/>'
        f'<stop offset="100%" stop-color="#15181f"/>'
        '</linearGradient>',
        # violet nebula blob — deep-space depth behind the starfield
        '<radialGradient id="nebula-violet" cx="50%" cy="50%" r="50%">'
        '<stop offset="0%" stop-color="rgba(180,126,255,0.20)"/>'
        '<stop offset="58%" stop-color="rgba(139,140,255,0.05)"/>'
        '<stop offset="100%" stop-color="rgba(139,140,255,0)"/>'
        '</radialGradient>',
        # lit-sphere shading — bright spot upper-left → a 3-D body
        '<radialGradient id="sphere-sun" cx="36%" cy="32%" r="72%">'
        '<stop offset="0%" stop-color="#fff4cf"/>'
        '<stop offset="55%" stop-color="#f7c940"/>'
        '<stop offset="100%" stop-color="#a8770f"/>'
        '</radialGradient>',
        '<radialGradient id="sphere-moon" cx="36%" cy="32%" r="74%">'
        '<stop offset="0%" stop-color="#f3f5fc"/>'
        '<stop offset="55%" stop-color="#aeb7cb"/>'
        '<stop offset="100%" stop-color="#4f5870"/>'
        '</radialGradient>',
        # sun corona — a soft blurred halo
        '<radialGradient id="corona-glow" cx="50%" cy="50%" r="50%">'
        '<stop offset="0%" stop-color="rgba(247,201,64,0.55)"/>'
        '<stop offset="42%" stop-color="rgba(247,201,64,0.15)"/>'
        '<stop offset="100%" stop-color="rgba(247,201,64,0)"/>'
        '</radialGradient>',
        # gear metal — one coherent top-lit sheen across the instrument
        f'<linearGradient id="gear-gold" gradientUnits="userSpaceOnUse" '
        f'x1="{_CX}" y1="24" x2="{_CX}" y2="456">'
        '<stop offset="0%" stop-color="#ffe79a"/>'
        '<stop offset="46%" stop-color="#f0bf3d"/>'
        '<stop offset="100%" stop-color="#7e5d11"/>'
        '</linearGradient>',
        f'<linearGradient id="gear-cyan" gradientUnits="userSpaceOnUse" '
        f'x1="{_CX}" y1="24" x2="{_CX}" y2="456">'
        '<stop offset="0%" stop-color="#bdf6ff"/>'
        '<stop offset="46%" stop-color="#3fd6ec"/>'
        '<stop offset="100%" stop-color="#136f82"/>'
        '</linearGradient>',
    ]
    # per-element radial gradients for the 五行 wedges
    for key in WUXING_KEYS:
        parts.append(
            f'<radialGradient id="wx-{key}" cx="50%" cy="50%" r="75%">'
            f'<stop offset="0%" stop-color="{WUXING_COLOR_DEEP[key]}"/>'
            f'<stop offset="100%" stop-color="{WUXING_COLOR[key]}"/>'
            f'</radialGradient>'
        )
    # warm bronze gradient for hexagram lines
    parts.append(
        '<linearGradient id="bronze" x1="0%" y1="0%" x2="100%" y2="0%">'
        f'<stop offset="0%" stop-color="#9c7637"/>'
        f'<stop offset="50%" stop-color="{_AMBER}"/>'
        f'<stop offset="100%" stop-color="#9c7637"/>'
        '</linearGradient>'
    )
    # lavender arc gradient for the branch ring
    parts.append(
        '<linearGradient id="arc-lav" x1="0%" y1="0%" x2="100%" y2="0%">'
        f'<stop offset="0%" stop-color="rgba(139,140,255,0.35)"/>'
        f'<stop offset="100%" stop-color="rgba(139,140,255,0.92)"/>'
        '</linearGradient>'
    )
    parts.append('</defs>')
    return "".join(parts)


def _svg_open() -> str:
    return (
        f'<svg viewBox="0 0 {_VB} {_VB}" width="100%" '
        f'preserveAspectRatio="xMidYMid meet" style="display:block;">'
        f'{_common_defs()}'
        f'<rect x="0" y="0" width="{_VB}" height="{_VB}" fill="{_CANVAS}"></rect>'
        f'<rect x="0" y="0" width="{_VB}" height="{_VB}" fill="url(#bg-glow)"></rect>'
        # two soft nebula blobs — deep-space depth, off-centre for life
        f'<ellipse cx="{_VB * 0.30:.0f}" cy="{_VB * 0.30:.0f}" '
        f'rx="{_VB * 0.44:.0f}" ry="{_VB * 0.36:.0f}" '
        f'fill="url(#nebula-violet)"></ellipse>'
        f'<ellipse cx="{_VB * 0.74:.0f}" cy="{_VB * 0.76:.0f}" '
        f'rx="{_VB * 0.34:.0f}" ry="{_VB * 0.30:.0f}" '
        f'fill="url(#bg-glow)" opacity="0.55"></ellipse>'
        f'{_starfield()}'
    )


def _centre_readout(top_label: str, top_value: str,
                    bottom_label: str, bottom_value: str,
                    meta: str, *, r_core: float = 100.0) -> str:
    """The engraved core disc with the dual MODEL / COMBINED readout.

    Shared by the 八字 astrolabe; the other instruments use a slim
    footer band instead (they have no natural centre).
    """
    return (
        # recessed plate
        f'<circle cx="{_CX}" cy="{_CY}" r="{r_core}" fill="url(#core-grad)" '
        f'stroke="{_HAIRLINE}" stroke-width="1.2"></circle>'
        f'<circle cx="{_CX}" cy="{_CY}" r="{r_core - 7}" fill="none" '
        f'stroke="rgba(255,255,255,0.05)" stroke-width="0.7"></circle>'
        f'<circle cx="{_CX}" cy="{_CY}" r="{r_core - 9.5}" fill="none" '
        f'stroke="rgba(0,0,0,0.4)" stroke-width="0.7"></circle>'
        # top label + value
        f'<text x="{_CX}" y="{_CY - 42}" font-family="{_MONO}" font-size="9.5" '
        f'fill="{_INK2}" letter-spacing="0.22em" text-anchor="middle" '
        f'dominant-baseline="middle">{_esc(top_label,18)}</text>'
        f'<text x="{_CX}" y="{_CY - 19}" font-family="{_SERIF}" font-size="27" '
        f'fill="{_INK0}" font-weight="600" text-anchor="middle" '
        f'dominant-baseline="middle" filter="url(#num-glow)">'
        f'{_esc(top_value,10)}</text>'
        # divider with end dots
        f'<line x1="{_CX-26}" y1="{_CY}" x2="{_CX+26}" y2="{_CY}" '
        f'stroke="{_HAIRLINE}" stroke-width="0.9"></line>'
        f'<circle cx="{_CX-26}" cy="{_CY}" r="1.5" fill="{_INK3}"></circle>'
        f'<circle cx="{_CX+26}" cy="{_CY}" r="1.5" fill="{_INK3}"></circle>'
        # bottom label + value
        f'<text x="{_CX}" y="{_CY + 17}" font-family="{_MONO}" font-size="9.5" '
        f'fill="{_INK2}" letter-spacing="0.22em" text-anchor="middle" '
        f'dominant-baseline="middle">{_esc(bottom_label,18)}</text>'
        f'<text x="{_CX}" y="{_CY + 40}" font-family="{_SERIF}" font-size="27" '
        f'fill="{_ACCENT}" font-weight="600" text-anchor="middle" '
        f'dominant-baseline="middle" filter="url(#num-glow)">'
        f'{_esc(bottom_value,10)}</text>'
        # meta tag
        f'<text x="{_CX}" y="{_CY + r_core - 13}" font-family="{_MONO}" '
        f'font-size="8.5" fill="{_INK3}" letter-spacing="0.2em" '
        f'text-anchor="middle" dominant-baseline="middle">'
        f'{_esc(meta,40)}</text>'
    )


def _footer_band(model_value: str, combined_value: str, meta: str) -> str:
    """A slim MODEL / COMBINED footer for the non-dial instruments."""
    y = _VB - 30
    return (
        f'<line x1="56" y1="{y-20}" x2="{_VB-56}" y2="{y-20}" '
        f'stroke="{_HAIRLINE}" stroke-width="0.8"></line>'
        f'<text x="120" y="{y}" font-family="{_MONO}" font-size="9" '
        f'fill="{_INK2}" letter-spacing="0.16em" text-anchor="middle">MODEL</text>'
        f'<text x="120" y="{y+19}" font-family="{_SERIF}" font-size="20" '
        f'fill="{_INK0}" font-weight="600" text-anchor="middle">'
        f'{_esc(model_value,8)}</text>'
        f'<text x="{_VB-120}" y="{y}" font-family="{_MONO}" font-size="9" '
        f'fill="{_INK2}" letter-spacing="0.16em" text-anchor="middle">COMBINED</text>'
        f'<text x="{_VB-120}" y="{y+19}" font-family="{_SERIF}" font-size="20" '
        f'fill="{_ACCENT}" font-weight="600" text-anchor="middle">'
        f'{_esc(combined_value,8)}</text>'
        f'<text x="{_CX}" y="{y+8}" font-family="{_MONO}" font-size="8" '
        f'fill="{_INK3}" letter-spacing="0.18em" text-anchor="middle">'
        f'{_esc(meta,30)}</text>'
    )


def _branch_ring(branch_probabilities: list[tuple[str, float, str]],
                 r_out: float, r_in: float) -> str:
    """The model's branch distribution as an arc ring (used by 八字)."""
    if not branch_probabilities:
        return ""
    arc_total, arc_start = 320.0, 110.0
    total = sum(max(p, 0.0) for _, p, _ in branch_probabilities) or 1.0
    out: list[str] = []
    cursor = arc_start
    for _label, prob, btype in branch_probabilities:
        span = arc_total * (max(prob, 0.0) / total)
        gap = 2.0
        a0, a1 = cursor + gap / 2, cursor + span - gap / 2
        if a1 > a0:
            alpha = 0.30 + 0.62 * min(1.0, prob)
            if btype == "wishful":
                col = f"rgba(88,197,180,{alpha:.3f})"
            elif btype == "worst":
                col = f"rgba(255,94,110,{alpha:.3f})"
            else:
                col = f"rgba(139,140,255,{alpha:.3f})"
            rmid = (r_out + r_in) / 2
            out.append(
                f'<path d="{_open_arc(_CX, _CY, rmid, a0, a1)}" fill="none" '
                f'stroke="{col}" stroke-width="{r_out - r_in:.1f}" '
                f'stroke-linecap="round" filter="url(#drop)"></path>'
            )
        cursor += span
    return "".join(out)


# ----------------------------------------------------------------------
# Nye-Clock celestial primitives — a real gear movement + lit spheres,
# so the founder's "天干地支咬合" and Sun-Earth-Moon system carry into
# the in-app instruments as genuine forms, not stick-figure ticks.
# ----------------------------------------------------------------------

def _ring_path(r_out: float, r_in: float) -> str:
    """A full annulus as one even-odd path (cx/cy = instrument centre)."""
    def _circ(r: float) -> str:
        return (f"M {_CX - r:.2f} {_CY:.2f} "
                f"A {r:.2f} {r:.2f} 0 1 1 {_CX + r:.2f} {_CY:.2f} "
                f"A {r:.2f} {r:.2f} 0 1 1 {_CX - r:.2f} {_CY:.2f} Z")
    return _circ(r_out) + " " + _circ(r_in)


def _gear_ring(rim_in: float, rim_out: float, n_teeth: int,
               tooth_h: float, outward: bool, grad_id: str,
               edge_col: str, phase_deg: float = 0.0) -> str:
    """A real toothed gear ring — the founder's 天干地支咬合 mechanism.

    An annular rim plus `n_teeth` trapezoidal teeth. `outward=True` is a
    pinion (teeth point away from centre); `False` a ring gear (teeth
    point inward). A 10-tooth gold 天干 ring gear and a 12-tooth cyan
    地支 pinion interlock to render the 60-cycle as a precision movement.
    """
    pitch = 360.0 / n_teeth
    half_base, half_tip = pitch * 0.30, pitch * 0.15
    if outward:
        r_root, r_crest = rim_out, rim_out + tooth_h
    else:
        r_root, r_crest = rim_in, rim_in - tooth_h
    teeth: list[str] = []
    for i in range(n_teeth):
        a = phase_deg + i * pitch
        x0, y0 = _polar(_CX, _CY, r_root, a - half_base)
        x1, y1 = _polar(_CX, _CY, r_crest, a - half_tip)
        x2, y2 = _polar(_CX, _CY, r_crest, a + half_tip)
        x3, y3 = _polar(_CX, _CY, r_root, a + half_base)
        teeth.append(
            f'<path d="M {x0:.1f} {y0:.1f} L {x1:.1f} {y1:.1f} '
            f'L {x2:.1f} {y2:.1f} L {x3:.1f} {y3:.1f} Z"></path>'
        )
    return (
        f'<g fill="url(#{grad_id})" stroke="{edge_col}" '
        f'stroke-width="0.6" stroke-linejoin="round">'
        f'<path d="{_ring_path(rim_out, rim_in)}" fill-rule="evenodd"></path>'
        f'{"".join(teeth)}'
        # a fine engraved groove along the rim mid-line
        f'<circle cx="{_CX}" cy="{_CY}" r="{(rim_in + rim_out) / 2:.1f}" '
        f'fill="none" stroke="rgba(0,0,0,0.30)" stroke-width="0.7"></circle>'
        f'</g>'
    )


def _lit_sphere(cx: float, cy: float, r: float, grad_id: str,
                edge_col: str, *, corona: bool = False,
                glyph: str = "", glyph_col: str = "",
                glyph_size: float = 13.0) -> str:
    """A celestial body as a lit sphere — radial-gradient shading from an
    upper-left light, a soft specular highlight, an optional blurred
    corona. The Nye Clock Sun-Earth-Moon look in static SVG."""
    parts: list[str] = []
    if corona:
        parts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r * 2.4:.1f}" '
            f'fill="url(#corona-glow)"></circle>'
        )
    parts.append(
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" '
        f'fill="url(#{grad_id})" stroke="{edge_col}" '
        f'stroke-width="0.9"></circle>'
        f'<circle cx="{cx - r * 0.32:.1f}" cy="{cy - r * 0.36:.1f}" '
        f'r="{r * 0.30:.1f}" fill="rgba(255,255,255,0.45)"></circle>'
    )
    if glyph:
        parts.append(
            f'<text x="{cx:.1f}" y="{cy + 1:.1f}" font-family="{_SERIF}" '
            f'font-size="{glyph_size:.0f}" fill="{glyph_col}" '
            f'font-weight="700" text-anchor="middle" '
            f'dominant-baseline="middle">{glyph}</text>'
        )
    return "".join(parts)


# ======================================================================
# Instrument 1 — 八字 "Five-Phase Astrolabe"
# ======================================================================

def _sexagenary_index(pillar: tuple[int, int]) -> int:
    """The 0–59 position of a 干支 pillar on the great sexagenary cycle.

    Solves n ≡ stem (mod 10), n ≡ branch (mod 12) by CRT: n = (6s−5b) mod 60.
    """
    s, b = pillar
    return (6 * s - 5 * b) % 60


def _render_bazi(reading: LensReading,
                 branch_probabilities: list[tuple[str, float, str]],
                 top_label: str, top_value: str,
                 bottom_label: str, bottom_value: str,
                 meta: str) -> str:
    """八字 "Sexagenary Engine".

    Borrows the founder's Nye Clock celestial instrument: the outer ring
    is the 60-step 干支 cycle where the 10-stem (gold) and 12-branch
    (cyan) tick systems visibly mesh like two gears — LCM(10,12)=60.
    The user's four pillars sit as marked coordinates on that cycle.
    Inside: the 五行 phase ring, the model's branch arcs, an engraved
    dual-readout core.
    """
    bazi = reading.bazi
    balance = reading.balance or {}
    dom_key = dominant_element(balance) if balance else None

    body: list[str] = [_svg_open()]

    # --- outer frame: double hairline ring + 4 cardinal diamonds ---
    body.append(
        f'<circle cx="{_CX}" cy="{_CY}" r="227" fill="none" '
        f'stroke="{_HAIRLINE}" stroke-width="0.7"></circle>'
        f'<circle cx="{_CX}" cy="{_CY}" r="222" fill="none" '
        f'stroke="{_HAIR_STRONG}" stroke-width="1.0" opacity="0.6"></circle>'
    )
    for ang in (0, 90, 180, 270):
        dx, dy = _polar(_CX, _CY, 224.5, ang)
        body.append(
            f'<path d="M {dx:.1f} {dy-4:.1f} L {dx+4:.1f} {dy:.1f} '
            f'L {dx:.1f} {dy+4:.1f} L {dx-4:.1f} {dy:.1f} Z" '
            f'fill="{_INK2}"></path>'
        )

    # === SEXAGENARY MOVEMENT — a 10-tooth gold 天干 ring gear meshing
    # with a 12-tooth cyan 地支 pinion. LCM(10,12) = 60 is the great
    # cycle; the founder's "天干地支咬合", rendered as a real movement. ===
    # cyan 地支 pinion underneath, gold 天干 ring gear over it
    body.append(_gear_ring(197.0, 203.0, 12, 9.0, True,
                           "gear-cyan", "#0c2630", phase_deg=15.0))
    body.append(_gear_ring(214.0, 220.0, 10, 9.0, False,
                           "gear-gold", "#2a200a"))
    # a hairline pitch circle through the mesh zone
    body.append(
        f'<circle cx="{_CX}" cy="{_CY}" r="208.5" fill="none" '
        f'stroke="rgba(247,201,64,0.16)" stroke-width="0.7"></circle>'
    )

    # --- the four pillars as jewels countersunk into the gold ring ---
    if bazi is not None:
        pillar_seq = (
            (bazi.year_pillar,  "YEAR"),
            (bazi.month_pillar, "MONTH"),
            (bazi.day_pillar,   "DAY"),
            (bazi.hour_pillar,  "HOUR"),
        )
        for pil, _name in pillar_seq:
            n = _sexagenary_index(pil)
            ang = n * 6.0
            mx, my = _polar(_CX, _CY, 217.0, ang)
            # countersunk seat → lavender jewel → bright core
            body.append(
                f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="6.3" '
                f'fill="#0c0e14" stroke="rgba(0,0,0,0.55)" '
                f'stroke-width="1.3"></circle>'
                f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="5.0" '
                f'fill="{_SURFACE}" stroke="{_ACCENT}" stroke-width="1.5" '
                f'filter="url(#soft-glow)"></circle>'
                f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="2.0" '
                f'fill="{_ACCENT}"></circle>'
            )

    # --- 五行 phase ring (gradient wedges) ---
    r_out, r_in_base = 195.0, 150.0
    sector = 72.0
    for i, key in enumerate(WUXING_KEYS):
        share = max(0.0, balance.get(key, 0.0))
        # an even-thickness phase ring — restraint over the old lumpy
        # variable wedge. The chart's balance reads through wedge
        # *opacity* + the dominant element's lit plate, not jagged bars.
        r_in = r_out - 30.0
        a0 = i * sector - sector / 2
        a1 = a0 + sector
        is_dom = (key == dom_key)
        glow = ' filter="url(#soft-glow)"' if is_dom else ""
        # only the dominant phase is lit; the rest are faint tints — the
        # same "dark ring, one focal element" restraint as the 占星 wheel.
        wedge_op = 0.88 if is_dom else min(0.32, 0.05 + share * 1.15)
        body.append(
            f'<path d="{_arc_path(_CX, _CY, r_out, r_in, a0, a1)}" '
            f'fill="url(#wx-{key})" '
            f'fill-opacity="{wedge_op:.3f}" '
            f'stroke="{_CANVAS}" stroke-width="1.2"{glow}></path>'
        )
        mr = (r_out + r_in_base) / 2 + 3
        gx, gy = _polar(_CX, _CY, mr, (a0 + a1) / 2)
        plate_r = 13.0 if is_dom else 10.0
        body.append(
            f'<circle cx="{gx:.1f}" cy="{gy:.1f}" r="{plate_r}" '
            f'fill="{_SURFACE}" stroke="{WUXING_COLOR[key]}" '
            f'stroke-width="{1.4 if is_dom else 0.8}"></circle>'
            f'<text x="{gx:.1f}" y="{gy+0.5:.1f}" font-family="{_SERIF}" '
            f'font-size="{19 if is_dom else 13}" '
            f'fill="{_INK0 if is_dom else _INK1}" '
            f'font-weight="600" text-anchor="middle" '
            f'dominant-baseline="middle">{WUXING_HANZI[i]}</text>'
        )

    # --- a slim branch-distribution detail ring, channelled between two
    # hairlines so it reads as a fine inlay, not a competing band (the
    # full distribution lives in the main quantum heatmap) ---
    body.append(
        f'<circle cx="{_CX}" cy="{_CY}" r="146" fill="none" '
        f'stroke="{_HAIR_SOFT}" stroke-width="0.7"></circle>'
        f'<circle cx="{_CX}" cy="{_CY}" r="139.5" fill="none" '
        f'stroke="{_HAIR_SOFT}" stroke-width="0.6" opacity="0.7"></circle>'
    )
    body.append(_branch_ring(branch_probabilities, 135.0, 127.0))
    body.append(
        f'<circle cx="{_CX}" cy="{_CY}" r="112" fill="none" '
        f'stroke="{_HAIR_SOFT}" stroke-width="0.7"></circle>'
        f'<circle cx="{_CX}" cy="{_CY}" r="108.5" fill="none" '
        f'stroke="{_HAIRLINE}" stroke-width="0.8" opacity="0.6"></circle>'
    )

    # --- engraved core with dual readout ---
    body.append(_centre_readout(top_label, top_value,
                                bottom_label, bottom_value, meta,
                                r_core=100.0))

    # --- corner 八字 cartouches — 干支 + sexagenary index, gold/cyan ---
    if bazi is not None:
        pillars = (
            (bazi.year_pillar,  "YEAR",  (40, 40)),
            (bazi.month_pillar, "MONTH", (_VB - 40, 40)),
            (bazi.day_pillar,   "DAY",   (40, _VB - 40)),
            (bazi.hour_pillar,  "HOUR",  (_VB - 40, _VB - 40)),
        )
        for pil, name, (px, py) in pillars:
            txt = pillar_text(pil)
            idx = _sexagenary_index(pil)
            stem_ch = txt[0] if txt else ""
            branch_ch = txt[1] if len(txt) > 1 else ""
            body.append(
                f'<g transform="translate({px-37},{py-20})">'
                f'<rect x="0" y="0" width="74" height="40" rx="7" '
                f'fill="{_SURFACE2}" stroke="{_HAIRLINE}" stroke-width="1"></rect>'
                # 天干 in gold, 地支 in cyan — the mesh, restated
                f'<text x="37" y="18" font-family="{_SERIF}" font-size="18" '
                f'text-anchor="middle" dominant-baseline="middle" '
                f'font-weight="600">'
                f'<tspan fill="{_GAL_GOLD}">{_esc(stem_ch,1)}</tspan>'
                f'<tspan fill="{_GAL_CYAN}">{_esc(branch_ch,1)}</tspan>'
                f'</text>'
                f'<text x="37" y="32" font-family="{_MONO}" font-size="7" '
                f'fill="{_INK3}" letter-spacing="0.12em" text-anchor="middle">'
                f'{name} · {idx + 1:02d}/60</text>'
                f'</g>'
            )

    body.append('</svg>')
    return "".join(body)


# ======================================================================
# Instrument 2 — 易经 hexagram
# ======================================================================

def _render_iching(reading: LensReading,
                    model_value: str, combined_value: str,
                    meta: str) -> str:
    hx: Hexagram = reading.hexagram  # type: ignore[assignment]
    body: list[str] = [_svg_open()]

    # framed plate
    body.append(
        f'<rect x="40" y="40" width="{_VB-80}" height="{_VB-80}" rx="14" '
        f'fill="{_SURFACE}" stroke="{_HAIRLINE}" stroke-width="1.2" '
        f'filter="url(#drop)"></rect>'
        f'<rect x="48" y="48" width="{_VB-96}" height="{_VB-96}" rx="10" '
        f'fill="none" stroke="rgba(216,166,87,0.18)" stroke-width="0.8"></rect>'
    )

    # heading: 卦名 + number
    body.append(
        f'<text x="{_CX}" y="86" font-family="{_MONO}" font-size="9.5" '
        f'fill="{_INK2}" letter-spacing="0.28em" text-anchor="middle">'
        f'I CHING · HEXAGRAM {hx.number:02d}</text>'
        f'<text x="{_CX}" y="128" font-family="{_SERIF}" font-size="46" '
        f'fill="{_AMBER}" font-weight="600" text-anchor="middle" '
        f'filter="url(#num-glow)">{_esc(hx.name,4)}</text>'
    )

    # the 6 lines — bottom (index 0) at the bottom
    line_w = 168.0
    line_h = 17.0
    gap_y = 12.0
    x_left = _CX - line_w / 2
    base_y = 322.0
    for i in range(6):
        yang = hx.lines[i]
        y = base_y - i * (line_h + gap_y)
        is_changing = i in hx.changing
        if yang:
            body.append(
                f'<rect x="{x_left:.1f}" y="{y:.1f}" width="{line_w:.1f}" '
                f'height="{line_h:.1f}" rx="3.5" fill="url(#bronze)" '
                f'stroke="#7a5a28" stroke-width="0.8" filter="url(#drop)"></rect>'
            )
        else:
            seg = (line_w - 26.0) / 2
            body.append(
                f'<rect x="{x_left:.1f}" y="{y:.1f}" width="{seg:.1f}" '
                f'height="{line_h:.1f}" rx="3.5" fill="url(#bronze)" '
                f'stroke="#7a5a28" stroke-width="0.8" filter="url(#drop)"></rect>'
                f'<rect x="{x_left+seg+26:.1f}" y="{y:.1f}" width="{seg:.1f}" '
                f'height="{line_h:.1f}" rx="3.5" fill="url(#bronze)" '
                f'stroke="#7a5a28" stroke-width="0.8" filter="url(#drop)"></rect>'
            )
        if is_changing:
            cx = x_left + line_w + 18
            cy = y + line_h / 2
            body.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" fill="none" '
                f'stroke="{_TEAL}" stroke-width="1.4"></circle>'
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="1.6" '
                f'fill="{_TEAL}"></circle>'
            )

    # trigram labels (upper / lower)
    ut, lt = hx.upper_trigram, hx.lower_trigram
    body.append(
        f'<text x="{x_left-30:.1f}" y="{base_y - 3.5*(line_h+gap_y)+8:.1f}" '
        f'font-family="{_SERIF}" font-size="26" fill="{_INK1}" '
        f'text-anchor="middle">{TRIGRAM_SYMBOL[ut]}</text>'
        f'<text x="{x_left-30:.1f}" y="{base_y - 3.5*(line_h+gap_y)+30:.1f}" '
        f'font-family="{_MONO}" font-size="8" fill="{_INK3}" '
        f'letter-spacing="0.1em" text-anchor="middle">UPPER {TRIGRAM_HANZI[ut]}</text>'
        f'<text x="{x_left-30:.1f}" y="{base_y - 1.0*(line_h+gap_y)+4:.1f}" '
        f'font-family="{_SERIF}" font-size="26" fill="{_INK1}" '
        f'text-anchor="middle">{TRIGRAM_SYMBOL[lt]}</text>'
        f'<text x="{x_left-30:.1f}" y="{base_y - 1.0*(line_h+gap_y)+26:.1f}" '
        f'font-family="{_MONO}" font-size="8" fill="{_INK3}" '
        f'letter-spacing="0.1em" text-anchor="middle">LOWER {TRIGRAM_HANZI[lt]}</text>'
    )

    # changing-lines note
    if hx.changing:
        note = "moving lines: " + ", ".join(str(c + 1) for c in hx.changing)
    else:
        note = "no moving lines — a settled reading"
    body.append(
        f'<text x="{_CX}" y="368" font-family="{_MONO}" font-size="8.5" '
        f'fill="{_TEAL if hx.changing else _INK3}" letter-spacing="0.08em" '
        f'text-anchor="middle">{_esc(note,48)}</text>'
    )

    body.append(_footer_band(model_value, combined_value, meta))
    body.append('</svg>')
    return "".join(body)


# ======================================================================
# Instrument 3 — 塔罗 3-card spread
# ======================================================================

def _tarot_glyph(name: str, cx: float, cy: float, col: str) -> str:
    """A compact line-art emblem for a Tarot card, ~46px tall.

    Drawn inside a medallion by the caller; stroke kept fine (1.7px)
    so the emblem reads as an engraved inlay, not a sketch.
    """
    s = f'stroke="{col}" stroke-width="1.7" fill="none" ' \
        'stroke-linecap="round" stroke-linejoin="round"'
    sf = f'fill="{col}" stroke="none"'
    if name == "star":
        pts = []
        for k in range(16):
            rr = 22 if k % 2 == 0 else 9
            a = math.radians(k * 22.5 - 90)
            pts.append(f"{cx+rr*math.cos(a):.1f},{cy+rr*math.sin(a):.1f}")
        return f'<polygon points="{" ".join(pts)}" {sf} opacity="0.92"></polygon>'
    if name == "sun":
        rays = "".join(
            f'<line x1="{cx+11*math.cos(math.radians(k*45)):.1f}" '
            f'y1="{cy+11*math.sin(math.radians(k*45)):.1f}" '
            f'x2="{cx+21*math.cos(math.radians(k*45)):.1f}" '
            f'y2="{cy+21*math.sin(math.radians(k*45)):.1f}" {s}></line>'
            for k in range(8))
        return f'<circle cx="{cx}" cy="{cy}" r="9" {sf}></circle>{rays}'
    if name in ("moon", "crescent"):
        return (f'<path d="M {cx+9} {cy-17} A 18 18 0 1 0 {cx+9} {cy+17} '
                f'A 13 13 0 1 1 {cx+9} {cy-17} Z" {sf} opacity="0.9"></path>')
    if name == "tower":
        return (f'<rect x="{cx-13}" y="{cy-8}" width="26" height="28" {s}></rect>'
                f'<path d="M {cx-15} {cy-8} L {cx} {cy-22} L {cx+15} {cy-8}" {s}></path>'
                f'<line x1="{cx}" y1="{cy-2}" x2="{cx}" y2="{cy+20}" {s}></line>')
    if name == "heart":
        return (f'<path d="M {cx} {cy+18} C {cx-26} {cy-2} {cx-13} {cy-22} '
                f'{cx} {cy-8} C {cx+13} {cy-22} {cx+26} {cy-2} {cx} {cy+18} Z" '
                f'{sf} opacity="0.9"></path>')
    if name == "scales":
        return (f'<line x1="{cx}" y1="{cy-20}" x2="{cx}" y2="{cy+18}" {s}></line>'
                f'<line x1="{cx-20}" y1="{cy-12}" x2="{cx+20}" y2="{cy-12}" {s}></line>'
                f'<path d="M {cx-20} {cy-12} L {cx-27} {cy+4} L {cx-13} {cy+4} Z" {s}></path>'
                f'<path d="M {cx+20} {cy-12} L {cx+13} {cy+4} L {cx+27} {cy+4} Z" {s}></path>')
    if name == "wheel":
        spokes = "".join(
            f'<line x1="{cx+5*math.cos(math.radians(k*45)):.1f}" '
            f'y1="{cy+5*math.sin(math.radians(k*45)):.1f}" '
            f'x2="{cx+19*math.cos(math.radians(k*45)):.1f}" '
            f'y2="{cy+19*math.sin(math.radians(k*45)):.1f}" {s}></line>'
            for k in range(8))
        return (f'<circle cx="{cx}" cy="{cy}" r="20" {s}></circle>'
                f'<circle cx="{cx}" cy="{cy}" r="5" {s}></circle>{spokes}')
    if name in ("wand", "spark", "trumpet", "lantern", "keys", "pendulum"):
        return (f'<line x1="{cx}" y1="{cy+20}" x2="{cx}" y2="{cy-16}" {s}></line>'
                f'<circle cx="{cx}" cy="{cy-18}" r="6" {sf} opacity="0.92"></circle>'
                f'<line x1="{cx-9}" y1="{cy-9}" x2="{cx+9}" y2="{cy-9}" {s}></line>')
    if name in ("chariot", "throne"):
        return (f'<rect x="{cx-16}" y="{cy-14}" width="32" height="20" rx="3" {s}></rect>'
                f'<circle cx="{cx-10}" cy="{cy+13}" r="7" {s}></circle>'
                f'<circle cx="{cx+10}" cy="{cy+13}" r="7" {s}></circle>')
    if name in ("lion", "chains", "scythe"):
        return (f'<circle cx="{cx}" cy="{cy-3}" r="15" {s}></circle>'
                f'<path d="M {cx-7} {cy+12} Q {cx} {cy+22} {cx+7} {cy+12}" {s}></path>'
                f'<circle cx="{cx-6}" cy="{cy-5}" r="2.2" {sf}></circle>'
                f'<circle cx="{cx+6}" cy="{cy-5}" r="2.2" {sf}></circle>')
    if name in ("chalice", "venus", "wreath"):
        return (f'<path d="M {cx-15} {cy-14} Q {cx} {cy+14} {cx+15} {cy-14} Z" {s}></path>'
                f'<line x1="{cx}" y1="{cy+2}" x2="{cx}" y2="{cy+18}" {s}></line>'
                f'<line x1="{cx-11}" y1="{cy+18}" x2="{cx+11}" y2="{cy+18}" {s}></line>')
    # default emblem — concentric diamond
    return (f'<path d="M {cx} {cy-20} L {cx+20} {cy} L {cx} {cy+20} '
            f'L {cx-20} {cy} Z" {s}></path>'
            f'<circle cx="{cx}" cy="{cy}" r="6" {sf}></circle>')


def _render_tarot(reading: LensReading,
                  model_value: str, combined_value: str,
                  meta: str) -> str:
    draw: TarotDraw = reading.tarot  # type: ignore[assignment]
    body: list[str] = [_svg_open()]

    body.append(
        f'<text x="{_CX}" y="62" font-family="{_MONO}" font-size="9.5" '
        f'fill="{_INK2}" letter-spacing="0.28em" text-anchor="middle">'
        f'TAROT · PAST · PRESENT · FUTURE</text>'
    )

    card_w, card_h = 124.0, 234.0
    gap = 16.0
    total_w = card_w * 3 + gap * 2
    x0 = _CX - total_w / 2
    top = 84.0

    for i, (card, is_rev) in enumerate(zip(draw.cards, draw.reversed)):
        cx0 = x0 + i * (card_w + card_h * 0 + card_w * 0 + gap) + i * 0
        cx0 = x0 + i * (card_w + gap)
        ccx = cx0 + card_w / 2
        # present card sits slightly raised + accented
        is_present = (i == 1)
        lift = 10 if is_present else 0
        cy0 = top - lift
        accent = _ACCENT if is_present else _HAIRLINE
        # card plate — top-lit face gradient + double frame
        body.append(
            f'<g filter="url(#drop)">'
            f'<rect x="{cx0:.1f}" y="{cy0:.1f}" width="{card_w}" '
            f'height="{card_h}" rx="11" fill="url(#card-face)" '
            f'stroke="{accent}" stroke-width="{1.6 if is_present else 1.1}"></rect>'
            f'</g>'
            f'<rect x="{cx0+6:.1f}" y="{cy0+6:.1f}" width="{card_w-12}" '
            f'height="{card_h-12}" rx="7" fill="none" '
            f'stroke="rgba(255,255,255,0.06)" stroke-width="0.8"></rect>'
        )
        # ornamental corner ticks
        for ox, oy in ((cx0+12, cy0+12), (cx0+card_w-12, cy0+12),
                       (cx0+12, cy0+card_h-12), (cx0+card_w-12, cy0+card_h-12)):
            body.append(
                f'<circle cx="{ox:.1f}" cy="{oy:.1f}" r="1.7" '
                f'fill="{_INK3}"></circle>'
            )
        # roman numeral
        body.append(
            f'<text x="{ccx:.1f}" y="{cy0+30:.1f}" font-family="{_SERIF}" '
            f'font-size="15" fill="{_INK2}" text-anchor="middle" '
            f'font-weight="600">{_roman(card.number)}</text>'
        )
        # emblem — set inside a medallion so even a simple glyph reads
        # as a crafted inlay. Reversed cards rotate the emblem 180°.
        gcx, gcy = ccx, cy0 + card_h / 2 - 8
        glyph_col = _AMBER if not is_rev else _INK2
        med_r = 35.0
        body.append(
            f'<circle cx="{gcx:.1f}" cy="{gcy:.1f}" r="{med_r}" '
            f'fill="rgba(216,166,87,0.05)" stroke="{_HAIR_STRONG}" '
            f'stroke-width="0.9"></circle>'
            f'<circle cx="{gcx:.1f}" cy="{gcy:.1f}" r="{med_r-4:.1f}" '
            f'fill="none" stroke="{_HAIR_SOFT}" stroke-width="0.7"></circle>'
        )
        # glyph scaled to 0.78 to sit comfortably within the medallion
        rot = f'rotate(180 {gcx:.1f} {gcy:.1f}) ' if is_rev else ""
        body.append(
            f'<g transform="{rot}translate({gcx:.1f} {gcy:.1f}) '
            f'scale(0.78) translate({-gcx:.1f} {-gcy:.1f})">'
            f'{_tarot_glyph(card.glyph, gcx, gcy, glyph_col)}</g>'
        )
        # card name
        body.append(
            f'<text x="{ccx:.1f}" y="{cy0+card_h-40:.1f}" font-family="{_SERIF}" '
            f'font-size="15" fill="{_INK0}" text-anchor="middle" '
            f'font-weight="600">{_esc(card.name,22)}</text>'
        )
        if is_rev:
            body.append(
                f'<text x="{ccx:.1f}" y="{cy0+card_h-24:.1f}" '
                f'font-family="{_MONO}" font-size="7.5" fill="{_CORAL}" '
                f'letter-spacing="0.16em" text-anchor="middle">REVERSED</text>'
            )
        # position label below the card
        body.append(
            f'<text x="{ccx:.1f}" y="{top+card_h+22:.1f}" font-family="{_MONO}" '
            f'font-size="8.5" fill="{_INK2}" letter-spacing="0.2em" '
            f'text-anchor="middle">{TAROT_POSITIONS[i].upper()}</text>'
        )

    body.append(_footer_band(model_value, combined_value, meta))
    body.append('</svg>')
    return "".join(body)


def _roman(n: int) -> str:
    if n == 0:
        return "0"
    vals = [(10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    out = ""
    for v, sym in vals:
        while n >= v:
            out += sym
            n -= v
    return out


# ======================================================================
# Instrument 4 — 紫微 12-palace chart
# ======================================================================

# 12 palace cells laid out as the classic 4×4 ring (clockwise from
# top-left). The 4 centre cells form the summary plate.
_ZIWEI_CELL_XY: tuple[tuple[int, int], ...] = (
    (0, 0), (1, 0), (2, 0), (3, 0),
    (3, 1), (3, 2), (3, 3),
    (2, 3), (1, 3), (0, 3),
    (0, 2), (0, 1),
)


# 吉 / 中 / 凶 star-nature colours.
_STAR_COLOR: dict[int, str] = {1: _INK0, 0: _INK1, -1: "#c98b92"}


def _render_ziwei(reading: LensReading,
                  model_value: str, combined_value: str,
                  meta: str) -> str:
    chart: ZiWeiChart = reading.ziwei  # type: ignore[assignment]
    body: list[str] = [_svg_open()]

    body.append(
        f'<text x="{_CX}" y="56" font-family="{_MONO}" font-size="9.5" '
        f'fill="{_INK2}" letter-spacing="0.26em" text-anchor="middle">'
        f'ZIWEI DOU SHU · 12 PALACES</text>'
    )

    grid_x, grid_y = 58.0, 76.0
    cell = 91.0

    # outer frame — double hairline, the structural one stronger
    body.append(
        f'<rect x="{grid_x-7:.1f}" y="{grid_y-7:.1f}" width="{cell*4+14:.1f}" '
        f'height="{cell*4+14:.1f}" rx="14" fill="none" '
        f'stroke="{_HAIRLINE}" stroke-width="1.1"></rect>'
        f'<rect x="{grid_x-3:.1f}" y="{grid_y-3:.1f}" width="{cell*4+6:.1f}" '
        f'height="{cell*4+6:.1f}" rx="11" fill="none" '
        f'stroke="{_HAIR_SOFT}" stroke-width="0.8"></rect>'
    )

    for idx, (gx, gy) in enumerate(_ZIWEI_CELL_XY):
        palace = ZIWEI_PALACES[idx]
        x = grid_x + gx * cell
        y = grid_y + gy * cell
        is_ming = (palace == "ming")
        gap = 3.0
        cw = cell - gap
        # cell plate
        glow = ' filter="url(#soft-glow)"' if is_ming else ""
        body.append(
            f'<rect x="{x+gap/2:.1f}" y="{y+gap/2:.1f}" width="{cw:.1f}" '
            f'height="{cw:.1f}" rx="8" fill="url(#cell-grad)" '
            f'stroke="{_ACCENT if is_ming else _HAIR_SOFT}" '
            f'stroke-width="{1.4 if is_ming else 0.9}"{glow}></rect>'
        )
        if is_ming:
            # faint lavender wash + a top accent rule
            body.append(
                f'<rect x="{x+gap/2:.1f}" y="{y+gap/2:.1f}" width="{cw:.1f}" '
                f'height="{cw:.1f}" rx="8" fill="rgba(139,140,255,0.07)"></rect>'
            )
        # top accent hairline inside the cell (craft detail)
        body.append(
            f'<line x1="{x+gap/2+10:.1f}" y1="{y+gap/2+0.5:.1f}" '
            f'x2="{x+cw-gap/2:.1f}" y2="{y+gap/2+0.5:.1f}" '
            f'stroke="{_ACCENT if is_ming else _HAIR_STRONG}" '
            f'stroke-width="{1.4 if is_ming else 0.8}" '
            f'opacity="{0.9 if is_ming else 0.5}"></line>'
        )
        # palace-name tab (small recessed pill, top-left)
        tab_x, tab_y = x + gap / 2 + 7, y + gap / 2 + 8
        body.append(
            f'<rect x="{tab_x:.1f}" y="{tab_y:.1f}" width="34" height="18" '
            f'rx="5" fill="{_SURFACE3}" '
            f'stroke="{_ACCENT if is_ming else _HAIR_SOFT}" '
            f'stroke-width="0.8" opacity="0.95"></rect>'
            f'<text x="{tab_x+17:.1f}" y="{tab_y+13:.1f}" '
            f'font-family="{_SERIF}" font-size="12.5" '
            f'fill="{_ACCENT if is_ming else _INK1}" font-weight="600" '
            f'text-anchor="middle">{ZIWEI_PALACE_HANZI[palace]}</text>'
        )
        # stars — centred column, coloured by 吉/中/凶 nature
        stars = chart.palace_stars.get(palace, [])
        scx = x + cell / 2
        sy0 = y + gap / 2 + 48
        for si, star in enumerate(stars[:4]):
            col = _STAR_COLOR.get(_STAR_NATURE.get(star, 0), _INK1)
            body.append(
                f'<text x="{scx:.1f}" y="{sy0+si*16:.1f}" '
                f'font-family="{_SERIF}" font-size="14.5" fill="{col}" '
                f'text-anchor="middle" font-weight="500">'
                f'{_esc(ziwei_star_hanzi(star),2)}</text>'
            )
        if not stars:
            body.append(
                f'<circle cx="{scx:.1f}" cy="{y+cell/2+10:.1f}" r="1.6" '
                f'fill="{_INK3}"></circle>'
            )

    # centre summary plate — the engraved-core treatment
    cxp = grid_x + cell
    cyp = grid_y + cell
    cw2 = cell * 2
    body.append(
        f'<rect x="{cxp:.1f}" y="{cyp:.1f}" width="{cw2:.1f}" '
        f'height="{cw2:.1f}" rx="12" fill="url(#core-grad)" '
        f'stroke="{_HAIRLINE}" stroke-width="1.2"></rect>'
        f'<rect x="{cxp+6:.1f}" y="{cyp+6:.1f}" width="{cw2-12:.1f}" '
        f'height="{cw2-12:.1f}" rx="9" fill="none" '
        f'stroke="rgba(255,255,255,0.05)" stroke-width="0.7"></rect>'
        f'<text x="{_CX}" y="{cyp+46:.1f}" font-family="{_MONO}" '
        f'font-size="9" fill="{_INK2}" letter-spacing="0.22em" '
        f'text-anchor="middle">MODEL</text>'
        f'<text x="{_CX}" y="{cyp+72:.1f}" font-family="{_SERIF}" '
        f'font-size="27" fill="{_INK0}" font-weight="600" '
        f'text-anchor="middle" filter="url(#num-glow)">'
        f'{_esc(model_value,8)}</text>'
        f'<line x1="{_CX-26}" y1="{cyp+88:.1f}" x2="{_CX+26}" '
        f'y2="{cyp+88:.1f}" stroke="{_HAIRLINE}" stroke-width="0.9"></line>'
        f'<circle cx="{_CX-26}" cy="{cyp+88:.1f}" r="1.5" fill="{_INK3}"></circle>'
        f'<circle cx="{_CX+26}" cy="{cyp+88:.1f}" r="1.5" fill="{_INK3}"></circle>'
        f'<text x="{_CX}" y="{cyp+108:.1f}" font-family="{_MONO}" '
        f'font-size="9" fill="{_INK2}" letter-spacing="0.22em" '
        f'text-anchor="middle">COMBINED</text>'
        f'<text x="{_CX}" y="{cyp+134:.1f}" font-family="{_SERIF}" '
        f'font-size="27" fill="{_ACCENT}" font-weight="600" '
        f'text-anchor="middle" filter="url(#num-glow)">'
        f'{_esc(combined_value,8)}</text>'
    )
    body.append(
        f'<text x="{_CX}" y="{_VB-28:.1f}" font-family="{_MONO}" '
        f'font-size="8.5" fill="{_INK3}" letter-spacing="0.18em" '
        f'text-anchor="middle">{_esc(meta,40)}</text>'
    )

    body.append('</svg>')
    return "".join(body)


# ======================================================================
# Instrument 5 — 占星 natal-chart wheel
# ======================================================================

def _render_astro(reading: LensReading,
                  branch_probabilities: list[tuple[str, float, str]],
                  top_label: str, top_value: str,
                  bottom_label: str, bottom_value: str,
                  meta: str) -> str:
    chart: NatalChart = reading.natal  # type: ignore[assignment]
    body: list[str] = [_svg_open()]

    # --- outer frame + cardinal diamonds ---
    body.append(
        f'<circle cx="{_CX}" cy="{_CY}" r="226" fill="none" '
        f'stroke="{_HAIRLINE}" stroke-width="0.7"></circle>'
        f'<circle cx="{_CX}" cy="{_CY}" r="221" fill="none" '
        f'stroke="{_HAIRLINE}" stroke-width="1.1"></circle>'
    )
    for ang in (0, 90, 180, 270):
        dx, dy = _polar(_CX, _CY, 223.5, ang)
        body.append(
            f'<path d="M {dx:.1f} {dy-4:.1f} L {dx+4:.1f} {dy:.1f} '
            f'L {dx:.1f} {dy+4:.1f} L {dx-4:.1f} {dy:.1f} Z" '
            f'fill="{_INK2}"></path>'
        )

    # --- graduated tick ring ---
    for i in range(72):
        ang = i * 5.0
        major = (i % 6 == 0)
        x1, y1 = _polar(_CX, _CY, 219.0, ang)
        x2, y2 = _polar(_CX, _CY, 208.0 if major else 213.0, ang)
        body.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{_INK1 if major else _INK3}" '
            f'stroke-width="{1.1 if major else 0.6}" '
            f'opacity="{0.85 if major else 0.5}"></line>'
        )

    # --- 12 zodiac sectors (30° each, Aries centred at top) ---
    r_out, r_in = 202.0, 152.0
    big3 = {chart.sun, chart.moon}
    for i, sign in enumerate(ZODIAC):
        a0 = i * 30.0 - 15.0
        a1 = a0 + 30.0
        col = ASTRO_ELEMENT_COLOR[sign.element]
        is_sun = (i == chart.sun)
        is_big3 = (i in big3)
        # a dark, restrained ring — only the sun-sign sector is lit, the
        # moon's gets a gentle tint, the rest are near-black. The 12
        # glyphs + hairline dividers carry the structure.
        alpha = 0.60 if is_sun else (0.19 if is_big3 else 0.085)
        glow = ' filter="url(#soft-glow)"' if is_sun else ""
        body.append(
            f'<path d="{_arc_path(_CX, _CY, r_out, r_in, a0, a1)}" '
            f'fill="{col}" fill-opacity="{alpha:.3f}" '
            f'stroke="{_HAIRLINE}" stroke-width="0.8"{glow}></path>'
        )
        # zodiac glyph at sector midpoint
        mr = (r_out + r_in) / 2
        gx, gy = _polar(_CX, _CY, mr, i * 30.0)
        body.append(
            f'<text x="{gx:.1f}" y="{gy+1:.1f}" font-family="{_SERIF}" '
            f'font-size="{23 if is_sun else 18}" '
            f'fill="{_INK0 if is_big3 else _INK1}" '
            f'font-weight="600" text-anchor="middle" '
            f'dominant-baseline="middle">{sign.glyph}</text>'
        )

    # --- Sun + Moon on orbital paths — the Nye Clock Sun-Earth-Moon
    # system, borrowed as static SVG: two concentric galaxy-blue orbits,
    # a lit-sphere body on each at its true sign's angle. (No ascendant
    # ring — the rising sign needs a birth latitude/longitude this
    # console does not collect.) ---
    sun_orbit, moon_orbit = 116.0, 140.0
    for orad in (moon_orbit, sun_orbit):
        # orbit path — a fine solid ring with a faint outer companion
        body.append(
            f'<circle cx="{_CX}" cy="{_CY}" r="{orad + 1.7:.1f}" fill="none" '
            f'stroke="{_GAL_BLUE}" stroke-width="0.6" opacity="0.13"></circle>'
            f'<circle cx="{_CX}" cy="{_CY}" r="{orad:.1f}" fill="none" '
            f'stroke="{_GAL_BLUE}" stroke-width="1.0" opacity="0.46"></circle>'
        )
    # 12 sign-graduation ticks on the inner (sun) orbit
    for k in range(12):
        tx1, ty1 = _polar(_CX, _CY, sun_orbit - 2.6, k * 30.0)
        tx2, ty2 = _polar(_CX, _CY, sun_orbit + 2.6, k * 30.0)
        body.append(
            f'<line x1="{tx1:.1f}" y1="{ty1:.1f}" x2="{tx2:.1f}" '
            f'y2="{ty2:.1f}" stroke="{_GAL_BLUE}" stroke-width="0.6" '
            f'opacity="0.34"></line>'
        )
    # the Moon — a lit silver sphere on the outer orbit
    mmx, mmy = _polar(_CX, _CY, moon_orbit, chart.moon * 30.0)
    body.append(
        f'<line x1="{_CX}" y1="{_CY}" x2="{mmx:.1f}" y2="{mmy:.1f}" '
        f'stroke="{_GAL_BLUE}" stroke-width="0.6" opacity="0.16"></line>'
    )
    body.append(_lit_sphere(mmx, mmy, 12.0, "sphere-moon", "#2c3346",
                            glyph="☽", glyph_col="#2a2f3e",
                            glyph_size=14.0))
    # the Sun — a lit gold sphere with a corona on the inner orbit
    ssx, ssy = _polar(_CX, _CY, sun_orbit, chart.sun * 30.0)
    body.append(
        f'<line x1="{_CX}" y1="{_CY}" x2="{ssx:.1f}" y2="{ssy:.1f}" '
        f'stroke="{_GAL_GOLD}" stroke-width="0.7" opacity="0.22"></line>'
    )
    body.append(_lit_sphere(ssx, ssy, 15.0, "sphere-sun", "#6e4d09",
                            corona=True, glyph="☉", glyph_col="#5a3f06",
                            glyph_size=17.0))

    # The natal wheel's "model" half is the orbital system above + the
    # tri-metric chips below the card; no separate branch ring here, so
    # the Sun-Earth-Moon orbits read cleanly (branch_probabilities is
    # accepted for signature parity with the other instruments).
    _ = branch_probabilities

    # --- engraved core with dual readout ---
    body.append(_centre_readout(top_label, top_value,
                                bottom_label, bottom_value, meta,
                                r_core=99.0))

    # --- corner cartouches: Sun sign / Moon sign + their element·mode ---
    sun_sign = ZODIAC[chart.sun]
    moon_sgn = ZODIAC[chart.moon]
    corners = (
        (f"{sun_sign.glyph} {sun_sign.name}", "SUN SIGN", (40, 40)),
        (f"{moon_sgn.glyph} {moon_sgn.name}", "MOON SIGN", (_VB - 40, 40)),
        (f"{sun_sign.element} · {sun_sign.modality}",
         "SUN", (40, _VB - 40)),
        (f"{moon_sgn.element} · {moon_sgn.modality}",
         "MOON", (_VB - 40, _VB - 40)),
    )
    for text, name, (px, py) in corners:
        body.append(
            f'<g transform="translate({px-44},{py-19})">'
            f'<rect x="0" y="0" width="88" height="38" rx="6" '
            f'fill="{_SURFACE2}" stroke="{_HAIRLINE}" stroke-width="1"></rect>'
            f'<text x="44" y="17" font-family="{_SERIF}" font-size="13" '
            f'fill="{_INK0}" font-weight="600" text-anchor="middle" '
            f'dominant-baseline="middle">{_esc(text,22)}</text>'
            f'<text x="44" y="30" font-family="{_MONO}" font-size="7" '
            f'fill="{_INK3}" letter-spacing="0.16em" text-anchor="middle">'
            f'{name}</text>'
            f'</g>'
        )

    body.append('</svg>')
    return "".join(body)


# ======================================================================
# Instrument 7 — the Nye Clock 玄学 view.
#
# [OMY-V415 / M2 / Acceptance #61] REBUILT from the canonical final Nye
# Clock — ``~/Downloads/UCSB/Adonyth/tw_.html`` (the founder's real 3-D
# WebGL clock; the project's own sync scripts name it the sole source
# file). The earlier renderer was built from the WRONG reference
# (``academic-cv-site/nye-clock-backdrop.html`` — a separate, older
# CV-site backdrop embed) and is superseded.
#
# What tw_.html actually looks like (recovered by screenshotting it in
# headless Chrome with software WebGL, then reading its CSS/structure):
#   • A deep-space backdrop — a near-black gradient (#111722 → #080c14)
#     with a faint starfield and violet/blue nebula glow.
#   • The EARTH globe is the heart of the 玄学 instrument — a textured
#     blue-green sphere inside a soft blue atmospheric halo.
#   • The 干支 ride the Earth as small CIRCULAR COIN tokens — each a
#     thin bezel ring + the character — arranged in concentric rings
#     around the globe, colour-coded by 五行 (the tw_.html element
#     palette: wood #5AAA6A / fire #D4623C / earth #C09A6A /
#     metal #C4AA5A / water #4A8ED4).
#   • The active 八字 pillar characters glow LARGE and free-floating
#     in space (a big element-coloured 天干 + 地支), exactly the
#     enlarged glowing glyphs in tw_.html.
#   • The SUN is a separate body off to one side — a white-hot core
#     with a layered golden corona (NOT at the wheel centre).
#   • The MOON is a small lit grey sphere near the Earth.
#
# This is a lightweight static SVG (no WebGL / Three.js / canvas / GPU
# — the founder vetoed embedding the real 3-D); it embeds verbatim via
# st.markdown(unsafe_allow_html=True).
#
# 玄学 data mapping (legible, not arbitrary):
#   • Earth at centre     — the 占星 Sun sign tints the atmospheric halo.
#   • 干支 coin rings      — the 60-step sexagenary cycle ringed around
#                           the Earth: an inner 地支 coin ring (12) and
#                           an outer 天干 coin ring (10), each coin's
#                           hue from its 五行.
#   • Active glyphs        — the day pillar's 天干 + 地支 glow large.
#   • Four pillar coins    — the 年/月/日/时 pillars are marked on the
#                           rings as lit jewelled coins.
#   • Moon                — placed at the 占星 Moon-sign angle.
#   • Sun                  — off-axis; the 占星 Sun sign tints its rim.
# ======================================================================

# Nye Clock canvas.
_NYE_VB_W = 1000
_NYE_VB_H = 920
_NYE_CX = 500.0
_NYE_CY = 455.0
_NYE_OBLIQUE_DEG = 20.0
# Elliptical Earth orbit + its stem/branch rails (legacy renderer).
_NYE_EARTH_RX = 330.0
_NYE_EARTH_RY = 196.0
_NYE_STEM_RX = 352.0
_NYE_STEM_RY = 208.0
_NYE_BR_RX = 306.0
_NYE_BR_RY = 182.0
_NYE_MESH_OUT_RX = 364.0
_NYE_MESH_OUT_RY = 214.0
_NYE_MESH_IN_RX = 296.0
_NYE_MESH_IN_RY = 174.0
# Moon orbit around the Earth.
_NYE_MOON_RX = 61.0
_NYE_MOON_RY = 37.0

# --- tw_.html-canonical 玄学-view layout (Acceptance #64) ----------
# Faithful to the real Nye Clock (~/Downloads/UCSB/Adonyth/tw_.html):
# a Sun-DOMINANT deep-space scene. The Sun is the large focal body in
# the upper-right with several concentric translucent corona rings;
# the Earth is SMALL, tucked into the lower-left corner, with a thin
# orbital ring, a small Moon, and a TIGHT cluster of 干支 coin tokens
# ringed close around it. Large, faint 干支 glyphs float SPARSELY
# across the black field. Lots of negative space; one focal glow.
#
# The Sun — the dominant body, upper-right.
_TW_SUN_CX = 648.0
_TW_SUN_CY = 322.0
# The Earth — small, lower-left corner.
_TW_EARTH_CX = 236.0
_TW_EARTH_CY = 648.0
_TW_EARTH_R = 58.0           # the Earth globe radius — small
# Two TIGHT concentric rings of 干支 coins hugging the corner Earth.
_TW_BRANCH_RING_R = 104.0    # inner ring — 12 地支 coins
_TW_STEM_RING_R = 150.0      # outer ring — 10 天干 coins
_TW_COIN_R = 13.0            # a 干支 coin token radius — small
# The canonical Nye Clock 五行 palette, read straight from tw_.html's
# CSS (wood / fire / earth / metal / water). Each coin is tinted by the
# 五行 of its 天干 / 地支.
_TW_WUXING: tuple[tuple[str, str], ...] = (
    ("#6ac07a", "#2f5e3a"),   # 0 wood  — rim, deep
    ("#e8705a", "#5e2a20"),   # 1 fire
    ("#d4b86a", "#5a4a26"),   # 2 earth
    ("#d8dce4", "#5a606c"),   # 3 metal
    ("#5aa6e4", "#214a6a"),   # 4 water
)


def _nye_ell(rx: float, ry: float, deg: float) -> tuple[float, float]:
    """Point on an ellipse centred at the origin (the oblique frame
    is applied by an outer <g rotate>). deg measured the SVG way."""
    r = math.radians(deg)
    return rx * math.cos(r), ry * math.sin(r)


def _nye_ell_arc(rx: float, ry: float, a0: float, a1: float) -> str:
    """Open elliptical arc path between two angles (degrees)."""
    p0 = _nye_ell(rx, ry, a0)
    p1 = _nye_ell(rx, ry, a1)
    delta = a1 - a0
    while delta <= 0:
        delta += 360.0
    large = 1 if delta > 180.0 else 0
    return (
        f"M {p0[0]:.2f} {p0[1]:.2f} "
        f"A {rx:.2f} {ry:.2f} 0 {large} 1 {p1[0]:.2f} {p1[1]:.2f}"
    )


def _nye_defs() -> str:
    """Gradient + filter defs — copied faithfully from the Nye Clock's
    helio instrument (sun core/corona/halo, earth ocean/land/atmo/limb,
    moon surface/shade, the cosmos background + vignette)."""
    return (
        '<defs>'
        # cosmos backdrop + vignette — deep near-black space, faithful
        # to tw_.html (only a whisper of blue, the rest is black).
        '<radialGradient id="nye-cosmos-bg" cx="50%" cy="44%" r="74%">'
        '<stop offset="0%" stop-color="rgba(14,22,46,0.55)"/>'
        '<stop offset="34%" stop-color="rgba(6,9,22,0.92)"/>'
        '<stop offset="100%" stop-color="rgba(1,2,7,1)"/>'
        '</radialGradient>'
        '<radialGradient id="nye-vignette" cx="50%" cy="46%" r="80%">'
        '<stop offset="0%" stop-color="rgba(2,4,12,0)"/>'
        '<stop offset="52%" stop-color="rgba(1,3,10,0.42)"/>'
        '<stop offset="100%" stop-color="rgba(0,0,4,0.98)"/>'
        '</radialGradient>'
        # soft nebula glows — a barely-there hint of deep-space depth
        # (kept very faint; tw_.html space is near-pure black).
        '<radialGradient id="nye-nebula-a" cx="50%" cy="50%" r="50%">'
        '<stop offset="0%" stop-color="rgba(110,82,210,0.07)"/>'
        '<stop offset="70%" stop-color="rgba(110,82,210,0)"/>'
        '</radialGradient>'
        '<radialGradient id="nye-nebula-b" cx="50%" cy="50%" r="50%">'
        '<stop offset="0%" stop-color="rgba(70,140,220,0.06)"/>'
        '<stop offset="72%" stop-color="rgba(70,140,220,0)"/>'
        '</radialGradient>'
        # sun
        # CENTRED fiery disc — a self-luminous star is brightest dead
        # centre (an off-centre highlight reads as a lit glass ball).
        '<radialGradient id="nye-sun-core" cx="50%" cy="50%" r="52%">'
        '<stop offset="0%" stop-color="#fffdf6"/>'
        '<stop offset="20%" stop-color="#fff0bf"/>'
        '<stop offset="42%" stop-color="#ffd166"/>'
        '<stop offset="64%" stop-color="#ff9a2e"/>'
        '<stop offset="84%" stop-color="#f06b16"/>'
        '<stop offset="100%" stop-color="#bc4408"/>'
        '</radialGradient>'
        '<radialGradient id="nye-sun-inner" cx="50%" cy="50%" r="50%">'
        '<stop offset="0%" stop-color="#ffffff"/>'
        '<stop offset="34%" stop-color="rgba(255,247,214,0.92)"/>'
        '<stop offset="70%" stop-color="rgba(255,205,110,0.30)"/>'
        '<stop offset="100%" stop-color="rgba(255,160,60,0)"/>'
        '</radialGradient>'
        '<radialGradient id="nye-sun-corona" cx="50%" cy="50%" r="50%">'
        '<stop offset="0%" stop-color="rgba(255,248,220,0.88)"/>'
        '<stop offset="28%" stop-color="rgba(255,190,100,0.45)"/>'
        '<stop offset="62%" stop-color="rgba(255,120,50,0.18)"/>'
        '<stop offset="100%" stop-color="rgba(255,80,30,0)"/>'
        '</radialGradient>'
        '<radialGradient id="nye-sun-halo" cx="50%" cy="50%" r="50%">'
        '<stop offset="0%" stop-color="rgba(255,230,180,0.35)"/>'
        '<stop offset="50%" stop-color="rgba(255,140,60,0.12)"/>'
        '<stop offset="100%" stop-color="rgba(255,100,40,0)"/>'
        '</radialGradient>'
        # the big translucent corona / atmosphere shells around the
        # Sun — soft dark-amber discs that fade out into black, the
        # dominant nested-sphere look of tw_.html. The rim is gentle
        # so the shells blend rather than read as hard concentric
        # rings.
        '<radialGradient id="nye-sun-shell" cx="50%" cy="50%" r="50%">'
        '<stop offset="0%" stop-color="rgba(40,21,9,0)"/>'
        '<stop offset="52%" stop-color="rgba(46,25,11,0.06)"/>'
        '<stop offset="76%" stop-color="rgba(64,35,16,0.14)"/>'
        '<stop offset="91%" stop-color="rgba(82,46,21,0.17)"/>'
        '<stop offset="100%" stop-color="rgba(96,54,25,0)"/>'
        '</radialGradient>'
        # earth
        # a SOLID lit ocean — bright on the sunlit (upper-right) side,
        # deep blue (never near-black) at the far limb, so the globe
        # reads as an opaque planet, not a fading translucent orb.
        '<radialGradient id="nye-earth-ocean" cx="64%" cy="32%" r="86%">'
        '<stop offset="0%" stop-color="#c4e7f6"/>'
        '<stop offset="30%" stop-color="#62a8cf"/>'
        '<stop offset="62%" stop-color="#31729a"/>'
        '<stop offset="100%" stop-color="#16415f"/>'
        '</radialGradient>'
        '<radialGradient id="nye-earth-land" cx="60%" cy="34%" r="80%">'
        '<stop offset="0%" stop-color="#8fb572"/>'
        '<stop offset="38%" stop-color="#6e9a52"/>'
        '<stop offset="66%" stop-color="#8a7846"/>'
        '<stop offset="100%" stop-color="#3f3a26"/>'
        '</radialGradient>'
        # a THIN atmosphere rim hugging the limb — not a glow halo
        # (the old wide halo made the globe look like it was emitting).
        '<radialGradient id="nye-earth-atmo" cx="50%" cy="50%" r="50%">'
        '<stop offset="0%" stop-color="rgba(150,215,255,0)"/>'
        '<stop offset="84%" stop-color="rgba(150,215,255,0)"/>'
        '<stop offset="93%" stop-color="rgba(168,224,255,0.5)"/>'
        '<stop offset="100%" stop-color="rgba(168,224,255,0)"/>'
        '</radialGradient>'
        # day / night terminator — a dark-only directional shadow from
        # the upper-right Sun (no white sheen, which read as a glow).
        '<linearGradient id="nye-earth-term" x1="100%" y1="0%" '
        'x2="0%" y2="100%">'
        '<stop offset="0%" stop-color="rgba(2,6,16,0)"/>'
        '<stop offset="46%" stop-color="rgba(2,6,16,0)"/>'
        '<stop offset="78%" stop-color="rgba(2,6,16,0.5)"/>'
        '<stop offset="100%" stop-color="rgba(1,3,10,0.88)"/>'
        '</linearGradient>'
        '<radialGradient id="nye-earth-limb" cx="72%" cy="32%" r="55%">'
        '<stop offset="0%" stop-color="rgba(255,255,255,0.5)"/>'
        '<stop offset="45%" stop-color="rgba(180,220,255,0.12)"/>'
        '<stop offset="100%" stop-color="rgba(0,0,0,0)"/>'
        '</radialGradient>'
        # moon
        '<radialGradient id="nye-moon-surf" cx="36%" cy="30%" r="64%">'
        '<stop offset="0%" stop-color="#f8fafc"/>'
        '<stop offset="38%" stop-color="#c4ccd8"/>'
        '<stop offset="100%" stop-color="#4a5468"/>'
        '</radialGradient>'
        '<radialGradient id="nye-moon-shade" cx="68%" cy="62%" r="58%">'
        '<stop offset="0%" stop-color="rgba(0,0,0,0)"/>'
        '<stop offset="55%" stop-color="rgba(0,0,0,0.22)"/>'
        '<stop offset="100%" stop-color="rgba(0,0,0,0.45)"/>'
        '</radialGradient>'
        # orbit rails
        '<linearGradient id="nye-stem-rail" x1="0%" y1="0%" '
        'x2="100%" y2="100%">'
        '<stop offset="0%" stop-color="rgba(255,218,150,0.98)"/>'
        '<stop offset="100%" stop-color="rgba(210,110,55,0.5)"/>'
        '</linearGradient>'
        '<linearGradient id="nye-branch-rail" x1="0%" y1="0%" '
        'x2="0%" y2="100%">'
        '<stop offset="0%" stop-color="rgba(150,220,255,0.92)"/>'
        '<stop offset="100%" stop-color="rgba(55,120,205,0.45)"/>'
        '</linearGradient>'
        # filters
        '<filter id="nye-soft-glow" x="-50%" y="-50%" '
        'width="200%" height="200%">'
        '<feGaussianBlur in="SourceGraphic" stdDeviation="3.2" '
        'result="b"/>'
        '<feMerge><feMergeNode in="b"/>'
        '<feMergeNode in="SourceGraphic"/></feMerge>'
        '</filter>'
        '<filter id="nye-sun-bloom" x="-80%" y="-80%" '
        'width="260%" height="260%">'
        '<feGaussianBlur in="SourceGraphic" stdDeviation="14" '
        'result="b"/>'
        '<feMerge><feMergeNode in="b"/>'
        '<feMergeNode in="SourceGraphic"/></feMerge>'
        '</filter>'
        '<filter id="nye-sun-tight" x="-40%" y="-40%" '
        'width="180%" height="180%">'
        '<feGaussianBlur in="SourceGraphic" stdDeviation="4.5" '
        'result="b"/>'
        '<feMerge><feMergeNode in="b"/>'
        '<feMergeNode in="SourceGraphic"/></feMerge>'
        '</filter>'
        # --- celestial-body surface textures: GPU-free fractal-noise
        #     filters. These lift the bodies from smooth glass balls to
        #     real, textured, lit spheres (static SVG only). ---
        # Sun: warp the fiery disc into churning plasma.
        '<filter id="nye-sun-plasma" x="-34%" y="-34%" '
        'width="168%" height="168%">'
        '<feTurbulence type="fractalNoise" baseFrequency="0.013" '
        'numOctaves="4" seed="17" result="t"/>'
        '<feDisplacementMap in="SourceGraphic" in2="t" scale="16" '
        'xChannelSelector="R" yChannelSelector="G"/>'
        '</filter>'
        # clips the plasma texture so it churns INSIDE a clean circular
        # silhouette — the Sun must read as a perfect round disc.
        '<clipPath id="nye-sun-clip">'
        '<circle cx="0" cy="0" r="66"></circle>'
        '</clipPath>'
        # Sun: dark granulation cells stippling the photosphere.
        '<filter id="nye-sun-granule">'
        '<feTurbulence type="fractalNoise" baseFrequency="0.058" '
        'numOctaves="3" seed="9" result="g"/>'
        '<feColorMatrix in="g" type="matrix" values="0 0 0 0 0 '
        '0 0 0 0 0 0 0 0 0 0 0 0 0 1.05 -0.5" result="m"/>'
        '<feComposite in="m" in2="SourceAlpha" operator="in"/>'
        '</filter>'
        # Earth: fractal continents masked out of a green disc.
        '<filter id="nye-earth-conti">'
        '<feTurbulence type="fractalNoise" baseFrequency="0.026" '
        'numOctaves="5" seed="5" result="c"/>'
        '<feComponentTransfer in="c" result="thr">'
        '<feFuncA type="discrete" tableValues="0 0 0 0 0 1 1 1"/>'
        '</feComponentTransfer>'
        '<feComposite in="SourceGraphic" in2="thr" operator="in"/>'
        '</filter>'
        # Earth: soft white cloud wisps.
        '<filter id="nye-earth-cloud">'
        '<feTurbulence type="fractalNoise" baseFrequency="0.032" '
        'numOctaves="4" seed="12" result="w"/>'
        '<feColorMatrix in="w" type="matrix" values="0 0 0 0 1 '
        '0 0 0 0 1 0 0 0 0 1 0 0 0 0.92 -0.4" result="cl"/>'
        '<feComposite in="cl" in2="SourceAlpha" operator="in"/>'
        '</filter>'
        # Moon: cratered grey mottling.
        '<filter id="nye-moon-tex">'
        '<feTurbulence type="fractalNoise" baseFrequency="0.2" '
        'numOctaves="3" seed="4" result="mn"/>'
        '<feColorMatrix in="mn" type="matrix" values="0 0 0 0 0 '
        '0 0 0 0 0 0 0 0 0 0 0 0 0 0.95 -0.42" result="mm"/>'
        '<feComposite in="mm" in2="SourceAlpha" operator="in"/>'
        '</filter>'
        '</defs>'
    )


def _nye_cosmos() -> str:
    """Deep-space backdrop — radial nebula fill + a deterministic star
    field + an outer vignette. Mirrors the Nye Clock's helioLayerCosmos
    (168 stars on a golden-angle spiral)."""
    out: list[str] = [
        f'<rect x="0" y="0" width="{_NYE_VB_W}" height="{_NYE_VB_H}" '
        f'fill="url(#nye-cosmos-bg)"></rect>'
    ]
    # two off-centre nebula blobs for deep-space depth
    out.append(
        f'<ellipse cx="{_NYE_VB_W * 0.22:.0f}" '
        f'cy="{_NYE_VB_H * 0.26:.0f}" rx="320" ry="250" '
        f'fill="url(#nye-nebula-a)"></ellipse>'
        f'<ellipse cx="{_NYE_VB_W * 0.78:.0f}" '
        f'cy="{_NYE_VB_H * 0.74:.0f}" rx="300" ry="240" '
        f'fill="url(#nye-nebula-b)"></ellipse>'
    )
    for s in range(168):
        a = (s * 137.5) % 360.0
        rr = 48.0 + (s * 79) % 420
        t = math.radians(a - 90.0)
        x = _NYE_CX + rr * math.cos(t)
        y = _NYE_CY + rr * math.sin(t)
        op = 0.07 + (s % 8) * 0.02
        rad = 0.32 + (s % 6) * 0.11
        out.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{rad:.2f}" '
            f'fill="rgba(255,255,255,{op:.3f})"></circle>'
        )
    out.append(
        f'<rect x="0" y="0" width="{_NYE_VB_W}" height="{_NYE_VB_H}" '
        f'fill="url(#nye-vignette)" style="pointer-events:none"></rect>'
    )
    return "".join(out)


def _nye_sun(sun_sign_color: str) -> str:
    """The Sun — the DOMINANT body of the 玄学 scene.

    Faithful to the real Nye Clock (tw_.html): a bright glowing core
    wrapped in SEVERAL big concentric translucent corona / atmosphere
    rings that fade outward into the black — the eye's single focal
    glow. Drawn at the origin; the caller translates it upper-right.
    The 占星 Sun-sign hue tints one engraved ring.
    """
    # the big nested corona / atmosphere shells — soft translucent
    # dark-amber discs that overlap and fade out into the black, the
    # dominant nested-sphere look of the real tw_.html Sun.
    shells = [
        (322.0, 0.62),
        (250.0, 0.78),
        (188.0, 0.95),
        (138.0, 1.0),
    ]
    parts = ['<g>']
    for r, op in shells:
        parts.append(
            f'<circle cx="0" cy="0" r="{r:.0f}" '
            f'fill="url(#nye-sun-shell)" opacity="{op:.2f}" '
            f'filter="url(#nye-sun-tight)"></circle>'
        )
    parts.append(
        # warm outer bloom + corona behind the body
        '<circle cx="0" cy="0" r="152" fill="url(#nye-sun-halo)" '
        'opacity="0.58" filter="url(#nye-sun-bloom)"></circle>'
        '<circle cx="0" cy="0" r="112" fill="url(#nye-sun-corona)" '
        'opacity="0.66" filter="url(#nye-sun-bloom)"></circle>'
        '<circle cx="0" cy="0" r="84" fill="url(#nye-sun-corona)" '
        'opacity="0.5"></circle>'
        # the Sun body — a clean ROUND fiery disc. The turbulent plasma
        # texture churns INSIDE it, clipped to the circle, so the
        # silhouette always stays a perfect round disc.
        '<circle cx="0" cy="0" r="66" fill="url(#nye-sun-core)"></circle>'
        '<g clip-path="url(#nye-sun-clip)">'
        '<circle cx="0" cy="0" r="96" fill="url(#nye-sun-core)" '
        'opacity="0.6" filter="url(#nye-sun-plasma)"></circle>'
        '<circle cx="0" cy="0" r="66" fill="#1a0a00" opacity="0.4" '
        'filter="url(#nye-sun-granule)"></circle>'
        '</g>'
        # white-hot centred bloom
        '<circle cx="0" cy="0" r="44" fill="url(#nye-sun-inner)" '
        'filter="url(#nye-sun-tight)"></circle>'
        # crisp circular limb — reinforces the clean round edge
        '<circle cx="0" cy="0" r="66" fill="none" '
        'stroke="rgba(255,226,150,0.35)" stroke-width="1.4"></circle>'
        # the 占星 Sun-sign hue — a soft tint washed into the corona
        f'<circle cx="0" cy="0" r="94" fill="none" '
        f'stroke="{sun_sign_color}" stroke-opacity="0.14" '
        f'stroke-width="8" filter="url(#nye-sun-bloom)"></circle>'
        '</g>'
    )
    return "".join(parts)


def _nye_earth() -> str:
    """The Earth globe — atmosphere, ocean, land masses, terminator,
    limb highlight, cloud wisps. Faithful to the Nye Clock
    helioEarthCluster. Drawn at the origin; the caller translates it
    onto the orbit."""
    return (
        '<g>'
        # a SOLID opaque ocean sphere — lit from the Sun (upper-right)
        '<circle r="39" cx="0" cy="0" fill="url(#nye-earth-ocean)">'
        '</circle>'
        # fractal-noise continents masked out of a lit, earthy disc
        '<circle r="39" cx="0" cy="0" fill="url(#nye-earth-land)" '
        'filter="url(#nye-earth-conti)"></circle>'
        # soft white cloud wisps
        '<circle r="39" cx="0" cy="0" fill="#ffffff" opacity="0.42" '
        'filter="url(#nye-earth-cloud)"></circle>'
        # day / night terminator — the far side falls into real shadow
        '<circle r="39" cx="0" cy="0" fill="url(#nye-earth-term)">'
        '</circle>'
        # a thin atmosphere rim hugging the limb (no glow halo)
        '<circle r="44" cx="0" cy="0" fill="url(#nye-earth-atmo)">'
        '</circle>'
        '<circle r="39" cx="0" cy="0" fill="none" '
        'stroke="rgba(150,205,245,0.4)" stroke-width="0.9"></circle>'
        '</g>'
    )


def _nye_moon(cx: float, cy: float) -> str:
    """The Moon lit sphere — surface, shade, craters, glint. Faithful
    to the Nye Clock orbHelioMoonNode."""
    return (
        f'<g transform="translate({cx:.2f},{cy:.2f})">'
        # lit grey surface
        '<circle r="11.2" cx="0" cy="0" fill="url(#nye-moon-surf)">'
        '</circle>'
        # cratered fractal-noise mottling
        '<circle r="11.2" cx="0" cy="0" fill="#000000" opacity="0.5" '
        'filter="url(#nye-moon-tex)"></circle>'
        # soft phase shade
        '<circle r="11.2" cx="0" cy="0" fill="url(#nye-moon-shade)" '
        'opacity="0.9"></circle>'
        # crisp lit limb
        '<circle r="11.2" cx="0" cy="0" fill="none" '
        'stroke="rgba(255,255,255,0.34)" stroke-width="0.45"></circle>'
        '</g>'
    )


def _tw_defs() -> str:
    """Extra defs for the tw_.html-faithful 玄学 view (Acceptance #61) —
    a per-五行 coin-token gradient set + an active-glyph glow filter.

    Layered on top of the shared ``_nye_defs`` celestial-body gradients;
    the cosmos / sun / earth / moon gradients come from there."""
    coin_grads: list[str] = []
    for i, (rim, deep) in enumerate(_TW_WUXING):
        coin_grads.append(
            f'<radialGradient id="tw-coin-{i}" cx="38%" cy="32%" r="74%">'
            f'<stop offset="0%" stop-color="{rim}" stop-opacity="0.96"/>'
            f'<stop offset="62%" stop-color="{deep}" stop-opacity="0.92"/>'
            f'<stop offset="100%" stop-color="#05070c" stop-opacity="0.98"/>'
            f'</radialGradient>'
        )
    return (
        '<defs>'
        + "".join(coin_grads)
        # the aura behind a large active 干支 glyph
        + '<filter id="tw-glyph-glow" x="-90%" y="-90%" '
        'width="280%" height="280%">'
        '<feGaussianBlur in="SourceGraphic" stdDeviation="6.5" '
        'result="b"/>'
        '<feMerge><feMergeNode in="b"/>'
        '<feMergeNode in="SourceGraphic"/></feMerge>'
        '</filter>'
        '</defs>'
    )


def _tw_coin(cx: float, cy: float, ch: str, elem_idx: int,
             *, active: bool = False, pillar: bool = False) -> str:
    """One 干支 coin token — a thin bezel ring + the character, tinted
    by 五行 — exactly the small circular 干支 coins ringing the Earth in
    tw_.html. ``active`` lights the day-pillar coin; ``pillar`` marks a
    coin that carries one of the four 八字 pillars with a jewel dot.

    All sub-geometry scales off ``_TW_COIN_R`` so the token reads
    crisp at the small corner-cluster size.
    """
    rim, _deep = _TW_WUXING[elem_idx]
    r = _TW_COIN_R * (1.22 if active else 1.0)
    bezel_op = 0.96 if (active or pillar) else 0.62
    bezel_w = 1.4 if active else (1.05 if pillar else 0.8)
    glow = ' filter="url(#nye-soft-glow)"' if active else ""
    font_px = r * (1.18 if active else 1.04)
    parts = [
        f'<g transform="translate({cx:.2f},{cy:.2f})">',
        # coin face
        f'<circle r="{r:.2f}" fill="url(#tw-coin-{elem_idx})" '
        f'stroke="{rim}" stroke-opacity="{bezel_op:.2f}" '
        f'stroke-width="{bezel_w}"{glow}></circle>',
        # inner hairline bezel
        f'<circle r="{r * 0.78:.2f}" fill="none" '
        f'stroke="rgba(255,255,255,0.16)" stroke-width="0.5"></circle>',
        # the 干支 character
        f'<text x="0" y="0.4" font-family="{_SERIF}" '
        f'font-size="{font_px:.1f}" '
        f'fill="{"#fff7e8" if active else "#e9edf4"}" '
        f'font-weight="600" text-anchor="middle" '
        f'dominant-baseline="middle">{_esc(ch, 1)}</text>',
    ]
    if pillar:
        # a small jewel dot at the coin's top — this coin carries a
        # 年/月/日/时 pillar.
        parts.append(
            f'<circle cx="0" cy="{-r - 3.4:.1f}" r="1.9" '
            f'fill="{_GAL_GOLD}" stroke="rgba(255,255,255,0.55)" '
            f'stroke-width="0.5" filter="url(#nye-soft-glow)"></circle>'
        )
    parts.append('</g>')
    return "".join(parts)


# Sparse large 干支 glyphs scattered across the black field — the
# faint floating characters of the real tw_.html scene. Deterministic
# positions (viewBox 1000×920); each is a big, dim, 五行-tinted glyph
# with generous black space around it. Kept clear of the Sun
# (upper-right) and the Earth cluster (lower-left).
_TW_FLOAT_GLYPHS: tuple[tuple[float, float, float, str], ...] = (
    # x,    y,     size,  kind ("stem" | "branch")
    (148.0, 116.0, 64.0, "branch"),
    (322.0, 196.0, 50.0, "stem"),
    (118.0, 330.0, 58.0, "branch"),
    (470.0, 96.0,  46.0, "branch"),
    (846.0, 678.0, 60.0, "stem"),
    (560.0, 800.0, 66.0, "branch"),
    (724.0, 560.0, 44.0, "stem"),
    (392.0, 470.0, 40.0, "branch"),
)


def _tw_float_glyph(cx: float, cy: float, size: float, ch: str,
                    elem_idx: int) -> str:
    """One large, faint, free-floating 干支 glyph — the sparse
    characters drifting across the deep-space field in tw_.html."""
    rim, _deep = _TW_WUXING[elem_idx]
    return (
        f'<text x="{cx:.1f}" y="{cy:.1f}" font-family="{_SERIF}" '
        f'font-size="{size:.0f}" fill="{rim}" fill-opacity="0.30" '
        f'font-weight="500" text-anchor="middle" '
        f'dominant-baseline="middle" '
        f'filter="url(#tw-glyph-glow)">{_esc(ch, 1)}</text>'
    )


def _render_nye_solar_system(
    reading_bazi: LensReading,
    reading_astro: LensReading,
    branch_probabilities: list[tuple[str, float, str]],
    top_label: str, top_value: str,
    bottom_label: str, bottom_value: str,
    meta: str,
) -> str:
    """The Nye Clock 玄学 view — a Sun-dominant deep-space scene.

    [OMY-V415 / M2 / Acceptance #64] REBUILT (4th attempt) to faithfully
    match the real Nye Clock ``~/Downloads/UCSB/Adonyth/tw_.html``. The
    founder rejected the previous Earth-centred, tight-busy-coin-wheel
    composition as "太乱" — wrong composition.

    The composition, matching tw_.html screenshot-for-screenshot:

      • Deep black space, generous negative space — calm, spacious.
      • A LARGE glowing Sun with several concentric translucent corona
        rings — the dominant element, upper-right.
      • A SMALL blue Earth globe tucked into the lower-left corner: a
        thin orbital ring, a small Moon beside it, a TIGHT cluster of
        small 五行-tinted 干支 coin tokens ringed close around it.
      • Large but faint 干支 characters floating SPARSELY across the
        black field at varied positions.

    A STATIC visual style only — NO live per-frame rendering, NO real
    clock time, NO WebGL / Three.js / canvas / GPU. Lightweight SVG
    that embeds verbatim. The 八字 / 占星 values come from the verified
    ``_metaphysics`` engine (calendar logic unchanged — display only).

    `branch_probabilities` is accepted for call-site parity.
    """
    _ = branch_probabilities
    bazi = reading_bazi.bazi
    chart = reading_astro.natal

    # --- 占星: Sun / Moon zodiac indices (from the verified engine) ---
    sun_idx = chart.sun if chart is not None else 0
    moon_idx = chart.moon if chart is not None else 6
    sun_color = (
        ASTRO_ELEMENT_COLOR[ZODIAC[sun_idx].element]
        if chart is not None else _GAL_GOLD
    )

    # --- 八字: the active stem / branch of the day pillar ---
    day_stem_idx = bazi.day_pillar[0] if bazi is not None else 0
    day_branch_idx = bazi.day_pillar[1] if bazi is not None else 0
    # which 天干 / 地支 indices carry one of the four pillars
    pillar_stems = (
        {p[0] for p in (bazi.year_pillar, bazi.month_pillar,
                        bazi.day_pillar, bazi.hour_pillar)}
        if bazi is not None else set()
    )
    pillar_branches = (
        {p[1] for p in (bazi.year_pillar, bazi.month_pillar,
                        bazi.day_pillar, bazi.hour_pillar)}
        if bazi is not None else set()
    )

    ecx, ecy = _TW_EARTH_CX, _TW_EARTH_CY

    body: list[str] = [
        f'<svg viewBox="0 0 {_NYE_VB_W} {_NYE_VB_H}" width="100%" '
        f'preserveAspectRatio="xMidYMid meet" style="display:block;" '
        f'role="img" aria-label="Nye Clock 玄学 view">',
        _nye_defs(),
        _tw_defs(),
        _nye_cosmos(),
    ]

    # === sparse large 干支 glyphs drifting across the black field ===
    # Drawn first so they sit BEHIND the bodies — faint, distant.
    for gx, gy, gsize, kind in _TW_FLOAT_GLYPHS:
        if kind == "stem":
            gi = (int(gx + gy)) % 10
            body.append(_tw_float_glyph(
                gx, gy, gsize, HEAVENLY_STEMS[gi], WUXING_OF_STEM[gi]))
        else:
            gi = (int(gx + gy)) % 12
            body.append(_tw_float_glyph(
                gx, gy, gsize, EARTHLY_BRANCHES[gi],
                WUXING_OF_BRANCH[gi]))

    # === the Sun — the DOMINANT body, upper-right, full scale ===
    body.append(
        f'<g transform="translate({_TW_SUN_CX},{_TW_SUN_CY})">'
        + _nye_sun(sun_color)
        + '</g>'
    )

    # === the small corner Earth + its tight 干支-coin cluster ========
    # A whisper of a 占星-Sun-sign-tinted atmospheric halo + a thin
    # orbital ring around the small Earth.
    body.append(
        f'<circle cx="{ecx}" cy="{ecy}" r="{_TW_EARTH_R + 11:.1f}" '
        f'fill="{sun_color}" fill-opacity="0.055"></circle>'
        f'<circle cx="{ecx}" cy="{ecy}" r="{_TW_EARTH_R + 30:.1f}" '
        f'fill="none" stroke="rgba(120,200,255,0.24)" '
        f'stroke-width="0.9"></circle>'
    )
    # the two faint guide circles the coin cluster rides on
    for ring_r in (_TW_BRANCH_RING_R, _TW_STEM_RING_R):
        body.append(
            f'<circle cx="{ecx}" cy="{ecy}" r="{ring_r}" fill="none" '
            f'stroke="rgba(150,196,255,0.13)" stroke-width="0.8">'
            f'</circle>'
        )

    # inner ring — 12 地支 coins, tinted by each branch's 五行
    for i in range(12):
        ang = i * 30.0
        cx, cy = _polar(ecx, ecy, _TW_BRANCH_RING_R, ang)
        body.append(_tw_coin(
            cx, cy, EARTHLY_BRANCHES[i], WUXING_OF_BRANCH[i],
            active=(i == day_branch_idx),
            pillar=(i in pillar_branches),
        ))
    # outer ring — 10 天干 coins, tinted by each stem's 五行
    for i in range(10):
        ang = i * 36.0
        cx, cy = _polar(ecx, ecy, _TW_STEM_RING_R, ang)
        body.append(_tw_coin(
            cx, cy, HEAVENLY_STEMS[i], WUXING_OF_STEM[i],
            active=(i == day_stem_idx),
            pillar=(i in pillar_stems),
        ))

    # the small Earth globe itself (_nye_earth() is drawn at r≈52)
    earth_scale = _TW_EARTH_R / 52.0
    body.append(
        f'<g transform="translate({ecx},{ecy}) scale({earth_scale:.3f})">'
        + _nye_earth()
        + '</g>'
    )
    # the small Moon — a lit sphere just outside the Earth
    mx, my = _polar(ecx, ecy, _TW_EARTH_R + 30.0, 48.0)
    body.append(_nye_moon(mx, my))

    # === the four 八字 pillars — small jewelled markers in a column on
    # the right, clear of the Sun, reading the verified engine. ===
    if bazi is not None:
        pillars = (
            (bazi.year_pillar,  "YEAR"),
            (bazi.month_pillar, "MONTH"),
            (bazi.day_pillar,   "DAY"),
            (bazi.hour_pillar,  "HOUR"),
        )
        px = 902.0
        py0 = 150.0
        pgap = 96.0
        for slot, (pil, name) in enumerate(pillars):
            txt = pillar_text(pil)
            rim, _d = _TW_WUXING[WUXING_OF_STEM[pil[0] % 10]]
            idx = _sexagenary_index(pil)
            gy = py0 + slot * pgap
            body.append(
                f'<g transform="translate({px},{gy})">'
                f'<circle r="30" fill="{rim}" fill-opacity="0.10" '
                f'filter="url(#tw-glyph-glow)"></circle>'
                f'<circle r="25" fill="rgba(8,11,20,0.62)" '
                f'stroke="{rim}" stroke-opacity="0.5" '
                f'stroke-width="1.0"></circle>'
                f'<text x="0" y="-3" font-family="{_SERIF}" '
                f'font-size="24" fill="{rim}" font-weight="600" '
                f'text-anchor="middle" dominant-baseline="middle">'
                f'{_esc(txt[0] if txt else "", 1)}</text>'
                f'<text x="0" y="13" font-family="{_SERIF}" '
                f'font-size="13" fill="#cdd4e0" font-weight="600" '
                f'text-anchor="middle" dominant-baseline="middle">'
                f'{_esc(txt[1] if len(txt) > 1 else "", 1)}</text>'
                f'<text x="0" y="40" font-family="{_MONO}" '
                f'font-size="7.5" fill="{_INK3}" '
                f'letter-spacing="0.14em" text-anchor="middle">'
                f'{name} · {idx + 1:02d}/60</text>'
                f'</g>'
            )

    # === readout plate — a compact instrument panel, lower-right, in
    # the open space clear of the Earth corner and the Sun. ===
    plate_w = 332.0
    plate_h = 88.0
    plate_x = _NYE_VB_W - plate_w - 40.0
    plate_y = _NYE_VB_H - plate_h - 36.0
    body.append(
        f'<g transform="translate({plate_x:.1f},{plate_y:.1f})">'
        f'<rect x="0" y="0" width="{plate_w}" height="{plate_h}" '
        f'rx="13" fill="rgba(8,11,20,0.80)" '
        f'stroke="rgba(255,255,255,0.10)" stroke-width="1"></rect>'
        f'<rect x="0.8" y="0.8" width="{plate_w - 1.6}" '
        f'height="{plate_h - 1.6}" rx="12" fill="none" '
        f'stroke="rgba(255,255,255,0.04)" stroke-width="0.7"></rect>'
        # left readout — MODEL
        f'<text x="{plate_w * 0.27:.0f}" y="25" font-family="{_MONO}" '
        f'font-size="8.5" fill="{_INK2}" letter-spacing="0.2em" '
        f'text-anchor="middle">{_esc(top_label, 18)}</text>'
        f'<text x="{plate_w * 0.27:.0f}" y="51" font-family="{_SERIF}" '
        f'font-size="28" fill="{_INK0}" font-weight="600" '
        f'text-anchor="middle" dominant-baseline="middle">'
        f'{_esc(top_value, 10)}</text>'
        # centre hairline divider
        f'<line x1="{plate_w * 0.5:.0f}" y1="18" '
        f'x2="{plate_w * 0.5:.0f}" y2="{plate_h - 18:.0f}" '
        f'stroke="rgba(255,255,255,0.10)" stroke-width="0.9"></line>'
        # right readout — 玄学 consensus
        f'<text x="{plate_w * 0.73:.0f}" y="25" font-family="{_MONO}" '
        f'font-size="8.5" fill="{_INK2}" letter-spacing="0.2em" '
        f'text-anchor="middle">{_esc(bottom_label, 18)}</text>'
        f'<text x="{plate_w * 0.73:.0f}" y="51" font-family="{_SERIF}" '
        f'font-size="28" fill="{_GAL_GOLD}" font-weight="600" '
        f'text-anchor="middle" dominant-baseline="middle">'
        f'{_esc(bottom_value, 10)}</text>'
        # meta strip along the bottom
        f'<text x="{plate_w * 0.5:.0f}" y="{plate_h - 12:.0f}" '
        f'font-family="{_MONO}" font-size="7" fill="{_INK3}" '
        f'letter-spacing="0.12em" text-anchor="middle">'
        f'{_esc(meta, 46)}</text>'
        f'</g>'
    )

    # === a slim caption naming the lens, top-left ===
    body.append(
        f'<text x="46" y="44" font-family="{_MONO}" '
        f'font-size="9" fill="{_INK3}" letter-spacing="0.30em" '
        f'text-anchor="start">NYE CLOCK · 玄学 LENS</text>'
    )

    body.append('</svg>')
    return "".join(body)


# ======================================================================
# Instrument 6 — the unified celestial astrolabe (八字 ⊕ 占星) [legacy]
# ======================================================================

def _render_celestial(reading_bazi: LensReading,
                      reading_astro: LensReading,
                      branch_probabilities: list[tuple[str, float, str]],
                      top_label: str, top_value: str,
                      bottom_label: str, bottom_value: str,
                      meta: str) -> str:
    """The unified celestial astrolabe — 八字 and 占星 on one dial.

    Both traditions are read off the sky, so they share a single
    instrument instead of two separate dials behind a selector:

      • outer ring  — the 八字 sexagenary gear movement (gold 天干 ring
                      gear meshing the cyan 地支 pinion; the four pillars
                      ride it as jewels).
      • middle ring — the 占星 zodiac wheel (12 sectors, sun sign lit).
      • inner ring  — the 八字 五行 phase ring (dominant element lit).
      • centre field— the 占星 Sun + Moon as lit spheres on orbits.
      • core        — the joint MODEL / 玄学-consensus readout.

    `branch_probabilities` is accepted for call-site parity; the branch
    distribution itself lives in the main quantum heatmap.
    """
    _ = branch_probabilities
    bazi = reading_bazi.bazi
    balance = reading_bazi.balance or {}
    dom_key = dominant_element(balance) if balance else None
    chart = reading_astro.natal

    body: list[str] = [_svg_open()]

    # --- frame + cardinal diamonds ---
    body.append(
        f'<circle cx="{_CX}" cy="{_CY}" r="226" fill="none" '
        f'stroke="{_HAIRLINE}" stroke-width="0.7"></circle>'
        f'<circle cx="{_CX}" cy="{_CY}" r="221" fill="none" '
        f'stroke="{_HAIR_STRONG}" stroke-width="1.0" opacity="0.6"></circle>'
    )
    for ang in (0, 90, 180, 270):
        dx, dy = _polar(_CX, _CY, 223.5, ang)
        body.append(
            f'<path d="M {dx:.1f} {dy-4:.1f} L {dx+4:.1f} {dy:.1f} '
            f'L {dx:.1f} {dy+4:.1f} L {dx-4:.1f} {dy:.1f} Z" '
            f'fill="{_INK2}"></path>'
        )

    # === 八字 sexagenary gear movement (outer mechanism) ===
    # muted as a group — on the unified dial the movement frames the
    # instrument; the four lit pillar jewels are its focal points.
    body.append(
        '<g opacity="0.42">'
        + _gear_ring(190.0, 196.0, 12, 9.0, True,
                     "gear-cyan", "#0c2630", phase_deg=15.0)
        + _gear_ring(207.0, 214.0, 10, 9.0, False,
                     "gear-gold", "#2a200a")
        + '</g>'
    )
    if bazi is not None:
        for pil in (bazi.year_pillar, bazi.month_pillar,
                    bazi.day_pillar, bazi.hour_pillar):
            ang = _sexagenary_index(pil) * 6.0
            mx, my = _polar(_CX, _CY, 210.5, ang)
            body.append(
                f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="5.8" '
                f'fill="#0c0e14" stroke="rgba(0,0,0,0.55)" '
                f'stroke-width="1.2"></circle>'
                f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="4.6" '
                f'fill="{_SURFACE}" stroke="{_ACCENT}" stroke-width="1.4" '
                f'filter="url(#soft-glow)"></circle>'
                f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="1.9" '
                f'fill="{_ACCENT}"></circle>'
            )

    # === 占星 zodiac wheel (middle ring) ===
    zr_out, zr_in = 186.0, 158.0
    big3 = {chart.sun, chart.moon} if chart is not None else set()
    for i, sign in enumerate(ZODIAC):
        a0 = i * 30.0 - 15.0
        a1 = a0 + 30.0
        col = ASTRO_ELEMENT_COLOR[sign.element]
        is_sun = (chart is not None and i == chart.sun)
        is_big3 = (i in big3)
        alpha = 0.58 if is_sun else (0.18 if is_big3 else 0.075)
        glow = ' filter="url(#soft-glow)"' if is_sun else ""
        body.append(
            f'<path d="{_arc_path(_CX, _CY, zr_out, zr_in, a0, a1)}" '
            f'fill="{col}" fill-opacity="{alpha:.3f}" '
            f'stroke="{_HAIRLINE}" stroke-width="0.8"{glow}></path>'
        )
        gx, gy = _polar(_CX, _CY, (zr_out + zr_in) / 2, i * 30.0)
        body.append(
            f'<text x="{gx:.1f}" y="{gy+1:.1f}" font-family="{_SERIF}" '
            f'font-size="{17 if is_sun else 13}" '
            f'fill="{_INK0 if is_big3 else _INK2}" font-weight="600" '
            f'text-anchor="middle" dominant-baseline="middle">'
            f'{sign.glyph}</text>'
        )

    # === 八字 五行 phase ring (thin inner ring) ===
    fr_out, fr_in = 152.0, 137.0
    sector = 72.0
    for i, key in enumerate(WUXING_KEYS):
        share = max(0.0, balance.get(key, 0.0))
        a0 = i * sector - sector / 2
        a1 = a0 + sector
        is_dom = (key == dom_key)
        glow = ' filter="url(#soft-glow)"' if is_dom else ""
        op = 0.86 if is_dom else min(0.30, 0.05 + share * 1.1)
        body.append(
            f'<path d="{_arc_path(_CX, _CY, fr_out, fr_in, a0, a1)}" '
            f'fill="url(#wx-{key})" fill-opacity="{op:.3f}" '
            f'stroke="{_CANVAS}" stroke-width="1.1"{glow}></path>'
        )
        gx, gy = _polar(_CX, _CY, (fr_out + fr_in) / 2, (a0 + a1) / 2)
        body.append(
            f'<text x="{gx:.1f}" y="{gy+0.5:.1f}" font-family="{_SERIF}" '
            f'font-size="{12.5 if is_dom else 10}" '
            f'fill="{_INK0 if is_dom else _INK2}" font-weight="600" '
            f'text-anchor="middle" dominant-baseline="middle">'
            f'{WUXING_HANZI[i]}</text>'
        )

    # === 占星 Sun + Moon orbital system (centre field) ===
    if chart is not None:
        sun_orbit, moon_orbit = 103.0, 122.0
        for orad in (moon_orbit, sun_orbit):
            body.append(
                f'<circle cx="{_CX}" cy="{_CY}" r="{orad:.1f}" fill="none" '
                f'stroke="{_GAL_BLUE}" stroke-width="0.9" '
                f'opacity="0.40"></circle>'
            )
        mmx, mmy = _polar(_CX, _CY, moon_orbit, chart.moon * 30.0)
        body.append(
            f'<line x1="{_CX}" y1="{_CY}" x2="{mmx:.1f}" y2="{mmy:.1f}" '
            f'stroke="{_GAL_BLUE}" stroke-width="0.6" opacity="0.16"></line>'
        )
        body.append(_lit_sphere(mmx, mmy, 9.5, "sphere-moon", "#2c3346",
                                glyph="☽", glyph_col="#2a2f3e",
                                glyph_size=12.0))
        ssx, ssy = _polar(_CX, _CY, sun_orbit, chart.sun * 30.0)
        body.append(
            f'<line x1="{_CX}" y1="{_CY}" x2="{ssx:.1f}" y2="{ssy:.1f}" '
            f'stroke="{_GAL_GOLD}" stroke-width="0.7" opacity="0.22"></line>'
        )
        body.append(_lit_sphere(ssx, ssy, 12.0, "sphere-sun", "#6e4d09",
                                corona=True, glyph="☉", glyph_col="#5a3f06",
                                glyph_size=14.0))

    # === engraved core — the joint MODEL / 玄学-consensus readout ===
    body.append(_centre_readout(top_label, top_value,
                                bottom_label, bottom_value, meta,
                                r_core=86.0))

    # --- corner cartouches — the four 八字 pillars in 干支 (gold stem /
    # cyan branch), filling the otherwise-empty corners ---
    if bazi is not None:
        for pil, name, (px, py) in (
            (bazi.year_pillar,  "YEAR",  (44, 44)),
            (bazi.month_pillar, "MONTH", (_VB - 44, 44)),
            (bazi.day_pillar,   "DAY",   (44, _VB - 44)),
            (bazi.hour_pillar,  "HOUR",  (_VB - 44, _VB - 44)),
        ):
            txt = pillar_text(pil)
            idx = _sexagenary_index(pil)
            body.append(
                f'<g transform="translate({px-37},{py-20})">'
                f'<rect x="0" y="0" width="74" height="40" rx="7" '
                f'fill="{_SURFACE2}" stroke="{_HAIRLINE}" stroke-width="1"></rect>'
                f'<text x="37" y="18" font-family="{_SERIF}" font-size="18" '
                f'text-anchor="middle" dominant-baseline="middle" '
                f'font-weight="600">'
                f'<tspan fill="{_GAL_GOLD}">{_esc(txt[0] if txt else "", 1)}</tspan>'
                f'<tspan fill="{_GAL_CYAN}">'
                f'{_esc(txt[1] if len(txt) > 1 else "", 1)}</tspan>'
                f'</text>'
                f'<text x="37" y="32" font-family="{_MONO}" font-size="7" '
                f'fill="{_INK3}" letter-spacing="0.12em" text-anchor="middle">'
                f'{name} · {idx + 1:02d}/60</text>'
                f'</g>'
            )

    body.append('</svg>')
    return "".join(body)


# ======================================================================
# Public dispatch
# ======================================================================

def render_reading_svg(
    reading: LensReading,
    branch_probabilities: list[tuple[str, float, str]],
    center_top_label: str,
    center_top_value: str,
    center_bottom_label: str,
    center_bottom_value: str,
    center_meta: str,
) -> str:
    """Render the divination instrument for `reading.system`.

    八字 → the astrolabe with the dual readout in the engraved core.
    紫微 / 易经 / 塔罗 → their own visual form with a MODEL / COMBINED
    footer band (the prior comparison chips render below in the app).
    """
    sys = reading.system
    if sys == "iching":
        return _render_iching(reading, center_top_value,
                              center_bottom_value, center_meta)
    if sys == "tarot":
        return _render_tarot(reading, center_top_value,
                             center_bottom_value, center_meta)
    if sys == "ziwei":
        return _render_ziwei(reading, center_top_value,
                             center_bottom_value, center_meta)
    if sys == "astro":
        return _render_astro(reading, branch_probabilities,
                             center_top_label, center_top_value,
                             center_bottom_label, center_bottom_value,
                             center_meta)
    return _render_bazi(reading, branch_probabilities,
                        center_top_label, center_top_value,
                        center_bottom_label, center_bottom_value,
                        center_meta)


def render_celestial_svg(
    reading_bazi: LensReading,
    reading_astro: LensReading,
    branch_probabilities: list[tuple[str, float, str]],
    center_top_label: str,
    center_top_value: str,
    center_bottom_label: str,
    center_bottom_value: str,
    center_meta: str,
) -> str:
    """Render the 玄学 lens as the Nye Clock solar system.

    The unified 玄学 lens calls this once. As of the v4.18 console
    redesign (Stage 3) the dense unified astrolabe — founder verdict
    "不知所云" — is replaced by a faithful static-SVG recreation of the
    founder's real Nye Clock app: a Sun-Earth-Moon orbital with the
    八字 sexagenary movement carried on the Earth orbit ring and the
    占星 Sun / Moon signs placing the bodies.

    The legacy astrolabe renderer (`_render_celestial`) is kept in the
    module for reference / back-compat but is no longer the lens.
    """
    return _render_nye_solar_system(
        reading_bazi, reading_astro, branch_probabilities,
        center_top_label, center_top_value,
        center_bottom_label, center_bottom_value, center_meta,
    )


# Back-compat shim — the previous single-system entry point.
def render_nye_clock_svg(
    bazi: BaZiPattern,
    balance: dict[str, float],
    branch_probabilities: list[tuple[str, float, str]],
    center_top_label: str,
    center_top_value: str,
    center_bottom_label: str,
    center_bottom_value: str,
    center_meta: str,
) -> str:
    """Deprecated — kept so older call sites / tests keep working.

    Wraps the 八字 reading into a LensReading and dispatches.
    """
    reading = LensReading(
        system="bazi", prior=0.5, auspice=0.5,
        bazi=bazi, balance=balance,
    )
    return _render_bazi(reading, branch_probabilities,
                        center_top_label, center_top_value,
                        center_bottom_label, center_bottom_value,
                        center_meta)


__all__ = ["render_reading_svg", "render_celestial_svg",
           "render_nye_clock_svg"]
