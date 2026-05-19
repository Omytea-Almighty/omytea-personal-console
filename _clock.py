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
    HEXAGRAM_NAMES,
    TAROT_POSITIONS,
    TRIGRAM_HANZI,
    TRIGRAM_SYMBOL,
    WUXING_COLOR,
    WUXING_COLOR_DEEP,
    WUXING_HANZI,
    WUXING_KEYS,
    ZIWEI_PALACE_HANZI,
    ZIWEI_PALACES,
    BaZiPattern,
    Hexagram,
    LensReading,
    TarotDraw,
    ZiWeiChart,
    dominant_element,
    pillar_text,
    ziwei_star_hanzi,
)

# ----------------------------------------------------------------------
# Palette
# ----------------------------------------------------------------------
_CANVAS   = "#0a0c11"
_SURFACE  = "#11141b"
_SURFACE2 = "#181c25"
_HAIRLINE = "#232834"
_INK0     = "#f0f2f5"
_INK1     = "#b9bfc8"
_INK2     = "#76808d"
_INK3     = "#4b525d"
_ACCENT   = "#8b8cff"
_TEAL     = "#58c5b4"
_CORAL    = "#ff5e6e"
_AMBER    = "#d8a657"

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
        # drop shadow for floating elements
        '<filter id="drop" x="-40%" y="-40%" width="180%" height="180%">'
        '<feDropShadow dx="0" dy="3" stdDeviation="4" '
        'flood-color="#000000" flood-opacity="0.55"/>'
        '</filter>',
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
        f'<rect x="0" y="0" width="{_VB}" height="{_VB}" fill="url(#bg-glow)"></rect>'
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


# ======================================================================
# Instrument 1 — 八字 "Five-Phase Astrolabe"
# ======================================================================

def _render_bazi(reading: LensReading,
                 branch_probabilities: list[tuple[str, float, str]],
                 top_label: str, top_value: str,
                 bottom_label: str, bottom_value: str,
                 meta: str) -> str:
    bazi = reading.bazi
    balance = reading.balance or {}
    dom_key = dominant_element(balance) if balance else None

    body: list[str] = [_svg_open()]

    # --- outer frame: double hairline ring + 4 cardinal diamonds ---
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
        r1 = 219.0
        r2 = 208.0 if major else 213.0
        x1, y1 = _polar(_CX, _CY, r1, ang)
        x2, y2 = _polar(_CX, _CY, r2, ang)
        body.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{_INK1 if major else _INK3}" '
            f'stroke-width="{1.1 if major else 0.6}" '
            f'opacity="{0.85 if major else 0.5}"></line>'
        )

    # --- 五行 sector ring (gradient wedges) ---
    r_out, r_in_base = 202.0, 152.0
    sector = 72.0
    for i, key in enumerate(WUXING_KEYS):
        share = max(0.0, balance.get(key, 0.0))
        thick = 8.0 + share * (r_out - r_in_base - 8.0)
        r_in = r_out - thick
        a0 = i * sector - sector / 2
        a1 = a0 + sector
        is_dom = (key == dom_key)
        glow = ' filter="url(#soft-glow)"' if is_dom else ""
        body.append(
            f'<path d="{_arc_path(_CX, _CY, r_out, r_in, a0, a1)}" '
            f'fill="url(#wx-{key})" '
            f'fill-opacity="{0.92 if is_dom else 0.62}" '
            f'stroke="{_CANVAS}" stroke-width="1.4"{glow}></path>'
        )
        # element glyph on a small recessed plate
        mr = (r_out + r_in_base) / 2 + 4
        gx, gy = _polar(_CX, _CY, mr, (a0 + a1) / 2)
        plate_r = 13.5 if is_dom else 10.5
        body.append(
            f'<circle cx="{gx:.1f}" cy="{gy:.1f}" r="{plate_r}" '
            f'fill="{_SURFACE}" stroke="{WUXING_COLOR[key]}" '
            f'stroke-width="{1.4 if is_dom else 0.8}" '
            f'opacity="{1.0 if is_dom else 0.9}"></circle>'
            f'<text x="{gx:.1f}" y="{gy+0.5:.1f}" font-family="{_SERIF}" '
            f'font-size="{20 if is_dom else 14}" '
            f'fill="{_INK0 if is_dom else _INK1}" '
            f'font-weight="600" text-anchor="middle" '
            f'dominant-baseline="middle">{WUXING_HANZI[i]}</text>'
        )

    # --- separator hairline + boundary dots ---
    body.append(
        f'<circle cx="{_CX}" cy="{_CY}" r="148" fill="none" '
        f'stroke="{_HAIRLINE}" stroke-width="0.7"></circle>'
    )
    for i in range(5):
        bx, by = _polar(_CX, _CY, 148, i * sector - sector / 2)
        body.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="1.6" '
                    f'fill="{_INK2}"></circle>')

    # --- branch arc ring ---
    body.append(_branch_ring(branch_probabilities, 142.0, 116.0))
    body.append(
        f'<circle cx="{_CX}" cy="{_CY}" r="112" fill="none" '
        f'stroke="{_HAIRLINE}" stroke-width="0.7"></circle>'
    )

    # --- inner micro-tick ring ---
    for i in range(48):
        ang = i * 7.5
        x1, y1 = _polar(_CX, _CY, 110, ang)
        x2, y2 = _polar(_CX, _CY, 106, ang)
        body.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{_INK3}" stroke-width="0.5" opacity="0.5"></line>'
        )

    # --- engraved core with dual readout ---
    body.append(_centre_readout(top_label, top_value,
                                bottom_label, bottom_value, meta,
                                r_core=100.0))

    # --- corner 八字 cartouches ---
    if bazi is not None:
        pillars = (
            (bazi.year_pillar,  "YEAR",  (40, 40)),
            (bazi.month_pillar, "MONTH", (_VB - 40, 40)),
            (bazi.day_pillar,   "DAY",   (40, _VB - 40)),
            (bazi.hour_pillar,  "HOUR",  (_VB - 40, _VB - 40)),
        )
        for pil, name, (px, py) in pillars:
            body.append(
                f'<g transform="translate({px-32},{py-19})">'
                f'<rect x="0" y="0" width="64" height="38" rx="6" '
                f'fill="{_SURFACE2}" stroke="{_HAIRLINE}" stroke-width="1"></rect>'
                f'<text x="32" y="17" font-family="{_SERIF}" font-size="17" '
                f'fill="{_INK0}" font-weight="600" text-anchor="middle" '
                f'dominant-baseline="middle">{_esc(pillar_text(pil),4)}</text>'
                f'<text x="32" y="30" font-family="{_MONO}" font-size="7.5" '
                f'fill="{_INK3}" letter-spacing="0.18em" text-anchor="middle">'
                f'{name}</text>'
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
    """A compact line-art emblem for a Tarot card, ~46px tall."""
    s = f'stroke="{col}" stroke-width="2" fill="none" ' \
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
        # card plate + double frame
        body.append(
            f'<g filter="url(#drop)">'
            f'<rect x="{cx0:.1f}" y="{cy0:.1f}" width="{card_w}" '
            f'height="{card_h}" rx="11" fill="{_SURFACE2}" '
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
        # emblem (rotated 180° if reversed)
        gcx, gcy = ccx, cy0 + card_h / 2 - 6
        glyph_col = _AMBER if not is_rev else _INK2
        rot = f' transform="rotate(180 {gcx:.1f} {gcy:.1f})"' if is_rev else ""
        body.append(f'<g{rot}>{_tarot_glyph(card.glyph, gcx, gcy, glyph_col)}</g>')
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


def _render_ziwei(reading: LensReading,
                  model_value: str, combined_value: str,
                  meta: str) -> str:
    chart: ZiWeiChart = reading.ziwei  # type: ignore[assignment]
    body: list[str] = [_svg_open()]

    body.append(
        f'<text x="{_CX}" y="58" font-family="{_MONO}" font-size="9.5" '
        f'fill="{_INK2}" letter-spacing="0.26em" text-anchor="middle">'
        f'ZIWEI DOU SHU · 12 PALACES</text>'
    )

    grid_x, grid_y = 56.0, 74.0
    cell = 92.0

    # outer frame
    body.append(
        f'<rect x="{grid_x-6}" y="{grid_y-6}" width="{cell*4+12}" '
        f'height="{cell*4+12}" rx="12" fill="none" '
        f'stroke="{_HAIRLINE}" stroke-width="1.1"></rect>'
    )

    for idx, (gx, gy) in enumerate(_ZIWEI_CELL_XY):
        palace = ZIWEI_PALACES[idx]
        x = grid_x + gx * cell
        y = grid_y + gy * cell
        is_ming = (palace == "ming")
        fill = "rgba(139,140,255,0.10)" if is_ming else _SURFACE
        stroke = _ACCENT if is_ming else _HAIRLINE
        body.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell}" height="{cell}" '
            f'rx="7" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{1.5 if is_ming else 0.9}"></rect>'
        )
        # palace name (top-left of cell)
        body.append(
            f'<text x="{x+9:.1f}" y="{y+19:.1f}" font-family="{_SERIF}" '
            f'font-size="14" fill="{_ACCENT if is_ming else _INK1}" '
            f'font-weight="600">{ZIWEI_PALACE_HANZI[palace]}</text>'
        )
        # stars in this palace (stacked, centred)
        stars = chart.palace_stars.get(palace, [])
        for si, star in enumerate(stars[:4]):
            body.append(
                f'<text x="{x+cell/2:.1f}" y="{y+40+si*17:.1f}" '
                f'font-family="{_SERIF}" font-size="15" fill="{_INK0}" '
                f'text-anchor="middle" font-weight="500">'
                f'{_esc(ziwei_star_hanzi(star),2)}</text>'
            )
        if not stars:
            body.append(
                f'<text x="{x+cell/2:.1f}" y="{y+cell/2+8:.1f}" '
                f'font-family="{_MONO}" font-size="9" fill="{_INK3}" '
                f'text-anchor="middle">·</text>'
            )

    # centre summary plate (the 2×2 hole)
    cxp = grid_x + cell
    cyp = grid_y + cell
    body.append(
        f'<rect x="{cxp:.1f}" y="{cyp:.1f}" width="{cell*2}" '
        f'height="{cell*2}" rx="10" fill="url(#core-grad)" '
        f'stroke="{_HAIRLINE}" stroke-width="1.1"></rect>'
        f'<text x="{_CX}" y="{cyp+44:.1f}" font-family="{_MONO}" '
        f'font-size="9" fill="{_INK2}" letter-spacing="0.2em" '
        f'text-anchor="middle">MODEL</text>'
        f'<text x="{_CX}" y="{cyp+72:.1f}" font-family="{_SERIF}" '
        f'font-size="27" fill="{_INK0}" font-weight="600" '
        f'text-anchor="middle" filter="url(#num-glow)">'
        f'{_esc(model_value,8)}</text>'
        f'<line x1="{_CX-30}" y1="{cyp+88:.1f}" x2="{_CX+30}" '
        f'y2="{cyp+88:.1f}" stroke="{_HAIRLINE}" stroke-width="0.9"></line>'
        f'<text x="{_CX}" y="{cyp+108:.1f}" font-family="{_MONO}" '
        f'font-size="9" fill="{_INK2}" letter-spacing="0.2em" '
        f'text-anchor="middle">COMBINED</text>'
        f'<text x="{_CX}" y="{cyp+136:.1f}" font-family="{_SERIF}" '
        f'font-size="27" fill="{_ACCENT}" font-weight="600" '
        f'text-anchor="middle" filter="url(#num-glow)">'
        f'{_esc(combined_value,8)}</text>'
    )
    body.append(
        f'<text x="{_CX}" y="{_VB-30:.1f}" font-family="{_MONO}" '
        f'font-size="8.5" fill="{_INK3}" letter-spacing="0.18em" '
        f'text-anchor="middle">{_esc(meta,40)}</text>'
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
    return _render_bazi(reading, branch_probabilities,
                        center_top_label, center_top_value,
                        center_bottom_label, center_bottom_value,
                        center_meta)


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


__all__ = ["render_reading_svg", "render_nye_clock_svg"]
